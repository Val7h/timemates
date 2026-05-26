from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, ForeignKey, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

import os

_db_url = os.getenv("DATABASE_URL", "sqlite:///./timeMates.db")
# Render fornece postgres://, SQLAlchemy 2 exige postgresql://
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = _db_url

def _make_engine():
    url = SQLALCHEMY_DATABASE_URL
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    try:
        from sqlalchemy.pool import NullPool
        import ssl as _ssl
        # Converte para dialeto pg8000 (Python puro, sem dependências C)
        pg8000_url = url.replace("postgresql://", "postgresql+pg8000://", 1)
        pg8000_url = pg8000_url.replace("postgres://", "postgresql+pg8000://", 1)
        # Remove parâmetros SSL da URL (pg8000 usa connect_args)
        if "?" in pg8000_url:
            pg8000_url = pg8000_url.split("?")[0]
        # Configura SSL para Neon
        ssl_ctx = _ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = _ssl.CERT_NONE
        print(f"[DB] Conectando com pg8000 em {pg8000_url[:40]}...")
        return create_engine(
            pg8000_url,
            poolclass=NullPool,
            connect_args={"ssl_context": ssl_ctx},
        )
    except Exception as e:
        print(f"[DB] PostgreSQL engine falhou ({e}), usando SQLite fallback")
        return create_engine("sqlite:///./fallback.db",
                             connect_args={"check_same_thread": False})

engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    cpf_hash = Column(String(200), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    phone_verified = Column(Boolean, default=False)
    profile_photo = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    profession = Column(String(100), nullable=True)
    bio = Column(String(500), nullable=True)
    show_city = Column(Boolean, default=True)
    show_profession = Column(Boolean, default=True)
    show_bio = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    is_system_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    memberships = relationship("RoomMembership", foreign_keys="RoomMembership.user_id", back_populates="user")
    messages = relationship("Message", back_populates="user")
    photos = relationship("Photo", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(300), nullable=False)
    type = Column(String(50), nullable=False)  # school, university, city, company
    state = Column(String(2), nullable=True)
    city = Column(String(100), nullable=True)
    neighborhood = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    approved = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    suggested_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rooms = relationship("Room", back_populates="institution")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    year = Column(Integer, nullable=False)
    group_name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="rooms")
    memberships = relationship("RoomMembership", back_populates="room")
    messages = relationship("Message", back_populates="room")
    photos = relationship("Photo", back_populates="room")
    remembered_persons = relationship("RememberedPerson", back_populates="room")
    invite_links = relationship("InviteLink", back_populates="room")


class RoomMembership(Base):
    __tablename__ = "room_memberships"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")   # member, admin, co_admin
    status = Column(String(20), default="pending") # pending, approved, rejected
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    room = relationship("Room", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id], back_populates="memberships")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="messages")
    user = relationship("User", back_populates="messages")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    caption = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="photos")
    user = relationship("User", back_populates="photos")


class RememberedPerson(Base):
    __tablename__ = "remembered_persons"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    full_name = Column(String(200), nullable=False)
    nickname = Column(String(100), nullable=True)
    description = Column(String(1000), nullable=True)
    matched_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmations = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="remembered_persons")


class RememberedPersonConfirmation(Base):
    __tablename__ = "remembered_person_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    remembered_person_id = Column(Integer, ForeignKey("remembered_persons.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class InviteLink(Base):
    __tablename__ = "invite_links"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(100), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    max_uses = Column(Integer, default=500)
    use_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="invite_links")


class MessageReaction(Base):
    """Reações emocionais em mensagens do chat."""
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reaction = Column(String(20), nullable=False)  # saudade | classico | eu_tava_la | inesquecivel
    created_at = Column(DateTime, default=datetime.utcnow)


class CurrentStudent(Base):
    """Aluno/funcionário atualmente na instituição (mural atual)."""
    __tablename__ = "current_students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    entry_year = Column(Integer, nullable=True)          # ano de entrada
    grade_or_period = Column(String(150), nullable=True) # "3º Ano", "Eng. Civil - 5º sem."
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    institution = relationship("Institution")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(String(500), nullable=False)
    read = Column(Boolean, default=False)
    related_room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
