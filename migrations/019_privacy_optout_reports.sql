-- Migration 019: Privacy P0 — Direito a desaparecer + Denúncia de conteúdo
-- person_opt_out: pessoa que NÃO quer ser procurada/encontrada (bloqueia #AchaQuemSumiu).
-- content_report: denúncia de conteúdo impróprio/abusivo (acha|mural|match|memoria).
-- Endpoints públicos sem auth, rate-limited por IP (POST /api/opt-out, POST /api/report).

CREATE TABLE IF NOT EXISTS person_opt_out (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(200),               -- lowercased na criação (match case-insensitive)
    email VARCHAR(255),
    telefone_hash VARCHAR(128),
    motivo TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_person_opt_out_nome ON person_opt_out(nome);
CREATE INDEX IF NOT EXISTS ix_person_opt_out_ativo ON person_opt_out(ativo);

CREATE TABLE IF NOT EXISTS content_report (
    id SERIAL PRIMARY KEY,
    content_type VARCHAR(30),        -- 'acha' | 'mural' | 'match' | 'memoria'
    content_id INTEGER,
    descricao TEXT,
    reporter_email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'aberto'
);

CREATE INDEX IF NOT EXISTS ix_content_report_status ON content_report(status);
CREATE INDEX IF NOT EXISTS ix_content_report_type ON content_report(content_type);
