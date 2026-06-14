# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Optional ERPNext integration, applied only when ERPNext is installed.

Projex core has NO hard dependency on ERPNext. When ERPNext is present, we add
the wedge links (Customer / Project) to Projex Project as Custom Fields so the
core schema stays installable and testable on a plain Frappe site.

Wired from hooks.py `after_install` and `after_migrate`.
"""

import frappe


def setup_custom_fields():
	if "erpnext" not in frappe.get_installed_apps():
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Projex Project": [
				{
					"fieldname": "erpnext_section",
					"label": "ERPNext",
					"fieldtype": "Section Break",
					"insert_after": "issue_counter",
					"collapsible": 1,
				},
				{
					"fieldname": "erpnext_customer",
					"label": "ERPNext Customer",
					"fieldtype": "Link",
					"options": "Customer",
					"insert_after": "erpnext_section",
					"description": "Optional: roll this project up to an ERPNext Customer",
				},
				{
					"fieldname": "erpnext_project",
					"label": "ERPNext Project",
					"fieldtype": "Link",
					"options": "Project",
					"insert_after": "erpnext_customer",
					"description": "Optional: link to an ERPNext Project for timesheets",
				},
			]
		},
		ignore_validate=True,
	)
	frappe.db.commit()
