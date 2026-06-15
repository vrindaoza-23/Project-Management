# Copyright (c) 2026, Projex and contributors
# For license information, please see license.txt

"""Rich demo-data generator for the **Aurora - Fitness Mobile app** (MOB) project.

Purpose: make every tab/section of the SPA render with believable content for a
product walkthrough video. Idempotent — re-running upserts by natural key and
re-applies enrichment, so it is safe to run repeatedly.

Run:
    bench --site mysite.localhost execute projex.seed_aurora.run
"""

import json
import frappe
from frappe.utils import add_days, nowdate

PROJECT = "MOB"
DEMO_LOGIN = "Administrator"   # the dev user who records the video


def _h(handle):
    return f"{handle}@projex.test"


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def _status_map():
    rows = frappe.get_all("Projex Status", filters={"project": ["in", ["", None]]},
                          fields=["name", "status_name"])
    return {r.status_name: r.name for r in rows}


def _label_map():
    rows = frappe.get_all("Projex Label", filters={"project": ["in", ["", None]]},
                          fields=["name", "label_name"])
    return {r.label_name: r.name for r in rows}


EXTRA_LABELS = [
    ("ios", "var(--sky-500)"), ("android", "var(--green-500)"),
    ("api", "var(--indigo-500)"), ("ux", "var(--pink-500)"),
    ("growth", "var(--amber-600)"),
]


def ensure_labels():
    for name, color in EXTRA_LABELS:
        if not frappe.db.get_value("Projex Label", {"label_name": name, "project": ["in", ["", None]]}):
            frappe.get_doc({"doctype": "Projex Label", "label_name": name,
                            "color": color}).insert(ignore_permissions=True)


# --------------------------------------------------------------------------- #
# Project framing
# --------------------------------------------------------------------------- #
def frame_project():
    """Rename to the full title and make the dev login a first-class member."""
    doc = frappe.get_doc("Projex Project", PROJECT)
    changed = False
    if doc.project_name != "Aurora- Fitness Mobile app":
        doc.project_name = "Aurora- Fitness Mobile app"
        changed = True
    if (doc.icon or "") != "dumbbell":
        doc.icon = "dumbbell"
        changed = True
    if (doc.status or "") != "Active":
        doc.status = "Active"
        changed = True
    if not any(m.user == DEMO_LOGIN for m in doc.members):
        doc.append("members", {"user": DEMO_LOGIN, "role": "Admin"})
        changed = True
    if changed:
        doc.save(ignore_permissions=True)
    # favorite it so it surfaces in the sidebar Favorites group
    if not frappe.db.exists("Projex Favorite", {"user": DEMO_LOGIN, "project": PROJECT}):
        frappe.get_doc({"doctype": "Projex Favorite", "user": DEMO_LOGIN,
                        "project": PROJECT}).insert(ignore_permissions=True)


# --------------------------------------------------------------------------- #
# Sprints (cycles)
# --------------------------------------------------------------------------- #
# name, start_offset, end_offset, state
SPRINTS = [
    ("Sprint 3", -35, -21, "Completed"),
    ("Sprint 4", -21, -7, "Completed"),
    ("Sprint 5", -7, 9, "Active"),
    ("Sprint 6", 10, 24, "Upcoming"),
]


def upsert_sprints():
    out = {}
    for name, so, eo, state in SPRINTS:
        existing = frappe.db.get_value("Projex Cycle", {"cycle_name": name, "project": PROJECT})
        if existing:
            c = frappe.get_doc("Projex Cycle", existing)
            c.start_date = add_days(nowdate(), so)
            c.end_date = add_days(nowdate(), eo)
            c.state = state
            c.save(ignore_permissions=True)
            out[name] = existing
            continue
        c = frappe.get_doc({
            "doctype": "Projex Cycle", "cycle_name": name, "project": PROJECT,
            "start_date": add_days(nowdate(), so), "end_date": add_days(nowdate(), eo),
            "state": state,
        }).insert(ignore_permissions=True)
        out[name] = c.name
    return out


