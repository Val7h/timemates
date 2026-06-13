"""Consent helpers — LGPD Art. 11 (Granular consent).

Provides helpers around the UserConsent model:
  * has_active_consent(db, user_id, type) -> bool
  * grant_consent(db, user_id, type, request=None, version='v1') -> UserConsent
  * revoke_consent(db, user_id, type) -> None
  * require_consent(consent_type) -> FastAPI dependency factory

Audit trail: IP and user-agent are stored as sha256 hashes, never plaintext.
Multiple grants of the same type may coexist; "active" means
``granted=True AND revoked_at IS NULL`` (most recent grant wins).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import UserConsent, User, get_db


# Canonical list of supported consent types. Anything else is rejected at the
# endpoint layer so we don't accidentally grant unknown purposes.
VALID_CONSENT_TYPES = {
    'terms_of_service',
    'privacy_policy',
    'tunel_biometric',
    'face_matching',
    'email_marketing',
    'reconnect_emails',
    'lgpd_data_processing',
}


def has_active_consent(db: Session, user_id: int, consent_type: str) -> bool:
    """Returns True if user has active (granted, not revoked) consent of type."""
    c = (
        db.query(UserConsent)
        .filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.granted == True,  # noqa: E712  (SQLAlchemy expr)
            UserConsent.revoked_at.is_(None),
        )
        .order_by(UserConsent.granted_at.desc())
        .first()
    )
    return c is not None


def _hash(value: str) -> str:
    return hashlib.sha256((value or '').encode()).hexdigest()


def grant_consent(
    db: Session,
    user_id: int,
    consent_type: str,
    request: Optional[Request] = None,
    version: str = 'v1',
) -> UserConsent:
    """Record a positive consent grant. Audit IP/UA hashes when request given."""
    ip_hash: Optional[str] = None
    ua_hash: Optional[str] = None
    if request is not None:
        client_ip = ''
        try:
            client_ip = request.client.host if request.client else ''
        except Exception:
            client_ip = ''
        ip_hash = _hash(client_ip)
        ua = request.headers.get('user-agent', '') if request.headers else ''
        ua_hash = _hash(ua)
    c = UserConsent(
        user_id=user_id,
        consent_type=consent_type,
        granted=True,
        granted_at=datetime.utcnow(),
        version=version,
        ip_address_hash=ip_hash,
        user_agent_hash=ua_hash,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def revoke_consent(db: Session, user_id: int, consent_type: str) -> int:
    """Revoke all active grants of (user_id, consent_type). Returns # revoked."""
    cs = (
        db.query(UserConsent)
        .filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == consent_type,
            UserConsent.revoked_at.is_(None),
        )
        .all()
    )
    now = datetime.utcnow()
    for c in cs:
        c.revoked_at = now
    db.commit()
    return len(cs)


def list_consents(db: Session, user_id: int) -> list[dict]:
    """Return one row per consent_type with current active state + last grant."""
    rows = (
        db.query(UserConsent)
        .filter(UserConsent.user_id == user_id)
        .order_by(UserConsent.granted_at.desc())
        .all()
    )
    by_type: dict[str, dict] = {}
    for r in rows:
        if r.consent_type in by_type:
            continue
        by_type[r.consent_type] = {
            'consent_type': r.consent_type,
            'granted': bool(r.granted) and r.revoked_at is None,
            'granted_at': r.granted_at.isoformat() if r.granted_at else None,
            'revoked_at': r.revoked_at.isoformat() if r.revoked_at else None,
            'version': r.version,
        }
    # Include valid types the user has never touched (so frontend can render UI)
    for t in VALID_CONSENT_TYPES:
        if t not in by_type:
            by_type[t] = {
                'consent_type': t,
                'granted': False,
                'granted_at': None,
                'revoked_at': None,
                'version': None,
            }
    return list(by_type.values())


def require_consent(consent_type: str):
    """FastAPI dependency factory: 403s if the current user lacks active consent.

    Usage::

        @app.post('/api/tunel/upload',
                  dependencies=[Depends(require_consent('tunel_biometric'))])
        def upload(...): ...

    Importing the auth dep inline avoids circular import w/ auth.py at module load.
    """
    def _dep(
        db: Session = Depends(get_db),
        current_user: User = Depends(_current_user_required_lazy),
    ):
        if not has_active_consent(db, current_user.id, consent_type):
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'consent_required',
                    'consent_type': consent_type,
                    'message': (
                        f"Consentimento '{consent_type}' obrigatório (LGPD Art. 11). "
                        f"Use POST /api/me/consents/{consent_type}/grant para conceder."
                    ),
                },
            )
        return True
    return _dep


def _current_user_required_lazy(*args, **kwargs):
    """Resolved lazily to break potential auth.py <-> consent_helpers cycle."""
    from auth import get_current_user_required  # local import
    # Re-dispatch through FastAPI's Depends by simply calling the underlying dep.
    # When FastAPI introspects the signature it sees no Depends here, so we wrap
    # via the actual dep below.
    raise RuntimeError("_current_user_required_lazy should be replaced at import time")


# At import time, swap the lazy placeholder for the real dependency. We do this
# AFTER the module body so that consumers importing require_consent get the
# real Depends chain (FastAPI inspects defaults at route-registration time).
try:
    from auth import get_current_user_required as _gcr_real

    def _current_user_required_lazy(  # type: ignore[no-redef]
        current_user: User = Depends(_gcr_real),
    ) -> User:
        return current_user
except Exception:
    # auth.py not importable at module load (e.g. during migrations). The dep
    # factory will fail loudly only if actually invoked.
    pass
