# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Whitelisted RPC endpoints for the Projex SPA.

The SPA reads most data through the auto REST API (`/api/resource/Projex *`)
via frappe-ui `useList`/`useDoc`. These methods cover aggregates and actions
that don't map cleanly to a single resource: personal queues, the inbox,
roadmap bars, drag-reorder, presence, the ERPNext time-log action, and AI.
"""

import re
from datetime import date

import frappe
from frappe.utils import add_days, getdate, nowdate, now_datetime

from projex import ai
from projex.permissions import accessible_projects
from projex.realtime import emit_presence

ISSUE_FIELDS = [
	"name", "issue_id", "title", "project", "status", "priority", "issue_type",
	"due_date", "start_date", "estimate", "rank", "cycle", "reporter", "parent_issue", "modified",
	"creation", "status_changed_on", "reopen_count", "rework_count",
]


# --------------------------------------------------------------------------- #
# Management / admin (all self-serve in-app — no desk needed)
# --------------------------------------------------------------------------- #
def _ensure_member_role():
	"""Logged-in users need the Projex Member role to create/manage."""
	if frappe.session.user == "Guest":
		frappe.throw("Login required", frappe.PermissionError)
	roles = set(frappe.get_roles())
	if not (roles & {"System Manager", "Projex Admin", "Projex Member"}):
		# Auto-grant base role so any authenticated user can self-serve.
		user = frappe.get_doc("User", frappe.session.user)
		user.append("roles", {"role": "Projex Member"})
		user.save(ignore_permissions=True)


@frappe.whitelist()
def create_workspace(workspace_name, icon=None):
	_ensure_member_role()
	if frappe.db.exists("Projex Workspace", workspace_name):
		frappe.throw(f"Workspace '{workspace_name}' already exists")
	doc = frappe.get_doc({
		"doctype": "Projex Workspace", "workspace_name": workspace_name, "icon": icon or "box",
		"members": [{"user": frappe.session.user, "role": "Admin"}],
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "workspace_name": doc.workspace_name, "icon": doc.icon}


@frappe.whitelist()
def get_workspace_detail(workspace):
	"""Everything the workspace settings dialog needs: profile, members, teams."""
	if not frappe.db.exists("Projex Workspace", workspace):
		frappe.throw("Workspace not found")
	if not _can_view_workspace(workspace):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc("Projex Workspace", workspace)
	members = [
		{
			"user": m.user, "role": m.role,
			"full_name": frappe.db.get_value("User", m.user, "full_name") or m.user,
		}
		for m in doc.members
	]
	teams = frappe.get_all(
		"Projex Team", filters={"workspace": workspace},
		fields=["name", "team_name", "icon", "color"], order_by="team_name asc",
	)
	project_count = frappe.db.count("Projex Project", {"workspace": workspace})
	return {
		"workspace": {
			"name": doc.name, "workspace_name": doc.workspace_name,
			"icon": doc.icon, "description": doc.description,
			"can_manage": _can_manage_workspace(workspace),
			"project_count": project_count,
		},
		"members": members,
		"teams": teams,
	}


@frappe.whitelist()
def update_workspace(workspace, fields):
	import json
	if isinstance(fields, str):
		fields = json.loads(fields)
	if not _can_manage_workspace(workspace):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc("Projex Workspace", workspace)
	for k in ("workspace_name", "icon", "description"):
		if k in fields:
			doc.set(k, fields[k])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def delete_workspace(workspace):
	"""Delete an empty workspace. Refuses while any project still lives in it —
	projects must be moved or deleted first. Its (project-less) teams go with it."""
	if not _can_manage_workspace(workspace):
		frappe.throw("Not permitted", frappe.PermissionError)
	if frappe.db.count("Projex Project", {"workspace": workspace}):
		frappe.throw("Move or delete this workspace's projects before deleting it.")
	for t in frappe.get_all("Projex Team", filters={"workspace": workspace}, pluck="name"):
		frappe.delete_doc("Projex Team", t, ignore_permissions=True, force=True)
	frappe.delete_doc("Projex Workspace", workspace, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def create_team(workspace, team_name, icon=None, color=None):
	"""Create a Team — an optional grouping of projects inside a workspace."""
	_ensure_member_role()
	if not workspace or not frappe.db.exists("Projex Workspace", workspace):
		frappe.throw("A valid workspace is required")
	if not _can_manage_workspace(workspace):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc({
		"doctype": "Projex Team", "team_name": team_name,
		"workspace": workspace, "icon": icon or "users", "color": color,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "team_name": doc.team_name, "workspace": doc.workspace, "icon": doc.icon}


@frappe.whitelist()
def update_team(team, fields):
	import json
	if isinstance(fields, str):
		fields = json.loads(fields)
	doc = frappe.get_doc("Projex Team", team)
	if not _can_manage_workspace(doc.workspace):
		frappe.throw("Not permitted", frappe.PermissionError)
	# Moving a team to another workspace needs manage rights on the destination too.
	dest = fields.get("workspace")
	if dest and dest != doc.workspace and not _can_manage_workspace(dest):
		frappe.throw("Not permitted", frappe.PermissionError)
	for k in ("team_name", "icon", "color", "workspace"):
		if k in fields:
			doc.set(k, fields[k])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def delete_team(team):
	"""Delete a team. Projects are kept — they just become ungrouped."""
	workspace = frappe.db.get_value("Projex Team", team, "workspace")
	if not _can_manage_workspace(workspace):
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.db.set_value("Projex Project", {"team": team}, "team", None)
	frappe.delete_doc("Projex Team", team, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def create_project(payload):
	import json
	if isinstance(payload, str):
		payload = json.loads(payload)
	_ensure_member_role()
	key = (payload.get("key") or "").strip().upper()
	if frappe.db.exists("Projex Project", key):
		frappe.throw(f"Project key '{key}' already in use")
	members = payload.get("members") or []
	user = frappe.session.user
	if not any(m.get("user") == user for m in members):
		members.append({"user": user, "role": "Admin"})
	doc = frappe.get_doc({
		"doctype": "Projex Project",
		"project_name": payload.get("project_name"),
		"key": key,
		"icon": payload.get("icon") or "folder",
		"color": payload.get("color"),
		"status": payload.get("status") or "Active",
		"lead": payload.get("lead") or user,
		"workspace": payload.get("workspace"),
		"team": payload.get("team"),
		"description": payload.get("description"),
		"members": [{"user": m["user"], "role": m.get("role", "Member")} for m in members],
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "key": doc.key, "project_name": doc.project_name}


@frappe.whitelist()
def update_project(project, fields):
	import json
	if isinstance(fields, str):
		fields = json.loads(fields)
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc("Projex Project", project)
	for k in ("project_name", "icon", "color", "status", "lead", "description", "workspace", "team"):
		if k in fields:
			doc.set(k, fields[k])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def get_project_detail(project):
	"""Everything the project settings dialog needs."""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc("Projex Project", project)
	members = []
	for m in doc.members:
		members.append({
			"user": m.user, "role": m.role,
			"full_name": frappe.db.get_value("User", m.user, "full_name") or m.user,
			"is_all_access": bool(
				set(frappe.get_roles(m.user)) & {"System Manager", "Projex Admin", "Administrator"}
			),
		})
	labels = frappe.get_all(
		"Projex Label", filters={"project": project}, fields=["name", "label_name", "color"]
	)
	cycles = frappe.get_all(
		"Projex Cycle", filters={"project": project},
		fields=["name", "cycle_name", "start_date", "end_date", "state"], order_by="start_date desc",
	)
	return {
		"project": {
			"name": doc.name, "project_name": doc.project_name, "key": doc.key,
			"icon": doc.icon, "color": doc.color, "status": doc.status, "lead": doc.lead,
			"workspace": doc.workspace, "team": doc.team, "description": doc.description,
			"is_archived": doc.is_archived,
			"can_manage": _can_manage_project(project),
			"can_grant_all_access": bool(
				set(frappe.get_roles()) & {"System Manager", "Projex Admin"}
			),
		},
		"members": members,
		"labels": labels,
		"cycles": cycles,
	}


# --------------------------------------------------------------------------- #
# People (per-project member management + activity)
# --------------------------------------------------------------------------- #
OPEN_CATEGORIES = {"backlog", "unstarted", "started"}


def _status_categories():
	"""Map of status name -> category (global + project-scoped)."""
	return {
		s.name: s.category
		for s in frappe.get_all("Projex Status", fields=["name", "category"])
	}


@frappe.whitelist()
def get_users_overview():
	"""All app users with a project-allocation + activity rollup, for the global
	Users management page. Restricted to people who manage at least one project."""
	if not _can_manage_any():
		frappe.throw("Not permitted", frappe.PermissionError)

	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		limit=0,
	)

	# Project allocation count (membership parents ∪ lead) per user — 2 queries.
	proj_set = {}
	for m in frappe.get_all("Projex Project Member", fields=["parent", "user"]):
		proj_set.setdefault(m.user, set()).add(m.parent)
	for p in frappe.get_all("Projex Project", fields=["name", "lead"]):
		if p.lead:
			proj_set.setdefault(p.lead, set()).add(p.name)

	# Cross-project open-task load + last activity — batched scans.
	cats = _status_categories()
	issues = frappe.get_all("Projex Issue", fields=["name", "status"], limit=0)
	status_of = {i.name: i.status for i in issues}
	open_load, assigned_total = {}, {}
	for r in frappe.get_all("Projex Issue Assignee", fields=["parent", "user"]):
		assigned_total[r.user] = assigned_total.get(r.user, 0) + 1
		if cats.get(status_of.get(r.parent)) in OPEN_CATEGORIES:
			open_load[r.user] = open_load.get(r.user, 0) + 1

	last_act = {}
	for a in frappe.get_all(
		"Projex Activity", fields=["actor", "creation"], order_by="creation desc", limit=0
	):
		if a.actor not in last_act:
			last_act[a.actor] = a.creation

	privileged = {"System Manager", "Projex Admin", "Administrator"}
	out = []
	for u in users:
		out.append({
			"user": u.name,
			"full_name": u.full_name or u.name,
			"user_image": u.user_image,
			"project_count": len(proj_set.get(u.name, ())),
			"open_tasks": open_load.get(u.name, 0),
			"assigned": assigned_total.get(u.name, 0),
			"is_all_access": bool(set(frappe.get_roles(u.name)) & privileged),
			"last_activity": last_act.get(u.name),
		})
	return {
		"can_grant_all_access": bool(set(frappe.get_roles()) & {"System Manager", "Projex Admin"}),
		"users": out,
	}


@frappe.whitelist()
def get_user_detail(user):
	"""One user's project allocations + cross-project activity for the Users page."""
	if not _can_manage_any():
		frappe.throw("Not permitted", frappe.PermissionError)

	cats = _status_categories()
	status_name = {
		s.name: s.status_name
		for s in frappe.get_all("Projex Status", fields=["name", "status_name"])
	}
	# project meta (name -> {project_name, key})
	pmeta = {
		p.name: p for p in frappe.get_all(
			"Projex Project", fields=["name", "project_name", "key", "lead"], limit=0
		)
	}

	# Allocations: projects where the user is a member (role) or lead.
	role_in = {
		m.parent: m.role for m in frappe.get_all(
			"Projex Project Member", filters={"user": user}, fields=["parent", "role"]
		)
	}
	member_projects = set(role_in)
	for name, p in pmeta.items():
		if p.lead == user:
			member_projects.add(name)

	projects = []
	for name in sorted(member_projects):
		p = pmeta.get(name)
		if not p:
			continue
		projects.append({
			"project": name,
			"project_name": p.project_name,
			"key": p.key,
			"role": role_in.get(name) or ("Lead" if p.lead == user else "Member"),
			"can_manage": _can_manage_project(name),
		})

	# Projects the actor can manage and where the user is NOT already a member.
	allocatable = [
		{"value": name, "label": p.project_name}
		for name, p in pmeta.items()
		if name not in member_projects and _can_manage_project(name)
	]
	allocatable.sort(key=lambda x: (x["label"] or "").lower())

	# Cross-project assigned tasks (readable status + project key).
	my_issue_names = {
		r.parent for r in frappe.get_all(
			"Projex Issue Assignee", filters={"user": user}, fields=["parent"]
		)
	}
	assigned = []
	if my_issue_names:
		for it in frappe.get_all(
			"Projex Issue", filters={"name": ["in", list(my_issue_names)]},
			fields=["name", "issue_id", "title", "status", "priority", "project"], limit=0,
		):
			pm = pmeta.get(it.project)
			assigned.append({
				"name": it.name, "issue_id": it.issue_id, "title": it.title,
				"status_name": status_name.get(it.status) or it.status,
				"category": cats.get(it.status),
				"project_key": pm.key if pm else it.project,
			})

	def _key_for_issue(issue):
		if not issue:
			return None
		proj = frappe.db.get_value("Projex Issue", issue, "project")
		pm = pmeta.get(proj)
		return pm.key if pm else proj

	activity = frappe.get_all(
		"Projex Activity", filters={"actor": user},
		fields=["name", "action", "detail", "issue", "project", "creation"],
		order_by="creation desc", limit=30,
	)
	for a in activity:
		pm = pmeta.get(a.project)
		a["project_key"] = pm.key if pm else a.project
		a["issue_id"] = frappe.db.get_value("Projex Issue", a.issue, "issue_id") if a.issue else None

	def _snippet(html):
		text = frappe.utils.strip_html(html or "").strip()
		return (text[:140] + "…") if len(text) > 140 else text

	comments = frappe.get_all(
		"Projex Comment", filters={"owner": user},
		fields=["name", "issue", "content", "creation"],
		order_by="creation desc", limit=20,
	)
	for c in comments:
		c["issue_id"] = frappe.db.get_value("Projex Issue", c.issue, "issue_id") if c.issue else None
		c["project_key"] = _key_for_issue(c.issue)
		c["snippet"] = _snippet(c.content)
		c.pop("content", None)

	# Mentions of this user across all comments (regex on @email).
	mentions = []
	for c in frappe.get_all(
		"Projex Comment", fields=["name", "issue", "content", "creation", "owner"],
		order_by="creation desc", limit=400,
	):
		if f"@{user}" in (c.content or ""):
			mentions.append({
				"name": c.name, "issue": c.issue,
				"issue_id": frappe.db.get_value("Projex Issue", c.issue, "issue_id") if c.issue else None,
				"project_key": _key_for_issue(c.issue),
				"by": frappe.db.get_value("User", c.owner, "full_name") or c.owner,
				"snippet": _snippet(c.content), "creation": c.creation,
			})
		if len(mentions) >= 20:
			break

	privileged = {"System Manager", "Projex Admin", "Administrator"}
	return {
		"user": user,
		"full_name": frappe.db.get_value("User", user, "full_name") or user,
		"user_image": frappe.db.get_value("User", user, "user_image"),
		"is_all_access": bool(set(frappe.get_roles(user)) & privileged),
		"can_grant_all_access": bool(set(frappe.get_roles()) & {"System Manager", "Projex Admin"}),
		"projects": projects,
		"allocatable": allocatable,
		"assigned": assigned,
		"activity": activity,
		"comments": comments,
		"mentions": mentions,
	}



