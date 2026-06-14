"""DB-backed rate limiting. Shared state across workers.

slowapi (BUG H4) keeps its counters in-process, so on Render's multi-worker
gunicorn each worker has its own bucket — a 5/day limit becomes 5*N/day in
practice. For LGPD-sensitive or expensive endpoints (reconnect, tunel upload,
mural creation) we need real shared state. Postgres is already there, no Redis
required.

Drop-in pattern:
    from rate_limit_db import check_rate_limit
    check_rate_limit(db, key='user:42:upload', max_per_window=5, window_seconds=86400)

Raises HTTPException 429 if exceeded.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from database import Base


class RateLimitHit(Base):
    """One row per allowed request. We count rows in the active window.

    Index on (key, created_at) makes the count query O(log n) on Postgres.
    Old rows are purged daily by ``cleanup_old_hits`` — without it the table
    grows unbounded and the count starts costing more than the work it gates.
    """
    __tablename__ = "rate_limit_hits"
    id = Column(Integer, primary_key=True)
    key = Column(String(200), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def check_rate_limit(db: Session, key: str, max_per_window: int, window_seconds: int):
    """Returns True if OK, raises 429 if exceeded.

    Records a hit on success (counts as one of the ``max_per_window``).
    The retry_after is computed from the oldest hit still in the window —
    once that one falls off the trailing edge, the user gets a slot back.

    Race note: two concurrent requests at limit-1 may both pass the count
    check and both record a hit, briefly putting the user at limit+1. We
    accept that — it's a soft limit, not a hard quota. Postgres SERIALIZABLE
    would be overkill for this and would deadlock under load.
    """
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=window_seconds)

    hits = db.query(RateLimitHit).filter(
        RateLimitHit.key == key,
        RateLimitHit.created_at >= window_start,
    ).count()

    if hits >= max_per_window:
        # Compute retry-after from the oldest hit still in the active window:
        # once it ages out, one slot becomes free.
        oldest_in_window = db.query(RateLimitHit).filter(
            RateLimitHit.key == key,
            RateLimitHit.created_at >= window_start,
        ).order_by(RateLimitHit.created_at.asc()).first()
        if oldest_in_window is not None:
            retry_after = int(
                (oldest_in_window.created_at
                 + timedelta(seconds=window_seconds) - now).total_seconds()
            )
        else:
            # Shouldn't happen (hits >= 1 means at least one row exists), but
            # don't crash if a race deleted it between the two queries.
            retry_after = window_seconds
        retry_after = max(retry_after, 1)
        # PT-BR friendly message — user-facing, matches the rest of the app.
        if retry_after >= 60:
            human = f"{retry_after // 60} minutos"
        else:
            human = f"{retry_after} segundos"
        raise HTTPException(
            status_code=429,
            detail={
                "detail": f"Limite atingido. Tenta de novo em {human}.",
                "retry_after": retry_after,
            },
        )

    # Record the hit. Commit so other workers see it immediately — the whole
    # point of this module is shared state across processes.
    hit = RateLimitHit(key=key, created_at=now)
    db.add(hit)
    db.commit()
    return True


def cleanup_old_hits(db: Session, older_than_days: int = 1) -> dict:
    """Purge hits older than N days. Run daily via cron.

    Default 1 day covers the longest current window (86400s = 1 day for the
    reconnect / upload / mural limits). If you add a multi-day window, bump
    this to match — purging too aggressively would let users escape the limit.
    """
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    deleted = db.query(RateLimitHit).filter(
        RateLimitHit.created_at < cutoff
    ).delete(synchronize_session=False)
    db.commit()
    return {
        "rate_limit_hits_purged": int(deleted or 0),
        "cutoff_utc": cutoff.isoformat(),
        "ran_at_utc": datetime.utcnow().isoformat(),
    }
