# Sentry Setup Guide — TimeMates

This guide walks you through enabling production error tracking with Sentry for TimeMates.

## Overview

Sentry is integrated with **graceful degradation**:

- If `SENTRY_DSN` is set, the SDK initializes and tracks unhandled exceptions, performance, and SQLAlchemy queries.
- If `SENTRY_DSN` is **not** set, the app boots normally with error tracking disabled. No errors, no crashes.

## 1. Create a Sentry Account

1. Go to https://sentry.io/signup/
2. Sign up with email or GitHub/Google SSO.
3. Choose the **Developer (Free)** plan to start — 5,000 errors/month included.
4. Pick a team slug (e.g. `timemates`) when prompted.

## 2. Create a FastAPI Project

1. From the Sentry dashboard, click **Projects > Create Project**.
2. Under **Choose your platform**, select **Python > FastAPI**.
3. Set the project name (e.g. `timemates-api`).
4. Assign it to a team and click **Create Project**.

## 3. Get the DSN

After project creation Sentry shows the integration snippet. Copy the DSN string — it looks like:

```
https://abcdef1234567890@o123456.ingest.us.sentry.io/7654321
```

You can also retrieve it later from **Settings > Projects > timemates-api > Client Keys (DSN)**.

## 4. Configure Environment Variables on Render

In the Render dashboard, open the TimeMates service and go to **Environment**:

| Key            | Value                                          | Required |
|----------------|------------------------------------------------|----------|
| `SENTRY_DSN`   | DSN copied above                               | Yes (to enable) |
| `ENVIRONMENT`  | `production` (or `staging`, `development`)     | Optional — defaults to `production` |
| `GIT_SHA`      | Current commit SHA (Render exposes `$RENDER_GIT_COMMIT`) | Optional — used to tag releases |

To wire `GIT_SHA` automatically on Render, add this to `render.yaml`:

```yaml
envVars:
  - key: GIT_SHA
    fromService:
      type: web
      name: timemates
      property: commitId
```

Or set it manually as `RENDER_GIT_COMMIT` and adjust the code accordingly.

Click **Save Changes** — Render redeploys automatically.

## 5. Verify Initialization

Tail the Render logs after deploy. You should see one of:

- `[SENTRY] Initialized successfully` — DSN was found and SDK loaded.
- `[SENTRY] No DSN configured, error tracking disabled` — env var missing.
- `[SENTRY] Failed to initialize: <error>` — DSN invalid or SDK import failed.

## 6. Test the Integration

A debug endpoint is exposed **only when `SENTRY_DSN` is set**:

```
GET /api/debug/sentry-test
```

Hit it once after deploy:

```bash
curl https://<your-render-url>/api/debug/sentry-test
```

The request returns a 500. Within ~30 seconds the error appears in your Sentry dashboard under **Issues** with the message:

> Sentry test exception - this is intentional to verify error tracking is working

Make sure the issue shows:
- Correct `environment` tag (`production` / `staging`).
- Correct `release` tag (your git SHA).
- A stack trace pointing to `main.py:sentry_test`.

## 7. (Optional) Remove the Test Endpoint

Once verification passes, you can leave the endpoint in place — it is only mounted when `SENTRY_DSN` is set, and it is reachable only by someone who knows the path. If you prefer to remove it, delete the `@app.get("/api/debug/sentry-test")` block in `main.py`.

## Configuration Reference

The SDK is initialized with:

- `traces_sample_rate=0.1` — 10% of transactions are traced for performance.
- `profiles_sample_rate=0.1` — 10% profiled.
- `send_default_pii=False` — no IP addresses / user emails leak by default.
- `attach_stacktrace=True` — every event has a stack trace.
- Integrations: `FastApiIntegration(transaction_style="endpoint")` and `SqlalchemyIntegration()`.

Tune these values in `main.py` once you know your traffic volume.

## User Context (Authenticated Requests)

To attach user identity to events on authenticated routes, call inside your auth dependency:

```python
import sentry_sdk
sentry_sdk.set_user({"id": user.id, "username": user.username})
```

Place this in `auth.get_current_user` after the user is resolved. With `send_default_pii=False` only the `id` is sent unless you opt-in.

## Troubleshooting

- **No events in Sentry**: confirm `[SENTRY] Initialized successfully` is in the logs. Check the DSN belongs to the same Sentry org/project.
- **Wrong release tag**: ensure `GIT_SHA` is set in Render env vars; otherwise events tag as `unknown`.
- **SDK import error**: `pip install -r requirements.txt` must include `sentry-sdk[fastapi]==2.18.0`.
