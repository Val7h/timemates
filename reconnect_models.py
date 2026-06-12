"""
Reconnect feature — SQLAlchemy model for ReconnectRequest.

Implements the "asymmetric reveal" pattern:
- Requester never learns whether target exists or saw the request.
- Target sees only Turma/context until they explicitly Accept.
- Decline is silent (requester sees nothing).
- 365-day cooling-off after decline.
- 30-day expiry on pending invites.

Note: `turma_id` references the `turmas` table created in migration 002.
We don't import the Turma ORM class (no model file yet) — the column is
declared with a raw ForeignKey string so SQLAlchemy resolves it lazily
once the runtime metadata includes turmas.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta

from database import Base


def _default_expiry():
    return datetime.utcnow() + timedelta(days=30)


class ReconnectRequest(Base):
    """A request from one user to reconnect with another via a shared Turma."""
    __tablename__ = "reconnect_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Turma context — references turmas.id from migration 002.
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=True)
    # 'pending' | 'accepted' | 'declined' | 'expired' | 'blocked'
    status = Column(String(20), default="pending", nullable=False, index=True)
    # AI-generated ice-breaker shown to target on accept and prefilled into WhatsApp.
    message = Column(String(1000), nullable=True)
    # JSON snapshot of what they have in common (turma name, year, mutual friends, etc).
    shared_context = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, default=_default_expiry, nullable=False)

    requester = relationship("User", foreign_keys=[requester_id])
    target = relationship("User", foreign_keys=[target_id])

    __table_args__ = (
        Index("ix_reconnect_target_status", "target_id", "status"),
        Index("ix_reconnect_requester_target", "requester_id", "target_id"),
    )
