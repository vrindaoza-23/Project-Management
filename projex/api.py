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
from frappe.utils import add_days, getdate, nowdate

from projex import ai
from projex.permissions import accessible_projects
from projex.realtime import emit_presence

ISSUE_FIELDS = [
	"name", "issue_id", "title", "project", "status", "priority",
	"due_date", "start_date", "estimate", "rank", "cycle", "reporter", "parent_issue", "modified",
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
	for k in ("project_name", "icon", "color", "status", "lead", "description", "workspace"):
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
			"workspace": doc.workspace, "description": doc.description,
			"can_manage": _can_manage_project(project),
		},
		"members": members,
		"labels": labels,
		"cycles": cycles,
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


@frappe.whitelist()
def add_member(parent_doctype, parent, user, role="Member"):
	if parent_doctype not in ("Projex Project", "Projex Workspace"):
		frappe.throw("Invalid parent")
	if parent_doctype == "Projex Project" and not _can_manage_project(parent):
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
def remove_member(parent_doctype, parent, user):
	if parent_doctype not in ("Projex Project", "Projex Workspace"):
		frappe.throw("Invalid parent")
	if parent_doctype == "Projex Project" and not _can_manage_project(parent):
		frappe.throw("Not permitted", frappe.PermissionError)
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
def create_cycle(project, cycle_name, start_date=None, end_date=None, state="Upcoming"):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	doc = frappe.get_doc({
		"doctype": "Projex Cycle", "cycle_name": cycle_name, "project": project,
		"start_date": start_date or None, "end_date": end_date or None, "state": state,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name, "cycle_name": doc.cycle_name}


@frappe.whitelist()
def delete_cycle(name):
	project = frappe.db.get_value("Projex Cycle", name, "project")
	if project and not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	frappe.delete_doc("Projex Cycle", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Bootstrap + board data (shell, list, board)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def bootstrap():
	"""Everything the app shell needs on load: projects, workspaces, people."""
	projects = frappe.get_list(
		"Projex Project",
		fields=["name", "project_name", "key", "icon", "color", "status", "workspace", "lead"],
		order_by="project_name asc",
		ignore_permissions=False,
	)
	workspaces = frappe.get_all(
		"Projex Workspace", fields=["name", "workspace_name", "icon"], order_by="workspace_name asc"
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
		"users": users,
		"counts": counts,
		"favorites": favorites,
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
			"priority": doc.priority, "due_date": str(doc.due_date) if doc.due_date else None,
			"start_date": str(doc.start_date) if doc.start_date else None,
			"estimate": doc.estimate, "cycle": doc.cycle, "reporter": doc.reporter,
			"parent_issue": doc.parent_issue, "creation": str(doc.creation),
			"modified": str(doc.modified),
			"assignees": [a.user for a in doc.assignees],
		},
		"status_meta": status,
		"labels": labels,
		"subtasks": subtasks,
		"comments": comments,
		"links": links,
		"attachments": attachments,
	}


# Fields a client is allowed to mutate via update_issue/create_issue.
# Everything else (issue_id, rank, reporter, owner, name, …) is off-limits to
# prevent mass-assignment; rank changes go through reorder_issue.
EDITABLE_ISSUE_FIELDS = {
	"title", "description", "status", "priority", "due_date", "start_date",
	"estimate", "cycle", "parent_issue", "assignees", "labels",
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
	for f in ("status", "priority", "due_date", "estimate", "cycle", "description", "parent_issue"):
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
		fields=["name", "cycle_name", "state"], order_by="start_date desc",
	)
	users = frappe.get_all(
		"User", filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "user_image"], limit=200,
	)
	return {"labels": labels, "cycles": cycles, "users": users}


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
		"activity": get_activity(project, 12),
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

	return {
		"distribution": distribution,
		"velocity": velocity,
		"throughput": throughput,
		"avg_cycle_time": avg_cycle,
		"total_completed": len(done),
	}


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
		return {"today": [], "week": [], "later": [], "done": []}

	issues = frappe.get_all(
		"Projex Issue",
		filters={"name": ["in", assigned]},
		fields=ISSUE_FIELDS,
		order_by="due_date asc",
	)
	_attach_status_meta(issues)

	today = getdate(nowdate())
	week_end = add_days(today, 7)
	groups = {"today": [], "week": [], "later": [], "done": []}
	for it in issues:
		if it.get("_status_category") in ("completed", "cancelled"):
			groups["done"].append(it)
		elif it.get("due_date") and getdate(it["due_date"]) <= today:
			groups["today"].append(it)
		elif it.get("due_date") and getdate(it["due_date"]) <= week_end:
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
	return {
		"erpnext": _erpnext_installed(),
		"timesheet": _erpnext_installed(),
		"ai": ai.is_ai_enabled(),
	}


@frappe.whitelist()
def log_time(issue, hours, activity_type=None, note=None):
	"""Create an ERPNext Timesheet entry linked to a Projex issue.

	Wedge integration #1. No-ops cleanly (raises a friendly error) when ERPNext
	is not installed. Reuses the issue's project ERPNext link when present.
	"""
	if not _erpnext_installed():
		frappe.throw("ERPNext is not installed; time logging is unavailable.")

	issue_doc = frappe.get_doc("Projex Issue", issue)
	project = frappe.get_doc("Projex Project", issue_doc.project)
	company = frappe.defaults.get_global_default("company")

	erpnext_project = project.get("erpnext_project")
	ts = frappe.new_doc("Timesheet")
	if company:
		ts.company = company
	ts.parent_project = erpnext_project or None
	ts.append("time_logs", {
		"activity_type": activity_type,
		"hours": float(hours),
		"project": erpnext_project or None,
		"is_billable": 1,
		"description": f"[{issue_doc.issue_id}] {issue_doc.title}" + (f"\n{note}" if note else ""),
		"from_time": frappe.utils.now_datetime(),
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
	from projex.permissions import user_can_access_project
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if not _erpnext_installed():
		frappe.throw("ERPNext is not installed.")
	doc = frappe.get_doc("Projex Project", project)
	doc.db_set("erpnext_customer", erpnext_customer or None)
	doc.db_set("erpnext_project", erpnext_project or None)
	frappe.db.commit()
	return {"ok": True}


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
