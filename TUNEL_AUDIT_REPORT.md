# Túnel do Tempo — Audit Report (LGPD + Safety + Performance)

Auditor: Quality & Compliance
Data: 2026-06-13
Escopo: `tunel_routes.py`, `tunel_detection.py`, `database.py` (TunelUpload/TunelFace), `migrations/005_tunel_foundation.sql`

---

## 1. LGPD Compliance Audit

### 1.1 Photo storage retention
- **Implementado**: soft-delete (`deleted_at` em `tunel_uploads`).
- **Gap CRÍTICO**: o comentário SQL diz "30-day purge required" e o modelo SQLAlchemy também — **mas não existe cron/job de purge**. Não há nada em `main.py` nem em scheduled tasks. Arquivo físico fica em disco indefinidamente.
- **Gap**: foto raw é mantida mesmo APÓS o embedding ser gerado. Recomendação LGPD (princípio da necessidade Art. 6º III): após detecção+embedding+match, descartar a foto raw — manter apenas thumbnail blurred + bbox + embedding.

### 1.2 Embedding storage (Art. 11 — dado sensível biométrico)
- **OK**: comentários SQL marcam embedding como dado sensível, advertem para nunca expor por API pública.
- **Gap**: armazenado em `JSON` (texto) sem cifragem at-rest. LGPD Art. 46 exige medidas técnicas. Recomendação: column-level encryption ou move para `pgvector` cifrado.
- **Gap**: o embedding atual é histogram-based, **não é embedding facial real**. Tecnicamente é menos sensível (não permite re-identificação cross-photo confiável), mas legalmente continua sendo "dado relativo a características biométricas" porque foi extraído da face.

### 1.3 Consentimento explícito por feature (Art. 8º §4º)
- **Gap CRÍTICO**: nenhum campo `consent_tunel`, `consent_biometric_processing`, `consent_face_matching` no User model. O upload é tratado como ato implícito de consentimento — **isso fere ANPD guia 2023** que exige consentimento granular para tratamento biométrico.
- **Gap**: não há registro de versão da política de privacidade aceita.

### 1.4 Right to delete (Art. 18 V/VI)
- **OK**: `DELETE /api/tunel/upload/{id}` existe, faz soft-delete do upload + apaga arquivo físico + hard-deletes `TunelFace` (embeddings).
- **Gap**: `db.query(TunelFace).filter(...).delete()` ignora o cascade já definido no FK. Funciona, mas se houver `matched_user_id` cruzando com este face, os matches confirmados em outros uploads ficam órfãos. Não há endpoint para o **terceiro reconhecido** revogar match.
- **Gap**: não há endpoint "deletar minha conta" que cascadeie ao Túnel (`ON DELETE CASCADE` no FK do `user_id` cobre o DB mas não os arquivos no disco).

### 1.5 Data export (Art. 18 II/V — portabilidade)
- **Gap CRÍTICO**: **não existe endpoint de exportação**. O usuário não tem como baixar suas fotos + metadata + embeddings em formato estruturado. Obrigatório para LGPD.

### 1.6 Cross-border transfer (Art. 33)
- **Gap**: não há documentação sobre região do Neon (DB) nem do object storage. Render hosting tipicamente é US — exige adequação Art. 33 (cláusulas contratuais ANPD ou países adequados). Sem doc, é violação.

### 1.7 EXIF scrub
- **OK**: `tunel_routes.py` linhas 71-82 strip EXIF.
- **Gap menor**: o método (`Image.new` + `putdata`) destrói também perfil ICC e orientação — fotos podem girar. Usar `img.save(path, exif=b'')` é mais limpo.
- **Gap**: scrub roda **depois** do `f.write(contents)` — o arquivo original com GPS toca o disco antes de ser limpo. Risco de leak em backup snapshot.

### LGPD Score: **4/10**
Implementações boas (EXIF scrub, soft-delete, comentários explícitos) mas faltam pilares: consentimento granular, export, cron de purge, criptografia at-rest, doc de transferência internacional.

---

## 2. Safety Audit

