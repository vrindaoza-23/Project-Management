"""Idempotent schema installer for Projex.

Creates roles and DocTypes programmatically. In developer mode this exports
each DocType's JSON into projex/projex/<module>/doctype/<name>/ so the schema
becomes versioned app source, synced on `bench migrate`.

Run once:
    bench --site <site> execute projex.setup.install_schema.run
Safe to re-run: existing DocTypes/roles are skipped.
"""

import frappe

MODULE = "Projex"
APP = "projex"

ROLES = ["Projex Admin", "Projex Member", "Projex Guest"]


def _field(fieldname, label, fieldtype, **kw):
	f = {"fieldname": fieldname, "label": label, "fieldtype": fieldtype}
	f.update(kw)
	return f


def _perms():
	"""Standard perm matrix: System Manager + Projex roles."""
	return [
		{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
		{"role": "Projex Admin", "read": 1, "write": 1, "create": 1, "delete": 1},
		{"role": "Projex Member", "read": 1, "write": 1, "create": 1, "delete": 0},
		{"role": "Projex Guest", "read": 1, "write": 0, "create": 0, "delete": 0},
	]


def _make_doctype(name, fields, *, istable=0, autoname=None, title_field=None,
				  track_changes=1, sort_field="modified", sort_order="DESC"):
	if frappe.db.exists("DocType", name):
		return False
	doc = {
		"doctype": "DocType",
		"name": name,
		"module": MODULE,
		"custom": 0,
		"istable": istable,
		"editable_grid": 1 if istable else 0,
		"engine": "InnoDB",
		"track_changes": track_changes if not istable else 0,
		"fields": fields,
		"permissions": [] if istable else _perms(),
	}
	if autoname:
		doc["autoname"] = autoname
	if title_field:
		doc["title_field"] = title_field
		doc["show_title_field_in_link"] = 1
	frappe.get_doc(doc).insert(ignore_permissions=True)
	return True


def create_roles():
	for r in ROLES:
		if not frappe.db.exists("Role", r):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": r,
				"desk_access": 1,
			}).insert(ignore_permissions=True)


