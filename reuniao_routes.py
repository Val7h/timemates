from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db, Turma, TurmaMembership, TurmaReuniao, TurmaReuniaoVote, TurmaReuniaoRSVP, ReuniaoPhoto, User
from auth import get_current_user_required

reuniao_router = APIRouter(prefix="/api", tags=["reuniao"])

# ===== CREATE REUNIÃO =====
@reuniao_router.post("/turmas/{turma_slug}/reuniao")
async def create_reuniao(
    turma_slug: str,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    body = await request.json()
    title = body.get('title', '').strip()
    description = body.get('description', '').strip()
    proposed_dates = body.get('proposed_dates', [])
    suggested_venue = body.get('suggested_venue')
    venue_city = body.get('venue_city')

    if not title:
        raise HTTPException(400, "Dá um nome pra esse encontro!")
    if not proposed_dates or len(proposed_dates) < 1:
        raise HTTPException(400, "Sugere pelo menos 1 data possível.")
    if len(proposed_dates) > 6:
        raise HTTPException(400, "Tenta limitar a 6 datas pra galera não enlouquecer.")

    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    membership = db.query(TurmaMembership).filter(
        TurmaMembership.turma_id == turma.id,
        TurmaMembership.user_id == current_user.id,
        TurmaMembership.status == 'verified',
    ).first()
    if not membership:
        raise HTTPException(403, "Você precisa estar na turma pra propor um encontro.")

    reuniao = TurmaReuniao(
        turma_id=turma.id,
        organizer_id=current_user.id,
        title=title,
        description=description,
        proposed_dates=proposed_dates,
        suggested_venue=suggested_venue,
        venue_city=venue_city,
        status='collecting_votes',
    )
    db.add(reuniao)
    db.commit()
    db.refresh(reuniao)

    return {
        "success": True,
        "reuniao_id": reuniao.id,
        "message": "Reunião criada! Bora chamar a galera.",
        "shareable_url": f"/reuniao/{reuniao.id}",
    }

# ===== LIST REUNIÕES DE UMA TURMA =====
@reuniao_router.get("/turmas/{turma_slug}/reunioes")
async def list_reunioes(
    turma_slug: str,
    db: Session = Depends(get_db),
):
    turma = db.query(Turma).filter(Turma.slug == turma_slug).first()
    if not turma:
        raise HTTPException(404, "Turma não encontrada.")

    reunioes = db.query(TurmaReuniao).filter(
        TurmaReuniao.turma_id == turma.id,
    ).order_by(TurmaReuniao.created_at.desc()).all()

    result = []
    for r in reunioes:
        votes_count = db.query(TurmaReuniaoVote).filter(TurmaReuniaoVote.reuniao_id == r.id).count()
        rsvps_count = db.query(TurmaReuniaoRSVP).filter(
            TurmaReuniaoRSVP.reuniao_id == r.id,
            TurmaReuniaoRSVP.status == 'confirmed',
        ).count()
        result.append({
            "id": r.id,
            "title": r.title,
            "status": r.status,
            "final_date": r.final_date.isoformat() if r.final_date else None,
            "proposed_dates": r.proposed_dates,
            "suggested_venue": r.suggested_venue,
            "votes_count": votes_count,
            "rsvps_count": rsvps_count,
        })
    return {"success": True, "reunioes": result}

# ===== VOTE NA DATA =====
@reuniao_router.post("/reuniao/{reuniao_id}/vote")
async def vote_date(
    reuniao_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    body = await request.json()
    date_voted = body.get('date')
    available = body.get('available', True)

    if not date_voted:
        raise HTTPException(400, "Qual data?")

    reuniao = db.query(TurmaReuniao).filter(TurmaReuniao.id == reuniao_id).first()
    if not reuniao:
        raise HTTPException(404, "Reunião não encontrada.")
    if date_voted not in (reuniao.proposed_dates or []):
        raise HTTPException(400, "Essa data não foi proposta.")

    # Upsert vote
    existing = db.query(TurmaReuniaoVote).filter(
        TurmaReuniaoVote.reuniao_id == reuniao_id,
        TurmaReuniaoVote.user_id == current_user.id,
        TurmaReuniaoVote.date_voted == date_voted,
    ).first()
    if existing:
        existing.available = available
    else:
        v = TurmaReuniaoVote(
            reuniao_id=reuniao_id,
            user_id=current_user.id,
            date_voted=date_voted,
            available=available,
        )
        db.add(v)
    db.commit()
    return {"success": True, "vote_registered": True}

# ===== CONFIRM FINAL DATE =====
@reuniao_router.post("/reuniao/{reuniao_id}/confirm")
async def confirm_date(
    reuniao_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    body = await request.json()
    final_date = body.get('final_date')

    reuniao = db.query(TurmaReuniao).filter(TurmaReuniao.id == reuniao_id).first()
    if not reuniao:
        raise HTTPException(404, "Reunião não encontrada.")
    if reuniao.organizer_id != current_user.id:
        raise HTTPException(403, "Só o organizador pode confirmar a data.")

    try:
        reuniao.final_date = datetime.fromisoformat(final_date)
    except Exception:
        raise HTTPException(400, "Formato de data inválido.")
    reuniao.status = 'confirmed'
    db.commit()
    return {"success": True, "message": "Confirmado! Vai ser bom demais."}

# ===== RSVP =====
@reuniao_router.post("/reuniao/{reuniao_id}/rsvp")
async def rsvp(
    reuniao_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    body = await request.json()
    status = body.get('status', 'confirmed')  # confirmed/maybe/no
    plus_ones = body.get('plus_ones', 0)

    if status not in ['confirmed', 'maybe', 'no']:
        raise HTTPException(400, "Status inválido.")

    existing = db.query(TurmaReuniaoRSVP).filter(
        TurmaReuniaoRSVP.reuniao_id == reuniao_id,
        TurmaReuniaoRSVP.user_id == current_user.id,
    ).first()
    if existing:
        existing.status = status
        existing.plus_ones = plus_ones
    else:
        r = TurmaReuniaoRSVP(
            reuniao_id=reuniao_id,
            user_id=current_user.id,
            status=status,
            plus_ones=plus_ones,
        )
        db.add(r)
    db.commit()

    msg = {
        'confirmed': 'Bora! Já tá anotado.',
        'maybe': 'Vê aí, te esperamos.',
        'no': 'Da próxima a gente se vê.',
    }[status]
    return {"success": True, "message": msg}

# ===== GET REUNIÃO DETAIL =====
@reuniao_router.get("/reuniao/{reuniao_id}")
async def get_reuniao(
    reuniao_id: int,
    db: Session = Depends(get_db),
):
    reuniao = db.query(TurmaReuniao).filter(TurmaReuniao.id == reuniao_id).first()
    if not reuniao:
        raise HTTPException(404, "Reunião não encontrada.")

    # Vote tally per date
    date_votes = {}
    for d in (reuniao.proposed_dates or []):
        votes = db.query(TurmaReuniaoVote).filter(
            TurmaReuniaoVote.reuniao_id == reuniao_id,
            TurmaReuniaoVote.date_voted == d,
            TurmaReuniaoVote.available == True,
        ).count()
        date_votes[d] = votes

    rsvps = db.query(TurmaReuniaoRSVP).filter(TurmaReuniaoRSVP.reuniao_id == reuniao_id).all()

    return {
        "success": True,
        "id": reuniao.id,
        "title": reuniao.title,
        "description": reuniao.description,
        "status": reuniao.status,
        "final_date": reuniao.final_date.isoformat() if reuniao.final_date else None,
        "suggested_venue": reuniao.suggested_venue,
        "venue_city": reuniao.venue_city,
        "date_votes": date_votes,
        "rsvps_summary": {
            "confirmed": sum(1 for r in rsvps if r.status == 'confirmed'),
            "maybe": sum(1 for r in rsvps if r.status == 'maybe'),
            "no": sum(1 for r in rsvps if r.status == 'no'),
            "plus_ones_total": sum(r.plus_ones for r in rsvps if r.status == 'confirmed'),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PHOTO LOOP — Flywheel Closer
# Reuniao acontece → quem confirmou RSVP sobe fotos → turma membros relembram
# → bate saudade → marca próxima reunião. O loop social que fecha o ciclo.
# ═══════════════════════════════════════════════════════════════════════════════

@reuniao_router.post("/reuniao/{reuniao_id}/photos")
async def upload_reuniao_photo(
    reuniao_id: int,
    photo: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Upload foto pós-encontro. Auth + RSVP=confirmed required."""
    reuniao = db.query(TurmaReuniao).filter(TurmaReuniao.id == reuniao_id).first()
    if not reuniao:
        raise HTTPException(404, "Reunião não encontrada")

    # Must have RSVP'd confirmed
    rsvp = db.query(TurmaReuniaoRSVP).filter(
        TurmaReuniaoRSVP.reuniao_id == reuniao_id,
        TurmaReuniaoRSVP.user_id == current_user.id,
        TurmaReuniaoRSVP.status == 'confirmed',
    ).first()
    if not rsvp:
        raise HTTPException(403, "Só quem confirmou presença pode subir fotos")

    # Validate
    ALLOWED = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
    if photo.content_type not in ALLOWED:
        raise HTTPException(400, "Foto deve ser jpg/png/webp")
    contents = await photo.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "Foto muito grande (max 10MB)")

    # Storage with EXIF scrub
    import os, uuid
    user_dir = f"uploads/reuniao_photos/{reuniao_id}"
    os.makedirs(user_dir, exist_ok=True)
    ext = photo.content_type.split('/')[-1].replace('jpeg', 'jpg')
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(user_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(contents)

    # EXIF scrub (LGPD: strip geolocation metadata)
    try:
        from PIL import Image
        img = Image.open(file_path)
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        clean.save(file_path)
    except Exception:
        pass

    rp = ReuniaoPhoto(
        reuniao_id=reuniao_id,
        uploader_user_id=current_user.id,
        file_path=f"/{file_path}",
        caption=caption,
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return {
        "success": True,
        "photo_id": rp.id,
        "file_path": rp.file_path,
        "message": "Foto subida — a turma vai matar saudade depois",
    }


@reuniao_router.get("/reuniao/{reuniao_id}/photos")
async def list_reuniao_photos(
    reuniao_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Lista fotos da reunião. Só confirmed RSVPs ou membros verified da turma podem ver."""
    reuniao = db.query(TurmaReuniao).filter(TurmaReuniao.id == reuniao_id).first()
    if not reuniao:
        raise HTTPException(404, "Reunião não encontrada")

    # Check membership: was confirmed RSVP OR is turma member verified
    rsvp = db.query(TurmaReuniaoRSVP).filter(
        TurmaReuniaoRSVP.reuniao_id == reuniao_id,
        TurmaReuniaoRSVP.user_id == current_user.id,
    ).first()
    if not rsvp:
        # Check verified turma member fallback
        member = db.query(TurmaMembership).filter(
            TurmaMembership.turma_id == reuniao.turma_id,
            TurmaMembership.user_id == current_user.id,
            TurmaMembership.status == 'verified',
        ).first()
        if not member:
            raise HTTPException(403, "Só membros da turma veem essas fotos")

    photos = db.query(ReuniaoPhoto).filter(
        ReuniaoPhoto.reuniao_id == reuniao_id,
        ReuniaoPhoto.deleted_at.is_(None),
    ).order_by(ReuniaoPhoto.created_at.desc()).all()

    return {
        "success": True,
        "count": len(photos),
        "photos": [
            {
                "id": p.id,
                "url": p.file_path,
                "caption": p.caption,
                "uploader_id": p.uploader_user_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in photos
        ],
    }