def _can_manage_project(project):
	roles = set(frappe.get_roles())
	if roles & {"System Manager", "Projex Admin"}:
		return True
	user = frappe.session.user
	if frappe.db.get_value("Projex Project", project, "lead") == user:
		return True
	# project member with Admin role
	for m in frappe.get_all(
		"Projex Project Member", filters={"parent": project, "user": user}, fields=["role"]
	):
		if m.role == "Admin":
			return True
	return False


def _can_manage_any(user=None):
	"""True if the user can manage at least one project (privileged, a lead, or an
	Admin member somewhere). Gates the global Users management page."""
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if roles & {"System Manager", "Projex Admin"}:
		return True
	if frappe.db.exists("Projex Project", {"lead": user}):
		return True
	return bool(frappe.db.exists("Projex Project Member", {"user": user, "role": "Admin"}))


def _can_manage_workspace(workspace):
	"""True for a privileged user or a workspace member with the Admin role."""
	roles = set(frappe.get_roles())
	if roles & {"System Manager", "Projex Admin"}:
		return True
	return any(
		m.role == "Admin"
		for m in frappe.get_all(
			"Projex Workspace Member",
			filters={"parent": workspace, "user": frappe.session.user},
			fields=["role"],
		)
	)


def _can_view_workspace(workspace):
	"""Read access to a workspace's members/teams: privileged users or any member."""
	roles = set(frappe.get_roles())
	if roles & {"System Manager", "Projex Admin"}:
		return True
	return bool(frappe.db.exists("Projex Workspace Member", {"parent": workspace, "user": frappe.session.user}))


def _would_orphan_workspace(workspace, user):
	"""True if removing/demoting `user` would leave the workspace with no Admin
	member — which would strand it (only a System Manager could recover it)."""
	admins = frappe.get_all(
		"Projex Workspace Member", filters={"parent": workspace, "role": "Admin"}, pluck="user"
	)
	return admins == [user]


MEMBER_ROLES = {"Admin", "Member", "Guest"}


def _can_manage_membership(parent_doctype, parent):
	"""Gate add/remove/role-change on a Project or Workspace member list."""
	if parent_doctype == "Projex Project":
		return _can_manage_project(parent)
	if parent_doctype == "Projex Workspace":
		return _can_manage_workspace(parent)
	frappe.throw("Invalid parent")


@frappe.whitelist()
def add_member(parent_doctype, parent, user, role="Member"):
	if parent_doctype not in ("Projex Project", "Projex Workspace"):
		frappe.throw("Invalid parent")
	if role not in MEMBER_ROLES:
		frappe.throw("Invalid role")
	if not _can_manage_membership(parent_doctype, parent):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc(parent_doctype, parent)
	child = "members"
	if any(m.user == user for m in doc.get(child)):
		return {"ok": True, "already": True}
	doc.append(child, {"user": user, "role": role})
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def update_member_role(parent_doctype, parent, user, role):
	"""Change an existing member's role (Admin/Member/Guest). A project member
	with the Admin role can manage the project (see _can_manage_project), so this
	is how a manager promotes a co-manager or demotes back to Member/Guest."""
	if parent_doctype not in ("Projex Project", "Projex Workspace"):
		frappe.throw("Invalid parent")
	if role not in MEMBER_ROLES:
		frappe.throw("Invalid role")
	if not _can_manage_membership(parent_doctype, parent):
		frappe.throw("Not permitted", frappe.PermissionError)
	if parent_doctype == "Projex Workspace" and role != "Admin" and _would_orphan_workspace(parent, user):
		frappe.throw("This is the workspace's only admin — promote someone else first.")
	doc = frappe.get_doc(parent_doctype, parent)
	row = next((m for m in doc.get("members") if m.user == user), None)
	if not row:
		frappe.throw("Not a member")
	row.role = role
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def set_all_access(user, enabled):
	"""Grant or revoke the global Projex Admin role (visibility into EVERY
	project). Restricted to System Manager / Projex Admin — a mere project
	admin must not be able to hand out all-project access."""
	if not (set(frappe.get_roles()) & {"System Manager", "Projex Admin"}):
		frappe.throw("Not permitted", frappe.PermissionError)
	enabled = frappe.parse_json(enabled) if isinstance(enabled, str) else enabled
	doc = frappe.get_doc("User", user)
	has_role = any(r.role == "Projex Admin" for r in doc.roles)
	if enabled and not has_role:
		doc.append("roles", {"role": "Projex Admin"})
		doc.save(ignore_permissions=True)
	elif not enabled and has_role:
		doc.set("roles", [r for r in doc.roles if r.role != "Projex Admin"])
		doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "all_access": bool(enabled)}


@frappe.whitelist()
def remove_member(parent_doctype, parent, user):
	if not _can_manage_membership(parent_doctype, parent):
		frappe.throw("Not permitted", frappe.PermissionError)
	if parent_doctype == "Projex Workspace" and _would_orphan_workspace(parent, user):
		frappe.throw("This is the workspace's only admin — promote someone else first.")
	doc = frappe.get_doc(parent_doctype, parent)
	doc.set("members", [m for m in doc.members if m.user != user])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def invite_user(email, project, full_name=None):
	"""Create a Frappe user (Projex Member) so teammates can be invited in-app.

	Gated: only someone who can manage the target project may invite (creating
	a Frappe User is sensitive). Rate-limited per inviter.
	"""
	if not _can_manage_project(project):
		frappe.throw("Only a project admin can invite people", frappe.PermissionError)

	email = (email or "").strip().lower()
	if not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
		frappe.throw("Enter a valid email")
	if frappe.db.exists("User", email):
		return {"name": email, "existing": True}

	# Throttle: cap new users created per inviter per hour.
	rkey = f"projex_invite:{frappe.session.user}"
	count = int(frappe.cache().get_value(rkey) or 0)
	if count >= 20:
		frappe.throw("Invite limit reached. Try again later.")
	frappe.cache().set_value(rkey, count + 1, expires_in_sec=3600)

	parts = (full_name or email.split("@")[0]).split(" ", 1)
	doc = frappe.get_doc({
		"doctype": "User", "email": email, "first_name": parts[0],
		"last_name": parts[1] if len(parts) > 1 else "",
		"send_welcome_email": 0, "user_type": "System User",
		"roles": [{"role": "Projex Member"}],
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "full_name": doc.full_name, "existing": False}


# Split a pasted blob of emails on commas, semicolons, whitespace or newlines.
import re as _re
def _parse_emails(blob):
	if isinstance(blob, (list, tuple)):
		raw = blob
	else:
		raw = _re.split(r"[\s,;]+", blob or "")
	seen, out = set(), []
	for e in raw:
		e = (e or "").strip().lower()
		if e and e not in seen and _re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e):
			seen.add(e)
			out.append(e)
	return out


@frappe.whitelist()
def bulk_invite(project, emails):
	"""Invite many people at once (paste or CSV). Creates a Frappe user where
	needed and adds each to the project. Returns a per-email summary."""
	if not _can_manage_project(project):
		frappe.throw("Only a project admin can invite people", frappe.PermissionError)
	parsed = _parse_emails(emails)
	if not parsed:
		frappe.throw("No valid email addresses found")
	existing_members = {
		m.user for m in frappe.get_all(
			"Projex Project Member", filters={"parent": project}, fields=["user"])
	}
	results = []
	for email in parsed:
		try:
			res = invite_user(email=email, project=project)  # gated + throttled
			user = res["name"]
			if user not in existing_members:
				add_member(parent_doctype="Projex Project", parent=project, user=user, role="Member")
				existing_members.add(user)
			results.append({"email": email, "status": "existing" if res.get("existing") else "invited"})
		except Exception as e:
			results.append({"email": email, "status": "error", "message": str(e)})
	return {"results": results}


@frappe.whitelist()
def create_invite_link(project, role="Member", expires_days=7, max_uses=0):
	"""Create a shareable join link for a project (manage-gated)."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	token = frappe.generate_hash(length=24)
	expires_on = None
	if int(expires_days or 0) > 0:
		expires_on = frappe.utils.add_to_date(frappe.utils.now_datetime(), days=int(expires_days))
	doc = frappe.get_doc({
		"doctype": "Projex Invite", "token": token, "project": project,
		"role": role or "Member", "expires_on": expires_on,
		"max_uses": int(max_uses or 0), "uses": 0, "disabled": 0,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"token": token, "url": f"{frappe.utils.get_url()}/projex?invite={token}", "name": doc.name}


@frappe.whitelist()
def list_invite_links(project):
	"""Active (non-disabled) invite links for a project (manage-gated)."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	rows = frappe.get_all(
		"Projex Invite", filters={"project": project, "disabled": 0},
		fields=["name", "token", "role", "expires_on", "max_uses", "uses"],
		order_by="creation desc",
	)
	for r in rows:
		r["url"] = f"{frappe.utils.get_url()}/projex?invite={r['token']}"
	return rows


