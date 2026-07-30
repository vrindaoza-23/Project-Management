# Projex → PSA for Frappe Partners — Delivery Roadmap

**Goal:** Evolve Projex from a Linear-style internal issue tracker into a
professional-services (PSA) product that Frappe partners can use to run
**client ERP implementations** end-to-end — plan, deliver, get sign-off,
and bill — natively on top of Frappe/ERPNext.

This document is the working plan. It is deliberately concrete: DocTypes,
fields, APIs, and the order we build them.

---

## Decisions locked (2026-07-26)

| Decision | Choice |
|---|---|
| Billing models to support | **All three:** milestone/fixed-fee, time & materials, retainer/AMC |
| Time tracking | **Write to ERPNext Timesheet** when ERPNext present; fall back to native `Projex Time Log` otherwise |
| Client portal v1 | **View status + approve deliverables/UAT sign-off + raise & track issues** |

---

## Product framing

Projex already has a strong **execution core** (Projects → Issues → Cycles,
List/Board/Gantt/Calendar/Backlog, comments, notifications, reports, GitHub +
read-only ERPNext finance). We keep all of it. We add the **PSA layer** that the
implementation-delivery use case needs and that a dev issue-tracker lacks:

1. **Methodology** — phases + milestones + deliverables with client sign-off
2. **Money** — billable time in ERPNext's ledger, and invoice generation for all three billing models
3. **Repeatability** — project templates that instantiate a standard implementation plan
4. **Client relationship** — a portal where the customer sees status, signs off, and raises issues

---

## Data model additions

### New DocTypes

| DocType | Kind | Purpose |
|---|---|---|
| `Projex Phase` | standard | Methodology phase within a project (Discovery, Config, Data Migration, UAT, Training, Go-Live, Hypercare). Ordered. |
| `Projex Milestone` | standard | Billing + delivery unit. Belongs to a project, optionally a phase. Carries billing type/amount and client sign-off state. |
| `Projex Deliverable` | standard | A signed-off artifact under a milestone (e.g. "Chart of Accounts configured"). Holds the approval audit trail. |
| `Projex Billing Rate` | child (on Project) | Role → hourly rate for T&M billing. |
| `Projex Project Template` | standard | A reusable implementation blueprint. |
| `Projex Template Phase` | child | Phase rows inside a template. |
| `Projex Template Task` | child | Task rows inside a template phase. |
| `Projex Template Milestone` | child | Milestone rows inside a template. |

### Extensions to existing DocTypes

- **Projex Project** (via ERPNext custom fields file, gated to ERPNext-installed sites):
  add `contract_value`, `billing_currency`, `billing_rates` (child `Projex Billing Rate`),
  keep existing `erpnext_customer` / `erpnext_project`.
- **Projex Issue**: add optional `phase` (Link → Projex Phase) and `milestone` (Link → Projex Milestone)
  so execution work rolls up to the delivery/billing structure.
- **Projex Time Log**: add `erpnext_timesheet` (Data — the ERPNext Timesheet name it synced to),
  `billing_rate`, and `billed` (Check) so we never double-bill.

### Projex Milestone — key fields

```
project (Link Projex Project, reqd)
phase (Link Projex Phase)
milestone_name (Data, reqd)
description (Text Editor)
target_date (Date)
status (Select: Planned / In Progress / Delivered / Approved / Rejected)
billing_type (Select: Fixed / Time & Materials / Retainer / Non-billable)
billing_amount (Currency)              # fixed-fee amount
billing_percent (Percent)             # optional % of contract_value
client_signoff_status (Select: Not Requested / Pending / Approved / Changes Requested)
signoff_requested_on (Datetime)
signed_off_by (Data)                  # client contact email/name
signed_off_on (Datetime)
signoff_note (Small Text)
invoiced (Check)
sales_invoice (Data)                  # ERPNext Sales Invoice name
```

---

## Build phases

### Phase 1 — Billable & client-facing (the partner MVP)

**1a. Delivery backbone** *(in progress)*
- DocTypes: `Projex Phase`, `Projex Milestone`, `Projex Deliverable`, `Projex Billing Rate`.
- Controllers: milestone status derives from its deliverables; sign-off transitions log to
  `Projex Activity`; deliverable approval writes an immutable audit line.
