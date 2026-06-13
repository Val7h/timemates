"""Ice-breaker generation. Template-based fallback when no LLM API key configured.
Future: integrate Claude/OpenAI API for personalized messages.

Voice (COPY_GUIDE_V2): saudoso, brotherly, bittersweet — never salesy,
never assuming intimacy. The user can always edit before sending.

Why templates first (and not LLM)?
  - Zero latency, zero cost, zero refusal risk for MVP.
  - Lets us ship the UX (3-options-then-edit) and harvest which templates
    actually get sent. Future swap to Claude becomes a single function body
    change once ANTHROPIC_API_KEY is set.
"""

from __future__ import annotations

import os
import random
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from database import User, Turma, TurmaMembership, TunelUpload


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


def generate_icebreaker(
    db: Session,
    requester_id: int,
    target_id: int,
) -> Dict:
    """Gera até 3 opções de mensagem baseadas no contexto compartilhado.

    Estratégia:
      * Se há Turma em comum → 2 templates específicos da turma + 1 de school.
      * Se não há → 3 genéricos com placeholder neutro 'lá atrás'.

    O resultado vem sempre como `editable=True`: a UI deve mostrar as três,
    deixar o user escolher uma e editar antes de POST /api/reconnect.
    """
    context = gather_shared_context(db, requester_id, target_id)
    shared = context['shared_turmas']

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
        'method': 'template_v1',  # quando trocar pra Claude, vira 'llm_claude'
        'editable': True,  # user pode (e deve) editar antes de enviar
    }


# ─── Future: LLM hook ────────────────────────────────────────────────────────
#
# Quando `ANTHROPIC_API_KEY` existir no env, substituir o corpo de
# `generate_icebreaker` por uma chamada ao Claude passando:
#   - shared Turmas (ano, instituição, cidade)
#   - mural memories tagueadas em comum (cheiros, lugares, professores)
#   - foto antiga do túnel se houver match facial > threshold
# e pedir 3 variações tom "saudoso brotherly bittersweet, PT-BR, máx 280 chars,
# sem assumir intimidade". Manter `editable=True` no retorno.
#
# Helper já estub:

def _llm_configured() -> bool:
    """Retorna True quando temos credenciais pra trocar templates por LLM."""
    return bool(os.getenv('ANTHROPIC_API_KEY'))
