from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, Float,
    DateTime, ForeignKey, Text, JSON
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


class Testimony(Base):
    """Depoimento de um ex-aluno/funcionário sobre uma instituição."""
    __tablename__ = "testimonies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    content = Column(String(500), nullable=False)
    year_attended = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    institution = relationship("Institution")


class EmailLog(Base):
    """Controle da sequência de e-mails de onboarding."""
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email_type = Column(String(50), nullable=False)   # welcome, followup_day3, followup_day7
    sent_at = Column(DateTime, default=datetime.utcnow)


class PushSubscription(Base):
    """Subscription Web Push do usuário (para notificações em background)."""
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class DMConversation(Base):
    """Conversa direta entre dois usuários."""
    __tablename__ = "dm_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("DMMessage", back_populates="conversation", order_by="DMMessage.created_at")
    user_a = relationship("User", foreign_keys=[user_a_id])
    user_b = relationship("User", foreign_keys=[user_b_id])


class DMMessage(Base):
    """Mensagem em uma conversa direta."""
    __tablename__ = "dm_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("dm_conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("DMConversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])


class Subscription(Base):
    """Stripe subscription do usuário (plano premium)."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    stripe_customer_id = Column(String(255), nullable=False, unique=True)
    stripe_subscription_id = Column(String(255), nullable=False, unique=True)
    plan = Column(String(50), default="premium")  # 'premium'
    status = Column(String(20), default="active")  # 'active', 'canceled', 'past_due'
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class LocalNews(Base):
    """Notícias locais por cidade."""
    __tablename__ = "local_news"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # breaking_news, local_event, trending_topic
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=True)
    source = Column(String(200), nullable=True)
    external_url = Column(String(500), nullable=True)
    published_at = Column(DateTime, nullable=True)
    ttl_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class LocalEvent(Base):
    """Eventos locais organizados na comunidade."""
    __tablename__ = "local_events"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    date = Column(String(20), nullable=False)  # formato: YYYY-MM-DD
    time = Column(String(20), nullable=True)   # formato: HH:MM
    location = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    event_url = Column(String(500), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="active")  # active, cancelled, completed
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    rsvps = relationship("EventRSVP", back_populates="event")


class EventRSVP(Base):
    """Confirmação de presença em eventos locais."""
    __tablename__ = "event_rsvps"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("local_events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # going, interested, not_going
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("LocalEvent", back_populates="rsvps")
    user = relationship("User", foreign_keys=[user_id])


class TrendingTopic(Base):
    """Tópicos em tendência na comunidade local."""
    __tablename__ = "trending_topics"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    hashtag = Column(String(100), nullable=False)
    mention_count = Column(Integer, default=0)
    sample_messages = Column(JSON, nullable=True)  # array de mensagens de exemplo
    trending_since = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WeeklyHighlight(Base):
    """Destaques semanais da comunidade (top mensagens, fotos, pessoas retornadas, etc)."""
    __tablename__ = "weekly_highlights"

    id = Column(Integer, primary_key=True, index=True)
    week_starting = Column(String(20), nullable=False, index=True)  # formato: YYYY-MM-DD
    category = Column(String(50), nullable=False)  # top_messages, top_photos, people_returned, new_rooms
    item_type = Column(String(50), nullable=False)  # message, photo, person, room
    item_id = Column(Integer, nullable=False)  # referência genérica (message_id, photo_id, etc)
    rank = Column(Integer, nullable=False)  # posição no ranking (1, 2, 3...)
    featured_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsDigest(Base):
    """Newsletter semanal enviada ao usuário com resumo de notícias."""
    __tablename__ = "news_digests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    week_starting = Column(String(20), nullable=False)  # formato: YYYY-MM-DD
    sent_at = Column(DateTime, nullable=True)
    news_items_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


# ═══════════════════════════════════════════════════════════════════════════════
# 8 NOVAS TABELAS - SISTEMA DE CIDADES COM DESAFIOS E RANKINGS
# ═══════════════════════════════════════════════════════════════════════════════

class City(Base):
    """Cidades brasileiras com metadados e localização."""
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True)  # "rio-de-janeiro", "sao-paulo"
    name = Column(String, index=True)
    state = Column(String)  # "RJ", "SP", "MG"
    population = Column(Integer)
    nickname = Column(String, nullable=True)  # "Cidade Maravilhosa", "Rainha da Borborema"
    landmark_image = Column(String, nullable=True)
    coordinates = Column(JSON)  # {"latitude": float, "longitude": float}
    created_at = Column(DateTime, default=datetime.utcnow)

    local_tips = relationship("LocalTip", back_populates="city", cascade="all, delete-orphan")
    challenges = relationship("CityChallenge", back_populates="city", cascade="all, delete-orphan")
    badges = relationship("CityBadge", back_populates="city", cascade="all, delete-orphan")
    pois = relationship("LocalPOI", back_populates="city", cascade="all, delete-orphan")
    leaderboards = relationship("CityLeaderboard", back_populates="city", cascade="all, delete-orphan")


class LocalTip(Base):
    """Dica local sobre um lugar na cidade, submetida por usuário."""
    __tablename__ = "local_tips"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, index=True)
    description = Column(Text)
    location = Column(String)
    rating = Column(Float, default=0.0)  # 0-5
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    city = relationship("City", back_populates="local_tips")
    user = relationship("User", foreign_keys=[user_id])


class CityChallenge(Base):
    """Desafio local para engajar usuários em cidades."""
    __tablename__ = "city_challenges"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    title = Column(String, index=True)
    description = Column(Text)
    reward_points = Column(Integer, default=100)
    difficulty = Column(String)  # "facil", "medio", "dificil"
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    city = relationship("City", back_populates="challenges")
    submissions = relationship("ChallengeSubmission", back_populates="challenge", cascade="all, delete-orphan")


class ChallengeSubmission(Base):
    """Submissão de um usuário para um desafio local."""
    __tablename__ = "challenge_submissions"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("city_challenges.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    photo_url = Column(String)
    approved = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)

    challenge = relationship("CityChallenge", back_populates="submissions")
    user = relationship("User", foreign_keys=[user_id])


class CityBadge(Base):
    """Badge ou conquista do usuário relacionada a cidade."""
    __tablename__ = "city_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_type = Column(String, index=True)  # "explorador", "foodie", "cultural"
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow, index=True)

    city = relationship("City", back_populates="badges")
    user = relationship("User", foreign_keys=[user_id])


class LocalPOI(Base):
    """Ponto de Interesse (POI) - lugar notável na cidade."""
    __tablename__ = "local_pois"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    name = Column(String, index=True)
    type = Column(String)  # "restaurant", "park", "museum", "landmark", "beach"
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    city = relationship("City", back_populates="pois")


class CityLeaderboard(Base):
    """Leaderboard de engajamento de usuários por cidade."""
    __tablename__ = "city_leaderboards"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    engagement_score = Column(Float, default=0.0)
    rank = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    city = relationship("City", back_populates="leaderboards")
    user = relationship("User", foreign_keys=[user_id])


class UserStreak(Base):
    """Controle de sequência de atividades do usuário."""
    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class CityNews(Base):
    """Notícias sobre cidades - posts e atualizações relevantes."""
    __tablename__ = "city_news"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    title = Column(String, nullable=False, index=True)
    content = Column(Text)
    source = Column(String)
    published_at = Column(DateTime, default=datetime.utcnow, index=True)
    views = Column(Integer, default=0)
    engagement_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    city = relationship("City", foreign_keys=[city_id])


class CityEvent(Base):
    """Eventos locais em cidades - shows, feiras, competições."""
    __tablename__ = "city_events"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    location = Column(String)
    category = Column(String)  # cultural, esporte, gastronomia, etc
    date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    attendees = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    city = relationship("City", foreign_keys=[city_id])


# ═══════════════════════════════════════════════════════════════════════════════
# 8 NEW FEATURES - DATABASE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class UserOAuthToken(Base):
    """OAuth Tokens for Google Calendar and Microsoft Outlook integration."""
    __tablename__ = "user_oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # "google", "microsoft"
    access_token = Column(String(1000), nullable=False)
    refresh_token = Column(String(1000), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class EducationalEvent(Base):
    """Educational events: workshops, webinars, courses."""
    __tablename__ = "educational_events"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    teacher_name = Column(String(200), nullable=True)
    type = Column(String(50), nullable=True)  # "webinar", "workshop", "course"
    date = Column(String(10), nullable=True)  # formato: YYYY-MM-DD
    time = Column(String(5), nullable=True)   # formato: HH:MM
    location = Column(String(500), nullable=True)
    max_participants = Column(Integer, nullable=True)
    enrolled = Column(Integer, default=0)
    is_free = Column(Boolean, default=True)
    price = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(200), nullable=True)

    city = relationship("City", foreign_keys=[city_id])


class EducationalEnrollment(Base):
    """User enrollment in educational events."""
    __tablename__ = "educational_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("educational_events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("EducationalEvent", foreign_keys=[event_id])
    user = relationship("User", foreign_keys=[user_id])


class TouristAttraction(Base):
    """Tourist attractions, hotels, restaurants in cities."""
    __tablename__ = "tourist_attractions"

    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=True)  # "attraction", "hotel", "restaurant", "museum"
    description = Column(Text, nullable=True)
    rating = Column(Float, default=0.0)
    address = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    website = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    city = relationship("City", foreign_keys=[city_id])


class ShareAnalytic(Base):
    """Tracking for social sharing analytics."""
    __tablename__ = "share_analytics"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=True)  # "news", "event", "attraction"
    content_id = Column(Integer, nullable=True)
    platform = Column(String(50), nullable=True)  # "whatsapp", "facebook", "twitter", "linkedin"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