- APIs: `get_delivery_plan(project)`, `create/update/delete_phase`, `create/update/delete_milestone`,
  `create/update/delete_deliverable`, `request_signoff`, `record_signoff` (internal), plus the
  portal-facing `client_approve_deliverable` / `client_reject_deliverable`.

**1b. ERPNext Timesheet write-back**
- Extend `log_time` / `create_time_log` in `api.py`: when ERPNext is installed and the project has an
  `erpnext_project`/`erpnext_customer`, also create an **ERPNext Timesheet** (one per user/day, append
  time_log rows) and stamp `erpnext_timesheet` back on the `Projex Time Log`. Native log stays as the
  projex-side source of truth; ERPNext gets the billing/costing copy. Fully guarded — no-op without ERPNext.

**1c. Billing / invoice generation**
- `generate_invoice(milestone)` — **Fixed**: create a draft ERPNext Sales Invoice for `billing_amount`
  (or `billing_percent` × `contract_value`) against the customer, mark milestone `invoiced` + link.
- `generate_tm_invoice(project, from, to)` — **T&M**: sum unbilled billable time × role rate, create a
  Sales Invoice with per-role lines, mark those `Projex Time Log`s `billed`.
- `Projex Retainer` handling — **Retainer/AMC**: monthly recurring milestone → recurring invoice via
  ERPNext Auto Repeat or a scheduled job.
- All invoice creation produces **drafts** (never auto-submits) — the partner reviews in ERPNext.

**1d. Project templates**
- `Projex Project Template` (+ child phases/tasks/milestones). Ship 1 built-in **"ERPNext Implementation"**
  template (standard phases + typical deliverables).
- API `instantiate_template(template, project)` — fan out phases, tasks, milestones onto a project,
  date-shifted from a start date.

**1e. Client portal**
- Role `Projex Client`; portal pages under `/projex/portal/...` (or reuse the SPA with a client-scoped
  boot + route guard). Customer contacts are Website Users linked to the project's customer.
- Screens: **Project status** (phases, milestones, %, dates — read-only), **Deliverable sign-off**
  (approve / request changes with note; writes audit), **Raise & track issues** (create + watch).
- Strict row-level permission: a client sees only projects for their customer, and only client-safe fields.

### Phase 2 — Portfolio economics
- Cross-project resource capacity & utilization; budget vs actual; margin dashboards (extend `FinanceView`).
- Milestone burn-up and delivery health across the portfolio.

### Phase 3 — Governance & support
- RAID register (Risks/Actions/Issues/Decisions) DocType + view.
- Auto-generated client status reports (weekly).
- Wire **Frappe Helpdesk** integration for hypercare SLA (the "Upcoming" card).

---

## Guardrails
- **ERPNext stays optional.** Every ERPNext write is guarded by `"erpnext" in frappe.get_installed_apps()`.
  Core installs and runs on a plain Frappe site (existing project invariant).
- **Invoices are drafts.** We never submit financial documents automatically.
- **No double-billing.** Time logs and milestones carry `billed`/`invoiced` flags checked before invoicing.
- **Idempotent setup.** New custom fields go through the existing `after_migrate` hook.
- Match existing conventions: `Projex ` DocType prefix, `Projex` module, the standard 4-role permission block.

---

