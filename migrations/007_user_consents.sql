-- Migration 007: Granular User Consent (LGPD Art. 11)
--
-- Adds user_consents table to track per-purpose consent. LGPD Art. 11 §1º:
-- consent for sensitive data (biometrics) must be SEPARATE and SPECIFIC.
-- Generic ToS acceptance does NOT cover biometric processing.
--
-- Consent types currently supported:
--   * terms_of_service        -- generic ToS acceptance
--   * privacy_policy          -- generic privacy policy acceptance
--   * tunel_biometric         -- LGPD Art. 11: upload of biometric data (faces)
--   * face_matching           -- LGPD Art. 11: embedding/matching against other faces
--   * email_marketing         -- promotional/marketing emails (LGPD Art. 7)
--   * reconnect_emails        -- transactional reconnect invitation emails
--   * lgpd_data_processing    -- generic processing consent for non-sensitive data
--
-- Revocation: revoked_at is set instead of deleting the row, so the audit trail
-- remains intact (LGPD Art. 37 — record of processing activities).
--
-- IP / user-agent: stored as sha256 hash (NOT plaintext) for audit reproducibility
-- without exposing PII. Hashes are 64 hex chars.
--
-- All statements use IF NOT EXISTS for idempotency.

CREATE TABLE IF NOT EXISTS user_consents (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type     VARCHAR(80) NOT NULL,
    granted          BOOLEAN NOT NULL,
    granted_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at       TIMESTAMP,
    version          VARCHAR(20) DEFAULT 'v1',
    ip_address_hash  VARCHAR(64),
    user_agent_hash  VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_user_consents_user_id
    ON user_consents (user_id);

CREATE INDEX IF NOT EXISTS idx_user_consents_user_type
    ON user_consents (user_id, consent_type);

CREATE INDEX IF NOT EXISTS idx_user_consents_active
    ON user_consents (user_id, consent_type, revoked_at);
