# PostHog Analytics Setup Guide

This document explains how to wire up **PostHog product analytics** for the
timeMates backend, and how to build the dashboards that measure our North Star
metric: **WADS/U (Weekly Active Discovery Sessions per User)**.

WADS/U is defined in `POSITIONING.md` as:
> sessions/week with >30s browsing + 1 event saved/clicked.

---

## 1. Create a PostHog account

1. Go to https://posthog.com and click **Get started — free**.
2. Choose **PostHog Cloud (US)** — closest region to our Render deployment.
   (If you require EU data residency, choose **PostHog Cloud (EU)** and adjust
   `POSTHOG_HOST` accordingly — see step 3.)
3. Create an Organization (e.g. `timeMates`) and a Project (e.g.
   `timeMates-production`).

> Free tier includes 1M events/month, more than enough for early traction.

---

## 2. Get your Project API Key

1. In PostHog, click the project name (top-left) → **Project settings**.
2. Scroll to **Project API Key** (starts with `phc_…`).
3. Copy it — this is the **public write key**, safe to ship to backend env.
   Do **not** use the Personal API Key (starts with `phx_…`); that one is for
   the management API and must stay secret.

While you're there, also copy the **Project ID** (a number). You'll need it
for the SQL retention queries below.

---

## 3. Configure environment variables on Render

In the Render dashboard for the `timeMates` web service:

1. Go to **Environment** → **Add Environment Variable**.
2. Add:

| Key                | Value                                  | Required |
|--------------------|----------------------------------------|----------|
| `POSTHOG_API_KEY`  | `phc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | yes      |
| `POSTHOG_HOST`     | `https://us.i.posthog.com`             | no — defaults to US |

For EU region, set `POSTHOG_HOST=https://eu.i.posthog.com`.

3. Click **Save Changes** — Render will redeploy automatically.
4. Tail logs and look for:
   ```
   [POSTHOG] Analytics initialized
   ```
   If the key is missing you'll instead see
   `[POSTHOG] No API key configured, analytics disabled` and the app will keep
   running normally (graceful degradation).

---

## 4. Events the backend already instruments

| Event              | Where it fires                                | Properties             |
|--------------------|-----------------------------------------------|------------------------|
| `signup`           | `POST /api/auth/register` (after commit)      | `source: "register"`   |
| `city_list_view`   | `GET /api/cities`                             | —                      |
| `city_view`        | `GET /api/events/{city}`                      | `city`                 |
| `event_view`       | *to be added — event detail endpoint*         | `event_id`, `city`     |
| `event_save`       | *to be added — RSVP / save endpoint*          | `event_id`, `city`     |
| `calendar_sync`    | *to be added — calendar OAuth callback*       | `provider`             |
| `share_click`      | *to be added — frontend share button*         | `event_id`, `channel`  |

`distinct_id` is the database `user.id` (string-coerced). Anonymous calls
(no JWT) skip tracking — `track_event` is a no-op when `user_id` is `None`.

---

## 5. Build the WADS/U funnel dashboard

PostHog → **Insights** → **+ New insight** → **Funnels**.

Steps:

1. **Step 1 — `city_view`**
   Filter: `$session_duration >= 30` (PostHog auto-captures session duration).
2. **Step 2 — `event_save`** *(or `event_view` until save is shipped)*
   Conversion window: **30 minutes**.

Settings:
- Aggregating by **unique users**
- Date range: **last 4 weeks**, breakdown by **week**
- Save the insight as **WADS/U funnel**

Then create a **Dashboard** called **North Star — WADS/U** and pin:
- The funnel insight above
- A **Trends** chart of `event_save` events, weekly active users
- A **Lifecycle** chart on `city_view` to see new / returning / dormant / resurrecting users

---

## 6. SQL queries — D1 / D7 / D30 retention

PostHog → **SQL editor** (HogQL). Replace the event name with whichever event
defines "activation" for you — we recommend `event_save` once it's live, and
`city_view` in the meantime.

### D1 retention
```sql
WITH first_seen AS (
  SELECT person_id, min(toDate(timestamp)) AS d0
  FROM events
  WHERE event = 'signup'
  GROUP BY person_id
)
SELECT
  d0 AS cohort_day,
  count(DISTINCT f.person_id) AS cohort_size,
  count(DISTINCT CASE WHEN toDate(e.timestamp) = d0 + INTERVAL 1 DAY
                      THEN e.person_id END) AS d1_returned,
  d1_returned * 100.0 / cohort_size AS d1_pct
FROM first_seen f
LEFT JOIN events e
  ON e.person_id = f.person_id
 AND e.event IN ('city_view', 'event_view', 'event_save')
GROUP BY d0
ORDER BY d0 DESC
LIMIT 30
```

### D7 retention
Same query, replace `INTERVAL 1 DAY` with `INTERVAL 7 DAY` and rename the
columns. To be precise you usually want "active on day 7 *or later within a
window*"; tweak the predicate to `BETWEEN d0 + INTERVAL 7 DAY AND d0 + INTERVAL 8 DAY`
for strict D7, or `>= d0 + INTERVAL 7 DAY AND <= d0 + INTERVAL 13 DAY` for the
weekly cohort window.

### D30 retention
Same shape, `INTERVAL 30 DAY`. With less data you'll want the rolling-window
variant:
```sql
... CASE WHEN toDate(e.timestamp) BETWEEN d0 + INTERVAL 28 DAY
                                       AND d0 + INTERVAL 30 DAY
         THEN e.person_id END ...
```

### WADS/U — weekly active discovery sessions per user
```sql
WITH weekly_sessions AS (
  SELECT
    person_id,
    toMonday(timestamp) AS week,
    count(DISTINCT $session_id) AS sessions
  FROM events
  WHERE event IN ('city_view', 'event_view', 'event_save')
    AND $session_duration >= 30
  GROUP BY person_id, week
)
SELECT
  week,
  count(DISTINCT person_id) AS active_users,
  sum(sessions)             AS total_sessions,
  sum(sessions) * 1.0 / count(DISTINCT person_id) AS wads_per_user
FROM weekly_sessions
GROUP BY week
ORDER BY week DESC
LIMIT 12
```

Pin the result as a **Line chart** on the North Star dashboard.

---

## 7. Verifying the integration end-to-end

1. Set `POSTHOG_API_KEY` locally in `.env` and restart the backend.
2. Log line should read `[POSTHOG] Analytics initialized`.
3. Register a new user via `POST /api/auth/register`.
4. In PostHog → **Activity** → **Live events**, you should see `signup`
   within ~5 seconds (PostHog batches by default).
5. Hit `GET /api/cities` and `GET /api/events/sao-paulo` with a Bearer token —
   confirm `city_list_view` and `city_view` show up.

If nothing appears:
- Confirm the key starts with `phc_` (not `phx_`).
- Confirm `POSTHOG_HOST` matches the region you selected (US vs EU).
- Check Render logs for `[POSTHOG] Failed to initialize: …`.

---

## 8. Operational notes

- **Silent failure by design.** `track_event` swallows all exceptions so an
  analytics outage can never take down a request path.
- **No PII.** We send only `user.id`, never email/CPF/phone. PostHog will
  identify users by numeric ID; correlate offline in the DB if needed.
- **Cost.** Free tier is 1M events/month. At our current event mix that covers
  roughly 50k MAU before we'd need to upgrade or sample.
- **Frontend events.** Once we ship `event_save`, `calendar_sync`, and
  `share_click`, prefer firing them from the backend on the authoritative
  state-change endpoint (e.g. RSVP save) rather than client-side, so we don't
  double-count or miss events from offline clients.
