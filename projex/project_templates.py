# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Project templates — instantiate a repeatable implementation blueprint onto a
project so a partner starts an engagement with the standard phases, tasks,
milestones and deliverables already in place (date-shifted from a start date).

Ships one built-in blueprint, "ERPNext Implementation", seeded idempotently from
the ``after_migrate`` hook.
"""

import frappe
from frappe.utils import add_days, getdate, nowdate

from projex.api import _can_manage_project


@frappe.whitelist()
def list_templates():
	return frappe.get_all(
		"Projex Project Template",
		fields=["name", "template_name", "description"],
		order_by="template_name asc",
	)


@frappe.whitelist()
def instantiate_template(template, project, start_date=None):
	"""Fan a template out onto a project. Phases/tasks/milestones/deliverables
	are created and dated relative to ``start_date`` (defaults to today)."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	tpl = frappe.get_doc("Projex Project Template", template)
	start = getdate(start_date) if start_date else getdate(nowdate())

	created = {"phases": 0, "tasks": 0, "milestones": 0, "deliverables": 0}
	phase_map = {}  # template phase_name -> created Projex Phase name

	for tp in sorted(tpl.phases, key=lambda r: r.position or 0):
		ph = frappe.get_doc({
			"doctype": "Projex Phase", "project": project,
			"phase_name": tp.phase_name, "position": tp.position or 0,
			"start_date": add_days(start, tp.offset_days or 0),
			"target_date": add_days(start, (tp.offset_days or 0) + (tp.duration_days or 0)),
		}).insert(ignore_permissions=True)
		phase_map[tp.phase_name] = ph.name
		created["phases"] += 1

	for tm in tpl.milestones:
		ms = frappe.get_doc({
			"doctype": "Projex Milestone", "project": project,
			"milestone_name": tm.milestone_name, "phase": phase_map.get(tm.phase),
			"billing_type": tm.billing_type or "Fixed",
			"billing_amount": tm.billing_amount or 0,
			"billing_percent": tm.billing_percent or 0,
			"target_date": add_days(start, tm.offset_days or 0),
		}).insert(ignore_permissions=True)
		created["milestones"] += 1
		for line in (tm.deliverables or "").splitlines():
			line = line.strip()
			if not line:
				continue
			frappe.get_doc({
				"doctype": "Projex Deliverable", "milestone": ms.name,
				"deliverable_name": line,
			}).insert(ignore_permissions=True)
			created["deliverables"] += 1

	for tt in tpl.tasks:
		frappe.get_doc({
			"doctype": "Projex Issue", "project": project, "title": tt.title,
			"issue_type": tt.issue_type or "Task", "phase": phase_map.get(tt.phase),
			"due_date": add_days(start, tt.offset_days or 0), "estimate": tt.estimate or 0,
		}).insert(ignore_permissions=True)
		created["tasks"] += 1

	frappe.db.commit()
	return {"ok": True, "created": created}


# --------------------------------------------------------------------------- #
# Built-in "ERPNext Implementation" blueprint (seeded on migrate, idempotent)
# --------------------------------------------------------------------------- #
_ERPNEXT_IMPL = {
	"template_name": "ERPNext Implementation",
	"description": "Standard partner methodology: Discovery → Configuration → "
	"Data Migration → UAT → Training → Go-Live → Hypercare.",
	"phases": [
		("Discovery", 1, 0, 10),
		("Configuration", 2, 10, 20),
		("Data Migration", 3, 25, 15),
		("UAT", 4, 40, 15),
		("Training", 5, 50, 10),
		("Go-Live", 6, 60, 5),
		("Hypercare", 7, 65, 30),
	],
	"tasks": [
		("Kickoff workshop", "Discovery", "Task", 2, 8),
		("Requirements gathering (BRD)", "Discovery", "Story", 8, 24),
		("Chart of Accounts design", "Discovery", "Task", 10, 12),
		("Company & fiscal year setup", "Configuration", "Task", 14, 8),
		("Configure core modules", "Configuration", "Story", 22, 40),
		("Custom fields & workflows", "Configuration", "Task", 28, 24),
		("Prepare data import templates", "Data Migration", "Task", 27, 12),
		("Migrate master data", "Data Migration", "Task", 33, 24),
		("Migrate opening balances", "Data Migration", "Task", 38, 16),
		("Prepare UAT scripts", "UAT", "Task", 41, 12),
		("Conduct UAT", "UAT", "Story", 48, 24),
		("Resolve UAT issues", "UAT", "Bug", 53, 24),
		("Administrator training", "Training", "Task", 52, 8),
		("End-user training", "Training", "Task", 58, 16),
		("Go-live cutover", "Go-Live", "Task", 61, 8),
		("Production smoke test", "Go-Live", "Task", 62, 6),
		("Post-go-live support", "Hypercare", "Task", 70, 40),
	],
	"milestones": [
		("Requirements sign-off", "Discovery", "Fixed", 0, 30, 10, "Signed BRD\nApproved project plan"),
		("Configuration complete", "Configuration", "Fixed", 0, 20, 30, "Configured ERPNext instance\nConfiguration document"),
		("UAT sign-off", "UAT", "Fixed", 0, 25, 55, "UAT sign-off sheet"),
		("Go-Live", "Go-Live", "Fixed", 0, 25, 65, "Production go-live confirmation"),
	],
}


def ensure_default_templates():
	"""Create the built-in ERPNext Implementation template if absent. Idempotent;
	wired from hooks.after_migrate. Does not overwrite partner edits."""
	name = _ERPNEXT_IMPL["template_name"]
	if frappe.db.exists("Projex Project Template", name):
		return
	doc = frappe.new_doc("Projex Project Template")
	doc.template_name = name
	doc.description = _ERPNEXT_IMPL["description"]
	for phase_name, pos, off, dur in _ERPNEXT_IMPL["phases"]:
		doc.append("phases", {
			"phase_name": phase_name, "position": pos,
			"offset_days": off, "duration_days": dur,
		})
	for title, phase, itype, off, est in _ERPNEXT_IMPL["tasks"]:
		doc.append("tasks", {
			"title": title, "phase": phase, "issue_type": itype,
			"offset_days": off, "estimate": est,
		})
	for mname, phase, btype, amt, pct, off, dels in _ERPNEXT_IMPL["milestones"]:
		doc.append("milestones", {
			"milestone_name": mname, "phase": phase, "billing_type": btype,
			"billing_amount": amt, "billing_percent": pct, "offset_days": off,
			"deliverables": dels,
		})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
