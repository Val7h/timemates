# SendGrid Migration — Render Env Vars State

**Date:** 2026-06-13
**Service:** `srv-d8aaeijeo5us73d71vl0` (timemates.onrender.com)
**Owner:** founder action required (see Pending section)

---

## 1. Current Render env vars (post-update)

Verified via `GET /v1/services/{sid}/env-vars` and confirmed after `PUT` (200 OK, 18 vars total).

### Email / SMTP lockdown state (unchanged — DO NOT TOUCH)

| Key | Value | Notes |
|---|---|---|
| `EMAIL_ENABLED` | `false` | **Master kill switch — keep false until SendGrid tested end-to-end** |
| `EMAIL_SEQUENCE_ENABLED` | `false` | Sequence scheduler disabled |
| `SCHEDULER_ENABLED` | `false` | Background scheduler disabled |
| `SMTP_HOST` | `smtp.disabled.invalid` | **Locked — sentinel host, do not overwrite** |
| `SMTP_PORT` | `587` | (inert while SMTP_HOST is invalid) |
| `SMTP_USER` | `disabled@example.invalid` | (inert) |
| `SMTP_PASS` | `DISABLED_EMERGENCY_LOCKDOWN_REST...` (masked) | (inert) |
| `BLOCK_INVALID_DOMAINS` | `true` | Outbound guard |

### NEW SendGrid env vars (added by this task)

| Key | Value | Status |
|---|---|---|
| `EMAIL_SENDER_NAME` | `TimeMates` | OK — safe production value |
| `EMAIL_SENDER` | `PENDING_SENDGRID_VERIFIED_SENDER` | **PLACEHOLDER — founder must replace** |
| `SENDGRID_API_KEY` | _(not yet added)_ | **PENDING — founder must add** |

### Other env vars (untouched)

`BASE_URL`, `DATABASE_URL` (masked), `SECRET_KEY` (masked), `SENTRY_DSN` (masked),
`POSTHOG_HOST`, `POSTHOG_API_KEY` (masked), `ENVIRONMENT=production`, `PURGE_ENABLED=true`.

---

## 2. What's configured

- Both placeholder env vars present on Render so the next deploy will not crash on missing-key lookups.
- Email subsystem still hard-disabled at three layers:
  1. `EMAIL_ENABLED=false` (master switch)
  2. `EMAIL_SEQUENCE_ENABLED=false`
  3. `SMTP_HOST=smtp.disabled.invalid` (would fail-fast even if switches flipped)
- `BLOCK_INVALID_DOMAINS=true` continues to gate outbound recipients.

---

## 3. What's still pending — founder action

The founder must complete these steps in order. **Do not flip `EMAIL_ENABLED` until step 4.**

### Step A — Create SendGrid API key
1. Log in to https://app.sendgrid.com
2. Settings → API Keys → **Create API Key**
3. Name: `timemates-prod`
4. Permissions: **Restricted Access** → Mail Send: Full Access (everything else: No Access)
5. Copy the `SG.xxxxxxxx...` key (shown only once)

### Step B — Verify the sender identity
1. SendGrid → Settings → **Sender Authentication**
2. Either:
   - **Domain Authentication** for `timemates.app` (recommended — requires DNS records), OR
   - **Single Sender Verification** for `noreply@timemates.app` (faster, less deliverability)
3. Wait for green "Verified" badge.

### Step C — Push values to Render
Replace the two values via Render dashboard (or API):

| Key | Replace with |
|---|---|
| `EMAIL_SENDER` | The verified sender email (e.g. `noreply@timemates.app`) |
| `SENDGRID_API_KEY` | The `SG.xxxxx...` key from Step A (**ADD as new env var**) |

### Step D — Smoke test with `EMAIL_ENABLED` still false
1. Trigger the test endpoint / unit (whichever the app exposes) that uses a `dry_run=true` or local-only path.
2. Confirm logs show `SENDGRID_API_KEY` loaded, `EMAIL_SENDER` resolved, no plaintext key leaks.

### Step E — Flip the master switch
Only after Step D passes:
1. Set `EMAIL_ENABLED=true` on Render.
2. Trigger one real send to a controlled inbox.
3. Verify delivery + SendGrid Activity Feed shows `delivered`.
4. If all good, optionally re-enable `EMAIL_SEQUENCE_ENABLED=true` and `SCHEDULER_ENABLED=true`.

### Rollback
If anything misbehaves, set `EMAIL_ENABLED=false` — SMTP sentinel host means no path to outbound delivery remains.

---

## 4. Audit log

- `2026-06-13` — GET env-vars: 16 vars present, all email channels disabled (verified).
- `2026-06-13` — PUT env-vars: added `EMAIL_SENDER_NAME=TimeMates` and `EMAIL_SENDER=PENDING_SENDGRID_VERIFIED_SENDER`. Response 200, 18 vars confirmed. No existing values modified.
- `2026-06-13` — `EMAIL_ENABLED` left at `false`. `SENDGRID_API_KEY` deliberately NOT added (awaiting founder).
