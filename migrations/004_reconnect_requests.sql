-- Migration 004: Reconnect Requests (asymmetric reveal)
--
-- Adds:
--   * users.allow_reconnect_requests   privacy opt-in flag (default TRUE).
--                                      Already added in migration 003 — the
--                                      ALTER below is idempotent and a no-op
--                                      if the column exists.
--   * reconnect_requests               request lifecycle:
--                                      pending/accepted/declined/expired/blocked.
--
-- Cross-dialect: written to work on both Postgres (Neon, prod) and SQLite
-- (local fallback). Postgres-specific types like SERIAL/JSONB/INTERVAL are
-- avoided in favor of portable equivalents that SQLAlchemy upgrades to the
-- right dialect at create_all time. INTEGER PRIMARY KEY + AUTOINCREMENT
-- equivalent is provided by SQLAlchemy's ORM mapper (`reconnect_models.py`);
-- this raw SQL only needs to create the table shape on Postgres.

-- ────────────────────────────────────────────────────────────────────────
-- 1. Privacy opt-in column on users (idempotent — 003 already added it).
-- ────────────────────────────────────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS allow_reconnect_requests BOOLEAN NOT NULL DEFAULT TRUE;

-- ────────────────────────────────────────────────────────────────────────
-- 2. reconnect_requests table (Postgres-targeted; SQLite gets it via ORM
--    create_all).
-- ────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reconnect_requests (
    id              SERIAL PRIMARY KEY,
    requester_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Turma context. References turmas.id from migration 002.
    turma_id        INTEGER REFERENCES turmas(id) ON DELETE SET NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    message         VARCHAR(1000),
    shared_context  JSON NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at    TIMESTAMP,
    expires_at      TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_reconnect_target_status
    ON reconnect_requests (target_id, status);

CREATE INDEX IF NOT EXISTS ix_reconnect_requester_target
    ON reconnect_requests (requester_id, target_id);

CREATE INDEX IF NOT EXISTS ix_reconnect_expires
    ON reconnect_requests (expires_at);

-- ────────────────────────────────────────────────────────────────────────
-- 3. Backfill: existing rows treated as opted-in (matches column default).
-- ────────────────────────────────────────────────────────────────────────
UPDATE users SET allow_reconnect_requests = TRUE
    WHERE allow_reconnect_requests IS NULL;
