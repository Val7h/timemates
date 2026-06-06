"""
Rotas FastAPI para notificações, presença, reações e eventos
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import asyncio
import json

from database import (
    get_db, User, Room, RoomMembership, Message,
    Notification, PushSubscription, UserPresence,
)
from models_extensions import (
    Event, EventRSVP, MessageReaction, News
)
from auth import get_current_user_required
from notification_service import NotificationService
from tracking_service import TrackingService

router = APIRouter(prefix="/api", tags=["notifications"])

# WebSocket manager para broadcast em tempo real
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, room_id: int, user_id: int, websocket: WebSocket):
        await websocket.accept()
        key = f"room_{room_id}"
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append((user_id, websocket))

    def disconnect(self, room_id: int, user_id: int):
        key = f"room_{room_id}"
        if key in self.active_connections:
            self.active_connections[key] = [
                (u, ws) for u, ws in self.active_connections[key]
                if u != user_id
            ]

    async def broadcast(self, room_id: int, message: dict):
        key = f"room_{room_id}"
        if key not in self.active_connections:
            return
        for user_id, websocket in self.active_connections[key]:
            try:
                await websocket.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


# ─────────────────────────────────────────
# PUSH SUBSCRIPTIONS
# ─────────────────────────────────────────

@router.post("/push/subscribe")
async def subscribe_to_push(
    subscription_data: dict,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Registra subscription Web Push para notificações do navegador
    """
    try:
        # Remove subscription anterior se existir
        existing = db.query(PushSubscription).filter(
            PushSubscription.user_id == current_user.id,
            PushSubscription.endpoint == subscription_data["endpoint"]
        ).first()

        if existing:
            db.delete(existing)

        # Cria nova subscription
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=subscription_data["endpoint"],
            p256dh=subscription_data["keys"]["p256dh"],
            auth=subscription_data["keys"]["auth"]
        )
        db.add(sub)
        db.commit()

        return {"status": "subscribed"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/push/unsubscribe")
async def unsubscribe_from_push(
    endpoint: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Remove subscription Web Push"""
    sub = db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.endpoint == endpoint
    ).first()

    if sub:
        db.delete(sub)
        db.commit()

    return {"status": "unsubscribed"}


# ─────────────────────────────────────────
# NOTIFICAÇÕES
# ─────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
    unread_only: bool = False,
    limit: int = 20
):
    """Lista notificações do usuário"""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifications = query.order_by(
        Notification.sent_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "data": n.data,
            "is_read": n.is_read,
            "sent_at": n.sent_at.isoformat()
        }
        for n in notifications
    ]


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Marca notificação como lida"""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")

    notif.is_read = True
    notif.read_at = datetime.utcnow()
    db.commit()

    return {"status": "marked_as_read"}


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Deleta notificação"""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")

    db.delete(notif)
    db.commit()

    return {"status": "deleted"}


# ─────────────────────────────────────────
# EVENTOS (EVENTS)
# ─────────────────────────────────────────

@router.post("/rooms/{room_id}/events")
async def create_event(
    room_id: int,
    event_data: dict,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Cria novo evento em uma room"""
    # Verifica se usuário é membro/admin da room
    membership = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id,
        RoomMembership.user_id == current_user.id,
        RoomMembership.role.in_(["admin", "co_admin"])
    ).first()

    if not membership:
        raise HTTPException(status_code=403, detail="Permissão negada")

    event = Event(
        room_id=room_id,
        title=event_data.get("title"),
        description=event_data.get("description"),
        start_at=datetime.fromisoformat(event_data.get("start_at")),
        end_at=datetime.fromisoformat(event_data.get("end_at")) if event_data.get("end_at") else None,
        location=event_data.get("location"),
        created_by_id=current_user.id
    )
    db.add(event)
    db.commit()

    # Tracking
    tracker = TrackingService(db)
    tracker.track_event_created = lambda: None  # Pode expandir depois

    return {"id": event.id, "status": "created"}


@router.get("/rooms/{room_id}/events")
async def get_events(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
    upcoming_only: bool = True
):
    """Lista eventos de uma room"""
    query = db.query(Event).filter(Event.room_id == room_id)

    if upcoming_only:
        query = query.filter(Event.start_at >= datetime.utcnow())

    events = query.order_by(Event.start_at).all()

    return [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "start_at": e.start_at.isoformat(),
            "end_at": e.end_at.isoformat() if e.end_at else None,
            "location": e.location,
            "created_by": e.created_by.full_name,
            "rsvp_count": len(e.rsvps),
            "going_count": len([r for r in e.rsvps if r.status == "going"])
        }
        for e in events
    ]


