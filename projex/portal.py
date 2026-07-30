# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Client portal — the customer-facing surface of a partner engagement.

A client (a User holding the portal-only ``Projex Client`` role, granted access
to specific projects via ``Projex Client Access``) can:
  - see the delivery status of their project(s) — phases, milestones, progress,
  - approve deliverables / request changes (UAT & deliverable sign-off),
  - raise issues and track the ones they raised.

Every endpoint verifies access explicitly against ``Projex Client Access`` and
never trusts a project name from the client. Billing internals (amounts, rates,
invoices) are never exposed here.
"""

import frappe

from projex.api import _can_manage_project

_REVIEW_OUTCOMES = ("Approved", "Changes Requested")


# --------------------------------------------------------------------------- #
# Access helpers
# --------------------------------------------------------------------------- #
def _client_project_names(user=None):
	user = user or frappe.session.user
	if user == "Guest":
		return set()
	return set(
		frappe.get_all(
			"Projex Client Access",
			filters={"user": user, "disabled": 0},
			pluck="project",
		)
	)


def _assert_client_project(project, user=None):
	if project not in _client_project_names(user):
		frappe.throw("Not permitted", frappe.PermissionError)


def _project_of_deliverable(deliverable):
	return frappe.db.get_value("Projex Deliverable", deliverable, "project")


# --------------------------------------------------------------------------- #
# Client reads
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def client_bootstrap():
	"""Everything the portal shell needs on load: the signed-in user and the
	projects they may see (with a headline progress figure)."""
	names = _client_project_names()
	projects = []
	for p in frappe.get_all(
		"Projex Project", filters={"name": ["in", list(names)] or [""]},
		fields=["name", "project_name", "status", "icon", "color"],
	) if names else []:
		projects.append({**p, "progress": _project_progress(p.name)})
	user = frappe.db.get_value("User", frappe.session.user, ["full_name", "user_image"], as_dict=True) or {}
	return {
		"user": frappe.session.user,
		"full_name": user.get("full_name"),
		"user_image": user.get("user_image"),
		"projects": projects,
	}


def _project_progress(project):
	"""Headline delivery progress = approved milestones / total milestones."""
	total = frappe.db.count("Projex Milestone", {"project": project})
	if not total:
		return 0
	approved = frappe.db.count("Projex Milestone", {"project": project, "status": "Approved"})
	return round(approved / total * 100)


@frappe.whitelist()
def client_get_delivery_plan(project):
	"""Client-safe delivery plan: phases → milestones → deliverables, with
	progress and sign-off state. Billing internals are intentionally omitted."""
	_assert_client_project(project)

	phases = frappe.get_all(
		"Projex Phase", filters={"project": project},
		fields=["name", "phase_name", "position", "status", "start_date", "target_date"],
		order_by="position asc, creation asc",
	)
	milestones = frappe.get_all(
		"Projex Milestone", filters={"project": project},
		fields=[
			"name", "milestone_name", "phase", "position", "status", "target_date",
			"client_signoff_status", "signoff_requested_on",
		],
		order_by="position asc, creation asc",
	)
	deliverables = frappe.get_all(
		"Projex Deliverable", filters={"project": project},
		fields=["name", "deliverable_name", "milestone", "status", "description", "review_note"],
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
		# does this milestone await the client's action?
		m["awaiting_client"] = m.client_signoff_status == "Pending" or any(
			d.status == "Submitted" for d in ds
		)

	ms_by_phase = {}
	for m in milestones:
		ms_by_phase.setdefault(m.phase or "__unphased__", []).append(m)
	for p in phases:
		p["milestones"] = ms_by_phase.get(p.name, [])
	unphased = ms_by_phase.get("__unphased__", [])
	if unphased:
		phases.append({"name": "__unphased__", "phase_name": "Other", "milestones": unphased})

	project_name = frappe.db.get_value("Projex Project", project, "project_name")
	return {"project": project, "project_name": project_name, "phases": phases}


@frappe.whitelist()
def client_list_issues(project):
	"""Issues this client raised on the project, with status."""
	_assert_client_project(project)
	rows = frappe.get_all(
		"Projex Issue",
		filters={"project": project, "reporter": frappe.session.user},
		fields=["name", "issue_id", "title", "issue_type", "status", "creation"],
		order_by="creation desc", limit=100,
	)
	# `status` is a Link to Projex Status (hash-named); resolve to its label.
	sids = list({r.status for r in rows if r.status})
	labels = {
		s.name: s.status_name
		for s in frappe.get_all(
			"Projex Status", filters={"name": ["in", sids]}, fields=["name", "status_name"]
		)
	} if sids else {}
	for r in rows:
		r["status"] = labels.get(r.status) or "Open"
	return {"issues": rows}


# --------------------------------------------------------------------------- #
# Client actions
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def client_review_deliverable(deliverable, outcome, note=None):
	"""Client approves a deliverable or requests changes. Rolls the decision up
	to the milestone's sign-off state."""
	if outcome not in _REVIEW_OUTCOMES:
		frappe.throw("Invalid outcome")
	project = _project_of_deliverable(deliverable)
	if not project:
		frappe.throw("Deliverable not found")
	_assert_client_project(project)

	doc = frappe.get_doc("Projex Deliverable", deliverable)
	doc.status = outcome
	doc.approved_by = frappe.session.user
	doc.approved_on = frappe.utils.now()
	doc.review_note = note or ""
	doc.save(ignore_permissions=True)  # controller rolls milestone delivery status

	_sync_milestone_signoff(doc.milestone)
	frappe.db.commit()
	return {"ok": True}