# --------------------------------------------------------------------------- #
# Issues
# --------------------------------------------------------------------------- #
# Each issue: dict with keys
#   title, type, status, priority, assignees[], labels[], start, due, points,
#   sprint, recurrence, subtasks(list of (title, done)), checklist[(t,done)],
#   comments[(handle, text)], links[(type, target_title)],
#   done_creation (offset, for backdated historical), done_modified (offset)
def _i(**kw):
    return kw


ISSUES = [
    # ----- Active sprint (Sprint 5): the live board -----------------------
    _i(title="Apple Health & Google Fit sync", type="Story", status="In progress",
       priority="Urgent", assignees=["alice", "han"], labels=["ios", "android", "backend"],
       start=-5, due=4, points=8, sprint="Sprint 5", recurrence="None",
       subtasks=[("HealthKit read permissions", 1), ("Fit REST polling job", 0),
                 ("Conflict resolution for duplicate workouts", 0)],
       checklist=[("Spike both SDKs", 1), ("Background sync budget", 1),
                  ("Privacy review", 0), ("Unit tests for merge logic", 0)],
       comments=[("alice", "HealthKit returns workouts as HKWorkout - mapping to our schema in a helper."),
                 ("han", "Google Fit needs OAuth refresh handling; added a token table."),
                 ("alice", "Good - let's gate the whole feature behind a remote flag for launch.")],
       links=[("blocks", "Workout summary share card")]),
    _i(title="Live workout tracking screen", type="Story", status="In progress",
       priority="High", assignees=["cris", "ben"], labels=["ios", "android", "ux"],
       start=-4, due=6, points=8, sprint="Sprint 5",
       checklist=[("Heart-rate zone colors", 1), ("Pause/resume state machine", 0),
                  ("Auto-lap every 1km", 0)],
       comments=[("cris", "Prototype in Figma; using a radial progress ring for the active zone.")],
       links=[("blocks", "Rest-timer haptics & sound")]),
    _i(title="Rest-timer haptics & sound", type="Task", status="In review",
       priority="Medium", assignees=["ben"], labels=["ios"], start=-3, due=2, points=3,
       sprint="Sprint 5",
       comments=[("ben", "Haptics feel great on iPhone 15; testing fallbacks on older devices.")]),
    _i(title="Onboarding goal-selection flow", type="Story", status="In review",
       priority="High", assignees=["fae", "cris"], labels=["design", "ux", "growth"],
       start=-6, due=1, points=5, sprint="Sprint 5",
       checklist=[("3 goal archetypes", 1), ("Copy review", 1), ("A11y pass", 0)],
       links=[("blocks", "Empty state for first-time dashboard")]),
    _i(title="Crash on resume after backgrounding", type="Bug", status="In progress",
       priority="Urgent", assignees=["han"], labels=["bug", "android"], start=-2, due=0,
       points=3, sprint="Sprint 5",
       comments=[("han", "Repro on Pixel 7 / Android 14 only. Looks like a stale Activity reference.")]),
    _i(title="Streak counter resets at midnight UTC", type="Bug", status="Todo",
       priority="High", assignees=["dani"], labels=["bug", "backend"], start=-1, due=3,
       points=2, sprint="Sprint 5"),
    _i(title="Workout summary share card", type="Task", status="Todo",
       priority="Medium", assignees=["gia"], labels=["design", "growth"], start=0, due=7,
       points=5, sprint="Sprint 5"),
    _i(title="Weekly progress push notification", type="Task", status="Todo",
       priority="Medium", assignees=["ben"], labels=["android", "ios"], start=1, due=8,
       points=3, sprint="Sprint 5", recurrence="Weekly"),

    # ----- Backlog / Sprint 6 (upcoming) ----------------------------------
    _i(title="Social feed: follow friends", type="Epic", status="Backlog",
       priority="High", assignees=["fae"], labels=["growth", "backend"], start=11, due=23,
       points=13, sprint="Sprint 6"),
    _i(title="In-app purchase: Aurora Pro", type="Epic", status="Backlog",
       priority="High", assignees=["alice"], labels=["ios", "android", "backend"],
       start=12, due=24, points=13, sprint="Sprint 6",
       links=[("blocked by", "Social feed: follow friends")]),
    _i(title="Apple Watch companion app", type="Story", status="Backlog",
       priority="Medium", assignees=["cris"], labels=["ios"], start=13, due=22, points=8,
       sprint="Sprint 6", links=[("blocks", "Live workout tracking screen")]),
    _i(title="Offline mode for logged workouts", type="Story", status="Backlog",
       priority="Medium", assignees=["han"], labels=["backend"], start=None, due=None,
       points=8, sprint=None),
    _i(title="Dark mode polish across all screens", type="Task", status="Backlog",
       priority="Low", assignees=["gia"], labels=["design", "ux"], start=None, due=None,
       points=5, sprint=None),
    _i(title="Localization: Spanish & German", type="Task", status="Backlog",
       priority="Low", assignees=["fae"], labels=["ux"], start=None, due=None, points=5,
       sprint=None),
    _i(title="Wearable: Garmin Connect import", type="Story", status="Backlog",
       priority="Low", assignees=[], labels=["api", "backend"], start=None, due=None,
       points=8, sprint=None),
    _i(title="GDPR data-export request flow", type="Task", status="Todo",
       priority="Medium", assignees=["dani"], labels=["backend", "customer"], start=2,
       due=14, points=3, sprint=None),
    _i(title="Battery drain during GPS tracking", type="Bug", status="Backlog",
       priority="High", assignees=["han"], labels=["bug", "perf", "android"], start=None,
       due=10, points=5, sprint=None),
    _i(title="Empty state for first-time dashboard", type="Task", status="Todo",
       priority="Low", assignees=["cris"], labels=["design", "ux"], start=3, due=12,
       points=2, sprint=None),

    # ----- Historical done (feeds throughput / cycle-time / velocity) -----
    _i(title="App scaffold: navigation & theming", type="Task", status="Done",
       priority="High", assignees=["ben"], labels=["frontend"], points=5,
       sprint="Sprint 3", done_creation=-34, done_modified=-30),
    _i(title="Auth: email + Apple/Google sign-in", type="Story", status="Done",
       priority="Urgent", assignees=["alice"], labels=["backend", "ios"], points=8,
       sprint="Sprint 3", done_creation=-33, done_modified=-27),
    _i(title="Exercise library data model", type="Task", status="Done",
       priority="High", assignees=["han"], labels=["backend"], points=5,
       sprint="Sprint 3", done_creation=-32, done_modified=-24),
    _i(title="Workout logging MVP", type="Story", status="Done",
       priority="High", assignees=["cris"], labels=["frontend"], points=8,
       sprint="Sprint 3", done_creation=-30, done_modified=-22),
    _i(title="Profile & settings screen", type="Task", status="Done",
       priority="Medium", assignees=["gia"], labels=["frontend", "design"], points=5,
       sprint="Sprint 4", done_creation=-20, done_modified=-16),
    _i(title="Push notification infrastructure", type="Task", status="Done",
       priority="High", assignees=["ben"], labels=["backend"], points=5,
       sprint="Sprint 4", done_creation=-19, done_modified=-13),
    _i(title="Analytics events: activation funnel", type="Task", status="Done",
       priority="Medium", assignees=["dani"], labels=["growth", "backend"], points=3,
       sprint="Sprint 4", done_creation=-18, done_modified=-11),
    _i(title="Onboarding A/B test harness", type="Task", status="Done",
       priority="Medium", assignees=["dani"], labels=["spike", "growth"], points=3,
       sprint="Sprint 4", done_creation=-16, done_modified=-9),
    _i(title="Fix: keyboard covers weight input", type="Bug", status="Done",
       priority="Medium", assignees=["cris"], labels=["bug", "ios"], points=2,
       sprint="Sprint 5", done_creation=-8, done_modified=-5),
    _i(title="Fix: avatar upload fails over 5MB", type="Bug", status="Done",
       priority="Low", assignees=["han"], labels=["bug", "backend"], points=2,
       sprint="Sprint 5", done_creation=-7, done_modified=-4),
    _i(title="Accessibility: VoiceOver on timer", type="Task", status="Done",
       priority="Medium", assignees=["fae"], labels=["a11y", "ios"], points=3,
       sprint="Sprint 5", done_creation=-6, done_modified=-2),
    _i(title="Perf: cold-start under 1.5s", type="Task", status="Done",
       priority="High", assignees=["ben"], labels=["perf"], points=5,
       sprint="Sprint 5", done_creation=-9, done_modified=-1),

    # one cancelled, for status distribution realism
    _i(title="AR form-check (camera) - shelved", type="Story", status="Cancelled",
       priority="Low", assignees=[], labels=["spike"], points=8, sprint=None,
       done_creation=-15, done_modified=-10),
]


