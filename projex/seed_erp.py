# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Seed ONE realistic, end-to-end ERP-implementation project for manual testing.

Creates a delivery-lead user (SPA), a consultant, and a client contact (portal),
a customer + rate card, a full delivery plan from the ERPNext Implementation
template with lifelike progress (a signed-off + invoiced milestone, one awaiting
the client, tasks done/in-progress, billable time logged), and grants the client
portal access.

Run:    bench --site <site> execute projex.seed_erp.run
Remove: bench --site <site> execute projex.seed_erp.remove

NOT production data — a demo engagement you can log into and click through.
"""

import frappe
from frappe.utils import add_days, get_datetime, now, today
from frappe.utils.password import update_password

KEY = "ERP"
PROJECT_NAME = "Contoso ERP Implementation"
WORKSPACE = "Contoso"
CUSTOMER = "Contoso Ltd"

LEAD = ("lead@contoso-erp.test", "Priya", "Nair", "Lead@12345")
CONSULTANT = ("consultant@contoso-erp.test", "Sam", "Verma", "Consult@12345")
CLIENT = ("client@contoso.test", "Dana", "Fox", "Client@12345")


def _ensure_user(email, first, last, pwd, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc({
			"doctype": "User", "email": email, "first_name": first, "last_name": last,
			"send_welcome_email": 0, "enabled": 1, "roles": [{"role": r} for r in roles],
		}).insert(ignore_permissions=True)
	else:
		u = frappe.get_doc("User", email)
		have = {r.role for r in u.roles}
		for r in roles:
			if r not in have:
				u.append("roles", {"role": r})
		u.save(ignore_permissions=True)
	update_password(email, pwd)


def _ensure_customer():
	if frappe.db.exists("Customer", CUSTOMER):
		return
	frappe.get_doc({
		"doctype": "Customer", "customer_name": CUSTOMER,
		"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups",
		"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
	}).insert(ignore_permissions=True)


def _wipe_project():
	"""Delete the demo project and everything under it (idempotent re-seed)."""
	for dt in ("Projex Time Log", "Projex Comment", "Projex Deliverable",
			   "Projex Milestone", "Projex Phase", "Projex Issue"):
		field = "issue" if dt == "Projex Comment" else "project"
		if dt == "Projex Comment":
			names = frappe.get_all(
				"Projex Comment",
				filters={"issue": ["in", frappe.get_all("Projex Issue", {"project": KEY}, pluck="name") or [""]]},
				pluck="name",
			)
		else:
			names = frappe.get_all(dt, filters={"project": KEY}, pluck="name")
		for n in names:
			frappe.delete_doc(dt, n, ignore_permissions=True, force=True)
	for n in frappe.get_all("Projex Client Access", filters={"project": KEY}, pluck="name"):
		frappe.delete_doc("Projex Client Access", n, ignore_permissions=True, force=True)
	if frappe.db.exists("Projex Project", KEY):
		frappe.delete_doc("Projex Project", KEY, ignore_permissions=True, force=True)


def run():
	frappe.set_user("Administrator")
	from projex import billing, delivery, portal
	from projex import project_templates as pt

	# --- people ---
	_ensure_user(*LEAD, ["Projex Admin", "Projex Member"])
	_ensure_user(*CONSULTANT, ["Projex Member"])
	_ensure_user(*CLIENT, ["Projex Client"])
	_ensure_customer()

	# --- workspace ---
	ws = frappe.db.get_value("Projex Workspace", {"workspace_name": WORKSPACE}, "name")
	if not ws:
		ws = frappe.get_doc({
			"doctype": "Projex Workspace", "workspace_name": WORKSPACE, "icon": "building-2",
			"description": "Contoso ERP rollout engagement",
			"members": [{"user": LEAD[0], "role": "Admin"}, {"user": CONSULTANT[0], "role": "Member"}],
		}).insert(ignore_permissions=True).name

	# --- project (fresh) ---
	_wipe_project()
	frappe.get_doc({
		"doctype": "Projex Project", "project_name": PROJECT_NAME, "key": KEY, "workspace": ws,
		"status": "Active", "icon": "rocket", "color": "var(--violet-500)", "lead": LEAD[0],
		"description": "End-to-end ERPNext implementation for Contoso Ltd.",
		"contract_value": 1200000, "billing_currency": "INR", "erpnext_customer": CUSTOMER,
		"members": [{"user": LEAD[0], "role": "Admin"}, {"user": CONSULTANT[0], "role": "Member"}],
		"billing_rates": [
			{"role": "Project Manager", "rate": 12000},
			{"role": "Consultant", "rate": 8000},
			{"role": "Developer", "rate": 7000},
		],
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	# --- delivery plan from template, started 20 days ago ---
	start = add_days(today(), -20)
	pt.instantiate_template("ERPNext Implementation", KEY, start_date=start)

	phases = {p.phase_name: p.name for p in frappe.get_all(
		"Projex Phase", filters={"project": KEY}, fields=["name", "phase_name"])}
	frappe.db.set_value("Projex Phase", phases["Discovery"],
						{"status": "Completed", "actual_end_date": add_days(today(), -10)})
	frappe.db.set_value("Projex Phase", phases["Configuration"], "status", "In Progress")

	st = {s.status_name: s.name for s in frappe.get_all(
		"Projex Status", filters={"project": ["in", ["", None]]}, fields=["name", "status_name"])}

	# --- tasks: Discovery done, Configuration in-flight; assign + due realism ---
	tasks = frappe.get_all("Projex Issue", filters={"project": KEY},
						   fields=["name", "title", "phase"], order_by="creation asc")
	config_seen = 0
	for t in tasks:
		if t.phase == phases["Discovery"]:
			frappe.db.set_value("Projex Issue", t.name,
								{"status": st["Done"], "status_changed_on": now()})
			_assign(t.name, LEAD[0])
		elif t.phase == phases["Configuration"]:
			config_seen += 1
			if config_seen <= 2:
				frappe.db.set_value("Projex Issue", t.name, {"status": st["In progress"]})
			_assign(t.name, CONSULTANT[0])

	# --- billable time (unbilled, so 'Bill time' T&M is testable) ---
	from projex import api
	disc_tasks = [t.name for t in tasks if t.phase == phases["Discovery"]]
	conf_tasks = [t.name for t in tasks if t.phase == phases["Configuration"]]
	logs = [
		(disc_tasks[0], 6, "Project Manager", LEAD[0], -18, 1),
		(disc_tasks[1] if len(disc_tasks) > 1 else disc_tasks[0], 8, "Consultant", CONSULTANT[0], -17, 1),
		(disc_tasks[2] if len(disc_tasks) > 2 else disc_tasks[0], 5, "Consultant", CONSULTANT[0], -16, 1),
		(conf_tasks[0], 7, "Developer", CONSULTANT[0], -6, 1),
		(conf_tasks[1] if len(conf_tasks) > 1 else conf_tasks[0], 4, "Consultant", CONSULTANT[0], -3, 1),
		(conf_tasks[0], 2, "Consultant", LEAD[0], -2, 0),  # one non-billable
	]
	for issue, hours, role, who, days, billable in logs:
		api.create_time_log(issue=issue, hours=hours, spent_on=add_days(today(), days),
							 activity=role, is_billable=billable, user=who)

	# --- milestone 1: client-approved + invoiced ---
	ms = {m.milestone_name: m.name for m in frappe.get_all(
		"Projex Milestone", filters={"project": KEY}, fields=["name", "milestone_name"])}
	m1 = ms["Requirements sign-off"]
	for d in frappe.get_all("Projex Deliverable", filters={"milestone": m1}, pluck="name"):
		dd = frappe.get_doc("Projex Deliverable", d)
		dd.status = "Approved"
		dd.approved_by = CLIENT[0]
		dd.approved_on = get_datetime(add_days(today(), -9))
		dd.review_note = "Approved during kickoff review."
		dd.save(ignore_permissions=True)
	frappe.get_doc("Projex Milestone", m1).record_signoff("Approved", CLIENT[0], "Signed off at kickoff.")

	invoice = None
	try:
		invoice = billing.generate_milestone_invoice(m1).get("sales_invoice")
	except Exception:
		frappe.log_error("seed_erp: milestone invoice skipped")

	# --- milestone 2: delivered, awaiting the client ---
	m2 = ms["Configuration complete"]
	for d in frappe.get_all("Projex Deliverable", filters={"milestone": m2}, pluck="name"):
		frappe.db.set_value("Projex Deliverable", d, "status", "Submitted")
	delivery.request_signoff(m2)

	# --- a comment for life ---
	if disc_tasks:
		frappe.get_doc({
			"doctype": "Projex Comment", "issue": disc_tasks[0],
			"content": "<p>Kickoff complete — chart of accounts structure agreed with Contoso finance.</p>",
		}).insert(ignore_permissions=True)

	# --- client portal access ---
	portal.grant_client_access(KEY, CLIENT[0])
	frappe.db.commit()

	base = f"http://{frappe.local.site}:8000"
	print("\n" + "=" * 64)
	print("  Contoso ERP Implementation — seeded")
	print("=" * 64)
	print(f"  Project:   {PROJECT_NAME}  (key {KEY})  workspace: {WORKSPACE}")
	print(f"  Phases:    {frappe.db.count('Projex Phase', {'project': KEY})}"
		  f"  Tasks: {frappe.db.count('Projex Issue', {'project': KEY})}"
		  f"  Milestones: {frappe.db.count('Projex Milestone', {'project': KEY})}"
		  f"  Time logs: {frappe.db.count('Projex Time Log', {'project': KEY})}")
	print(f"  Milestone 1 invoice (draft): {invoice or 'skipped'}")
	print("-" * 64)
	print("  APP (delivery lead):  " + base + "/projex")
	print(f"      login: {LEAD[0]}  /  {LEAD[3]}")
	print("  CLIENT PORTAL:        " + base + "/projex-portal")
	print(f"      login: {CLIENT[0]}  /  {CLIENT[3]}")
	print(f"  (consultant login: {CONSULTANT[0]} / {CONSULTANT[3]})")
	print("=" * 64 + "\n")


def _assign(issue, user):
	doc = frappe.get_doc("Projex Issue", issue)
	if user not in {a.user for a in doc.assignees}:
		doc.append("assignees", {"user": user})
		doc.save(ignore_permissions=True)


def remove():
	"""Tear down everything this seed created (project, users, workspace, customer)."""
	frappe.set_user("Administrator")
	_wipe_project()
	# draft invoices raised for the project's customer by the seed
	for si in frappe.get_all("Sales Invoice", filters={"customer": CUSTOMER, "docstatus": 0}, pluck="name"):
		frappe.delete_doc("Sales Invoice", si, ignore_permissions=True, force=True)
	ws = frappe.db.get_value("Projex Workspace", {"workspace_name": WORKSPACE}, "name")
	if ws:
		frappe.delete_doc("Projex Workspace", ws, ignore_permissions=True, force=True)
	if frappe.db.exists("Customer", CUSTOMER):
		try:
			frappe.delete_doc("Customer", CUSTOMER, ignore_permissions=True, force=True)
		except Exception:
			pass
	for email, *_ in (LEAD, CONSULTANT, CLIENT):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, ignore_permissions=True, force=True)
	frappe.db.commit()
	print("Removed Contoso ERP demo (project, users, workspace, customer, draft invoices).")
