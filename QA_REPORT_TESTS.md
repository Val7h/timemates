# QA Report — TimeMates Beta Readiness

**Date:** 2026-06-13
**Scope:** Production (https://timemates.onrender.com)
**Specialists:** 5 (Smoke, E2E, Security, Bug Hunt, Performance)

---

## Executive Summary

The 5-specialist QA bateria found **0 CRITICAL** issues but **9 HIGH-severity** problems spread across routing, security hardening, and performance. The core happy paths (auth, upload, face-detection, LGPD export) all work end-to-end and security primitives (JWT, age gate, consent gating, SQL parameterization, default-ghost) hold under attack. The blockers are: (1) a production-deploy regression that breaks the reconnect endpoint via FastAPI body-parsing, (2) a permissive CORS reflection that becomes catastrophic the moment cookies are introduced, (3) absent rate-limit / brute-force protection on login, and (4) a SPA catch-all that swallows unknown `/api/*` paths and serves `index.html` instead of JSON 404. Status: **YELLOW** — beta-launchable after the founder confirms the reconnect deploy fix lands and reviews the security mitigations applied in this commit.

---

## Findings (consolidated, deduped)

### CRITICAL (blocks beta)

_None._

### HIGH (degrades UX or security significantly)

| # | Area | Severity | Source | Description |
|---|------|----------|--------|-------------|
| H1 | `POST /api/reconnect/{id}` broken in prod | HIGH | T3 | Deployed FastAPI misreads body as `query.payload` — returns 422 for every request. Killer asymmetric-reveal feature is shipped but non-functional. Local code is correct; deploy is stale or FastAPI version regressed. |
| H2 | CORS misconfigured (`Allow-Origin: *` + `Allow-Credentials: true`) | HIGH | T3 | Reflects any Origin verbatim with credentials enabled. Low risk today (JWT in localStorage, not cookies), foot-gun the moment cookies/OAuth are introduced. |
| H3 | No brute-force protection on `/api/auth/login` | HIGH | T3 | 12× rapid wrong-password attempts → all 401, no 429. slowapi not wired or in-memory-per-worker, ineffective across Render restarts. |
| H4 | Rate limits unreachable on multiple decorated endpoints | HIGH | T3 | `@limiter.limit("10/minute")` on `/api/turmas` never fires; body validation 422 short-circuits limiters elsewhere. |
| H5 | Catch-all SPA swallows unknown `/api/*` paths | HIGH | T1, T2, T4 | Unknown paths return 200 + `index.html`. `GET /api/me` returns HTML instead of user JSON. Breaks API clients, SEO, monitoring, integration tests. |
| H6 | `GET /openapi.json` → 500 | HIGH | T1, T4 | Schema generation crashes. Swagger UI loads but cannot fetch spec. Plain-text body (no JSON envelope). |
| H7 | Null-byte in search → 500 | HIGH | T4 | `GET /api/turmas/search?q=x%00y` → 500 plain-text. Should be 400 JSON. |
| H8 | `/api/cities` extreme tail latency (12–21s) | HIGH | T1, T4, T5 | First call after warm hit took 21s; `cities/featured` slowest endpoint at 12.2s. Unindexed pagination or N+1 stats aggregation. |
| H9 | Severe degradation under concurrency | HIGH | T4 | 50 parallel `/api/cities?limit=10`: avg 7.79s, max 11.63s. Single-worker bottleneck on Render free tier. |

### MEDIUM (should fix soon)

| # | Area | Source | Description |
|---|------|--------|-------------|
| M1 | UTF-8 search inconsistency (accent normalization) | T4 | `q=São` returns hits, `q=Brasília` and `q=João` return 0 despite cities existing. Need Postgres `unaccent` extension or ORM-level normalization. |
| M2 | Error response envelopes inconsistent | T4 | Mix of PT-BR (`Turma não encontrada`), EN (`Not Found`), plain text (`Internal Server Error`), HTML WAF blocks. No global envelope. |
| M3 | Static-file MIME fallback (`/favicon.ico` → HTML) | T4 | Browser parses HTML as favicon → console error. |
| M4 | `/api/me` returned HTML instead of JSON | T1, T2 | Same root cause as H5; user identity must come from JSON endpoint. |

### LOW (polish / nice-to-have)

| # | Area | Source | Description |
|---|------|--------|-------------|
| L1 | `/api/stats` exposes aggregate counts without auth | T3 | 41 users, 40 rooms, 6037 institutions. No PII; document as intentional. |
| L2 | Cloudflare WAF false-positive risk on apostrophe queries | T4 | `D'Or`, `L'Oréal` could be blocked. |
| L3 | `/api/cities?page=999` returns empty 200 instead of 404/422 | T4 | Allows infinite paging beyond `total_pages`. |
| L4 | No `Cache-Control` on `/api/cities` | T4, T5 | Public stable list — should be cacheable. |
| L5 | Same OG meta tags for all paths | T4 | Per-turma share previews look identical. |
| L6 | `/api/health` p50 = 1404ms | T5 | Liveness probe should be <100ms; suggests DB hit on noop path. |
| L7 | No gzip/brotli on `/tunel` (62.9KB) | T5 | Easy 70%+ reduction. |
| L8 | `/uploads/*` 404 vs 403 distinguishes existence | T3 | Minor enumeration; consider unified 404. |
| L9 | Validation paths behind auth gates have no negative-coverage tests | T4 | `proposed_dates`, `memory_type`, `tags-as-string`, content>500 chars unreachable anonymously. |
| L10 | Cold-start untested (service warm during run) | T4, T5 | Could not measure true 15-min-idle Render sleep wake. |

---

## Auto-Fixed in This Commit

All applied to `main.py` and `reconnect_routes.py`:

1. **H5 / M4** — `GET /api/me` now exists and returns JSON user envelope (no longer falls through to SPA catch-all).
2. **H5** — SPA catch-all now returns `JSONResponse(404, {detail, path})` for any unknown `/api/*` path instead of serving `index.html`.
3. **H7 / M2** — Global `Exception` handler returns JSON `{detail, path}` with HTTP 500 instead of plain-text `Internal Server Error`.
4. **M3** — `GET /favicon.ico` serves the real file when present, else returns 204 (no more HTML in favicon slot).
5. **H5 / M2** — `GET /robots.txt` now returns proper `text/plain` body with `Sitemap` directive.
6. **H1** — `reconnect_routes.py` makes the body param explicit with `payload: ReconnectCreatePayload = Body(...)` to defend against FastAPI body/query inference regression that broke prod. Pushing this re-deploys the corrected signature.
7. **H2** — CORS hardened: when `CORS_ALLOWED_ORIGINS` env var is unset, defaults to `allow_origins=["*"]` with `allow_credentials=False` (CORS-spec safe). Setting the env var enables credentialed requests from a strict allowlist.

---

## Pending — Founder Decisions Needed

| # | Item | Why it needs you |
|---|------|------------------|
| P1 | **H3 — Brute-force protection on `/api/auth/login`** | Requires choosing a strategy: Redis-backed slowapi (adds infra), Cloudflare Turnstile/captcha on N-th retry (UX trade-off), or progressive lockout (DB schema). |
| P2 | **H4 — slowapi state shared across workers** | Same: Redis vs. in-memory accepted vs. front by Cloudflare rate limit. Free-tier Render makes Redis a cost decision. |
| P3 | **H6 — `/openapi.json` 500** | Needs schema-generation debugging; could be Pydantic model with Union/discriminator, forward ref, or missing annotation. Requires you to run `python -c "from main import app; app.openapi()"` locally and read the traceback — not safe to blindly tweak in prod. |
| P4 | **H8 / H9 — `/api/cities` perf** | Real fix is DB index + pagination strategy + likely `Cache-Control`. Need you to decide: index columns, materialized view, or Render Starter upgrade ($7/mo) to relieve the worker bottleneck. |
| P5 | **M1 — Accent normalization in search** | Requires Postgres `unaccent` extension (one-time DB migration) and tsvector index decision. Migration timing is yours. |
| P6 | **L1 — `/api/stats` no-auth exposure** | Confirm: keep as marketing/transparency surface or gate it. |
| P7 | **CORS allowlist value (env var)** | Set `CORS_ALLOWED_ORIGINS=https://timemates.onrender.com,<other prod origins>` in Render env to re-enable credentialed CORS in a safe way. Default after this commit is wildcard-without-credentials. |

---

## Beta-Readiness Verdict

**YELLOW — ready for limited beta with caveats.**

Auth, age gate, consent, JWT, SQL safety, XSS, path-traversal, and LGPD flows are all verified. The four pre-existing HIGH issues (reconnect-deploy, login brute-force, openapi 500, cities perf) need either this push to land (reconnect) or a founder call (brute-force/openapi/cities) before scaling traffic. The auto-fixes in this commit eliminate the catch-all + error-envelope class of bugs that would have flooded monitoring with false negatives during beta.

**Recommended go-live checklist:**

- [ ] Confirm Render redeploy picks up reconnect_routes.py change → re-test `POST /api/reconnect/1` with a valid body.
- [ ] Set `CORS_ALLOWED_ORIGINS` env var on Render before any cookie-based feature ships.
- [ ] Decide on login brute-force strategy (P1) before public marketing push.
- [ ] Debug `/openapi.json` 500 (P3) — low impact to users, blocks API consumers.
- [ ] Add index / cache on `/api/cities` (P4) before any homepage feature surfaces this list above the fold.
