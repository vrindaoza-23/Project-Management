# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from projex.activity import log as log_activity


class ProjexPhase(Document):
	def after_insert(self):
		log_activity(self.project, None, "phase.created", self.phase_name)

	def on_update(self):
		if self.has_value_changed("status"):
			log_activity(
				self.project, None, "phase.status", f"{self.phase_name} → {self.status}"
			)
			if self.status == "Completed" and not self.actual_end_date:
				self.db_set("actual_end_date", frappe.utils.today())
