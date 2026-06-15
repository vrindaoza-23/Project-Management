# Copyright (c) 2026, Projex and Contributors
# See license.txt

"""Tests for the Scrum/PM layer: issue type, sprints (cycles), burndown,
the issues dashboard, the sprint review, project docs and project delete.

Uses UnitTestCase (not IntegrationTestCase) to avoid ERPNext's import-time
Fiscal Year bootstrap on this seeded site. The api methods commit, so every
test is written to be idempotent / self-cleaning.
"""

import frappe
from frappe.tests.classes.unit_test_case import UnitTestCase
from frappe.utils import add_days, nowdate

from projex import api
from projex.setup import defaults


def _global_status(name):
	return frappe.db.get_value("Projex Status", {"status_name": name, "project": ["in", ["", None]]})


class IntegrationTestProjexScrum(UnitTestCase):
	KEY = "QSC"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		defaults.run()  # roles + global statuses (mirrors install)
		cls._reset_project()
		cls.sprint = cls._sprint()
		cls.completed_issue = cls._issue("Completed one", _global_status("Done"), points=5, cycle=cls.sprint)
		cls.open_issue = cls._issue("Open one", _global_status("In progress"), points=3, cycle=cls.sprint)
		cls.bug = cls._issue("A bug", _global_status("Todo"), points=2, issue_type="Bug")
		frappe.db.commit()

	@classmethod
	def _reset_project(cls):
		if frappe.db.exists("Projex Project", cls.KEY):
			api.delete_project(cls.KEY)
		frappe.get_doc(
			{"doctype": "Projex Project", "project_name": "QA Scrum", "key": cls.KEY}
		).insert(ignore_permissions=True)

	@classmethod
	def _sprint(cls):
		doc = frappe.get_doc({
			"doctype": "Projex Cycle", "cycle_name": "Sprint 1", "project": cls.KEY,
			"start_date": add_days(nowdate(), -3), "end_date": add_days(nowdate(), 4), "state": "Active",
		}).insert(ignore_permissions=True)
		return doc.name

	@classmethod
	def _issue(cls, title, status, points=0, cycle=None, issue_type="Task"):
		return frappe.get_doc({
			"doctype": "Projex Issue", "title": title, "project": cls.KEY, "status": status,
			"estimate": points, "cycle": cycle, "issue_type": issue_type,
		}).insert(ignore_permissions=True)

	def setUp(self):
		frappe.set_user("Administrator")

	# ---- issue type (QA bug flow) ------------------------------------------
	def test_issue_type_is_editable(self):
		api.update_issue(self.open_issue.name, frappe.as_json({"issue_type": "Story"}))
		self.assertEqual(frappe.db.get_value("Projex Issue", self.open_issue.name, "issue_type"), "Story")
		api.update_issue(self.open_issue.name, frappe.as_json({"issue_type": "Task"}))

	# ---- sprints (cycles) ---------------------------------------------------
	def test_update_cycle_state(self):
		api.update_cycle(self.sprint, frappe.as_json({"state": "Completed"}))
		self.assertEqual(frappe.db.get_value("Projex Cycle", self.sprint, "state"), "Completed")
		api.update_cycle(self.sprint, frappe.as_json({"state": "Active"}))

	def test_burndown_series(self):
		burndown = api.get_burndown(self.KEY, self.sprint)
		self.assertEqual(burndown["total_points"], 8)  # 5 + 3 (bug not in sprint)
		self.assertEqual(len(burndown["series"]), 8)  # 7-day span -> 8 daily points
		self.assertEqual(burndown["series"][0]["ideal"], 8)
		self.assertEqual(burndown["series"][-1]["ideal"], 0)

	# ---- sprint review ------------------------------------------------------
	def test_sprint_review(self):
		review = api.get_sprint_review(self.KEY, self.sprint)
		self.assertEqual(review["total_issues"], 2)
		self.assertEqual(review["done_issues"], 1)
		self.assertEqual(review["total_points"], 8)
		self.assertEqual(review["done_points"], 5)
		self.assertEqual(len(review["carryover"]), 1)

	# ---- issues dashboard ---------------------------------------------------
	def test_issues_dashboard(self):
		dashboard = api.get_issues_dashboard(self.KEY)
		self.assertEqual(dashboard["total"], 3)
		type_counts = {row["label"]: row["count"] for row in dashboard["by_type"]}
		self.assertEqual(type_counts.get("Bug"), 1)
		self.assertTrue(any(bug["issue_id"] == self.bug.issue_id for bug in dashboard["open_bugs"]))

	# ---- project docs (PRD / BRD / MOM) ------------------------------------
	def test_doc_crud(self):
		created = api.create_doc(self.KEY, "Product PRD", "PRD", "# Overview")
		name = created["name"]
		self.assertTrue(any(doc["name"] == name for doc in api.get_docs(self.KEY)))
		api.update_doc(name, frappe.as_json({"content": "# Updated"}))
		self.assertIn("Updated", api.get_doc_detail(name)["content"])
		self.assertEqual(len(api.get_docs(self.KEY, "BRD")), 0)  # type filter
		api.delete_doc_entry(name)
		self.assertFalse(frappe.db.exists("Projex Doc", name))

	# ---- project delete (cascade) ------------------------------------------
	def test_delete_project_cascades(self):
		key = "QDEL"
		if frappe.db.exists("Projex Project", key):
			api.delete_project(key)
		frappe.get_doc(
			{"doctype": "Projex Project", "project_name": "Delete me", "key": key}
		).insert(ignore_permissions=True)
		issue = self._child_issue(key)
		api.delete_project(key)
		self.assertFalse(frappe.db.exists("Projex Project", key))
		self.assertFalse(frappe.db.exists("Projex Issue", issue))

	def _child_issue(self, key):
		doc = frappe.get_doc({
			"doctype": "Projex Issue", "title": "throwaway", "project": key,
			"status": _global_status("Todo"),
		}).insert(ignore_permissions=True)
		return doc.name