@frappe.whitelist()
def revoke_invite_link(name):
	project = frappe.db.get_value("Projex Invite", name, "project")
	if not project or not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.db.set_value("Projex Invite", name, "disabled", 1)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def accept_invite(token):
	"""Add the logged-in user to the invite's project. Idempotent; validates
	expiry, disabled flag and use cap."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Please log in to accept this invite", frappe.PermissionError)
	name = frappe.db.exists("Projex Invite", {"token": token, "disabled": 0})
	if not name:
		frappe.throw("This invite link is invalid or has been revoked")
	inv = frappe.get_doc("Projex Invite", name)
	if inv.expires_on and frappe.utils.get_datetime(inv.expires_on) < frappe.utils.now_datetime():
		frappe.throw("This invite link has expired")
	if inv.max_uses and inv.uses >= inv.max_uses:
		frappe.throw("This invite link has reached its use limit")

	_ensure_member_role()
	already = frappe.db.exists("Projex Project Member", {"parent": inv.project, "user": user})
	if not already:
		proj = frappe.get_doc("Projex Project", inv.project)
		proj.append("members", {"user": user, "role": inv.role or "Member"})
		proj.save(ignore_permissions=True)
		inv.db_set("uses", (inv.uses or 0) + 1)
	frappe.db.commit()
	key = frappe.db.get_value("Projex Project", inv.project, "key")
	return {"project": inv.project, "key": key, "already_member": bool(already)}


@frappe.whitelist()
def create_label(project, label_name, color=None):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc({
		"doctype": "Projex Label", "label_name": label_name,
		"color": color or "var(--gray-500)", "project": project,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "label_name": doc.label_name, "color": doc.color}


@frappe.whitelist()
def delete_label(name):
	project = frappe.db.get_value("Projex Label", name, "project")
	if project and not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.delete_doc("Projex Label", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def create_cycle(project, cycle_name, start_date=None, end_date=None, state="Upcoming", goal=None):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc({
		"doctype": "Projex Cycle", "cycle_name": cycle_name, "project": project,
		"start_date": start_date or None, "end_date": end_date or None,
		"state": state, "goal": goal or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "cycle_name": doc.cycle_name}


@frappe.whitelist()
def update_cycle(name, fields):
	"""Edit a cycle/sprint (rename, dates, goal, or state: Upcoming/Active/Completed)."""
	import json
	if isinstance(fields, str):
		fields = json.loads(fields)
	project = frappe.db.get_value("Projex Cycle", name, "project")
	if project and not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc("Projex Cycle", name)
	for k in ("cycle_name", "start_date", "end_date", "state", "goal"):
		if k in fields:
			doc.set(k, fields[k] or None)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "state": doc.state}


@frappe.whitelist()
def start_sprint(cycle, start_date=None, end_date=None, goal=None):
	"""Begin a sprint: stamp dates/goal and flip the cycle to Active."""
	project = frappe.db.get_value("Projex Cycle", cycle, "project")
	if not project or not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc("Projex Cycle", cycle)
	if start_date:
		doc.start_date = start_date
	if end_date:
		doc.end_date = end_date
	if goal is not None:
		doc.goal = goal or None
	doc.state = "Active"
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "state": doc.state}


@frappe.whitelist()
def complete_sprint(cycle, carryover_to=None):
	"""Finish a sprint: mark it Completed and move every UNFINISHED issue (status
	category not completed/cancelled) to the backlog (carryover_to=None) or to
	another cycle. Returns how many were done vs carried over."""
	project = frappe.db.get_value("Projex Cycle", cycle, "project")
	if not project or not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if carryover_to:
		dest_project = frappe.db.get_value("Projex Cycle", carryover_to, "project")
		if dest_project != project:
			frappe.throw("Carryover target must be in the same project")

	cats = _status_categories()
	done_cats = {"completed", "cancelled"}
	issues = frappe.get_all(
		"Projex Issue", filters={"project": project, "cycle": cycle},
		fields=["name", "status"], limit=0,
	)
	done = carried = 0
	for it in issues:
		if cats.get(it.status) in done_cats:
			done += 1
		else:
			frappe.db.set_value("Projex Issue", it.name, "cycle", carryover_to or None)
			carried += 1

	frappe.db.set_value("Projex Cycle", cycle, "state", "Completed")
	frappe.db.commit()
	return {"ok": True, "done": done, "carried": carried, "carryover_to": carryover_to or None}


@frappe.whitelist()
def delete_cycle(name):
	project = frappe.db.get_value("Projex Cycle", name, "project")
	if project and not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.delete_doc("Projex Cycle", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def delete_project(project):
	"""Delete a project and everything scoped to it (admin only, irreversible).

	Removes dependent rows in dependency order via direct deletes (avoids
	link-validation errors), then the project doc itself.
	"""
	if not _can_manage_project(project):
		frappe.throw("Only a project admin can delete this project", frappe.PermissionError)
	if not frappe.db.exists("Projex Project", project):
		return {"ok": True}

	issues = frappe.get_all("Projex Issue", filters={"project": project}, pluck="name")
	if issues:
		frappe.db.delete("Projex Comment", {"issue": ["in", issues]})
		frappe.db.delete("Projex Issue Link", {"issue": ["in", issues]})
		frappe.db.delete("Projex Issue Link", {"target": ["in", issues]})
		frappe.db.delete("Projex Notification", {"issue": ["in", issues]})
		frappe.db.delete("Projex Issue Assignee", {"parent": ["in", issues]})
		frappe.db.delete("Projex Issue Label", {"parent": ["in", issues]})
		frappe.db.delete("Projex Issue", {"project": project})
	frappe.db.delete("Projex Activity", {"project": project})
	frappe.db.delete("Projex Favorite", {"project": project})
	frappe.db.delete("Projex View", {"project": project})
	frappe.db.delete("Projex Label", {"project": project})
	frappe.db.delete("Projex Cycle", {"project": project})
	frappe.db.delete("Projex Status", {"project": project})
	frappe.delete_doc("Projex Project", project, ignore_permissions=True, force=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def archive_project(project, archived=1):
	"""Toggle a project's archived flag (manage-gated). Archived projects are
	hidden from the main sidebar but kept intact (reversible)."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.db.set_value("Projex Project", project, "is_archived", 1 if int(archived) else 0)
	frappe.db.commit()
	return {"ok": True, "is_archived": 1 if int(archived) else 0}


