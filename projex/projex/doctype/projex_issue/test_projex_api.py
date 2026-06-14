# Copyright (c) 2026, Projex and Contributors
# See license.txt

import frappe
from frappe.tests.classes.unit_test_case import UnitTestCase

from projex import api
from projex.setup import defaults


def _status(name):
	return frappe.db.get_value("Projex Status", {"status_name": name, "project": ["in", ["", None]]})


class IntegrationTestProjexApi(UnitTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		defaults.run()  # roles + global statuses (mirrors install)
		# fresh project
		if frappe.db.exists("Projex Project", "QAP"):
			frappe.db.delete("Projex Issue", {"project": "QAP"})
			frappe.delete_doc("Projex Project", "QAP", force=True, ignore_permissions=True)
		frappe.get_doc({"doctype": "Projex Project", "project_name": "QA API", "key": "QAP"}).insert(
			ignore_permissions=True
		)
		cls.a = cls._issue("First", _status("In progress"))
		cls.b = cls._issue("Second", _status("Done"))
		frappe.db.commit()

	@classmethod
	def _issue(cls, title, status):
		return frappe.get_doc({
			"doctype": "Projex Issue", "title": title, "project": "QAP", "status": status,
		}).insert(ignore_permissions=True)

	def setUp(self):
		frappe.set_user("Administrator")

	# ---- install defaults ---------------------------------------------------
	def test_default_statuses_exist(self):
		self.assertTrue(_status("Todo"))
		self.assertTrue(_status("Done"))
		self.assertTrue(frappe.db.exists("Role", "Projex Member"))

	# ---- summary / reports / gantt -----------------------------------------
	def test_summary(self):
		s = api.get_project_summary("QAP")
		self.assertEqual(set(s["cards"]), {"completed", "updated", "created", "due_soon"})
		self.assertTrue(len(s["status_breakdown"]) >= 1)

	def test_reports(self):
		r = api.get_project_reports("QAP")
		self.assertEqual(len(r["throughput"]), 6)
		self.assertIn("avg_cycle_time", r)

	def test_gantt(self):
		g = api.get_gantt("QAP")
		self.assertTrue(all({"id", "start", "end", "progress"} <= set(t) for t in g))

	# ---- favorites / links / views -----------------------------------------
	def test_favorite_toggle(self):
		self.assertTrue(api.toggle_favorite("QAP")["favorite"])
		self.assertFalse(api.toggle_favorite("QAP")["favorite"])

	def test_issue_link_roundtrip(self):
		res = api.add_issue_link(self.a.name, "blocks", self.b.name)
		detail = api.get_issue(self.a.name)
		self.assertTrue(any(x["name"] == res["name"] for x in detail["links"]))
		api.remove_issue_link(res["name"])

	def test_saved_view_roundtrip(self):
		v = api.save_view("QAP", "Test view", "list", frappe.as_json({"sortBy": "due"}))
		self.assertTrue(any(x["name"] == v["name"] for x in api.get_views("QAP")))
		api.delete_view(v["name"])

	# ---- security: field allowlist -----------------------------------------
	def test_update_issue_ignores_disallowed_fields(self):
		original_id = self.a.issue_id
		api.update_issue(self.a.name, frappe.as_json({"issue_id": "HACK-999", "title": "Renamed"}))
		row = frappe.db.get_value("Projex Issue", self.a.name, ["issue_id", "title"], as_dict=True)
		self.assertEqual(row.issue_id, original_id)  # protected
		self.assertEqual(row.title, "Renamed")  # allowed

	# ---- security: invite gating -------------------------------------------
	def test_invite_requires_project_admin(self):
		outsider = "qa_outsider_api@example.com"
		if not frappe.db.exists("User", outsider):
			frappe.get_doc({
				"doctype": "User", "email": outsider, "first_name": "QA",
				"send_welcome_email": 0, "user_type": "System User",
				"roles": [{"role": "Projex Member"}],
			}).insert(ignore_permissions=True)
		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			api.invite_user("newbie_api@example.com", "QAP")
		frappe.set_user("Administrator")