def _due(off):
    return add_days(nowdate(), off) if off is not None else None


def upsert_issues(statuses, labels, sprints):
    name_by_title = {}
    for spec in ISSUES:
        title = spec["title"]
        existing = frappe.db.get_value("Projex Issue", {"project": PROJECT, "title": title})
        fields = {
            "issue_type": spec.get("type", "Task"),
            "status": statuses[spec["status"]],
            "priority": spec.get("priority", "None"),
            "estimate": spec.get("points", 0),
            "start_date": _due(spec.get("start")),
            "due_date": _due(spec.get("due")),
            "cycle": sprints.get(spec["sprint"]) if spec.get("sprint") else None,
            "recurrence": spec.get("recurrence", "None"),
            "reporter": _h("ben"),
            "description": f"<p>{_describe(spec)}</p>",
        }
        if existing:
            doc = frappe.get_doc("Projex Issue", existing)
            for k, v in fields.items():
                setattr(doc, k, v)
            _set_children(doc, spec, labels)
            doc.save(ignore_permissions=True)
            name = existing
        else:
            doc = frappe.get_doc({"doctype": "Projex Issue", "title": title,
                                  "project": PROJECT, **fields})
            _set_children(doc, spec, labels)
            doc.insert(ignore_permissions=True)
            name = doc.name
        name_by_title[title] = name

        _backdate(name, spec)
        _seed_subtasks(name, spec, statuses)
        _seed_comments(name, spec)
    # links need all names resolved first
    for spec in ISSUES:
        for lt, target_title in spec.get("links", []):
            src = name_by_title.get(spec["title"])
            tgt = name_by_title.get(target_title)
            if src and tgt and not frappe.db.exists(
                "Projex Issue Link", {"issue": src, "link_type": lt, "target": tgt}
            ):
                frappe.get_doc({"doctype": "Projex Issue Link", "issue": src,
                                "link_type": lt, "target": tgt}).insert(ignore_permissions=True)
    return name_by_title