@frappe.whitelist()
def duplicate_project(project, new_name, new_key, include_issues=1, reset_status=1):
	"""Clone a project as a template: meta, members, labels, cycles, and
	(optionally) its issues with their hierarchy. Comments/time/attachments are
	never copied. When reset_status, every cloned issue starts in the first
	unstarted status."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	new_key = (new_key or "").strip().upper()
	if not new_key:
		frappe.throw("A project key is required")
	if frappe.db.exists("Projex Project", new_key):
		frappe.throw(f"Project key '{new_key}' already in use")
	include_issues = int(include_issues)
	reset_status = int(reset_status)

	src = frappe.get_doc("Projex Project", project)
	new_proj = frappe.get_doc({
		"doctype": "Projex Project",
		"project_name": new_name or f"{src.project_name} copy",
		"key": new_key,
		"icon": src.icon, "color": src.color, "status": src.status,
		"workspace": src.workspace, "lead": frappe.session.user,
		"description": src.description,
		"members": [{"user": m.user, "role": m.role} for m in src.members],
	}).insert(ignore_permissions=True)

	# Per-project labels + cycles must be recreated and remapped.
	label_map = {}
	for lbl in frappe.get_all("Projex Label", filters={"project": project},
							  fields=["name", "label_name", "color"]):
		nl = frappe.get_doc({
			"doctype": "Projex Label", "project": new_proj.name,
			"label_name": lbl.label_name, "color": lbl.color,
		}).insert(ignore_permissions=True)
		label_map[lbl.name] = nl.name
	cycle_map = {}
	for cyc in frappe.get_all("Projex Cycle", filters={"project": project},
							  fields=["name", "cycle_name", "start_date", "end_date", "state"]):
		nc = frappe.get_doc({
			"doctype": "Projex Cycle", "project": new_proj.name, "cycle_name": cyc.cycle_name,
			"start_date": cyc.start_date, "end_date": cyc.end_date, "state": cyc.state,
		}).insert(ignore_permissions=True)
		cycle_map[cyc.name] = nc.name

	issues_copied = 0
	if include_issues:
		first_unstarted = frappe.db.get_value(
			"Projex Status", {"category": "unstarted", "project": ["in", ["", None]]},
			"name", order_by="position asc",
		)
		src_issues = frappe.get_all(
			"Projex Issue", filters={"project": project},
			fields=["name", "title", "description", "priority", "issue_type", "estimate",
					"due_date", "start_date", "status", "cycle", "parent_issue", "rank"],
			order_by="creation asc", limit_page_length=1000,
		)
		issue_map = {}
		# Pass 1: create issues (no parent links yet).
		for it in src_issues:
			doc = frappe.get_doc({
				"doctype": "Projex Issue", "project": new_proj.name, "workspace": src.workspace,
				"title": it.title, "description": it.description, "priority": it.priority,
				"issue_type": it.issue_type, "estimate": it.estimate,
				"due_date": it.due_date, "start_date": it.start_date,
				"status": first_unstarted if reset_status else it.status,
				"cycle": cycle_map.get(it.cycle), "rank": it.rank,
				"assignees": [
					{"user": a.user} for a in frappe.get_all(
						"Projex Issue Assignee", filters={"parent": it.name}, fields=["user"])
				],
				# Per-project labels are remapped to their clones; global labels
				# (project unset) are shared, so keep the original reference.
				"labels": [
					{"label": label_map.get(l.label, l.label)} for l in frappe.get_all(
						"Projex Issue Label", filters={"parent": it.name}, fields=["label"])
				],
			}).insert(ignore_permissions=True)
			issue_map[it.name] = doc.name
			issues_copied += 1
		# Pass 2: rewire parent_issue using the old→new map.
		for it in src_issues:
			if it.parent_issue and it.parent_issue in issue_map:
				frappe.db.set_value("Projex Issue", issue_map[it.name],
									"parent_issue", issue_map[it.parent_issue])

	frappe.db.commit()
	return {"name": new_proj.name, "key": new_proj.key, "issues_copied": issues_copied}


# --------------------------------------------------------------------------- #
# Bootstrap + board data (shell, list, board)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def bootstrap():
	"""Everything the app shell needs on load: projects, workspaces, people."""
	projects = frappe.get_list(
		"Projex Project",
		fields=["name", "project_name", "key", "icon", "color", "status", "workspace", "team", "lead", "is_archived"],
		order_by="project_name asc",
		ignore_permissions=False,
	)
	# Per-project manage flag (mirrors _can_manage_project): privileged users can
	# manage everything, otherwise a project's lead or an Admin member can. Drives
	# the sidebar row menu (archive/delete) so it only offers those where allowed.
	privileged_manage = bool(set(frappe.get_roles()) & {"System Manager", "Projex Admin"})
	admin_of = (
		set()
		if privileged_manage
		else set(
			frappe.get_all(
				"Projex Project Member",
				filters={"user": frappe.session.user, "role": "Admin"},
				pluck="parent",
			)
		)
	)
	for p in projects:
		p["can_manage"] = privileged_manage or p.get("lead") == frappe.session.user or p["name"] in admin_of
	workspaces = frappe.get_all(
		"Projex Workspace", fields=["name", "workspace_name", "icon"], order_by="workspace_name asc"
	)
	# Which workspaces the user may open in settings (privileged => all). Drives
	# the settings switcher so it only lists workspaces get_workspace_detail allows.
	privileged = bool(set(frappe.get_roles()) & {"System Manager", "Projex Admin"})
	my_ws = set(
		frappe.get_all("Projex Workspace Member", filters={"user": frappe.session.user}, pluck="parent")
	)
	for w in workspaces:
		w["is_member"] = privileged or w["name"] in my_ws
	teams = frappe.get_all(
		"Projex Team", fields=["name", "team_name", "workspace", "icon", "color"],
		order_by="team_name asc",
	)
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "user_image"],
		limit=200,
	)
	counts = {
		"inbox": frappe.db.count("Projex Notification", {"user": frappe.session.user, "is_read": 0}),
	}
	favorites = frappe.get_all(
		"Projex Favorite", filters={"user": frappe.session.user}, pluck="project"
	)
	return {
		"user": frappe.session.user,
		"projects": projects,
		"workspaces": workspaces,
		"teams": teams,
		"users": users,
		"counts": counts,
		"favorites": favorites,
		"can_manage_users": _can_manage_any(),
	}


@frappe.whitelist()
def get_statuses(project=None):
	"""Statuses for a project (project-scoped + global), ordered by position."""
	rows = frappe.get_all(
		"Projex Status",
		filters={"project": ["in", [project, "", None]]} if project else {},
		fields=["name", "status_name", "category", "color_theme", "dot_hollow", "position"],
		order_by="position asc",
	)
	return rows


ISSUE_PAGE_CAP = 500  # hard ceiling so List/Board never load unbounded


@frappe.whitelist()
def get_issues(project, include_subtasks=False, limit=None):
	"""Enriched, permission-checked issues for List/Board (no client N+1).

	Capped at ISSUE_PAGE_CAP; returns `truncated`/`total` so the UI can warn
	when a project has more issues than were loaded.
	"""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	filters = {"project": project}
	if not include_subtasks:
		filters["parent_issue"] = ["in", ["", None]]

	total = frappe.db.count("Projex Issue", filters)
	cap = min(int(limit or ISSUE_PAGE_CAP), ISSUE_PAGE_CAP)
	issues = frappe.get_all(
		"Projex Issue", filters=filters, fields=ISSUE_FIELDS, order_by="rank asc", limit=cap
	)
	if not issues:
		return {"issues": [], "statuses": get_statuses(project), "total": 0, "truncated": False}

	names = [i.name for i in issues]
	_enrich_issues(issues, names, project)
	return {
		"issues": issues,
		"statuses": get_statuses(project),
		"total": total,
		"truncated": total > len(issues),
	}


def _enrich_issues(issues, names, project):
	# Assignees (one query)
	assignee_rows = frappe.get_all(
		"Projex Issue Assignee", filters={"parent": ["in", names]},
		fields=["parent", "user"],
	)
	by_issue_assignees = {}
	for r in assignee_rows:
		by_issue_assignees.setdefault(r.parent, []).append(r.user)

	# Labels (one query) + label meta
	label_rows = frappe.get_all(
		"Projex Issue Label", filters={"parent": ["in", names]},
		fields=["parent", "label"],
	)
	label_meta = {
		l.name: l for l in frappe.get_all(
			"Projex Label", fields=["name", "label_name", "color"]
		)
	}
	by_issue_labels = {}
	for r in label_rows:
		meta = label_meta.get(r.label)
		if meta:
			by_issue_labels.setdefault(r.parent, []).append(
				{"label": r.label, "label_name": meta.label_name, "color": meta.color}
			)

	# Subtask counts (children grouped by parent + completed category)
	completed = {
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": ["in", ["completed", "cancelled"]]},
			fields=["name"],
		)
	}
	sub_rows = frappe.get_all(
		"Projex Issue", filters={"parent_issue": ["in", names]},
		fields=["parent_issue", "status"],
	)
	sub_total, sub_done = {}, {}
	for r in sub_rows:
		sub_total[r.parent_issue] = sub_total.get(r.parent_issue, 0) + 1
		if r.status in completed:
			sub_done[r.parent_issue] = sub_done.get(r.parent_issue, 0) + 1

	# Comment counts
	comment_rows = frappe.get_all(
		"Projex Comment", filters={"issue": ["in", names]}, fields=["issue"]
	)
	comment_count = {}
	for r in comment_rows:
		comment_count[r.issue] = comment_count.get(r.issue, 0) + 1

	for it in issues:
		it["assignees"] = by_issue_assignees.get(it.name, [])
		it["labels"] = by_issue_labels.get(it.name, [])
		it["sub_total"] = sub_total.get(it.name, 0)
		it["sub_done"] = sub_done.get(it.name, 0)
		it["comment_count"] = comment_count.get(it.name, 0)


@frappe.whitelist()
def get_issue(name):
	"""Full enriched issue for the Task Drawer: meta, people, subtasks, comments."""
	from projex.permissions import user_can_access_project
	project = frappe.db.get_value("Projex Issue", name, "project")
	if not project or not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	doc = frappe.get_doc("Projex Issue", name)
	status = frappe.db.get_value(
		"Projex Status", doc.status,
		["name", "status_name", "category", "color_theme", "dot_hollow"], as_dict=True,
	) if doc.status else None

	labels = []
	for row in doc.labels:
		meta = frappe.db.get_value("Projex Label", row.label, ["label_name", "color"], as_dict=True)
		if meta:
			labels.append({"label": row.label, **meta})

	subtasks = frappe.get_all(
		"Projex Issue",
		filters={"parent_issue": name},
		fields=["name", "issue_id", "title", "status"],
		order_by="rank asc",
	)
	completed = {
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": ["in", ["completed", "cancelled"]]}, fields=["name"]
		)
	}
	for s in subtasks:
		s["done"] = s["status"] in completed

	import json
	comments = frappe.get_all(
		"Projex Comment",
		filters={"issue": name},
		fields=["name", "content", "owner", "creation", "reactions"],
		order_by="creation asc",
	)
	for c in comments:
		c["author_name"] = frappe.db.get_value("User", c.owner, "full_name") or c.owner
		c["reactions"] = json.loads(c.get("reactions") or "{}")

	# linked work + attachments
	links = frappe.get_all(
		"Projex Issue Link", filters={"issue": name},
		fields=["name", "link_type", "target"],
	)
	for lk in links:
		lk["target_title"] = frappe.db.get_value("Projex Issue", lk.target, "title")
	attachments = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Projex Issue", "attached_to_name": name},
		fields=["name", "file_name", "file_url", "file_size"],
		order_by="creation desc",
	)

	return {
		"issue": {
			"name": doc.name, "issue_id": doc.issue_id, "title": doc.title,
			"description": doc.description, "project": doc.project, "status": doc.status,
			"priority": doc.priority, "issue_type": doc.issue_type,
			"due_date": str(doc.due_date) if doc.due_date else None,
			"start_date": str(doc.start_date) if doc.start_date else None,
			"estimate": doc.estimate, "cycle": doc.cycle, "reporter": doc.reporter,
			"recurrence": doc.recurrence or "None",
			"parent_issue": doc.parent_issue, "creation": str(doc.creation),
			"modified": str(doc.modified),
			"status_changed_on": str(doc.status_changed_on) if doc.status_changed_on else None,
			"reopen_count": doc.reopen_count or 0, "rework_count": doc.rework_count or 0,
			"assignees": [a.user for a in doc.assignees],
		},
		"status_meta": status,
		"labels": labels,
		"subtasks": subtasks,
		"checklist": [
			{"name": c.name, "title": c.title, "done": bool(c.done)} for c in doc.checklist
		],
		"comments": comments,
		"links": links,
		"attachments": attachments,
		"github_links": _github_links_safe(name),
	}


def _github_links_safe(issue):
	"""GitHub links for the drawer; never let the integration break issue load."""
	try:
		from projex import github

		return github._links(issue)
	except Exception:
		return []


# Fields a client is allowed to mutate via update_issue/create_issue.
# Everything else (issue_id, rank, reporter, owner, name, …) is off-limits to
# prevent mass-assignment; rank changes go through reorder_issue.
EDITABLE_ISSUE_FIELDS = {
	"title", "description", "status", "priority", "issue_type", "due_date", "start_date",
	"estimate", "cycle", "parent_issue", "assignees", "labels", "recurrence",
}


@frappe.whitelist()
def update_issue(name, fields):
	"""Load → set → save so controller hooks (realtime, notifications) fire.

	Only fields in EDITABLE_ISSUE_FIELDS are accepted; `assignees` and `labels`
	(lists of ids) rewrite their child tables.
	"""
	import json
	if isinstance(fields, str):
		fields = json.loads(fields)
	doc = frappe.get_doc("Projex Issue", name)  # respects has_permission
	for k, v in fields.items():
		if k not in EDITABLE_ISSUE_FIELDS:
			continue  # silently ignore disallowed fields
		if k == "assignees":
			doc.set("assignees", [{"user": u} for u in (v or [])])
		elif k == "labels":
			doc.set("labels", [{"label": lbl} for lbl in (v or [])])
		else:
			doc.set(k, v)
	doc.save()
	frappe.db.commit()
	return {"name": doc.name, "modified": str(doc.modified)}


@frappe.whitelist()
def bulk_update_issues(names, fields):
	"""Apply `fields` (same allowlist as update_issue) to many issues at once.

	Each issue is loaded→saved individually so controller hooks (realtime,
	activity) fire per issue. Returns the count updated.
	"""
	import json
	if isinstance(names, str):
		names = json.loads(names)
	if isinstance(fields, str):
		fields = json.loads(fields)
	clean = {k: v for k, v in fields.items() if k in EDITABLE_ISSUE_FIELDS}
	if not clean:
		frappe.throw("No editable fields supplied")
	updated = 0
	for name in names or []:
		doc = frappe.get_doc("Projex Issue", name)  # respects has_permission
		for k, v in clean.items():
			if k == "assignees":
				doc.set("assignees", [{"user": u} for u in (v or [])])
			elif k == "labels":
				doc.set("labels", [{"label": lbl} for lbl in (v or [])])
			else:
				doc.set(k, v)
		doc.save()
		updated += 1
	frappe.db.commit()
	return {"updated": updated}


@frappe.whitelist()
def bulk_delete_issues(names):
	"""Delete many issues at once.

	An issue accrues linked records — Activity, Comments, Notifications, Time
	Logs, Issue Links and subtasks — whose Link fields make Frappe's integrity
	check refuse a bare delete_doc (LinkExistsError). Clear those dependents
	first (in dependency order), detach any subtasks, then delete the issue via
	delete_doc so its on_trash/realtime still fires and child rows cascade.
	"""
	import json
	if isinstance(names, str):
		names = json.loads(names)
	names = names or []
	# Same gate delete_doc applied implicitly before — keep it explicit.
	for name in names:
		if not frappe.has_permission("Projex Issue", "delete", doc=name):
			frappe.throw(f"Not permitted to delete {name}", frappe.PermissionError)
	deleted = 0
	for name in names:
		frappe.db.delete("Projex Comment", {"issue": name})
		frappe.db.delete("Projex Issue Link", {"issue": name})
		frappe.db.delete("Projex Issue Link", {"target": name})
		frappe.db.delete("Projex Notification", {"issue": name})
		frappe.db.delete("Projex Time Log", {"issue": name})
		frappe.db.delete("Projex Activity", {"issue": name})
		frappe.db.set_value("Projex Issue", {"parent_issue": name}, "parent_issue", None)
		frappe.delete_doc("Projex Issue", name)  # fires on_trash (realtime); children cascade
		deleted += 1
	frappe.db.commit()
	return {"deleted": deleted}


@frappe.whitelist()
def set_checklist(issue, items):
	"""Replace an issue's checklist with `items` (list of {title, done}).

	Whole-table replace keeps the API tiny and atomic — the drawer sends the
	full list on every add/toggle/delete. Goes through load→save so the issue's
	controller hooks (realtime) fire.
	"""
	import json
	if isinstance(items, str):
		items = json.loads(items)
	doc = frappe.get_doc("Projex Issue", issue)  # respects has_permission
	doc.set("checklist", [
		{"title": (it.get("title") or "").strip(), "done": 1 if it.get("done") else 0}
		for it in (items or [])
		if (it.get("title") or "").strip()
	])
	doc.save()
	frappe.db.commit()
	return {
		"checklist": [
			{"name": c.name, "title": c.title, "done": bool(c.done)} for c in doc.checklist
		]
	}


@frappe.whitelist()
def create_issue(payload):
	"""Create an issue with optional assignees/labels (used by the create dialog)."""
	import json
	if isinstance(payload, str):
		payload = json.loads(payload)
	from projex.permissions import user_can_access_project
	project = payload.get("project")
	if not project or not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.new_doc("Projex Issue")
	doc.title = payload.get("title")
	doc.project = project
	for f in ("status", "priority", "issue_type", "due_date", "estimate", "cycle", "description", "parent_issue"):
		if payload.get(f):
			doc.set(f, payload[f])
	doc.set("assignees", [{"user": u} for u in payload.get("assignees", [])])
	doc.set("labels", [{"label": lbl} for lbl in payload.get("labels", [])])
	doc.insert()
	frappe.db.commit()
	return {"name": doc.name, "issue_id": doc.issue_id}


@frappe.whitelist()
def get_pickers(project):
	"""Options for editing controls: labels, cycles, members."""
	from projex.permissions import accessible_projects
	labels = frappe.get_all(
		"Projex Label",
		filters={"project": ["in", [project, "", None]]},
		fields=["name", "label_name", "color"],
		order_by="label_name asc",
	)
	cycles = frappe.get_all(
		"Projex Cycle", filters={"project": project},
		fields=["name", "cycle_name", "state", "start_date", "end_date", "goal"],
		order_by="start_date desc",
	)
	users = frappe.get_all(
		"User", filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "user_image"], limit=200,
	)
	return {"labels": labels, "cycles": cycles, "users": users, "can_manage": _can_manage_project(project)}


@frappe.whitelist()
def toggle_reaction(comment, emoji):
	"""Toggle the current user's reaction on a comment. Returns the new map."""
	import json
	doc = frappe.get_doc("Projex Comment", comment)
	data = json.loads(doc.reactions or "{}")
	users = set(data.get(emoji, []))
	user = frappe.session.user
	if user in users:
		users.discard(user)
	else:
		users.add(user)
	if users:
		data[emoji] = sorted(users)
	else:
		data.pop(emoji, None)
	doc.reactions = json.dumps(data)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return data


