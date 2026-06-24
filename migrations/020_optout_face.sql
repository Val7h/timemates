-- Migration 020: Opt-out FACIAL — fechar o buraco estrutural de privacidade.
--
-- Permite que QUALQUER pessoa (usuária ou não, sem login) bloqueie o PRÓPRIO
-- ROSTO de aparecer em qualquer busca facial — inclusive em fotos que TERCEIROS
-- subam — e impede que o rosto de quem optou por sair seja retido/processado.
--
-- Estende person_opt_out com o vetor do rosto a suprimir + verificação por email.
-- O motor (tunel_matching.is_face_opted_out) compara candidatos contra estes
-- embeddings via cosine_similarity e suprime acima de SUPPRESS_THRESHOLD (0.80,
-- conservador). O upload de terceiros (tunel_routes) NÃO retém o embedding de um
-- rosto com opt-out facial ativo (LGPD: não-retenção).
--
-- DESIGN: opt-out fica ATIVO IMEDIATAMENTE (ativo=TRUE na criação) — fail-safe em
-- favor da proteção. `verified` apenas FORTALECE (prova de posse do email,
-- permite gerenciar), NÃO é pré-requisito para a proteção.
--
-- NOTA: create_all() cobre TABELA nova, mas NÃO adiciona colunas a tabela já
-- existente — por isso estes ALTER TABLE ... IF NOT EXISTS são necessários.

ALTER TABLE person_opt_out ADD COLUMN IF NOT EXISTS face_embedding JSON;
ALTER TABLE person_opt_out ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(50);
ALTER TABLE person_opt_out ADD COLUMN IF NOT EXISTS verified BOOLEAN DEFAULT FALSE;
ALTER TABLE person_opt_out ADD COLUMN IF NOT EXISTS verify_token VARCHAR(64);
ALTER TABLE person_opt_out ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;

-- Índice para achar rápido por token de confirmação (GET /api/opt-out/confirm).
CREATE INDEX IF NOT EXISTS ix_person_opt_out_verify_token ON person_opt_out(verify_token);
