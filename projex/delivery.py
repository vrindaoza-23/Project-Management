# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Delivery plan: phases → milestones → deliverables, with client sign-off.

This is the PSA layer that turns Projex from an issue tracker into an
implementation-delivery tool: a structured, billable plan a partner runs a
client engagement against, and that a client can sign off on.

Whitelisted here (called as ``projex.delivery.*``), mirroring the ``github.py``
module split so ``api.py`` stays focused on the core tracker.
"""

import frappe

from projex.api import _can_manage_project, _company_currency, _erpnext_installed
from projex.permissions import user_can_access_project

_SIGNOFF_OUTCOMES = ("Approved", "Changes Requested")


def _require_access(project):
	if not user_can_access_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)


def _require_manage(project):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)


# --------------------------------------------------------------------------- #
# Read
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def get_delivery_plan(project):
	"""The full delivery plan for a project: ordered phases, each with its
	milestones, each with its deliverables and a computed progress percent.
	Milestones not attached to a phase are grouped under a synthetic 'Unphased'
	bucket so nothing is hidden."""
	_require_access(project)

	phases = frappe.get_all(
		"Projex Phase",
		filters={"project": project},
		fields=[
			"name", "phase_name", "position", "status",
			"start_date", "target_date", "actual_end_date", "description",
		],
		order_by="position asc, creation asc",
	)
	milestones = frappe.get_all(
		"Projex Milestone",
		filters={"project": project},
		fields=[
			"name", "milestone_name", "phase", "position", "status", "target_date",
			"billing_type", "billing_amount", "billing_percent",
			"client_signoff_status", "signoff_requested_on", "signed_off_by",
			"signed_off_on", "signoff_note", "invoiced", "sales_invoice",
		],
		order_by="position asc, creation asc",
	)
	deliverables = frappe.get_all(
		"Projex Deliverable",
		filters={"project": project},
		fields=[
			"name", "deliverable_name", "milestone", "status", "description",
			"approved_by", "approved_on", "review_note",
		],
		order_by="creation asc",
	)

	dels_by_ms = {}
	for d in deliverables:
		dels_by_ms.setdefault(d.milestone, []).append(d)

	for m in milestones:
		ds = dels_by_ms.get(m.name, [])
		approved = sum(1 for d in ds if d.status == "Approved")
		m["deliverables"] = ds
		m["progress"] = round(approved / len(ds) * 100) if ds else (100 if m.status == "Approved" else 0)

	ms_by_phase = {}
	for m in milestones:
		ms_by_phase.setdefault(m.phase or "__unphased__", []).append(m)

	for p in phases:
		p["milestones"] = ms_by_phase.get(p.name, [])

	unphased = ms_by_phase.get("__unphased__", [])
	if unphased:
		phases.append({
			"name": "__unphased__", "phase_name": "Unphased", "position": 9999,
			"status": None, "milestones": unphased, "synthetic": True,
		})

	pr = frappe.db.get_value(
		"Projex Project", project,
		["project_name", "erpnext_customer", "contract_value", "billing_currency"],
		as_dict=True,
	) or frappe._dict()
	return {
		"project": project,
		"project_name": pr.get("project_name") or project,
		"phases": phases,
		"can_manage": _can_manage_project(project),
		"currency": pr.get("billing_currency") or _company_currency(),
		"contract_value": pr.get("contract_value") or 0,
		# invoicing is only possible with ERPNext installed AND a customer linked
		"can_invoice": bool(_erpnext_installed() and pr.get("erpnext_customer")),
	}


# --------------------------------------------------------------------------- #
# Phases
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def create_phase(project, phase_name, position=None, target_date=None, description=None):
	_require_manage(project)
	doc = frappe.get_doc({
		"doctype": "Projex Phase", "project": project, "phase_name": phase_name,
		"position": position or 0, "target_date": target_date or None,
		"description": description or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def update_phase(name, **fields):
	project = frappe.db.get_value("Projex Phase", name, "project")
	_require_manage(project)
	doc = frappe.get_doc("Projex Phase", name)
	for k in ("phase_name", "position", "status", "start_date", "target_date", "actual_end_date", "description"):
		if k in fields:
			doc.set(k, fields[k])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def delete_phase(name):
	project = frappe.db.get_value("Projex Phase", name, "project")
	_require_manage(project)
	# Detach milestones rather than cascade-delete them.
	for m in frappe.get_all("Projex Milestone", filters={"phase": name}, pluck="name"):
		frappe.db.set_value("Projex Milestone", m, "phase", None)
	frappe.delete_doc("Projex Phase", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Milestones
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def create_milestone(project, milestone_name, phase=None, billing_type="Fixed",
					 billing_amount=None, billing_percent=None, target_date=None,
					 position=None, description=None):
	_require_manage(project)
	doc = frappe.get_doc({
		"doctype": "Projex Milestone", "project": project, "milestone_name": milestone_name,
		"phase": phase or None, "billing_type": billing_type,
		"billing_amount": billing_amount or 0, "billing_percent": billing_percent or 0,
		"target_date": target_date or None, "position": position or 0,
		"description": description or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def update_milestone(name, **fields):
	project = frappe.db.get_value("Projex Milestone", name, "project")
	_require_manage(project)
	doc = frappe.get_doc("Projex Milestone", name)
	for k in ("milestone_name", "phase", "position", "status", "target_date",
			  "billing_type", "billing_amount", "billing_percent", "description"):
		if k in fields:
			doc.set(k, fields[k])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def delete_milestone(name):
	project = frappe.db.get_value("Projex Milestone", name, "project")
	_require_manage(project)
	for d in frappe.get_all("Projex Deliverable", filters={"milestone": name}, pluck="name"):
		frappe.delete_doc("Projex Deliverable", d, ignore_permissions=True, force=True)
	frappe.delete_doc("Projex Milestone", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Deliverables
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def create_deliverable(milestone, deliverable_name, description=None):
	project = frappe.db.get_value("Projex Milestone", milestone, "project")
	_require_manage(project)
	doc = frappe.get_doc({
		"doctype": "Projex Deliverable", "milestone": milestone,
		"deliverable_name": deliverable_name, "description": description or None,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def update_deliverable(name, **fields):
	project = frappe.db.get_value("Projex Deliverable", name, "project")
	_require_manage(project)
	doc = frappe.get_doc("Projex Deliverable", name)
	for k in ("deliverable_name", "status", "description"):
		if k in fields:
			doc.set(k, fields[k])
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def delete_deliverable(name):
	project = frappe.db.get_value("Projex Deliverable", name, "project")
	_require_manage(project)
	frappe.delete_doc("Projex Deliverable", name, ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Sign-off
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def request_signoff(milestone):
	"""Partner asks the client to review/approve a milestone. Marks it Delivered
	and sign-off Pending; the client then acts from the portal."""
	doc = frappe.get_doc("Projex Milestone", milestone)
	_require_manage(doc.project)
	doc.db_set({
		"client_signoff_status": "Pending",
		"signoff_requested_on": frappe.utils.now(),
	})
	if doc.status in ("Planned", "In Progress"):
		doc.db_set("status", "Delivered")
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def record_signoff(milestone, outcome, note=None):
	"""Record a milestone-level sign-off decision. Internal/manager path; the
	portal equivalents are client_review_deliverable / client_signoff_milestone."""
	if outcome not in _SIGNOFF_OUTCOMES:
		frappe.throw("Invalid outcome")
	doc = frappe.get_doc("Projex Milestone", milestone)
	_require_manage(doc.project)
	doc.record_signoff(outcome, frappe.session.user, note or "")
	frappe.db.commit()
	return {"ok": True}
