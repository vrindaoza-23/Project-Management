# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""GitHub App connection flow — one-click org install, like Linear/Jira.

Instead of the admin hand-registering an App and pasting a webhook secret +
PAT, we drive GitHub's *manifest* flow:

  1. Admin clicks "Connect" -> browser POSTs a manifest to github.com, which
     pre-fills the "create App" page. The admin confirms.
  2. GitHub redirects back to `app_created` with a short-lived code; we exchange
     it (`/app-manifests/{code}/conversions`) for the App's id, private key,
     webhook secret and client credentials — all stored on the Single settings.
  3. We send the admin to install the App; GitHub redirects to `app_installed`
     with the installation id, which we persist.

API calls then authenticate as the installation: mint an RS256 JWT from the
private key, exchange it for a ~1h installation token (cached in Redis). This
module owns creation/auth; webhook handling stays in `github.py`.
"""

import time

import frappe

from projex.github import GITHUB_API, SETTINGS, _gh_request, _settings

STATE_CACHE = "projex_gh_app_state"
TOKEN_CACHE = "projex_gh_inst_token"

# Least-privilege: write issues (comment + none else), read PRs/checks/code.
APP_PERMISSIONS = {
	"issues": "write",
	"pull_requests": "read",
	"checks": "read",
	"contents": "read",
	"metadata": "read",
}
APP_EVENTS = ["pull_request", "push", "check_suite", "status", "installation"]


# --------------------------------------------------------------------------- #
# Step 1 — manifest
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def app_manifest():
	"""Return the manifest + a one-time state for the browser to POST to GitHub."""
	frappe.only_for("System Manager")
	state = frappe.generate_hash(length=32)
	frappe.cache().set_value(f"{STATE_CACHE}:{state}", "1", expires_in_sec=900)
	site = frappe.utils.get_url()
	manifest = {
		"name": f"Projex ({frappe.local.site})"[:34],
		"url": site,
		"hook_attributes": {"url": f"{site}/api/method/projex.github.webhook"},
		"redirect_url": f"{site}/api/method/projex.github_app.app_created",
		"setup_url": f"{site}/api/method/projex.github_app.app_installed",
		"setup_on_update": True,
		"public": False,
		"default_permissions": APP_PERMISSIONS,
		"default_events": APP_EVENTS,
	}
	return {
		"post_url": f"https://github.com/settings/apps/new?state={state}",
		"manifest": frappe.as_json(manifest),
		"state": state,
	}


# --------------------------------------------------------------------------- #
# Step 2 — manifest conversion (GitHub redirects the browser here)
# --------------------------------------------------------------------------- #
@frappe.whitelist(allow_guest=True)
def app_created(code=None, state=None):
	"""Exchange the manifest `code` for App credentials, then send the admin on
	to install the App."""
	if not _valid_state(state):
		return _redirect("/projex?github=state_error")
	creds = _convert_manifest(code)
	if not creds:
		return _redirect("/projex?github=convert_error")
	_store_app(creds)
	# Off to install it; GitHub will bounce back to `app_installed`.
	slug = creds.get("slug")
	return _redirect(f"https://github.com/apps/{slug}/installations/new" if slug else "/projex?github=connected")


def _convert_manifest(code):
	"""POST the temporary code to GitHub; returns the App payload (unauthenticated)."""
	if not code:
		return None
	return _gh_request("POST", f"/app-manifests/{code}/conversions", token=None)


def _store_app(creds):
	s = _settings()
	s.enabled = 1
	s.app_id = str(creds.get("id") or "")
	s.app_slug = creds.get("slug")
	s.client_id = creds.get("client_id")
	if creds.get("client_secret"):
		s.client_secret = creds["client_secret"]
	if creds.get("pem"):
		s.private_key = creds["pem"]
	if creds.get("webhook_secret"):
		s.webhook_secret = creds["webhook_secret"]
	s.save(ignore_permissions=True)
	frappe.db.commit()


# --------------------------------------------------------------------------- #
# Step 3 — installation (GitHub redirects here after the admin installs)
# --------------------------------------------------------------------------- #
@frappe.whitelist(allow_guest=True)
def app_installed(installation_id=None, setup_action=None, **kwargs):
	if installation_id:
		set_installation(installation_id)
	return _redirect("/projex?github=connected")


@frappe.whitelist()
def install_url():
	"""Where the admin installs (or re-installs) the connected App."""
	frappe.only_for("System Manager")
	slug = _settings().app_slug
	if not slug:
		frappe.throw("Connect a GitHub App first.")
	return f"https://github.com/apps/{slug}/installations/new"


@frappe.whitelist()
def disconnect_app():
	"""Forget the App entirely (does not delete it on GitHub)."""
	frappe.only_for("System Manager")
	s = _settings()
	for f in ("app_id", "app_slug", "installation_id", "client_id", "client_secret", "private_key"):
		setattr(s, f, "")
	s.enabled = 0
	s.save(ignore_permissions=True)
	frappe.cache().delete_value(TOKEN_CACHE)
	frappe.db.commit()
	return {"ok": True}


def set_installation(installation_id):
	frappe.db.set_single_value(SETTINGS, "installation_id", str(installation_id))
	frappe.cache().delete_value(TOKEN_CACHE)  # force a fresh token for the new install
	frappe.db.commit()


def clear_installation():
	frappe.db.set_single_value(SETTINGS, "installation_id", "")
	frappe.cache().delete_value(TOKEN_CACHE)
	frappe.db.commit()


# --------------------------------------------------------------------------- #
# Authentication — JWT + installation token
# --------------------------------------------------------------------------- #
def is_app_configured():
	s = _settings()
	return bool(s.app_id and s.installation_id and s.get_password("private_key", raise_exception=False))


def installation_token():
	"""Cached installation access token, or None if the App isn't ready."""
	cached = frappe.cache().get_value(TOKEN_CACHE)
	if cached and cached.get("exp", 0) > time.time() + 60:
		return cached["token"]

	s = _settings()
	if not is_app_configured():
		return None
	jwt_token = _app_jwt(s)
	if not jwt_token:
		return None
	resp = _gh_request("POST", f"/app/installations/{s.installation_id}/access_tokens", token=jwt_token)
	if not resp or not resp.get("token"):
		return None
	exp = _parse_expiry(resp.get("expires_at"))
	frappe.cache().set_value(TOKEN_CACHE, {"token": resp["token"], "exp": exp}, expires_in_sec=3000)
	return resp["token"]


def _app_jwt(s):
	import jwt

	pem = s.get_password("private_key", raise_exception=False)
	if not pem or not s.app_id:
		return None
	now = int(time.time())
	# iat backdated 60s to tolerate clock skew; exp <= 10 min per GitHub.
	payload = {"iat": now - 60, "exp": now + 540, "iss": str(s.app_id)}
	try:
		return jwt.encode(payload, pem, algorithm="RS256")
	except Exception:
		frappe.log_error("projex github app jwt sign failed")
		return None


def _parse_expiry(expires_at):
	if not expires_at:
		return time.time() + 3000
	try:
		dt = frappe.utils.get_datetime(expires_at.replace("Z", ""))
		return dt.timestamp()
	except Exception:
		return time.time() + 3000


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _valid_state(state):
	if not state:
		return False
	key = f"{STATE_CACHE}:{state}"
	ok = frappe.cache().get_value(key)
	frappe.cache().delete_value(key)  # one-time use
	return bool(ok)


def _redirect(location):
	if not location.startswith("http"):
		location = frappe.utils.get_url(location)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = location
