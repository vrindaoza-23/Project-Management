# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document

from projex.realtime import emit_comment_event

MENTION_RE = re.compile(r"@([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")


class ProjexComment(Document):
	def after_insert(self):
		from projex import activity
		project = frappe.db.get_value("Projex Issue", self.issue, "project")
		emit_comment_event("projex:comment", self, project)
		activity.log(project, self.issue, "commented", "")
		self._notify_participants(project)

	def _notify_participants(self, project):
		actor = frappe.session.user
		issue = frappe.get_doc("Projex Issue", self.issue)
		# Explicit @mentions (by email) get a 'mention' notification.
		mentioned = set(MENTION_RE.findall(self.content or ""))
		# Everyone else on the issue gets a 'comment' notification.
		participants = {row.user for row in (issue.assignees or [])}
		if issue.reporter:
			participants.add(issue.reporter)

		for user in mentioned:
			if user != actor and frappe.db.exists("User", user):
				_notify(user, "mention", actor, self.issue, "Mentioned you in a comment")

		for user in participants - mentioned:
			if user and user != actor:
				_notify(user, "comment", actor, self.issue, "Commented on this issue")


def _notify(user, ntype, actor, issue, snippet):
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


def get_permission_query_conditions(user=None):
	from projex.permissions import accessible_projects
	user = user or frappe.session.user
	projects = accessible_projects(user)
	if projects is None:
		return ""
	if not projects:
		return "1=0"
	quoted = ", ".join(frappe.db.escape(p) for p in projects)
	# Comments are visible if their issue belongs to an accessible project.
	return (
		"`tabProjex Comment`.issue IN "
		f"(SELECT name FROM `tabProjex Issue` WHERE project IN ({quoted}))"
	)
