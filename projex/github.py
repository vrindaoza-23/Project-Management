# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""GitHub integration: inbound webhooks + linking + auto status transitions.

The flow mirrors what Linear/Jira do:

  1. A developer names a branch / PR that mentions an issue's key (BIL-12).
  2. GitHub POSTs a signed webhook here on PR open / sync / merge / CI.
  3. We verify the signature, parse the magic word, and:
       - upsert a Projex GitHub Link row (PR state, CI, author…),
       - move the issue (open -> In Progress, merge -> Done),
       - drop a system comment on the issue,
     all fanned out over realtime like any other mutation.

Everything degrades cleanly: no settings / disabled / unmapped repo -> no-op.
Outbound calls (posting a comment back to the PR) are best-effort and only
happen when an access token is configured.
"""

import hashlib
import hmac
import json
import re

import frappe
from frappe.utils import now_datetime

SETTINGS = "Projex GitHub Settings"
LINK = "Projex GitHub Link"

# An issue key looks like BIL-12 / WEB-3: uppercase project key, dash, number.
# We match it inside branch names, PR titles/bodies and commit messages.
MAGIC_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
# "closes/fixes/resolves BIL-12" — only these mark an issue Done on merge.
CLOSING_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+([A-Z][A-Z0-9]+-\d+)", re.I)

GITHUB_API = "https://api.github.com"


# --------------------------------------------------------------------------- #
# Inbound webhook
# --------------------------------------------------------------------------- #
@frappe.whitelist(allow_guest=True)
def webhook():
	"""Receive a GitHub webhook. Verify, then dispatch by event type."""
	settings = _settings()
	if not settings.enabled:
		return {"ok": False, "msg": "integration disabled"}

	raw = frappe.request.get_data() if frappe.request else b""
	sig = frappe.get_request_header("X-Hub-Signature-256") or ""
	if not _verify_signature(raw, sig, settings.get_password("webhook_secret", raise_exception=False)):
		frappe.throw("Invalid signature", frappe.PermissionError)

	event = frappe.get_request_header("X-GitHub-Event") or ""
	if event == "ping":
		return {"ok": True, "msg": "pong"}

	payload = frappe.parse_json(raw.decode("utf-8")) if raw else {}
	# The request is trusted now (HMAC verified). Run the rest as a system user
	# so activity, notifications and permission checks resolve to a real actor.
	frappe.set_user("Administrator")
	try:
		handler = {
			"pull_request": handle_pull_request,
			"push": handle_push,
			"check_suite": handle_check_suite,
			"status": handle_status,
			"installation": handle_installation,
		}.get(event)
		if handler:
			handler(payload, settings)
			frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(f"projex github webhook failed: {event}")
	# Always 200 so GitHub doesn't enter a redelivery storm.
	return {"ok": True, "event": event}


def handle_pull_request(payload, settings):
	pr = payload.get("pull_request") or {}
	action = payload.get("action")
	repo = (payload.get("repository") or {}).get("full_name")
	project = _project_for_repo(settings, repo)
	if not project or not pr:
		return

	branch = (pr.get("head") or {}).get("ref") or ""
	text = " ".join([pr.get("title") or "", pr.get("body") or "", branch])
	issues = _issues_in(text, project)
	if not issues:
		return

	state = _pr_state(pr)
	user = pr.get("user") or {}
	newly = []
	for issue in issues:
		link, created = _upsert_link(
			match={"issue": issue, "kind": "Pull Request", "repository": repo, "number": pr.get("number")},
			values={
				"title": pr.get("title"), "url": pr.get("html_url"), "branch": branch,
				"state": state, "merged": 1 if pr.get("merged") else 0,
				"author": user.get("login"), "author_avatar": user.get("avatar_url"),
			},
		)
		if created:
			newly.append(issue)
			if settings.post_comment:
				_comment(issue, f'🔗 Linked pull request <a href="{pr.get("html_url")}">{repo}#{pr.get("number")}</a>'
						 f' opened by @{user.get("login")}.')

	# Post a comment back onto the PR the first time it links issues (best-effort,
	# in the background so a slow/failing GitHub API never blocks the webhook).
	if newly and action in ("opened", "reopened", "ready_for_review") and _access_token():
		frappe.enqueue(
			"projex.github.push_pr_comment", queue="short",
			repo=repo, number=pr.get("number"), issues=newly,
		)

	_apply_transitions(action, pr, text, issues, project, settings)


def handle_push(payload, settings):
	"""Link commits whose messages mention an issue key."""
	repo = (payload.get("repository") or {}).get("full_name")
	project = _project_for_repo(settings, repo)
	if not project:
		return
	branch = (payload.get("ref") or "").replace("refs/heads/", "")
	for commit in payload.get("commits") or []:
		msg = commit.get("message") or ""
		for issue in _issues_in(msg, project):
			author = commit.get("author") or {}
			_upsert_link(
				match={"issue": issue, "kind": "Commit", "repository": repo, "url": commit.get("url")},
				values={
					"number": 0, "branch": branch, "state": "merged", "merged": 1,
					"title": msg.splitlines()[0][:140], "author": author.get("username") or author.get("name"),
				},
			)


def handle_check_suite(payload, settings):
	"""Roll a CI conclusion onto the PR links it belongs to."""
	suite = payload.get("check_suite") or {}
	repo = (payload.get("repository") or {}).get("full_name")
	ci = _ci_from_conclusion(suite.get("status"), suite.get("conclusion"))
	for pr in suite.get("pull_requests") or []:
		_set_ci(repo, pr.get("number"), ci)


def handle_installation(payload, settings):
	"""Track the App installation id as it's added/removed on GitHub."""
	from projex import github_app

	action = payload.get("action")
	inst = (payload.get("installation") or {}).get("id")
	if action in ("created", "new_permissions_accepted", "unsuspend") and inst:
		github_app.set_installation(inst)
	elif action in ("deleted", "suspend"):
		github_app.clear_installation()


