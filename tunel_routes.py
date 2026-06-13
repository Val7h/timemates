"""
Túnel do Tempo — Upload Routes (Sprint 2 S1 Foundation)

Endpoints LGPD-aware para upload de fotos antigas:
  - POST   /api/tunel/upload          (multipart: file + metadata)
  - GET    /api/tunel/uploads/me      (lista uploads do user)
  - DELETE /api/tunel/upload/{id}     (LGPD Art. 18: direito ao apagamento)

Validações:
  - MIME: jpg/jpeg/png/webp
  - Tamanho máximo: 10MB
  - Auth obrigatório
  - EXIF scrub (remove GPS, câmera, timestamp da foto)
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, User, TunelUpload, TunelFace
from auth import get_current_user_required, require_18_plus
from consent_helpers import has_active_consent
from tunel_icebreaker import generate_icebreaker


# ─── Rate-limit key function ──────────────────────────────────────────────────
# Slowapi's key_func runs BEFORE the FastAPI auth dependency, so we look at
# request.state.user (which each endpoint binds explicitly) and fall back to IP.
# IP-keyed rate limits would be trivially shared across NATed users (carrier
# CGNAT, office wifi), so per-user buckets are the only sane choice for LGPD-
# sensitive endpoints.
def _user_id_key(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


# Limiter is injected at app startup via ``attach_limiter`` (called from main.py
# after the slowapi Limiter is constructed). We hold a module-level proxy so
# the @decorators below resolve at import time without circular-importing main.
class _LimiterProxy:
    """Forwards .limit(...) to the real slowapi Limiter once attached.

    The @limit decorators below execute at MODULE IMPORT time — before main.py
    has a chance to inject the real Limiter. So this proxy returns a thin
    wrapper that captures (args, kwargs, func) and re-applies them once the
    real limiter is attached. This keeps the route registration order in main.py
    sane (import → attach) without forcing a register_routes() refactor.
    """
    _real = None
    _pending: list = []  # (args, kwargs, func) tuples awaiting real limiter

    def limit(self, *args, **kwargs):
        proxy = self

        def _decorator(func):
            if proxy._real is not None:
                return proxy._real.limit(*args, **kwargs)(func)
            # Stash for later. We mutate func in-place by wrapping it with a
            # closure that re-resolves the wrapped target the first time it's
            # called (after attach_limiter has run during app boot).
            proxy._pending.append((args, kwargs, func))
            return func  # FastAPI captures this; we patch its slot at attach.

        return _decorator


limiter = _LimiterProxy()


def attach_limiter(real_limiter, app=None) -> None:
    """Inject the app-wide slowapi Limiter and apply any pending decorators.

    Call once from main.py BEFORE include_router(tunel_router). If called
    after, we re-decorate every pending function and patch the router's
    endpoint slot so FastAPI uses the wrapped version.
    """
    limiter._real = real_limiter
    if not limiter._pending:
        return
    # Re-decorate every pending function. If the router has already been
    # registered with the app, patch its routes in place.
    patched = {}
    for args, kwargs, func in limiter._pending:
        wrapped = real_limiter.limit(*args, **kwargs)(func)
        patched[func] = wrapped
    limiter._pending.clear()
    # Patch the router's APIRoute.endpoint pointers so FastAPI dispatches
    # to the rate-limited version on the next request.
    try:
        for route in tunel_router.routes:
            ep = getattr(route, "endpoint", None)
            if ep in patched:
                route.endpoint = patched[ep]
                # FastAPI cached the dependant at add_api_route time. Rebuild it
                # so the new endpoint signature (which slowapi reads via
                # `request: Request`) is picked up.
                try:
                    from fastapi.dependencies.utils import get_dependant
                    route.dependant = get_dependant(path=route.path_format,
                                                    call=patched[ep])
                except Exception:
                    pass
    except NameError:
        # tunel_router not yet defined; decorators were registered first.
        pass

try:
    import tunel_detection
    DETECTION_AVAILABLE = True
except Exception as _e:
    DETECTION_AVAILABLE = False

try:
    from tunel_matching import find_matches_for_upload, initiate_reconnect_for_face
    MATCHING_AVAILABLE = True
except Exception:
    MATCHING_AVAILABLE = False

logger = logging.getLogger(__name__)


def _run_detection(upload: TunelUpload, db: Session) -> int:
    """Roda face detection num upload, persiste TunelFace rows e atualiza status.

    Retorna nº de faces detectadas. Isolado em função pra reuso entre POST /upload
    e POST /{upload_id}/process (re-trigger).
    """
    if not DETECTION_AVAILABLE:
        upload.processing_status = 'failed'
        db.commit()
        return 0
    try:
        result = tunel_detection.process_upload(upload.file_path)
        faces = result.get('faces', [])
        # Limpa faces antigas antes de re-inserir (caso seja re-trigger)
        db.query(TunelFace).filter(TunelFace.upload_id == upload.id).delete()
        for f in faces:
            face_row = TunelFace(
                upload_id=upload.id,
                face_index=f['face_index'],
                bbox_x=f['bbox_x'],
                bbox_y=f['bbox_y'],
                bbox_w=f['bbox_w'],
                bbox_h=f['bbox_h'],
                embedding=f.get('embedding'),
                embedding_model=f.get('embedding_model'),
                confidence=f.get('confidence'),
            )
            db.add(face_row)
        upload.faces_detected_count = len(faces)
        upload.processing_status = 'detected'
        db.commit()
        return len(faces)
    except Exception as e:
        logger.exception(f"Face detection falhou para upload {upload.id}: {e}")
        upload.processing_status = 'failed'
        db.commit()
        return 0

tunel_router = APIRouter(prefix="/api/tunel", tags=["tunel"])

ALLOWED_MIME = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
UPLOAD_DIR_BASE = "uploads/tunel"


@tunel_router.post("/upload")
@limiter.limit("5/day", key_func=_user_id_key)
async def upload_old_photo(
    request: Request,
    file: UploadFile = File(...),
    photo_year_estimated: Optional[int] = Form(None),
    photo_context: Optional[str] = Form(None),
    turma_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Upload de foto antiga pro Túnel do Tempo.

    Faz validação MIME + tamanho, scrubba EXIF (LGPD: GPS/câmera/timestamp são
    dados pessoais), e registra metadata pra face detection futura (Sprint 2 S2).
    Rate-limit: 5/dia/user (uploads são caros — face detection, storage).
    """
    request.state.user = current_user  # bind for slowapi key_func
    # LGPD Art. 14 + ECA: gate 18+ antes de qualquer trabalho. Fotos escolares
    # antigas costumam conter colegas menores; iniciar face matching nesse
    # contexto exige operador adulto.
    require_18_plus(current_user)
    # LGPD Art. 11: biometric consent must be granted SEPARATELY from ToS.
    # Uploads contain face biometrics (embeddings) — without consent, refuse.
    if not has_active_consent(db, current_user.id, 'tunel_biometric'):
        raise HTTPException(
            status_code=403,
            detail={
                'error': 'consent_required',
                'consent_type': 'tunel_biometric',
                'message': "Consentimento biométrico necessário (LGPD Art. 11). "
                           "Conceda em POST /api/me/consents/tunel_biometric/grant.",
            },
        )
    # Validação MIME
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Tipo não suportado. Use jpg, png ou webp.")

    # Validação tamanho
    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(400, "Foto muito grande. Máximo 10MB.")

    # Storage por user (facilita purge LGPD)
    user_dir = os.path.join(UPLOAD_DIR_BASE, str(current_user.id))
    os.makedirs(user_dir, exist_ok=True)
    ext = file.content_type.split('/')[-1].replace('jpeg', 'jpg')
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(user_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(contents)

    # EXIF scrub (importante pra privacy!)
    # Remove GPS, modelo da câmera, timestamp original — tudo pode identificar.
    exif_scrubbed = False
    try:
        from PIL import Image
        img = Image.open(file_path)
        # Salvar sem EXIF: recria a imagem com os mesmos pixels mas sem metadata
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        clean.save(file_path)
        exif_scrubbed = True
    except Exception as e:
        logger.warning(f"EXIF scrub falhou: {e}")

    # Salvar no DB
    upload = TunelUpload(
        user_id=current_user.id,
        turma_id=turma_id,
        file_path=file_path,
        file_size_bytes=len(contents),
        mime_type=file.content_type,
        original_filename=file.filename,
        photo_year_estimated=photo_year_estimated,
        photo_context=photo_context,
        exif_scrubbed=exif_scrubbed,
        processing_status='pending',
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    # Sprint 2 S2: face detection inline (síncrona — Haar Cascades é leve).
    # Se virar gargalo no Render free tier, migrar pra BackgroundTasks.
    faces_detected = _run_detection(upload, db)

    return {
        "success": True,
        "upload_id": upload.id,
        "preview_url": f"/uploads/tunel/{current_user.id}/{filename}",
        "file_size_kb": round(len(contents) / 1024, 1),
        "exif_scrubbed": exif_scrubbed,
        "faces_detected": faces_detected,
        "processing_status": upload.processing_status,
    }


@tunel_router.post("/{upload_id}/process")
@limiter.limit("3/day", key_func=_user_id_key)
async def reprocess_upload(
    upload_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Re-trigger face detection num upload existente.

    Rate limit: 3 reprocessamentos/dia/user (slowapi). Útil quando: melhoramos
    o modelo, ou primeira detecção retornou 0 faces e o user quer tentar de
    novo. O bloco DB-based abaixo serve de defense-in-depth se slowapi reset
    after restart.
    """
    request.state.user = current_user
    upload = db.query(TunelUpload).filter(
        TunelUpload.id == upload_id,
        TunelUpload.user_id == current_user.id,
        TunelUpload.deleted_at.is_(None),
    ).first()
    if not upload:
        raise HTTPException(404, "Upload não encontrado")

    # Rate limit: conta uploads do user processados nas últimas 24h.
    # Sem tabela extra — usa processing_status como proxy.
    since = datetime.utcnow() - timedelta(hours=24)
    recent_processed = db.query(func.count(TunelUpload.id)).filter(
        TunelUpload.user_id == current_user.id,
        TunelUpload.processing_status.in_(['detected', 'failed']),
        TunelUpload.created_at >= since,
    ).scalar() or 0
    if recent_processed >= 3 and upload.processing_status in ('detected', 'failed'):
        raise HTTPException(
            429,
            "Limite de 3 reprocessamentos por dia atingido. Tente amanhã."
        )

    faces_detected = _run_detection(upload, db)
    return {
        "success": True,
        "upload_id": upload.id,
        "faces_detected": faces_detected,
        "processing_status": upload.processing_status,
    }


@tunel_router.get("/{upload_id}/faces")
@limiter.limit("30/minute", key_func=_user_id_key)
async def list_faces(
    upload_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Lista faces detectadas no upload — SEM embedding bruto (dado biométrico).

    Retorna bbox + confidence + match info. Embeddings ficam server-side pro
    matching, nunca expostos ao cliente (LGPD: embedding facial é sensível).
    Rate-limit: 30/min/user (UI polling-friendly mas anti-scrape).
    """
    request.state.user = current_user
    upload = db.query(TunelUpload).filter(
        TunelUpload.id == upload_id,
        TunelUpload.user_id == current_user.id,
        TunelUpload.deleted_at.is_(None),
    ).first()
    if not upload:
        raise HTTPException(404, "Upload não encontrado")

    faces = db.query(TunelFace).filter(
        TunelFace.upload_id == upload_id
    ).order_by(TunelFace.face_index).all()

    return {
        "success": True,
        "upload_id": upload_id,
        "processing_status": upload.processing_status,
        "faces_count": len(faces),
        "faces": [
            {
                "id": f.id,
                "face_index": f.face_index,
                "bbox": {
                    "x": f.bbox_x,
                    "y": f.bbox_y,
                    "w": f.bbox_w,
                    "h": f.bbox_h,
                },
                "confidence": f.confidence,
                "matched_user_id": f.matched_user_id,
                "match_confidence": f.match_confidence,
                # embedding propositalmente omitido (LGPD — dado biométrico)
            }
            for f in faces
        ],
    }


@tunel_router.get("/uploads/me")
@limiter.limit("60/minute", key_func=_user_id_key)
async def list_my_uploads(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Lista uploads do próprio user (não-deletados).

    Rate-limit: 60/min/user (generoso — endpoint de leitura, mas evita scraping).
    """
    request.state.user = current_user
    uploads = db.query(TunelUpload).filter(
        TunelUpload.user_id == current_user.id,
        TunelUpload.deleted_at.is_(None),
    ).order_by(TunelUpload.created_at.desc()).all()
    return {
        "success": True,
        "uploads": [
            {
                "id": u.id,
                "preview_url": f"/{u.file_path}",
                "photo_year": u.photo_year_estimated,
                "photo_context": u.photo_context,
                "faces_detected": u.faces_detected_count,
                "status": u.processing_status,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in uploads
        ],
    }


@tunel_router.delete("/upload/{upload_id}")
async def delete_upload(
    upload_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """LGPD Art. 18: usuário pode apagar a qualquer momento.

    Soft-delete no DB (mantém audit trail) + apaga arquivo físico + apaga
    faces detectadas (embeddings são dado biométrico sensível).
    """
    upload = db.query(TunelUpload).filter(
        TunelUpload.id == upload_id,
        TunelUpload.user_id == current_user.id,
    ).first()
    if not upload:
        raise HTTPException(404, "Upload não encontrado")
    # Soft delete + apaga arquivo físico
    upload.deleted_at = datetime.utcnow()
    try:
        os.remove(upload.file_path)
    except Exception:
        pass
    # Apaga faces associadas (embeddings biométricos)
    db.query(TunelFace).filter(TunelFace.upload_id == upload_id).delete()
    db.commit()
    return {"success": True, "deleted": True}


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 2 S3 — Matching Engine endpoints
# Privacy: nunca expõe nome/foto do candidato. Apenas similarity + bbox + face_id.
# Reveal de identidade só via /api/reconnect (double opt-in assimétrico).
# Rate limit: 10 matches/dia/user (enforced em tunel_matching).
# ═══════════════════════════════════════════════════════════════════════════════

@tunel_router.get("/{upload_id}/matches")
@limiter.limit("10/day", key_func=_user_id_key)
async def get_matches_for_upload(
    upload_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Roda matching pra todas faces detectadas no upload do user.

    Só o dono do upload pode pedir matches. Resposta NÃO contém nome ou foto
    dos candidatos — só similarity, bbox e face_id (handle pro reconnect).
    Rate-limit: 10/dia/user — matching é caro (embedding compare contra base
    inteira) e cada chamada toca dados biométricos de terceiros.
    """
    request.state.user = current_user
    # LGPD Art. 11: face matching compares embeddings against OTHER users —
    # distinct from just uploading your own photo. Requires its own consent.
    if not has_active_consent(db, current_user.id, 'face_matching'):
        raise HTTPException(
            status_code=403,
            detail={
                'error': 'consent_required',
                'consent_type': 'face_matching',
                'message': "Consentimento de matching facial necessário (LGPD Art. 11). "
                           "Conceda em POST /api/me/consents/face_matching/grant.",
            },
        )
    result = find_matches_for_upload(db, upload_id, current_user.id)
    if 'error' in result:
        if result['error'] == 'upload not found':
            raise HTTPException(404, "Upload não encontrado")
        if result['error'] == 'not owner':
            raise HTTPException(403, "Você só pode buscar matches em fotos suas")
        raise HTTPException(400, result['error'])
    return {"success": True, **result}


@tunel_router.post("/match/{face_id}/reconnect")
@limiter.limit("5/day", key_func=_user_id_key)
async def reconnect_via_match(
    face_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Inicia reveal assimétrico contra o dono da face matched.

    Não revela identidade aqui: apenas retorna target_user_id pra ser passado
    pro /api/reconnect (que implementa double opt-in). Se o owner está em
    ghost_mode_global, devolve 404 (não vaza existência).
    Rate-limit: 5/dia/user — espelho do limite em /api/reconnect (mesmo orçamento
    diário, não importa o caminho usado pra iniciar o reveal).
    """
    request.state.user = current_user
    return initiate_reconnect_for_face(db, face_id, current_user.id)


# ═════════════════════════════════════════════════════════════════════════════
# ICE-BREAKER (template fallback, LLM-ready)
# ═════════════════════════════════════════════════════════════════════════════
#
# UX flow:
#   1. User clica "Reconectar" no perfil/foto do target.
#   2. Frontend chama GET /api/tunel/icebreaker/{target_user_id} → recebe 3
#      sugestões + context_summary.
#   3. User escolhe uma, edita o texto, e então POSTa em /api/reconnect/{id}
#      com a mensagem final no campo `ice_breaker`.
#
# Rate limit: 20/dia/user. Bucket simples em memória (resetado no boot).
# Quando ANTHROPIC_API_KEY existir, generate_icebreaker passa a chamar Claude
# e o método retorna 'llm_claude' em vez de 'template_v1' — frontend não muda.

from collections import defaultdict
from threading import Lock

_ICEBREAKER_DAILY_LIMIT = 20
_icebreaker_counters: dict = defaultdict(lambda: {'day': None, 'count': 0})
_icebreaker_lock = Lock()


def _check_icebreaker_quota(user_id: int):
    """Retorna (allowed: bool, remaining: int). Reset diário em UTC midnight."""
    today = datetime.utcnow().date().isoformat()
    with _icebreaker_lock:
        bucket = _icebreaker_counters[user_id]
        if bucket['day'] != today:
            bucket['day'] = today
            bucket['count'] = 0
        if bucket['count'] >= _ICEBREAKER_DAILY_LIMIT:
            return False, 0
        bucket['count'] += 1
        return True, _ICEBREAKER_DAILY_LIMIT - bucket['count']


@tunel_router.get("/icebreaker/{target_user_id}")
@limiter.limit("20/day", key_func=_user_id_key)
def get_icebreaker_suggestions(
    target_user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Retorna 3 sugestões de ice-breaker pra reconexão.

    Quota: 20/dia por usuário (anti-abuse, suficiente pra explorar). Quando
    estourada, retorna 429 com `retry_after_hours` pro frontend mostrar.

    Não revela se o target existe — a checagem dura acontece em /api/reconnect
    (asymmetric reveal). Aqui só geramos copy baseada em Turmas verificadas em
    comum, que o requester já teria ao acessar a página da Turma de qualquer
    forma. Sem dado biométrico nem foto exposta neste endpoint.
    """
    request.state.user = current_user
    if target_user_id == current_user.id:
        raise HTTPException(400, "Não dá pra se reconectar com você mesmo.")

    allowed, remaining = _check_icebreaker_quota(current_user.id)
    if not allowed:
        raise HTTPException(
            429,
            detail={
                "error": "Você atingiu o limite diário de sugestões. Tenta amanhã.",
                "retry_after_hours": 24,
                "daily_limit": _ICEBREAKER_DAILY_LIMIT,
            },
        )

    result = generate_icebreaker(db, current_user.id, target_user_id)
    result['quota_remaining'] = remaining
    return result
