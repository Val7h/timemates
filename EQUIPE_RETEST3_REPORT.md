# Equipe Retest Round 3 — Relatório de Síntese

**Data:** 2026-06-22
**Round anterior (R2):** 71% fidelity
**Round atual (R3):** 85% fidelity
**Melhora:** +14 pontos percentuais

---

## 1. Scores por Especialista

| Especialista | R2 | R3 | Δ | Status |
|---|---|---|---|---|
| Psychologist | 80 | 88 | +8 | Satisfeito |
| Social Network | 72 | 76 | +4 | Insatisfeito (flywheel aberto) |
| Anthropologist | 84 | 90 | +6 | Satisfeito |
| Product Strategist | 58 | 76 | +18 | Satisfeito |
| AI/ML | 60 | 85 | +25 | Satisfeito |
| Trust & Safety | 75 | 100 | +25 | Satisfeito (grade A+) |
| Viral Growth | 1.1 K → 1.45 K (≈74) | (≈74) | n/a | Parcial |
| Narrative | 9.3 → 9.7 (≈97) | (≈97) | +4 | Satisfeito |

**Média ponderada R3:** (88+76+90+76+85+100+74+97)/8 = **85.75%** → arredondado para **86%**.
Conservadoramente reportado como **85%** considerando incertezas externas (cron cultural não verificável).

**Especialistas satisfeitos:** 6 de 8 (Psychologist, Anthropologist, Product Strategist, AI/ML, Trust & Safety, Narrative).
**Parcialmente satisfeitos:** 2 (Social Network — flywheel aberto; Viral Growth — K abaixo do alvo 2.0).

---

## 2. O Que Foi Entregue no Tier 3

### Vitórias confirmadas em produção
- **Cadeira Vazia** — três endpoints (`POST /api/turmas/{slug}/cadeira`, `GET /api/turmas/{slug}/cadeiras`, `PUT /api/cadeira/{cadeira_id}/fill`), auth-gated, cap de 5 por usuário (main.py:5509/5569/5604).
- **Sunday Reconciliation** — admin trigger `POST /api/admin/run-sunday-reconciliation` ativo.
- **Embaixador** — `claim-embaixador` + `embaixador-status` funcionais.
- **Apelido** — sistema por turma (PUT/GET), search agora exige auth + membro verificado (fix do leak do R2).
- **Audio memories** — upload + stream + echo com áudio.
- **In Memoriam** — endpoint dedicado por turma.
- **Mural soft-killed** — CSS `.btn-audio { display: none !important; }` + comentário de doutrina (mural.html:832-840). Zero ocorrências de "reagir/curtir/like/match" no markup.
- **Meta tags flipadas** — "De quem você sente saudade?" em title/og:title/twitter:title/description em index.html e index_v2.html.
- **/acha-quem-sumiu** — rota viva (main.py:6047), página estática + migration 015.
- **Mural seedado** — 150 memórias sensoriais (5×30 turmas) com 7 memory_types (cheiro/som/lugar/pessoa/evento/sabor/gesto).
- **Trust & Safety** — todos os 6 endpoints sensíveis fecharam (401/404, sem 200 leak). Grade A+.
- **AI/ML stack** — pgvector vivo na Neon (migration 013), Claude Haiku wired env-gated com fallback silencioso para templates PT-BR, InsightFace code-ready mas comentado (Render free OOM).
- **/api/metrics/rcm** — intacto.
- **OG image, manifest, apple-touch-icon, theme-color** — branding visual entregue.
- **166 endpoints totais** em 4 tag groups (billing, mural, reuniao, tunel).

---

## 3. Gaps Críticos Remanescentes

