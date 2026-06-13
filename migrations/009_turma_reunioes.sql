-- Migration 009: Turma Reuniões (churrasco/dinner organizer)
-- Adds turma_reunioes, turma_reuniao_votes, turma_reuniao_rsvps tables.

CREATE TABLE IF NOT EXISTS turma_reunioes (
    id SERIAL PRIMARY KEY,
    turma_id INTEGER NOT NULL REFERENCES turmas(id),
    organizer_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    proposed_dates JSON DEFAULT '[]'::json,
    suggested_venue VARCHAR(300),
    venue_city VARCHAR(100),
    final_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'collecting_votes',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_turma_reunioes_turma_id ON turma_reunioes(turma_id);

CREATE TABLE IF NOT EXISTS turma_reuniao_votes (
    id SERIAL PRIMARY KEY,
    reuniao_id INTEGER NOT NULL REFERENCES turma_reunioes(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    date_voted VARCHAR(20) NOT NULL,
    available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_turma_reuniao_votes_reuniao_id ON turma_reuniao_votes(reuniao_id);

CREATE TABLE IF NOT EXISTS turma_reuniao_rsvps (
    id SERIAL PRIMARY KEY,
    reuniao_id INTEGER NOT NULL REFERENCES turma_reunioes(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'confirmed',
    plus_ones INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_turma_reuniao_rsvps_reuniao_id ON turma_reuniao_rsvps(reuniao_id);
