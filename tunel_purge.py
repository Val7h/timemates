"""Daily cron: purge tunel_uploads soft-deleted > 30 days ago.

Called by APScheduler from main.py lifespan (PURGE_ENABLED=true) OR by a Render
Cron Job invoking this module directly: `python -m tunel_purge`.

Hard-deletes the DB row, the physical file under uploads/tunel/{user_id}/...,
and any TunelFace embeddings (biometric data — must die with the upload).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

from database import SessionLocal, TunelFace, TunelUpload

logger = logging.getLogger(__name__)


def purge_deleted_uploads(retention_days: int = 30) -> dict:
    """Hard-delete tunel_uploads soft-deleted more than ``retention_days`` ago.

    Also removes the physical photo file and any face embeddings tied to it.
    Safe to call repeatedly — rows already purged simply won't match the filter.
    Returns a small report dict for logging / cron observability.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        uploads = db.query(TunelUpload).filter(
            TunelUpload.deleted_at.isnot(None),
            TunelUpload.deleted_at < cutoff,
        ).all()
        files_deleted = 0
        faces_deleted = 0
        for u in uploads:
            try:
                if u.file_path and os.path.exists(u.file_path):
                    os.remove(u.file_path)
                    files_deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete file {u.file_path}: {e}")
            f_count = db.query(TunelFace).filter(
                TunelFace.upload_id == u.id
            ).delete(synchronize_session=False)
            faces_deleted += f_count or 0
            db.delete(u)
        db.commit()
        report = {
            'uploads_purged': len(uploads),
            'files_deleted': files_deleted,
            'faces_deleted': faces_deleted,
            'retention_days': retention_days,
            'cutoff_utc': cutoff.isoformat(),
            'ran_at_utc': datetime.utcnow().isoformat(),
        }
        logger.info(f"[TUNEL_PURGE] {report}")
        return report
    finally:
        db.close()


def purge_pending_account_deletions(cool_off_days: int = 7) -> dict:
    """Hard-delete user accounts whose deletion request expired the cool-off.

    Companion to the LGPD deletion-request flow: users opt in via
    POST /api/me/lgpd-deletion-request, get a 7-day window to cancel, and
    if they don't cancel, this cron wipes the account on the next run.

    Implementation uses the ``is_active`` flag plus a deletion sentinel in
    the user's bio field (``__lgpd_deletion__:ISO_TS``) because we don't want
    to require a new column for a low-traffic flow. main.py's lgpd-deletion-*
    endpoints write this sentinel.
    """
    from database import User  # local import to avoid circulars at module load

    db = SessionLocal()
    purged = 0
    try:
        cutoff = datetime.utcnow() - timedelta(days=cool_off_days)
        candidates = db.query(User).filter(
            User.is_active == False,  # noqa: E712 — SQL boolean
            User.bio.like("__lgpd_deletion__:%"),
        ).all()
        for u in candidates:
            try:
                _, _, ts = (u.bio or "").partition(":")
                requested_at = datetime.fromisoformat(ts) if ts else None
            except Exception:
                requested_at = None
            if requested_at is None or requested_at >= cutoff:
                continue
            # Cascade: face embeddings + uploads + the row itself.
            uploads = db.query(TunelUpload).filter(
                TunelUpload.user_id == u.id
            ).all()
            for up in uploads:
                try:
                    if up.file_path and os.path.exists(up.file_path):
                        os.remove(up.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete file {up.file_path}: {e}")
                db.query(TunelFace).filter(
                    TunelFace.upload_id == up.id
                ).delete(synchronize_session=False)
                db.delete(up)
            db.delete(u)
            purged += 1
        db.commit()
        report = {
            'accounts_purged': purged,
            'cool_off_days': cool_off_days,
            'ran_at_utc': datetime.utcnow().isoformat(),
        }
        logger.info(f"[LGPD_DELETION_PURGE] {report}")
        return report
    finally:
        db.close()


if __name__ == "__main__":
    # Allows: python -m tunel_purge  (for Render Cron Job)
    logging.basicConfig(level=logging.INFO)
    r1 = purge_deleted_uploads()
    r2 = purge_pending_account_deletions()
    print({"uploads": r1, "accounts": r2})