def _describe(spec):
    bits = {
        "Bug": "Defect report for the Aurora fitness app.",
        "Story": "User-facing story for the Aurora fitness app.",
        "Epic": "Large initiative tracked across multiple sprints.",
        "Task": "Engineering task for the Aurora fitness app.",
    }
    return bits.get(spec.get("type", "Task"), "Aurora work item.") + \
        f" Priority: {spec.get('priority', 'None')}."


def _set_children(doc, spec, labels):
    doc.set("assignees", [{"user": _h(a)} for a in spec.get("assignees", [])])
    doc.set("labels", [{"label": labels[l]} for l in spec.get("labels", []) if l in labels])
    if spec.get("checklist"):
        doc.set("checklist", [{"title": t, "done": d} for t, d in spec["checklist"]])


def _backdate(name, spec):
    """Push creation/modified into the past for historical 'Done' items so the
    throughput / cycle-time / burndown charts span real weeks."""
    if spec.get("done_modified") is None:
        return
    created = add_days(nowdate(), spec.get("done_creation", spec["done_modified"] - 4)) + " 09:00:00"
    modified = add_days(nowdate(), spec["done_modified"]) + " 17:30:00"
    frappe.db.sql(
        "UPDATE `tabProjex Issue` SET creation=%s, modified=%s WHERE name=%s",
        (created, modified, name),
    )


