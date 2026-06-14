-- BUG H4: slowapi state was per-worker on Render — DB-backed limiter needs shared rows.
-- Cron `cleanup_old_hits` (rate_limit_db.py) purges rows older than 1 day daily.
CREATE TABLE IF NOT EXISTS rate_limit_hits (
  id SERIAL PRIMARY KEY,
  key VARCHAR(200),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_hits_key ON rate_limit_hits(key);
CREATE INDEX IF NOT EXISTS idx_rate_limit_hits_created_at ON rate_limit_hits(created_at);
