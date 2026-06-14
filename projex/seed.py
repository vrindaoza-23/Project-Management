# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Idempotent demo-data generator for Projex.

Mirrors the *shape* of the design prototype's data.js (a SaaS team building a
billing redesign) so the SPA renders against realistic content. Everything is
created through the ORM — there is no hardcoded data in the frontend.

Run:
    bench --site <site> execute projex.seed.run
Re-running is safe: records are upserted by natural key (user email, project
key, status/label/cycle name + project, issue title + project).
"""

import frappe
from frappe.utils import add_days, nowdate

DEMO_USER = "alice@projex.test"
# The user who actually logs into the dev site. We make them a real participant
# (workspace/project member, assignee, inbox recipient) so every screen has
# content for them — without hardcoding anything in the frontend.
DEMO_LOGIN = "Administrator"

USERS = [
	("alice@projex.test", "Alice", "Chen"),
	("ben@projex.test", "Ben", "Okafor"),
	("cris@projex.test", "Cris", "Park"),
	("dani@projex.test", "Dani", "Rao"),
	("erez@projex.test", "Erez", "Solano"),
	("fae@projex.test", "Fae", "Lindqvist"),
	("gia@projex.test", "Gia", "Mendoza"),
	("han@projex.test", "Han", "Yusuf"),
]

# status_name, category, color_theme, dot_hollow, position
STATUSES = [
	("Backlog", "backlog", "gray", 1, 0),
	("Todo", "unstarted", "gray", 0, 1),
	("In progress", "started", "blue", 0, 2),
	("In review", "started", "amber", 0, 3),
	("Done", "completed", "green", 0, 4),
	("Cancelled", "cancelled", "gray", 1, 5),
]

LABELS = [
	("frontend", "var(--blue-500)"), ("backend", "var(--green-600)"),
	("design", "var(--purple-500)"), ("bug", "var(--red-500)"),
	("a11y", "var(--violet-500)"), ("perf", "var(--amber-500)"),
	("spike", "var(--teal-600)"), ("customer", "var(--orange-500)"),
]

# key, name, icon, status, lead
PROJECTS = [
	("BIL", "Billing v2", "credit-card", "Active", "alice@projex.test"),
	("ONB", "Onboarding refresh", "sparkles", "Active", "cris@projex.test"),
	("MOB", "Mobile app", "smartphone", "Planning", "ben@projex.test"),
	("MKT", "Marketing site", "megaphone", "Active", "fae@projex.test"),
	("INF", "Infra & Platform", "server", "Active", "han@projex.test"),
	("RES", "Research & insights", "microscope", "On hold", "dani@projex.test"),
]

# project, name, start_offset_days, end_offset_days, state
CYCLES = [
	("BIL", "Cycle 24", -7, 7, "Active"),
	("BIL", "Cycle 25", 8, 22, "Upcoming"),
]

PRIORITY = {"urgent": "Urgent", "high": "High", "medium": "Medium", "low": "Low", "none": "None"}
STATUS_MAP = {
	"doing": "In progress", "review": "In review", "todo": "Todo",
	"backlog": "Backlog", "done": "Done", "cancel": "Cancelled",
}


def _due(token):
	if not token:
		return None
	rel = {"Today": 0, "Mon": 4, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4,
		   "Next wk": 7, "yesterday": -1}
	if token in rel:
		return add_days(nowdate(), rel[token])
	return None


# project, title, status, priority, [assignee handles], [label names], due, points, sub, done
ISSUES = [
	("BIL", "Redesign invoice detail page", "doing", "high", ["cris", "alice"], ["design", "frontend"], "Tue", 5, 4, 2),
	("BIL", "Add proration preview to upgrade flow", "doing", "urgent", ["alice"], ["frontend", "backend", "customer"], "Today", 8, 6, 4),
	("BIL", "Stripe webhook idempotency review", "review", "high", ["han"], ["backend", "perf"], "Wed", 3, 0, 0),
	("BIL", "Empty state when no invoices exist", "todo", "low", ["cris"], ["design"], "Fri", 1, 0, 0),
	("BIL", "Tax-ID validation against VIES", "todo", "medium", ["han", "dani"], ["backend"], "Next wk", 5, 0, 0),
	("BIL", "PDF receipt: i18n date formatting", "backlog", "low", [], ["bug"], None, 2, 0, 0),
	("BIL", "Pricing page: yearly toggle animation", "done", "medium", ["cris"], ["frontend", "design"], None, 2, 0, 0),
	("BIL", "Audit log for plan changes", "done", "medium", ["han"], ["backend"], None, 3, 0, 0),
	("ONB", "Welcome screen - 3-step survey", "doing", "high", ["cris", "fae"], ["design", "frontend"], "Thu", 5, 3, 1),
	("ONB", "Sample workspace auto-provisioning", "todo", "high", ["han"], ["backend"], "Mon", 8, 0, 0),
	("ONB", "A/B test: progress bar vs checklist", "review", "medium", ["dani"], ["spike"], None, 3, 0, 0),
	("ONB", "Drop-off analytics dashboard", "backlog", "medium", ["dani"], [], None, 5, 0, 0),
	("MOB", "Push notification permission primer", "todo", "medium", ["ben"], ["design"], None, 3, 0, 0),
	("MOB", "Biometric login (Face ID / fingerprint)", "backlog", "low", ["ben"], ["frontend"], None, 5, 0, 0),
	("MOB", "Offline drafts for issue creation", "backlog", "low", [], ["frontend"], None, 8, 0, 0),
	("MKT", "New homepage hero - copy + visual", "doing", "high", ["fae", "gia"], ["design"], "Fri", 5, 0, 0),
	("MKT", "Customer logo wall - refresh", "review", "low", ["gia"], ["design"], None, 1, 0, 0),
	("MKT", "Pricing page rebuild", "todo", "medium", ["fae"], ["frontend", "design"], "Next wk", 5, 0, 0),
	("INF", "Postgres 16 upgrade - staging", "doing", "urgent", ["han", "erez"], ["backend", "perf"], "Today", 8, 5, 3),
	("INF", "Renew TLS certs (3 domains)", "todo", "urgent", ["erez"], ["bug"], "Mon", 1, 0, 0),
	("INF", "p99 latency budget for /api/issues", "doing", "high", ["erez"], ["perf", "backend"], "Wed", 5, 0, 0),
	("INF", "OpenTelemetry - gateway to workers", "todo", "medium", ["han"], ["backend"], None, 8, 0, 0),
	("INF", "Daily backup verification cron", "done", "medium", ["erez"], ["backend"], None, 2, 0, 0),
	("RES", "SMB churn interviews (n=12)", "backlog", "medium", ["dani"], [], None, 5, 0, 0),
	("BIL", "Webhook retry with exponential backoff", "todo", "medium", ["han"], ["backend", "perf"], "Next wk", 3, 0, 0),
	("BIL", "Dunning email sequence copy", "backlog", "low", ["fae"], ["customer"], None, 2, 0, 0),
	("ONB", "Checklist completion celebration", "todo", "low", ["cris"], ["design"], None, 1, 0, 0),
	("INF", "Rotate database credentials", "todo", "high", ["erez"], ["backend"], "Thu", 2, 0, 0),
	("MKT", "SEO meta + sitemap regeneration", "backlog", "low", ["gia"], [], None, 2, 0, 0),
	("MOB", "Crash reporting integration", "todo", "medium", ["ben"], ["backend"], "Next wk", 3, 0, 0),
]

# issue title -> list of (author handle, content)
COMMENTS = {
	"Add proration preview to upgrade flow": [
		("cris", "Pulled the Stripe response shape into Figma - upcoming_invoice already returns line items."),
		("han", "Watch out for the trial-conversion edge case - proration_behavior is none there."),
		("alice", "Good catch. Adding it to the test matrix."),
	],
	"Postgres 16 upgrade - staging": [
		("erez", "Staging snapshot taken. Running pg_upgrade dry run now."),
		("han", "Remember to bump the connection pool ceiling after cutover."),
	],
}


def _h(handle):
	return f"{handle}@projex.test"


# --------------------------------------------------------------------------- #
def upsert_users():
	for email, first, last in USERS:
		if frappe.db.exists("User", email):
			continue
		frappe.get_doc({
			"doctype": "User", "email": email, "first_name": first, "last_name": last,
			"send_welcome_email": 0, "user_type": "System User",
			"roles": [{"role": "Projex Member"}],
		}).insert(ignore_permissions=True)


def upsert_statuses():
	out = {}
	for name, category, theme, hollow, pos in STATUSES:
		existing = frappe.db.get_value("Projex Status", {"status_name": name, "project": ["in", ["", None]]})
		if existing:
			out[name] = existing
			continue
		doc = frappe.get_doc({
			"doctype": "Projex Status", "status_name": name, "category": category,
			"color_theme": theme, "dot_hollow": hollow, "position": pos,
		}).insert(ignore_permissions=True)
		out[name] = doc.name
	return out


def upsert_labels():
	out = {}
	for name, color in LABELS:
		existing = frappe.db.get_value("Projex Label", {"label_name": name, "project": ["in", ["", None]]})
		if existing:
			out[name] = existing
			continue
		doc = frappe.get_doc({
			"doctype": "Projex Label", "label_name": name, "color": color,
		}).insert(ignore_permissions=True)
		out[name] = doc.name
	return out


def upsert_workspace():
	title = "Pinecone Labs"
	existing = frappe.db.get_value("Projex Workspace", {"workspace_name": title})
	if existing:
		return existing
	doc = frappe.get_doc({
		"doctype": "Projex Workspace", "workspace_name": title, "icon": "box",
		"description": "Demo workspace seeded by projex.seed",
		"members": [{"user": e, "role": "Admin" if e == DEMO_USER else "Member"} for e, *_ in USERS],
	}).insert(ignore_permissions=True)
	return doc.name


def upsert_projects(workspace):
	for key, pname, icon, status, lead in PROJECTS:
		if frappe.db.exists("Projex Project", key):
			continue
		frappe.get_doc({
			"doctype": "Projex Project", "project_name": pname, "key": key, "icon": icon,
			"status": status, "lead": lead, "workspace": workspace,
			"members": [{"user": e, "role": "Member"} for e, *_ in USERS],
		}).insert(ignore_permissions=True)


def upsert_cycles():
	for project, cname, so, eo, state in CYCLES:
		if frappe.db.get_value("Projex Cycle", {"cycle_name": cname, "project": project}):
			continue
		frappe.get_doc({
			"doctype": "Projex Cycle", "cycle_name": cname, "project": project,
			"start_date": add_days(nowdate(), so), "end_date": add_days(nowdate(), eo),
			"state": state,
		}).insert(ignore_permissions=True)


def upsert_issues(statuses, labels):
	cycle_24 = frappe.db.get_value("Projex Cycle", {"cycle_name": "Cycle 24", "project": "BIL"})
	for project, title, st, prio, assignees, lbls, due, points, sub, done in ISSUES:
		if frappe.db.exists("Projex Issue", {"project": project, "title": title}):
			continue
		doc = frappe.get_doc({
			"doctype": "Projex Issue", "title": title, "project": project,
			"status": statuses[STATUS_MAP[st]], "priority": PRIORITY[prio],
			"due_date": _due(due), "estimate": points,
			"cycle": cycle_24 if project == "BIL" else None,
			"reporter": DEMO_USER,
			"assignees": [{"user": _h(a)} for a in assignees],
			"labels": [{"label": labels[l]} for l in lbls],
			"description": f"<p>Seeded issue for <b>{title}</b>.</p>",
		})
		doc.insert(ignore_permissions=True)
		_seed_subtasks(doc, sub, done)


def _seed_subtasks(parent, sub, done):
	for i in range(sub):
		title = f"{parent.title} - subtask {i + 1}"
		if frappe.db.exists("Projex Issue", {"project": parent.project, "title": title}):
			continue
		child = frappe.get_doc({
			"doctype": "Projex Issue", "title": title, "project": parent.project,
			"parent_issue": parent.name, "reporter": DEMO_USER,
			"status": parent.status if i >= done else _completed_status(),
			"priority": "Medium",
		})
		child.insert(ignore_permissions=True)


def _completed_status():
	return frappe.db.get_value("Projex Status", {"status_name": "Done", "project": ["in", ["", None]]})


def upsert_comments():
	for title, items in COMMENTS.items():
		issue = frappe.db.get_value("Projex Issue", {"title": title})
		if not issue:
			continue
		for handle, content in items:
			html = f"<p>{content}</p>"
			if frappe.db.exists("Projex Comment", {"issue": issue, "content": html}):
				continue
			c = frappe.get_doc({
				"doctype": "Projex Comment", "issue": issue, "content": html,
			})
			c.flags.ignore_permissions = True
			c.owner = _h(handle)
			c.insert(ignore_permissions=True)


def debug_run():
	"""Wrapper that prints any traceback (bench execute swallows exceptions)."""
	import traceback
	try:
		return run()
	except Exception:
		traceback.print_exc()
		raise


def assign_demo_login():
	"""Make the dev login user a participant so every screen has content."""
	if not frappe.db.exists("User", DEMO_LOGIN):
		return
	# Workspace membership
	ws = frappe.get_doc("Projex Workspace", "Pinecone Labs")
	if not any(m.user == DEMO_LOGIN for m in ws.members):
		ws.append("members", {"user": DEMO_LOGIN, "role": "Admin"})
		ws.save(ignore_permissions=True)
	# Assign to a spread of issues across projects (populates My tasks)
	picks = []
	for key in ("BIL", "INF", "ONB"):
		picks += frappe.get_all(
			"Projex Issue",
			filters={"project": key, "parent_issue": ["in", ["", None]]},
			pluck="name", order_by="creation asc", limit=2,
		)
	for name in picks:
		doc = frappe.get_doc("Projex Issue", name)
		if not any(a.user == DEMO_LOGIN for a in doc.assignees):
			doc.append("assignees", {"user": DEMO_LOGIN})
			doc.save(ignore_permissions=True)


def seed_demo_inbox():
	"""A few inbox notifications for the demo login user (idempotent)."""
	if not frappe.db.exists("User", DEMO_LOGIN):
		return
	samples = [
		("mention", "cris@projex.test", "BIL-2", "Mentioned you in a comment"),
		("assigned", "alice@projex.test", "BIL-1", "Assigned you to an issue"),
		("comment", "han@projex.test", "INF-1", "Commented on this issue"),
		("status", "alice@projex.test", "BIL-1", "moved to In review"),
		("review", "erez@projex.test", "INF-1", "Requested your review"),
	]
	for ntype, actor, issue, snippet in samples:
		if not frappe.db.exists("Projex Issue", issue):
			continue
		exists = frappe.db.exists(
			"Projex Notification",
			{"user": DEMO_LOGIN, "issue": issue, "notification_type": ntype, "snippet": snippet},
		)
		if exists:
			continue
		frappe.get_doc({
			"doctype": "Projex Notification", "user": DEMO_LOGIN,
			"notification_type": ntype, "actor": actor, "issue": issue,
			"snippet": snippet, "is_read": 0,
		}).insert(ignore_permissions=True)


def run():
	upsert_users()
	statuses = upsert_statuses()
	labels = upsert_labels()
	workspace = upsert_workspace()
	upsert_projects(workspace)
	upsert_cycles()
	upsert_issues(statuses, labels)
	upsert_comments()
	assign_demo_login()
	seed_demo_inbox()
	frappe.db.commit()

	counts = {dt: frappe.db.count(dt) for dt in [
		"Projex Workspace", "Projex Project", "Projex Status", "Projex Label",
		"Projex Cycle", "Projex Issue", "Projex Comment", "Projex Notification",
	]}
	print("Seed complete. Row counts:")
	for dt, n in counts.items():
		print(f"  {dt:24} {n}")
	return counts