@frappe.whitelist()
def add_comment(issue, content):
	"""Post a comment (author = current user); fires comment realtime + notifications."""
	from projex.permissions import user_can_access_project
	project = frappe.db.get_value("Projex Issue", issue, "project")
	if not project or not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc({"doctype": "Projex Comment", "issue": issue, "content": content})
	doc.insert()
	frappe.db.commit()
	return {
		"name": doc.name, "content": doc.content, "owner": doc.owner,
		"author_name": frappe.db.get_value("User", doc.owner, "full_name") or doc.owner,
		"creation": str(doc.creation),
	}


# --------------------------------------------------------------------------- #
# Summary dashboard + reports (Jira-parity analytics)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_project_summary(project):
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	week_ago = add_days(nowdate(), -7)
	week_ahead = add_days(nowdate(), 7)
	completed_statuses = [
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": ["in", ["completed", "cancelled"]]}, fields=["name"]
		)
	]
	base = {"project": project, "parent_issue": ["in", ["", None]]}

	completed = frappe.db.count("Projex Issue", {
		**base, "status": ["in", completed_statuses or [""]], "modified": [">=", week_ago],
	}) if completed_statuses else 0
	updated = frappe.db.count("Projex Issue", {**base, "modified": [">=", week_ago]})
	created = frappe.db.count("Projex Issue", {**base, "creation": [">=", week_ago]})
	due_soon = frappe.db.count("Projex Issue", {
		**base, "due_date": ["between", [nowdate(), week_ahead]],
		"status": ["not in", completed_statuses or [""]],
	})

	# status donut
	statuses = frappe.get_all(
		"Projex Status",
		filters={"project": ["in", [project, "", None]]},
		fields=["name", "status_name", "color_theme"], order_by="position asc",
	)
	breakdown = []
	total = 0
	for s in statuses:
		n = frappe.db.count("Projex Issue", {**base, "status": s.name})
		if n:
			breakdown.append({"status_name": s.status_name, "color_theme": s.color_theme, "count": n})
			total += n

	return {
		"cards": {"completed": completed, "updated": updated, "created": created, "due_soon": due_soon},
		"status_breakdown": breakdown,
		"total": total,
		"activity": get_activity_digest(project, 6),
	}


@frappe.whitelist()
def get_gantt(project):
	"""Tasks formatted for frappe-gantt: id/name/start/end/progress/dependencies."""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	issues = frappe.get_all(
		"Projex Issue",
		filters={"project": project, "parent_issue": ["in", ["", None]]},
		fields=["name", "issue_id", "title", "start_date", "due_date", "creation", "status"],
		order_by="creation asc",
	)
	# progress by status category
	cats = {s.name: s.category for s in frappe.get_all("Projex Status", fields=["name", "category"])}
	progress_map = {"completed": 100, "cancelled": 100, "started": 50}

	# dependencies from issue links
	links = frappe.get_all(
		"Projex Issue Link",
		filters={"issue": ["in", [i.name for i in issues]]},
		fields=["issue", "link_type", "target"],
	)
	deps = {}
	for lk in links:
		# "A blocked by B"  -> A depends on B
		# "A blocks B"      -> B depends on A
		if lk.link_type == "blocked by":
			deps.setdefault(lk.issue, set()).add(lk.target)
		elif lk.link_type == "blocks":
			deps.setdefault(lk.target, set()).add(lk.issue)

	tasks = []
	for it in issues:
		start = str(it.start_date) if it.start_date else str(it.creation)[:10]
		end = str(it.due_date) if it.due_date else start
		if end < start:
			end = start
		tasks.append({
			"id": it.name,
			"name": f"{it.issue_id}  {it.title}",
			"start": start,
			"end": end,
			"progress": progress_map.get(cats.get(it.status), 0),
			"dependencies": ", ".join(sorted(deps.get(it.name, []))),
		})
	return tasks


@frappe.whitelist()
def get_activity(project, limit=20):
	rows = frappe.get_all(
		"Projex Activity",
		filters={"project": project},
		fields=["name", "issue", "actor", "action", "detail", "creation"],
		order_by="creation desc",
		limit=int(limit),
	)
	for r in rows:
		r["actor_name"] = frappe.db.get_value("User", r.actor, "full_name") or r.actor
		r["issue_id"] = frappe.db.get_value("Projex Issue", r.issue, "issue_id") if r.issue else None
	return rows


# Bulk actions that arrive in bursts (a batch import or a recurring-task sweep)
# and drown the signal ones. On the Overview digest they collapse into a single
# count row instead of one line each; the full log keeps them separate.
_DIGEST_COLLAPSE = {"created", "recurred"}


def get_activity_digest(project, limit=5):
	"""Curated feed for the Overview panel. A consecutive run of the same actor
	doing the same bulk action (e.g. six 'created' rows in a row) collapses into
	one 'created 6 tasks' entry, so status changes, comments and assignments
	aren't buried under task-creation spam. The full chronological log lives on
	the Activity tab via get_activity()."""
	rows = frappe.get_all(
		"Projex Activity",
		filters={"project": project},
		fields=["name", "issue", "actor", "action", "detail", "creation"],
		order_by="creation desc",
		limit=60,
	)
	digest, i, n = [], 0, len(rows)
	while i < n and len(digest) < int(limit):
		r = rows[i]
		run = 1
		if r.action in _DIGEST_COLLAPSE:
			while i + run < n and rows[i + run].actor == r.actor and rows[i + run].action == r.action:
				run += 1
		if run > 1:
			digest.append({
				"name": r.name, "issue": None, "actor": r.actor, "action": r.action,
				"detail": None, "creation": r.creation, "count": run,
			})
		else:
			digest.append({**r, "count": 1})
		i += run

	for d in digest:
		d["actor_name"] = frappe.db.get_value("User", d["actor"], "full_name") or d["actor"]
		d["issue_id"] = frappe.db.get_value("Projex Issue", d["issue"], "issue_id") if d["issue"] else None
	return digest


@frappe.whitelist()
def get_project_reports(project):
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	completed_statuses = [
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": "completed"}, fields=["name"]
		)
	]
	base = {"project": project, "parent_issue": ["in", ["", None]]}

	# status distribution
	statuses = frappe.get_all(
		"Projex Status", filters={"project": ["in", [project, "", None]]},
		fields=["name", "status_name", "color_theme"], order_by="position asc",
	)
	distribution = []
	for s in statuses:
		n = frappe.db.count("Projex Issue", {**base, "status": s.name})
		distribution.append({"label": s.status_name, "color_theme": s.color_theme, "count": n})

	# velocity: completed estimate (points) per cycle
	velocity = []
	for c in frappe.get_all("Projex Cycle", filters={"project": project},
							fields=["name", "cycle_name"], order_by="start_date asc"):
		pts = frappe.db.sql(
			"""SELECT COALESCE(SUM(estimate),0) FROM `tabProjex Issue`
			   WHERE project=%s AND cycle=%s AND status IN %s""",
			(project, c.name, tuple(completed_statuses or [""])),
		)[0][0]
		count = frappe.db.count("Projex Issue", {"project": project, "cycle": c.name})
		velocity.append({"cycle": c.cycle_name, "points": int(pts or 0), "issues": count})

	# throughput: issues completed per week (last 6 weeks)
	throughput = []
	for w in range(5, -1, -1):
		start = add_days(nowdate(), -7 * (w + 1))
		end = add_days(nowdate(), -7 * w)
		n = frappe.db.count("Projex Issue", {
			**base, "status": ["in", completed_statuses or [""]],
			"modified": ["between", [start, end]],
		}) if completed_statuses else 0
		throughput.append({"week": end, "count": n})

	# avg cycle time (days) for completed issues
	done = frappe.get_all("Projex Issue", filters={
		**base, "status": ["in", completed_statuses or [""]]},
		fields=["creation", "modified"], limit=200)
	days = [(getdate(d.modified) - getdate(d.creation)).days for d in done]
	avg_cycle = round(sum(days) / len(days), 1) if days else 0

	# aging: how long OPEN tasks have sat in their current status (time-in-status)
	open_cats = ["backlog", "unstarted", "started"]
	open_statuses = [
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": ["in", open_cats]}, fields=["name"]
		)
	]
	aging = {"le3": 0, "d4_7": 0, "d8_14": 0, "gt14": 0}
	open_rows = frappe.get_all("Projex Issue", filters={
		**base, "status": ["in", open_statuses or [""]]},
		fields=["status_changed_on", "modified"], limit=0) if open_statuses else []
	now = now_datetime()
	for r in open_rows:
		ref = r.status_changed_on or r.modified
		d = (now - ref).days if ref else 0
		if d <= 3:
			aging["le3"] += 1
		elif d <= 7:
			aging["d4_7"] += 1
		elif d <= 14:
			aging["d8_14"] += 1
		else:
			aging["gt14"] += 1

	# rework: how often tasks bounced backward (reopened / rejected)
	counts = frappe.get_all(
		"Projex Issue", filters=base, fields=["reopen_count", "rework_count"], limit=0,
	)
	total = len(counts)
	total_reopens = sum(c.reopen_count or 0 for c in counts)
	total_rejections = sum(c.rework_count or 0 for c in counts)
	reworked = sum(1 for c in counts if (c.reopen_count or 0) or (c.rework_count or 0))
	rework = {
		"reworked_tasks": reworked,
		"total_reopens": total_reopens,
		"total_rejections": total_rejections,
		"rework_rate": round(reworked / total * 100) if total else 0,
	}

	return {
		"distribution": distribution,
		"velocity": velocity,
		"throughput": throughput,
		"avg_cycle_time": avg_cycle,
		"total_completed": len(done),
		"aging": aging,
		"rework": rework,
	}


