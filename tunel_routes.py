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
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db, User, TunelUpload, TunelFace
from auth import get_current_user_required

logger = logging.getLogger(__name__)

tunel_router = APIRouter(prefix="/api/tunel", tags=["tunel"])

ALLOWED_MIME = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
UPLOAD_DIR_BASE = "uploads/tunel"


@tunel_router.post("/upload")
async def upload_old_photo(
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
    """
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

    return {
        "success": True,
        "upload_id": upload.id,
        "preview_url": f"/uploads/tunel/{current_user.id}/{filename}",
        "file_size_kb": round(len(contents) / 1024, 1),
        "exif_scrubbed": exif_scrubbed,
        "next_step": "Aguarde processamento. Face detection virá no Sprint 2.",
    }


@tunel_router.get("/uploads/me")
async def list_my_uploads(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Lista uploads do próprio user (não-deletados)."""
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
