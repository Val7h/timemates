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

from database import TunelFace, TunelUpload, User, TurmaMembership

logger = logging.getLogger(__name__)

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

    results = []
    for cand in candidates:
        if not cand.embedding:
            continue
        sim = cosine_similarity(target_embedding, cand.embedding)
        if sim < threshold:
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

    results = []
    for r in rows:
        sim = float(r.similarity)
        if sim < threshold:
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