### 2.1 Rate limits
- **Gap CRÍTICO**: nenhuma rota `/api/tunel/*` tem decorator `@limiter.limit(...)`. O Limiter existe em `main.py` mas não é aplicado às rotas do Túnel. Um stalker/bot pode:
  - Fazer 10.000 uploads de teste (10MB cada = 100GB de disk)
  - Tentar matching brute-force
- Recomendação: `5/hour` para upload, `30/minute` para list, `10/minute` para delete.

### 2.2 Default-ghost respeitado no matching
- **NÃO TESTADO/INCERTO**: o código de matching (Sprint S3+) ainda não foi escrito. `TunelFace.matched_user_id` aponta para qualquer User, sem checar `is_discoverable`, `ghost_mode_global` ou `allow_reconnect_requests`. Se Sprint S3 fizer match direto, fere default-ghost.
- **Risco arquitetural**: o face matching produz `matched_user_id` automaticamente — o usuário-alvo nunca consentiu em ser reconhecido por foto antiga upada por terceiro.

### 2.3 Asymmetric reveal preservado
- **Não aplicável ainda**: a feature de reveal está em `reconnect_routes.py`. O Túnel não tem ainda endpoint que mostre matches. Precisa ser arquitetado: quem upou a foto NÃO deve ver "essa cara é Fulano" — deve ver "encontramos alguém, quer enviar request de reconexão? (assimétrico)".

### 2.4 Cenário stalker
- **VULNERABILIDADE GRAVE**: stalker upa foto da vítima (sozinha ou em grupo). Sistema detecta face, gera embedding, e (no Sprint S3) potencialmente faz match com a vítima real registrada — **sem consentimento da vítima**. Isso transforma a feature em sistema de identificação facial não-autorizada.
- **Mitigação obrigatória antes de S3**: matching só pode ocorrer entre fotos de usuários que estejam na **mesma turma** com membership `approved` E que tenham opt-in `consent_face_matching=TRUE`. Vítima sempre pode revogar.
- **Mitigação obrigatória**: rate-limit por user para upload + manual review se > N rostos detectados de pessoas diferentes.

### 2.5 Proteção de menores (18+)
- **Gap CRÍTICO**: User model **não tem `birthdate`/`date_of_birth`**. Impossível enforçar 18+. Fotos podem ser de crianças (formaturas escolares 1995!), e biometria de menor é hipersensível (ECA + LGPD Art. 14).
- Recomendação: bloquear toda foto rotulada como `photo_context` contendo termos "escola", "infantil", "kid", e exigir confirmação explícita "esta foto não contém menores ou tenho autorização dos responsáveis". Adicionar `birthdate` ao registro com gate 18+.

### Safety Score: **3/10**
Sem rate limit, sem gate de menor, cenário stalker viável, default-ghost vulnerável no matching futuro.

---

## 3. Performance Audit

### 3.1 OpenCV Haar Cascade latência
- Haar `detectMultiScale` em imagem 1024×768 → ~80–200 ms CPU single-thread (sem GPU).
- 10MB max image (pode ser 4000×3000) → 400–900 ms.
- **Hoje roda síncrono dentro do request HTTP** (em `tunel_routes.py` o status é `pending` mas não há background task). Será um problema quando S2 conectar o pipeline.
- Recomendação: mover para Celery/RQ/BackgroundTasks. Resize antes da detecção (max 1024px lado maior).

### 3.2 Matching O(n) sobre todos os faces
- Sem `pgvector`, matching é Python loop sobre `TunelFace.embedding` (JSON). Para <10k embeddings, OK (~poucos segundos). Para >100k, inviável.
- Recomendação futura: pgvector + index HNSW. Já que `embedding` é JSON, migrar agora antes de seed.

### 3.3 DB índices
- **OK**: `ix_tunel_uploads_user_id`, `ix_tunel_uploads_turma_id`, `ix_tunel_uploads_processing_status`, `ix_tunel_uploads_deleted_at` (este último útil para purge cron).
- **OK**: `ix_tunel_faces_upload_id`, `ix_tunel_faces_matched_user_id`.
- **Gap**: nenhum índice composto. Query "uploads de uma turma, pending" faz duas-index scan. Adicionar `(turma_id, processing_status)`.
- **Gap**: query do delete em `TunelFace` por `upload_id` está coberta, mas o lookup do upload em `delete_upload` filtra `(id, user_id)` sem índice composto — só PK lookup, performance OK mas pouco seguro contra IDOR se PK fosse adivinhável (já é serial → enumerable; usar UUID público).

