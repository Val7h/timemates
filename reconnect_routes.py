"""
Reconnect routes — /api/reconnect with asymmetric reveal.

Design rules (Phase 1 spec):

  1. Asymmetric reveal
     ────────────────
     * Requester NEVER learns whether the target exists, is on the platform,
       received the email, or even saw the request. Every POST returns 200
       with the same opaque body.
     * Target sees Turma + shared_context + ice-breaker preview, but the
       requester's name/photo are revealed ONLY on Accept.
     * Decline = silence. No email, no notification, no status drift the
       requester can detect.

  2. Rate limit
     ──────────
     5 send attempts per day per requester (slowapi, key = requester user id).

  3. Cooling-off
     ───────────
     365-day block on re-requesting the same target after a Decline.
     Pending invites also block dup-requests until they expire or resolve.

  4. WhatsApp deeplink on Accept
     ───────────────────────────
     wa.me/{phone}?text={ice_breaker} — only if the requester opted in with
     a verified phone (`phone_verified=TRUE`). Otherwise we return a plain
     reveal payload and let the UI offer in-app DM.

  5. Block
     ─────
     Marks status='blocked', revokes requester's access to any Turma the
     target is in, and silently swallows any future reconnect attempts
     from the same requester toward the same target.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db, User, RoomMembership
from auth import get_current_user_required, require_18_plus
from reconnect_models import ReconnectRequest
import reconnect_email

# Cooling-off after a decline. The requester gets no signal that this is
# why a fresh attempt silently no-ops.
COOLING_OFF_DAYS = 365
PENDING_TTL_DAYS = 30


router = APIRouter(prefix="/api", tags=["reconnect"])


# ─── Pydantic payloads ────────────────────────────────────────────────────────

class ReconnectCreatePayload(BaseModel):
    turma_id: Optional[int] = Field(None, description="Shared Turma (Room) context.")
    message: Optional[str] = Field(None, max_length=1000,
                                   description="Optional personal note from requester.")
    ice_breaker: Optional[str] = Field(None, max_length=500,
                                       description="AI-generated WhatsApp opener.")


# ─── Helpers ──────────────────────────────────────────────────────────────────

# Opaque success body — identical for every POST regardless of outcome.
# This is what keeps the reveal asymmetric: a successful enqueue, a silent
# decline-cooldown no-op, and a "target doesn't exist" all look the same.
_OPAQUE_OK = {"ok": True, "message": "Se a pessoa existir e quiser ser encontrada, ela vai saber."}


def _build_shared_context(db: Session, requester: User, target_id: int,
                          turma_id: Optional[int]) -> dict:
    """Snapshot of common ground at request time.

    Frozen here (not computed on read) so a later block/leave doesn't
    silently change what the target sees.
    """
    ctx: dict = {}
    if turma_id:
        # turmas table is from migration 002 — no ORM class yet, use raw SQL.
        row = db.execute(
            text("SELECT cohort_label, cohort_year, institution_name, city "
                 "FROM turmas WHERE id = :tid"),
            {"tid": turma_id},
        ).mappings().first()
        if row:
            ctx["turma_name"] = row["cohort_label"] or f"Turma {row['cohort_year']}"
            ctx["turma_year"] = row["cohort_year"]
            ctx["institution_name"] = row["institution_name"]
            ctx["institution_city"] = row["city"]
    # Mutual Turmas (count of turmas both users are approved members of),
    # capped at 5. Falls back to 0 if either turma_memberships table or the
    # join target is missing.
    try:
        mutual_count = db.execute(
            text(
                "SELECT COUNT(*) FROM ("
                "  SELECT tm1.turma_id FROM turma_memberships tm1"
                "  JOIN turma_memberships tm2 ON tm1.turma_id = tm2.turma_id"
                "  WHERE tm1.user_id = :rid AND tm1.status = 'approved'"
                "    AND tm2.user_id = :tid AND tm2.status = 'approved'"
                "  LIMIT 5"
                ") AS m"
            ),
            {"rid": requester.id, "tid": target_id},
        ).scalar() or 0
    except Exception:
        mutual_count = 0
    ctx["mutual_turma_count"] = int(mutual_count)
    return ctx


def _turma_label(db: Session, turma_id: Optional[int]) -> str:
    """Human-readable label for the email subject. Generic fallback if
    no Turma context (still asymmetric — no requester info)."""
    if not turma_id:
        return "do seu passado"
    row = db.execute(
        text("SELECT cohort_label, cohort_year, institution_name "
             "FROM turmas WHERE id = :tid"),
        {"tid": turma_id},
    ).mappings().first()
    if not row:
        return "do seu passado"
    label = row["cohort_label"] or f"Turma {row['cohort_year']}"
    inst = row["institution_name"] or ""
    return f"{label} ({row['cohort_year']}) — {inst}".strip(" —")


# ─── POST /api/reconnect/{target_user_id} ─────────────────────────────────────

def register_routes(app, limiter):
    """Attach reconnect routes to the FastAPI app.

    `limiter` is the slowapi Limiter instance from main.py; we receive it
    so the 5/day key is the *requester's user id*, not the remote IP. IP
    rate limits would be trivially bypassed via NAT and would also
    rate-limit honest users who share a network.
    """

    def _user_id_key(request: Request) -> str:
        # slowapi calls this with the Request before our auth dep runs, so
        # we fall back to IP if the user isn't attached yet. The endpoint
        # itself enforces auth via Depends; this key is just for the bucket.
        user = getattr(request.state, "user", None)
        return f"user:{user.id}" if user else f"ip:{request.client.host if request.client else 'unknown'}"

    @app.post("/api/reconnect/{target_user_id}")
    @limiter.limit("5/day", key_func=_user_id_key)
    def create_reconnect_request(
        target_user_id: int,
        request: Request,
        payload: ReconnectCreatePayload = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_required),
    ):
        """Create a reconnect request. ALWAYS returns 200 with an opaque body.

        Every branch below — target not found, opted out, cooling-off,
        duplicate, blocked, or successfully sent — returns the same
        ``_OPAQUE_OK`` payload. This is the load-bearing invariant of the
        asymmetric reveal: from the requester's side, the platform is a
        black box.
        """
        # Bind user to request.state so the rate-limit key_func can see it.
        request.state.user = current_user

        # ── 18+ gate (LGPD Art. 14 + ECA).
        # Reconnect inicia contato direto entre dois adultos via WhatsApp; o
        # requester precisa ter idade comprovável. Diferente das outras
        # branches "silenciosas" (que retornam _OPAQUE_OK pra esconder estado
        # do target), aqui falhamos com 403 explícito: o problema está com o
        # requester, não com o target, então não há informação a vazar.
        require_18_plus(current_user)

        # Can't reconnect with yourself. Return opaque OK anyway (no signal).
        if target_user_id == current_user.id:
            return _OPAQUE_OK

        target = db.query(User).filter(User.id == target_user_id,
                                       User.is_active == True).first()

        # ── Branch 1: target doesn't exist or deactivated.
        # Silent no-op. Requester sees the same 200 as a real send.
        if not target:
            return _OPAQUE_OK

        # ── Branch 2: target opted out of reconnect requests.
        # Silent no-op. Privacy default protects ghosts.
        if not getattr(target, "allow_reconnect_requests", True):
            return _OPAQUE_OK

        now = datetime.utcnow()

        # ── Branch 3: cooling-off after a previous decline.
        recent_decline = (
            db.query(ReconnectRequest)
            .filter(
                ReconnectRequest.requester_id == current_user.id,
                ReconnectRequest.target_id == target_user_id,
                ReconnectRequest.status == "declined",
                ReconnectRequest.responded_at >= now - timedelta(days=COOLING_OFF_DAYS),
            ).first()
        )
        if recent_decline:
            return _OPAQUE_OK

        # ── Branch 4: target previously blocked this requester.
        already_blocked = (
            db.query(ReconnectRequest)
            .filter(
                ReconnectRequest.requester_id == current_user.id,
                ReconnectRequest.target_id == target_user_id,
                ReconnectRequest.status == "blocked",
            ).first()
        )
        if already_blocked:
            return _OPAQUE_OK

        # ── Branch 5: pending request already in-flight (dedupe).
        existing_pending = (
            db.query(ReconnectRequest)
            .filter(
                ReconnectRequest.requester_id == current_user.id,
                ReconnectRequest.target_id == target_user_id,
                ReconnectRequest.status == "pending",
                ReconnectRequest.expires_at > now,
            ).first()
        )
        if existing_pending:
            return _OPAQUE_OK

        # ── Create the request.
        req = ReconnectRequest(
            requester_id=current_user.id,
            target_id=target_user_id,
            turma_id=payload.turma_id,
            status="pending",
            message=payload.ice_breaker or payload.message,
            shared_context=_build_shared_context(db, current_user, target_user_id,
                                                 payload.turma_id),
            created_at=now,
            expires_at=now + timedelta(days=PENDING_TTL_DAYS),
        )
        db.add(req)
        db.commit()
        db.refresh(req)

        # ── Send the asymmetric-reveal email. Fire-and-forget; failures
        # are logged but never surface to the requester.
        # LGPD Art. 7/11: only email the TARGET if they've consented to receive
        # reconnect emails. We silently skip otherwise so the requester gets the
        # same opaque OK (no signal that the target opted out).
        try:
            from consent_helpers import has_active_consent as _has_consent
            target_opted_in = _has_consent(db, target.id, 'reconnect_emails')
        except Exception:
            target_opted_in = False
        if target_opted_in:
            try:
                turma_name = _turma_label(db, payload.turma_id)
                reconnect_email.send_reconnect_invite(
                    to_email=target.email,
                    turma_name=turma_name,
                    request_id=req.id,
                    full_name=target.full_name,
                )
            except Exception as e:
                print(f"[RECONNECT] email send failed for req={req.id}: {e}")
        else:
            print(f"[RECONNECT] target {target.id} not consented to reconnect_emails; "
                  f"request {req.id} stored but email skipped")

        return _OPAQUE_OK


    # ─── GET /api/me/reconnect-requests ───────────────────────────────────────
    @app.get("/api/me/reconnect-requests")
    def list_my_pending_requests(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_required),
    ):
        """List pending requests TO me. Requester identity stays hidden."""
        now = datetime.utcnow()

        # Lazy expiry: mark stale pending rows as expired on read.
        stale = (
            db.query(ReconnectRequest)
            .filter(ReconnectRequest.target_id == current_user.id,
                    ReconnectRequest.status == "pending",
                    ReconnectRequest.expires_at <= now)
            .all()
        )
        for r in stale:
            r.status = "expired"
        if stale:
            db.commit()

        pending = (
            db.query(ReconnectRequest)
            .filter(ReconnectRequest.target_id == current_user.id,
                    ReconnectRequest.status == "pending",
                    ReconnectRequest.expires_at > now)
            .order_by(ReconnectRequest.created_at.desc())
            .all()
        )

        out = []
        for r in pending:
            ctx = r.shared_context or {}
            # IMPORTANT: no requester_id, requester_name, requester_photo,
            # or requester_email in this payload. The reveal is gated on
            # the Accept endpoint.
            out.append({
                "request_id": r.id,
                "turma_context": {
                    "turma_name": ctx.get("turma_name"),
                    "turma_year": ctx.get("turma_year"),
                    "institution_name": ctx.get("institution_name"),
                    "institution_city": ctx.get("institution_city"),
                },
                "shared_context_summary": {
                    "mutual_turma_count": ctx.get("mutual_turma_count", 0),
                },
                "message_preview": (r.message[:160] + "…") if r.message and len(r.message) > 160 else r.message,
                "created_at": r.created_at.isoformat(),
                "expires_at": r.expires_at.isoformat(),
            })
        return {"requests": out, "count": len(out)}


    # ─── POST /api/reconnect-requests/{id}/accept ─────────────────────────────
    @app.post("/api/reconnect-requests/{request_id}/accept")
    def accept_reconnect_request(
        request_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_required),
    ):
        """Accept: NOW both identities are revealed and we return a
        WhatsApp deeplink (if the requester opted in with a verified phone).
        """
        req = (
            db.query(ReconnectRequest)
            .filter(ReconnectRequest.id == request_id,
                    ReconnectRequest.target_id == current_user.id)
            .first()
        )
        if not req:
            raise HTTPException(status_code=404, detail="request_not_found")
        if req.status != "pending":
            raise HTTPException(status_code=409, detail=f"request_{req.status}")
        if req.expires_at <= datetime.utcnow():
            req.status = "expired"
            db.commit()
            raise HTTPException(status_code=410, detail="request_expired")

        req.status = "accepted"
        req.responded_at = datetime.utcnow()
        db.commit()

        requester = db.query(User).filter(User.id == req.requester_id).first()
        if not requester:
            # Edge case: requester deleted account between request and accept.
            return {"status": "accepted", "requester": None,
                    "whatsapp_deeplink": None,
                    "note": "A pessoa não está mais disponível."}

        # WhatsApp deeplink — only if requester opted in with a verified
        # phone. Otherwise the UI should fall back to an in-app DM.
        whatsapp_deeplink = None
        if requester.phone and getattr(requester, "phone_verified", False):
            digits = "".join(ch for ch in requester.phone if ch.isdigit())
            ice_breaker = req.message or (
                f"Oi! Sou {requester.full_name.split()[0] if requester.full_name else 'eu'}, "
                f"a gente foi da Turma {(req.shared_context or {}).get('turma_name', '')}. "
                "Quanto tempo!"
            )
            whatsapp_deeplink = f"https://wa.me/{digits}?text={quote(ice_breaker)}"

        return {
            "status": "accepted",
            "requester": {
                "id": requester.id,
                "full_name": requester.full_name,
                "profile_photo": requester.profile_photo,
                "city": requester.city if requester.show_city else None,
                "profession": requester.profession if requester.show_profession else None,
                "bio": requester.bio if requester.show_bio else None,
            },
            "ice_breaker": req.message,
            "shared_context": req.shared_context,
            "whatsapp_deeplink": whatsapp_deeplink,
        }


    # ─── POST /api/reconnect-requests/{id}/decline ────────────────────────────
    @app.post("/api/reconnect-requests/{request_id}/decline")
    def decline_reconnect_request(
        request_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_required),
    ):
        """Decline silently. The requester is never notified — they just
        never get a response. A 365-day cooling-off blocks re-requests.
        """
        req = (
            db.query(ReconnectRequest)
            .filter(ReconnectRequest.id == request_id,
                    ReconnectRequest.target_id == current_user.id)
            .first()
        )
        if not req:
            raise HTTPException(status_code=404, detail="request_not_found")
        if req.status != "pending":
            raise HTTPException(status_code=409, detail=f"request_{req.status}")

        req.status = "declined"
        req.responded_at = datetime.utcnow()
        db.commit()
        # No email, no notification, no webhook. Silence is the feature.
        return {"status": "declined"}


    # ─── POST /api/reconnect-requests/{id}/block ──────────────────────────────
    @app.post("/api/reconnect-requests/{request_id}/block")
    def block_requester(
        request_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user_required),
    ):
        """Block the requester. Also retroactively removes them from any
        shared Turma the target is a member of so the target stops appearing
        in shared contexts going forward.
        """
        req = (
            db.query(ReconnectRequest)
            .filter(ReconnectRequest.id == request_id,
                    ReconnectRequest.target_id == current_user.id)
            .first()
        )
        if not req:
            raise HTTPException(status_code=404, detail="request_not_found")

        req.status = "blocked"
        req.responded_at = datetime.utcnow()

        # Retroactive scrub: remove the requester from every Turma the
        # target is currently approved in, so the requester stops seeing
        # the target in any shared context. The requester gets no
        # notification — they discover the loss of access only on next
        # turma load. Best-effort against both the legacy `rooms` schema
        # and the new `turma_memberships` schema.
        try:
            db.execute(
                text(
                    "DELETE FROM turma_memberships "
                    "WHERE user_id = :rid AND turma_id IN ("
                    "  SELECT turma_id FROM turma_memberships "
                    "  WHERE user_id = :tid AND status = 'approved'"
                    ")"
                ),
                {"rid": req.requester_id, "tid": current_user.id},
            )
        except Exception as e:
            print(f"[RECONNECT block] turma_memberships scrub skipped: {e}")
        try:
            target_room_ids = [
                rid for (rid,) in db.query(RoomMembership.room_id)
                .filter(RoomMembership.user_id == current_user.id,
                        RoomMembership.status == "approved")
                .all()
            ]
            if target_room_ids:
                (db.query(RoomMembership)
                    .filter(RoomMembership.user_id == req.requester_id,
                            RoomMembership.room_id.in_(target_room_ids))
                    .delete(synchronize_session=False))
        except Exception as e:
            print(f"[RECONNECT block] room_memberships scrub skipped: {e}")

        # Also kill any other pending requests from the same requester to
        # this target so they can't sneak through a stale row.
        (db.query(ReconnectRequest)
            .filter(ReconnectRequest.requester_id == req.requester_id,
                    ReconnectRequest.target_id == current_user.id,
                    ReconnectRequest.status == "pending")
            .update({"status": "blocked",
                     "responded_at": datetime.utcnow()},
                    synchronize_session=False))

        db.commit()
        return {"status": "blocked"}