## Progress log
- 2026-07-26: Roadmap authored. Starting Phase 1a (delivery backbone DocTypes).
- 2026-07-26: **Phase 1a–1d shipped & verified** on site `asifv2` (frappe v16 + erpnext v17):
  - **1a Delivery backbone** — DocTypes `Projex Phase`, `Projex Milestone`, `Projex Deliverable`,
    `Projex Billing Rate` (child); controllers with milestone status rollup from deliverables and
    sign-off transitions; `contract_value`/`billing_currency`/`billing_rates` custom fields on Project;
    `phase`/`milestone` link fields added to `Projex Issue`. API in `projex/delivery.py`
    (`get_delivery_plan`, phase/milestone/deliverable CRUD, `request_signoff`, `record_signoff`).
  - **1b ERPNext Timesheet write-back** — `create_time_log` now mirrors each native Projex Time Log
    into an ERPNext Timesheet (guarded, best-effort, link stamped back); `delete_time_log` cleans up
    the draft mirror. New Time Log fields: `billing_rate`, `billed`, `sales_invoice`, `erpnext_timesheet`.
  - **1c Billing** — `projex/billing.py`: `generate_milestone_invoice` (Fixed/Retainer → draft Sales
    Invoice), `generate_tm_invoice` (unbilled billable time × rate card, grouped by role). Drafts only;
    double-bill guards via `invoiced`/`billed`; income account resolved for the line rows.
  - **1d Project templates** — `Projex Project Template` (+ child phase/task/milestone tables),
    `projex/project_templates.py::instantiate_template`, and a built-in **"ERPNext Implementation"**
    template (7 phases, 17 tasks, 4 billing milestones, deliverables) seeded via `after_migrate`.
  - All slices verified end-to-end via `bench execute`; test data cleaned up afterward.
- 2026-07-26: **Phase 1e (client portal) shipped & verified.**
  - Portal-only role **Projex Client** (`desk_access=0`) + **Projex Client Access** doctype (user→project grant).
  - [portal.py](../projex/portal.py) — client-scoped API: `client_bootstrap`, `client_get_delivery_plan`
    (billing internals stripped), `client_review_deliverable` (approve / request changes → rolls up to
    milestone sign-off), `client_list_issues`, `client_raise_issue`, plus partner-side
    `grant_client_access` / `revoke_client_access` / `list_client_access`.
  - Self-contained portal page [www/projex_portal.html](../projex/www/projex_portal.html) at **/projex-portal**
    (status hero + delivery accordion with Approve / Request-changes + Issues tab). Login required.
  - Verified end-to-end over real HTTP+CSRF as a client user: page render, guest→login redirect, bootstrap,
    delivery plan, deliverable approval, issue raise/list, and **cross-project isolation** (PermissionError on
    a non-owned project). Test data + user cleaned up; dev server stopped.
  - Gotchas hit & recorded in memory: hyphenated www `.py` isn't importable (route rule workaround); `boot`
    is a reserved context key; `bench serve` (no supervisord); `default_site` is pos.localhost.

- 2026-07-26: **Partner-side SPA shipped & verified in-browser.**
  - New **Delivery** surface (tab) in `ProjectView.vue` → [DeliveryView.vue](../frontend/src/pages/DeliveryView.vue):
    progress hero; phases → milestones (billing badge + status/sign-off pills) → deliverables; manager actions
    for add/delete phase-milestone-deliverable, send-to-client / pull-back, request sign-off, mark approved,
    **generate invoice** (Fixed/Retainer, when a customer is linked), **Bill time** (T&M), **Apply template**
    (empty-state), and a **Clients** panel (grant/revoke portal access).
  - Backend: `get_delivery_plan` now also returns `can_manage`, `currency`, `contract_value`, `can_invoice`.
  - `yarn build` clean; verified in a real browser (logged in as a Projex Admin): the Delivery tab renders the
    full 7-phase plan, and a live "Send to client" click flipped a deliverable Draft→In review and rolled the
    milestone In progress→Delivered. Test user/project cleaned up; dev server stopped.

- 2026-07-26: **Apply-template-on-create shipped & verified in-browser.**
  - [CreateProjectDialog.vue](../frontend/src/components/CreateProjectDialog.vue) now offers a
    "Delivery template" picker (default "None — start blank") and, when a template is chosen, a start-date
    field. On submit it creates the project, then calls `instantiate_template` before navigating; a template
    failure is non-fatal (project still opens, with a warning toast).
  - Verified in a real browser: created "Contoso ERP Rollout" with the ERPNext Implementation template →
    landed on the project with a full 7-phase delivery plan, dates shifted from the chosen start date.

**Phase 1 + partner console + template-on-create complete.** Next candidates: Phase 2 (portfolio economics
— cross-project utilization, budget-vs-actual, margin dashboards); structured resource roles for T&M;
inline milestone editing in DeliveryView.
