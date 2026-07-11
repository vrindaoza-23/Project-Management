# Copyright (c) 2026, Projex and Contributors
# See license.txt

"""Regression test for bulk_delete_issues.

An issue accrues linked records (Activity, Comment, Notification, Time Log,
Issue Link) and subtasks. A bare frappe.delete_doc refuses to delete it
(LinkExistsError), which used to make deleting any real task fail. This test
creates a task with those dependents and asserts the delete now succeeds and
cleans them up.
"""

import frappe
from frappe.tests import IntegrationTestCase

from projex import api


class TestIssueDelete(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.created = []

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self.created:
			if frappe.db.exists("Projex Issue", name):
				frappe.db.delete("Projex Comment", {"issue": name})
				frappe.db.delete("Projex Activity", {"issue": name})
				frappe.db.delete("Projex Notification", {"issue": name})
				frappe.delete_doc("Projex Issue", name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def _make_issue(self, title):
		issue = frappe.get_doc({
			"doctype": "Projex Issue", "project": "BIL", "title": title,
		}).insert(ignore_permissions=True)
		self.created.append(issue.name)
		return issue

	def test_delete_issue_with_activity_and_comment(self):
		issue = self._make_issue("ZZ delete-me with deps")
		# an Activity + Comment linked to the issue (the exact records that blocked delete)
		frappe.get_doc({
			"doctype": "Projex Activity", "project": "BIL", "issue": issue.name,
			"actor": "Administrator", "action": "created",
		}).insert(ignore_permissions=True)
		frappe.get_doc({
			"doctype": "Projex Comment", "issue": issue.name, "content": "<p>hi</p>",
		}).insert(ignore_permissions=True)
		frappe.db.commit()

		res = api.bulk_delete_issues(frappe.as_json([issue.name]))
		self.assertEqual(res["deleted"], 1)
		self.assertFalse(frappe.db.exists("Projex Issue", issue.name))
		# dependents cleaned up, not orphaned
		self.assertFalse(frappe.db.exists("Projex Activity", {"issue": issue.name}))
		self.assertFalse(frappe.db.exists("Projex Comment", {"issue": issue.name}))
		self.created.remove(issue.name)

	def test_delete_parent_detaches_subtask(self):
		parent = self._make_issue("ZZ parent")
		child = self._make_issue("ZZ child")
		frappe.db.set_value("Projex Issue", child.name, "parent_issue", parent.name)
		frappe.db.commit()

		api.bulk_delete_issues(frappe.as_json([parent.name]))
		self.assertFalse(frappe.db.exists("Projex Issue", parent.name))
		# the surviving subtask must not dangle a link to the deleted parent
		self.assertIsNone(frappe.db.get_value("Projex Issue", child.name, "parent_issue"))
		self.created.remove(parent.name)
