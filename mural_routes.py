"""Mural da Saudade da Turma — memorias sensoriais coletivas.
Cada user sobe UMA memoria por turma (nao conquista, nao curriculum).
Sistema cose memorias por tags afetivas."""

import json
import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import FileResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db, MuralMemory, Turma, TurmaMembership, User
from auth import get_current_user_required, SECRET_KEY, ALGORITHM

from rate_limit_db import check_rate_limit

mural_router = APIRouter(prefix="/api", tags=["mural"])


# ─── Security helpers ────────────────────────────────────────────────────────
def require_verified_member(db: Session, user_id: int, turma_id: int) -> TurmaMembership:
    """LGPD/Trust&Safety guard: only verified members of a turma may read or
    write its sensitive surfaces (mural, in-memoriam, cadê, audio, search).

    Raises 403 with a clear PT-BR message otherwise. Returns the membership
    row so callers can use the apelido/role downstream without a re-query.
    """
    m = db.query(TurmaMembership).filter(
        TurmaMembership.user_id == user_id,
        TurmaMembership.turma_id == turma_id,
        TurmaMembership.status == 'verified',
    ).first()
    if not m:
        raise HTTPException(403, "Você precisa ser membro verificado dessa turma")
    return m


# ─── Signed audio URLs ───────────────────────────────────────────────────────
# Direct /uploads/mural_audio/<user_id>/<file> paths are biometric voice data
# (LGPD Art. 5º II) and must NOT be guessable nor servable without an active
# session + turma membership. We mint short-lived JWT tokens scoped to a
# specific (user, filename) pair; the streaming endpoint re-validates the
# requesting user's membership at fetch time.

AUDIO_TOKEN_TTL_SECONDS = 60 * 60  # 1 hour
AUDIO_TOKEN_AUD = "mural_audio"


def _audio_relative_path(audio_url: str) -> Optional[str]:
    """Strip a stored audio_url ('/uploads/mural_audio/123/abc.webm') down to
    the user_id/filename pair the signer/server uses. Returns None if the
    URL is not a mural_audio path (already external, malformed, etc.)."""
    if not audio_url:
        return None
    marker = "uploads/mural_audio/"
    idx = audio_url.find(marker)
    if idx < 0:
        return None
    return audio_url[idx + len(marker):]  # "<user_id>/<filename>"


