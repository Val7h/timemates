-- Migration 014: Cadeira Vazia (viral mechanic — "lugar de quem some")
-- Cada user pode deixar até 5 cadeiras vazias por turma com nome/apelido
-- e última lembrança. Outros membros (ou o proprio sumido) podem preencher.

CREATE TABLE IF NOT EXISTS cadeiras_vazias (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    turma_id INTEGER REFERENCES turmas(id),
    slot_index INTEGER,
    filled_by_user_id INTEGER REFERENCES users(id),
    nome_apelido VARCHAR(100),
    ultima_lembranca VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW(),
    filled_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_cadeiras_vazias_turma_id ON cadeiras_vazias(turma_id);
CREATE INDEX IF NOT EXISTS ix_cadeiras_vazias_user_id ON cadeiras_vazias(user_id);
CREATE INDEX IF NOT EXISTS ix_cadeiras_vazias_turma_user
    ON cadeiras_vazias(turma_id, user_id);
