"""Ice-breaker generation. Claude LLM if ANTHROPIC_API_KEY set, else templates.

Voice (COPY_GUIDE_V2): saudoso, brotherly, bittersweet — never salesy,
never assuming intimacy. The user can always edit before sending.

LLM strategy (Sprint 3 AI/ML):
  - When ANTHROPIC_API_KEY is set in env, route to Claude Haiku (cheapest/fastest)
    with a tight prompt that ONLY cites verified context (no hallucinated memories).
  - On ANY failure (network, JSON parse, quota), silently fall back to templates
    so the user-facing UX never breaks.
  - To enable LLM: add ANTHROPIC_API_KEY to Render env vars
    See: https://console.anthropic.com/

Why templates as the foundation (and not LLM-only)?
  - Zero latency, zero cost, zero refusal risk on the hot path.
  - Lets us ship the UX (3-options-then-edit) and harvest which messages
    actually get sent. Claude is opt-in via the env var.
"""

from __future__ import annotations

import os
import json
import re
import logging
import random
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from database import User, Turma, TurmaMembership, TunelUpload


# Cached at import time. Render redeploys whenever env vars change, so
# this is effectively live without paying the os.getenv cost per request.
_llm_configured = bool(os.getenv('ANTHROPIC_API_KEY'))


# ─── Templates PT-BR (COPY_GUIDE_V2: saudoso, brotherly, bittersweet) ─────────
#
# Cada template tem placeholders nomeados. Nunca presumimos intimidade ("amigo",
# "querido"), nem usamos linguagem de venda. Tom: "achei uma foto e lembrei".

TEMPLATES_GENERIC: List[str] = [
    "Você lembra de mim? Acho que estávamos juntos {context}. Quanto tempo, hein?",
    "Achei uma foto antiga e jurava que era você. {context}. Tudo bem aí?",
    "Topa matar uma saudade? Se for você mesmo {context} eu adoraria reencontrar.",
    "Foi mal a abordagem do nada, mas... {context}? Lembrei agora e quis dizer oi.",
    "Sei que faz um tempão. {context} — você ainda lembra? Bora colocar a conversa em dia?",
]

TEMPLATES_SAME_TURMA: List[str] = [
    "Lembra da nossa Turma {ano}? {sentido} ver as fotos antigas trouxe você na cabeça. Tudo bem?",
    "Achei uma foto da Turma {ano} e você tava lá. Que saudade — bora marcar um café?",
    "Reencontrei pessoal da Turma {ano} e perguntaram de você. Tá sumido(a)! Tudo bem?",
    "Tô organizando algo da Turma {ano}. Você topa dar as caras de novo? Bora.",
]

TEMPLATES_SAME_SCHOOL: List[str] = [
    "Estudamos no(a) {school}, certo? Lembro de você ali. Quanto tempo passou! Tudo certo?",
    "Você é do(a) {school}? Aposto que sim. Bora atualizar essa história?",
]

# Conectivos para variar o tom do template SAME_TURMA sem repetir abertura.
_SENTIDOS = [
    "Tava aqui pensando e",
    "Que loucura,",
    "Outro dia,",
    "Do nada me bateu uma saudade —",
]


def gather_shared_context(
    db: Session,
    requester_id: int,
    target_id: int,
) -> Dict:
    """Coleta contexto verificado entre dois users.

    Só conta Turmas onde AMBOS estão como 'verified' — pending/ghost não
    geram contexto, pois ainda não temos prova social de que pertencem.
    """
    req_turmas = set(
        t[0] for t in db.query(TurmaMembership.turma_id).filter(
            TurmaMembership.user_id == requester_id,
            TurmaMembership.status == 'verified',
        ).all()
    )
    target_turmas = set(
        t[0] for t in db.query(TurmaMembership.turma_id).filter(
            TurmaMembership.user_id == target_id,
            TurmaMembership.status == 'verified',
        ).all()
    )
    shared_turma_ids = req_turmas & target_turmas
    shared_turmas = (
        db.query(Turma).filter(Turma.id.in_(shared_turma_ids)).all()
        if shared_turma_ids else []
    )

    return {
        'shared_turmas': [
            {
                'id': t.id,
                'institution_name': t.institution_name,
                'cohort_year': t.cohort_year,
                'cohort_label': t.cohort_label,
                'kind': t.kind,
            }
            for t in shared_turmas
        ],
        'shared_count': len(shared_turmas),
    }