def handle_status(payload, settings):
	"""Legacy commit-status event: map to PR links by branch."""
	repo = (payload.get("repository") or {}).get("full_name")
	ci = _ci_from_conclusion("completed" if payload.get("state") != "pending" else "in_progress", payload.get("state"))
	for branch in payload.get("branches") or []:
		names = frappe.get_all(
			LINK, filters={"repository": repo, "branch": branch.get("name"), "kind": "Pull Request"}, pluck="name"
		)
		for name in names:
			frappe.db.set_value(LINK, name, "ci_status", ci, update_modified=False)


# --------------------------------------------------------------------------- #
# Transitions
# --------------------------------------------------------------------------- #
def _apply_transitions(action, pr, text, issues, project, settings):
	# PR opened / marked ready -> In Progress (only from a not-yet-started state).
	if settings.move_on_open and action in ("opened", "reopened", "ready_for_review"):
		target = _status_for(project, "started")
		for issue in issues:
			_move_issue(issue, target, forward_only=("backlog", "unstarted"))

	# PR merged -> Done. Respect the "closing keyword" preference.
	if settings.move_on_merge and action == "closed" and pr.get("merged"):
		closers = _issues_in(text, project, regex=CLOSING_RE) if settings.close_on_keyword else issues
		target = _status_for(project, "completed")
		for issue in closers:
			_move_issue(issue, target, block=("completed", "cancelled"))


