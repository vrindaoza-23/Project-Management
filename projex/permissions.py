# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Project-membership based row-level permissions.

A user can access a Projex Project if any of:
  - they are a System Manager / Projex Admin,
  - they are the project lead,
  - they are listed in the project's members child table.

Access is strictly per-project: workspace membership is a grouping layer only
and does NOT grant access to the workspace's projects. Issues, comments,
cycles, etc. inherit access from their project. Enforced server-side via
`permission_query_conditions` (list filtering) and `has_permission`
(single-doc gating), registered in hooks.py.
"""

import frappe


def _is_privileged(user):
	roles = set(frappe.get_roles(user))
	return bool(roles & {"System Manager", "Projex Admin", "Administrator"})


def accessible_projects(user=None):
	"""Return the set of project names the user may access."""
	user = user or frappe.session.user
	if _is_privileged(user):
		return None  # None == no restriction

	projects = set()
	# Direct project membership or lead.
	rows = frappe.get_all(
		"Projex Project", filters={"lead": user}, pluck="name"
	)
	projects.update(rows)
	member_rows = frappe.get_all(
		"Projex Project Member", filters={"user": user}, fields=["parent"]
	)
	projects.update(r.parent for r in member_rows)
	return projects


def accessible_project_condition(user, column):
	"""SQL condition string for permission_query_conditions hooks."""
	user = user or frappe.session.user
	projects = accessible_projects(user)
	if projects is None:
		return ""
	if not projects:
		return f"{column} IS NULL AND 1=0"  # no access -> empty result
	quoted = ", ".join(frappe.db.escape(p) for p in projects)
	return f"{column} IN ({quoted})"


def user_can_access_project(project, user=None):
	user = user or frappe.session.user
	projects = accessible_projects(user)
	if projects is None:
		return True
	return project in projects
