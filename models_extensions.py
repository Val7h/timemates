"""
Extensões ao database.py para suportar:
- Notificações
- Presença online
- Reações em mensagens
- Eventos
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, ForeignKey, Text, JSON, Float
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = __import__('database').Base


class Event(Base):
    """Modelo para eventos associados a rooms"""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=True)
    location = Column(String(300), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", foreign_keys=[room_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    rsvps = relationship("EventRSVP", back_populates="event")


class EventRSVP(Base):
    """Modelo para RSVPs em eventos"""
    __tablename__ = "event_rsvps"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="interested")  # interested, going, maybe, not_going
    rsvp_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="rsvps")
    user = relationship("User", foreign_keys=[user_id])


class Notification(Base):
    """Notificações do sistema para usuários"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # breaking_news, event_reminder, weekly_digest, message, reaction
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, default={})  # { event_id, room_id, message_id, etc }
    is_read = Column(Boolean, default=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class PushSubscription(Base):
    """Web Push API subscriptions para notificações"""
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    endpoint = Column(String(500), nullable=False, unique=True)
    p256dh = Column(String(300), nullable=False)
    auth = Column(String(300), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class UserPresence(Base):
    """Presença online em tempo real"""
    __tablename__ = "user_presence"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)  # NULL = online em geral
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    online_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    room = relationship("Room", foreign_keys=[room_id])


class MessageReaction(Base):
    """Reações em mensagens (emojis)"""
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    emoji = Column(String(10), nullable=False)  # 👍, ❤️, 🔥, 😂, etc
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", foreign_keys=[message_id])
    user = relationship("User", foreign_keys=[user_id])


class News(Base):
    """Notícias do sistema (para breaking news alerts)"""
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    priority = Column(String(20), default="normal")  # low, normal, high, breaking
    published_at = Column(DateTime, default=datetime.utcnow)
    published_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    published_by = relationship("User", foreign_keys=[published_by_id])


class EmailLog(Base):
    """Log de emails enviados (para rastreamento)"""
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String(200), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # weekly_digest, event_reminder, etc
    status = Column(String(20), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
