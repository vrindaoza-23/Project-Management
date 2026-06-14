# Deploying Projex

Projex is a standard Frappe v16 app. It needs Frappe; **ERPNext is optional**
(only for the timesheet/customer integration — without it those features hide).

On install the `after_install` hook creates the Projex roles and the six
default statuses, so a fresh site is usable immediately. **Do not run
`projex.seed.run` in production** — it's demo data.

---

## Option A — Frappe Cloud (easiest)

1. Push this app to a Git repo Frappe Cloud can read.
2. In Frappe Cloud → **Create a new Bench** on the `version-16` stack.
3. Add the app from your repo (and ERPNext if you want the integration).
4. Create a site on that bench and install `projex`.
5. Configure (see **Configuration** below). Done — FC handles HTTPS, backups, updates.

---

## Option B — Self-host with frappe_docker (custom image)

Uses the official [frappe_docker](https://github.com/frappe/frappe_docker) build flow.

1. Edit [`deploy/apps.json`](deploy/apps.json) — set your Projex repo URL (drop
   the ERPNext entry if you don't need the integration).
2. Build a custom image:
   ```bash
   export APPS_JSON_BASE64=$(base64 -w0 deploy/apps.json)
   docker build \
     --build-arg=FRAPPE_BRANCH=version-16 \
     --build-arg=APPS_JSON_BASE64=$APPS_JSON_BASE64 \
     --tag=yourorg/projex:latest \
     --file=images/layered/Containerfile .          # from a frappe_docker checkout
   ```
3. Deploy with frappe_docker's `compose.yaml` + overrides (mariadb, redis,
   nginx/traefik for HTTPS). Point the image to `yourorg/projex:latest`.
4. Create the site and install the app:
   ```bash
   docker compose exec backend bench new-site <site> --install-app projex \
     --mariadb-root-password <pw> --admin-password <pw>
   ```

---

## Configuration

```bash
# AI (optional — features hide when unset; never commit keys)
bench --site <site> set-config projex_ai_provider openai
bench --site <site> set-config projex_ai_api_key <key>

# Email (for notification emails) — configure an outgoing Email Account in-app,
# or set SMTP via site config / Frappe Cloud mail settings.
```

ERPNext integration is auto-detected: if the `erpnext` app is installed, the
Customer/Project links and time-logging turn on automatically.

---

## Operations

- **Backups:** `bench --site <site> backup --with-files` (schedule via cron, or
  use Frappe Cloud's managed backups). Store off-box.
- **HTTPS:** terminate at nginx/traefik (frappe_docker) or `bench setup lets-encrypt`.
- **Updates:** `bench update` / rebuild the image; always run
  `bench --site <site> migrate` after deploying new code (re-applies defaults &
  ERPNext custom fields idempotently).
- **Monitoring:** wire Frappe's error log + an external collector (e.g. Sentry)
  before going wide.

## Pre-launch checklist

- [ ] CI green on the repo (backend tests + frontend build + Playwright smoke)
- [ ] HTTPS + a real domain
- [ ] Scheduled, off-box backups verified by a test restore
- [ ] SMTP configured and a test notification email received
- [ ] Admin password rotated; no secrets in the repo
- [ ] Load check on the largest expected project (List/Board cap is 500 tasks/req)