@frappe.whitelist()
def get_burndown(project, cycle=None):
	"""Sprint burndown: ideal vs. actual remaining story points per day.

	Picks the given cycle, else the Active one, else the most recent dated cycle.
	`remaining` is filled up to today only; future days are null so the actual
	line stops at "now".
	"""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	if not cycle:
		active = frappe.get_all(
			"Projex Cycle", filters={"project": project, "state": "Active"},
			fields=["name"], limit=1,
		)
		if active:
			cycle = active[0].name
		else:
			recent = frappe.get_all(
				"Projex Cycle", filters={"project": project, "start_date": ["is", "set"]},
				fields=["name"], order_by="start_date desc", limit=1,
			)
			cycle = recent[0].name if recent else None

	if not cycle:
		return {"cycle": None, "series": [], "total_points": 0}

	c = frappe.db.get_value(
		"Projex Cycle", cycle, ["name", "cycle_name", "start_date", "end_date"], as_dict=True
	)
	if not c or not c.start_date or not c.end_date:
		return {"cycle": cycle, "cycle_name": c.cycle_name if c else None, "series": [], "total_points": 0,
				"needs_dates": True}

	completed_statuses = {
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": ["in", ["completed", "cancelled"]]}, fields=["name"]
		)
	}
	issues = frappe.get_all(
		"Projex Issue", filters={"project": project, "cycle": cycle},
		fields=["name", "estimate", "status", "modified"],
	)
	total = sum((i.estimate or 0) for i in issues)

	# points completed on each day (approx: status is done as of `modified`)
	done_on = {}
	for i in issues:
		if i.status in completed_statuses:
			d = getdate(i.modified)
			done_on[d] = done_on.get(d, 0) + (i.estimate or 0)

	start, end = getdate(c.start_date), getdate(c.end_date)
	span = (end - start).days
	today = getdate(nowdate())
	series, burned = [], 0
	for n in range(span + 1):
		day = add_days(start, n)
		day_d = getdate(day)
		ideal = round(total * (1 - n / span), 2) if span else 0
		burned += done_on.get(day_d, 0)
		remaining = (total - burned) if day_d <= today else None
		series.append({"date": str(day), "ideal": ideal, "remaining": remaining})

	return {
		"cycle": cycle, "cycle_name": c.cycle_name,
		"start_date": str(start), "end_date": str(end),
		"total_points": total, "series": series,
	}


# --------------------------------------------------------------------------- #
# Issues dashboard + sprint review
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_issues_dashboard(project):
	"""Aggregate issue counts for the project issues dashboard: by type, status
	category, priority, plus open-bug spotlight and per-assignee load."""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	base = {"project": project, "parent_issue": ["in", ["", None]]}
	cats = {s.name: s.category for s in frappe.get_all("Projex Status", fields=["name", "category"])}
	open_cats = {"backlog", "unstarted", "started"}

	issues = frappe.get_all(
		"Projex Issue", filters=base,
		fields=["name", "issue_id", "title", "issue_type", "status", "priority", "due_date", "estimate"],
	)
	est_of = {i.name: (i.estimate or 0) for i in issues}
	by_type, by_priority, by_cat = {}, {}, {}
	for it in issues:
		t = it.issue_type or "Task"
		by_type[t] = by_type.get(t, 0) + 1
		by_priority[it.priority or "None"] = by_priority.get(it.priority or "None", 0) + 1
		cat = cats.get(it.status) or "unstarted"
		by_cat[cat] = by_cat.get(cat, 0) + 1

	# open bugs spotlight
	open_bugs = [
		{"name": it.name, "issue_id": it.issue_id, "title": it.title, "priority": it.priority,
		 "due_date": str(it.due_date) if it.due_date else None}
		for it in issues
		if (it.issue_type == "Bug") and (cats.get(it.status) in open_cats)
	]

	# per-assignee open load (tasks + story points), across ALL project members so
	# under-loaded people surface too — then flag over/under-allocation vs the team avg.
	assignee_rows = frappe.get_all(
		"Projex Issue Assignee", filters={"parent": ["in", [i.name for i in issues] or [""]]},
		fields=["parent", "user"],
	)
	open_names = {i.name for i in issues if cats.get(i.status) in open_cats}
	tasks, points = {}, {}
	for r in assignee_rows:
		if r.parent in open_names:
			tasks[r.user] = tasks.get(r.user, 0) + 1
			points[r.user] = points.get(r.user, 0) + est_of.get(r.parent, 0)
	members = frappe.get_all("Projex Project Member", filters={"parent": project}, pluck="user")
	people = list(dict.fromkeys(list(members) + list(tasks)))  # members ∪ anyone with load
	people = [u for u in people if u != "Administrator"] or people
	loads = [points.get(u, 0) for u in people]
	avg = (sum(loads) / len(loads)) if loads else 0

	def _level(pts, tk):
		if tk == 0:
			return "under"
		if avg and pts > max(8, avg * 1.4):
			return "over"
		if avg and pts < avg * 0.4:
			return "under"
		return "ok"

	workload = sorted(
		[{
			"user": u,
			"name_full": frappe.db.get_value("User", u, "full_name") or u,
			"open": tasks.get(u, 0), "points": points.get(u, 0),
			"level": _level(points.get(u, 0), tasks.get(u, 0)),
		} for u in people],
		key=lambda x: -x["points"],
	)
	max_points = max([w["points"] for w in workload], default=0)

	PRIORITY_ORDER = ["Urgent", "High", "Medium", "Low", "None"]
	return {
		"total": len(issues),
		"by_type": [{"label": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: -x[1])],
		"by_priority": [{"label": p, "count": by_priority.get(p, 0)} for p in PRIORITY_ORDER],
		"by_category": by_cat,
		"open_bugs": sorted(open_bugs, key=lambda b: PRIORITY_ORDER.index(b["priority"]) if b["priority"] in PRIORITY_ORDER else 9),
		"workload": workload,
		"workload_max_points": max_points,
		"workload_avg_points": round(avg, 1),
	}


@frappe.whitelist()
def get_sprint_review(project, cycle=None):
	"""Sprint review: scope, completed vs. carryover, and points for a cycle."""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	cycles = frappe.get_all(
		"Projex Cycle", filters={"project": project},
		fields=["name", "cycle_name", "state", "start_date", "end_date"], order_by="start_date desc",
	)
	if not cycle:
		active = next((c for c in cycles if c.state == "Active"), None)
		cycle = (active or (cycles[0] if cycles else None))
		cycle = cycle.name if cycle else None
	if not cycle:
		return {"cycle": None, "cycles": cycles}

	c = next((x for x in cycles if x.name == cycle), None)
	completed_statuses = {
		s.name for s in frappe.get_all(
			"Projex Status", filters={"category": ["in", ["completed", "cancelled"]]}, fields=["name"]
		)
	}
	issues = frappe.get_all(
		"Projex Issue", filters={"project": project, "cycle": cycle},
		fields=["name", "issue_id", "title", "status", "priority", "issue_type", "estimate"],
		order_by="rank asc",
	)
	for it in issues:
		it["done"] = it.status in completed_statuses
	done = [i for i in issues if i["done"]]
	carry = [i for i in issues if not i["done"]]
	pts = lambda rows: sum((r.estimate or 0) for r in rows)
	return {
		"cycle": cycle,
		"cycle_name": c.cycle_name if c else None,
		"state": c.state if c else None,
		"start_date": str(c.start_date) if c and c.start_date else None,
		"end_date": str(c.end_date) if c and c.end_date else None,
		"cycles": cycles,
		"total_issues": len(issues),
		"done_issues": len(done),
		"total_points": pts(issues),
		"done_points": pts(done),
		"completed": done,
		"carryover": carry,
	}


# --------------------------------------------------------------------------- #
# Project docs (PRD / BRD / Standup MOM / Change requests / notes)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_docs(project, doc_type=None):
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	filters = {"project": project}
	if doc_type:
		filters["doc_type"] = doc_type
	rows = frappe.get_all(
		"Projex Doc", filters=filters,
		fields=["name", "title", "doc_type", "doc_date", "owner", "modified"],
		order_by="modified desc",
	)
	for r in rows:
		r["owner_name"] = frappe.db.get_value("User", r.owner, "full_name") or r.owner
	return rows


@frappe.whitelist()
def get_doc_detail(name):
	doc = frappe.get_doc("Projex Doc", name)
	from projex.permissions import user_can_access_project
	if not user_can_access_project(doc.project):
		frappe.throw("Not permitted", frappe.PermissionError)
	return {
		"name": doc.name, "title": doc.title, "project": doc.project,
		"doc_type": doc.doc_type, "doc_date": str(doc.doc_date) if doc.doc_date else None,
		"content": doc.content, "owner": doc.owner,
		"owner_name": frappe.db.get_value("User", doc.owner, "full_name") or doc.owner,
		"modified": str(doc.modified),
	}


@frappe.whitelist()
def create_doc(project, title, doc_type="Note", content=None, doc_date=None):
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc({
		"doctype": "Projex Doc", "project": project, "title": title,
		"doc_type": doc_type, "content": content, "doc_date": doc_date or None,
	}).insert()
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def update_doc(name, fields):
	import json
	if isinstance(fields, str):
		fields = json.loads(fields)
	doc = frappe.get_doc("Projex Doc", name)
	for k in ("title", "doc_type", "content", "doc_date"):
		if k in fields:
			doc.set(k, fields[k] or None)
	doc.save()
	frappe.db.commit()
	return {"name": doc.name, "modified": str(doc.modified)}


@frappe.whitelist()
def delete_doc_entry(name):
	project = frappe.db.get_value("Projex Doc", name, "project")
	if project and not _can_manage_project(project):
		# allow the author to delete their own doc
		if frappe.db.get_value("Projex Doc", name, "owner") != frappe.session.user:
			frappe.throw("Not permitted", frappe.PermissionError)
	frappe.delete_doc("Projex Doc", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Favorites / saved views / attachments / issue links
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def toggle_favorite(project):
	user = frappe.session.user
	existing = frappe.db.get_value("Projex Favorite", {"user": user, "project": project})
	if existing:
		frappe.delete_doc("Projex Favorite", existing, ignore_permissions=True)
		frappe.db.commit()
		return {"favorite": False}
	frappe.get_doc({"doctype": "Projex Favorite", "user": user, "project": project}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"favorite": True}


ATTACH_MAX_BYTES = 25 * 1024 * 1024  # 25 MB
ATTACH_BLOCKED_EXT = {
	".exe", ".sh", ".bat", ".cmd", ".com", ".scr", ".js", ".mjs", ".jar",
	".msi", ".dll", ".app", ".vbs", ".ps1",
}


def validate_attachment(doc, method=None):
	"""doc_events hook on File: enforce size + block dangerous types for issues."""
	if doc.attached_to_doctype != "Projex Issue":
		return
	if doc.file_size and doc.file_size > ATTACH_MAX_BYTES:
		frappe.throw("Attachment exceeds the 25 MB limit.")
	import os
	ext = os.path.splitext(doc.file_name or "")[1].lower()
	if ext in ATTACH_BLOCKED_EXT:
		frappe.throw(f"File type '{ext}' is not allowed.")


@frappe.whitelist()
def get_attachments(issue):
	return frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Projex Issue", "attached_to_name": issue},
		fields=["name", "file_name", "file_url", "file_size", "is_private"],
		order_by="creation desc",
	)


