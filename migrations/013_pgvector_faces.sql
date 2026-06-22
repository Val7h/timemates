-- pgvector migration: armazenar embeddings ArcFace 512-dim como vetor nativo
-- pra cosine-similarity search com índice ivfflat (Neon supports pgvector).
-- Coluna nova `embedding_vec` convive com a JSON `embedding` antiga durante
-- backfill — código v2 lê/escreve vec, v1 continua no JSON.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE tunel_faces ADD COLUMN IF NOT EXISTS embedding_vec vector(512);

CREATE INDEX IF NOT EXISTS idx_tunel_faces_embedding_vec
  ON tunel_faces USING ivfflat (embedding_vec vector_cosine_ops)
  WITH (lists = 100);
