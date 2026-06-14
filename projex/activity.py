# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Lightweight activity/audit log feeding the Summary dashboard and drawer."""

import frappe


def log(project, issue, action, detail=""):
	if not project:
		return
	try:
		frappe.get_doc({
			"doctype": "Projex Activity",
			"project": project, "issue": issue,
			"actor": frappe.session.user, "action": action, "detail": detail,
		}).insert(ignore_permissions=True)
		frappe.publish_realtime(
			"projex:activity", {"project": project, "issue": issue},
			room=f"projex:project:{project}",
		)
	except Exception:
		# Never let audit logging break a mutation.
		frappe.log_error("projex activity log failed")
