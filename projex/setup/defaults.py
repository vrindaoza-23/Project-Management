# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Production install defaults — runs on after_install AND after_migrate.

Creates the things a working site needs but that are NOT demo data:
the Projex roles and the six global default statuses. Idempotent.
(Demo content lives in projex.seed and must never run in production.)
"""

import frappe

ROLES = ["Projex Admin", "Projex Member", "Projex Guest"]

# The client/customer role is portal-only — it must NOT get desk access.
PORTAL_ROLES = ["Projex Client"]

# status_name, category, color_theme, dot_hollow, position
DEFAULT_STATUSES = [
	("Backlog", "backlog", "gray", 1, 0),
	("Todo", "unstarted", "gray", 0, 1),
	("In progress", "started", "blue", 0, 2),
	("In review", "started", "amber", 0, 3),
	("Done", "completed", "green", 0, 4),
	("Cancelled", "cancelled", "gray", 1, 5),
]


def ensure_roles():
	for r in ROLES:
		if not frappe.db.exists("Role", r):
			frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 1}).insert(
				ignore_permissions=True
			)
	for r in PORTAL_ROLES:
		if not frappe.db.exists("Role", r):
			frappe.get_doc({"doctype": "Role", "role_name": r, "desk_access": 0}).insert(
				ignore_permissions=True
			)


def ensure_statuses():
	# Only create global (project-less) defaults if none exist yet.
	for name, category, theme, hollow, pos in DEFAULT_STATUSES:
		exists = frappe.db.get_value(
			"Projex Status", {"status_name": name, "project": ["in", ["", None]]}
		)
		if exists:
			continue
		frappe.get_doc({
			"doctype": "Projex Status", "status_name": name, "category": category,
			"color_theme": theme, "dot_hollow": hollow, "position": pos,
		}).insert(ignore_permissions=True)


def run():
	# DocType `Projex Status` must exist before seeding (after_migrate guarantees it).
	if not frappe.db.exists("DocType", "Projex Status"):
		return
	ensure_roles()
	ensure_statuses()
	frappe.db.commit()