@router.post("/events/{event_id}/rsvp")
async def rsvp_event(
    event_id: int,
    status: str,  # going, interested, maybe, not_going
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Confirma RSVP em evento"""
    event = db.query(Event).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    # Remove RSVP anterior se existir
    existing = db.query(EventRSVP).filter(
        EventRSVP.event_id == event_id,
        EventRSVP.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)

    # Cria novo RSVP
    rsvp = EventRSVP(
        event_id=event_id,
        user_id=current_user.id,
        status=status
    )
    db.add(rsvp)
    db.commit()

    # Tracking
    tracker = TrackingService(db)
    tracker.track_rsvp_event(
        user_id=current_user.id,
        event_id=event_id,
        room_id=event.room_id,
        status=status
    )

    return {"status": "rsvp_confirmed", "rsvp_status": status}


@router.get("/events/{event_id}/rsvps")
async def get_event_rsvps(
    event_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Lista RSVPs de um evento (apenas os que estão 'going')"""
    rsvps = db.query(EventRSVP).filter(
        EventRSVP.event_id == event_id,
        EventRSVP.status == "going"
    ).all()

    return [
        {
            "user_id": r.user_id,
            "full_name": r.user.full_name,
            "profile_photo": r.user.profile_photo,
            "status": r.status,
            "rsvp_at": r.rsvp_at.isoformat()
        }
        for r in rsvps
    ]


# ─────────────────────────────────────────
# PRESENÇA ONLINE (PRESENCE)
# ─────────────────────────────────────────

@router.post("/presence/update")
async def update_presence(
    room_id: Optional[int] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Atualiza presença online do usuário"""
    # Remove presença anterior
    db.query(UserPresence).filter(
        UserPresence.user_id == current_user.id
    ).delete()

    # Registra nova presença
    presence = UserPresence(
        user_id=current_user.id,
        room_id=room_id,
        online_at=datetime.utcnow()
    )
    db.add(presence)
    db.commit()

    # Broadcast para a room
    if room_id:
        await manager.broadcast(room_id, {
            "type": "presence_update",
            "user_id": current_user.id,
            "action": "online"
        })

    return {"status": "presence_updated"}


@router.get("/rooms/{room_id}/presence")
async def get_room_presence(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Lista usuários online em uma room"""
    # Considera online se foi visto nos últimos 5 minutos
    threshold = datetime.utcnow() - timedelta(minutes=5)

    online_users = db.query(UserPresence).filter(
        UserPresence.room_id == room_id,
        UserPresence.last_seen >= threshold
    ).all()

    return [
        {
            "user_id": p.user_id,
            "full_name": p.user.full_name,
            "profile_photo": p.user.profile_photo,
            "online_at": p.online_at.isoformat()
        }
        for p in online_users
    ]


# ─────────────────────────────────────────
# REAÇÕES EM MENSAGENS (REACTIONS)
# ─────────────────────────────────────────

@router.post("/messages/{message_id}/reactions")
async def add_reaction(
    message_id: int,
    emoji: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Adiciona reação a uma mensagem"""
    message = db.query(Message).get(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")

    # Verifica se já existe
    existing = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id,
        MessageReaction.user_id == current_user.id,
        MessageReaction.emoji == emoji
    ).first()

    if existing:
        return {"status": "already_reacted"}

    # Cria reação
    reaction = MessageReaction(
        message_id=message_id,
        user_id=current_user.id,
        emoji=emoji
    )
    db.add(reaction)
    db.commit()

    # Broadcast para a room
    await manager.broadcast(message.room_id, {
        "type": "reaction_added",
        "message_id": message_id,
        "emoji": emoji,
        "user_id": current_user.id
    })

    # Tracking
    tracker = TrackingService(db)
    tracker.track_reaction_added(
        user_id=current_user.id,
        message_id=message_id,
        room_id=message.room_id,
        emoji=emoji
    )

    return {"status": "reaction_added", "emoji": emoji}


@router.delete("/messages/{message_id}/reactions/{emoji}")
async def remove_reaction(
    message_id: int,
    emoji: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Remove reação de uma mensagem"""
    reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id,
        MessageReaction.user_id == current_user.id,
        MessageReaction.emoji == emoji
    ).first()

    if not reaction:
        raise HTTPException(status_code=404, detail="Reação não encontrada")

    message = reaction.message
    db.delete(reaction)
    db.commit()

    # Broadcast
    await manager.broadcast(message.room_id, {
        "type": "reaction_removed",
        "message_id": message_id,
        "emoji": emoji,
        "user_id": current_user.id
    })

    return {"status": "reaction_removed"}


@router.get("/messages/{message_id}/reactions")
async def get_message_reactions(
    message_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Lista reações de uma mensagem"""
    reactions = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id
    ).all()

    # Agrupa por emoji
    emoji_counts = {}
    for r in reactions:
        if r.emoji not in emoji_counts:
            emoji_counts[r.emoji] = []
        emoji_counts[r.emoji].append({
            "user_id": r.user_id,
            "full_name": r.user.full_name
        })

    return {
        "message_id": message_id,
        "reactions": [
            {
                "emoji": emoji,
                "count": len(users),
                "users": users
            }
            for emoji, users in sorted(emoji_counts.items())
        ]
    }


# ─────────────────────────────────────────
# WEBSOCKET: Real-time updates
# ─────────────────────────────────────────

@router.websocket("/ws/room/{room_id}")
async def websocket_room_updates(websocket: WebSocket, room_id: int, db: Session = Depends(get_db)):
    """
    WebSocket para atualizações em tempo real de uma room
    - Reações
    - Presença
    - Mensagens novas
    """
    # Extrai user_id do query param ou token
    user_id = websocket.query_params.get("user_id")
    if not user_id:
        await websocket.close(code=4001, reason="user_id required")
        return

    user_id = int(user_id)
    await manager.connect(room_id, user_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            # Apenas retransmite para outros clientes
            if data.get("type") in ["reaction", "message", "presence"]:
                await manager.broadcast(room_id, data)

    except WebSocketDisconnect:
        manager.disconnect(room_id, user_id)
        await manager.broadcast(room_id, {
            "type": "presence_update",
            "user_id": user_id,
            "action": "offline"
        })
