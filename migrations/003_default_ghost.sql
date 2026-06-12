-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration 003: Default-Ghost Privacy Model
-- ═══════════════════════════════════════════════════════════════════════════════
-- Implements privacy-by-default for User table:
--   * is_discoverable: FALSE by default (user must opt-in to be findable)
--   * allow_reconnect_requests: TRUE by default (can still receive requests)
--   * ghost_mode_global: FALSE by default (panic toggle overrides everything)
--
-- For existing 7 users: defaults set them to ghost mode. They can opt-in later.
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_discoverable BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS allow_reconnect_requests BOOLEAN DEFAULT TRUE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ghost_mode_global BOOLEAN DEFAULT FALSE NOT NULL;

-- Ensure existing users default to ghost (safety wins on retro-fit)
UPDATE users SET is_discoverable = FALSE WHERE is_discoverable IS NULL;
UPDATE users SET allow_reconnect_requests = TRUE WHERE allow_reconnect_requests IS NULL;
UPDATE users SET ghost_mode_global = FALSE WHERE ghost_mode_global IS NULL;

-- Per-turma opt-in table: lets a ghost user be visible only inside specific turmas
CREATE TABLE IF NOT EXISTS user_turma_visibility (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    turma_id INTEGER NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, turma_id)
);

CREATE INDEX IF NOT EXISTS idx_user_turma_vis_user ON user_turma_visibility(user_id);
CREATE INDEX IF NOT EXISTS idx_user_turma_vis_turma ON user_turma_visibility(turma_id);
CREATE INDEX IF NOT EXISTS idx_users_discoverable ON users(is_discoverable) WHERE is_discoverable = TRUE;
