"""Verify market-parity endpoints. Run:
	bench --site <site> execute projex.setup.verify_market.run
"""

import frappe
from projex import api

results = []


def check(label, cond, extra=""):
	ok = bool(cond)
	results.append(ok)
	print(f"  [{'PASS' if ok else 'FAIL'}] {label}{(' — ' + str(extra)) if extra else ''}")


def run():
	results.clear()
	frappe.set_user("alice@projex.test")

	# generate activity
	api.update_issue("BIL-1", frappe.as_json({"priority": "Medium"}))

	s = api.get_project_summary("BIL")
	check("summary cards", set(s["cards"]) == {"completed", "updated", "created", "due_soon"}, s["cards"])
	check("summary status donut", len(s["status_breakdown"]) > 0, f"{len(s['status_breakdown'])} slices")
	check("summary activity feed", len(s["activity"]) > 0, f"{len(s['activity'])} events")

	r = api.get_project_reports("BIL")
	check("reports distribution", len(r["distribution"]) == 6)
	check("reports velocity per cycle", len(r["velocity"]) >= 1, f"{len(r['velocity'])} cycles")
	check("reports throughput 6wk", len(r["throughput"]) == 6)
	check("reports avg cycle time present", "avg_cycle_time" in r, r["avg_cycle_time"])

	f1 = api.toggle_favorite("BIL")
	check("favorite on", f1["favorite"] is True)
	f2 = api.toggle_favorite("BIL")
	check("favorite off (toggle)", f2["favorite"] is False)

	lk = api.add_issue_link("BIL-1", "blocks", "BIL-2")
	d = api.get_issue("BIL-1")
	check("issue link added + in get_issue", any(x["name"] == lk["name"] for x in d["links"]))
	check("get_issue exposes attachments", "attachments" in d)
	api.remove_issue_link(lk["name"])

	v = api.save_view("BIL", "My urgent", "list", frappe.as_json({"statusFilter": [], "sortBy": "priority"}))
	views = api.get_views("BIL")
	check("saved view persists", any(x["name"] == v["name"] for x in views))
	api.delete_view(v["name"])

	frappe.set_user("Administrator")
	print(f"\n{sum(results)}/{len(results)} market checks passed.")
	return all(results)