def signed_audio_url(user_id: int, filename: str, ttl_seconds: int = AUDIO_TOKEN_TTL_SECONDS) -> str:
    """Return a short-lived signed URL for an audio file. `filename` may be
    the bare filename or "<owner_id>/<filename>" (as stored in audio_url).
    The token carries owner+filename so the server can locate the file and
    re-check the caller's membership at fetch time."""
    if "/" in filename:
        owner_id_str, fname = filename.split("/", 1)
        try:
            owner_id = int(owner_id_str)
        except ValueError:
            owner_id = user_id
    else:
        owner_id, fname = user_id, filename
    payload = {
        "aud": AUDIO_TOKEN_AUD,
        "owner_id": owner_id,
        "filename": fname,
        "exp": datetime.utcnow() + timedelta(seconds=ttl_seconds),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return f"/api/mural/audio/{token}"


def _signed_audio_url_for_memory(memory: "MuralMemory") -> Optional[str]:
    """Convenience: take a MuralMemory row and produce a signed URL for its
    audio (if any). Returns None when the memory has no audio."""
    rel = _audio_relative_path(memory.audio_url)
    if not rel:
        return None
    return signed_audio_url(memory.user_id, rel)

MEMORY_TYPES = ['smell', 'sound', 'place', 'person', 'event', 'taste', 'gesture']

# ─── Audio config ─────────────────────────────────────────────────────────────
AUDIO_DIR = "uploads/mural_audio"
AUDIO_MIME_ALLOWED = {
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave', 'audio/x-wav',
    'audio/webm', 'audio/ogg', 'audio/mp4',
}
AUDIO_MAX_BYTES = 5 * 1024 * 1024  # ~60s
os.makedirs(AUDIO_DIR, exist_ok=True)


def _ext_for_mime(mime: str) -> str:
    """Map an audio MIME to a sane file extension."""
    if not mime:
        return 'bin'
    base = mime.split(';')[0].strip().lower()
    mapping = {
        'audio/mpeg': 'mp3', 'audio/mp3': 'mp3',
        'audio/wav': 'wav', 'audio/wave': 'wav', 'audio/x-wav': 'wav',
        'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'm4a',
    }
    return mapping.get(base, base.split('/')[-1] or 'bin')


async def _save_audio_for_user(user_id: int, audio: UploadFile) -> str:
    """Validate + persist an audio upload. Returns the /uploads/... URL."""
    mime = (audio.content_type or '').split(';')[0].strip().lower()
    if mime not in AUDIO_MIME_ALLOWED:
        raise HTTPException(400, "Formato de áudio não suportado. Tenta MP3, WAV ou WebM.")
    contents = await audio.read()
    if len(contents) > AUDIO_MAX_BYTES:
        raise HTTPException(400, "Áudio muito longo. Máximo 60s (~5MB).")
    if len(contents) == 0:
        raise HTTPException(400, "Áudio vazio.")
    user_dir = os.path.join(AUDIO_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{_ext_for_mime(mime)}"
    file_path = os.path.join(user_dir, filename).replace("\\", "/")
    with open(file_path, 'wb') as f:
        f.write(contents)
    return f"/{file_path}", len(contents)

# ===== ADD MEMORY =====
@mural_router.post("/turmas/{turma_slug}/mural")
async def add_memory(
    turma_slug: str,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """User adds ONE sensory memory to a turma's mural.

    Accepts EITHER application/json OR multipart/form-data. When sent as
    multipart, an optional `audio` file field is persisted and attached to
    the new memory in the same request (one round-trip from the form).
    """
    # ── DB-backed rate limit (BUG H4): 30 memories/day/user. Mural creation
    # is the spammable surface — content shows up in every turma feed — so
    # the limit must be enforced across all workers, not per-process.
    check_rate_limit(
        db,
        key=f"user:{current_user.id}:mural",
        max_per_window=30,
        window_seconds=86400,
    )

    # Parse body — multipart (with optional audio) OR JSON.
    content_type_hdr = (request.headers.get('content-type') or '').lower()
    audio_upload: Optional[UploadFile] = None
    if 'multipart/form-data' in content_type_hdr:
        form = await request.form()
        memory_type = (form.get('memory_type') or form.get('type') or 'event')
        content = (form.get('content') or form.get('text') or '').strip()
        raw_tags = form.get('tags') or '[]'
        try:
            tags = json.loads(raw_tags) if isinstance(raw_tags, str) and raw_tags.startswith('[') else \
                [t.strip() for t in str(raw_tags).split(',') if t.strip()]
        except Exception:
            tags = []
        in_memoriam = str(form.get('in_memoriam') or form.get('is_memoriam') or '').lower() in ('1', 'true', 'on', 'yes')
        maybe_audio = form.get('audio')
        if isinstance(maybe_audio, UploadFile):
            audio_upload = maybe_audio
    else:
        body = await request.json()
        # Accept both backend-native ('memory_type', 'content', 'in_memoriam')
        # and frontend-legacy ('type', 'text', 'is_memoriam') field names.
        memory_type = body.get('memory_type') or body.get('type') or 'event'
        content = (body.get('content') or body.get('text') or '').strip()
        tags = body.get('tags', [])
        in_memoriam = body.get('in_memoriam', body.get('is_memoriam', False))

    if not content:
        raise HTTPException(400, "Conta a memória, vai!")
    if len(content) > 500:
        raise HTTPException(400, "Tenta encurtar a memória pra caber em uma respirada (max 500 chars).")
    if memory_type not in MEMORY_TYPES:
        raise HTTPException(400, f"Tipo deve ser um de: {MEMORY_TYPES}")

    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Essa turma não existe ainda.")

    # User precisa ser membro da turma (verified)
    membership = db.query(TurmaMembership).filter(
        TurmaMembership.turma_id == turma.id,
        TurmaMembership.user_id == current_user.id,
        TurmaMembership.status == 'verified',
    ).first()
    if not membership:
        raise HTTPException(403, "Você precisa estar na turma pra subir uma memória.")

    memory = MuralMemory(
        turma_id=turma.id,
        user_id=current_user.id,
        memory_type=memory_type,
        content=content,
        tags=tags if isinstance(tags, list) else [],
        in_memoriam=bool(in_memoriam),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    # Optional audio: same-request attach (frontend can post the form once).
    audio_url = None
    if audio_upload is not None:
        try:
            audio_url, _ = await _save_audio_for_user(current_user.id, audio_upload)
            memory.audio_url = audio_url
            db.commit()
        except HTTPException:
            # Memory is already saved — bubble up so client can retry just
            # the audio via the /audio endpoint without losing the text.
            raise

    return {
        "success": True,
        "memory_id": memory.id,
        "id": memory.id,  # frontend optimistic-prepend reads .id
        "memory_type": memory.memory_type,
        "content": memory.content,
        "tags": memory.tags or [],
        "in_memoriam": memory.in_memoriam,
        "has_audio": bool(memory.audio_url),
        "audio_url": _signed_audio_url_for_memory(memory),
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "message": "Memória subiu pro mural. Saudade compartilhada.",
    }


# ===== UPLOAD AUDIO TO EXISTING MEMORY =====
@mural_router.post("/turmas/{turma_slug}/mural/{memory_id}/audio")
async def upload_memory_audio(
    turma_slug: str,
    memory_id: int,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Upload audio (até 60s) pra uma memória existente.

    Sem voz, o Mural é Twitter clone. Com voz, vira WhatsApp grupo de turma
    em câmera lenta — que é como saudade soa.
    """
    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    memory = db.query(MuralMemory).filter(MuralMemory.id == memory_id).first()
    if not memory:
        raise HTTPException(404, "Memória não encontrada.")
    if memory.turma_id != turma.id:
        raise HTTPException(404, "Memória não pertence a essa turma.")
    if memory.user_id != current_user.id:
        raise HTTPException(403, "Você só pode adicionar áudio às suas memórias.")

    audio_url, size_bytes = await _save_audio_for_user(current_user.id, audio)
    memory.audio_url = audio_url
    db.commit()

    return {
        "success": True,
        "audio_url": _signed_audio_url_for_memory(memory),
        # Rough estimate: ~16KB/s for typical WebM/Opus voice; good enough
        # for the UI to show "~Xs" without decoding the file server-side.
        "duration_estimate_seconds": size_bytes // (16 * 1024),
    }


# ===== AUDIO REPLY TO ANOTHER USER'S MEMORY ("Eu também lembro → áudio") =====
@mural_router.post("/mural/{memory_id}/echo/audio")
async def echo_with_audio(
    memory_id: int,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """After 'Eu também lembro', user can attach a voice reply.

    Creates a fresh MuralMemory in the same turma carrying the audio + an
    echo tag pointing at the original. Keeps the original untouched
    (only the original author can edit it).
    """
    original = db.query(MuralMemory).filter(MuralMemory.id == memory_id).first()
    if not original:
        raise HTTPException(404, "Memória não encontrada.")

    # ── BUG: verified membership required to attach voice to a turma ──────
    require_verified_member(db, current_user.id, original.turma_id)

    # Reuse the user's audio storage + validation rules.
    audio_url, size_bytes = await _save_audio_for_user(current_user.id, audio)

    reply = MuralMemory(
        turma_id=original.turma_id,
        user_id=current_user.id,
        memory_type=original.memory_type,
        content=f"(áudio em resposta) {original.content[:200]}",
        tags=(original.tags or []) + ['echo_audio_of:' + str(memory_id)],
        in_memoriam=original.in_memoriam,
        audio_url=audio_url,
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)

    return {
        "success": True,
        "reply_memory_id": reply.id,
        "audio_url": _signed_audio_url_for_memory(reply),
        "duration_estimate_seconds": size_bytes // (16 * 1024),
        "message": "Tua voz tá no mural agora.",
    }

# ===== LIST MURAL =====
@mural_router.get("/turmas/{turma_slug}/mural")
async def list_memories(
    turma_slug: str,
    memory_type: Optional[str] = None,
    in_memoriam: Optional[bool] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Lista memorias do mural de uma turma. Apenas membros verified — o
    mural contém voz (dado biométrico, LGPD) e memórias afetivas íntimas."""
    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    # ── BUG: Trust&Safety / LGPD — auth + membership obrigatórios ─────────
    require_verified_member(db, current_user.id, turma.id)

    q = db.query(MuralMemory).filter(MuralMemory.turma_id == turma.id)
    if memory_type:
        q = q.filter(MuralMemory.memory_type == memory_type)
    if in_memoriam is not None:
        q = q.filter(MuralMemory.in_memoriam == in_memoriam)

    memories = q.order_by(MuralMemory.created_at.desc()).limit(100).all()

    # Group by tags pra surface "outros lembram disso tambem"
    tag_counts = {}
    for m in memories:
        for tag in (m.tags or []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "success": True,
        "turma": {
            "slug": turma.slug,
            "institution_name": turma.institution_name,
            "cohort_year": turma.cohort_year,
        },
        "memories_count": len(memories),
        "memories": [
            {
                "id": m.id,
                "memory_type": m.memory_type,
                "content": m.content,
                "tags": m.tags or [],
                "in_memoriam": m.in_memoriam,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "has_audio": bool(m.audio_url),
                # Never leak raw /uploads/... paths — biometric voice data.
                # Mint a 1h signed token; client refetches when it expires.
                "audio_url": _signed_audio_url_for_memory(m),
            }
            for m in memories
        ],
        "top_tags": sorted(tag_counts.items(), key=lambda x: -x[1])[:10],
    }

# ===== ECHO (eu tambem lembro) =====
@mural_router.post("/mural/{memory_id}/echo")
async def echo_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """User toca 'eu tambem lembro' numa memoria de outro user.
    Cria uma 'echo' memoria com mesmo conteudo + tag de echo."""
    original = db.query(MuralMemory).filter(MuralMemory.id == memory_id).first()
    if not original:
        raise HTTPException(404, "Memória não encontrada.")

    # ── BUG: must be verified member of the *original's* turma ────────────
    require_verified_member(db, current_user.id, original.turma_id)

    # Verifica se ja deu echo
    existing = db.query(MuralMemory).filter(
        MuralMemory.turma_id == original.turma_id,
        MuralMemory.user_id == current_user.id,
        MuralMemory.content == original.content,
    ).first()
    if existing:
        return {"success": True, "already_echoed": True}

    echo = MuralMemory(
        turma_id=original.turma_id,
        user_id=current_user.id,
        memory_type=original.memory_type,
        content=original.content,
        tags=(original.tags or []) + ['echo_of:' + str(memory_id)],
        in_memoriam=original.in_memoriam,
    )
    db.add(echo)
    db.commit()
    return {
        "success": True,
        "message": "Você também lembra. Que bom.",
        "suggest_voice_note": True,  # tag pra UI sugerir gravar audio
    }

# ===== CADE? — turma procura sumidos =====
@mural_router.post("/turmas/{turma_slug}/cade")
async def report_missing(
    turma_slug: str,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """User diz: 'cade o Fulano?' — turma colabora procurando."""
    body = await request.json()
    nome = (body.get('nome') or '').strip()
    ultima_lembranca = (body.get('ultima_lembranca') or '').strip()

    if not nome:
        raise HTTPException(400, "Quem você está procurando?")

    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    # ── BUG: a non-member could enumerate apelidos via "cadê" matches ─────
    require_verified_member(db, current_user.id, turma.id)

    # Apelido lookup — brasileiros perguntam "Cadê o Cabeção?", não "Cadê o
    # João Carlos da Silva?". Se o apelido bate em algum membro verified da
    # turma, linka o report direto ao perfil dele.
    from sqlalchemy import func
    matched_membership_id = None
    matched_user_id = None
    matched_apelido = None
    if nome:
        m = db.query(TurmaMembership).filter(
            TurmaMembership.turma_id == turma.id,
            TurmaMembership.status == 'verified',
            func.lower(TurmaMembership.apelido).contains(nome.lower()),
        ).first()
        if m:
            matched_membership_id = m.id
            matched_user_id = m.user_id
            matched_apelido = m.apelido

    tags = ['cade', f'pessoa:{nome.lower()}']
    if matched_membership_id:
        tags.append(f'membership:{matched_membership_id}')
        tags.append(f'apelido:{(matched_apelido or "").lower()}')

    # Cria uma "memoria" especial tipo 'cade'
    memory = MuralMemory(
        turma_id=turma.id,
        user_id=current_user.id,
        memory_type='cade',
        content=f"Cadê o(a) {nome}? — Última lembrança: {ultima_lembranca or '(em branco)'}",
        tags=tags,
        in_memoriam=False,
    )
    db.add(memory)
    db.commit()

    return {
        "success": True,
        "message": f"A turma toda agora tá procurando {nome}. Vamos achar.",
        "memory_id": memory.id,
        "matched_by_apelido": matched_membership_id is not None,
        "matched_membership_id": matched_membership_id,
        "matched_user_id": matched_user_id,
        "matched_apelido": matched_apelido,
    }

# ===== IN MEMORIAM SECTION =====
@mural_router.get("/turmas/{turma_slug}/mural/in-memoriam")
async def list_in_memoriam(
    turma_slug: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Section sagrada: memorias de quem partiu. Acesso restrito a membros
    verified — dado de luto não pode vazar pra estranhos (LGPD + dignidade)."""
    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    # ── BUG: grief data leak — auth + membership obrigatórios ─────────────
    require_verified_member(db, current_user.id, turma.id)

    memories = db.query(MuralMemory).filter(
        MuralMemory.turma_id == turma.id,
        MuralMemory.in_memoriam == True,
    ).order_by(MuralMemory.created_at.desc()).all()

    return {
        "success": True,
        "section": "in_memoriam",
        "message": "Quem partiu mas continua na memória da turma.",
        "memories": [
            {
                "id": m.id,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ],
    }


# ===== SIGNED AUDIO STREAM =====
@mural_router.get("/mural/audio/{token}")
async def stream_audio(
    token: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Resolve a signed audio token + stream the file. Re-checks that the
    requester is still a verified member of the memory's turma at fetch
    time — revoking access the moment someone leaves the turma."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=AUDIO_TOKEN_AUD,
        )
    except JWTError:
        raise HTTPException(403, "Link de áudio expirou ou é inválido.")

    owner_id = payload.get("owner_id")
    filename = payload.get("filename")
    if not owner_id or not filename or "/" in filename or filename.startswith("."):
        raise HTTPException(400, "Token de áudio malformado.")

    # Locate the memory that owns this audio so we can verify the listener
    # belongs to that memory's turma RIGHT NOW (not just at mint time).
    expected_url_fragment = f"uploads/mural_audio/{owner_id}/{filename}"
    memory = db.query(MuralMemory).filter(
        MuralMemory.audio_url.like(f"%{expected_url_fragment}")
    ).first()
    if not memory:
        raise HTTPException(404, "Áudio não encontrado.")

    require_verified_member(db, current_user.id, memory.turma_id)

    file_path = os.path.join(AUDIO_DIR, str(owner_id), filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "Arquivo de áudio sumiu do disco.")

    return FileResponse(file_path)
