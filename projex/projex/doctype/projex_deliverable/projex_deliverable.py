# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from projex.activity import log as log_activity


class ProjexDeliverable(Document):
	def after_insert(self):
		log_activity(self.project, None, "deliverable.created", self.deliverable_name)
		self._roll_up()

	def on_update(self):
		if self.has_value_changed("status"):
			log_activity(
				self.project,
				None,
				"deliverable.status",
				f"{self.deliverable_name} → {self.status}",
			)
			self._roll_up()

	def on_trash(self):
		self._roll_up()

	def _roll_up(self):
		if not self.milestone:
			return
		milestone = frappe.get_doc("Projex Milestone", self.milestone)
		milestone.roll_up_from_deliverables()
