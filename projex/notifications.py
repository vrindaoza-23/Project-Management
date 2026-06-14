# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt
"""Central notification delivery: in-app record + realtime + optional email.

Both the Issue and Comment controllers funnel through `deliver()` so in-app
and email behaviour stay consistent. Email is best-effort — if the site has no
outgoing email account configured, the send is skipped and the in-app
notification still lands (logged, never raised).
"""

import frappe

# Notification type -> the preference field that gates its email. Types not
# listed here (e.g. due, review) are gated only by the master `email_enabled`.
_TYPE_PREF = {
	"mention": "email_mentions",
	"assigned": "email_assigned",
	"comment": "email_comments",
	"status": "email_status",
}

_DEFAULT_PREFS = {
	"email_enabled": 1,
	"email_mentions": 1,
	"email_assigned": 1,
	"email_comments": 1,
	"email_status": 1,
}


def get_preferences(user):
	"""Return the user's email preferences, falling back to all-on defaults."""
	name = frappe.db.exists("Projex Notification Preference", {"user": user})
	if not name:
		return {"user": user, **_DEFAULT_PREFS}
	row = frappe.db.get_value(
		"Projex Notification Preference", name, list(_DEFAULT_PREFS.keys()), as_dict=True
	)
	return {"user": user, **{k: int(row.get(k)) for k in _DEFAULT_PREFS}}


def _email_allowed(user, ntype):
	prefs = get_preferences(user)
	if not prefs.get("email_enabled"):
		return False
	pref_field = _TYPE_PREF.get(ntype)
	if pref_field is None:
		return True  # no per-type toggle -> master switch already passed
	return bool(prefs.get(pref_field))


def deliver(user, ntype, actor, issue, snippet):
	"""Create the in-app notification, push realtime, and email if allowed."""
	frappe.get_doc({
		"doctype": "Projex Notification",
		"user": user,
		"notification_type": ntype,
		"actor": actor,
		"issue": issue,
		"snippet": snippet,
		"is_read": 0,
	}).insert(ignore_permissions=True)
	frappe.publish_realtime(
		"projex:notification", {"user": user, "issue": issue, "type": ntype}, user=user
	)
	if _email_allowed(user, ntype):
		_send_email(user, ntype, actor, issue, snippet)


def _send_email(user, ntype, actor, issue, snippet):
	recipient = frappe.db.get_value("User", user, "email") or user
	if not recipient or "@" not in recipient:
		return
	doc = frappe.db.get_value("Projex Issue", issue, ["issue_id", "title"], as_dict=True) or {}
	actor_name = frappe.db.get_value("User", actor, "full_name") or actor
	issue_ref = doc.get("issue_id") or issue
	subject = f"[{issue_ref}] {snippet}"
	site = frappe.utils.get_url()
	body = f"""<p><b>{frappe.utils.escape_html(actor_name)}</b> {frappe.utils.escape_html(snippet)}</p>
<p style="color:#6b7280">{frappe.utils.escape_html(doc.get('title') or '')}</p>
<p><a href="{site}/projex">Open {issue_ref} in Projex</a></p>"""
	try:
		frappe.sendmail(
			recipients=[recipient],
			subject=subject,
			message=body,
			reference_doctype="Projex Issue",
			reference_name=issue,
			now=False,  # enqueue to the Email Queue
		)
	except Exception:
		# No outgoing account / SMTP error: keep in-app notifications working.
		frappe.log_error(title="Projex email notification skipped")
