-- Migration 015: #AchaQuemSumiu (landing pública anônima)
-- Quem você perdeu de vista e gostaria de reencontrar?
-- Submit anônimo (sem auth), rate-limited 5/hour/IP.

CREATE TABLE IF NOT EXISTS acha_quem_sumiu (
    id SERIAL PRIMARY KEY,
    nome_procurado VARCHAR(200),
    ultima_lembranca TEXT,
    contexto TEXT,
    searcher_email VARCHAR(255),
    searcher_name VARCHAR(200),
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_acha_quem_sumiu_status ON acha_quem_sumiu(status);
CREATE INDEX IF NOT EXISTS ix_acha_quem_sumiu_created_at ON acha_quem_sumiu(created_at DESC);
