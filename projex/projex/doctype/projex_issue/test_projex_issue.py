# Copyright (c) 2026, Projex and Contributors
# See license.txt

import frappe
from frappe.tests.classes.unit_test_case import UnitTestCase

from projex import api
from projex.permissions import accessible_projects

# UnitTestCase doesn't generate Frappe test records, so it won't recurse into
# ERPNext's (Company/Fiscal Year) test bootstrap on a site where ERPNext is
# installed. Our tests build their own fixtures below.


def _ensure_status(name, category):
	existing = frappe.db.get_value("Projex Status", {"status_name": name, "project": ["in", ["", None]]})
	if existing:
		return existing
	return frappe.get_doc({
		"doctype": "Projex Status", "status_name": name, "category": category,
		"color_theme": "gray", "position": 0,
	}).insert(ignore_permissions=True).name


def _make_project(key):
	# Tests commit (controllers/API call db.commit) and UnitTestCase doesn't roll
	# back, so purge any prior issues for this key before recreating the project.
	if frappe.db.exists("Projex Project", key):
		frappe.db.delete("Projex Issue", {"project": key})
		frappe.delete_doc("Projex Project", key, force=True, ignore_permissions=True)
		frappe.db.commit()
	return frappe.get_doc({
		"doctype": "Projex Project", "project_name": f"Test {key}", "key": key,
	}).insert(ignore_permissions=True)


class IntegrationTestProjexIssue(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.todo = _ensure_status("Todo", "unstarted")
		cls.done = _ensure_status("Done", "completed")
		frappe.set_user("Administrator")

	def setUp(self):
		frappe.set_user("Administrator")

	def _new_issue(self, project, title, **kw):
		return frappe.get_doc({
			"doctype": "Projex Issue", "title": title, "project": project,
			"status": self.todo, **kw,
		}).insert(ignore_permissions=True)

	# 1. Per-project key naming ------------------------------------------------
	def test_autoname_per_project_key(self):
		p = _make_project("TST")
		a = self._new_issue(p.name, "First")
		b = self._new_issue(p.name, "Second")
		self.assertEqual(a.name, "TST-1")
		self.assertEqual(b.name, "TST-2")
		self.assertEqual(a.issue_id, "TST-1")

	def test_counter_isolated_between_projects(self):
		p1 = _make_project("AAA")
		p2 = _make_project("BBB")
		self._new_issue(p1.name, "x")
		i2 = self._new_issue(p2.name, "y")
		self.assertEqual(i2.name, "BBB-1")

	# 2. Project key validation -----------------------------------------------
	def test_invalid_key_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({
				"doctype": "Projex Project", "project_name": "Bad", "key": "TOOLONG",
			}).insert(ignore_permissions=True)

	# 3. Notifications on assignment ------------------------------------------
	def test_assignment_creates_notification(self):
		p = _make_project("NOT")
		user = frappe.db.get_value(
			"User", {"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator"]]}, "name"
		) or "Administrator"
		i = self._new_issue(p.name, "Assign me", assignees=[{"user": user}])
		count = frappe.db.count(
			"Projex Notification", {"issue": i.name, "notification_type": "assigned"}
		)
		if user != "Administrator":
			self.assertGreaterEqual(count, 1)

	# 4. Permission scoping ----------------------------------------------------
	def test_outsider_scoped_out(self):
		p = _make_project("SEC")
		self._new_issue(p.name, "secret")
		outsider = "projex_outsider@example.com"
		if not frappe.db.exists("User", outsider):
			frappe.get_doc({
				"doctype": "User", "email": outsider, "first_name": "Out",
				"send_welcome_email": 0, "user_type": "System User",
				"roles": [{"role": "Projex Member"}],
			}).insert(ignore_permissions=True)
		frappe.set_user(outsider)
		self.assertEqual(accessible_projects(outsider), set())
		visible = frappe.get_list(
			"Projex Issue", filters={"project": p.name}, ignore_permissions=False
		)
		self.assertEqual(len(visible), 0)
		frappe.set_user("Administrator")

	# 5. Reorder produces a midpoint rank -------------------------------------
	def test_reorder_midpoint(self):
		p = _make_project("RNK")
		a = self._new_issue(p.name, "a")
		self._new_issue(p.name, "b")
		c = self._new_issue(p.name, "c")
		res = api.reorder_issue(c.name, before=None, after=a.name)
		self.assertTrue(res["rank"])
		a_rank = int(frappe.db.get_value("Projex Issue", a.name, "rank"))
		self.assertGreater(int(res["rank"]), a_rank)
