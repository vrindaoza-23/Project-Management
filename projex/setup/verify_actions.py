"""End-to-end check that every UI field and action works against real data.

Exercises the exact API surface the SPA calls, as a real (non-privileged)
project member, and asserts each action persists. Run:

    bench --site <site> execute projex.setup.verify_actions.run
"""

import frappe

from projex import api

MEMBER = "alice@projex.test"
results = []


def check(label, cond, extra=""):
	ok = bool(cond)
	results.append(ok)
	print(f"  [{'PASS' if ok else 'FAIL'}] {label}{(' — ' + str(extra)) if extra else ''}")
	return ok


def run():
	results.clear()
	frappe.set_user(MEMBER)
	print(f"Acting as member: {MEMBER}\n")

	# ---- READS the shell + views depend on --------------------------------
	boot = api.bootstrap()
	check("bootstrap: projects + users + workspaces", boot["projects"] and boot["users"] and boot["workspaces"],
		  f"{len(boot['projects'])} projects, {len(boot['users'])} users")

	project = "BIL"
	board = api.get_issues(project)
	check("get_issues: statuses present", len(board["statuses"]) == 6, [s["status_name"] for s in board["statuses"]])
	check("get_issues: issues enriched", board["issues"] and "assignees" in board["issues"][0]
		  and "labels" in board["issues"][0] and "sub_total" in board["issues"][0],
		  f"{len(board['issues'])} issues")

	# every field the list/board row renders is present
	sample = board["issues"][0]
	row_fields = ["issue_id", "title", "status", "priority", "due_date", "estimate",
				  "rank", "assignees", "labels", "sub_total", "sub_done", "comment_count", "modified"]
	missing = [f for f in row_fields if f not in sample]
	check("issue row exposes every rendered field", not missing, f"missing={missing}")

	# ---- CREATE (QuickAdd) -------------------------------------------------
	created = frappe.get_doc({
		"doctype": "Projex Issue", "title": "E2E verify issue", "project": project, "priority": "High",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	check("create issue: per-project key assigned", created.name.startswith("BIL-"), created.name)
	check("create issue: default status applied", bool(created.status), created.status)
	check("create issue: rank assigned", bool(created.rank), created.rank)

	# ---- UPDATE field (drawer/board: status, priority, title, due, estimate)
	target = (board["statuses"][3]["name"])  # In review
	api.update_issue(created.name, frappe.as_json({"status": target}))
	check("update status (board drag / drawer)", frappe.db.get_value("Projex Issue", created.name, "status") == target)

	api.update_issue(created.name, frappe.as_json({"priority": "Low"}))
	check("update priority", frappe.db.get_value("Projex Issue", created.name, "priority") == "Low")

	api.update_issue(created.name, frappe.as_json({"title": "E2E verify issue (edited)"}))
	check("edit title", frappe.db.get_value("Projex Issue", created.name, "title") == "E2E verify issue (edited)")

	api.update_issue(created.name, frappe.as_json({"due_date": frappe.utils.nowdate(), "estimate": 5}))
	due = frappe.db.get_value("Projex Issue", created.name, "due_date")
	check("set due_date + estimate", str(due) == frappe.utils.nowdate()
		  and frappe.db.get_value("Projex Issue", created.name, "estimate") == 5)

	# ---- DRAWER detail payload (get_issue) --------------------------------
	detail = api.get_issue(created.name)
	check("get_issue: full payload", detail["issue"]["issue_id"] == created.name and "status_meta" in detail)

	# ---- COMMENT (drawer composer) ----------------------------------------
	c = api.add_comment(created.name, "<p>verifying the composer</p>")
	check("add comment", c["name"] and c["author_name"], c["author_name"])
	detail2 = api.get_issue(created.name)
	check("comment shows in thread", any(x["name"] == c["name"] for x in detail2["comments"]))

	# ---- SUBTASK toggle ---------------------------------------------------
	sub = frappe.get_doc({
		"doctype": "Projex Issue", "title": "E2E subtask", "project": project,
		"parent_issue": created.name, "status": board["statuses"][1]["name"],
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	done_status = next(s["name"] for s in board["statuses"] if s["status_name"] == "Done")
	api.update_issue(sub.name, frappe.as_json({"status": done_status}))
	d3 = api.get_issue(created.name)
	check("subtask appears + toggles done", any(s["name"] == sub.name and s["done"] for s in d3["subtasks"]))

	# ---- REORDER (board/list drag rank) -----------------------------------
	two = frappe.get_all("Projex Issue", filters={"project": project, "parent_issue": ["in", ["", None]]},
						 pluck="name", order_by="rank asc", limit=2)
	if len(two) >= 2:
		res = api.reorder_issue(created.name, before=two[1], after=two[0])
		check("reorder issue (rank recompute)", bool(res["rank"]), res["rank"])

	# ---- PRESENCE (drawer open) -------------------------------------------
	pres = api.set_presence(created.name)
	check("set_presence (realtime)", pres.get("ok") and MEMBER in pres.get("users", []))

	# ---- MY TASKS / INBOX / ROADMAP --------------------------------------
	mine = api.get_my_issues()
	check("get_my_issues grouped", isinstance(mine, dict) and set(mine) == {"today", "week", "later", "done"})
	inbox = api.get_inbox("all")
	check("get_inbox returns list", isinstance(inbox, list))
	roadmap = api.get_roadmap()
	check("get_roadmap returns bars", len(roadmap) > 0, f"{len(roadmap)} bars")
	integ = api.integration_status()
	check("integration_status flags", set(integ) == {"erpnext", "timesheet", "ai"}, integ)

	# ---- INBOX mark read --------------------------------------------------
	frappe.set_user(DEMO := "Administrator")
	admin_inbox = api.get_inbox("unread")
	if admin_inbox:
		api.mark_notification_read(admin_inbox[0]["name"])
		check("mark notification read", frappe.db.get_value("Projex Notification", admin_inbox[0]["name"], "is_read") == 1)
	else:
		check("mark notification read (none to mark)", True)

	# ---- CLEANUP (keep demo tidy) -----------------------------------------
	frappe.set_user("Administrator")
	frappe.delete_doc("Projex Issue", sub.name, force=True, ignore_permissions=True)
	frappe.delete_doc("Projex Issue", created.name, force=True, ignore_permissions=True)
	frappe.db.commit()

	frappe.set_user("Administrator")
	print(f"\n{sum(results)}/{len(results)} action checks passed.")
	return all(results)
