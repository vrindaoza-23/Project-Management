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

	# ---- timesheets + finance ----------------------------------------------
	def test_timesheets_native_analytics(self):
		# Native flow-time analytics + native (in-app) time logs, no ERPNext needed.
		ts = api.get_project_timesheets("QAP")
		self.assertEqual(set(ts["auto"]), {"per_status", "avg_lead_days", "avg_cycle_days", "completed"})
		self.assertTrue(ts["logged"]["available"])
		for k in ("total_hours", "billable_hours", "by_user", "by_issue", "entries"):
			self.assertIn(k, ts["logged"])

	def test_create_and_delete_time_log(self):
		before = api.get_project_timesheets("QAP")["logged"]["total_hours"]
		res = api.create_time_log(issue=self.a.name, hours=2.5, activity="Dev", is_billable=1)
		after = api.get_project_timesheets("QAP")["logged"]
		self.assertEqual(after["total_hours"], before + 2.5)
		self.assertTrue(any(e["name"] == res["name"] for e in after["entries"]))
		api.delete_time_log(res["name"])
		self.assertEqual(api.get_project_timesheets("QAP")["logged"]["total_hours"], before)

	def test_erpnext_link_options_gated(self):
		# Manager gets a (possibly empty) options payload; non-manager is refused.
		opts = api.erpnext_link_options("QAP")
		self.assertIn("projects", opts)
		self.assertIn("customers", opts)
		u = self._mk_user("qa_link_outsider@example.com")
		frappe.set_user(u)
		with self.assertRaises(frappe.PermissionError):
			api.erpnext_link_options("QAP")
		frappe.set_user("Administrator")

	def test_finance_requires_link_and_manage(self):
		# No ERPNext project linked → graceful, not an error (as manager/Administrator).
		fin = api.get_project_finance("QAP")
		self.assertFalse(fin["available"])
		# A non-manager is refused outright.
		u = self._mk_user("qa_fin_outsider@example.com")
		frappe.set_user(u)
		with self.assertRaises(frappe.PermissionError):
			api.get_project_finance("QAP")
		frappe.set_user("Administrator")

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
		outsider = self._mk_user("qa_outsider_api@example.com")
		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			api.invite_user("newbie_api@example.com", "QAP")
		frappe.set_user("Administrator")

	# ---- access control: strict per-project + role/admin gating ------------
	def _mk_user(self, email):
		if not frappe.db.exists("User", email):
			frappe.get_doc({
				"doctype": "User", "email": email, "first_name": "QA",
				"send_welcome_email": 0, "user_type": "System User",
				"roles": [{"role": "Projex Member"}],
			}).insert(ignore_permissions=True)
		return email

	def test_access_is_strictly_per_project(self):
		"""Workspace membership must NOT grant access to the workspace's projects."""
		from projex.permissions import accessible_projects

		u = self._mk_user("qa_ws_only@example.com")
		ws = frappe.get_doc({
			"doctype": "Projex Workspace", "workspace_name": "QA WS Strict", "icon": "box",
			"members": [{"user": u, "role": "Member"}],
		}).insert(ignore_permissions=True)
		proj = frappe.get_doc({
			"doctype": "Projex Project", "project_name": "QA WS Proj", "key": "QWSP",
			"workspace": ws.name,
		}).insert(ignore_permissions=True)
		try:
			self.assertNotIn(proj.name, accessible_projects(u))
		finally:
			frappe.delete_doc("Projex Project", proj.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Projex Workspace", ws.name, force=True, ignore_permissions=True)
			frappe.db.commit()

	def test_update_member_role_requires_manage(self):
		u = self._mk_user("qa_member_only@example.com")
		api.add_member("Projex Project", "QAP", u, "Member")
		try:
			frappe.set_user(u)  # plain Member cannot manage
			with self.assertRaises(frappe.PermissionError):
				api.update_member_role("Projex Project", "QAP", u, "Admin")
		finally:
			frappe.set_user("Administrator")
			api.remove_member("Projex Project", "QAP", u)

	# ---- aging + rework counters -------------------------------------------
	def test_status_change_counters(self):
		iss = self._issue("Aging counters", _status("Todo"))
		try:
			self.assertTrue(frappe.db.get_value("Projex Issue", iss.name, "status_changed_on"))

			def move(to):
				d = frappe.get_doc("Projex Issue", iss.name)
				d.status = _status(to)
				d.save(ignore_permissions=True)

			move("In review")    # forward
			move("In progress")  # backward → rework
			self.assertEqual(frappe.db.get_value("Projex Issue", iss.name, "rework_count"), 1)
			self.assertEqual(frappe.db.get_value("Projex Issue", iss.name, "reopen_count"), 0)

			move("Done")         # forward
			move("Todo")         # reopened from done
			self.assertEqual(frappe.db.get_value("Projex Issue", iss.name, "reopen_count"), 1)

			rep = api.get_project_reports("QAP")
			self.assertIn("aging", rep)
			self.assertIn("rework", rep)
			self.assertEqual(set(rep["aging"]), {"le3", "d4_7", "d8_14", "gt14"})
		finally:
			frappe.delete_doc("Projex Issue", iss.name, force=True, ignore_permissions=True)

	# ---- sprint lifecycle: complete_sprint carryover -----------------------
	def test_complete_sprint_carryover(self):
		# Two cycles; put the open issue (a) and the done issue (b) into c1.
		c1 = api.create_cycle("QAP", "Sprint A", state="Active")["name"]
		c2 = api.create_cycle("QAP", "Sprint B", state="Upcoming")["name"]
		api.update_issue(self.a.name, frappe.as_json({"cycle": c1}))
		api.update_issue(self.b.name, frappe.as_json({"cycle": c1}))
		try:
			# Complete → unfinished (a) goes to backlog, done (b) stays, state Completed.
			res = api.complete_sprint(c1, carryover_to=None)
			self.assertEqual(res["done"], 1)
			self.assertEqual(res["carried"], 1)
			self.assertIsNone(frappe.db.get_value("Projex Issue", self.a.name, "cycle"))
			self.assertEqual(frappe.db.get_value("Projex Issue", self.b.name, "cycle"), c1)
			self.assertEqual(frappe.db.get_value("Projex Cycle", c1, "state"), "Completed")

			# Carryover into another sprint.
			api.update_issue(self.a.name, frappe.as_json({"cycle": c2}))
			res2 = api.complete_sprint(c2, carryover_to=c1)
			self.assertEqual(frappe.db.get_value("Projex Issue", self.a.name, "cycle"), c1)
		finally:
			frappe.set_user("Administrator")
			api.update_issue(self.a.name, frappe.as_json({"cycle": None}))
			api.update_issue(self.b.name, frappe.as_json({"cycle": None}))
			api.delete_cycle(c1)
			api.delete_cycle(c2)

	def test_complete_sprint_requires_manage(self):
		c = api.create_cycle("QAP", "Sprint Gate", state="Active")["name"]
		u = self._mk_user("qa_sprint_outsider@example.com")
		try:
			frappe.set_user(u)
			with self.assertRaises(frappe.PermissionError):
				api.complete_sprint(c)
		finally:
			frappe.set_user("Administrator")
			api.delete_cycle(c)

	def test_set_all_access_requires_super(self):
		from projex.permissions import accessible_projects

		mgr = self._mk_user("qa_proj_admin@example.com")
		target = self._mk_user("qa_target@example.com")
		api.add_member("Projex Project", "QAP", mgr, "Admin")
		try:
			frappe.set_user(mgr)  # project admin is NOT allowed to grant all-access
			with self.assertRaises(frappe.PermissionError):
				api.set_all_access(target, 1)
			frappe.set_user("Administrator")  # a super user is
			api.set_all_access(target, 1)
			self.assertIsNone(accessible_projects(target))
			api.set_all_access(target, 0)
			self.assertIsNotNone(accessible_projects(target))
		finally:
			frappe.set_user("Administrator")
			api.remove_member("Projex Project", "QAP", mgr)