def _move_issue(issue, target_status, forward_only=None, block=None):
	"""Set an issue's status, guarding against pointless / backward moves.

	forward_only: only move when the issue's current category is in this set.
	block:        never move when the current category is in this set.
	Saving flows through the normal controller so realtime/activity/notify fire.
	"""
	if not target_status:
		return
	doc = frappe.get_doc("Projex Issue", issue)
	if doc.status == target_status:
		return
	current = frappe.db.get_value("Projex Status", doc.status, "category") if doc.status else None
	if forward_only is not None and current not in forward_only:
		return
	if block is not None and current in block:
		return
	doc.status = target_status
	doc.save(ignore_permissions=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _settings():
	return frappe.get_cached_doc(SETTINGS)


def is_enabled():
	try:
		return bool(frappe.get_cached_value(SETTINGS, SETTINGS, "enabled"))
	except Exception:
		return False


def _verify_signature(raw, header, secret):
	if not secret or not header.startswith("sha256="):
		return False
	digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
	return hmac.compare_digest(f"sha256={digest}", header)


def _project_for_repo(settings, repo):
	if not repo:
		return None
	for row in settings.repos or []:
		if (row.repository or "").strip().lower() == repo.strip().lower():
			return row.project
	return None


def _issues_in(text, project, regex=MAGIC_RE):
	"""Distinct, in-project issue keys mentioned in text (name == issue_id)."""
	out = []
	for key in dict.fromkeys(m.upper() for m in regex.findall(text or "")):
		if frappe.db.get_value("Projex Issue", key, "project") == project and key not in out:
			out.append(key)
	return out


def _pr_state(pr):
	if pr.get("merged"):
		return "merged"
	if pr.get("draft"):
		return "draft"
	return "closed" if pr.get("state") == "closed" else "open"


def _status_for(project, category):
	"""Lowest-position status of a category, project-scoped then global."""
	return frappe.db.get_value(
		"Projex Status", {"project": project, "category": category}, "name", order_by="position asc"
	) or frappe.db.get_value(
		"Projex Status", {"project": ["in", ["", None]], "category": category}, "name", order_by="position asc"
	)


def _ci_from_conclusion(status, conclusion):
	if status and status != "completed":
		return "pending"
	return {"success": "success", "failure": "failure", "timed_out": "failure", "cancelled": "failure"}.get(
		conclusion, "pending"
	)


def _set_ci(repo, number, ci):
	name = frappe.db.get_value(LINK, {"repository": repo, "number": number, "kind": "Pull Request"}, "name")
	if name:
		frappe.db.set_value(LINK, name, "ci_status", ci, update_modified=False)


def _upsert_link(match, values):
	name = frappe.db.get_value(LINK, match, "name")
	values = {**values, "last_synced": now_datetime()}
	if name:
		doc = frappe.get_doc(LINK, name)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc, False
	doc = frappe.get_doc({"doctype": LINK, **match, **values})
	doc.insert(ignore_permissions=True)
	return doc, True


def _comment(issue, html):
	"""System comment on the issue — reuses the normal comment path so it
	fans out over realtime and notifies participants."""
	frappe.get_doc({"doctype": "Projex Comment", "issue": issue, "content": html}).insert(ignore_permissions=True)


# --------------------------------------------------------------------------- #
# Outbound (GitHub REST API) — all optional, gated on an access token.
# --------------------------------------------------------------------------- #
def _access_token():
	"""Effective token for GitHub API calls: prefer the App installation token,
	fall back to a manually configured personal access token."""
	from projex import github_app

	tok = github_app.installation_token()
	if tok:
		return tok
	try:
		return _settings().get_password("access_token", raise_exception=False)
	except Exception:
		return None


def _gh_request(method, path, token, json=None):
	"""Thin GitHub REST call. Returns parsed JSON or None; never raises.
	`token` may be None for unauthenticated endpoints (manifest conversion)."""
	import requests

	headers = {
		"Accept": "application/vnd.github+json",
		"X-GitHub-Api-Version": "2022-11-28",
	}
	if token:
		headers["Authorization"] = f"Bearer {token}"
	try:
		resp = requests.request(method, f"{GITHUB_API}{path}", headers=headers, json=json, timeout=10)
		if resp.status_code >= 300:
			frappe.log_error(f"github api {method} {path} -> {resp.status_code}: {resp.text[:500]}")
			return None
		return resp.json() if resp.content else {}
	except Exception:
		frappe.log_error(f"github api {method} {path} failed")
		return None


def push_pr_comment(repo, number, issues):
	"""Comment back on the PR with deep links to the issues it now tracks.
	Enqueued from the webhook so GitHub latency never blocks the response."""
	token = _access_token()
	if not token or not number:
		return
	lines = [f"- **{i}** — {_issue_deeplink(i)}" for i in issues]
	body = "Tracked in Projex:\n" + "\n".join(lines)
	_gh_request("POST", f"/repos/{repo}/issues/{number}/comments", token, json={"body": body})


def _issue_deeplink(issue):
	"""Best-effort URL to where this issue lives (the project board); the SPA
	has no per-issue route, so we link the board and name the issue."""
	row = frappe.db.get_value("Projex Issue", issue, ["project"], as_dict=True)
	key = frappe.db.get_value("Projex Project", row.project, "key") if row else None
	return frappe.utils.get_url(f"/projex/projects/{key}") if key else frappe.utils.get_url("/projex")


def _refresh_one(link, token):
	"""Reconcile one PR link against GitHub: state, merged, draft, CI."""
	pull = _gh_request("GET", f"/repos/{link.repository}/pulls/{link.number}", token)
	if not pull:
		return
	updates = {"state": _pr_state(pull), "merged": 1 if pull.get("merged") else 0, "last_synced": now_datetime()}
	sha = (pull.get("head") or {}).get("sha")
	if sha:
		combined = _gh_request("GET", f"/repos/{link.repository}/commits/{sha}/status", token)
		if combined:
			updates["ci_status"] = _ci_from_conclusion("completed", combined.get("state"))
	frappe.db.set_value(LINK, link.name, updates, update_modified=False)


# --------------------------------------------------------------------------- #
# SPA-facing API
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_settings():
	"""Admin view of the config. Secrets are returned as booleans, never values."""
	frappe.only_for("System Manager")
	s = _settings()
	return {
		"enabled": bool(s.enabled),
		"account": s.account,
		"has_webhook_secret": bool(s.get_password("webhook_secret", raise_exception=False)),
		"has_access_token": bool(s.get_password("access_token", raise_exception=False)),
		"app_connected": bool(s.app_id),
		"app_slug": s.app_slug,
		"app_installed": bool(s.installation_id),
		"move_on_open": bool(s.move_on_open),
		"move_on_merge": bool(s.move_on_merge),
		"close_on_keyword": bool(s.close_on_keyword),
		"post_comment": bool(s.post_comment),
		"repos": [{"repository": r.repository, "project": r.project} for r in (s.repos or [])],
		"webhook_url": frappe.utils.get_url("/api/method/projex.github.webhook"),
	}


@frappe.whitelist()
def save_settings(payload):
	"""Persist admin edits. Secret fields only overwrite when a value is sent."""
	frappe.only_for("System Manager")
	data = frappe.parse_json(payload)
	s = _settings()
	s.enabled = 1 if data.get("enabled") else 0
	s.account = data.get("account")
	for flag in ("move_on_open", "move_on_merge", "close_on_keyword", "post_comment"):
		setattr(s, flag, 1 if data.get(flag) else 0)
	if data.get("webhook_secret"):
		s.webhook_secret = data["webhook_secret"]
	if data.get("access_token"):
		s.access_token = data["access_token"]
	s.repos = []
	for row in data.get("repos") or []:
		if row.get("repository") and row.get("project"):
			s.append("repos", {"repository": row["repository"].strip(), "project": row["project"]})
	s.save(ignore_permissions=True)
	frappe.db.commit()
	return get_settings()


@frappe.whitelist()
def generate_secret():
	"""A fresh random secret for the admin to paste into GitHub. Not persisted
	until they save."""
	frappe.only_for("System Manager")
	return frappe.generate_hash(length=40)


@frappe.whitelist()
def disconnect():
	frappe.only_for("System Manager")
	s = _settings()
	s.enabled = 0
	s.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def links_for_issue(issue):
	"""PR/branch/commit links shown in the Task Drawer for one issue."""
	_require_issue_access(issue)
	return _links(issue)


@frappe.whitelist()
def refresh_links(issue):
	"""Reconcile this issue's PR links against GitHub on demand. Needs a token."""
	_require_issue_access(issue)
	token = _access_token()
	if not token:
		frappe.throw("Add a GitHub access token in Integrations settings to refresh from GitHub.")
	for link in frappe.get_all(LINK, filters={"issue": issue, "kind": "Pull Request"}, fields=["name", "repository", "number"]):
		_refresh_one(frappe._dict(link), token)
	frappe.db.commit()
	return _links(issue)


@frappe.whitelist()
def remove_link(name):
	"""Unlink a PR/commit from its issue (does not touch anything on GitHub)."""
	issue = frappe.db.get_value(LINK, name, "issue")
	if not issue:
		return {"ok": True}
	_require_issue_access(issue)
	frappe.delete_doc(LINK, name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


def _require_issue_access(issue):
	from projex.permissions import user_can_access_project

	project = frappe.db.get_value("Projex Issue", issue, "project")
	if not project or not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)


def _links(issue):
	rows = frappe.get_all(
		LINK,
		filters={"issue": issue},
		fields=[
			"name", "kind", "repository", "number", "title", "url", "branch",
			"state", "ci_status", "merged", "author", "author_avatar",
		],
		order_by="creation asc",
	)
	return rows
