"""Face matching engine. Uses cosine similarity over JSON embeddings.
Future: migrate to pgvector when scale > 10k faces.

PRIVACY INVARIANTS (Sprint 2 S3):
  - Respects is_discoverable opt-in (default-ghost).
  - Respects ghost_mode_global panic toggle.
  - Allows same-turma matches even if user is not discoverable globally.
  - NEVER exposes name/photo of candidate in match response.
    Only similarity + bbox + a face_id used to trigger asymmetric reveal
    via the existing /api/reconnect double opt-in flow.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import TunelFace, TunelUpload, User, TurmaMembership, PersonOptOut

logger = logging.getLogger(__name__)

# ─── Opt-out facial (supressão) ───────────────────────────────────────────────
# LIMIAR CONSERVADOR: deliberadamente mais agressivo (mais baixo) que o de match
# (0.85). Erramos a favor da PROTEÇÃO: se há dúvida razoável de que o candidato é
# a pessoa que pediu para sumir, suprimimos. Um falso-positivo aqui só esconde um
# rosto a mais de uma busca; um falso-negativo expõe quem explicitamente pediu
# privacidade — assimetria de dano que justifica o limiar baixo.
SUPPRESS_THRESHOLD = 0.80


def _load_opted_out_faces(db: Session) -> List[Dict]:
    """Carrega UMA vez a lista de rostos com opt-out facial ativo.

    Retorna lista de dicts {embedding, model}. Chamada UMA vez por busca (não por
    candidato) para evitar re-query em loop — ver uso cacheado abaixo.
    """
    rows = db.query(PersonOptOut).filter(
        PersonOptOut.ativo == True,  # noqa: E712
        PersonOptOut.face_embedding.isnot(None),
    ).all()
    return [{'embedding': r.face_embedding, 'model': r.embedding_model} for r in rows]


def is_face_opted_out(db: Session, embedding: List[float], _cache: Optional[List[Dict]] = None) -> bool:
    """True se `embedding` bate com ALGUM rosto que pediu opt-out facial (>= SUPPRESS_THRESHOLD).

    Compara o embedding candidato contra TODOS os PersonOptOut ativos com
    face_embedding não-nulo via cosine_similarity. Usado para:
      - SUPRIMIR candidatos no motor de busca (find_matches_*).
      - NÃO-RETER o embedding no upload de terceiros (tunel_routes).

    `_cache`: passe a lista de _load_opted_out_faces(db) para evitar re-query por
    candidato dentro de um loop. Se None, faz a query (caminho de chamada única,
    ex.: no upload).
    """
    if not embedding:
        return False
    opted = _cache if _cache is not None else _load_opted_out_faces(db)
    for o in opted:
        oe = o.get('embedding')
        if not oe:
            continue
        if cosine_similarity(embedding, oe) >= SUPPRESS_THRESHOLD:
            return True
    return False

# Rate limit: 10 matches/dia/user (in-memory; replace with Redis in prod).
_RATE_LIMIT_PER_DAY = 10
_rate_state: Dict[int, List[datetime]] = {}


def _check_rate_limit(user_id: int) -> None:
    now = datetime.utcnow()
    cutoff = now - timedelta(days=1)
    hits = [t for t in _rate_state.get(user_id, []) if t > cutoff]
    if len(hits) >= _RATE_LIMIT_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {_RATE_LIMIT_PER_DAY} buscas de matching por dia atingido. Tente amanhã.",
        )
    hits.append(now)
    _rate_state[user_id] = hits


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    a_np = np.array(a)
    b_np = np.array(b)
    na = np.linalg.norm(a_np)
    nb = np.linalg.norm(b_np)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / (na * nb))


def find_matches_for_face(
    db: Session,
    target_embedding: List[float],
    requester_user_id: int,
    threshold: float = 0.85,
    limit: int = 5,
) -> List[Dict]:
    """
    Encontra faces similares na base.
    Respeita default-ghost: só retorna users discoverable OR same turma.
    NUNCA expõe nome/foto do candidato — só id mascarado + bbox + similaridade.
    """
    # Buscar todas faces de OUTROS users (joined com upload pra filtrar deleted)
    candidates = db.query(TunelFace).join(
        TunelUpload, TunelFace.upload_id == TunelUpload.id
    ).filter(
        TunelUpload.user_id != requester_user_id,
        TunelUpload.deleted_at.is_(None),
    ).all()

    # IDs de users em turmas comuns com requester (filtro discoverability).
    requester_turmas = db.query(TurmaMembership.turma_id).filter(
        TurmaMembership.user_id == requester_user_id,
        TurmaMembership.status == 'verified',
    ).subquery()

    shared_turma_users = set(
        u[0] for u in db.query(TurmaMembership.user_id).filter(
            TurmaMembership.turma_id.in_(requester_turmas)
        ).all()
    )

    # Opt-out facial: carrega rostos suprimidos UMA vez por busca (não por candidato).
    opted_out_cache = _load_opted_out_faces(db)

    results = []
    for cand in candidates:
        if not cand.embedding:
            continue
        sim = cosine_similarity(target_embedding, cand.embedding)
        if sim < threshold:
            continue
        # OPT-OUT FACIAL: se o rosto do candidato pediu para sumir, suprime ANTES
        # de qualquer outro filtro. Ninguém com opt-out facial vira resultado.
        if is_face_opted_out(db, cand.embedding, _cache=opted_out_cache):
            continue
        # Pegar owner da face via upload
        owner = db.query(User).join(
            TunelUpload, TunelUpload.user_id == User.id
        ).filter(TunelUpload.id == cand.upload_id).first()
        if not owner:
            continue
        # Filtro: discoverable OR same turma
        if not owner.is_discoverable and owner.id not in shared_turma_users:
            continue
        # Filtro: not panic-ghost
        if getattr(owner, 'ghost_mode_global', False):
            continue
        # ANTI-STALKER: target só aparece se ELE TAMBÉM upou foto E consentiu face_matching
        try:
            from consent_helpers import has_active_consent
            from database import TunelUpload
            target_has_consent = has_active_consent(db, owner.id, 'face_matching')
            target_uploaded = db.query(TunelUpload).filter(
                TunelUpload.user_id == owner.id,
                TunelUpload.deleted_at.is_(None),
            ).count() > 0
            if not (target_has_consent and target_uploaded):
                continue  # bloqueado por consent
        except Exception:
            # Conservador: se algo falhar, NÃO mostrar match
            continue
        # PRIVACY: NÃO expor name, email, photo_url, nada identificável.
        # face_id é o handle pro reconnect flow assimétrico.
        results.append({
            'face_id': cand.id,
            'upload_id': cand.upload_id,
            'similarity': round(sim, 3),
            'preview_bbox': {
                'x': cand.bbox_x, 'y': cand.bbox_y,
                'w': cand.bbox_w, 'h': cand.bbox_h,
            },
            'reconnect_hint': 'Use POST /api/tunel/match/{face_id}/reconnect para iniciar reveal assimétrico.',
        })
    results.sort(key=lambda r: -r['similarity'])
    return results[:limit]


def find_matches_for_upload(
    db: Session,
    upload_id: int,
    requester_user_id: int,
) -> Dict:
    """Roda matching pra cada face detectada num upload do próprio user."""
    upload = db.query(TunelUpload).filter(TunelUpload.id == upload_id).first()
    if not upload:
        return {'error': 'upload not found'}
    if upload.user_id != requester_user_id:
        return {'error': 'not owner'}

    # Rate limit aplicado por upload-search (1 request = 1 cota).
    _check_rate_limit(requester_user_id)

    faces = db.query(TunelFace).filter(TunelFace.upload_id == upload_id).all()
    out = []
    for f in faces:
        if not f.embedding:
            continue
        matches = find_matches_for_face(db, f.embedding, requester_user_id)
        out.append({
            'face_index': f.face_index,
            'matches_count': len(matches),
            'top_matches': matches,
        })
    return {'upload_id': upload_id, 'faces': out}


def find_matches_v2(
    db: Session,
    target_embedding: List[float],
    requester_user_id: int,
    threshold: float = 0.5,
    limit: int = 5,
) -> List[Dict]:
    """v2: pgvector cosine search em vez do loop Python.

    Usa operador `<=>` do pgvector (cosine distance: 0 = idêntico, 2 = oposto).
    similarity = 1 - distance, threshold 0.5 funciona pra ArcFace (vs 0.85 pro
    histogram antigo — escalas diferentes).

    Preserva TODOS os filtros de privacidade do find_matches_for_face:
    default-ghost, ghost_mode_global, anti-stalker consent, same-turma override.
    """
    from sqlalchemy import text

    # pgvector quer string '[v1,v2,...]' como literal — bind param :emb
    embedding_str = '[' + ','.join(str(x) for x in target_embedding) + ']'

    # Sobre-buscamos (limit * 3) pra ter folga após filtros de privacidade
    rows = db.execute(text('''
        SELECT f.id, f.upload_id, f.bbox_x, f.bbox_y, f.bbox_w, f.bbox_h,
               f.embedding AS cand_embedding,
               1 - (f.embedding_vec <=> CAST(:emb AS vector)) AS similarity,
               u.user_id AS owner_id
        FROM tunel_faces f
        JOIN tunel_uploads u ON u.id = f.upload_id
        WHERE f.embedding_vec IS NOT NULL
          AND u.user_id != :requester
          AND u.deleted_at IS NULL
        ORDER BY f.embedding_vec <=> CAST(:emb AS vector)
        LIMIT :lim
    '''), {'emb': embedding_str, 'requester': requester_user_id, 'lim': limit * 3}).fetchall()

    # Filtro discoverability (mesma lógica do v1)
    requester_turmas = db.query(TurmaMembership.turma_id).filter(
        TurmaMembership.user_id == requester_user_id,
        TurmaMembership.status == 'verified',
    ).subquery()
    shared_turma_users = set(
        u[0] for u in db.query(TurmaMembership.user_id).filter(
            TurmaMembership.turma_id.in_(requester_turmas)
        ).all()
    )

    # Opt-out facial: carrega rostos suprimidos UMA vez por busca (não por candidato).
    opted_out_cache = _load_opted_out_faces(db)

    results = []
    for r in rows:
        sim = float(r.similarity)
        if sim < threshold:
            continue
        # OPT-OUT FACIAL: suprime QUALQUER candidato cujo rosto pediu para sumir.
        # A query traz f.embedding (JSON) p/ checar sem re-query por candidato.
        # O JSON pode voltar como str (alguns drivers) ou já parseado — normaliza.
        cand_emb = r.cand_embedding
        if isinstance(cand_emb, str):
            try:
                import json as _json
                cand_emb = _json.loads(cand_emb)
            except Exception:
                cand_emb = None
        if cand_emb and is_face_opted_out(db, cand_emb, _cache=opted_out_cache):
            continue
        owner = db.query(User).filter(User.id == r.owner_id).first()
        if not owner:
            continue
        if not owner.is_discoverable and owner.id not in shared_turma_users:
            continue
        if getattr(owner, 'ghost_mode_global', False):
            continue
        # ANTI-STALKER: mesma checagem do v1
        try:
            from consent_helpers import has_active_consent
            target_has_consent = has_active_consent(db, owner.id, 'face_matching')
            target_uploaded = db.query(TunelUpload).filter(
                TunelUpload.user_id == owner.id,
                TunelUpload.deleted_at.is_(None),
            ).count() > 0
            if not (target_has_consent and target_uploaded):
                continue
        except Exception:
            continue

        results.append({
            'face_id': r.id,
            'upload_id': r.upload_id,
            'similarity': round(sim, 3),
            'preview_bbox': {
                'x': r.bbox_x, 'y': r.bbox_y,
                'w': r.bbox_w, 'h': r.bbox_h,
            },
            'reconnect_hint': 'Use POST /api/tunel/match/{face_id}/reconnect para iniciar reveal assimétrico.',
        })
        if len(results) >= limit:
            break
    return results


def initiate_reconnect_for_face(
    db: Session,
    face_id: int,
    requester_user_id: int,
) -> Dict:
    """Inicia reconnect assimétrico contra o owner de uma face matched.

    NÃO revela identidade aqui. Apenas devolve o user_id alvo, que será passado
    pro /api/reconnect existente — que implementa double opt-in (alvo precisa
    aceitar pra revelar foto/nome de cada lado).
    """
    face = db.query(TunelFace).filter(TunelFace.id == face_id).first()
    if not face:
        raise HTTPException(404, "Face não encontrada")
    upload = db.query(TunelUpload).filter(
        TunelUpload.id == face.upload_id,
        TunelUpload.deleted_at.is_(None),
    ).first()
    if not upload:
        raise HTTPException(404, "Upload da face não encontrado ou deletado")
    if upload.user_id == requester_user_id:
        raise HTTPException(400, "Você não pode reconectar com você mesmo")

    target = db.query(User).filter(User.id == upload.user_id).first()
    if not target:
        raise HTTPException(404, "Usuário alvo não encontrado")
    if getattr(target, 'ghost_mode_global', False):
        # Panic-ghost: como se não existisse. Mesma mensagem do not-found
        # pra não vazar existência do user.
        raise HTTPException(404, "Face não encontrada")

    return {
        'success': True,
        'target_user_id': target.id,  # consumido pelo /api/reconnect (assimétrico)
        'next_step': 'POST /api/reconnect com este target_user_id para enviar pedido de reconexão. Identidade só é revelada após double opt-in.',
    }
