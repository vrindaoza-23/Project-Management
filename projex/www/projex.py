# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
	"""Inject boot data into the SPA page.

	The built index.html iterates `boot` and assigns each key to window[...].
	We must provide at least `csrf_token` (so frappe-ui POST requests pass CSRF)
	and the site name (so the realtime socket can connect). Login is required.
	"""
	if frappe.session.user == "Guest":
		frappe.redirect("/login?redirect-to=/projex")

	context.no_cache = 1
	# Never let the browser cache the SPA entry HTML. It references content-hashed
	# JS chunks that change on every build; a cached HTML points at deleted chunks
	# and the lazy routes 404 ("Failed to fetch dynamically imported module").
	# The hashed assets under /assets remain immutably cacheable.
	frappe.local.response_headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
	context.boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"sitename": frappe.local.site,
		"site_name": frappe.local.site,
		"user": frappe.session.user,
	}
	return context
