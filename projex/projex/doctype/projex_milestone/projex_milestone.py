# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from projex.activity import log as log_activity

# Milestone status that each sign-off outcome drives the milestone to.
_SIGNOFF_TO_STATUS = {
	"Approved": "Approved",
	"Changes Requested": "Rejected",
}


class ProjexMilestone(Document):
	def after_insert(self):
		log_activity(self.project, None, "milestone.created", self.milestone_name)

	def on_update(self):
		if self.has_value_changed("status"):
			log_activity(
				self.project, None, "milestone.status", f"{self.milestone_name} → {self.status}"
			)

	def roll_up_from_deliverables(self):
		"""Derive milestone delivery status from its deliverables.

		Empty milestone keeps its manual status. Otherwise: all approved →
		Approved; any changes-requested → Rejected; any submitted → Delivered;
		anything still draft → In Progress.
		"""
		states = frappe.get_all(
			"Projex Deliverable", filters={"milestone": self.name}, pluck="status"
		)
		if not states:
			return
		if all(s == "Approved" for s in states):
			new_status = "Approved"
		elif any(s == "Changes Requested" for s in states):
			new_status = "Rejected"
		elif any(s in ("Submitted", "Approved") for s in states):
			new_status = "Delivered"
		else:
			new_status = "In Progress"
		if new_status != self.status:
			self.db_set("status", new_status)

	def record_signoff(self, outcome, by, note=""):
		"""Apply a client sign-off decision. `outcome` is Approved / Changes Requested."""
		self.db_set(
			{
				"client_signoff_status": outcome,
				"signed_off_by": by,
				"signed_off_on": frappe.utils.now(),
				"signoff_note": note or "",
			}
		)
		mapped = _SIGNOFF_TO_STATUS.get(outcome)
		if mapped:
			self.db_set("status", mapped)
		log_activity(
			self.project, None, "milestone.signoff", f"{self.milestone_name}: {outcome} by {by}"
		)
