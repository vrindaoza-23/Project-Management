"""Phase 1 acceptance checks. Run:
    bench --site <site> execute projex.setup.verify.run
"""

import frappe

from projex import api
from projex.permissions import accessible_projects


def _ok(label, cond, extra=""):
	print(f"  [{'PASS' if cond else 'FAIL'}] {label}{(' - ' + extra) if extra else ''}")
	return bool(cond)


def run():
	results = []
	demo = "alice@projex.test"

	# 1. API reachable as a real member -------------------------------------
	frappe.set_user(demo)
	groups = api.get_my_issues()
	total_mine = sum(len(v) for v in groups.values())
	results.append(_ok("get_my_issues returns grouped issues", total_mine > 0, f"{total_mine} issues"))

	inbox = api.get_inbox("all")
	results.append(_ok("get_inbox returns notifications", isinstance(inbox, list)))

	roadmap = api.get_roadmap()
	results.append(_ok("get_roadmap returns project bars", len(roadmap) > 0, f"{len(roadmap)} bars"))

	status = api.integration_status()
	results.append(_ok("integration_status reports flags", set(status) == {"erpnext", "timesheet", "ai"}, str(status)))

	# 2. Member sees issues via permission-aware get_list -------------------
	member_visible = frappe.get_list("Projex Issue", limit=0, ignore_permissions=False)
	results.append(_ok("member can list issues (permission_query_conditions)", len(member_visible) > 0,
					   f"{len(member_visible)} visible"))

	# 3. Outsider is scoped out ---------------------------------------------
	outsider = "outsider@projex.test"
	if not frappe.db.exists("User", outsider):
		frappe.set_user("Administrator")
		frappe.get_doc({
			"doctype": "User", "email": outsider, "first_name": "Out", "last_name": "Sider",
			"send_welcome_email": 0, "user_type": "System User", "roles": [{"role": "Projex Member"}],
		}).insert(ignore_permissions=True)
		frappe.db.commit()
	frappe.set_user(outsider)
	allowed = accessible_projects(outsider)
	outsider_visible = frappe.get_list("Projex Issue", limit=0, ignore_permissions=False)
	results.append(_ok("outsider scoped out of all projects", allowed == set(), f"allowed={allowed}"))
	results.append(_ok("outsider sees zero issues", len(outsider_visible) == 0,
					   f"{len(outsider_visible)} visible"))

	# 4. Realtime emit path callable (no client, but must not error) --------
	frappe.set_user(demo)
	an_issue = frappe.db.get_value("Projex Issue", {"project": "BIL"}, "name")
	try:
		api.set_presence(an_issue)
		realtime_ok = True
	except Exception as e:  # noqa: BLE001
		realtime_ok = False
		print("    presence error:", e)
	results.append(_ok("set_presence (realtime) executes", realtime_ok))

	# 5. reorder_issue recomputes a rank ------------------------------------
	frappe.set_user("Administrator")
	issues = frappe.get_all("Projex Issue", filters={"project": "BIL"}, fields=["name"], limit=3)
	if len(issues) >= 3:
		res = api.reorder_issue(issues[2].name, before=issues[0].name, after=issues[1].name)
		results.append(_ok("reorder_issue returns new rank", bool(res.get("rank")), res.get("rank")))

	frappe.set_user("Administrator")
	print(f"\n{sum(results)}/{len(results)} checks passed.")
	return all(results)
