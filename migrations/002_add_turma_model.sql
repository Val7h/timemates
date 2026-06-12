-- Migration: 002_add_turma_model
-- Description: TimeMates reconnection pivot. TURMA (cohort) becomes the central unit.
-- Adds: turmas, turma_memberships, turma_vouches, mural_memories
-- LGPD: default-ghost enforced at column level (visibility default 'ghost').

-- ─────────────────────────────────────────────────────────────────────────────
-- TURMAS - a cohort (escola/faculdade/empresa/bairro/igreja, year)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turmas (
    id SERIAL PRIMARY KEY,
    institution_id INTEGER REFERENCES institutions(id),
    institution_name VARCHAR(300) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(2),
    kind VARCHAR(50) NOT NULL,
    cohort_year INTEGER NOT NULL,
    cohort_label VARCHAR(100),
    founder_id INTEGER REFERENCES users(id),
    total_members INTEGER DEFAULT 0,
    total_verified INTEGER DEFAULT 0,
    is_unlocked BOOLEAN DEFAULT FALSE,
    slug VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_turmas_slug ON turmas(slug);
CREATE INDEX IF NOT EXISTS idx_turmas_institution ON turmas(institution_id);
CREATE INDEX IF NOT EXISTS idx_turmas_cohort_year ON turmas(cohort_year);
CREATE INDEX IF NOT EXISTS idx_turmas_city_state ON turmas(city, state);
CREATE INDEX IF NOT EXISTS idx_turmas_kind ON turmas(kind);

-- ─────────────────────────────────────────────────────────────────────────────
-- TURMA_MEMBERSHIPS - default-ghost (visibility 'ghost' by default)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turma_memberships (
    id SERIAL PRIMARY KEY,
    turma_id INTEGER REFERENCES turmas(id),
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending',
    visibility VARCHAR(20) DEFAULT 'ghost',
    is_founder BOOLEAN DEFAULT FALSE,
    verified_by_vouches INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_turma_memberships_turma ON turma_memberships(turma_id);
CREATE INDEX IF NOT EXISTS idx_turma_memberships_user ON turma_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_turma_memberships_status ON turma_memberships(status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_turma_memberships_turma_user
    ON turma_memberships(turma_id, user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- TURMA_VOUCHES - peer verification ("eu garanto que esta pessoa estudou aqui")
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS turma_vouches (
    id SERIAL PRIMARY KEY,
    turma_id INTEGER REFERENCES turmas(id),
    voucher_user_id INTEGER REFERENCES users(id),
    vouched_user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_turma_vouches_turma ON turma_vouches(turma_id);
CREATE INDEX IF NOT EXISTS idx_turma_vouches_vouched ON turma_vouches(vouched_user_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_turma_vouches_unique
    ON turma_vouches(turma_id, voucher_user_id, vouched_user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- MURAL_MEMORIES - Mural da Saudade (uma memória sensorial por user por turma)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mural_memories (
    id SERIAL PRIMARY KEY,
    turma_id INTEGER REFERENCES turmas(id),
    user_id INTEGER REFERENCES users(id),
    memory_type VARCHAR(50),
    content VARCHAR(500) NOT NULL,
    tags JSON DEFAULT '[]'::json,
    audio_url VARCHAR(500),
    in_memoriam BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mural_memories_turma ON mural_memories(turma_id);
CREATE INDEX IF NOT EXISTS idx_mural_memories_user ON mural_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_mural_memories_type ON mural_memories(memory_type);
