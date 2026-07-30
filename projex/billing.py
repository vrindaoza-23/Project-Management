# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Invoice generation for the three partner billing models.

  - Fixed / milestone:  bill a milestone's fixed amount (or percent of contract).
  - Time & Materials:   bill unbilled billable time at role rates from the rate card.
  - Retainer / AMC:     bill a recurring milestone amount (partner repeats monthly).

Everything is created as an ERPNext Sales Invoice **draft** (docstatus 0) — the
partner reviews and submits it in ERPNext. All ERPNext access is guarded so the
module imports cleanly on a plain Frappe site, and no double-billing: milestones
carry `invoiced`, time logs carry `billed`.
"""

import frappe

from projex.api import _can_manage_project, _company_currency, _erpnext_installed


def _require_billing_ready(project):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if not _erpnext_installed():
		frappe.throw("ERPNext is not installed; invoicing is unavailable.")
	pr = frappe.db.get_value(
		"Projex Project", project, ["erpnext_customer", "contract_value", "billing_currency"], as_dict=True
	) or frappe._dict()
	if not pr.erpnext_customer:
		frappe.throw("Link an ERPNext Customer to this project before invoicing.")
	return pr


def _income_account(company):
	"""Resolve an income account for invoice lines: company default, else any
	non-group Income account for the company. Returns None if none exists."""
	if not company:
		return None
	acc = frappe.db.get_value("Company", company, "default_income_account")
	if acc:
		return acc
	return (
		frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Income Account", "is_group": 0},
			"name",
		)
		or frappe.db.get_value(
			"Account", {"company": company, "root_type": "Income", "is_group": 0}, "name"
		)
	)


def _new_sales_invoice(customer, currency, project_label):
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	company = frappe.defaults.get_global_default("company")
	if company:
		si.company = company
	if currency:
		si.currency = currency
	si.due_date = frappe.utils.add_days(frappe.utils.nowdate(), 15)
	si.remarks = f"Projex — {project_label}"
	si._projex_income_account = _income_account(company)
	return si


def _add_line(si, item_name, description, qty, rate):
	row = {"item_name": item_name[:140], "description": description, "qty": qty, "rate": rate}
	if getattr(si, "_projex_income_account", None):
		row["income_account"] = si._projex_income_account
	si.append("items", row)


# --------------------------------------------------------------------------- #
# Fixed / milestone  (and Retainer, same shape)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def generate_milestone_invoice(milestone):
	"""Create a draft Sales Invoice for a Fixed or Retainer milestone."""
	ms = frappe.get_doc("Projex Milestone", milestone)
	pr = _require_billing_ready(ms.project)
	if ms.invoiced:
		frappe.throw(f"Milestone already invoiced on {ms.sales_invoice}.")
	if ms.billing_type not in ("Fixed", "Retainer"):
		frappe.throw("Only Fixed or Retainer milestones bill a milestone amount. Use T&M billing for time.")

	amount = ms.billing_amount
	if not amount and ms.billing_percent and pr.contract_value:
		amount = round(pr.contract_value * ms.billing_percent / 100.0, 2)
	if not amount:
		frappe.throw("Set a billing amount (or percent + project contract value) on the milestone.")

	project_name = frappe.db.get_value("Projex Project", ms.project, "project_name") or ms.project
	si = _new_sales_invoice(pr.erpnext_customer, pr.get("billing_currency"), project_name)
	_add_line(
		si, ms.milestone_name,
		f"{project_name} — {ms.milestone_name} ({ms.billing_type})", 1, amount,
	)
	si.insert(ignore_permissions=True)

	ms.db_set({"invoiced": 1, "sales_invoice": si.name})
	frappe.db.commit()
	return {"ok": True, "sales_invoice": si.name, "amount": amount}


# --------------------------------------------------------------------------- #
# Time & Materials
# --------------------------------------------------------------------------- #
def _rate_card(project):
	"""role(lower) -> rate, plus a fallback (first entry's rate) for unmatched logs."""
	rows = frappe.get_all(
		"Projex Billing Rate", filters={"parent": project, "parenttype": "Projex Project"},
		fields=["role", "rate"], order_by="idx asc",
	)
	by_role = {(r.role or "").strip().lower(): r.rate for r in rows}
	fallback = rows[0].rate if rows else 0
	return by_role, fallback


@frappe.whitelist()
def generate_tm_invoice(project, from_date=None, to_date=None):
	"""Bill unbilled, billable native time in a date range at rate-card rates.

	Each time log's rate is matched from the project rate card by its `activity`
	(treated as the delivery role); unmatched logs use the first rate-card entry.
	Lines are grouped by rate so the invoice reads one row per role."""
	pr = _require_billing_ready(project)

	filters = {"project": project, "is_billable": 1, "billed": 0}
	if from_date:
		filters["spent_on"] = [">=", from_date]
	logs = frappe.get_all(
		"Projex Time Log", filters=filters,
		fields=["name", "hours", "activity", "spent_on"], order_by="spent_on asc",
	)
	if to_date:
		logs = [l for l in logs if not l.spent_on or str(l.spent_on) <= str(to_date)]
	if not logs:
		frappe.throw("No unbilled billable time in this range.")

	by_role, fallback = _rate_card(project)
	if not by_role and not fallback:
		frappe.throw("Add a T&M rate card to the project before billing time.")

	# group hours by resolved rate, and remember which logs each covers
	groups = {}  # role_label -> {rate, hours, logs}
	for l in logs:
		role = (l.activity or "").strip()
		rate = by_role.get(role.lower(), fallback)
		key = role or "Consulting"
		g = groups.setdefault(key, {"rate": rate, "hours": 0.0, "logs": []})
		g["hours"] += float(l.hours or 0)
		g["logs"].append((l.name, rate))

	project_name = frappe.db.get_value("Projex Project", project, "project_name") or project
	si = _new_sales_invoice(pr.erpnext_customer, None, project_name)
	period = f" ({from_date or '…'} → {to_date or 'now'})"
	for role, g in groups.items():
		_add_line(
			si, f"{role} (T&M)", f"{project_name} — {role} time{period}",
			round(g["hours"], 2), g["rate"],
		)
	si.insert(ignore_permissions=True)

	# mark every covered log billed + stamp its captured rate
	for g in groups.values():
		for name, rate in g["logs"]:
			frappe.db.set_value("Projex Time Log", name,
								{"billed": 1, "sales_invoice": si.name, "billing_rate": rate},
								update_modified=False)
	frappe.db.commit()
	total_hours = round(sum(g["hours"] for g in groups.values()), 2)
	return {"ok": True, "sales_invoice": si.name, "hours": total_hours, "lines": len(groups)}
