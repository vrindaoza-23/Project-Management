# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
	"""Client portal shell. Login required; the page calls the client-scoped
	``projex.portal.*`` endpoints, which enforce per-project access.

	Standalone page (full <!doctype html>) using the same `boot` injection as the
	main SPA shell, so CSRF works identically and does not depend on web.html."""
	if frappe.session.user == "Guest":
		frappe.redirect("/login?redirect-to=/projex-portal")

	context.no_cache = 1
	frappe.local.response_headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
	# NB: `boot` is a reserved website context key (Frappe overwrites it), so use
	# our own names and inject them directly.
	context.pp_csrf = frappe.sessions.get_csrf_token()
	context.pp_user = frappe.session.user
	return context
