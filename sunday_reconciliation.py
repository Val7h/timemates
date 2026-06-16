"""Sunday Reconciliation — habit loop semanal.

Toda domingo 09:00 BRT (12:00 UTC):
- Pra cada user ativo:
  - Pick ONE dormant tie via algorithm:
    * Score by: tempo desde último contato + força do laço (turmas em comum) + 'why now' signals (aniversário próximo, etc)
  - Send 1 push notification + 1 email com link direto pro reconnect
  - Track in metrics

Frequency: weekly, never more.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, User, TurmaMembership, Turma
from reconnect_models import ReconnectRequest
import logging
import random

logger = logging.getLogger(__name__)


def find_best_dormant_tie(db: Session, user_id: int) -> dict:
    """Find 1 person to surface this Sunday.
    Algorithm:
    - User must be in same verified turma
    - User has not been reconnected with in last 90 days
    - User exists (default-ghost respected: opt-in required)
    - Score by: shared turmas count, time since last contact
    """
    # Get user's verified turmas
    my_turmas = db.query(TurmaMembership.turma_id).filter(
        TurmaMembership.user_id == user_id,
        TurmaMembership.status == 'verified',
    ).all()
    my_turma_ids = [t[0] for t in my_turmas]
    if not my_turma_ids:
        return None

    # Find candidates: people in my turmas, not me, who allow reconnect
    from sqlalchemy import func

    candidates_q = db.query(
        User.id, User.full_name, func.count(TurmaMembership.id).label('shared_count')
    ).join(
        TurmaMembership, TurmaMembership.user_id == User.id
    ).filter(
        TurmaMembership.turma_id.in_(my_turma_ids),
        TurmaMembership.status == 'verified',
        User.id != user_id,
        User.allow_reconnect_requests == True,
    ).group_by(User.id, User.full_name).order_by(func.count(TurmaMembership.id).desc())

    candidates = candidates_q.limit(20).all()
    if not candidates:
        return None

    # Filter out people who already got a recent reconnect from this user
    recent_cutoff = datetime.utcnow() - timedelta(days=90)
    recent_targets = set()
    for r in db.query(ReconnectRequest.target_id).filter(
        ReconnectRequest.requester_id == user_id,
        ReconnectRequest.created_at >= recent_cutoff,
    ).all():
        recent_targets.add(r[0])

    candidates = [(uid, name, sc) for uid, name, sc in candidates if uid not in recent_targets]
    if not candidates:
        return None

    # Pick top scored (most shared turmas), with a bit of randomness for variety
    top_candidates = candidates[:5]
    chosen = random.choice(top_candidates)
    return {
        'target_user_id': chosen[0],
        'target_name': chosen[1],
        'shared_turmas_count': chosen[2],
    }


def run_sunday_reconciliation():
    """Called by cron every Sunday 09:00 BRT.
    For each active user, surface 1 dormant tie."""
    db = SessionLocal()
    try:
        active_users = db.query(User).filter(
            User.is_active == True,
            User.allow_reconnect_requests == True,
        ).all()

        count_sent = 0
        for user in active_users:
            tie = find_best_dormant_tie(db, user.id)
            if not tie:
                continue
            # Email via SendGrid (if configured)
            try:
                from email_service_sendgrid import _send_via_sendgrid
                first = (user.full_name or 'Você').split()[0]
                target_first = tie['target_name'].split()[0]
                msg_html = f"""
                <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px;">
                  <h1 style="color:#d4a853;">{first}, esse domingo é {target_first}.</h1>
                  <p>Vocês têm {tie['shared_turmas_count']} turma(s) em comum.</p>
                  <p>Há quanto tempo você não dá um oi pra {target_first}?</p>
                  <a href="https://timemates.onrender.com/tunel"
                     style="display:inline-block;background:#d4a853;color:#000;padding:12px 24px;text-decoration:none;border-radius:8px;">
                    Mandar um oi
                  </a>
                  <p style="margin-top:24px;font-size:13px;color:#888;">
                    Você só recebe esse email aos domingos. Um por semana, no máximo.
                    Pra desativar, edite suas preferências em /api/me/visibility.
                  </p>
                </div>
                """
                _send_via_sendgrid(
                    to_email=user.email,
                    to_name=user.full_name or '',
                    subject=f"Domingo de saudade — {target_first} de novo?",
                    html_content=msg_html,
                )
                count_sent += 1
            except Exception as e:
                logger.warning(f"sunday recon failed for user {user.id}: {e}")

        logger.info(f"[SUNDAY RECON] sent {count_sent} reconciliation prompts")
        return {"users_processed": len(active_users), "emails_sent": count_sent}
    finally:
        db.close()
