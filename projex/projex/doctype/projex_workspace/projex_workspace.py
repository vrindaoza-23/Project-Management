# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ProjexWorkspace(Document):
	def autoname(self):
		# Name by title so links read "Pinecone Labs" rather than a hash.
		self.name = (self.workspace_name or "").strip()
