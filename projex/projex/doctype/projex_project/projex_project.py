# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class ProjexProject(Document):
	def autoname(self):
		# Name the project by its key so issues read BIL-12 and URLs are /projects/BIL.
		self.key = (self.key or "").strip().upper()
		self.name = self.key

	def validate(self):
		self._normalize_key()

	def _normalize_key(self):
		if not self.key:
			frappe.throw("Project key is required")
		self.key = self.key.strip().upper()
		if not re.fullmatch(r"[A-Z]{2,4}", self.key):
			frappe.throw("Key must be 2-4 letters (A-Z), e.g. BIL")
		# Uniqueness is enforced by the unique field; surface a friendly error.
		clash = frappe.db.exists(
			"Projex Project", {"key": self.key, "name": ["!=", self.name or ""]}
		)
		if clash:
			frappe.throw(f"Project key '{self.key}' is already in use")


def get_permission_query_conditions(user=None):
	from projex.permissions import accessible_project_condition
	return accessible_project_condition(user, "`tabProjex Project`.name")


def has_permission(doc, user=None, permission_type=None):
	from projex.permissions import user_can_access_project
	return user_can_access_project(doc.name, user)
