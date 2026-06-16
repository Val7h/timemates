-- Apelido per-turma: brasileiros lembram do "Cabeção", não do "João Carlos da Silva".
-- Sem isso, "Cadê o Cabeção?" não funciona como no WhatsApp do grupo.
ALTER TABLE turma_memberships ADD COLUMN IF NOT EXISTS apelido VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_turma_memberships_apelido
  ON turma_memberships (LOWER(apelido));
