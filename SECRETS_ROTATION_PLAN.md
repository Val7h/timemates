# SECRETS ROTATION PLAN — timeMates

**Audit Date:** 2026-06-07
**Auditor:** DevSecOps Specialist
**Severity:** P0 / URGENT — DEFERRED to next session per founder decision
**Repository:** C:/Users/Admin/timeMates

---

## ⏸️ ROTATION DEFERRED - PENDING TASKS

**Founder decision (2026-06-07):** Postponed rotation to focus on Day 2 observability stack.

**Pending items:**

1. **TimeMates Neon rotation:**
   - Current endpoint: `ep-soft-morning-apoyasgn` (confirmed via Render API)
   - Status: Production stable with leaked credential still active
   - Risk: Medium (credential in git history but no public repo evidence yet)
   - Next session: Use Neon API or manual UI on correct project

2. **Wealth Lab accidental rotation:**
   - User accidentally reset password on `ep-hidden-poetry-apaoqurp` project
   - New password obtained: `npg_J1wBPfuUi7YA` (was tested but reverted)
   - **Action needed:** Update `.env` of Wealth Lab project locally with new connection string:
     ```
     postgresql://neondb_owner:npg_J1wBPfuUi7YA@ep-hidden-poetry-apaoqurp-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
     ```
   - Location: C:/Users/Admin/Whelth-Lab/ (or wherever Wealth Lab project lives)

**Resume rotation:** Run `/loop force-task-secrets-rotation` next session.

---

---

## Executive Summary

A git-history audit of the `timeMates` repository found **one confirmed leaked production credential** committed to the `master` branch, plus several additional concerns. The current `.env` file is correctly gitignored and was never committed, but a one-off script (`connect_neon.py`) was committed with a hardcoded Neon Postgres connection string containing a live password.

**Verdict: URGENT_ROTATE required for the Neon database credential.**

---

## Findings

### CONFIRMED LEAK — Neon `DATABASE_URL`

- **File:** `connect_neon.py`
- **Commit:** `2905930` — "feat: Script para conectar e popular Neon diretamente" (2026-06-06)
- **Also re-introduced in:** `5950dd2` — "Feat: Implement all 8 features for weeks 1-3 in parallel"
- **Leaked value pattern:** `postgresql://neondb_owner:npg_xNUu0X********@ep-soft-morning-apoyasgn.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require`
- **Exposure:** Present in `git log -p --all`. If the repo was ever pushed to a public remote, treat as fully compromised.

### Repository Hygiene

| Check | Result |
|---|---|
| `.env` listed in `.gitignore` | YES |
| `.env` ever committed to history | NO |
| `.env.example` committed | YES (expected, contains only placeholders like `your-...`) |
| `vapid_keys.json` tracked | NO (untracked, but NOT in `.gitignore` — RISK of future accidental commit) |
| `gitleaks` installed | NO |

### Secrets Inventory (from `.env` + `.env.example`)

| Secret | In current `.env` | Leaked in git history | Action |
|---|---|---|---|
| `DATABASE_URL` (Neon) | (referenced) | **YES — confirmed leak in `connect_neon.py`** | **ROTATE IMMEDIATELY** |
| `JWT_SECRET` | (referenced) | No real value found (only `...` placeholders) | Rotate as precaution |
| `GOOGLE_CLIENT_SECRET` | (referenced) | Only `"your-client-secret"` placeholder found | Rotate as precaution |
| `MICROSOFT_CLIENT_SECRET` | (referenced) | Only `"your-client-secret"` placeholder found | Rotate as precaution |
| `VAPID_PRIVATE_KEY` | (referenced) | No real value in history, but `vapid_keys.json` exists locally untracked and NOT gitignored | Add to `.gitignore` + rotate as precaution |
| `STRIPE_SECRET_KEY` | YES | Only `sk_test_xxxxx` / `sk_test_...` placeholders found | No action (test keys), rotate before going live |
| `STRIPE_WEBHOOK_SECRET` | YES | Not found | Rotate as precaution |
| `STRIPE_PUBLIC_KEY` | YES | Only placeholders | Public key — no rotation needed |
| `SMTP_PASS` | YES | Not found | Rotate as precaution |

---

## Rotation Procedures

### 1. Neon `DATABASE_URL` — URGENT

