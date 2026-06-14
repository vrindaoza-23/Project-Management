# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Realtime fan-out helpers.

Events are published to a per-project room so only clients viewing that
project receive them. The SPA subscribes via socket.io and patches its
frappe-ui resources in place (reconciling against optimistic updates).
"""

import frappe


def project_room(project):
	return f"projex:project:{project}"


def emit_issue_event(event, doc):
	"""Emit a compact issue payload to the project room."""
	payload = {
		"name": doc.name,
		"issue_id": doc.get("issue_id"),
		"project": doc.get("project"),
		"status": doc.get("status"),
		"priority": doc.get("priority"),
		"title": doc.get("title"),
		"rank": doc.get("rank"),
		"modified": str(doc.get("modified") or ""),
	}
	frappe.publish_realtime(event, payload, room=project_room(doc.get("project")))


def emit_comment_event(event, doc, project):
	frappe.publish_realtime(
		event,
		{"name": doc.name, "issue": doc.get("issue"), "project": project},
		room=project_room(project),
	)


def emit_presence(project, issue, users):
	frappe.publish_realtime(
		"projex:presence",
		{"issue": issue, "users": users},
		room=project_room(project),
	)