def _seed_subtasks(parent_name, spec, statuses):
    done_status = statuses["Done"]
    parent = frappe.get_doc("Projex Issue", parent_name)
    for sub_title, is_done in spec.get("subtasks", []):
        full = f"{spec['title']} - {sub_title}"
        if frappe.db.exists("Projex Issue", {"project": PROJECT, "title": full}):
            continue
        frappe.get_doc({
            "doctype": "Projex Issue", "title": full, "project": PROJECT,
            "parent_issue": parent_name, "reporter": _h("ben"),
            "status": done_status if is_done else parent.status,
            "priority": "Medium", "issue_type": "Task",
        }).insert(ignore_permissions=True)


def _seed_comments(name, spec):
    for handle, text in spec.get("comments", []):
        html = f"<p>{text}</p>"
        if frappe.db.exists("Projex Comment", {"issue": name, "content": html}):
            continue
        c = frappe.get_doc({"doctype": "Projex Comment", "issue": name, "content": html})
        c.flags.ignore_permissions = True
        c.owner = _h(handle)
        c.insert(ignore_permissions=True)


def seed_reactions():
    """A couple of emoji reactions on the first comment of two issues."""
    targets = {
        "Apple Health & Google Fit sync": {"👍": ["alice", "han", "ben"], "🚀": ["cris"]},
        "Live workout tracking screen": {"🔥": ["ben", "gia"], "👀": ["fae"]},
    }
    for title, react in targets.items():
        issue = frappe.db.get_value("Projex Issue", {"project": PROJECT, "title": title})
        if not issue:
            continue
        comment = frappe.db.get_value("Projex Comment", {"issue": issue}, "name", order_by="creation asc")
        if not comment:
            continue
        data = {emoji: [_h(h) for h in handles] for emoji, handles in react.items()}
        frappe.db.set_value("Projex Comment", comment, "reactions", json.dumps(data),
                            update_modified=False)


# --------------------------------------------------------------------------- #
# Live-looking activity + inbox (status transitions on a few active issues)
# --------------------------------------------------------------------------- #
def stir_activity(statuses):
    """Drive a few real status transitions so the Activity feed and Inbox have
    natural 'changed status' / 'assigned' entries (fires controller hooks)."""
    frappe.set_user(DEMO_LOGIN)
    moves = [
        ("Rest-timer haptics & sound", "In review"),
        ("Onboarding goal-selection flow", "In review"),
        ("Crash on resume after backgrounding", "In progress"),
    ]
    for title, target in moves:
        name = frappe.db.get_value("Projex Issue", {"project": PROJECT, "title": title})
        if not name:
            continue
        doc = frappe.get_doc("Projex Issue", name)
        if doc.status != statuses[target]:
            doc.status = statuses[target]
            doc.save(ignore_permissions=True)
    frappe.set_user("Administrator")


# --------------------------------------------------------------------------- #
# Docs (PRD / BRD / MOM / Change Request / Note)
# --------------------------------------------------------------------------- #
DOCS = [
    ("Aurora v1 - Product Requirements", "PRD", -30, """
<h2>Vision</h2><p>Aurora is the simplest way to log workouts, track streaks and stay
motivated. v1 targets iOS &amp; Android with Apple Health / Google Fit sync.</p>
<h3>Goals</h3><ul><li>Time-to-first-logged-workout under 60 seconds</li>
<li>7-day retention &gt; 35%</li><li>Crash-free sessions &gt; 99.5%</li></ul>
<h3>Out of scope (v1)</h3><ul><li>Social feed</li><li>Apple Watch app</li>
<li>Nutrition tracking</li></ul>"""),
    ("Aurora Business Requirements", "BRD", -28, """
<h2>Business case</h2><p>Fitness app market is crowded but underserved on
simplicity. Aurora monetizes via <b>Aurora Pro</b> (subscription) after a 7-day trial.</p>
<h3>Success metrics</h3><ul><li>10k installs in first quarter</li>
<li>4% trial-to-paid conversion</li></ul>"""),
    ("Daily Standup - notes", "Standup MOM", -1, """
<p><b>Yesterday:</b> Health sync OAuth landed; rest-timer haptics in review.</p>
<p><b>Today:</b> Live workout screen state machine; chase the Android resume crash.</p>
<p><b>Blockers:</b> Need design sign-off on the share card.</p>"""),
    ("CR-001: Switch analytics to Amplitude", "Change Request", -6, """
<h2>Change</h2><p>Move activation-funnel analytics from the in-house pipeline to
Amplitude for faster iteration.</p><h3>Impact</h3><ul><li>2 days eng work</li>
<li>Re-instrument 8 events</li><li>Privacy review required</li></ul>
<p><b>Decision:</b> Approved for Sprint 5.</p>"""),
    ("Research: onboarding drop-off", "Note", -12, """
<p>From 12 user interviews: the goal-selection step is where most users hesitate.
Suggest reducing to 3 archetypes and deferring detailed targets to after first log.</p>"""),
]