def generate_icebreaker_templates(
    shared_context: Dict,
    target_full_name: str,
) -> Dict:
    """Pure-template generator (the original logic, extracted for fallback use).

    Estratégia:
      * Se há Turma em comum → 2 templates específicos da turma + 1 de school.
      * Se não há → 3 genéricos com placeholder neutro 'lá atrás'.
    """
    shared = shared_context.get('shared_turmas', [])
    suggestions: List[str] = []
    if shared:
        # Pega a Turma mais "rica" (com cohort_label > sem label) como âncora.
        t = sorted(shared, key=lambda x: (x.get('cohort_label') is None, -x['cohort_year']))[0]

        # 2 templates de Turma específica
        for tpl in random.sample(
            TEMPLATES_SAME_TURMA,
            k=min(2, len(TEMPLATES_SAME_TURMA)),
        ):
            msg = tpl.format(
                ano=t['cohort_year'],
                sentido=random.choice(_SENTIDOS),
            )
            suggestions.append(msg)

        # 1 template de School/institution
        for tpl in random.sample(TEMPLATES_SAME_SCHOOL, k=1):
            suggestions.append(tpl.format(school=t['institution_name']))
    else:
        # Sem contexto verificado: 3 genéricos. A copy fica deliberadamente
        # vaga ("lá atrás") pra não fabricar memória que não existe.
        for tpl in random.sample(TEMPLATES_GENERIC, k=3):
            suggestions.append(tpl.format(context='lá atrás'))

    return {
        'success': True,
        'context_summary': (
            f"{len(shared)} turma(s) em comum"
            if shared else "Sem contexto compartilhado verificado"
        ),
        'suggestions': suggestions[:3],
        'method': 'template_v1',
        'editable': True,  # user pode (e deve) editar antes de enviar
    }


def generate_icebreaker_v2(shared_context: Dict, target_full_name: str) -> Dict:
    """Generate 3 ice-breaker variants.

    If ANTHROPIC_API_KEY is set, uses Claude Haiku. Else falls back to templates.
    Any LLM error (network, parse, quota) silently degrades to templates so the
    user-facing UX is never blocked.
    """
    if not _llm_configured:
        return generate_icebreaker_templates(shared_context, target_full_name)

    try:
        from anthropic import Anthropic
        client = Anthropic()

        first_name = target_full_name.split()[0] if target_full_name else 'amigo'
        prompt = f"""Você é um copywriter brasileiro que escreve mensagens de reconexão entre ex-colegas.

Pessoa A quer reconectar com Pessoa B (chamada {first_name}).
Contexto VERIFICADO compartilhado:
{shared_context}

Gere 3 variantes de mensagem PT-BR de reconexão, cada uma:
- Máximo 280 caracteres
- Tom: brotherly + saudoso + nada cringe
- Cita APENAS fatos do contexto acima (NÃO INVENTE)
- Sem "amigo querido" ou similar
- Sem emoji em excesso

Retorne APENAS um JSON array de 3 strings, sem nenhum outro texto."""

        response = client.messages.create(
            model='claude-haiku-4-5-20251001',  # cheapest/fastest
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt}],
        )
        text = response.content[0].text.strip()

        # Extract JSON array (model may wrap in ```json fences or prose)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            suggestions = json.loads(match.group())
            if isinstance(suggestions, list) and len(suggestions) >= 1:
                return {
                    'success': True,
                    'context_summary': (
                        f"{len(shared_context.get('shared_turmas', []))} turma(s) em comum"
                    ),
                    'suggestions': suggestions[:3],
                    'method': 'llm_claude_haiku',
                    'editable': True,
                }
    except Exception as e:
        logging.warning(f"[ICEBREAKER] Claude failed: {e}, falling back to templates")

    return generate_icebreaker_templates(shared_context, target_full_name)


def generate_icebreaker(
    db: Session,
    requester_id: int,
    target_id: int,
) -> Dict:
    """Gera até 3 opções de mensagem baseadas no contexto compartilhado.

    Roteamento:
      * ANTHROPIC_API_KEY no env → Claude Haiku (com fallback p/ templates).
      * Sem env var → templates puros.

    O resultado vem sempre como `editable=True`: a UI deve mostrar as três,
    deixar o user escolher uma e editar antes de POST /api/reconnect.
    """
    context = gather_shared_context(db, requester_id, target_id)

    # Resolve target name for LLM personalization (Claude path only — templates
    # ignore it). Best-effort: if user disappeared mid-flow we just pass empty.
    target = db.query(User).filter(User.id == target_id).first()
    target_full_name = (target.full_name if target and target.full_name else '') or ''

    return generate_icebreaker_v2(context, target_full_name)


# ─── Legacy helper kept for backward compat with anything that imported it ────

def _llm_configured_check() -> bool:
    """Retorna True quando temos credenciais pra trocar templates por LLM.

    Deprecated: prefer the module-level `_llm_configured` constant which is
    cached at import time (Render restarts the process on env var changes).
    """
    return bool(os.getenv('ANTHROPIC_API_KEY'))