def create_doctypes():
	created = []

	# ---- Workspace + members ------------------------------------------------
	if _make_doctype("Projex Workspace Member", [
		_field("user", "User", "Link", options="User", reqd=1, in_list_view=1),
		_field("role", "Role", "Select", options="Admin\nMember\nGuest", default="Member", in_list_view=1),
	], istable=1):
		created.append("Projex Workspace Member")

	if _make_doctype("Projex Workspace", [
		_field("workspace_name", "Workspace name", "Data", reqd=1, in_list_view=1),
		_field("icon", "Icon", "Data", description="Lucide icon name"),
		_field("description", "Description", "Small Text"),
		_field("members", "Members", "Table", options="Projex Workspace Member"),
	], title_field="workspace_name"):
		created.append("Projex Workspace")

	# ---- Project + members --------------------------------------------------
	if _make_doctype("Projex Project Member", [
		_field("user", "User", "Link", options="User", reqd=1, in_list_view=1),
		_field("role", "Role", "Select", options="Admin\nMember\nGuest", default="Member", in_list_view=1),
	], istable=1):
		created.append("Projex Project Member")

	project_fields = [
		_field("project_name", "Project name", "Data", reqd=1, in_list_view=1),
		_field("key", "Key", "Data", reqd=1, unique=1, in_list_view=1,
			   description="2-4 chars, used for issue ids e.g. BIL-12"),
		_field("workspace", "Workspace", "Link", options="Projex Workspace", in_standard_filter=1),
		_field("icon", "Icon", "Data", description="Lucide icon name"),
		_field("color", "Color", "Data", description="Palette token e.g. var(--blue-500)"),
		_field("status", "Status", "Select", options="Active\nPlanning\nOn hold\nCompleted",
			   default="Active", in_list_view=1, in_standard_filter=1),
		_field("lead", "Lead", "Link", options="User"),
		_field("description", "Description", "Small Text"),
		_field("members", "Members", "Table", options="Projex Project Member"),
		_field("issue_counter", "Issue counter", "Int", hidden=1, default=0,
			   description="Internal: last issue number for this project key"),
		# ERPNext links (Customer/Project) are added as Custom Fields only when
		# ERPNext is installed — see projex.setup.erpnext_integration. Core stays
		# installable on a plain Frappe site.
	]
	if _make_doctype("Projex Project", project_fields, title_field="project_name"):
		created.append("Projex Project")

	# ---- Status -------------------------------------------------------------
	if _make_doctype("Projex Status", [
		_field("status_name", "Status name", "Data", reqd=1, in_list_view=1),
		_field("category", "Category", "Select",
			   options="backlog\nunstarted\nstarted\ncompleted\ncancelled",
			   default="unstarted", in_list_view=1),
		_field("color_theme", "Color theme", "Select",
			   options="gray\nblue\namber\ngreen\nred\npurple", default="gray", in_list_view=1),
		_field("dot_hollow", "Hollow dot", "Check", default=0),
		_field("position", "Position", "Int", default=0),
		_field("project", "Project", "Link", options="Projex Project",
			   description="Leave empty for a global/default status"),
	], title_field="status_name"):
		created.append("Projex Status")

	# ---- Label --------------------------------------------------------------
	if _make_doctype("Projex Label", [
		_field("label_name", "Label", "Data", reqd=1, in_list_view=1),
		_field("color", "Color", "Data", description="Palette token e.g. var(--blue-500)"),
		_field("project", "Project", "Link", options="Projex Project"),
	], title_field="label_name"):
		created.append("Projex Label")

	# ---- Cycle --------------------------------------------------------------
	if _make_doctype("Projex Cycle", [
		_field("cycle_name", "Cycle name", "Data", reqd=1, in_list_view=1),
		_field("project", "Project", "Link", options="Projex Project", in_standard_filter=1),
		_field("start_date", "Start date", "Date"),
		_field("end_date", "End date", "Date"),
		_field("state", "State", "Select", options="Active\nUpcoming\nCompleted",
			   default="Upcoming", in_list_view=1),
	], title_field="cycle_name"):
		created.append("Projex Cycle")

	# ---- Issue child tables -------------------------------------------------
	if _make_doctype("Projex Issue Assignee", [
		_field("user", "User", "Link", options="User", reqd=1, in_list_view=1),
	], istable=1):
		created.append("Projex Issue Assignee")

	if _make_doctype("Projex Issue Label", [
		_field("label", "Label", "Link", options="Projex Label", reqd=1, in_list_view=1),
	], istable=1):
		created.append("Projex Issue Label")

	# ---- Issue (core) -------------------------------------------------------
	issue_fields = [
		_field("title", "Title", "Data", reqd=1, in_list_view=1),
		_field("issue_id", "Issue ID", "Data", read_only=1, in_list_view=1, bold=1,
			   description="Per-project key e.g. BIL-12 (mirrors name)"),
		_field("project", "Project", "Link", options="Projex Project", reqd=1, in_standard_filter=1),
		_field("workspace", "Workspace", "Link", options="Projex Workspace",
			   fetch_from="project.workspace", read_only=1),
		_field("col_1", "", "Column Break"),
		_field("status", "Status", "Link", options="Projex Status", in_standard_filter=1),
		_field("priority", "Priority", "Select", options="Urgent\nHigh\nMedium\nLow\nNone",
			   default="None", in_standard_filter=1, in_list_view=1),
		_field("rank", "Rank", "Data", description="Lexo-rank for manual ordering"),
		_field("people_section", "People", "Section Break"),
		_field("assignees", "Assignees", "Table MultiSelect", options="Projex Issue Assignee"),
		_field("reporter", "Reporter", "Link", options="User"),
		_field("col_2", "", "Column Break"),
		_field("labels", "Labels", "Table MultiSelect", options="Projex Issue Label"),
		_field("planning_section", "Planning", "Section Break"),
		_field("cycle", "Cycle", "Link", options="Projex Cycle"),
		_field("due_date", "Due date", "Date"),
		_field("estimate", "Estimate", "Int", description="Story points"),
		_field("col_3", "", "Column Break"),
		_field("parent_issue", "Parent issue", "Link", options="Projex Issue"),
		_field("desc_section", "Description", "Section Break"),
		_field("description", "Description", "Text Editor"),
	]
	if _make_doctype("Projex Issue", issue_fields, title_field="title"):
		created.append("Projex Issue")

	# ---- Comment ------------------------------------------------------------
	if _make_doctype("Projex Comment", [
		_field("issue", "Issue", "Link", options="Projex Issue", reqd=1, in_standard_filter=1),
		_field("content", "Content", "Text Editor", reqd=1),
	]):
		created.append("Projex Comment")

	# ---- Notification (Inbox) ----------------------------------------------
	if _make_doctype("Projex Notification", [
		_field("user", "User", "Link", options="User", reqd=1, in_standard_filter=1),
		_field("notification_type", "Type", "Select",
			   options="mention\nassigned\ncomment\nstatus\ndue\nreview",
			   in_list_view=1, in_standard_filter=1),
		_field("actor", "Actor", "Link", options="User"),
		_field("issue", "Issue", "Link", options="Projex Issue"),
		_field("snippet", "Snippet", "Small Text", in_list_view=1),
		_field("is_read", "Is read", "Check", default=0, in_standard_filter=1),
	]):
		created.append("Projex Notification")

	# ---- Activity (audit log feeding Summary + drawer) ---------------------
	if _make_doctype("Projex Activity", [
		_field("project", "Project", "Link", options="Projex Project", in_standard_filter=1),
		_field("issue", "Issue", "Link", options="Projex Issue", in_standard_filter=1),
		_field("actor", "Actor", "Link", options="User", in_standard_filter=1),
		_field("action", "Action", "Data", in_list_view=1),
		_field("detail", "Detail", "Small Text", in_list_view=1),
	], track_changes=0):
		created.append("Projex Activity")

	# ---- Issue links (blocks / relates / duplicates) -----------------------
	if _make_doctype("Projex Issue Link", [
		_field("issue", "Issue", "Link", options="Projex Issue", reqd=1, in_standard_filter=1),
		_field("link_type", "Link type", "Select",
			   options="blocks\nblocked by\nrelates to\nduplicates", default="relates to", in_list_view=1),
		_field("target", "Target", "Link", options="Projex Issue", reqd=1, in_list_view=1),
	]):
		created.append("Projex Issue Link")

	# ---- Favorite (star a project) -----------------------------------------
	if _make_doctype("Projex Favorite", [
		_field("user", "User", "Link", options="User", reqd=1, in_standard_filter=1),
		_field("project", "Project", "Link", options="Projex Project", reqd=1, in_standard_filter=1),
	]):
		created.append("Projex Favorite")

	# ---- Saved view (per-user list/board filters) --------------------------
	if _make_doctype("Projex View", [
		_field("view_name", "View name", "Data", reqd=1, in_list_view=1),
		_field("user", "User", "Link", options="User", in_standard_filter=1),
		_field("project", "Project", "Link", options="Projex Project", in_standard_filter=1),
		_field("view_type", "View type", "Select", options="list\nboard\ncalendar", default="list"),
		_field("config", "Config", "Long Text", description="JSON: filter/sort/group"),
		_field("is_shared", "Shared", "Check", default=0),
	], title_field="view_name"):
		created.append("Projex View")

	# ---- Time Log (native in-app timesheet: hours spent on a task) ----------
	if _make_doctype("Projex Time Log", [
		_field("issue", "Task", "Link", options="Projex Issue", reqd=1, in_standard_filter=1, in_list_view=1),
		_field("project", "Project", "Link", options="Projex Project",
			   fetch_from="issue.project", in_standard_filter=1),
		_field("user", "User", "Link", options="User", reqd=1, in_standard_filter=1, in_list_view=1),
		_field("hours", "Hours", "Float", reqd=1, in_list_view=1),
		_field("spent_on", "Spent on", "Date", in_list_view=1),
		_field("activity", "Activity", "Data"),
		_field("is_billable", "Billable", "Check", default=0),
		_field("note", "Note", "Small Text"),
	]):
		created.append("Projex Time Log")

	return created


def run():
	create_roles()
	created = create_doctypes()
	frappe.db.commit()
	print(f"Roles ensured: {ROLES}")
	print(f"DocTypes created ({len(created)}): {created}" if created else "All DocTypes already existed.")
	return created