def upsert_docs():
    for title, dtype, off, content in DOCS:
        if frappe.db.exists("Projex Doc", {"project": PROJECT, "title": title}):
            continue
        frappe.get_doc({
            "doctype": "Projex Doc", "project": PROJECT, "title": title,
            "doc_type": dtype, "doc_date": add_days(nowdate(), off),
            "content": content.strip(),
        }).insert(ignore_permissions=True)


# --------------------------------------------------------------------------- #
# Inbox notifications for the dev login (MOB-flavoured)
# --------------------------------------------------------------------------- #
def seed_inbox():
    if not frappe.db.exists("User", DEMO_LOGIN):
        return
    samples = [
        ("mention", "alice", "Apple Health & Google Fit sync", "Mentioned you: can you review the merge logic?"),
        ("assigned", "ben", "Workout summary share card", "Assigned you to design the share card"),
        ("review", "fae", "Onboarding goal-selection flow", "Requested your review"),
        ("comment", "han", "Crash on resume after backgrounding", "Commented: repro is Pixel-only"),
        ("status", "cris", "Rest-timer haptics & sound", "moved to In review"),
        ("due", "ben", "Crash on resume after backgrounding", "is due today"),
    ]
    for ntype, actor, title, snippet in samples:
        issue = frappe.db.get_value("Projex Issue", {"project": PROJECT, "title": title})
        if not issue:
            continue
        if frappe.db.exists("Projex Notification",
                            {"user": DEMO_LOGIN, "issue": issue, "notification_type": ntype,
                             "snippet": snippet}):
            continue
        frappe.get_doc({
            "doctype": "Projex Notification", "user": DEMO_LOGIN,
            "notification_type": ntype, "actor": _h(actor), "issue": issue,
            "snippet": snippet, "is_read": 0,
        }).insert(ignore_permissions=True)


# --------------------------------------------------------------------------- #
def debug_run():
    import traceback
    try:
        return run()
    except Exception:
        traceback.print_exc()
        raise


def run():
    ensure_labels()
    statuses = _status_map()
    labels = _label_map()
    frame_project()
    sprints = upsert_sprints()
    upsert_issues(statuses, labels, sprints)
    seed_reactions()
    stir_activity(statuses)
    upsert_docs()
    seed_inbox()
    frappe.db.commit()

    n_issue = frappe.db.count("Projex Issue", {"project": PROJECT})
    print("Aurora (MOB) populated. Counts:")
    for dt, flt in [
        ("Projex Issue", {"project": PROJECT}),
        ("Projex Cycle", {"project": PROJECT}),
        ("Projex Doc", {"project": PROJECT}),
        ("Projex Comment", None),
        ("Projex Activity", {"project": PROJECT}),
        ("Projex Notification", {"user": DEMO_LOGIN}),
    ]:
        if dt == "Projex Comment":
            issues = frappe.get_all("Projex Issue", filters={"project": PROJECT}, pluck="name")
            n = frappe.db.count("Projex Comment", {"issue": ["in", issues or [""]]})
        else:
            n = frappe.db.count(dt, flt)
        print(f"  {dt:22} {n}")
    return {"issues": n_issue}