@frappe.whitelist()
def delete_attachment(name):
	frappe.delete_doc("File", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def add_issue_link(issue, link_type, target):
	if issue == target:
		frappe.throw("An issue can't link to itself")
	doc = frappe.get_doc({
		"doctype": "Projex Issue Link", "issue": issue, "link_type": link_type, "target": target,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def remove_issue_link(name):
	frappe.delete_doc("Projex Issue Link", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def save_view(project, view_name, view_type, config, is_shared=0):
	existing = frappe.db.get_value(
		"Projex View", {"project": project, "user": frappe.session.user, "view_name": view_name}
	)
	if existing:
		doc = frappe.get_doc("Projex View", existing)
		doc.config = config
		doc.view_type = view_type
		doc.save(ignore_permissions=True)
	else:
		doc = frappe.get_doc({
			"doctype": "Projex View", "project": project, "user": frappe.session.user,
			"view_name": view_name, "view_type": view_type, "config": config, "is_shared": is_shared,
		}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}


@frappe.whitelist()
def get_views(project):
	user = frappe.session.user
	return frappe.get_all(
		"Projex View",
		filters=[["project", "=", project], ["user", "=", user]],
		fields=["name", "view_name", "view_type", "config", "is_shared"],
		order_by="view_name asc",
	)


@frappe.whitelist()
def delete_view(name):
	frappe.delete_doc("Projex View", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Personal queues / aggregates
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_my_issues():
	"""Issues assigned to the current user, grouped for the 'My tasks' view."""
	user = frappe.session.user
	assigned = frappe.get_all(
		"Projex Issue Assignee", filters={"user": user}, fields=["parent"], pluck="parent"
	)
	if not assigned:
		return {"overdue": [], "today": [], "week": [], "later": [], "done": []}

	issues = frappe.get_all(
		"Projex Issue",
		filters={"name": ["in", assigned]},
		fields=ISSUE_FIELDS,
		order_by="due_date asc",
	)
	_attach_status_meta(issues)

	today = getdate(nowdate())
	week_end = add_days(today, 7)
	groups = {"overdue": [], "today": [], "week": [], "later": [], "done": []}
	for it in issues:
		due = getdate(it["due_date"]) if it.get("due_date") else None
		if it.get("_status_category") in ("completed", "cancelled"):
			groups["done"].append(it)
		elif due and due < today:
			groups["overdue"].append(it)
		elif due and due == today:
			groups["today"].append(it)
		elif due and due <= week_end:
			groups["week"].append(it)
		else:
			groups["later"].append(it)
	return groups


@frappe.whitelist()
def get_inbox(filter=None):
	"""Notifications for the current user. filter: all|unread|mentions|assigned."""
	filters = {"user": frappe.session.user}
	if filter == "unread":
		filters["is_read"] = 0
	elif filter == "mentions":
		filters["notification_type"] = "mention"
	elif filter == "assigned":
		filters["notification_type"] = "assigned"
	return frappe.get_all(
		"Projex Notification",
		filters=filters,
		fields=["name", "notification_type", "actor", "issue", "snippet", "is_read", "creation"],
		order_by="creation desc",
		limit=100,
	)


@frappe.whitelist()
def mark_notification_read(name=None, all=False):
	if all:
		frappe.db.set_value(
			"Projex Notification", {"user": frappe.session.user, "is_read": 0}, "is_read", 1
		)
		return {"ok": True}
	notif = frappe.get_doc("Projex Notification", name)
	if notif.user != frappe.session.user:
		frappe.throw("Not your notification", frappe.PermissionError)
	notif.is_read = 1
	notif.save(ignore_permissions=True)
	return {"ok": True}


@frappe.whitelist()
def get_notification_prefs():
	"""Current user's email notification preferences (all-on by default)."""
	from projex.notifications import get_preferences
	return get_preferences(frappe.session.user)


@frappe.whitelist()
def set_notification_prefs(fields):
	"""Upsert the current user's email notification preferences."""
	import json
	from projex.notifications import _DEFAULT_PREFS
	if isinstance(fields, str):
		fields = json.loads(fields)
	user = frappe.session.user
	name = frappe.db.exists("Projex Notification Preference", {"user": user})
	doc = (
		frappe.get_doc("Projex Notification Preference", name)
		if name
		else frappe.get_doc({"doctype": "Projex Notification Preference", "user": user})
	)
	for k in _DEFAULT_PREFS:
		if k in fields:
			doc.set(k, 1 if fields[k] else 0)
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	from projex.notifications import get_preferences
	return get_preferences(user)


@frappe.whitelist()
def get_roadmap(workspace=None):
	"""Roadmap bars: one per project with a coarse quarter position from cycles."""
	filters = {}
	if workspace:
		filters["workspace"] = workspace
	allowed = accessible_projects()
	if allowed is not None:
		if not allowed:
			return []
		filters["name"] = ["in", list(allowed)]

	projects = frappe.get_all(
		"Projex Project", filters=filters, fields=["name", "project_name", "icon", "color", "status"]
	)
	bars = []
	for p in projects:
		cyc = frappe.get_all(
			"Projex Cycle",
			filters={"project": p.name},
			fields=["start_date", "end_date"],
			order_by="start_date asc",
		)
		start = min((c.start_date for c in cyc if c.start_date), default=None)
		end = max((c.end_date for c in cyc if c.end_date), default=None)
		bars.append({
			"project": p.name, "label": p.project_name, "icon": p.icon,
			"color": p.color, "status": p.status,
			"start_date": str(start) if start else None,
			"end_date": str(end) if end else None,
		})
	return bars


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def reorder_issue(issue, before=None, after=None):
	"""Recompute a midpoint rank between two neighbours (lexo-rank style)."""
	def rank_of(name):
		return frappe.db.get_value("Projex Issue", name, "rank") if name else None

	lo = rank_of(after)
	hi = rank_of(before)
	new_rank = _midpoint(lo, hi)
	frappe.db.set_value("Projex Issue", issue, "rank", new_rank)
	frappe.db.commit()
	return {"issue": issue, "rank": new_rank}


def _midpoint(lo, hi):
	"""Numeric midpoint of two zero-padded numeric rank strings."""
	lo_n = int(lo) if lo else 0
	hi_n = int(hi) if hi else lo_n + 2000
	if hi_n - lo_n <= 1:
		hi_n = lo_n + 2000  # rebalance gap
	return str((lo_n + hi_n) // 2).zfill(12)


@frappe.whitelist()
def set_presence(issue):
	"""Announce that the current user is viewing an issue (ephemeral)."""
	project = frappe.db.get_value("Projex Issue", issue, "project")
	if not project:
		return {"ok": False}
	cache_key = f"projex:presence:{issue}"
	viewers = frappe.cache().hget(cache_key, "users") or {}
	viewers[frappe.session.user] = frappe.utils.now()
	frappe.cache().hset(cache_key, "users", viewers)
	frappe.cache().expire(cache_key, 60)
	emit_presence(project, issue, list(viewers.keys()))
	return {"ok": True, "users": list(viewers.keys())}


# --------------------------------------------------------------------------- #
# ERPNext integration (the wedge) — degrades gracefully when erpnext is absent
# --------------------------------------------------------------------------- #
def _erpnext_installed():
	return "erpnext" in frappe.get_installed_apps()


@frappe.whitelist()
def integration_status():
	"""Tell the SPA which integrations are live so it can hide unavailable UI."""
	from projex import github

	return {
		"erpnext": _erpnext_installed(),
		"timesheet": _erpnext_installed(),
		"ai": ai.is_ai_enabled(),
		"github": github.is_enabled(),
	}


@frappe.whitelist()
def log_time(issue, hours, activity_type=None, note=None, spent_on=None, is_billable=1):
	"""Create an ERPNext Timesheet entry linked to a Projex issue.

	Wedge integration #1. No-ops cleanly (raises a friendly error) when ERPNext
	is not installed. Reuses the issue's project ERPNext link when present.
	Callable from the Timesheets tab (pick a task) or a task drawer.
	"""
	if not _erpnext_installed():
		frappe.throw("ERPNext is not installed; time logging is unavailable.")
	from projex.permissions import user_can_access_project

	issue_doc = frappe.get_doc("Projex Issue", issue)
	if not user_can_access_project(issue_doc.project):
		frappe.throw("Not permitted", frappe.PermissionError)
	project = frappe.get_doc("Projex Project", issue_doc.project)
	company = frappe.defaults.get_global_default("company")

	from_time = frappe.utils.now_datetime()
	if spent_on:
		# keep the wall-clock time so multiple same-day logs don't collide
		from_time = frappe.utils.get_datetime(f"{spent_on} {from_time.strftime('%H:%M:%S')}")

	is_billable = frappe.parse_json(is_billable) if isinstance(is_billable, str) else is_billable

	erpnext_project = project.get("erpnext_project")
	ts = frappe.new_doc("Timesheet")
	if company:
		ts.company = company
	ts.parent_project = erpnext_project or None
	ts.append("time_logs", {
		"activity_type": activity_type,
		"hours": float(hours),
		"project": erpnext_project or None,
		"is_billable": 1 if is_billable else 0,
		"billing_hours": float(hours) if is_billable else 0,
		"description": f"[{issue_doc.issue_id}] {issue_doc.title}" + (f"\n{note}" if note else ""),
		"from_time": from_time,
	})
	ts.flags.ignore_permissions = False
	ts.insert()
	return {"ok": True, "timesheet": ts.name}


@frappe.whitelist()
def get_activity_types():
	"""ERPNext Activity Types for the log-time dialog (empty if not installed)."""
	if not _erpnext_installed():
		return []
	return frappe.get_all("Activity Type", fields=["name"], limit=50, pluck="name")


@frappe.whitelist()
def get_issue_time_logs(issue):
	"""Read-only: timesheet detail rows referencing this issue + billed status."""
	if not _erpnext_installed():
		return []
	issue_doc = frappe.db.get_value("Projex Issue", issue, ["issue_id"], as_dict=True)
	if not issue_doc:
		return []
	rows = frappe.get_all(
		"Timesheet Detail",
		filters={"description": ["like", f"%[{issue_doc.issue_id}]%"]},
		fields=["parent", "hours", "is_billable", "sales_invoice", "activity_type"],
		limit=50,
	)
	for r in rows:
		r["billed"] = bool(r.get("sales_invoice"))
	return rows


@frappe.whitelist()
def set_project_links(project, erpnext_customer=None, erpnext_project=None):
	"""Set the optional ERPNext links on a Projex Project (project settings UI)."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if not _erpnext_installed():
		frappe.throw("ERPNext is not installed.")
	doc = frappe.get_doc("Projex Project", project)
	doc.db_set("erpnext_customer", erpnext_customer or None)
	doc.db_set("erpnext_project", erpnext_project or None)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def erpnext_link_options(project):
	"""ERPNext Projects + Customers to populate the link pickers in settings."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if not _erpnext_installed():
		return {"erpnext": False, "projects": [], "customers": []}
	projects = [
		{"value": p.name, "label": p.project_name or p.name}
		for p in frappe.get_all("Project", fields=["name", "project_name"], order_by="modified desc", limit=200)
	]
	customers = [
		{"value": c.name, "label": c.customer_name or c.name}
		for c in frappe.get_all("Customer", fields=["name", "customer_name"], order_by="modified desc", limit=200)
	]
	return {"erpnext": True, "projects": projects, "customers": customers}


# --------------------------------------------------------------------------- #
# Timesheets (native time analytics + ERPNext logged time) + project Finance
# --------------------------------------------------------------------------- #
def _company_currency():
	company = frappe.defaults.get_global_default("company")
	if company:
		cur = frappe.db.get_value("Company", company, "default_currency")
		if cur:
			return cur
	return frappe.db.get_default("currency") or "USD"


def _erpnext_project(project):
	if not _erpnext_installed():
		return None
	return frappe.db.get_value("Projex Project", project, "erpnext_project")


def _time_analytics(project):
	"""Native, ERPNext-free time analytics derived from status history:
	  - per-status average time a task sits before moving on,
	  - average lead time (created -> completed) and cycle time (started -> completed).
	Reconstructed from Projex Activity 'changed status' rows + issue.creation."""
	statuses = frappe.get_all(
		"Projex Status", fields=["name", "status_name", "category", "position"]
	)
	cat_by_name = {s.status_name: s.category for s in statuses}
	DAY = 86400.0

	issues = frappe.get_all(
		"Projex Issue", filters={"project": project},
		fields=["name", "creation"], limit=0,
	)
	if not issues:
		return {"per_status": [], "avg_lead_days": 0, "avg_cycle_days": 0, "completed": 0}
	created = {i.name: i.creation for i in issues}
	names = list(created)

	acts = frappe.get_all(
		"Projex Activity",
		filters={"project": project, "issue": ["in", names], "action": "changed status"},
		fields=["issue", "detail", "creation"],
		order_by="issue asc, creation asc", limit=0,
	)
	# group changes per issue: [(time, label, category)]
	changes = {}
	for a in acts:
		label = (a.detail or "").lstrip("→").strip()
		changes.setdefault(a.issue, []).append((a.creation, label, cat_by_name.get(label)))

	status_total, status_count = {}, {}
	lead, cycle = [], []
	completed = 0
	done_cats = {"completed", "cancelled"}
	started_cats = {"started"}
	for name, chs in changes.items():
		# time a task sits in a status = gap between consecutive changes
		for idx in range(len(chs) - 1):
			t0, label, _cat = chs[idx]
			t1 = chs[idx + 1][0]
			secs = (t1 - t0).total_seconds()
			if secs > 0 and label:
				status_total[label] = status_total.get(label, 0) + secs
				status_count[label] = status_count.get(label, 0) + 1
		# lead/cycle: find first 'started' entry and the completion entry
		done_t = next((t for (t, _l, c) in reversed(chs) if c in done_cats), None)
		if done_t:
			completed += 1
			lead.append((done_t - created[name]).total_seconds() / DAY)
			started_t = next((t for (t, _l, c) in chs if c in started_cats), None)
			if started_t:
				cycle.append((done_t - started_t).total_seconds() / DAY)

	per_status = sorted(
		[
			{"status_name": k, "avg_days": round(status_total[k] / status_count[k] / DAY, 1), "moves": status_count[k]}
			for k in status_total
		],
		key=lambda x: -x["avg_days"],
	)
	avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else 0
	return {
		"per_status": per_status,
		"avg_lead_days": avg(lead),
		"avg_cycle_days": avg(cycle),
		"completed": completed,
	}


def _mirror_time_log_to_erpnext(doc):
	"""Best-effort: mirror a native Projex Time Log into an ERPNext Timesheet so
	billing/costing/payroll reconcile in one ledger. Returns the Timesheet name
	or None. NEVER raises — the native log is the projex-side source of truth and
	must not be held hostage to ERPNext validation."""
	if not _erpnext_installed():
		return None
	try:
		erpnext_project = frappe.db.get_value("Projex Project", doc.project, "erpnext_project")
		issue = frappe.db.get_value(
			"Projex Issue", doc.issue, ["issue_id", "title"], as_dict=True
		) or frappe._dict(issue_id=doc.issue, title="")
		company = frappe.defaults.get_global_default("company")
		from_time = frappe.utils.get_datetime(f"{doc.spent_on} 09:00:00")
		ts = frappe.new_doc("Timesheet")
		if company:
			ts.company = company
		ts.parent_project = erpnext_project or None
		ts.append(
			"time_logs",
			{
				"hours": float(doc.hours),
				"project": erpnext_project or None,
				"is_billable": 1 if doc.is_billable else 0,
				"billing_hours": float(doc.hours) if doc.is_billable else 0,
				"description": f"[{issue.issue_id}] {issue.title}"
				+ (f"\n{doc.note}" if doc.note else ""),
				"from_time": from_time,
			},
		)
		ts.insert(ignore_permissions=True)
		return ts.name
	except Exception:
		frappe.log_error("projex: ERPNext timesheet mirror failed")
		return None


@frappe.whitelist()
def create_time_log(issue, hours, spent_on=None, activity=None, is_billable=0, note=None, user=None):
	"""Record time spent on a task — a NATIVE Projex Time Log (stored in the app,
	no ERPNext needed). When ERPNext is installed it is also mirrored into an
	ERPNext Timesheet (single ledger for billing) and the link stamped back.
	A timesheet entry references the existing task it was for; it does not create a task."""
	from projex.permissions import user_can_access_project
	project = frappe.db.get_value("Projex Issue", issue, "project")
	if not project or not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	# Members log their own time; only a manager may log on someone else's behalf.
	who = user or frappe.session.user
	if who != frappe.session.user and not _can_manage_project(project):
		who = frappe.session.user
	is_billable = frappe.parse_json(is_billable) if isinstance(is_billable, str) else is_billable
	doc = frappe.get_doc({
		"doctype": "Projex Time Log", "issue": issue, "project": project, "user": who,
		"hours": float(hours), "spent_on": spent_on or frappe.utils.nowdate(),
		"activity": activity or None, "is_billable": 1 if is_billable else 0, "note": note or None,
	}).insert(ignore_permissions=True)
	ts_name = _mirror_time_log_to_erpnext(doc)
	if ts_name:
		doc.db_set("erpnext_timesheet", ts_name)
	frappe.db.commit()
	return {"ok": True, "name": doc.name, "erpnext_timesheet": ts_name}


@frappe.whitelist()
def delete_time_log(name):
	"""Remove a native time log (own entry, or a manager of its project).
	Also removes its mirrored ERPNext Timesheet when that copy is still an
	unbilled draft, so the two ledgers stay in step."""
	row = frappe.db.get_value(
		"Projex Time Log", name, ["project", "user", "billed", "erpnext_timesheet"], as_dict=True
	)
	if not row:
		return {"ok": True}
	if row.user != frappe.session.user and not _can_manage_project(row.project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if row.billed:
		frappe.throw("This time has already been billed and cannot be deleted.")
	if row.erpnext_timesheet and frappe.db.exists("Timesheet", row.erpnext_timesheet):
		try:
			ts = frappe.get_doc("Timesheet", row.erpnext_timesheet)
			if ts.docstatus == 0:
				ts.delete(ignore_permissions=True)
		except Exception:
			frappe.log_error("projex: ERPNext timesheet cleanup on delete failed")
	frappe.delete_doc("Projex Time Log", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def get_project_timesheets(project):
	"""Timesheets view: native flow-time analytics (always) + native logged hours
	(Projex Time Log — created in-app, no ERPNext dependency)."""
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)

	auto = _time_analytics(project)

	rows = frappe.get_all(
		"Projex Time Log", filters={"project": project},
		fields=["name", "issue", "user", "hours", "spent_on", "activity", "is_billable", "note"],
		order_by="spent_on desc, creation desc", limit=0,
	)
	issue_ids, names = {}, {}
	total = billable = 0.0
	by_user, by_issue = {}, {}
	entries = []
	for r in rows:
		total += r.hours or 0
		if r.is_billable:
			billable += r.hours or 0
		if r.issue not in issue_ids:
			issue_ids[r.issue] = frappe.db.get_value("Projex Issue", r.issue, "issue_id") or r.issue
		if r.user not in names:
			names[r.user] = frappe.db.get_value("User", r.user, "full_name") or r.user
		iid = issue_ids[r.issue]
		by_user[r.user] = by_user.get(r.user, 0) + (r.hours or 0)
		by_issue[iid] = by_issue.get(iid, 0) + (r.hours or 0)
		entries.append({
			"name": r.name, "issue": r.issue, "issue_id": iid,
			"by": names[r.user], "hours": r.hours or 0, "spent_on": str(r.spent_on) if r.spent_on else None,
			"activity": r.activity, "billable": bool(r.is_billable), "note": r.note,
		})

	logged = {
		"available": True,
		"total_hours": round(total, 2),
		"billable_hours": round(billable, 2),
		"by_user": sorted(
			[{"user": u, "name": names[u], "hours": round(h, 2)} for u, h in by_user.items()],
			key=lambda x: -x["hours"],
		),
		"by_issue": sorted(
			[{"issue_id": k, "hours": round(v, 2)} for k, v in by_issue.items()],
			key=lambda x: -x["hours"],
		),
		"entries": entries[:100],
	}
	return {"auto": auto, "logged": logged, "erpnext": _erpnext_installed()}


@frappe.whitelist()
def get_project_finance(project):
	"""Per-project P&L pulled from the linked ERPNext Project (cost, billed,
	sales, gross margin). Manager-gated. Returns available:False otherwise."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	erp = _erpnext_project(project)
	if not erp:
		return {"available": False, "erpnext": _erpnext_installed()}
	summary = frappe.db.get_value(
		"Project", erp,
		[
			"estimated_costing", "total_costing_amount", "total_purchase_cost",
			"total_sales_amount", "total_billable_amount", "total_billed_amount",
			"total_consumed_material_cost", "gross_margin", "per_gross_margin",
			"actual_time", "percent_complete",
		],
		as_dict=True,
	) or {}
	invoices = []
	if frappe.db.has_column("Sales Invoice", "project"):
		invoices = frappe.get_all(
			"Sales Invoice", filters={"project": erp},
			fields=["name", "grand_total", "outstanding_amount", "status", "posting_date"],
			order_by="posting_date desc", limit=50,
		)
	return {
		"available": True, "erpnext_project": erp, "currency": _company_currency(),
		"summary": summary, "invoices": invoices,
	}


# --------------------------------------------------------------------------- #
# AI surfaces — provider-agnostic, all return {enabled: bool, ...}
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def ai_stalled_issues(project=None):
	"""Heuristic 'stalled' detector (works without a key); enriched when AI on."""
	filters = {}
	if project:
		filters["project"] = project
	cutoff = add_days(nowdate(), -4)
	issues = frappe.get_all(
		"Projex Issue",
		filters={**filters, "modified": ["<", cutoff]},
		fields=["name", "issue_id", "title", "project", "modified"],
		limit=10,
	)
	# Even without a provider key we can surface the heuristic result.
	return ai.result(enabled=True, stalled=issues, ai_enhanced=ai.is_ai_enabled())


@frappe.whitelist()
def ai_suggest_owners(issue):
	if not ai.is_ai_enabled():
		return ai.result(enabled=False)
	return ai.result(enabled=True, suggestions=[])


@frappe.whitelist()
def ai_generate_test_plan(issue):
	if not ai.is_ai_enabled():
		return ai.result(enabled=False)
	return ai.result(enabled=True, plan=[])


@frappe.whitelist()
def ai_due_from_velocity(issue):
	if not ai.is_ai_enabled():
		return ai.result(enabled=False)
	return ai.result(enabled=True, due_date=None)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _attach_status_meta(issues):
	cats = {
		s.name: s.category
		for s in frappe.get_all("Projex Status", fields=["name", "category"])
	}
	for it in issues:
		it["_status_category"] = cats.get(it.get("status"))
