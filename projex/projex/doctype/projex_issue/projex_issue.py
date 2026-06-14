# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from projex.realtime import emit_issue_event
from projex import activity


class ProjexIssue(Document):
	def autoname(self):
		"""Per-project key naming: <KEY>-<n> (e.g. BIL-12)."""
		if not self.project:
			frappe.throw("Project is required")
		key, counter = frappe.db.get_value("Projex Project", self.project, ["key", "issue_counter"])
		n = (counter or 0) + 1
		# Reserve the number atomically so concurrent inserts don't collide.
		frappe.db.set_value("Projex Project", self.project, "issue_counter", n, update_modified=False)
		self.name = f"{key}-{n}"
		self.issue_id = self.name

	def before_insert(self):
		if not self.reporter:
			self.reporter = frappe.session.user
		if not self.status:
			self.status = _default_status_for(self.project)
		if not self.rank:
			# Append to the end; midpoint inserts happen via the reorder API.
			self.rank = _next_rank(self.project)

	def validate(self):
		if self.parent_issue and self.parent_issue == self.name:
			frappe.throw("An issue cannot be its own parent")

	# ---- lifecycle: realtime + notifications --------------------------------
	def after_insert(self):
		emit_issue_event("projex:issue_created", self)
		activity.log(self.project, self.name, "created", self.title)
		self._notify_assignees(reason="assigned")

	def on_update(self):
		emit_issue_event("projex:issue_updated", self)
		before = self.get_doc_before_save()
		if before:
			old = {a.user for a in (before.assignees or [])}
			new = {a.user for a in (self.assignees or [])}
			added = new - old
			if added:
				self._notify_assignees(reason="assigned", only=added)
				activity.log(self.project, self.name, "assigned", ", ".join(added))
			if before.status != self.status:
				self._notify_status_change()
				label = frappe.db.get_value("Projex Status", self.status, "status_name") or self.status
				activity.log(self.project, self.name, "changed status", f"→ {label}")
			if before.priority != self.priority:
				activity.log(self.project, self.name, "changed priority", f"→ {self.priority}")
			if before.title != self.title:
				activity.log(self.project, self.name, "renamed", self.title)

	def on_trash(self):
		emit_issue_event("projex:issue_deleted", self)

	def _notify_assignees(self, reason, only=None):
		actor = frappe.session.user
		for row in self.assignees or []:
			if only is not None and row.user not in only:
				continue
			if row.user == actor:
				continue
			_create_notification(
				user=row.user, notification_type=reason, actor=actor,
				issue=self.name, snippet=f'Assigned you to "{self.title}"',
			)

	def _notify_status_change(self):
		actor = frappe.session.user
		recipients = {row.user for row in (self.assignees or [])}
		if self.reporter:
			recipients.add(self.reporter)
		status_label = frappe.db.get_value("Projex Status", self.status, "status_name") or self.status
		for user in recipients:
			if user and user != actor:
				_create_notification(
					user=user, notification_type="status", actor=actor,
					issue=self.name, snippet=f"moved to {status_label}",
				)


def _default_status_for(project):
	"""First 'unstarted' status scoped to the project, else a global default."""
	status = frappe.db.get_value(
		"Projex Status",
		{"project": project, "category": "unstarted"},
		"name",
		order_by="position asc",
	)
	if not status:
		status = frappe.db.get_value(
			"Projex Status", {"project": ["in", ["", None]], "category": "unstarted"},
			"name", order_by="position asc",
		)
	return status


def _next_rank(project):
	count = frappe.db.count("Projex Issue", {"project": project})
	# Sparse integer ranks as zero-padded strings keep lexicographic order.
	return str((count + 1) * 1000).zfill(12)


def _create_notification(user, notification_type, actor, issue, snippet):
	frappe.get_doc({
		"doctype": "Projex Notification",
		"user": user,
		"notification_type": notification_type,
		"actor": actor,
		"issue": issue,
		"snippet": snippet,
		"is_read": 0,
	}).insert(ignore_permissions=True)
	frappe.publish_realtime(
		"projex:notification", {"user": user, "issue": issue, "type": notification_type},
		user=user,
	)


# ---- row-level permission scoping (registered in hooks.py) ------------------
def get_permission_query_conditions(user=None):
	from projex.permissions import accessible_project_condition
	return accessible_project_condition(user, "`tabProjex Issue`.project")


def has_permission(doc, user=None, permission_type=None):
	from projex.permissions import user_can_access_project
	return user_can_access_project(doc.project, user)
