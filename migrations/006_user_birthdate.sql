-- Migration 006: User birthdate + 18+ gate (age compliance)
--
-- Why:
--   * LGPD Art. 14 — tratamento de dados de crianças/adolescentes exige
--     consentimento parental e proteções específicas. Sem birthdate, é
--     impossível diferenciar adultos de menores.
--   * ECA — features sensíveis (Túnel do Tempo: fotos escolares que podem
--     conter menores; reconnect: contato direto entre usuários; turmas:
--     reflexo de escolas com históricos de menores) precisam gate 18+.
--
-- Columns added to users:
--   * birthdate                 — DATE, nullable (users legados não têm).
--   * age_verified              — BOOLEAN, default FALSE (auto-declarado é
--                                  unverified; só vira TRUE via gov.br ou doc).
--   * age_verification_method   — VARCHAR(50), nullable
--                                  ('self_declared' | 'gov_br' | 'doc_upload' | ...).
--
-- Cross-dialect notes:
--   * Postgres (Neon, prod) suporta ADD COLUMN IF NOT EXISTS.
--   * SQLite (dev fallback) ignora IF NOT EXISTS em ADD COLUMN mas o runner
--     captura "duplicate column" e segue.
--   * Default FALSE em age_verified evita NULL em rows existentes.

ALTER TABLE users ADD COLUMN IF NOT EXISTS birthdate DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS age_verified BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS age_verification_method VARCHAR(50);

-- Index parcial: queries do tipo "users sem birthdate" (compliance audits,
-- prompt de coleta) são frequentes pós-rollout. Mantém custo baixo (só
-- linha incompletas indexadas).
CREATE INDEX IF NOT EXISTS ix_users_birthdate_null
    ON users (id) WHERE birthdate IS NULL;
