# Projex

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Built on Frappe](https://img.shields.io/badge/built%20on-Frappe-0089ff.svg)](https://frappeframework.com)

A Linear-grade, keyboard-first project-management app built on the
[Frappe Framework](https://frappeframework.com), with a Vue 3 + [frappe-ui](https://ui.frappe.io)
SPA and optional, native **ERPNext** integration.

Projex isn't "another Linear clone." Its reason to exist is the wedge: a
polished, opinionated issue tracker that lives inside your Frappe permissions
and links natively to ERPNext (timesheets, customers/projects) — built on
inherited Frappe infrastructure (auth, permissions, REST, realtime, jobs).

## Features (v1)

- Workspaces → Projects → Issues with status, priority, assignees, labels, sub-issues, due dates
- **Cycles** (time-boxed iterations)
- Views: **List** (grouped by status), **Board** (kanban, drag to change status), **Roadmap**
- **Task drawer**: description, subtasks, comments with @mentions, metadata rail
- **Command palette** (⌘K) + keyboard navigation (`g i / g m / g r`, `c`, `Esc`)
- **Optimistic updates** + **realtime sync** across clients (socket.io)
- In-app **notifications** (inbox)
- **ERPNext wedge** (optional): log time from an issue → ERPNext Timesheet; link a project to an ERPNext Customer/Project. Degrades cleanly when ERPNext is absent.
- **AI** behind a provider abstraction — disabled and hidden when no key is configured

## Requirements

- Frappe Framework v16 (Python 3.12+; the reference dev env uses 3.14 + Node 24)
- A Frappe bench with MariaDB and Redis
- ERPNext v16 *(optional — only needed for the timesheet/customer integrations)*

## Install

```bash
# From your bench directory
bench get-app projex https://github.com/<your-org>/projex --branch version-16
bench --site <your-site> install-app projex
bench --site <your-site> migrate
```

Installation automatically creates the **Projex roles** (Admin / Member / Guest)
and the **six default statuses** (Backlog → Cancelled) via the `after_install`
hook — no manual setup needed. The app is usable on a clean site immediately.

### Seed realistic demo data (optional — NOT for production)

```bash
bench --site <your-site> execute projex.seed.run
```

This creates a demo workspace (Pinecone Labs) with 6 projects, ~30 tasks across
statuses and priorities, subtasks, labels, cycles, and comments. Idempotent
(upserts by natural key). **Do not run on a production site** — it's demo data.

### Open the app

```
http://<your-site>:8000/projex
```

## Develop the frontend

```bash
cd apps/projex/frontend
yarn install
yarn dev      # Vite dev server with proxy to the bench
yarn build    # builds into projex/public/frontend and copies the page to projex/www
```

## AI configuration (optional)

AI features are off by default and degrade gracefully. To enable, configure a
provider key in site config (never commit keys):

```bash
bench --site <your-site> set-config projex_ai_provider openai
bench --site <your-site> set-config projex_ai_api_key <your-key>
```

See [`.env.example`](.env.example).

## Architecture

- **Backend** (`projex/`): DocTypes (Workspace, Project, Issue, Status, Label,
  Cycle, Comment, Notification), controllers with per-project issue keys
  (`BIL-12`), realtime emits, project-membership row-level permissions
  (`permission_query_conditions`), whitelisted API in `projex/api.py`.
- **Frontend** (`frontend/`): Vue 3 + Vite + frappe-ui SPA. Data via frappe-ui
  resources — **no hardcoded domain data**; everything comes from the API.
- **ERPNext integration** is applied as Custom Fields only when ERPNext is
  installed (`projex/setup/erpnext_integration.py`), so core stays installable
  on a plain Frappe site.

## Tests

```bash
bench --site <your-site> run-tests --app projex --skip-before-tests
```

## Contributing

This app uses `pre-commit` for formatting and linting (ruff, eslint, prettier,
pyupgrade). See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
cd apps/projex
pre-commit install
```

## License

[AGPL-3.0](license.txt) — consistent with Frappe/ERPNext.
