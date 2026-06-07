# UptimeRobot Setup for TimeMates

End-to-end guide for configuring UptimeRobot monitors that watch the TimeMates
production deployment on Render.

## Monitors to Create

| Monitor | URL | Interval | Type | Alert |
|---|---|---|---|---|
| Health Check | https://timemates.onrender.com/health | 5 min | HTTPS | Email+SMS |
| Cities API | https://timemates.onrender.com/api/cities | 5 min | HTTPS | Email |
| Docs | https://timemates.onrender.com/docs | 15 min | HTTPS | Email |
| Events SP | https://timemates.onrender.com/api/events/S%C3%A3o%20Paulo | 15 min | HTTPS | Email |

## Setup Steps

1. Sign up: https://uptimerobot.com/signUp (free tier: 50 monitors, 5-min interval)
2. Create monitors as above
3. Configure alert contacts
4. Set up status page (optional)

### 1. Sign up

Visit https://uptimerobot.com/signUp. The free tier covers:
- 50 monitors
- 5-minute check interval
- Email alerts (SMS via paid add-on)
- Public status pages

### 2. Create monitors

For each row in the table above:

1. Click **+ New Monitor**
2. **Monitor Type**: HTTP(s)
3. **Friendly Name**: copy from the "Monitor" column
4. **URL**: copy verbatim from the "URL" column (note the URL-encoded `S%C3%A3o%20Paulo`)
5. **Monitoring Interval**: 5 or 15 minutes per the table
6. **Monitor Timeout**: 30 seconds (Render free tier cold starts can take ~20s)
7. **HTTP Method**: GET
8. **Keyword Monitoring** (recommended):
   - Health Check: keyword `"status":"ok"`, alert when **not exists**
   - Cities API: keyword `São Paulo`, alert when **not exists**
   - Docs: keyword `Swagger UI`, alert when **not exists**
9. Select Alert Contacts created in step 3
10. **Create Monitor**

### 3. Configure alert contacts

Settings > **My Settings** > **Alert Contacts**

Recommended contacts:
- **Email (primary)**: your operations inbox
- **Email (oncall)**: rotating on-call address
- **SMS** (paid tier or via free Telegram/Discord webhook): for the Health Check only
- **Slack / Discord webhook**: post into `#alerts` channel

Bind contacts to monitors per the "Alert" column.

### 4. Status page (optional)

Settings > **Status Pages** > **+ Add New Status Page**

- **Friendly Name**: TimeMates Status
- **Custom Domain**: `status.timemates.com.br` (CNAME to `stats.uptimerobot.com`)
- **Monitors**: select all four above
- **Public**: yes

## Why These Monitors

- **/health**: detects total outage instantly. JSON includes `database_connected`
  so the keyword monitor catches DB-only outages even if Render thinks the
  process is healthy.
- **/api/cities**: detects the bug we just fixed could regress. If this returns
  empty array or 500, the city dropdown is broken.
- **/docs**: confirms Swagger reachable (signals deploy success). Static asset
  failures often indicate a bad build.
- **/api/events**: confirms data pipeline working. The São Paulo route exercises
  URL decoding plus the event aggregation query.

## Alert Tuning

- Set **alert threshold** to "after 2 consecutive failures" to avoid pager
  fatigue from transient Render cold-start timeouts.
- **Maintenance Windows**: define a recurring weekly window during your deploy
  slot so you don't page yourself on planned restarts.
- Add an **SSL Certificate Expiration** monitor for `timemates.onrender.com`
  (UptimeRobot offers this as a separate monitor type — 30-day warning).

## Health Endpoint Contract

`GET /health` (alias of `/api/health`) returns:

```json
{
  "status": "ok",
  "timestamp": "2026-06-07T12:34:56.000000",
  "version": "abc1234",
  "database_connected": true,
  "db": "postgresql"
}
```

- `status` flips to `"degraded"` when the DB ping fails.
- `version` reads the `GIT_SHA` env var (set in Render build hook:
  `export GIT_SHA=$(git rev-parse --short HEAD)`).
- The HTTP status code remains `200` even when degraded so UptimeRobot's
  keyword monitor (looking for `"status":"ok"`) is what triggers the alert.

## Verifying Setup

After creating monitors, verify with:

```bash
curl https://timemates.onrender.com/health
curl https://timemates.onrender.com/api/cities | head -c 200
curl -I https://timemates.onrender.com/docs
curl 'https://timemates.onrender.com/api/events/S%C3%A3o%20Paulo' | head -c 200
```

All four should return `200 OK` with non-empty bodies before you rely on the
monitors in production.
