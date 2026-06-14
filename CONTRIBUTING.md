# Contributing to Projex

Thanks for your interest in improving Projex!

## Ground rules

- **No hardcoded domain data in the frontend.** Everything comes from the API.
  Use the idempotent seed (`projex.seed.run`) for demo content.
- **Inherit, don't reinvent.** Auth, permissions, REST, realtime, and jobs come
  from Frappe. Write only the product layer.
- **Hold the v1 scope ceiling.** No custom-field UI, workflow engine, dashboards,
  or time-tracking UI beyond the ERPNext timesheet link.
- **Feel is a feature.** Keep mutations optimistic, realtime in sync, and core
  flows keyboard-operable.

## Dev setup

```bash
# In a Frappe v16 bench
bench get-app projex <repo-url> --branch version-16
bench --site <site> install-app projex
bench --site <site> execute projex.seed.run

# Frontend
cd apps/projex/frontend && yarn install && yarn dev
```

## Code style

Install pre-commit hooks (ruff, eslint, prettier, pyupgrade):

```bash
cd apps/projex
pre-commit install
```

## Tests

```bash
bench --site <site> run-tests --app projex --skip-before-tests
```

Add tests for new DocType logic (controllers, permissions, API). Backend tests
use `frappe.tests.classes.unit_test_case.UnitTestCase` and build their own
fixtures.

## Pull requests

- Keep PRs focused; use conventional commit messages (`feat:`, `fix:`, `chore:`).
- Describe what changed and how you verified it.
- Ensure CI is green (lint + tests + frontend build).