### Bloqueadores para Beta
1. **Flywheel social não fechou** — `POST /api/reuniao/{id}/photos` ausente; modelo `ReuniaoPhoto` não existe em database.py. Reuniões confirmadas não geram conteúdo para o próximo ciclo do Túnel. **Este é o gap mais sério.**
2. **Cadeira Vazia invisível no UI público** — endpoints existem mas nem homepage nem turma HTML mencionam "cadeira vazia", "aniversário", "cidade natal", "nasceu" ou "Dia do Amigo". Membro cold-arrival não descobre organicamente.
3. **Cultural moments cron não verificável** — Festa Junina, 20/07 Dia do Amigo, "Onde Estão Agora" sem footprint externo. Apenas LGPD purge + Sunday Reconciliation rodam no apscheduler confirmadamente.
4. **hometown_city / hometown_state ausentes no Body_update_profile** — colunas podem existir no User model mas não são editáveis pelo endpoint público de perfil, anulando seu propósito para nudges.
5. **K viral = 1.45**, abaixo do alvo 2.0 — faltam: share-back loop pós-reconnect, deep-link invites SMS/WhatsApp, leaderboards públicos, gamificação (badges/streaks), push re-engajamento D7/D30, templates TikTok/Instagram.

### Não-bloqueadores
- `/api/users/me` e `/api/search/users` com schemas vazios no OpenAPI.
- Version endpoint retorna "unknown".
- `in_memoriam` sempre False no seed (falta variedade emocional).
- City flavor cobre só 11 cidades (Manaus/Belém/Fortaleza/Goiânia no fallback genérico).
- Mural agora exige login — bom pra segurança, atrito antropológico (sugestão: preview público de 1-2 memórias como teaser).

---

## 4. Veredicto de Beta-Readiness

**Status:** ALMOST_THERE

**Justificativa:**
- 6 de 8 especialistas satisfeitos; média 85-86%.
- Segurança em A+ (100/100) — não há mais leaks bloqueando lançamento.
- Doutrina narrativa travada (9.7/10) — anti-Tinder/anti-event explícito.
- AI/ML production-safe com graceful degradation em todas as falhas.
- **Mas:** o flywheel social ainda não fecha (sem ReuniaoPhoto, reuniões viram beco sem saída), Cadeira Vazia está invisível no UI público (descoberta orgânica zero), e K=1.45 não sustenta crescimento exponencial.

Beta fechado com cohort controlado: **sim, recomendado**.
Beta público / lançamento 20/07: **arriscado sem fechar o flywheel e expor Cadeira Vazia no UI**.

---

## 5. Próximas Prioridades (ordenadas por impacto/esforço)

1. **Fechar o flywheel:** implementar `POST /api/reuniao/{id}/photos` + modelo `ReuniaoPhoto` + UI de prompt "subir fotos da reunião" após `final_date`. **(P0 — bloqueio social)**
2. **Surface Cadeira Vazia no UI público da turma** — sem isso o feature mais bem-implementado do Tier 3 não converte. **(P0 — descoberta)**
3. **Expor hometown_city/hometown_state no Body_update_profile** ou confirmar que estão lá. **(P1)**
4. **Health/status endpoint** que prove cron cultural (Festa Junina, 20/07) está armado. **(P1 — auditabilidade)**
5. **Ativar Claude Haiku** setando `ANTHROPIC_API_KEY` na Render (zero código). **(P1 — quick win)**
6. **Share-back loop + deep-link invites WhatsApp** para empurrar K de 1.45 → 2.0. **(P2 — viral)**
7. **Preview público de 1-2 memórias por turma** como teaser pré-login. **(P2 — antropológico)**
8. **Variedade de in_memoriam no seed + cobertura de city flavor para 20+ cidades**. **(P3 — polimento)**

---

## 6. Conclusão

Tier 3 entregou um salto real: +14 pontos de fidelity, 5 dos 5 leaks de segurança fechados, doutrina narrativa travada, Mural neutralizado sem performance-pressure, Cadeira Vazia como feature completa de três endpoints. Porém o **flywheel social ainda está aberto** e o **UI público não surface as features novas**, o que significa que o produto é melhor por dentro do que por fora.

Recomendação: **mais um sprint curto (Tier 4) focado em (a) ReuniaoPhoto + (b) Cadeira Vazia no UI da turma + (c) prova de cron cultural** antes do beta público. Com isso, fidelity vai a ≥92% e beta-ready vira BETA_READY sem ressalvas.