def _sync_milestone_signoff(milestone):
	"""Aggregate deliverable reviews into the milestone's client sign-off state."""
	if not milestone:
		return
	states = frappe.get_all("Projex Deliverable", filters={"milestone": milestone}, pluck="status")
	if not states:
		return
	ms = frappe.get_doc("Projex Milestone", milestone)
	if all(s == "Approved" for s in states):
		ms.record_signoff("Approved", frappe.session.user, "")
	elif any(s == "Changes Requested" for s in states):
		ms.record_signoff("Changes Requested", frappe.session.user, "")


@frappe.whitelist()
def client_raise_issue(project, title, description=None, issue_type="Bug"):
	"""Client raises an issue/request against their project."""
	_assert_client_project(project)
	if issue_type not in ("Task", "Bug", "Story"):
		issue_type = "Bug"
	doc = frappe.get_doc({
		"doctype": "Projex Issue", "project": project, "title": title,
		"issue_type": issue_type, "description": description or None,
		"reporter": frappe.session.user,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True, "name": doc.name, "issue_id": doc.issue_id}


# --------------------------------------------------------------------------- #
# Partner-side management (grant / revoke client access)
# --------------------------------------------------------------------------- #
@frappe.whitelist()
def grant_client_access(project, email):
	"""Give an existing User portal access to a project and the Projex Client role.
	Manager-gated. The user must already exist (invite/create them first)."""
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	if not frappe.db.exists("User", email):
		frappe.throw(f"No user '{email}'. Create the user first, then grant access.")
	existing = frappe.db.get_value(
		"Projex Client Access", {"user": email, "project": project}, "name"
	)
	if existing:
		frappe.db.set_value("Projex Client Access", existing, "disabled", 0)
	else:
		frappe.get_doc({
			"doctype": "Projex Client Access", "user": email, "project": project,
		}).insert(ignore_permissions=True)
	# Ensure the portal role is assigned.
	user = frappe.get_doc("User", email)
	if "Projex Client" not in {r.role for r in user.roles}:
		user.append("roles", {"role": "Projex Client"})
		user.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def revoke_client_access(project, email):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	name = frappe.db.get_value("Projex Client Access", {"user": email, "project": project}, "name")
	if name:
		frappe.db.set_value("Projex Client Access", name, "disabled", 1)
		frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def list_client_access(project):
	if not _can_manage_project(project):
		frappe.throw("Not permitted", frappe.PermissionError)
	return frappe.get_all(
		"Projex Client Access",
		filters={"project": project, "disabled": 0},
		fields=["name", "user", "customer"],
	)
