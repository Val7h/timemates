"""Mural da Saudade da Turma — memorias sensoriais coletivas.
Cada user sobe UMA memoria por turma (nao conquista, nao curriculum).
Sistema cose memorias por tags afetivas."""

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db, MuralMemory, Turma, TurmaMembership, User
from auth import get_current_user_required
from rate_limit_db import check_rate_limit

mural_router = APIRouter(prefix="/api", tags=["mural"])

MEMORY_TYPES = ['smell', 'sound', 'place', 'person', 'event', 'taste', 'gesture']

# ===== ADD MEMORY =====
@mural_router.post("/turmas/{turma_slug}/mural")
async def add_memory(
    turma_slug: str,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """User adds ONE sensory memory to a turma's mural."""
    # ── DB-backed rate limit (BUG H4): 30 memories/day/user. Mural creation
    # is the spammable surface — content shows up in every turma feed — so
    # the limit must be enforced across all workers, not per-process.
    check_rate_limit(
        db,
        key=f"user:{current_user.id}:mural",
        max_per_window=30,
        window_seconds=86400,
    )
    body = await request.json()
    memory_type = body.get('memory_type', 'event')
    content = body.get('content', '').strip()
    tags = body.get('tags', [])
    in_memoriam = body.get('in_memoriam', False)

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

    return {
        "success": True,
        "memory_id": memory.id,
        "message": "Memória subiu pro mural. Saudade compartilhada.",
    }

# ===== LIST MURAL =====
@mural_router.get("/turmas/{turma_slug}/mural")
async def list_memories(
    turma_slug: str,
    memory_type: Optional[str] = None,
    in_memoriam: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """Lista memorias do mural de uma turma."""
    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

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

    # Cria uma "memoria" especial tipo 'cade'
    memory = MuralMemory(
        turma_id=turma.id,
        user_id=current_user.id,
        memory_type='cade',
        content=f"Cadê o(a) {nome}? — Última lembrança: {ultima_lembranca or '(em branco)'}",
        tags=['cade', f'pessoa:{nome.lower()}'],
        in_memoriam=False,
    )
    db.add(memory)
    db.commit()

    return {
        "success": True,
        "message": f"A turma toda agora tá procurando {nome}. Vamos achar.",
        "memory_id": memory.id,
    }

# ===== IN MEMORIAM SECTION =====
@mural_router.get("/turmas/{turma_slug}/mural/in-memoriam")
async def list_in_memoriam(
    turma_slug: str,
    db: Session = Depends(get_db),
):
    """Section sagrada: memorias de quem partiu."""
    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

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