1. Log in to https://console.neon.tech
2. Open project `ep-soft-morning-apoyasgn` (or whichever maps to `neondb`).
3. Go to **Roles** → `neondb_owner` → **Reset password**.
4. Copy the new connection string (sslmode=require).
5. Update locally: edit `.env`, set new `DATABASE_URL=...`.
6. Update on Render: Dashboard → Service → **Environment** → edit `DATABASE_URL` → **Save Changes** (triggers redeploy).
7. Verify connectivity: `python -c "import os; from sqlalchemy import create_engine; create_engine(os.getenv('DATABASE_URL')).connect()"`.
8. **Purge history (optional but recommended):**
   - `git filter-repo --path connect_neon.py --invert-paths` (or BFG Repo-Cleaner).
   - Force-push: coordinate with all collaborators first.
9. **Sanitize `connect_neon.py`** in working tree: replace hardcoded string with `os.getenv("DATABASE_URL")`. Commit the fix even if history isn't purged.

### 2. `JWT_SECRET`

1. Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
2. Update `.env` locally.
3. Update Render env var `JWT_SECRET`.
4. **Impact:** All existing user sessions/JWTs will be invalidated — users must re-login. Announce or schedule during low-traffic window.

### 3. `GOOGLE_CLIENT_SECRET`

1. Go to https://console.cloud.google.com → APIs & Services → Credentials.
2. Open the OAuth 2.0 Client ID used by timeMates.
3. Click **Reset Secret** (or create a new one and delete the old after cutover).
4. Update `.env` and Render env var `GOOGLE_CLIENT_SECRET`.
5. Verify Google login still works in production.

### 4. `MICROSOFT_CLIENT_SECRET`

1. Go to https://portal.azure.com → Azure AD / Entra ID → App registrations → timeMates app.
2. **Certificates & secrets** → **New client secret** (generate new before deleting old).
3. Update `.env` and Render env var `MICROSOFT_CLIENT_SECRET`.
4. Verify Microsoft login still works.
5. Delete the old secret entry in Azure portal after confirmed cutover.

### 5. `VAPID_PRIVATE_KEY` (Web Push)

1. Generate new keypair: `npx web-push generate-vapid-keys` (or the Python `py_vapid` CLI).
2. Update `.env` with new `VAPID_PRIVATE_KEY` and `VAPID_PUBLIC_KEY`.
3. Update Render env vars `VAPID_PRIVATE_KEY` and `VAPID_PUBLIC_KEY`.
4. **Impact:** All existing push subscriptions become invalid. Users will be re-prompted to subscribe on next visit.
5. **IMMEDIATE:** Add `vapid_keys.json` to `.gitignore` to prevent future accidental commits.

### 6. Stripe Keys

- **`STRIPE_SECRET_KEY`** (currently `sk_test_*`): Only rotate if switching to live, or if you suspect leak.
  - Dashboard → Developers → API keys → **Roll secret key**.
- **`STRIPE_WEBHOOK_SECRET`**: Dashboard → Developers → Webhooks → endpoint → **Roll secret**. Update `.env` + Render.
- After rotation, re-test a webhook event using Stripe CLI: `stripe trigger payment_intent.succeeded`.

### 7. `SMTP_PASS`

1. Provider depends on `SMTP_HOST` (Gmail / SendGrid / Mailgun / etc.).
2. Generate a new app password or API key from the provider.
3. Update `.env` and Render env var `SMTP_PASS`.
4. Test by triggering a transactional email (password reset).

---

## Render Deployment — Where to Update

For each rotated secret:

1. https://dashboard.render.com → select the timeMates service.
2. Left sidebar → **Environment**.
3. Locate the variable, click the value, paste new value, click **Save Changes**.
4. Render automatically redeploys on env var change. Monitor the **Logs** tab for startup errors.

---

## Preventive Hardening (do this NOW)

1. **Add to `.gitignore`:**
   ```
   vapid_keys.json
   .env.local
   .env.production
   .env.*.local
   *.pem
   *.key
   secrets/
   ```
2. **Sanitize `connect_neon.py`** to read `DATABASE_URL` from env, never hardcode.
3. **Install `gitleaks` pre-commit hook:**
   ```
   pip install pre-commit
   # add .pre-commit-config.yaml with zricethezav/gitleaks
   pre-commit install
   ```
4. **Add CI step:** Run `gitleaks detect --source . --redact` on every push (GitHub Actions / Render build hook).
5. **Audit collaborators:** Confirm who has pulled the leaked commit. If pushed to a public remote, assume the credential is fully compromised (bots scrape GitHub within minutes).

---

## Recommendation

**URGENT_ROTATE** — Rotate the Neon `DATABASE_URL` today. Treat all other secrets as precautionary rotations within 7 days. Add `vapid_keys.json` to `.gitignore` before next commit.