### Perf Score: **6/10**
Setup correto para MVP. Pipeline síncrono e absence de pgvector são bloqueadores para escala.

---

## 4. Top 5 Issues to Fix Before Scaling (blockers)

1. **[LGPD/Safety BLOCKER] Sem campo `birthdate` no User → impossível gate 18+** e zero proteção de menores em fotos escolares antigas (cenário-piloto do produto!). Bloqueador para beta público.
2. **[LGPD BLOCKER] Sem consentimento granular `consent_tunel_biometric`** registrado por user + sem registro de versão de política aceita. Bloqueador para passar review ANPD.
3. **[Safety BLOCKER] Cenário stalker viável** — terceiro upa foto da vítima, sistema gera embedding e (em S3) fará match sem opt-in da vítima. Exige `consent_face_matching` + restrição a turmas compartilhadas com membership approved.
4. **[Safety/Cost BLOCKER] Zero rate limit em `/api/tunel/*`** — abuso trivial (disk DoS, brute-force matching). Adicionar `@limiter.limit("5/hour")` em upload, `@limiter.limit("30/minute")` em list/delete.
5. **[LGPD BLOCKER] Falta cron de purge 30 dias + endpoint de export (portabilidade)** — Art. 18 II/V e princípio da necessidade Art. 6º III. Adicionar job scheduled + `GET /api/tunel/export/me` retornando ZIP de fotos+JSON.

---

## 5. Recommendations (prioridade)

### Antes de beta público (P0)
- Adicionar `birthdate` em User; bloquear `/api/tunel/upload` se `age < 18`.
- Adicionar `consent_tunel_biometric`, `consent_face_matching`, `policy_version_accepted` em User.
- Adicionar `@limiter.limit("5/hour")` em upload, `@limiter.limit("30/minute")` em list, `@limiter.limit("10/minute")` em delete.
- Implementar cron de purge 30d (rows + arquivos físicos) via APScheduler ou Celery beat.
- Implementar `GET /api/tunel/export/me` (LGPD Art. 18 V/II).
- Documentar região do Neon + Render em `/public/landing/privacy.html` (Art. 33).

### Antes de Sprint S3 matching (P0)
- Matching só dentro de turma onde **ambos** usuários têm membership approved.
- Matching só se vítima opt-in `consent_face_matching=TRUE`.
- Matching nunca revela identidade para quem upou — usa fluxo asymmetric reveal do reconnect.
- Endpoint para qualquer usuário "revogar match" e bloquear futuras detecções no embedding dele.

### Hardening (P1)
- Mover face detection para background task (FastAPI `BackgroundTasks` no MVP, Celery em scale).
- Resize obrigatório para max 1024px antes da detecção.
- Migrar `embedding JSON` para `pgvector` com index HNSW antes de >10k uploads.
- Cifrar embeddings at-rest (column-level KMS).
- Trocar histograma por FaceNet/ArcFace ONNX (qualidade do match — histograma terá MUITO falso positivo).
- EXIF scrub: ler bytes em memória, strip EXIF com Pillow, depois `f.write` — evitar arquivo raw com GPS tocar disco.
- IDs públicos em UUID em vez de SERIAL (anti-enumeration).
- Índice composto `(turma_id, processing_status)`.

### Documentação (P1)
- Atualizar `/public/landing/privacy.html` com seção específica Túnel: tipos de dado, retenção 30d, base legal (consentimento granular), direitos do titular, DPO/encarregado.
- Manter `policy_version` no DB e exigir re-consent quando muda.

---

## Scorecard

| Eixo | Score |
|------|-------|
| LGPD Compliance | 4/10 |
| Safety | 3/10 |
| Performance | 6/10 |
| **Geral** | **4.3/10** |

**Pronto para beta?** **Não.** 5 blockers críticos. Estimativa: 3–5 dias-dev para destravar P0 mínimo viável (birthdate, consent flags, rate-limit, cron purge, export endpoint, doc de privacidade). Sprint S3 matching NÃO pode subir sem opt-in `consent_face_matching` e restrição a turmas compartilhadas.
