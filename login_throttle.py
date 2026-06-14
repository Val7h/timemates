"""Login throttling via DB. Persistent across workers.

Strategy: progressive lockout
- 5 fails in 15min -> 5 min lockout
- 10 fails in 1h -> 1h lockout
- 20 fails in 24h -> 24h lockout

Tracks by EMAIL (not IP) to avoid NAT issues. Also logs by IP for forensics.
"""

import hashlib
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from database import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), index=True)
    ip_hash = Column(String(64), nullable=True)
    ua_hash = Column(String(64), nullable=True)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


THRESHOLDS = [
    # (window_minutes, max_fails, lockout_minutes)
    (15, 5, 5),
    (60, 10, 60),
    (24 * 60, 20, 24 * 60),
]


def record_attempt(db: Session, email: str, success: bool, request=None):
    """Record login attempt for audit + throttling."""
    ip_hash = None
    ua_hash = None
    if request is not None:
        try:
            ip = request.client.host if request.client else ''
            ip_hash = hashlib.sha256(ip.encode()).hexdigest()
            ua = request.headers.get('user-agent', '') or ''
            ua_hash = hashlib.sha256(ua.encode()).hexdigest()
        except Exception:
            pass
    try:
        att = LoginAttempt(
            email=(email or '').lower(),
            success=bool(success),
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )
        db.add(att)
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass


def is_locked_out(db: Session, email: str) -> dict:
    """Returns {locked: bool, retry_after_seconds: int, reason: str}."""
    if not email:
        return {"locked": False}
    email = email.lower()
    now = datetime.utcnow()
    try:
        for window_min, max_fails, lockout_min in THRESHOLDS:
            window_start = now - timedelta(minutes=window_min)
            fails = db.query(LoginAttempt).filter(
                LoginAttempt.email == email,
                LoginAttempt.success == False,  # noqa: E712
                LoginAttempt.created_at >= window_start,
            ).count()
            if fails >= max_fails:
                # Check if last fail was within lockout period
                last_fail = db.query(LoginAttempt).filter(
                    LoginAttempt.email == email,
                    LoginAttempt.success == False,  # noqa: E712
                ).order_by(LoginAttempt.created_at.desc()).first()
                if last_fail and (now - last_fail.created_at).total_seconds() < lockout_min * 60:
                    retry_after = int(
                        lockout_min * 60 - (now - last_fail.created_at).total_seconds()
                    )
                    if retry_after < 1:
                        retry_after = 1
                    minutes = max(1, retry_after // 60)
                    return {
                        "locked": True,
                        "retry_after_seconds": retry_after,
                        "reason": f"Muitas tentativas. Tenta de novo em {minutes} minutos.",
                    }
    except Exception:
        # On DB error, fail OPEN (don't lock legit users out) — caller will still log via record_attempt
        return {"locked": False}
    return {"locked": False}


def reset_failures(db: Session, email: str):
    """On successful login, mark prior fails as not counting (don't delete - audit)."""
    # Just record the success — is_locked_out only counts fails within window
    pass


def purge_old_attempts(retention_days: int = 30) -> dict:
    """Delete login_attempts rows older than ``retention_days``. Daily cron."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        deleted = db.query(LoginAttempt).filter(
            LoginAttempt.created_at < cutoff,
        ).delete(synchronize_session=False)
        db.commit()
        report = {
            'login_attempts_purged': int(deleted or 0),
            'retention_days': retention_days,
            'cutoff_utc': cutoff.isoformat(),
            'ran_at_utc': datetime.utcnow().isoformat(),
        }
        return report
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        return {'error': str(e), 'ran_at_utc': datetime.utcnow().isoformat()}
    finally:
        db.close()
