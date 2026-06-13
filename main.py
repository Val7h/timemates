import os
import sys
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Centralized UTF-8 stdout/stderr reconfiguration (fixes São Paulo/Brasília accent bugs on Windows)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ===== SENTRY INTEGRATION (graceful degradation) =====
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "production"),
            release=os.getenv("GIT_SHA", "unknown"),
            send_default_pii=False,
            attach_stacktrace=True,
        )
        print("[SENTRY] Initialized successfully")
    except Exception as e:
        print(f"[SENTRY] Failed to initialize: {e}")
else:
    print("[SENTRY] No DSN configured, error tracking disabled")

# ===== POSTHOG ANALYTICS (graceful degradation) =====
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")
posthog_client = None
if POSTHOG_API_KEY:
    try:
        from posthog import Posthog
        posthog_client = Posthog(
            project_api_key=POSTHOG_API_KEY,
            host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"),
        )
        print("[POSTHOG] Analytics initialized")
    except Exception as e:
        print(f"[POSTHOG] Failed to initialize: {e}")
else:
    print("[POSTHOG] No API key configured, analytics disabled")

def track_event(user_id, event_name, properties=None):
    if posthog_client and user_id:
        try:
            posthog_client.capture(
                distinct_id=str(user_id),
                event=event_name,
                properties=properties or {}
            )
        except Exception:
            pass  # Silent fail to never block requests

# Stripe
import stripe
from fastapi import Request

# Carrega .env se existir (sem dependência externa)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _ef:
        for _line in _ef:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

import email_service as mail

from fastapi import (
    FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect,
    UploadFile, File, Form, Query
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import (
    get_db, Base, engine, SessionLocal,
    User, Institution, Room, RoomMembership, Message,
    Photo, RememberedPerson, RememberedPersonConfirmation,
    InviteLink, Notification, CurrentStudent, MessageReaction,
    Testimony, EmailLog, PushSubscription, DMConversation, DMMessage, Subscription,
    City, LocalEvent, EventRSVP, LocalNews,
    Turma, TurmaMembership, TurmaVouch, MuralMemory,
    UserTurmaVisibility,
)
from auth import (
    get_current_user, get_current_user_required,
    hash_password, verify_password, create_access_token, validate_cpf,
    require_18_plus, calculate_age,
)
from billing_routes import router as billing_router
from mural_routes import mural_router
from reuniao_routes import reuniao_router

# ===== NEW FEATURE IMPORTS =====
# Swagger Documentation
try:
    from features_implementations.swagger_setup import setup_swagger
except Exception:
    logger.exception('Feature loader failed: %s', 'swagger_setup')
    print(f'[FEATURE] Failed to load: swagger_setup')
    def setup_swagger(app): pass

# Push Notifications
try:
    from features_implementations.push_notifications import setup_push_notifications
except Exception:
    logger.exception('Feature loader failed: %s', 'push_notifications')
    print(f'[FEATURE] Failed to load: push_notifications')
    def setup_push_notifications(app): pass

# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# Calendar Integration (Google & Outlook)
# try:
#     from features_implementations.calendar_integration import setup_calendar_integration
# except Exception:
#     logger.exception('Feature loader failed: %s', 'calendar_integration')
#     print(f'[FEATURE] Failed to load: calendar_integration')
#     def setup_calendar_integration(app): pass
def setup_calendar_integration(app): pass  # DEPRECATED V2 PIVOT stub

# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# Educational Section
# try:
#     from features_implementations.education_section import setup_education_section
# except Exception:
#     logger.exception('Feature loader failed: %s', 'education_section')
#     print(f'[FEATURE] Failed to load: education_section')
#     def setup_education_section(app): pass
def setup_education_section(app): pass  # DEPRECATED V2 PIVOT stub

# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# Tourism Data & Distance Calculation
# try:
#     from features_implementations.tourism_data import setup_tourism_section
# except Exception:
#     logger.exception('Feature loader failed: %s', 'tourism_data')
#     print(f'[FEATURE] Failed to load: tourism_data')
#     def setup_tourism_section(app): pass
def setup_tourism_section(app): pass  # DEPRECATED V2 PIVOT stub

# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# Social Sharing
# try:
#     from features_implementations.social_sharing import setup_social_sharing
# except Exception:
#     logger.exception('Feature loader failed: %s', 'social_sharing')
#     print(f'[FEATURE] Failed to load: social_sharing')
#     def setup_social_sharing(app): pass
def setup_social_sharing(app): pass  # DEPRECATED V2 PIVOT stub

# ===== END NEW FEATURE IMPORTS =====

# Register reconnect_requests table with Base metadata so create_all picks it
# up. Importing for side-effect — the routes module is loaded separately
# further down (see "Reconnect Routes" block).
try:
    import reconnect_models  # noqa: F401  (side-effect: registers ORM table)
except Exception as _e:
    print(f"[FEATURE] reconnect_models import failed: {_e}")

try:
    Base.metadata.create_all(bind=engine)
except Exception as _e:
    print(f"[DB] create_all erro: {_e}")

# Indexes para escalar /api/cities até 300+ cidades (idempotente, ambos SQLite e Postgres)
try:
    from sqlalchemy import text as _idx_text
    with engine.connect() as _conn:
        for _idx_sql in (
            "CREATE INDEX IF NOT EXISTS ix_cities_state ON cities (state)",
            "CREATE INDEX IF NOT EXISTS ix_cities_population ON cities (population)",
            "CREATE INDEX IF NOT EXISTS ix_cities_state_population ON cities (state, population)",
        ):
            try:
                _conn.execute(_idx_text(_idx_sql))
            except Exception as _idx_e:
                print(f"[DB] index erro ({_idx_sql}): {_idx_e}")
        try:
            _conn.commit()
        except Exception:
            pass
    print("[DB] indexes cities (state, population) garantidos")
except Exception as _e:
    print(f"[DB] index creation skipped: {_e}")

from contextlib import asynccontextmanager

def _generate_icons():
    """Gera ícones PWA (192x192 e 512x512)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        for size in (192, 512):
            path = f"static/icon-{size}.png"
            if os.path.exists(path):
                continue
            img = Image.new("RGB", (size, size), "#1E3A5F")
            draw = ImageDraw.Draw(img)
            # Círculo interno dourado
            pad = size // 8
            draw.ellipse([pad, pad, size-pad, size-pad], fill="#D4A853")
            # Letra T centralizada
            try:
                font = ImageFont.truetype("arial.ttf", size // 2)
            except Exception:
                font = ImageFont.load_default()
            draw.text((size//2, size//2), "T", font=font, fill="#1E3A5F", anchor="mm")
            img.save(path, "PNG")
        print("[PWA] Ícones gerados")
    except Exception as e:
        print(f"[PWA] Ícones: {e}")


def _generate_og_image():
    """Gera og-card.png para Open Graph (WhatsApp/Facebook preview)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        W, H = 1200, 630
        img = Image.new("RGB", (W, H), "#1E3A5F")
        draw = ImageDraw.Draw(img)

        # Fundo degradê manual
        for i in range(H):
            r = int(0x1E + (0x2A - 0x1E) * i / H)
            g = int(0x3A + (0x50 - 0x3A) * i / H)
            b = int(0x5F + (0x8A - 0x5F) * i / H)
            draw.line([(0, i), (W, i)], fill=(r, g, b))

        # Retângulo decorativo dourado
        draw.rectangle([60, 60, W-60, H-60], outline="#D4A853", width=4)
        draw.rectangle([80, 80, W-80, H-80], outline="#D4A853", width=1)

        # Textos
        try:
            fn_big  = ImageFont.truetype("arial.ttf", 96)
            fn_sub  = ImageFont.truetype("arial.ttf", 42)
            fn_tiny = ImageFont.truetype("arial.ttf", 30)
        except Exception:
            fn_big = fn_sub = fn_tiny = ImageFont.load_default()

        # "TimeMates"
        draw.text((W//2, 220), "TimeMates", font=fn_big, fill="#ffffff", anchor="mm")
        # Destaque dourado na segunda parte
        tm_w = draw.textlength("Time", font=fn_big)
        draw.text((W//2 + tm_w//2 - draw.textlength("Mates", font=fn_big)//2, 220),
                  "Mates", font=fn_big, fill="#D4A853", anchor="mm")

        draw.text((W//2, 340), "O mapa das pessoas que cruzaram sua vida", font=fn_sub, fill="rgba(255,255,255,180)", anchor="mm")
        draw.text((W//2, 500), "timemates.onrender.com", font=fn_tiny, fill="#D4A853", anchor="mm")

        os.makedirs("static", exist_ok=True)
        img.save("static/og-card.png", "PNG", optimize=True)
        print("[OG] og-card.png gerado com sucesso")
    except Exception as e:
        print(f"[OG] Nao foi possivel gerar og-card.png: {e}")


@asynccontextmanager
async def lifespan(app):
    # ===== SETUP 8 FEATURES =====
    # Feature 1: Swagger Documentation
    try:
        setup_swagger(app)
        print("[FEATURE] Swagger Documentation setup completed")
    except Exception as e:
        print(f"[FEATURE] Swagger setup failed (non-critical): {e}")

    # Feature 2: Push Notifications
    try:
        setup_push_notifications(app)
        print("[FEATURE] Push Notifications setup completed")
    except Exception as e:
        print(f"[FEATURE] Push Notifications setup failed (non-critical): {e}")

    # DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
    # Will be removed after Phase 1 if no use case emerges
    # Feature 3 & 4: Calendar Integration (Google & Outlook)
    # try:
    #     setup_calendar_integration(app)
    #     print("[FEATURE] Calendar Integration setup completed")
    # except Exception as e:
    #     print(f"[FEATURE] Calendar Integration setup failed (non-critical): {e}")

    # DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
    # Will be removed after Phase 1 if no use case emerges
    # Feature 5: Educational Section
    # try:
    #     setup_education_section(app)
    #     print("[FEATURE] Educational Section setup completed")
    # except Exception as e:
    #     print(f"[FEATURE] Educational Section setup failed (non-critical): {e}")

    # DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
    # Will be removed after Phase 1 if no use case emerges
    # Feature 6, 8: Tourism Data & Distance Calculation
    # try:
    #     setup_tourism_section(app)
    #     print("[FEATURE] Tourism Data setup completed")
    # except Exception as e:
    #     print(f"[FEATURE] Tourism Data setup failed (non-critical): {e}")

    # DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
    # Will be removed after Phase 1 if no use case emerges
    # Feature 7: Social Sharing
    # try:
    #     setup_social_sharing(app)
    #     print("[FEATURE] Social Sharing setup completed")
    # except Exception as e:
    #     print(f"[FEATURE] Social Sharing setup failed (non-critical): {e}")
    # ===== END FEATURE SETUP =====

    _generate_icons()
    _generate_og_image()
    try:
        from seed_all import seed_db
        db = SessionLocal()
        try:
            seed_db(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[SEED] Erro no startup (nao critico): {e}")

    try:
        from seed_demo import seed_demo
        db = SessionLocal()
        try:
            seed_demo(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[DEMO] Erro no startup (nao critico): {e}")

    # Sequência de e-mails de onboarding (roda no startup)
    # EMERGENCY DISABLED 2026-06-07: estava bombardeando o inbox do founder com
    # bounces para usuários seed (@campinagrandeseed.local etc.).
    # Reativar apenas após: (1) sanitizar usuários seed do DB, (2) revisar template
    # "Seus ex-colegas estão esperando por você" (contradiz POSITIONING.md — somos
    # EVENTOS, não reconexão), (3) setar EMAIL_ENABLED=true conscientemente.
    if os.getenv("EMAIL_SEQUENCE_ENABLED", "false").lower() == "true":
        try:
            _run_email_sequence()
        except Exception as e:
            print(f"[EMAIL_SEQ] Erro (nao critico): {e}")
    else:
        print("[EMAIL_SEQ] DISABLED (EMAIL_SEQUENCE_ENABLED!=true) — emergency stop active")

    # ─── LGPD: nightly purge of soft-deleted tunel uploads (>30d) + cool-off
    # ─── account deletions (>7d after request, not cancelled).
    # Gated by PURGE_ENABLED so local/staging doesn't accidentally hard-delete
    # while we're still debugging the deletion UX.
    _tunel_purge_scheduler = None
    if os.getenv("PURGE_ENABLED", "false").lower() == "true":
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from tunel_purge import (
                purge_deleted_uploads,
                purge_pending_account_deletions,
            )
            _tunel_purge_scheduler = BackgroundScheduler(timezone="UTC")
            _tunel_purge_scheduler.add_job(
                purge_deleted_uploads, 'cron', hour=3, minute=0,
                id='tunel_purge_uploads', replace_existing=True,
            )
            _tunel_purge_scheduler.add_job(
                purge_pending_account_deletions, 'cron', hour=3, minute=15,
                id='lgpd_purge_accounts', replace_existing=True,
            )
            _tunel_purge_scheduler.start()
            app.state.tunel_purge_scheduler = _tunel_purge_scheduler
            print("[CRON] LGPD purge scheduler started (daily 03:00 UTC)")
        except Exception as e:
            print(f"[CRON] Failed to start LGPD purge scheduler: {e}")
    else:
        print("[CRON] LGPD purge DISABLED (PURGE_ENABLED!=true)")

    yield

    # Graceful shutdown of background jobs so SIGTERM doesn't leave the
    # scheduler thread alive on Render redeploys.
    if _tunel_purge_scheduler is not None:
        try:
            _tunel_purge_scheduler.shutdown(wait=False)
        except Exception:
            pass


def _run_email_sequence():
    """Envia follow-up emails para usuários que ainda não os receberam.

    Defense-in-depth (post-incident 2026-06-07):
    1. EMAIL_SEQUENCE_ENABLED env gate (checked by lifespan caller).
    2. EMAIL_ENABLED kill-switch (enforced inside email_service._send).
    3. email_service._is_sendable domain/TLD/name allowlist.
    4. SQL-level email_opt_out filter (this function).
    5. Hard-coded seed/demo domain skip below.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Skip opt-outs at the query level when the column exists. Tolerate
        # legacy DBs without the column by falling back to a name-based query.
        from sqlalchemy import text as _seq_text
        try:
            users = db.execute(
                _seq_text(
                    "SELECT id, email, full_name, created_at FROM users "
                    "WHERE is_active = TRUE "
                    "AND COALESCE(email_opt_out, FALSE) = FALSE"
                )
            ).fetchall()
        except Exception:
            db.rollback()
            users = [
                (u.id, u.email, u.full_name, u.created_at)
                for u in db.query(User).filter(User.is_active == True).all()
            ]
        sent = 0
        for uid, uemail, ufullname, ucreated_at in users:
            # Ignora contas demo / seed obviamente falsas (defesa em profundidade)
            elower = (uemail or "").lower()
            if (
                "@demo.timemates" in elower
                or "@seed" in elower
                or elower.endswith(".local")
                or elower.endswith(".test")
                or elower.endswith(".invalid")
                or elower.endswith(".example")
                or "campinagrandeseed" in elower
            ):
                continue
            days_since = (now - ucreated_at).days
            already_sent = {
                log.email_type
                for log in db.query(EmailLog).filter(EmailLog.user_id == uid).all()
            }
            if days_since >= 3 and "followup_day3" not in already_sent:
                mail.send_followup_day3(uemail, ufullname)
                db.add(EmailLog(user_id=uid, email_type="followup_day3"))
                sent += 1
            if days_since >= 7 and "followup_day7" not in already_sent:
                mail.send_followup_day7(uemail, ufullname)
                db.add(EmailLog(user_id=uid, email_type="followup_day7"))
                sent += 1
        if sent:
            db.commit()
            print(f"[EMAIL_SEQ] {sent} email(s) de follow-up enviados")
        else:
            print("[EMAIL_SEQ] Nenhum email enviado (todos filtrados/já recebidos)")
    finally:
        db.close()

app = FastAPI(title="TimeMates API", version="1.0.0", lifespan=lifespan)

# ===== RATE LIMITING SETUP =====
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

RATE_LIMITS = {
    'auth': '5/minute',
    'messages': '100/minute',
    'search': '50/minute',
    'general': '200/minute'
}

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return {"error": "rate_limit_exceeded", "message": "Muitos requests. Tente novamente em 1 minuto.", "retry_after": 60}

# ===== SENTRY TEST ENDPOINT (only active if SENTRY_DSN is set) =====
if SENTRY_DSN:
    @app.get("/api/debug/sentry-test")
    async def sentry_test():
        """Trigger an exception to verify Sentry integration. Only active when SENTRY_DSN is configured."""
        raise RuntimeError("Sentry test exception - this is intentional to verify error tracking is working")

# Stripe Setup
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Tokens de recuperação de senha: { token: {"user_id": int, "expires": datetime} }
_reset_tokens: Dict[str, dict] = {}

_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
    _cors_allow_credentials = True
else:
    # Safe default: wildcard origin requires credentials=False per CORS spec.
    # Set CORS_ALLOWED_ORIGINS env to enable credentialed requests from a strict allowlist.
    _cors_origins = ["*"]
    _cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para garantir encoding UTF-8 correto
@app.middleware("http")
async def add_utf8_header(request, call_next):
    response = await call_next(request)
    # Só adiciona charset se for JSON
    if "application/json" in response.headers.get("content-type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    elif "text/html" in response.headers.get("content-type", ""):
        response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

os.makedirs("uploads/photos", exist_ok=True)
os.makedirs("uploads/avatars", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static_files")

# ─── Billing Routes (Stripe) ──────────────────────────────────────────────────
app.include_router(billing_router)

# ─── Mural da Saudade Routes (memorias sensoriais coletivas) ──────────────────
app.include_router(mural_router)

# ─── Reunião Button Routes (turma churrasco/dinner organizer) ────────────────
app.include_router(reuniao_router)

# ─── Túnel do Tempo Routes (old photo upload + face detection foundation) ─────
try:
    import tunel_routes as _tunel_mod
    # Inject the slowapi limiter BEFORE include_router so per-user rate limits
    # (5/day upload, 30/min faces, 10/day matches, etc.) attach to each route.
    # See tunel_routes._LimiterProxy for the deferred-decoration mechanism.
    _tunel_mod.attach_limiter(limiter, app)
    app.include_router(_tunel_mod.tunel_router)
    os.makedirs("uploads/tunel", exist_ok=True)
    print("[FEATURE] tunel routes registered (rate-limited per-user)")
except Exception:
    logger.exception("Feature loader failed: %s", "tunel_routes")
    print("[FEATURE] Failed to load: tunel_routes")

# ─── Reconnect Routes (asymmetric reveal) ─────────────────────────────────────
# Phase 1 spec: 5/day per-user rate limit, opaque responses, silent decline,
# 365-day cooling-off, WhatsApp deeplink on accept. See reconnect_routes.py.
try:
    import reconnect_routes
    reconnect_routes.register_routes(app, limiter)
    print("[FEATURE] reconnect routes registered")
except Exception:
    logger.exception("Feature loader failed: %s", "reconnect_routes")
    print("[FEATURE] Failed to load: reconnect_routes")

# ─── WebSocket Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[int, List[WebSocket]] = {}
        self.online_users: Dict[int, Dict[int, dict]] = {}  # room_id -> {user_id -> user_data}

    async def connect(self, ws: WebSocket, room_id: int, user_id: int = None, user: User = None):
        await ws.accept()
        self.connections.setdefault(room_id, []).append(ws)

        # Se user_id e user foram fornecidos, rastreia como online
        if user_id is not None and user is not None:
            if room_id not in self.online_users:
                self.online_users[room_id] = {}
            self.online_users[room_id][user_id] = {
                "id": user_id,
                "name": user.full_name,
                "avatar": "👤",
                "color": self._get_user_color(user_id),
            }

    def disconnect(self, ws: WebSocket, room_id: int, user_id: int = None):
        if room_id in self.connections:
            try:
                self.connections[room_id].remove(ws)
            except ValueError:
                pass

        # Remove usuário online se não houver mais conexões WebSocket dele nesta sala
        if user_id is not None and room_id in self.online_users and user_id in self.online_users[room_id]:
            # Verifica se ainda há conexões ativas nesta sala
            active_conns = len(self.connections.get(room_id, []))
            if active_conns == 0:
                if user_id in self.online_users[room_id]:
                    del self.online_users[room_id][user_id]
                if not self.online_users[room_id]:
                    del self.online_users[room_id]

    def get_online_users(self, room_id: int) -> List[dict]:
        """Retorna lista de usuários online em uma sala."""
        return list(self.online_users.get(room_id, {}).values())

    def _get_user_color(self, user_id: int) -> str:
        """Gera uma cor consistente baseada no user_id."""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#52BE80"
        ]
        return colors[user_id % len(colors)]

    async def broadcast(self, data: dict, room_id: int):
        for ws in list(self.connections.get(room_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                pass

    async def broadcast_online_users(self, room_id: int):
        """Envia lista atualizada de usuários online para todos na sala."""
        users_list = self.get_online_users(room_id)
        await self.broadcast({
            "type": "online_users",
            "users": users_list,
            "timestamp": datetime.utcnow().isoformat(),
        }, room_id)


manager = ConnectionManager()


# ─── DM WebSocket Manager ─────────────────────────────────────────────────────

class DMManager:
    """Gerencia conexões WebSocket para mensagens diretas (por user_id)."""
    def __init__(self):
        self.connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket, user_id: int):
        await ws.accept()
        self.connections.setdefault(user_id, []).append(ws)

    def disconnect(self, ws: WebSocket, user_id: int):
        if user_id in self.connections:
            try:
                self.connections[user_id].remove(ws)
            except ValueError:
                pass

    async def send_to_user(self, data: dict, user_id: int):
        for ws in list(self.connections.get(user_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                pass


dm_manager = DMManager()


# ─── VAPID / Web Push ─────────────────────────────────────────────────────────

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL       = os.getenv("VAPID_EMAIL", "admin@timemates.onrender.com")
_VAPID_FILE = os.path.join(os.path.dirname(__file__), "vapid_keys.json")

def _ensure_vapid():
    global VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY
    if VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY:
        return
    if os.path.exists(_VAPID_FILE):
        try:
            d = json.loads(open(_VAPID_FILE).read())
            VAPID_PRIVATE_KEY = d["private"]
            VAPID_PUBLIC_KEY  = d["public"]
            print(f"[PUSH] Loaded VAPID keys from file")
            return
        except Exception:
            pass
    try:
        import base64
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        from py_vapid import Vapid
        v = Vapid()
        v.generate_keys()
        VAPID_PRIVATE_KEY = v.private_pem().decode()
        # Converte EC key object → base64url string (necessário para JSON + frontend)
        raw_pub = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        VAPID_PUBLIC_KEY = base64.urlsafe_b64encode(raw_pub).decode("utf-8").rstrip("=")
        with open(_VAPID_FILE, "w") as f:
            json.dump({"private": VAPID_PRIVATE_KEY, "public": VAPID_PUBLIC_KEY}, f)
        print(f"[PUSH] Generated VAPID. Public key: {VAPID_PUBLIC_KEY[:30]}...")
    except Exception as e:
        print(f"[PUSH] VAPID setup failed: {e}. Push notifications disabled.")

_ensure_vapid()


def _send_push(subscription: PushSubscription, title: str, body: str, url: str = "/"):
    """Envia push notification de forma síncrona (chame em thread separada se necessário)."""
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        return
    try:
        from pywebpush import webpush, WebPushException
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
        )
    except Exception as e:
        print(f"[PUSH] Send error: {e}")


def _push_to_user(db: Session, user_id: int, title: str, body: str, url: str = "/"):
    """Envia push para todas as subscriptions de um usuário."""
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all()
    for s in subs:
        _send_push(s, title, body, url)


BASE_URL = os.getenv("BASE_URL", "https://timemates.onrender.com")
GOOGLE_ANALYTICS_ID = os.getenv("GOOGLE_ANALYTICS_ID", "")


# ─── Debug / Health ──────────────────────────────────────────────────────────

@app.get("/api/health")
@app.get("/health")
def health_check():
    """Verifica saúde da aplicação e conexão com o banco.

    Used by UptimeRobot for production monitoring. Returns:
      - status: "ok" if DB is reachable, "degraded" otherwise
      - timestamp: current UTC time (ISO 8601)
      - version: git SHA if exposed via GIT_SHA env var
      - database_connected: bool
    """
    from sqlalchemy import text as sa_text
    dialect = engine.dialect.name
    try:
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("GIT_SHA", "unknown"),
        "database_connected": db_ok,
        "db": dialect,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "full_name": u.full_name,
        "email": u.email,
        "phone": u.phone,
        "profile_photo": u.profile_photo,
        "city": u.city if u.show_city else None,
        "profession": u.profession if u.show_profession else None,
        "bio": u.bio if u.show_bio else None,
        "show_city": u.show_city,
        "show_profession": u.show_profession,
        "show_bio": u.show_bio,
        "is_system_admin": u.is_system_admin,
        "created_at": u.created_at.isoformat(),
    }


def require_admin(current_user: User = Depends(get_current_user_required)):
    if not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user


def get_membership(room_id: int, user: User, db: Session, require_approved=True) -> RoomMembership:
    m = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id,
        RoomMembership.user_id == user.id,
    ).first()
    if require_approved and (not m or m.status != "approved"):
        raise HTTPException(status_code=403, detail="Sem acesso a esta sala")
    return m


# ─── Busca de pessoas ────────────────────────────────────────────────────────

@app.get("/api/users/search")
def search_users(
    q: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Busca pública por usuários — enforces default-ghost.

    Só retorna usuários que explicitamente fizeram opt-in via
    is_discoverable=TRUE e que não estão em ghost_mode_global.
    """
    if len(q.strip()) < 2:
        return []
    limit = min(limit, 50)
    users = (
        db.query(User)
        .filter(
            User.full_name.ilike(f"%{q.strip()}%"),
            User.is_active == True,
            User.is_discoverable == True,        # default-ghost enforcement
            User.ghost_mode_global == False,     # panic toggle respected
        )
        .limit(limit).all()
    )
    return [{
        "id": u.id,
        "full_name": u.full_name,
        "profile_photo": u.profile_photo,
        "city": u.city if u.show_city else None,
        "profession": u.profession if u.show_profession else None,
    } for u in users]


# ─── Preview público da sala ──────────────────────────────────────────────────

@app.get("/api/rooms/{room_id}/preview")
def room_preview(room_id: int, db: Session = Depends(get_db)):
    """Informações públicas de uma sala — sem necessidade de login."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    approved = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "approved"
    ).count()
    photo_count = db.query(Photo).filter(Photo.room_id == room_id).count()
    last_msg = (
        db.query(Message).filter(Message.room_id == room_id)
        .order_by(Message.created_at.desc()).first()
    )
    return {
        "id": room.id,
        "year": room.year,
        "group_name": room.group_name,
        "description": room.description,
        "institution_name": room.institution.name if room.institution else "",
        "member_count": approved,
        "photo_count": photo_count,
        "last_activity": (last_msg.created_at if last_msg else room.created_at).isoformat(),
    }


def notify_room_admins(room_id: int, requester: User, db: Session):
    admins = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id,
        RoomMembership.role.in_(["admin", "co_admin"]),
        RoomMembership.status == "approved",
    ).all()
    room = db.query(Room).filter(Room.id == room_id).first()
    for a in admins:
        db.add(Notification(
            user_id=a.user_id,
            type="join_request",
            title="Nova solicitação de acesso",
            message=f"{requester.full_name} quer entrar em '{room.group_name} - {room.year}'",
            related_room_id=room_id,
        ))
        db.commit()
        _push_to_user(db, a.user_id, "Nova solicitação de entrada",
                      f"{requester.full_name} quer entrar em {room.group_name} - {room.year}")
        admin_user = db.query(User).filter(User.id == a.user_id).first()
        if admin_user:
            mail.send_join_request_to_admin(
                admin_email=admin_user.email,
                admin_name=admin_user.full_name,
                requester_name=requester.full_name,
                room_name=f"{room.group_name} - {room.year}",
                inst_name=room.institution.name,
                room_id=room_id,
            )
    db.commit()


def check_remembered_match(user: User, room_id: int, db: Session):
    name_lower = user.full_name.lower()
    room = db.query(Room).filter(Room.id == room_id).first()
    for rp in db.query(RememberedPerson).filter(
        RememberedPerson.room_id == room_id,
        RememberedPerson.matched_user_id == None,
    ).all():
        if rp.full_name.lower() in name_lower or name_lower in rp.full_name.lower():
            rp.matched_user_id = user.id
            inst_name = room.institution.name if room and room.institution else ""
            room_label = f"{room.group_name} — {room.year}" if room else ""

            # Notifica quem lembrou (criador do registro)
            db.add(Notification(
                user_id=rp.created_by_id,
                type="remembered_found",
                title="Alguém que você lembrou entrou!",
                message=f"{user.full_name} entrou na sala {room_label}!",
                related_room_id=room_id,
            ))
            creator = db.query(User).filter(User.id == rp.created_by_id).first()
            if creator and room:
                mail.send_remembered_found(
                    to_email=creator.email,
                    name=creator.full_name,
                    found_name=user.full_name,
                    room_name=room_label,
                )

            # Notifica a pessoa encontrada: "Você foi lembrado!"
            db.add(Notification(
                user_id=user.id,
                type="you_were_remembered",
                title="🥹 Alguém lembra de você!",
                message=f"Um colega da sala {room_label} ({inst_name}) te adicionou nos Lembrados.",
                related_room_id=room_id,
            ))
            db.commit()
            _push_to_user(db, user.id, "🥹 Alguém lembra de você!",
                          f"Um colega de {inst_name} te adicionou nos Lembrados.", "/")
            mail.send_you_were_remembered(
                to_email=user.email,
                name=user.full_name,
                room_name=room_label,
                inst_name=inst_name,
            )
    db.commit()


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def public_stats(db: Session = Depends(get_db)):
    """Estatísticas públicas para a landing page."""
    return {
        "users": db.query(User).filter(User.is_active == True).count(),
        "rooms": db.query(Room).count(),
        "institutions": db.query(Institution).filter(Institution.approved == True).count(),
    }

@app.get("/api/config")
def get_config():
    """Configurações públicas do frontend."""
    return {
        "ga_id": GOOGLE_ANALYTICS_ID,
        "vapid_public_key": VAPID_PUBLIC_KEY,
    }


@app.get("/api/ping")
def ping():
    """Keep-alive leve — sem query no banco."""
    return {"ok": True}


@app.get("/api/admin/email-status")
async def email_status():
    """Diagnostic endpoint. Returns email backend config (no secrets)."""
    try:
        from email_service_sendgrid import is_email_configured
        return is_email_configured()
    except Exception as e:
        return {"error": str(e), "backend": "unknown"}


@app.post("/api/auth/register")
async def register(
    request: Request,
    db: Session = Depends(get_db),
):
    # Accept both JSON and form-data payloads
    content_type = (request.headers.get("content-type") or "").lower()
    data: dict = {}
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="JSON inválido")
    else:
        try:
            form = await request.form()
            data = {k: v for k, v in form.items()}
        except Exception:
            data = {}
    full_name = (data.get("full_name") or data.get("name") or "").strip() if isinstance(data.get("full_name") or data.get("name") or "", str) else ""
    email = (data.get("email") or "").strip() if isinstance(data.get("email") or "", str) else ""
    password = data.get("password") or ""
    cpf = data.get("cpf")
    phone = data.get("phone")
    missing = [f for f, v in (("full_name", full_name), ("email", email), ("password", password)) if not v]
    if missing:
        raise HTTPException(status_code=422, detail=f"Campos obrigatórios ausentes: {', '.join(missing)}")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    if db.query(User).filter(User.email == email.lower()).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    import hashlib
    if cpf:
        if not validate_cpf(cpf):
            raise HTTPException(status_code=400, detail="CPF inválido. Verifique os dígitos e tente novamente.")
        cpf_clean = "".join(filter(str.isdigit, cpf))
        cpf_sha = hashlib.sha256(cpf_clean.encode()).hexdigest()
        if db.query(User).filter(User.cpf_hash == cpf_sha).first():
            raise HTTPException(status_code=400, detail="CPF já cadastrado")
    else:
        # sem CPF: hash único baseado no e-mail + uuid
        cpf_sha = hashlib.sha256(f"no-cpf:{email.lower()}:{uuid.uuid4()}".encode()).hexdigest()
    phone_clean = None
    if phone:
        phone_clean = "".join(filter(str.isdigit, phone))
        if phone_clean and db.query(User).filter(User.phone == phone_clean).first():
            raise HTTPException(status_code=400, detail="Celular já cadastrado")

    is_first = db.query(User).count() == 0
    user = User(
        full_name=full_name.strip(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        cpf_hash=cpf_sha,
        phone=phone_clean,
        is_system_admin=is_first,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    mail.send_welcome(user.email, user.full_name)
    db.add(EmailLog(user_id=user.id, email_type="welcome"))
    db.commit()
    track_event(user.id, "signup", {"source": "register"})
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user_to_dict(user)}


@app.post("/api/auth/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    # Accept both JSON and form-data payloads (mirrors /api/auth/register)
    content_type = (request.headers.get("content-type") or "").lower()
    data: dict = {}
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="JSON inválido")
    else:
        try:
            form = await request.form()
            data = {k: v for k, v in form.items()}
        except Exception:
            data = {}
    email = (data.get("email") or data.get("username") or "")
    email = email.strip() if isinstance(email, str) else ""
    password = data.get("password") or ""
    if not email or not password:
        missing = [f for f, v in (("email", email), ("password", password)) if not v]
        raise HTTPException(status_code=422, detail=f"Campos obrigatórios ausentes: {', '.join(missing)}")
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user_to_dict(user)}


@app.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user_required)):
    return user_to_dict(current_user)


# ═══════════════════════════════════════════════════════════════════════════════
# LGPD Art. 11 — Granular Consent endpoints
# Lists, grants, and revokes per-purpose consent. Biometric consents
# (tunel_biometric, face_matching) MUST be granted separately from ToS.
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/me/consents")
def list_my_consents(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Lista todos os consents do usuário, um por consent_type, incluindo
    tipos válidos que o user ainda não tocou (granted=False)."""
    from consent_helpers import list_consents
    return {"consents": list_consents(db, current_user.id)}


@app.post("/api/me/consents/{consent_type}/grant")
def grant_my_consent(
    consent_type: str,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Concede consent específico. Persiste hash do IP+UA para audit (LGPD Art. 37)."""
    from consent_helpers import VALID_CONSENT_TYPES, grant_consent
    if consent_type not in VALID_CONSENT_TYPES:
        raise HTTPException(400, f"consent_type inválido: {consent_type}")
    c = grant_consent(db, current_user.id, consent_type, request=request, version='v1')
    return {
        "success": True,
        "consent_type": c.consent_type,
        "granted_at": c.granted_at.isoformat() if c.granted_at else None,
        "version": c.version,
    }


@app.post("/api/me/consents/{consent_type}/revoke")
def revoke_my_consent(
    consent_type: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Revoga consent. LGPD Art. 8 §5: revogação deve ser tão fácil quanto conceder."""
    from consent_helpers import VALID_CONSENT_TYPES, revoke_consent
    if consent_type not in VALID_CONSENT_TYPES:
        raise HTTPException(400, f"consent_type inválido: {consent_type}")
    n = revoke_consent(db, current_user.id, consent_type)
    return {"success": True, "consent_type": consent_type, "revoked_count": n}


@app.post("/api/me/report-misuse")
async def report_misuse(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """User reporta upload feito sem consent dele. Marca pra delete + log."""
    body = await request.json()
    upload_id = body.get('upload_id')
    reason = body.get('reason', 'Não consentiu uso da foto')
    if not upload_id:
        raise HTTPException(400, "upload_id obrigatório")
    from database import TunelUpload, MatchAttemptLog
    upload = db.query(TunelUpload).filter(TunelUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(404, "Upload não encontrado")
    # Soft-delete the upload
    upload.deleted_at = datetime.utcnow()
    # Log incident
    log = MatchAttemptLog(
        requester_id=current_user.id,
        action_taken='misuse_reported',
    )
    db.add(log)
    db.commit()
    logger.warning(f"[MISUSE] User {current_user.id} reported upload {upload_id}: {reason}")
    return {"success": True, "upload_marked_deleted": True}


@app.post("/api/auth/forgot-password")
async def forgot_password(
    request: Request,
    db: Session = Depends(get_db),
):
    # Accept both JSON and form-data payloads (mirrors /api/auth/login)
    content_type = (request.headers.get("content-type") or "").lower()
    data: dict = {}
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="JSON inválido")
    else:
        try:
            form = await request.form()
            data = {k: v for k, v in form.items()}
        except Exception:
            data = {}
    email = data.get("email") or ""
    email = email.strip() if isinstance(email, str) else ""
    if not email:
        raise HTTPException(status_code=422, detail="Campos obrigatórios ausentes: email")
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    # Retorna sempre 200 para não revelar se o e-mail existe
    if user:
        token = uuid.uuid4().hex + uuid.uuid4().hex
        _reset_tokens[token] = {
            "user_id": user.id,
            "expires": datetime.utcnow() + timedelta(hours=1),
        }
        mail.send_password_reset(user.email, user.full_name, token)
    return {"message": "Se este e-mail estiver cadastrado, você receberá um link em breve."}


@app.post("/api/auth/reset-password")
def reset_password(
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    entry = _reset_tokens.get(token)
    if not entry or entry["expires"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Link inválido ou expirado. Solicite um novo.")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    user = db.query(User).filter(User.id == entry["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    user.password_hash = hash_password(new_password)
    db.commit()
    del _reset_tokens[token]
    return {"message": "Senha redefinida com sucesso! Faça login com a nova senha."}


# ─── Institutions ─────────────────────────────────────────────────────────────

@app.get("/api/institutions")
def list_institutions(
    type: Optional[str] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    from sqlalchemy import func, distinct as sa_distinct
    from database import Room as RoomModel

    limit = min(limit, 500)  # teto de segurança

    # Query única com contagem de turmas por JOIN — sem N+1
    q = (
        db.query(
            Institution,
            func.count(sa_distinct(RoomModel.id)).label("room_count"),
        )
        .outerjoin(RoomModel, RoomModel.institution_id == Institution.id)
        .filter(Institution.approved == True)
    )
    if type:
        q = q.filter(Institution.type == type)
    if state:
        q = q.filter(Institution.state == state)
    if search:
        q = q.filter(Institution.name.ilike(f"%{search}%"))

    rows = q.group_by(Institution.id).order_by(Institution.name).limit(limit).all()

    return [
        {
            "id": inst.id,
            "name": inst.name,
            "type": inst.type,
            "state": inst.state,
            "city": inst.city,
            "neighborhood": inst.neighborhood,
            "sector": inst.sector,
            "room_count": room_count,
            "member_count": 0,  # calculado sob demanda em /institutions/{id}
        }
        for inst, room_count in rows
    ]


@app.get("/api/institutions/{institution_id}")
def get_institution(institution_id: int, db: Session = Depends(get_db)):
    inst = db.query(Institution).filter(
        Institution.id == institution_id, Institution.approved == True
    ).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")

    rooms = []
    for room in inst.rooms:
        approved = db.query(RoomMembership).filter(
            RoomMembership.room_id == room.id, RoomMembership.status == "approved"
        ).count()
        pending = db.query(RoomMembership).filter(
            RoomMembership.room_id == room.id, RoomMembership.status == "pending"
        ).count()
        last_msg = (
            db.query(Message)
            .filter(Message.room_id == room.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        rooms.append({
            "id": room.id,
            "year": room.year,
            "group_name": room.group_name,
            "description": room.description,
            "member_count": approved,
            "pending_count": pending,
            "last_activity": (last_msg.created_at if last_msg else room.created_at).isoformat(),
            "created_at": room.created_at.isoformat(),
        })

    rooms.sort(key=lambda x: x["last_activity"], reverse=True)

    # Buscar população e nickname da cidade se existir
    city_population = None
    city_nickname = None
    if inst.city:
        try:
            city_obj = db.query(City).filter(City.name == inst.city).first()
            if city_obj:
                city_population = city_obj.population
                city_nickname = city_obj.nickname
        except:
            pass

    return {
        "id": inst.id, "name": inst.name, "type": inst.type,
        "state": inst.state, "city": inst.city,
        "neighborhood": inst.neighborhood, "sector": inst.sector,
        "city_population": city_population,
        "city_nickname": city_nickname,
        "rooms": rooms,
    }


# ─── Mural Atual ──────────────────────────────────────────────────────────────

@app.get("/api/institutions/{institution_id}/mural")
def get_mural(institution_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    entries = (
        db.query(CurrentStudent)
        .filter(CurrentStudent.institution_id == institution_id)
        .order_by(CurrentStudent.entry_year.desc().nullslast(), CurrentStudent.created_at.desc())
        .all()
    )
    my_id = current_user.id if current_user else None
    result = []
    for e in entries:
        u = e.user
        result.append({
            "id": e.id,
            "user_id": e.user_id,
            "is_mine": e.user_id == my_id,
            "full_name": u.full_name,
            "profile_photo": u.profile_photo,
            "entry_year": e.entry_year,
            "grade_or_period": e.grade_or_period,
            "since": e.created_at.isoformat(),
        })
    return result


@app.post("/api/institutions/{institution_id}/mural")
def join_mural(
    institution_id: int,
    entry_year: Optional[int] = Form(None),
    grade_or_period: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    inst = db.query(Institution).filter(
        Institution.id == institution_id, Institution.approved == True
    ).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")

    # Atualiza se já existe, cria se não existe
    existing = db.query(CurrentStudent).filter(
        CurrentStudent.user_id == current_user.id,
        CurrentStudent.institution_id == institution_id,
    ).first()

    if existing:
        existing.entry_year = entry_year
        existing.grade_or_period = grade_or_period.strip() or None
        existing.updated_at = datetime.utcnow()
    else:
        db.add(CurrentStudent(
            user_id=current_user.id,
            institution_id=institution_id,
            entry_year=entry_year,
            grade_or_period=grade_or_period.strip() or None,
        ))
    db.commit()
    return {"message": "Presença registrada no mural!"}


@app.delete("/api/institutions/{institution_id}/mural")
def leave_mural(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    deleted = db.query(CurrentStudent).filter(
        CurrentStudent.user_id == current_user.id,
        CurrentStudent.institution_id == institution_id,
    ).delete()
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Você não está no mural desta instituição")
    return {"message": "Presença removida do mural."}


@app.post("/api/institutions/suggest")
def suggest_institution(
    name: str = Form(...),
    type: str = Form(...),
    state: str = Form(...),
    city: str = Form(None),
    neighborhood: str = Form(None),
    sector: str = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    db.add(Institution(
        name=name.strip(), type=type, state=state.upper(),
        city=city, neighborhood=neighborhood, sector=sector,
        approved=False, suggested_by_id=current_user.id,
    ))
    db.commit()
    return {"message": "Sugestão enviada! Será analisada pelos administradores."}


# ─── Rooms ────────────────────────────────────────────────────────────────────

@app.post("/api/rooms")
def create_room(
    institution_id: int = Form(...),
    year: int = Form(...),
    group_name: str = Form(...),
    description: str = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    if not db.query(Institution).filter(
        Institution.id == institution_id, Institution.approved == True
    ).first():
        raise HTTPException(status_code=404, detail="Instituição não encontrada")

    if db.query(Room).filter(
        Room.institution_id == institution_id,
        Room.year == year,
        Room.group_name == group_name,
    ).first():
        raise HTTPException(status_code=400, detail="Essa sala já existe! Solicite acesso.")

    room = Room(
        institution_id=institution_id, year=year,
        group_name=group_name.strip(), description=description,
        created_by_id=current_user.id,
    )
    db.add(room)
    db.flush()
    db.add(RoomMembership(
        room_id=room.id, user_id=current_user.id,
        role="admin", status="approved", approved_at=datetime.utcnow(),
    ))
    db.commit()
    db.refresh(room)
    return {"id": room.id, "message": "Sala criada! Você é o ADM."}


@app.get("/api/rooms/{room_id}")
def get_room(
    room_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")

    approved_count = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "approved"
    ).count()

    my_membership = None
    if current_user:
        m = db.query(RoomMembership).filter(
            RoomMembership.room_id == room_id, RoomMembership.user_id == current_user.id
        ).first()
        if m:
            my_membership = {"role": m.role, "status": m.status}

    return {
        "id": room.id,
        "institution_id": room.institution_id,
        "institution_name": room.institution.name,
        "year": room.year,
        "group_name": room.group_name,
        "description": room.description,
        "member_count": approved_count,
        "my_membership": my_membership,
        "created_at": room.created_at.isoformat(),
    }


# ─── Memberships ──────────────────────────────────────────────────────────────

@app.post("/api/rooms/{room_id}/join")
def join_room(
    room_id: int,
    message: str = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    existing = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.user_id == current_user.id
    ).first()
    if existing:
        if existing.status == "approved":
            return {"message": "Você já é membro!", "already_member": True}
        if existing.status == "pending":
            raise HTTPException(status_code=400, detail="Sua solicitação já está pendente")
        existing.status = "pending"
        existing.message = message
        db.commit()
        notify_room_admins(room_id, current_user, db)
        return {"message": "Solicitação reenviada!"}

    # Salas criadas pelo admin do sistema entram direto (sem fila de aprovação)
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    creator = db.query(User).filter(User.id == room.created_by_id).first()
    auto_approve = creator and creator.is_system_admin
    status = "approved" if auto_approve else "pending"
    approved_at = datetime.utcnow() if auto_approve else None

    db.add(RoomMembership(
        room_id=room_id, user_id=current_user.id,
        role="member", status=status, message=message,
        approved_at=approved_at,
    ))
    db.commit()
    if auto_approve:
        return {"message": "Você entrou na sala! 🎉", "auto_approved": True}
    notify_room_admins(room_id, current_user, db)
    return {"message": "Solicitação enviada! Aguarde aprovação do ADM."}


@app.get("/api/rooms/{room_id}/members")
def get_members(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)
    members = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "approved"
    ).all()
    return [{
        "user_id": m.user.id,
        "full_name": m.user.full_name,
        "profile_photo": m.user.profile_photo,
        "city": m.user.city if m.user.show_city else None,
        "profession": m.user.profession if m.user.show_profession else None,
        "role": m.role,
        "joined_at": (m.approved_at or m.created_at).isoformat(),
    } for m in members]


@app.get("/api/rooms/{room_id}/pending")
def get_pending(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    m = get_membership(room_id, current_user, db)
    if m.role not in ["admin", "co_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")
    pending = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "pending"
    ).all()
    return [{
        "user_id": p.user.id,
        "full_name": p.user.full_name,
        "profile_photo": p.user.profile_photo,
        "message": p.message,
        "requested_at": p.created_at.isoformat(),
    } for p in pending]


@app.get("/api/rooms/{room_id}/online-users")
def get_online_users(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Retorna lista de usuários conectados agora na sala.
    Usa o tracking do ConnectionManager para listar quem está online via WebSocket.

    Resposta:
    [
      { "id": 1, "name": "Maria", "avatar": "😊", "color": "#FF6B6B" },
      { "id": 2, "name": "Pedro", "avatar": "🎮", "color": "#4ECDC4" }
    ]
    """
    get_membership(room_id, current_user, db)
    return manager.get_online_users(room_id)


@app.post("/api/rooms/{room_id}/members/{user_id}/approve")
def approve_member(
    room_id: int, user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    m = get_membership(room_id, current_user, db)
    if m.role not in ["admin", "co_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")
    target = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id,
        RoomMembership.user_id == user_id,
        RoomMembership.status == "pending",
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    target.status = "approved"
    target.approved_at = datetime.utcnow()
    room = db.query(Room).filter(Room.id == room_id).first()
    db.add(Notification(
        user_id=user_id, type="approved",
        title="Acesso aprovado! 🎉",
        message=f"Voce entrou na sala '{room.group_name} - {room.year}' em {room.institution.name}",
        related_room_id=room_id,
    ))
    db.commit()
    _push_to_user(db, user_id, "Acesso aprovado! 🎉",
                  f"Você entrou em {room.group_name} - {room.year}", "/")
    approved_user = db.query(User).filter(User.id == user_id).first()
    if approved_user:
        mail.send_approved(
            to_email=approved_user.email,
            name=approved_user.full_name,
            room_name=f"{room.group_name} - {room.year}",
            inst_name=room.institution.name,
        )
    return {"message": "Membro aprovado!"}


@app.post("/api/rooms/{room_id}/members/{user_id}/reject")
def reject_member(
    room_id: int, user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    m = get_membership(room_id, current_user, db)
    if m.role not in ["admin", "co_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")
    target = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.user_id == user_id
    ).first()
    if target:
        target.status = "rejected"
        db.commit()
        rejected_user = db.query(User).filter(User.id == user_id).first()
        room = db.query(Room).filter(Room.id == room_id).first()
        if rejected_user and room:
            mail.send_rejected(
                to_email=rejected_user.email,
                name=rejected_user.full_name,
                room_name=f"{room.group_name} - {room.year}",
                inst_name=room.institution.name,
            )
    return {"message": "Solicitação rejeitada"}


@app.post("/api/rooms/{room_id}/members/{user_id}/promote")
def promote_member(
    room_id: int, user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    m = get_membership(room_id, current_user, db)
    if m.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas o ADM principal pode promover")
    target = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.user_id == user_id,
        RoomMembership.status == "approved",
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Membro não encontrado")
    target.role = "co_admin"
    db.commit()
    return {"message": "Membro promovido a Co-ADM!"}


@app.delete("/api/rooms/{room_id}/members/{user_id}")
def remove_member(
    room_id: int, user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    m = get_membership(room_id, current_user, db)
    if m.role not in ["admin", "co_admin"] and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    target = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.user_id == user_id
    ).first()
    if target:
        db.delete(target)
        db.commit()
    return {"message": "Membro removido"}


# ─── Chat (REST + WebSocket) ──────────────────────────────────────────────────

@app.get("/api/rooms/{room_id}/messages")
def get_messages(
    room_id: int,
    limit: int = 80,
    offset: int = 0,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func as sa_func
    get_membership(room_id, current_user, db)
    msgs = (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.asc())
        .offset(offset).limit(limit).all()
    )
    msg_ids = [m.id for m in msgs]

    # Busca contagens de reações em uma query só (sem N+1)
    from collections import defaultdict
    reactions_by_msg: dict = defaultdict(dict)
    if msg_ids:
        rows = (
            db.query(MessageReaction.message_id, MessageReaction.reaction,
                     sa_func.count(MessageReaction.id).label("cnt"))
            .filter(MessageReaction.message_id.in_(msg_ids))
            .group_by(MessageReaction.message_id, MessageReaction.reaction)
            .all()
        )
        for msg_id, reaction, cnt in rows:
            reactions_by_msg[msg_id][reaction] = cnt

    # Reação do usuário atual
    my_reactions: dict = {}
    if msg_ids:
        mine = db.query(MessageReaction).filter(
            MessageReaction.message_id.in_(msg_ids),
            MessageReaction.user_id == current_user.id,
        ).all()
        my_reactions = {r.message_id: r.reaction for r in mine}

    return [{
        "id": m.id, "user_id": m.user_id,
        "user_name": m.user.full_name,
        "user_photo": m.user.profile_photo,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
        "reactions": reactions_by_msg.get(m.id, {}),
        "my_reaction": my_reactions.get(m.id),
    } for m in msgs]


VALID_REACTIONS = {"saudade", "classico", "eu_tava_la", "inesquecivel"}


@app.post("/api/rooms/{room_id}/messages")
async def post_message(
    room_id: int,
    content: str = Form(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Tarefa 2: Envia mensagem e trigger de push notifications para outros usuários."""
    if not content.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="Mensagem muito longa")

    get_membership(room_id, current_user, db)

    msg = Message(room_id=room_id, user_id=current_user.id, content=content.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Tarefa 2: Após salvar mensagem, envia push para cada user (exceto quem enviou)
    room_members = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id,
        RoomMembership.status == "approved",
        RoomMembership.user_id != current_user.id,  # Exclui quem enviou
    ).all()

    for member in room_members:
        if member.user_id != current_user.id:  # Extra safety check
            _push_to_user(
                db,
                member.user_id,
                title=f"{current_user.full_name} respondeu no chat",
                body=content[:50],
                url=f"/r/{room_id}",
            )

    return {
        "id": msg.id,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "user_photo": current_user.profile_photo,
        "content": content.strip(),
        "created_at": msg.created_at.isoformat(),
    }


@app.post("/api/rooms/{room_id}/messages/{msg_id}/react")
async def react_message(
    room_id: int, msg_id: int,
    reaction: str = Form(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func as sa_func
    get_membership(room_id, current_user, db)
    if reaction not in VALID_REACTIONS:
        raise HTTPException(status_code=400, detail="Reação inválida")

    existing = db.query(MessageReaction).filter(
        MessageReaction.message_id == msg_id,
        MessageReaction.user_id == current_user.id,
    ).first()

    if existing:
        if existing.reaction == reaction:
            db.delete(existing)   # toggle off
        else:
            existing.reaction = reaction  # troca reação
    else:
        db.add(MessageReaction(message_id=msg_id, user_id=current_user.id, reaction=reaction))
    db.commit()

    # Calcula novo total para broadcast
    counts = (
        db.query(MessageReaction.reaction, sa_func.count(MessageReaction.id).label("cnt"))
        .filter(MessageReaction.message_id == msg_id)
        .group_by(MessageReaction.reaction).all()
    )
    totals = {r: c for r, c in counts}
    await manager.broadcast({"type": "reaction_update", "message_id": msg_id, "reactions": totals}, room_id)
    return {"reactions": totals}


@app.websocket("/ws/{room_id}")
async def ws_chat(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(None),
):
    db = SessionLocal()
    try:
        if not token:
            await websocket.close(code=4001)
            return
        from auth import decode_token
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except Exception:
            await websocket.close(code=4001)
            return

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            await websocket.close(code=4001)
            return

        membership = db.query(RoomMembership).filter(
            RoomMembership.room_id == room_id,
            RoomMembership.user_id == user_id,
            RoomMembership.status == "approved",
        ).first()
        if not membership:
            await websocket.close(code=4003)
            return

        await manager.connect(websocket, room_id, user_id, user)

        # Broadcast do evento USER_JOINED
        await manager.broadcast({
            "type": "user_joined",
            "user_id": user_id,
            "user": {
                "id": user_id,
                "full_name": user.full_name,
                "profile_photo": user.profile_photo,
            },
            "avatar": user.profile_photo or "",
            "timestamp": datetime.utcnow().isoformat(),
        }, room_id)

        # Broadcast da lista atualizada de usuários online
        await manager.broadcast_online_users(room_id)

        await manager.broadcast({
            "type": "system",
            "message": f"{user.full_name} entrou na sala",
            "timestamp": datetime.utcnow().isoformat(),
        }, room_id)

        try:
            while True:
                raw = await websocket.receive_text()
                content = json.loads(raw).get("content", "").strip()
                if not content or len(content) > 2000:
                    continue
                msg = Message(room_id=room_id, user_id=user_id, content=content)
                db.add(msg)
                db.commit()
                db.refresh(msg)
                await manager.broadcast({
                    "type": "message",
                    "id": msg.id,
                    "user_id": user_id,
                    "user_name": user.full_name,
                    "user_photo": user.profile_photo,
                    "content": content,
                    "created_at": msg.created_at.isoformat(),
                }, room_id)
        except WebSocketDisconnect:
            manager.disconnect(websocket, room_id, user_id)

            # Broadcast da lista atualizada de usuários online
            await manager.broadcast_online_users(room_id)

            await manager.broadcast({
                "type": "system",
                "message": f"{user.full_name} saiu da sala",
                "timestamp": datetime.utcnow().isoformat(),
            }, room_id)
    finally:
        db.close()


# ─── Photos ───────────────────────────────────────────────────────────────────

MAX_PHOTOS = 200
MAX_SIZE_MB = 5


@app.get("/api/rooms/{room_id}/photos")
def get_photos(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)
    photos = db.query(Photo).filter(Photo.room_id == room_id).order_by(Photo.created_at.desc()).all()
    return [{
        "id": p.id,
        "url": f"/uploads/photos/{p.filename}",
        "caption": p.caption,
        "uploaded_by": p.user.full_name,
        "user_id": p.user_id,
        "created_at": p.created_at.isoformat(),
    } for p in photos]


@app.post("/api/rooms/{room_id}/photos")
async def upload_photo(
    room_id: int,
    caption: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)

    if db.query(Photo).filter(Photo.room_id == room_id).count() >= MAX_PHOTOS:
        raise HTTPException(status_code=400, detail=f"Limite de {MAX_PHOTOS} fotos atingido")

    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Formato não permitido. Use JPG, PNG ou WEBP.")

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Arquivo muito grande. Máximo: {MAX_SIZE_MB}MB")

    ext = (file.filename or "foto.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = f"uploads/photos/{filename}"

    with open(filepath, "wb") as f:
        f.write(content)

    try:
        from PIL import Image
        img = Image.open(filepath)
        img.thumbnail((1200, 1200))
        img.save(filepath, optimize=True, quality=85)
    except Exception:
        pass

    photo = Photo(
        room_id=room_id, user_id=current_user.id,
        filename=filename, original_filename=file.filename or filename,
        caption=caption,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return {
        "id": photo.id,
        "url": f"/uploads/photos/{filename}",
        "caption": caption,
        "uploaded_by": current_user.full_name,
        "created_at": photo.created_at.isoformat(),
    }


@app.delete("/api/rooms/{room_id}/photos/{photo_id}")
def delete_photo(
    room_id: int, photo_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    m = get_membership(room_id, current_user, db)
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.room_id == room_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Foto não encontrada")
    if photo.user_id != current_user.id and m.role not in ["admin", "co_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão")
    try:
        os.remove(f"uploads/photos/{photo.filename}")
    except OSError:
        pass
    db.delete(photo)
    db.commit()
    return {"message": "Foto removida"}


# ─── Remembered Persons ───────────────────────────────────────────────────────

@app.get("/api/rooms/{room_id}/remembered")
def get_remembered(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)
    rps = db.query(RememberedPerson).filter(
        RememberedPerson.room_id == room_id
    ).order_by(RememberedPerson.confirmations.desc()).all()
    return [{
        "id": r.id, "full_name": r.full_name, "nickname": r.nickname,
        "description": r.description, "confirmations": r.confirmations,
        "matched": r.matched_user_id is not None,
        "created_by_id": r.created_by_id,
        "created_at": r.created_at.isoformat(),
    } for r in rps]


@app.post("/api/rooms/{room_id}/remembered")
def create_remembered(
    room_id: int,
    full_name: str = Form(...),
    nickname: str = Form(None),
    description: str = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)
    rp = RememberedPerson(
        room_id=room_id, created_by_id=current_user.id,
        full_name=full_name.strip(), nickname=nickname, description=description,
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return {"id": rp.id, "full_name": rp.full_name, "message": "Adicionado com sucesso!"}


@app.post("/api/rooms/{room_id}/remembered/{rp_id}/confirm")
def confirm_remembered(
    room_id: int, rp_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)
    if db.query(RememberedPersonConfirmation).filter(
        RememberedPersonConfirmation.remembered_person_id == rp_id,
        RememberedPersonConfirmation.user_id == current_user.id,
    ).first():
        return {"message": "Você já confirmou"}
    db.add(RememberedPersonConfirmation(
        remembered_person_id=rp_id, user_id=current_user.id
    ))
    rp = db.query(RememberedPerson).filter(RememberedPerson.id == rp_id).first()
    if rp:
        rp.confirmations += 1
    db.commit()
    return {"message": "Confirmado!"}


# ─── Invite Links ─────────────────────────────────────────────────────────────

@app.post("/api/rooms/{room_id}/invites")
def create_invite(
    room_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    get_membership(room_id, current_user, db)
    token = uuid.uuid4().hex + uuid.uuid4().hex
    db.add(InviteLink(
        room_id=room_id, created_by_id=current_user.id,
        token=token, expires_at=datetime.utcnow() + timedelta(days=7),
    ))
    db.commit()
    return {"token": token}


@app.get("/api/invites/{token}")
def get_invite_info(token: str, db: Session = Depends(get_db)):
    invite = db.query(InviteLink).filter(
        InviteLink.token == token, InviteLink.is_active == True
    ).first()
    if not invite or invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Convite inválido ou expirado")
    room = invite.room
    return {
        "room_id": room.id,
        "institution_name": room.institution.name,
        "year": room.year,
        "group_name": room.group_name,
        "member_count": db.query(RoomMembership).filter(
            RoomMembership.room_id == room.id, RoomMembership.status == "approved"
        ).count(),
    }


@app.post("/api/invites/{token}/use")
def use_invite(
    token: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    invite = db.query(InviteLink).filter(
        InviteLink.token == token, InviteLink.is_active == True
    ).first()
    if not invite or invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Convite inválido ou expirado")

    room_id = invite.room_id
    existing = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.user_id == current_user.id
    ).first()
    if existing and existing.status == "approved":
        return {"message": "Você já é membro!", "room_id": room_id}

    if existing:
        existing.status = "approved"
        existing.approved_at = datetime.utcnow()
    else:
        db.add(RoomMembership(
            room_id=room_id, user_id=current_user.id,
            role="member", status="approved",
            invited_by_id=invite.created_by_id,
            approved_at=datetime.utcnow(),
        ))

    invite.use_count += 1
    db.commit()
    check_remembered_match(current_user, room_id, db)
    return {"message": "Bem-vindo à sala!", "room_id": room_id}


# ─── Notifications ────────────────────────────────────────────────────────────

@app.get("/api/notifications")
def get_notifications(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50).all()
    )
    return [{
        "id": n.id, "type": n.type, "title": n.title,
        "message": n.message, "read": n.read,
        "related_room_id": n.related_room_id,
        "created_at": n.created_at.isoformat(),
    } for n in notifs]


@app.post("/api/notifications/read-all")
def read_all_notifications(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read == False
    ).update({"read": True})
    db.commit()
    return {"message": "OK"}


# ─── User Profile ─────────────────────────────────────────────────────────────

@app.put("/api/users/profile")
async def update_profile(
    full_name: str = Form(None),
    city: str = Form(None),
    profession: str = Form(None),
    bio: str = Form(None),
    show_city: str = Form("true"),
    show_profession: str = Form("true"),
    show_bio: str = Form("true"),
    avatar: UploadFile = File(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    if full_name and full_name.strip():
        if len(full_name.strip()) < 3:
            raise HTTPException(status_code=400, detail="Nome muito curto")
        if len(full_name.strip()) > 200:
            raise HTTPException(status_code=400, detail="Nome muito longo")
        current_user.full_name = full_name.strip()
    current_user.city = city or None
    current_user.profession = profession or None
    current_user.bio = bio or None
    current_user.show_city = show_city.lower() == "true"
    current_user.show_profession = show_profession.lower() == "true"
    current_user.show_bio = show_bio.lower() == "true"

    if avatar and avatar.filename:
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if avatar.content_type in allowed:
            content = await avatar.read()
            if len(content) <= 2 * 1024 * 1024:
                ext = (avatar.filename or "avatar.jpg").rsplit(".", 1)[-1].lower()
                if ext not in ("jpg", "jpeg", "png", "webp"):
                    ext = "jpg"
                filename = f"avatar_{current_user.id}.{ext}"
                filepath = f"uploads/avatars/{filename}"
                with open(filepath, "wb") as f:
                    f.write(content)
                try:
                    from PIL import Image
                    img = Image.open(filepath)
                    img.thumbnail((400, 400))
                    img.save(filepath, optimize=True, quality=85)
                except Exception:
                    pass
                current_user.profile_photo = f"/uploads/avatars/{filename}"

    db.commit()
    db.refresh(current_user)
    return user_to_dict(current_user)


@app.delete("/api/users/me")
def delete_account(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Desativa a conta (soft delete) — mantém histórico de mensagens e fotos."""
    current_user.is_active = False
    current_user.full_name = "Usuário removido"
    current_user.bio = None
    current_user.city = None
    current_user.profession = None
    current_user.profile_photo = None
    db.commit()
    return {"message": "Conta encerrada. Sentiremos sua falta! 💙"}


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT-GHOST PRIVACY ENDPOINTS (migration 003)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/me")
def get_me(
    current_user: User = Depends(get_current_user_required),
):
    """Return the authenticated user's basic profile as JSON.

    Without this dedicated endpoint, GET /api/me fell through to the SPA
    catch-all and returned the homepage HTML with status 200, which
    confused API clients and integration tests.
    """
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": getattr(current_user, "phone", None),
        "phone_verified": bool(getattr(current_user, "phone_verified", False)),
        "is_discoverable": bool(getattr(current_user, "is_discoverable", False)),
        "allow_reconnect_requests": bool(getattr(current_user, "allow_reconnect_requests", False)),
        "ghost_mode_global": bool(getattr(current_user, "ghost_mode_global", False)),
        "birthdate": current_user.birthdate.isoformat() if getattr(current_user, "birthdate", None) else None,
        "created_at": current_user.created_at.isoformat() if getattr(current_user, "created_at", None) else None,
    }


@app.get("/api/me/visibility")
def get_my_visibility(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Retorna as configurações atuais de visibilidade do usuário.

    Inclui flags globais + lista de turmas onde o usuário fez opt-in.
    """
    turma_optins = (
        db.query(UserTurmaVisibility)
        .filter(UserTurmaVisibility.user_id == current_user.id,
                UserTurmaVisibility.is_visible == True)
        .all()
    )
    return {
        "is_discoverable": bool(current_user.is_discoverable),
        "allow_reconnect_requests": bool(current_user.allow_reconnect_requests),
        "ghost_mode_global": bool(current_user.ghost_mode_global),
        "visible_in_turmas": [t.turma_id for t in turma_optins],
        "effective_state": (
            "ghost_panic" if current_user.ghost_mode_global
            else ("discoverable" if current_user.is_discoverable else "ghost_default")
        ),
    }


@app.put("/api/me/visibility")
def update_my_visibility(
    is_discoverable: Optional[bool] = None,
    allow_reconnect_requests: Optional[bool] = None,
    ghost_mode_global: Optional[bool] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Atualiza configurações de visibilidade — todos os campos são opcionais.

    Default-ghost permanece em vigor: a única forma de aparecer em buscas é
    setar is_discoverable=TRUE explicitamente.
    """
    changed = []
    if is_discoverable is not None:
        current_user.is_discoverable = bool(is_discoverable)
        changed.append("is_discoverable")
    if allow_reconnect_requests is not None:
        current_user.allow_reconnect_requests = bool(allow_reconnect_requests)
        changed.append("allow_reconnect_requests")
    if ghost_mode_global is not None:
        current_user.ghost_mode_global = bool(ghost_mode_global)
        changed.append("ghost_mode_global")
    db.commit()
    db.refresh(current_user)
    return {
        "success": True,
        "changed": changed,
        "is_discoverable": bool(current_user.is_discoverable),
        "allow_reconnect_requests": bool(current_user.allow_reconnect_requests),
        "ghost_mode_global": bool(current_user.ghost_mode_global),
    }


@app.put("/api/me/birthdate")
async def set_my_birthdate(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🎂 Set data de nascimento (one-shot, imutável após gravar).

    LGPD Art. 14 + ECA: gate 18+ exige data de nascimento. Aceitamos
    auto-declaração (`age_verification_method='self_declared'`) — o
    `age_verified` permanece FALSE até confirmação via gov.br ou docs.

    Regras:
      * Campo `birthdate` no body, formato ISO 'YYYY-MM-DD'.
      * Ano entre 1925 e (ano atual − 18). Impede menores e datas absurdas.
      * Imutável depois da primeira gravação. Mudança requer ticket via
        DPO/suporte (defesa contra alteração pós-fato pra burlar gates).
    """
    # Bloqueia mudança se já tem birthdate
    if current_user.birthdate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Data de nascimento já registrada. Para corrigir, "
                "abra um chamado com o DPO via suporte."
            ),
        )

    # Aceita JSON ou form-data, mesmo padrão de /api/auth/register
    content_type = (request.headers.get("content-type") or "").lower()
    data: dict = {}
    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="JSON inválido")
    else:
        try:
            form = await request.form()
            data = {k: v for k, v in form.items()}
        except Exception:
            data = {}

    raw = (data.get("birthdate") or "").strip() if isinstance(data.get("birthdate"), str) else ""
    if not raw:
        raise HTTPException(status_code=422, detail="Campo 'birthdate' é obrigatório")

    # Parse rígido YYYY-MM-DD (date.fromisoformat aceita exatamente esse formato)
    from datetime import date as _date
    try:
        bd = _date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Formato inválido. Use YYYY-MM-DD (ex: 1985-04-15).",
        )

    # Validação de ano: 1925..(ano atual − 18). Limite superior bloqueia menores.
    today = _date.today()
    min_year = 1925
    max_year = today.year - 18
    if bd.year < min_year or bd.year > max_year:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ano de nascimento deve estar entre {min_year} e {max_year}. "
                "TimeMates é restrito a maiores de 18 anos."
            ),
        )

    # Double-check idade efetiva: ano permitido mas dia/mês ainda não fizeram 18
    if calculate_age(bd) < 18:
        raise HTTPException(
            status_code=422,
            detail="TimeMates é restrito a maiores de 18 anos.",
        )

    current_user.birthdate = bd
    current_user.age_verified = False  # self_declared não é verified
    current_user.age_verification_method = "self_declared"
    db.commit()
    db.refresh(current_user)

    return {
        "success": True,
        "birthdate": current_user.birthdate.isoformat(),
        "age": calculate_age(current_user.birthdate),
        "age_verified": bool(current_user.age_verified),
        "age_verification_method": current_user.age_verification_method,
        "immutable": True,
    }


@app.post("/api/me/panic-ghost")
def panic_ghost(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🚨 One-tap ghost everywhere.

    Liga ghost_mode_global + desliga is_discoverable + desliga TODOS os opt-ins
    de turmas. Operação atômica. Para sair do pânico, use PUT /api/me/visibility.
    """
    current_user.ghost_mode_global = True
    current_user.is_discoverable = False
    # Desliga todos os opt-ins de turmas (não deleta — só marca invisible para histórico)
    db.query(UserTurmaVisibility).filter(
        UserTurmaVisibility.user_id == current_user.id
    ).update({"is_visible": False})
    db.commit()
    return {
        "success": True,
        "message": "Modo fantasma ativado. Você está invisível em todo o sistema.",
        "ghost_mode_global": True,
        "is_discoverable": False,
        "turma_optins_cleared": True,
    }


@app.post("/api/me/visibility/turma/{turma_id}")
def opt_in_to_turma(
    turma_id: int,
    is_visible: bool = True,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Opt-in (ou opt-out) para visibilidade dentro de uma turma específica.

    Permite que um usuário ghost seja descoberto APENAS nessa turma.
    Passar is_visible=False remove o opt-in.
    Se ghost_mode_global=True, a operação é rejeitada (pânico tem precedência).
    """
    # Verificar que a turma existe
    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    if current_user.ghost_mode_global and is_visible:
        raise HTTPException(
            status_code=409,
            detail="Modo pânico ativo — desative ghost_mode_global antes de fazer opt-in.",
        )

    existing = (
        db.query(UserTurmaVisibility)
        .filter(UserTurmaVisibility.user_id == current_user.id,
                UserTurmaVisibility.turma_id == turma_id)
        .first()
    )
    if existing:
        existing.is_visible = bool(is_visible)
    else:
        db.add(UserTurmaVisibility(
            user_id=current_user.id,
            turma_id=turma_id,
            is_visible=bool(is_visible),
        ))
    db.commit()
    return {
        "success": True,
        "turma_id": turma_id,
        "is_visible": bool(is_visible),
        "message": (
            f"Você agora é visível na turma {turma_id}."
            if is_visible else
            f"Opt-in removido da turma {turma_id}."
        ),
    }


@app.get("/api/users/{user_id}")
def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """Perfil público de outro usuário — dados sensíveis respeitam as preferências de privacidade."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Salas em comum (para exibir na tela de perfil)
    my_rooms = {
        m.room_id for m in db.query(RoomMembership).filter(
            RoomMembership.user_id == current_user.id,
            RoomMembership.status == "approved"
        ).all()
    }
    their_rooms = db.query(RoomMembership).filter(
        RoomMembership.user_id == user_id,
        RoomMembership.status == "approved"
    ).all()
    shared_rooms = [
        {
            "room_id": m.room_id,
            "group_name": m.room.group_name,
            "institution_name": m.room.institution.name,
        }
        for m in their_rooms if m.room_id in my_rooms
    ]
    return {
        "id": user.id,
        "full_name": user.full_name,
        "profile_photo": user.profile_photo,
        "city": user.city if user.show_city else None,
        "profession": user.profession if user.show_profession else None,
        "bio": user.bio if user.show_bio else None,
        "member_since": user.created_at.isoformat(),
        "shared_rooms": shared_rooms,
    }


@app.get("/api/users/{user_id}/rooms")
def get_user_rooms(
    user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    if current_user.id != user_id and not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Sem permissão")
    memberships = db.query(RoomMembership).filter(
        RoomMembership.user_id == user_id, RoomMembership.status == "approved"
    ).all()
    return [{
        "room_id": m.room_id,
        "institution_name": m.room.institution.name,
        "year": m.room.year,
        "group_name": m.room.group_name,
        "role": m.role,
        "joined_at": (m.approved_at or m.created_at).isoformat(),
    } for m in memberships]


# ─── Admin ────────────────────────────────────────────────────────────────────

@app.get("/api/admin/stats")
def admin_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "institutions_approved": db.query(Institution).filter(Institution.approved == True).count(),
        "institutions_pending": db.query(Institution).filter(Institution.approved == False).count(),
        "rooms": db.query(Room).count(),
        "photos": db.query(Photo).count(),
        "messages": db.query(Message).count(),
    }


@app.get("/api/admin/institutions/pending")
def admin_pending_institutions(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    insts = db.query(Institution).filter(Institution.approved == False).order_by(Institution.created_at.desc()).all()
    return [{
        "id": i.id, "name": i.name, "type": i.type,
        "state": i.state, "city": i.city,
        "created_at": i.created_at.isoformat(),
    } for i in insts]


@app.post("/api/admin/institutions/{institution_id}/approve")
def admin_approve_institution(
    institution_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Não encontrada")
    inst.approved = True
    inst.approved_by_id = admin.id
    db.commit()
    return {"message": "Instituição aprovada!"}


@app.delete("/api/admin/institutions/{institution_id}")
def admin_reject_institution(
    institution_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if inst:
        db.delete(inst)
        db.commit()
    return {"message": "Removida"}


@app.post("/api/admin/institutions")
def admin_add_institution(
    name: str = Form(...),
    type: str = Form(...),
    state: str = Form(...),
    city: str = Form(None),
    neighborhood: str = Form(None),
    sector: str = Form(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    inst = Institution(
        name=name.strip(), type=type, state=state.upper(),
        city=city, neighborhood=neighborhood, sector=sector,
        approved=True, approved_by_id=admin.id,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return {"id": inst.id, "message": "Instituição adicionada!"}


@app.get("/api/admin/users")
def admin_list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    return [user_to_dict(u) for u in users]


# ─── Depoimentos ─────────────────────────────────────────────────────────────

@app.get("/api/institutions/{institution_id}/testimonies")
def get_testimonies(institution_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Testimony)
        .filter(Testimony.institution_id == institution_id)
        .order_by(Testimony.created_at.desc())
        .limit(30).all()
    )
    return [{
        "id": t.id,
        "user_id": t.user_id,
        "full_name": t.user.full_name,
        "profile_photo": t.user.profile_photo,
        "content": t.content,
        "year_attended": t.year_attended,
        "created_at": t.created_at.isoformat(),
    } for t in rows]


@app.post("/api/institutions/{institution_id}/testimonies")
def add_testimony(
    institution_id: int,
    content: str = Form(...),
    year_attended: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    if len(content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Depoimento muito curto (mínimo 10 caracteres)")
    if len(content) > 500:
        raise HTTPException(status_code=400, detail="Depoimento muito longo (máximo 500 caracteres)")
    # Um depoimento por usuário por instituição
    existing = db.query(Testimony).filter(
        Testimony.user_id == current_user.id,
        Testimony.institution_id == institution_id,
    ).first()
    if existing:
        existing.content = content.strip()
        existing.year_attended = year_attended
    else:
        db.add(Testimony(
            user_id=current_user.id,
            institution_id=institution_id,
            content=content.strip(),
            year_attended=year_attended,
        ))
    db.commit()
    return {"message": "Depoimento salvo! ❤️"}


# ─── Push Notifications ──────────────────────────────────────────────────────

@app.get("/api/push/vapid-public-key")
def get_vapid_key():
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push não configurado")
    return {"public_key": VAPID_PUBLIC_KEY}


@app.post("/api/push/subscribe")
def push_subscribe(
    endpoint: str = Form(...),
    p256dh: str = Form(...),
    auth: str = Form(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    existing = db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint
    ).first()
    if existing:
        existing.user_id = current_user.id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        ))
    db.commit()
    return {"message": "Subscribed"}


@app.delete("/api/push/unsubscribe")
def push_unsubscribe(
    endpoint: str = Form(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.endpoint == endpoint,
    ).delete()
    db.commit()
    return {"message": "Unsubscribed"}


# ─── Mensagens Diretas (DM) ───────────────────────────────────────────────────

def _get_or_create_conv(db: Session, user_a: int, user_b: int) -> DMConversation:
    conv = db.query(DMConversation).filter(
        ((DMConversation.user_a_id == user_a) & (DMConversation.user_b_id == user_b)) |
        ((DMConversation.user_a_id == user_b) & (DMConversation.user_b_id == user_a))
    ).first()
    if not conv:
        conv = DMConversation(user_a_id=user_a, user_b_id=user_b)
        db.add(conv)
        db.commit()
        db.refresh(conv)
    return conv


@app.get("/api/dm/conversations")
def list_dm_conversations(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    convs = db.query(DMConversation).filter(
        (DMConversation.user_a_id == current_user.id) |
        (DMConversation.user_b_id == current_user.id)
    ).order_by(DMConversation.updated_at.desc()).all()

    result = []
    for c in convs:
        other = c.user_b if c.user_a_id == current_user.id else c.user_a
        last_msg = db.query(DMMessage).filter(
            DMMessage.conversation_id == c.id
        ).order_by(DMMessage.created_at.desc()).first()
        unread = db.query(DMMessage).filter(
            DMMessage.conversation_id == c.id,
            DMMessage.sender_id != current_user.id,
            DMMessage.read == False,
        ).count()
        result.append({
            "conv_id": c.id,
            "other_user_id": other.id,
            "other_name": other.full_name,
            "other_photo": other.profile_photo,
            "last_message": last_msg.content[:80] if last_msg else None,
            "last_at": last_msg.created_at.isoformat() if last_msg else c.created_at.isoformat(),
            "unread": unread,
        })
    return result


@app.get("/api/dm/{other_user_id}/messages")
def get_dm_messages(
    other_user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    other = db.query(User).filter(User.id == other_user_id, User.is_active == True).first()
    if not other:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    conv = _get_or_create_conv(db, current_user.id, other_user_id)
    # Marca como lido
    db.query(DMMessage).filter(
        DMMessage.conversation_id == conv.id,
        DMMessage.sender_id == other_user_id,
        DMMessage.read == False,
    ).update({"read": True})
    db.commit()
    msgs = db.query(DMMessage).filter(
        DMMessage.conversation_id == conv.id
    ).order_by(DMMessage.created_at.asc()).limit(100).all()
    return {
        "conv_id": conv.id,
        "other": {
            "id": other.id,
            "full_name": other.full_name,
            "profile_photo": other.profile_photo,
            "city": other.city if other.show_city else None,
            "profession": other.profession if other.show_profession else None,
        },
        "messages": [{
            "id": m.id,
            "sender_id": m.sender_id,
            "content": m.content,
            "read": m.read,
            "created_at": m.created_at.isoformat(),
        } for m in msgs],
    }


@app.post("/api/dm/{other_user_id}/send")
async def send_dm(
    other_user_id: int,
    content: str = Form(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    if not content.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")
    if len(content) > 2000:
        raise HTTPException(status_code=400, detail="Mensagem muito longa")
    other = db.query(User).filter(User.id == other_user_id, User.is_active == True).first()
    if not other:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    conv = _get_or_create_conv(db, current_user.id, other_user_id)
    msg = DMMessage(
        conversation_id=conv.id,
        sender_id=current_user.id,
        content=content.strip(),
    )
    db.add(msg)
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)

    payload = {
        "type": "dm",
        "conv_id": conv.id,
        "msg_id": msg.id,
        "sender_id": current_user.id,
        "sender_name": current_user.full_name,
        "sender_photo": current_user.profile_photo,
        "content": msg.content,
        "created_at": msg.created_at.isoformat(),
    }
    # Broadcast via WS para remetente e destinatário
    await dm_manager.send_to_user(payload, other_user_id)
    await dm_manager.send_to_user(payload, current_user.id)

    # Push notification para destinatário
    _push_to_user(
        db, other_user_id,
        title=f"💬 {current_user.full_name}",
        body=content[:100],
        url="/?dm=1",
    )
    return payload


@app.websocket("/ws/dm")
async def ws_dm(websocket: WebSocket, token: str = Query(None)):
    if not token:
        await websocket.close(code=4001)
        return
    from auth import decode_token
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    db.close()
    if not user:
        await websocket.close(code=4001)
        return

    await dm_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()   # heartbeat / ping
    except WebSocketDisconnect:
        dm_manager.disconnect(websocket, user_id)


# ─── SEO / Páginas públicas ───────────────────────────────────────────────────

import re as _re
import unicodedata as _uni

def _slugify(text: str) -> str:
    t = _uni.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    t = _re.sub(r'[^\w\s-]', '', t.lower())
    return _re.sub(r'[-\s]+', '-', t).strip('-') or "inst"

def _esc(s) -> str:
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _page_html(title: str, desc: str, canonical: str, body: str, year: int = None) -> str:
    y = year or datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>{_esc(title)}</title>
<meta name="description" content="{_esc(desc)}"/>
<link rel="canonical" href="{canonical}"/>
<meta property="og:type" content="website"/>
<meta property="og:url" content="{canonical}"/>
<meta property="og:title" content="{_esc(title)}"/>
<meta property="og:description" content="{_esc(desc)}"/>
<meta property="og:site_name" content="TimeMates"/>
<meta property="og:image" content="{BASE_URL}/static/og-card.png"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta name="google-site-verification" content="MBtOa2SdYo58vO8Z1XgOOrJ_Apm3VN7aqi16-_XJXck"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="{_esc(title)}"/>
<meta name="twitter:description" content="{_esc(desc)}"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#F7F5F2;color:#374151;min-height:100vh}}
a{{text-decoration:none;color:inherit}}
.hd{{background:#1E3A5F;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.logo{{color:#fff;font-size:1.35rem;font-weight:800;letter-spacing:-.5px}}.logo span{{color:#D4A853}}
.logo-sub{{color:rgba(255,255,255,.6);font-size:.75rem;margin-top:1px}}
.btn-p{{background:#D4A853;color:#1E3A5F;font-weight:700;padding:10px 22px;border-radius:8px;font-size:.88rem;white-space:nowrap;display:inline-block;transition:opacity .15s}}
.btn-p:hover{{opacity:.85}}
.hero{{background:#1E3A5F;padding:44px 24px 52px;text-align:center;color:#fff}}
.hero-ic{{font-size:3.2rem;margin-bottom:14px}}
.hero h1{{font-size:2rem;font-weight:800;line-height:1.2;margin-bottom:8px}}
.hero-sub{{color:rgba(255,255,255,.7);font-size:.95rem;margin-bottom:20px}}
.stats{{display:flex;justify-content:center;gap:36px;flex-wrap:wrap;margin-top:28px;padding-top:28px;border-top:1px solid rgba(255,255,255,.15)}}
.st{{text-align:center}}.st-n{{font-size:2rem;font-weight:800;color:#D4A853}}.st-l{{font-size:.78rem;color:rgba(255,255,255,.6);margin-top:3px}}
.sec{{max-width:740px;margin:0 auto;padding:36px 20px}}
.sec h2{{font-size:1.1rem;font-weight:700;color:#1E3A5F;margin-bottom:16px;display:flex;align-items:center;gap:8px}}
.rc{{background:#fff;border:1.5px solid #E5E0D6;border-radius:12px;padding:16px 18px;display:flex;align-items:center;gap:14px;margin-bottom:10px;transition:all .2s;cursor:pointer}}
.rc:hover{{border-color:#D4A853;box-shadow:0 4px 14px rgba(0,0,0,.09);transform:translateY(-1px)}}
.rc-year{{background:#1E3A5F;color:#fff;font-weight:800;font-size:1rem;padding:8px 12px;border-radius:8px;min-width:60px;text-align:center;flex-shrink:0}}
.rc-info{{flex:1}}.rc-name{{display:block;font-weight:600;color:#1E3A5F;margin-bottom:3px;font-size:.95rem}}
.rc-m{{font-size:.8rem;color:#9CA3AF}}
.rc-arr{{color:#D4A853;font-size:1.2rem;font-weight:700}}
.empty-r{{text-align:center;color:#9CA3AF;padding:36px;background:#fff;border-radius:12px;border:1.5px dashed #E5E0D6;font-size:.9rem}}
.cta{{background:linear-gradient(135deg,#1E3A5F 0%,#2a4f8a 100%);padding:52px 24px;text-align:center;color:#fff}}
.cta h2{{font-size:1.5rem;font-weight:800;margin-bottom:10px}}
.cta p{{color:rgba(255,255,255,.75);font-size:.95rem;margin-bottom:28px;max-width:480px;margin-inline:auto;line-height:1.6}}
.btn-cta{{background:#D4A853;color:#1E3A5F;font-weight:800;padding:14px 36px;border-radius:10px;font-size:1rem;display:inline-block;transition:transform .15s}}
.btn-cta:hover{{transform:scale(1.04)}}
.share-sec{{max-width:740px;margin:0 auto;padding:0 20px 40px}}
.share-box{{background:#fff;border:1.5px solid #E5E0D6;border-radius:12px;padding:24px}}
.share-box h3{{font-size:.95rem;font-weight:700;color:#1E3A5F;margin-bottom:6px}}
.share-box p{{color:#6B7280;font-size:.82rem;margin-bottom:14px;line-height:1.5}}
.share-txt{{background:#F7F5F2;border-radius:8px;padding:14px;font-size:.83rem;line-height:1.65;border:1px solid #E5E0D6;white-space:pre-wrap;font-family:inherit;color:#374151}}
.share-btns{{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}}
.btn-copy{{background:#1E3A5F;color:#fff;border:none;padding:9px 20px;border-radius:6px;cursor:pointer;font-size:.83rem;font-weight:600;transition:opacity .15s}}
.btn-copy:hover{{opacity:.8}}
.btn-wa{{background:#25D366;color:#fff;padding:9px 20px;border-radius:6px;font-size:.83rem;font-weight:600;transition:opacity .15s}}
.btn-wa:hover{{opacity:.85}}
.qr-wrap{{text-align:center;margin-top:20px}}.qr-wrap img{{border-radius:10px;border:3px solid #E5E0D6}}
.qr-wrap p{{font-size:.75rem;color:#9CA3AF;margin-top:6px}}
.ft{{background:#1E3A5F;padding:20px;text-align:center;color:rgba(255,255,255,.45);font-size:.77rem}}
.ft a{{color:#D4A853}}
@media(max-width:480px){{.hero h1{{font-size:1.4rem}}.st-n{{font-size:1.5rem}}.stats{{gap:20px}}}}
</style>
</head>
<body>
<div class="hd">
  <div>
    <div class="logo">Time<span>Mates</span></div>
    <div class="logo-sub">O mapa das pessoas que cruzaram sua vida</div>
  </div>
  <a href="{BASE_URL}/index.html" class="btn-p">Entrar na plataforma →</a>
</div>
{body}
<div class="ft">© {y} TimeMates · <a href="{BASE_URL}/index.html">Acessar a plataforma</a></div>
<script>
function copyShare(id){{
  const el=document.getElementById(id);
  if(!el)return;
  navigator.clipboard?.writeText(el.innerText).then(()=>{{
    const b=el.parentElement.querySelector('.btn-copy');
    if(b){{b.textContent='✅ Copiado!';setTimeout(()=>b.textContent='📋 Copiar',2200)}}
  }});
}}
</script>
</body></html>"""


@app.get("/p/{institution_id}", response_class=HTMLResponse)
@app.get("/p/{institution_id}/{slug}", response_class=HTMLResponse)
def institution_public_page(
    institution_id: int, slug: str = "",
    db: Session = Depends(get_db)
):
    """Página pública SEO-otimizada de uma instituição."""
    inst = db.query(Institution).filter(
        Institution.id == institution_id, Institution.approved == True
    ).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instituição não encontrada")

    correct_slug = _slugify(inst.name)
    canonical = f"{BASE_URL}/p/{institution_id}/{correct_slug}"
    if slug and slug != correct_slug:
        return RedirectResponse(url=canonical, status_code=301)

    from sqlalchemy import func as _f, distinct as _d
    rows = (
        db.query(Room, _f.count(RoomMembership.id).label("mc"))
        .outerjoin(RoomMembership, (RoomMembership.room_id == Room.id) & (RoomMembership.status == "approved"))
        .filter(Room.institution_id == institution_id)
        .group_by(Room.id)
        .order_by(Room.year.desc())
        .all()
    )
    room_count = len(rows)
    member_count = db.query(RoomMembership).join(Room).filter(
        Room.institution_id == institution_id, RoomMembership.status == "approved"
    ).count()

    type_icon = {"school":"🏫","university":"🎓","company":"🏢","city":"🏙️"}.get(inst.type,"🏛️")
    type_label = {"school":"Escola","university":"Faculdade","company":"Empresa","city":"Cidade"}.get(inst.type,"Instituição")
    location = " · ".join(filter(None,[inst.city, inst.state]))
    og_title = f"Ex-alunos de {inst.name} | TimeMates"
    og_desc = (f"{room_count} turma{'s' if room_count!=1 else ''} · "
               f"{member_count} membro{'s' if member_count!=1 else ''}. "
               f"Você fez parte de {inst.name}? Encontre seus colegas no TimeMates!")

    place_word = {"school":"escola","university":"faculdade","company":"empresa","city":"cidade"}.get(inst.type,"lugar")
    verb_past  = {"school":"estudou em","university":"estudou em","company":"trabalhou na","city":"viveu em"}.get(inst.type,"passou por")
    rooms_html = "".join(
        f'<a href="{BASE_URL}/r/{r.id}" class="rc">'
        f'<span class="rc-year">{r.year}</span>'
        f'<div class="rc-info"><span class="rc-name">{_esc(r.group_name)}</span>'
        f'<span class="rc-m">👥 {mc} membro{"s" if mc!=1 else ""}</span></div>'
        f'<span class="rc-arr">→</span></a>'
        for r, mc in rows
    ) or '<div class="empty-r">Nenhuma turma ainda. Seja o primeiro a criar uma!</div>'

    share_text = (f"📚 Ei, você {verb_past} {inst.name}?\n\n"
                  f"Tem uma sala no TimeMates onde ex-colegas estão se reencontrando! "
                  f"É grátis e você pode encontrar quem não vê faz tempo 🥹\n\n"
                  f"👉 {canonical}")
    wa_url = f"https://wa.me/?text={_re.sub(chr(10), '%0A', share_text).replace(' ','%20')}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={canonical}"

    body = f"""
<div class="hero">
  <div class="hero-ic">{type_icon}</div>
  <h1>{_esc(inst.name)}</h1>
  <div class="hero-sub">{_esc(type_label)}{(" · " + _esc(location)) if location else ""}</div>
  <div class="stats">
    <div class="st"><div class="st-n">{room_count}</div><div class="st-l">turma{"s" if room_count!=1 else ""}</div></div>
    <div class="st"><div class="st-n">{member_count}</div><div class="st-l">membro{"s" if member_count!=1 else ""} reunido{"s" if member_count!=1 else ""}</div></div>
  </div>
</div>
<div class="sec">
  <h2>📚 Turmas cadastradas</h2>
  {rooms_html}
</div>
<div class="cta">
  <h2>Você fez parte de {_esc(inst.name)}?</h2>
  <p>Crie sua conta grátis e encontre seus colegas, amigos e pessoas que cruzaram sua vida nesta {_esc(place_word)}.</p>
  <a href="{BASE_URL}/index.html" class="btn-cta">Encontrar minha turma — é grátis →</a>
</div>
<div class="share-sec">
  <div class="share-box">
    <h3>📤 Chame seus ex-colegas</h3>
    <p>Cole no grupo do WhatsApp, Facebook ou e-mail da sua turma. Quanto mais gente, melhor!</p>
    <div class="share-txt" id="st-inst">{_esc(share_text)}</div>
    <div class="share-btns">
      <button class="btn-copy" onclick="copyShare('st-inst')">📋 Copiar</button>
      <a href="{wa_url}" class="btn-wa" target="_blank" rel="noopener">💬 Enviar no WhatsApp</a>
    </div>
    <div class="qr-wrap">
      <img src="{qr_url}" width="150" height="150" alt="QR Code" loading="lazy"/>
      <p>QR Code para compartilhar pessoalmente</p>
    </div>
  </div>
</div>"""

    return HTMLResponse(_page_html(og_title, og_desc, canonical, body))


@app.get("/r/{room_id}", response_class=HTMLResponse)
def room_public_page(room_id: int, db: Session = Depends(get_db)):
    """Página pública SEO-otimizada de uma sala/turma."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")

    inst = room.institution
    member_count = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "approved"
    ).count()
    last_msg = db.query(Message).filter(Message.room_id == room_id).order_by(Message.created_at.desc()).first()

    canonical = f"{BASE_URL}/r/{room_id}"
    inst_url = f"{BASE_URL}/p/{inst.id}/{_slugify(inst.name)}"

    og_title = f"Turma {room.year} — {room.group_name} | {inst.name} | TimeMates"
    og_desc = (f"{member_count} membro{'s' if member_count!=1 else ''} reunido{'s' if member_count!=1 else ''}. "
               f"Você estava na turma de {room.year} de {inst.name}? Entre no TimeMates e reencontre seus colegas!")

    share_text = (f"🎓 Ei, você era da turma {room.year} de {inst.name}?\n\n"
                  f"A turma {room.group_name} tem uma sala no TimeMates! "
                  f"Já somos {member_count} membro{'s' if member_count!=1 else ''} e queremos te encontrar 🥹\n\n"
                  f"👉 {canonical}")
    wa_url = f"https://wa.me/?text={_re.sub(chr(10), '%0A', share_text).replace(' ','%20')}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={canonical}"
    last_activity = ""
    if last_msg:
        diff = datetime.utcnow() - last_msg.created_at
        if diff.days == 0:
            last_activity = "Ativa hoje"
        elif diff.days == 1:
            last_activity = "Ativa ontem"
        elif diff.days < 7:
            last_activity = f"Ativa há {diff.days} dias"
        else:
            last_activity = f"Última msg em {last_msg.created_at.strftime('%d/%m/%Y')}"

    body = f"""
<div class="hero">
  <div class="hero-ic">🎓</div>
  <h1>Turma {room.year}</h1>
  <div class="hero-sub">{_esc(room.group_name)} · <a href="{inst_url}" style="color:rgba(255,255,255,.8);text-decoration:underline">{_esc(inst.name)}</a></div>
  <div class="stats">
    <div class="st"><div class="st-n">{member_count}</div><div class="st-l">membro{"s" if member_count!=1 else ""} reunido{"s" if member_count!=1 else ""}</div></div>
    {('<div class="st"><div class="st-n" style="font-size:1rem;padding-top:8px">🟢</div><div class="st-l">' + last_activity + "</div></div>") if last_activity else ""}
  </div>
</div>
<div class="cta">
  <h2>Você estava nessa turma?</h2>
  <p>Crie sua conta grátis, solicite acesso e reencontre seus colegas de {_esc(inst.name)} da turma de {room.year}.</p>
  <a href="{BASE_URL}/index.html" class="btn-cta">Entrar na turma — é grátis →</a>
</div>
<div class="share-sec">
  <div class="share-box">
    <h3>📤 Chame seus colegas de turma</h3>
    <p>Cole esse texto no grupo do WhatsApp ou Facebook da turma e traga mais colegas!</p>
    <div class="share-txt" id="st-room">{_esc(share_text)}</div>
    <div class="share-btns">
      <button class="btn-copy" onclick="copyShare('st-room')">📋 Copiar</button>
      <a href="{wa_url}" class="btn-wa" target="_blank" rel="noopener">💬 Enviar no WhatsApp</a>
    </div>
    <div class="qr-wrap">
      <img src="{qr_url}" width="150" height="150" alt="QR Code" loading="lazy"/>
      <p>QR Code para compartilhar pessoalmente</p>
    </div>
  </div>
</div>"""

    return HTMLResponse(_page_html(og_title, og_desc, canonical, body))


@app.get("/u/{user_id}", response_class=HTMLResponse)
def user_public_page(user_id: int, db: Session = Depends(get_db)):
    """Página pública de perfil de um usuário."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    canonical = f"{BASE_URL}/u/{user_id}"
    name = _esc(user.full_name)
    initials = "".join(w[0] for w in user.full_name.split()[:2]).upper()
    profession = _esc(user.profession or "")
    city = _esc(user.city or "")
    sub_parts = [p for p in [profession if user.show_profession else "", city if user.show_city else ""] if p]
    subtitle = " · ".join(sub_parts) or "Membro do TimeMates"

    og_title = f"{user.full_name} | TimeMates"
    og_desc = f"{subtitle}. Conecte-se com {user.full_name.split()[0]} e seus ex-colegas no TimeMates."

    # Salas públicas do usuário
    memberships = db.query(RoomMembership).filter(
        RoomMembership.user_id == user_id,
        RoomMembership.status == "approved",
    ).all()

    rooms_html = ""
    for m in memberships[:12]:
        r = m.room
        inst = r.institution
        rooms_html += (
            f'<a href="{BASE_URL}/r/{r.id}" class="rc" style="margin-bottom:8px;">'
            f'<span class="rc-year">{r.year}</span>'
            f'<div class="rc-info">'
            f'<span class="rc-name">{_esc(r.group_name)}</span>'
            f'<span class="rc-m">{_esc(inst.name)}</span></div>'
            f'<span class="rc-arr">→</span></a>'
        )
    if not rooms_html:
        rooms_html = '<div class="empty-r">Nenhuma sala pública ainda.</div>'

    avatar = (f'<img src="{BASE_URL}{_esc(user.profile_photo)}" '
              f'style="width:96px;height:96px;border-radius:50%;object-fit:cover;'
              f'border:4px solid #D4A853;" alt="{name}"/>'
              if user.profile_photo else
              f'<div style="width:96px;height:96px;border-radius:50%;background:#D4A853;'
              f'color:#1E3A5F;font-size:2rem;font-weight:800;display:flex;align-items:center;'
              f'justify-content:center;border:4px solid rgba(255,255,255,.3);">{initials}</div>')

    body = f"""
<div class="hero" style="padding:40px 24px 48px;">
  <div style="margin-bottom:16px;">{avatar}</div>
  <h1 style="font-size:1.6rem;">{name}</h1>
  <div class="hero-sub">{_esc(subtitle)}</div>
</div>
<div class="sec">
  <h2>🚪 Turmas que participa</h2>
  {rooms_html}
</div>
<div class="cta">
  <h2>Você conhece {_esc(user.full_name.split()[0])}?</h2>
  <p>Entre no TimeMates, encontre sua turma e reencontre pessoas que fizeram parte da sua história.</p>
  <a href="{BASE_URL}/index.html" class="btn-cta">Criar conta grátis →</a>
</div>"""

    return HTMLResponse(_page_html(og_title, og_desc, canonical, body))


@app.get("/sitemap.xml", response_class=Response)
def sitemap(db: Session = Depends(get_db)):
    """Sitemap XML para indexação pelo Google."""
    insts = db.query(Institution).filter(Institution.approved == True).order_by(Institution.id).all()
    rooms = db.query(Room).order_by(Room.id).all()
    users = db.query(User).filter(User.is_active == True).order_by(User.id).all()

    urls = [f"  <url><loc>{BASE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>"]
    for inst in insts:
        slug = _slugify(inst.name)
        urls.append(f"  <url><loc>{BASE_URL}/p/{inst.id}/{slug}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>")
    for r in rooms:
        urls.append(f"  <url><loc>{BASE_URL}/r/{r.id}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>")
    for u in users:
        urls.append(f"  <url><loc>{BASE_URL}/u/{u.id}</loc><changefreq>monthly</changefreq><priority>0.5</priority></url>")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls)
    xml += "\n</urlset>"
    return Response(content=xml, media_type="application/xml")


@app.get("/api/rooms/{room_id}/share-kit")
def room_share_kit(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna textos prontos e links para compartilhamento da sala."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")

    inst = room.institution
    member_count = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "approved"
    ).count()

    room_url = f"{BASE_URL}/r/{room_id}"
    inst_url = f"{BASE_URL}/p/{inst.id}/{_slugify(inst.name)}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={room_url}"

    whatsapp_text = (f"🎓 Ei, você era da turma {room.year} de {inst.name}?\n\n"
                     f"A turma '{room.group_name}' tem uma sala no TimeMates! "
                     f"Já somos {member_count} membro{'s' if member_count!=1 else ''} e queremos te encontrar 🥹\n\n"
                     f"👉 {room_url}")

    facebook_text = (f"Oi pessoal! Quem era da turma {room.year} de {inst.name}?\n\n"
                     f"Criamos uma sala no TimeMates — uma plataforma gratuita para ex-alunos se reencontrarem. "
                     f"Entra lá, é rapidinho e você vai lembrar de muita gente! 😊\n\n"
                     f"🔗 {room_url}")

    email_text = (f"Assunto: Nos encontramos no TimeMates — turma {room.year} de {inst.name}\n\n"
                  f"Oi!\n\nSaudade de vocês! Criei uma sala no TimeMates para a nossa turma {room.year} "
                  f"de {inst.name}.\n\nJá tem {member_count} membro{'s' if member_count!=1 else ''} lá. "
                  f"É grátis e leva menos de 2 minutos para criar sua conta.\n\n"
                  f"👉 {room_url}\n\nAbrações!")

    return {
        "room_url": room_url,
        "inst_url": inst_url,
        "qr_url": qr_url,
        "whatsapp_text": whatsapp_text,
        "facebook_text": facebook_text,
        "email_text": email_text,
        "member_count": member_count,
    }


# ─── Static / Invite page ─────────────────────────────────────────────────────

@app.get("/sw.js")
def service_worker():
    return FileResponse("static/sw.js", media_type="application/javascript")

@app.get("/google_CAIfv-vYcBhk0WeyPAj9RQkRuwETlAKHoz4cqoArjw.html")
def google_verify():
    """Arquivo de verificação alternativo do Google Search Console."""
    return Response(
        content="google-site-verification: google_CAIfv-vYcBhk0WeyPAj9RQkRuwETlAKHoz4cqoArjw.html",
        media_type="text/html"
    )

@app.get("/convite/{token}")
def invite_page(token: str):
    return FileResponse("static/index.html")


# ─── Open Graph deep links (/r/{id} e /i/{id}) ───────────────────────────────
# Servem o mesmo SPA mas com OG tags dinâmicas para preview no Facebook/WhatsApp.

def _inject_og(og_title: str, og_desc: str, og_url: str) -> Response:
    """Lê index.html, substitui as OG tags estáticas por tags dinâmicas e retorna."""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html = f.read()
    except Exception:
        return FileResponse("static/index.html")

    og_block = (
        f'<meta property="og:title" content="{og_title}"/>\n'
        f'<meta property="og:description" content="{og_desc}"/>\n'
        f'<meta property="og:url" content="{og_url}"/>\n'
        f'<meta name="twitter:title" content="{og_title}"/>\n'
        f'<meta name="twitter:description" content="{og_desc}"/>\n'
    )
    # Substitui apenas as tags og:title, og:description, og:url e twitter equivalentes
    # Usa [^>]* em vez de [^/]* para não travar em URLs que contêm barras (://)
    import re as _re
    for tag in ("og:title", "og:description", "og:url", "twitter:title", "twitter:description"):
        html = _re.sub(rf'<meta property="{tag}"[^>]*/>', "", html)
        html = _re.sub(rf'<meta name="{tag}"[^>]*/>', "", html)
    # Insere logo após <meta name="theme-color"...>
    html = _re.sub(
        r'(<meta name="theme-color"[^>]*/>)',
        r'\1\n' + og_block,
        html, count=1,
    )
    return Response(content=html, media_type="text/html")


@app.get("/r/{room_id}")
def room_og_page(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        return FileResponse("static/index.html")
    count = db.query(RoomMembership).filter(
        RoomMembership.room_id == room_id, RoomMembership.status == "approved"
    ).count()
    title = f"{room.group_name} — {room.institution.name} | TimeMates"
    desc  = (
        f"{'Já somos' if count > 1 else 'Seja o primeiro!'} "
        f"{count} ex-aluno{'s' if count != 1 else ''} nessa sala. "
        f"Entre e reencontre seus colegas de {room.institution.city or 'escola'} — grátis!"
    )
    url = f"https://timemates.onrender.com/r/{room_id}"
    return _inject_og(title, desc, url)


@app.get("/i/{institution_id}")
def institution_og_page(institution_id: int, db: Session = Depends(get_db)):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        return FileResponse("static/index.html")
    room_count = db.query(Room).filter(Room.institution_id == institution_id).count()
    title = f"{inst.name} | TimeMates"
    desc  = (
        f"{room_count} sala{'s' if room_count != 1 else ''} de ex-alunos de "
        f"{inst.city or inst.name}. Entre, escolha sua época e reencontre seus colegas — grátis!"
    )
    url = f"https://timemates.onrender.com/i/{institution_id}"
    return _inject_og(title, desc, url)




# ===== LOCAL NEWS & EVENTS API =====

@app.get("/api/news/{city}")
@limiter.limit("30/minute")
def get_news(request: Request, city: str = "", page: int = 1, limit: int = 10, db: Session = Depends(get_db)):
    """📰 Listar notícias locais por cidade (paginado)"""
    if not city:
        return {"success": False, "error": "Cidade é obrigatória"}

    offset = (page - 1) * limit
    total = db.query(LocalNews).filter(LocalNews.city.ilike(f"%{city}%")).count()
    news = db.query(LocalNews).filter(
        LocalNews.city.ilike(f"%{city}%")
    ).order_by(LocalNews.published_at.desc()).offset(offset).limit(limit).all()

    return {
        "success": True,
        "data": [
            {
                "id": n.id,
                "title": n.title,
                "content": n.content[:200],
                "category": n.category,
                "city": n.city,
                "image_url": n.image_url,
                "source": n.source,
                "published_at": n.published_at.isoformat() if n.published_at else None,
                "created_at": n.created_at.isoformat()
            } for n in news
        ],
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }


# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# @app.get("/api/events/{city}")
# @limiter.limit("30/minute")
# def get_events(request: Request, city: str = "", db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user)):
#     """Listar proximos eventos locais"""
#     track_event(current_user.id if current_user else None, "city_view", {"city": city})
#     if not city:
#         return {"success": False, "error": "Cidade e obrigatoria", "data": [], "total": 0}
#
#     try:
#         from datetime import datetime as dt
#         today = dt.utcnow().strftime("%Y-%m-%d")
#
#         events = db.query(LocalEvent).filter(
#             LocalEvent.city.ilike(f"%{city}%"),
#             LocalEvent.date >= today,
#             LocalEvent.status == "active"
#         ).order_by(LocalEvent.date.asc()).limit(10).all()
#
#         result = []
#         for e in events:
#             try:
#                 rsvp_count = db.query(EventRSVP).filter(
#                     EventRSVP.event_id == e.id,
#                     EventRSVP.status == "going"
#                 ).count()
#             except Exception:
#                 rsvp_count = 0
#             creator_name = "Admin"
#             try:
#                 if e.created_by and getattr(e.created_by, "full_name", None):
#                     creator_name = e.created_by.full_name
#             except Exception:
#                 creator_name = "Admin"
#             result.append({
#                 "id": e.id,
#                 "title": e.title,
#                 "date": e.date,
#                 "time": e.time,
#                 "location": e.location,
#                 "description": e.description,
#                 "image_url": e.image_url,
#                 "rsvp_count": rsvp_count,
#                 "created_by": creator_name
#             })
#
#         return {"success": True, "data": result, "total": len(result)}
#     except Exception as ex:
#         print(f"[EVENTS] Error fetching events for city={city}: {ex}")
#         return {"success": True, "data": [], "total": 0, "error": str(ex)}
#
#
# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# @app.post("/api/events")
# @limiter.limit("20/minute")
# def create_event(
#     request: Request,
#     title: str = "",
#     date: str = "",
#     time: str = "",
#     location: str = "",
#     description: str = "",
#     city: str = "",
#     current_user: User = Depends(get_current_user_required),
#     db: Session = Depends(get_db),
# ):
#     """Criar novo evento (room members only)"""
#     if not all([title, date, location, city]):
#         raise HTTPException(status_code=400, detail="Campos obrigatorios faltando")
#
#     event = LocalEvent(
#         title=title,
#         date=date,
#         time=time,
#         location=location,
#         description=description,
#         city=city,
#         created_by_id=current_user.id,
#         status="active"
#     )
#     db.add(event)
#     db.commit()
#     db.refresh(event)
#
#     # Notificar todos os usuarios da cidade
#     _push_to_user(
#         db, current_user.id,
#         f"Evento criado: {title}",
#         f"{date} em {location}",
#         f"/events/{event.id}"
#     )
#
#     return {"success": True, "event_id": event.id, "message": "Evento criado com sucesso"}
#
#
# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# @app.post("/api/events/{event_id}/rsvp")
# @limiter.limit("50/minute")
# def rsvp_event(
#     request: Request,
#     event_id: int,
#     status: str = "going",
#     current_user: User = Depends(get_current_user_required),
#     db: Session = Depends(get_db),
# ):
#     """RSVP para um evento (going/interested/not_going)"""
#     if status not in ["going", "interested", "not_going"]:
#         raise HTTPException(status_code=400, detail="Status invalido")
#
#     event = db.query(LocalEvent).filter(LocalEvent.id == event_id).first()
#     if not event:
#         raise HTTPException(status_code=404, detail="Evento nao encontrado")
#
#     existing = db.query(EventRSVP).filter(
#         EventRSVP.event_id == event_id,
#         EventRSVP.user_id == current_user.id
#     ).first()
#
#     if existing:
#         existing.status = status
#     else:
#         db.add(EventRSVP(event_id=event_id, user_id=current_user.id, status=status))
#
#     db.commit()
#
#     going_count = db.query(EventRSVP).filter(
#         EventRSVP.event_id == event_id,
#         EventRSVP.status == "going"
#     ).count()
#
#     return {
#         "success": True,
#         "message": f"RSVP atualizado para '{status}'",
#         "event_id": event_id,
#         "rsvp_count": going_count
#     }


@app.get("/api/trending/{city}")
@limiter.limit("40/minute")
def get_trending(request: Request, city: str = "", db: Session = Depends(get_db)):
    """🔥 Listar trending topics da cidade"""
    if not city:
        return {"success": False, "error": "Cidade é obrigatória"}

    trending = db.query(TrendingTopic).filter(
        TrendingTopic.city.ilike(f"%{city}%")
    ).order_by(TrendingTopic.mention_count.desc()).limit(10).all()

    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "hashtag": t.hashtag,
                "mention_count": t.mention_count,
                "trending_since": t.trending_since.isoformat(),
                "sample_messages": t.sample_messages or []
            } for t in trending
        ],
        "total": len(trending)
    }


@app.get("/api/highlights/week")
@limiter.limit("60/minute")
def get_weekly_highlights(request: Request, db: Session = Depends(get_db)):
    """⭐ Destaques da semana (top messages, photos, people returned, etc)"""
    from datetime import datetime as dt, timedelta

    today = dt.utcnow().strftime("%Y-%m-%d")
    week_start = (dt.utcnow() - timedelta(days=dt.utcnow().weekday())).strftime("%Y-%m-%d")

    highlights = db.query(WeeklyHighlight).filter(
        WeeklyHighlight.week_starting == week_start
    ).order_by(WeeklyHighlight.category, WeeklyHighlight.rank).all()

    result = {
        "top_messages": [],
        "top_photos": [],
        "people_returned": [],
        "new_rooms": [],
        "trending": []
    }

    for h in highlights:
        category = h.category
        if category in result:
            result[category].append({
                "id": h.id,
                "item_type": h.item_type,
                "item_id": h.item_id,
                "rank": h.rank
            })

    return {"success": True, "data": result, "week_starting": week_start}


@app.post("/api/admin/news")
@limiter.limit("20/minute")
def admin_create_news(
    request: Request,
    title: str = "",
    content: str = "",
    city: str = "",
    category: str = "breaking_news",
    image_url: str = "",
    source: str = "TimeMates",
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🔐 Admin: Criar notícia manualmente"""
    if not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Apenas admins podem criar notícias")

    if not all([title, content, city]):
        raise HTTPException(status_code=400, detail="Campos obrigatórios faltando")

    from datetime import datetime as dt, timedelta
    news = LocalNews(
        title=title,
        content=content,
        city=city,
        category=category,
        image_url=image_url,
        source=source,
        published_at=dt.utcnow(),
        ttl_expires_at=dt.utcnow() + timedelta(days=7)
    )
    db.add(news)
    db.commit()
    db.refresh(news)

    return {"success": True, "news_id": news.id, "message": "Notícia criada"}


@app.delete("/api/admin/news/{news_id}")
@limiter.limit("20/minute")
def admin_delete_news(
    request: Request,
    news_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🔐 Admin: Deletar notícia"""
    if not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Apenas admins podem deletar")

    news = db.query(LocalNews).filter(LocalNews.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="Notícia não encontrada")

    db.delete(news)
    db.commit()

    return {"success": True, "message": "Notícia deletada"}


@app.delete("/api/admin/events/{event_id}")
@limiter.limit("20/minute")
def admin_cancel_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🔐 Admin: Cancelar evento"""
    event = db.query(LocalEvent).filter(LocalEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    if event.created_by_id != current_user.id and not current_user.is_system_admin:
        raise HTTPException(status_code=403, detail="Apenas criador ou admin pode cancelar")

    event.status = "cancelled"
    db.commit()

    # Notificar todos que RSVP'd
    rsvps = db.query(EventRSVP).filter(EventRSVP.event_id == event_id).all()
    for rsvp in rsvps:
        _push_to_user(db, rsvp.user_id, "❌ Evento cancelado", f"O evento '{event.title}' foi cancelado")

    return {"success": True, "message": "Evento cancelado"}


@app.get("/api/stats/news")
@limiter.limit("100/minute")
def get_news_stats(request: Request, db: Session = Depends(get_db)):
    """📊 Estatísticas de notícias locais"""
    news_count = db.query(LocalNews).count()
    events_count = db.query(LocalEvent).filter(LocalEvent.status == "active").count()
    rsvp_count = db.query(EventRSVP).count()
    trending_count = db.query(TrendingTopic).count()

    return {
        "success": True,
        "data": {
            "news": news_count,
            "events": events_count,
            "rsvps": rsvp_count,
            "trending_topics": trending_count
        }
    }


# ===== CITIES & GAMIFICATION API (27 CAPITAIS BRASILEIRAS) =====

# Função para normalizar texto (remover acentos)
import unicodedata

def normalize_text(text):
    """Remove acentos e normaliza para busca"""
    nfd = unicodedata.normalize('NFD', str(text))
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn').lower()

# Importar serviço IBGE
try:
    from ibge_service import IBGEService, get_city_data_with_ibge
except Exception:
    print("[WARN] ibge_service não encontrado, IBGE integration desabilitada")
    IBGEService = None

@app.get("/api/cities/search")
@limiter.limit("60/minute")
def search_cities(request: Request, q: str = "", db: Session = Depends(get_db)):
    """🔍 Buscar cidades por nome (funciona com e sem acentos)"""
    if len(q.strip()) < 1:
        return {"success": True, "data": [], "query": q}

    # Normalizar query
    q_normalized = normalize_text(q)

    # Buscar todas as cidades
    all_cities = db.query(City).all()

    # Filtrar com normalização
    results = []
    for city in all_cities:
        city_normalized = normalize_text(city.name)
        if q_normalized in city_normalized or city_normalized in q_normalized:
            results.append({
                "id": city.id,
                "slug": city.slug,
                "name": city.name,
                "state": city.state,
                "population": city.population,
            })

    return {
        "success": True,
        "query": q,
        "data": results,
        "total": len(results)
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CITY SCALING INFRASTRUCTURE (300 cities support)
# State → Region mapping (City model has no `region` column, derive from state)
# ═══════════════════════════════════════════════════════════════════════════════
STATE_TO_REGION = {
    # Norte
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    # Nordeste
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    # Centro-Oeste
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    # Sudeste
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    # Sul
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

REGIONS_VALID = {"Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"}

def _states_in_region(region: str) -> List[str]:
    region_norm = region.strip()
    # Tolerate "centro-oeste"/"centrooeste"/"Centro Oeste"
    region_norm_l = region_norm.lower().replace(" ", "-").replace("--", "-")
    target = None
    for r in REGIONS_VALID:
        if r.lower() == region_norm_l or r.lower().replace("-", "") == region_norm_l.replace("-", ""):
            target = r
            break
    if target is None:
        return []
    return [st for st, reg in STATE_TO_REGION.items() if reg == target]


# Simple in-process TTL cache for /api/cities/featured (static-ish data)
_FEATURED_CACHE: Dict[str, object] = {"payload": None, "expires_at": 0.0}
_FEATURED_CACHE_TTL_SECONDS = 300  # 5 minutes


def _city_to_payload(city, news_count: int = 0, events_count: int = 0, total_users: int = 0, total_cities: int = 27):
    try:
        coords = city.coordinates if city.coordinates is not None else {}
    except Exception:
        coords = {}
    return {
        "id": city.id,
        "slug": city.slug,
        "name": city.name,
        "state": city.state,
        "region": STATE_TO_REGION.get(city.state, "Desconhecida"),
        "population": city.population,
        "coordinates": coords,
        "landmark_image": city.landmark_image,
        "stats": {
            "news": news_count,
            "events": events_count,
            "users": max(10, total_users // max(total_cities, 1)) if total_users else 10,
            "engagement_score": round((news_count + events_count) * 1.5, 1)
        }
    }


def _probe_news_events_tables(db: Session):
    """Probe LocalNews/LocalEvent tables once — return (news_ok, events_ok)."""
    news_table_ok = True
    events_table_ok = True
    try:
        db.query(LocalNews).limit(1).all()
    except Exception:
        logger.warning("[/api/cities] tabela local_news indisponível — news_count=0")
        news_table_ok = False
        try:
            db.rollback()
        except Exception:
            pass
    try:
        db.query(LocalEvent).limit(1).all()
    except Exception:
        logger.warning("[/api/cities] tabela local_events indisponível — events_count=0")
        events_table_ok = False
        try:
            db.rollback()
        except Exception:
            pass
    return news_table_ok, events_table_ok


@app.get("/api/cities")
@limiter.limit("60/minute")
def list_cities(
    request: Request,
    page: int = Query(1, ge=1, description="Página (1-based)"),
    limit: int = Query(50, ge=1, le=200, description="Itens por página (max 200)"),
    state: Optional[str] = Query(None, description="Filtrar por UF, ex. SP"),
    region: Optional[str] = Query(None, description="Filtrar por região: Norte, Nordeste, Centro-Oeste, Sudeste, Sul"),
    min_pop: Optional[int] = Query(None, ge=0, description="População mínima"),
    q: Optional[str] = Query(None, description="Busca textual no nome"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """🌍 Listar cidades brasileiras (paginado, filtrável).

    BACKWARDS-COMPAT: continua retornando {"success", "data", "total"} no formato antigo,
    PLUS metadados de paginação ("page", "limit", "total_pages", "filters_applied").
    Default limit=50 cobre as 27 capitais originais em 1 página.

    REGRESSION TEST (inline): GET /api/cities (sem params) deve retornar HTTP 200 com
    todas as cidades atuais (≤50) na primeira página. UTF-8 names like "São Paulo",
    "Brasília", "Vitória" devem serializar corretamente. Se LocalNews/LocalEvent
    falhar (tabela ausente), stats default = 0 — nunca 500.
    """
    track_event(current_user.id if current_user else None, "city_list_view")

    filters_applied: Dict[str, object] = {}

    # Build base query with DB-side filters (uses indexes on state/population)
    try:
        query = db.query(City)

        if state:
            state_norm = state.strip().upper()
            query = query.filter(City.state == state_norm)
            filters_applied["state"] = state_norm

        if region:
            states_in = _states_in_region(region)
            if not states_in:
                return {
                    "success": False,
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "total_pages": 0,
                    "filters_applied": {"region": region},
                    "error": f"unknown_region: {region}",
                }
            query = query.filter(City.state.in_(states_in))
            filters_applied["region"] = region

        if min_pop is not None:
            query = query.filter(City.population >= min_pop)
            filters_applied["min_pop"] = min_pop

        if q and q.strip():
            q_clean = q.strip()
            # ILIKE for accent-insensitive-ish prefix/substring; Postgres ILIKE is case-insensitive
            query = query.filter(City.name.ilike(f"%{q_clean}%"))
            filters_applied["q"] = q_clean

        total = query.count()
        total_pages = (total + limit - 1) // limit if total else 0

        offset = (page - 1) * limit
        cities = query.order_by(City.population.desc().nullslast(), City.name.asc()).offset(offset).limit(limit).all()
    except Exception as exc:
        logger.exception("[/api/cities] Falha ao consultar tabela cities: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "success": False,
            "data": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "total_pages": 0,
            "filters_applied": filters_applied,
            "error": "db_unavailable",
        }

    # Pre-compute total memberships once (avoid N+1)
    try:
        total_users = db.query(RoomMembership).count()
    except Exception:
        logger.exception("[/api/cities] Falha ao contar RoomMembership; usando 0")
        try:
            db.rollback()
        except Exception:
            pass
        total_users = 0

    # Probe optional tables once
    news_table_ok, events_table_ok = _probe_news_events_tables(db)

    # Use total cities globally (not paged subset) for users/city distribution
    try:
        total_cities_global = db.query(City).count() or 27
    except Exception:
        total_cities_global = 27
        try:
            db.rollback()
        except Exception:
            pass

    result = []
    for city in cities:
        news_count = 0
        events_count = 0
        if news_table_ok:
            try:
                news_count = db.query(LocalNews).filter(LocalNews.city == city.name).count()
            except Exception:
                logger.exception("[/api/cities] news_count falhou para %s", city.name)
                try:
                    db.rollback()
                except Exception:
                    pass
                news_table_ok = False
        if events_table_ok:
            try:
                events_count = db.query(LocalEvent).filter(LocalEvent.city == city.name).count()
            except Exception:
                logger.exception("[/api/cities] events_count falhou para %s", city.name)
                try:
                    db.rollback()
                except Exception:
                    pass
                events_table_ok = False

        result.append(_city_to_payload(city, news_count, events_count, total_users, total_cities_global))

    return {
        "success": True,
        "data": result,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "filters_applied": filters_applied,
    }


@app.get("/api/cities/featured")
@limiter.limit("120/minute")
def list_featured_cities(request: Request, db: Session = Depends(get_db)):
    """⭐ Top 27 capitais (backwards-compat para o mapa do frontend).

    Resposta cacheada em memória por 5 minutos — dados quase estáticos.
    Sem paginação. Use /api/cities para a lista paginada completa.
    """
    import time
    now = time.time()
    cached_payload = _FEATURED_CACHE.get("payload")
    cached_expires = _FEATURED_CACHE.get("expires_at", 0.0)
    if cached_payload is not None and isinstance(cached_expires, (int, float)) and now < cached_expires:
        return cached_payload

    try:
        cities = db.query(City).order_by(City.population.desc().nullslast(), City.name.asc()).limit(27).all()
    except Exception as exc:
        logger.exception("[/api/cities/featured] db erro: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "data": [], "total": 0, "error": "db_unavailable"}

    try:
        total_users = db.query(RoomMembership).count()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        total_users = 0

    news_table_ok, events_table_ok = _probe_news_events_tables(db)

    data = []
    for city in cities:
        news_count = 0
        events_count = 0
        if news_table_ok:
            try:
                news_count = db.query(LocalNews).filter(LocalNews.city == city.name).count()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                news_table_ok = False
        if events_table_ok:
            try:
                events_count = db.query(LocalEvent).filter(LocalEvent.city == city.name).count()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
                events_table_ok = False
        data.append(_city_to_payload(city, news_count, events_count, total_users, max(len(cities), 27)))

    payload = {
        "success": True,
        "data": data,
        "total": len(data),
        "cached_ttl_seconds": _FEATURED_CACHE_TTL_SECONDS,
    }
    _FEATURED_CACHE["payload"] = payload
    _FEATURED_CACHE["expires_at"] = now + _FEATURED_CACHE_TTL_SECONDS
    return payload


@app.get("/api/cities/by-state/{state}")
@limiter.limit("60/minute")
def list_cities_by_state(request: Request, state: str, db: Session = Depends(get_db)):
    """🏙️ Todas as cidades de uma UF (sem paginação — esperado ≤30 cada).
    Ex: /api/cities/by-state/SP
    """
    state_norm = (state or "").strip().upper()
    if len(state_norm) != 2 or not state_norm.isalpha():
        return {"success": False, "data": [], "total": 0, "error": "invalid_state_code"}
    try:
        cities = (
            db.query(City)
            .filter(City.state == state_norm)
            .order_by(City.population.desc().nullslast(), City.name.asc())
            .all()
        )
    except Exception as exc:
        logger.exception("[/api/cities/by-state] db erro: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "data": [], "total": 0, "error": "db_unavailable"}

    data = [_city_to_payload(c, 0, 0, 0, max(len(cities), 1)) for c in cities]
    return {
        "success": True,
        "state": state_norm,
        "region": STATE_TO_REGION.get(state_norm, "Desconhecida"),
        "data": data,
        "total": len(data),
    }


@app.get("/api/cities/by-region/{region}")
@limiter.limit("60/minute")
def list_cities_by_region(request: Request, region: str, db: Session = Depends(get_db)):
    """🗺️ Todas as cidades de uma região (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
    Ex: /api/cities/by-region/Sudeste
    """
    states_in = _states_in_region(region)
    if not states_in:
        return {"success": False, "data": [], "total": 0, "error": f"unknown_region: {region}"}
    try:
        cities = (
            db.query(City)
            .filter(City.state.in_(states_in))
            .order_by(City.population.desc().nullslast(), City.name.asc())
            .all()
        )
    except Exception as exc:
        logger.exception("[/api/cities/by-region] db erro: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return {"success": False, "data": [], "total": 0, "error": "db_unavailable"}

    data = [_city_to_payload(c, 0, 0, 0, max(len(cities), 1)) for c in cities]
    return {
        "success": True,
        "region": region,
        "states": states_in,
        "data": data,
        "total": len(data),
    }


@app.get("/api/cities/top10/with-regions")
@limiter.limit("60/minute")
def get_top10_cities_with_regions(request: Request, db: Session = Depends(get_db)):
    """🗺️ Top 10 maiores cidades com regiões metropolitanas e coordenadas"""
    cities = db.query(City).order_by(City.population.desc()).limit(10).all()

    # Dados de regiões metropolitanas brasileiras
    metropolitan_regions = {
        "São Paulo": {
            "name": "Região Metropolitana de São Paulo",
            "population": 22183000,
            "cities": ["São Paulo", "Guarulhos", "São Bernardo do Campo", "Santo André"],
            "radius_km": 45
        },
        "Rio de Janeiro": {
            "name": "Região Metropolitana do Rio de Janeiro",
            "population": 13000000,
            "cities": ["Rio de Janeiro", "Niterói", "Duque de Caxias", "São Gonçalo"],
            "radius_km": 40
        },
        "Brasília": {
            "name": "Região Integrada de Desenvolvimento do Distrito Federal e Entorno (RIDE)",
            "population": 4000000,
            "cities": ["Brasília", "Gama", "Taguatinga", "Sobradinho"],
            "radius_km": 30
        },
        "Salvador": {
            "name": "Região Metropolitana de Salvador",
            "population": 4000000,
            "cities": ["Salvador", "Lauro de Freitas", "Simões Filho"],
            "radius_km": 25
        },
        "Belo Horizonte": {
            "name": "Região Metropolitana de Belo Horizonte",
            "population": 6000000,
            "cities": ["Belo Horizonte", "Contagem", "Betim", "Sabará"],
            "radius_km": 35
        },
        "Fortaleza": {
            "name": "Região Metropolitana de Fortaleza",
            "population": 4000000,
            "cities": ["Fortaleza", "Maracanaú", "Caucaia", "Aquiraz"],
            "radius_km": 35
        },
        "Curitiba": {
            "name": "Região Metropolitana de Curitiba",
            "population": 3600000,
            "cities": ["Curitiba", "Pinhais", "Almirante Tamandaré", "Araucária"],
            "radius_km": 30
        },
        "Porto Alegre": {
            "name": "Região Metropolitana de Porto Alegre",
            "population": 4300000,
            "cities": ["Porto Alegre", "Viamão", "Novo Hamburgo", "Gravataí"],
            "radius_km": 35
        },
        "Recife": {
            "name": "Região Metropolitana de Recife",
            "population": 4000000,
            "cities": ["Recife", "Jaboatão dos Guararapes", "Olinda", "Paulista"],
            "radius_km": 30
        },
        "Manaus": {
            "name": "Região Metropolitana de Manaus",
            "population": 2200000,
            "cities": ["Manaus", "Iranduba", "Careiro"],
            "radius_km": 25
        }
    }

    result = []
    for city in cities:
        metro = metropolitan_regions.get(city.name, {})

        result.append({
            "id": city.id,
            "slug": city.slug,
            "name": city.name,
            "state": city.state,
            "population": city.population,
            "rank": len(result) + 1,
            "coordinates": city.coordinates or {"lat": -15.7942, "lng": -47.8822},  # Brasília default
            "metropolitan_region": {
                "name": metro.get("name", f"Região de {city.name}"),
                "population": metro.get("population", city.population * 2),
                "cities": metro.get("cities", [city.name]),
                "radius_km": metro.get("radius_km", 30)
            },
            "nickname": city.nickname or "",
            "stats": {
                "news": db.query(LocalNews).filter(LocalNews.city == city.name).count(),
                "events": db.query(LocalEvent).filter(LocalEvent.city == city.name).count()
            }
        })

    return {
        "success": True,
        "data": result,
        "total": len(result),
        "center": {"lat": -14.2350, "lng": -51.9253},  # Brasil center
        "zoom": 4
    }


@app.get("/api/city/{slug}/info-ibge")
@limiter.limit("30/minute")
def get_city_ibge_info(request: Request, slug: str, db: Session = Depends(get_db)):
    """📊 Informações de uma cidade com dados do IBGE (população em tempo real)"""
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="Cidade não encontrada")

    result = {
        "success": True,
        "city": {
            "id": city.id,
            "slug": city.slug,
            "name": city.name,
            "state": city.state,
            "landmark": city.landmark_image,
            "coordinates": city.coordinates
        },
        "population": {
            "stored_in_db": city.population,
            "last_updated": city.created_at.isoformat() if city.created_at else None
        },
        "ibge": {
            "enabled": IBGEService is not None,
            "note": "Integração com IBGE para população em tempo real"
        }
    }

    # Se IBGE service disponível, tenta buscar dados atualizados
    if IBGEService:
        try:
            # Encontrar código IBGE (simplificado - em produção seria mais robusto)
            ibge_code_map = {
                "sao-paulo": 3550308,
                "rio-de-janeiro": 3304557,
                "belo-horizonte": 3106200,
                "brasilia": 5300108,
                "salvador": 2704302,
                "fortaleza": 2304400,
                "curitiba": 4106902,
                "porto-alegre": 4314902,
                "recife": 2611606,
                "manaus": 1302603,
                "belem": 1501402,
                "sao-luis": 2111300,
                "teresina": 2211001,
                "natal": 2408102,
                "joao-pessoa": 2507507,
                "maceio": 2704302,
                "goiania": 5208707,
                "cuiaba": 5103403,
                "campo-grande": 5002704,
                "florianopolis": 4204402,
                "vitoria": 3505708,
                "macapa": 1600055,
                "porto-velho": 1100205,
                "boa-vista": 1400100,
                "palmas": 2804901,
                "campina-grande": 2504009
            }

            ibge_code = ibge_code_map.get(slug)
            if ibge_code:
                ibge_info = IBGEService.get_city_info(ibge_code)
                ibge_pop = IBGEService.get_population_estimate(ibge_code)

                result["ibge"]["info"] = ibge_info
                result["ibge"]["population"] = ibge_pop

                # Se conseguiu buscar do IBGE, atualiza resultado
                if ibge_pop.get("success"):
                    result["population"]["ibge_current"] = ibge_pop.get("population")
                    result["population"]["source"] = "IBGE API"

        except Exception as e:
            result["ibge"]["error"] = str(e)

    return result


@app.get("/api/city/{slug}")
@limiter.limit("60/minute")
def get_city_dashboard(request: Request, slug: str, db: Session = Depends(get_db)):
    """📊 Dashboard completo de uma cidade com notícias, eventos, desafios"""
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="Cidade não encontrada")

    news = db.query(LocalNews).filter(LocalNews.city == city.name).limit(5).all()
    events = db.query(LocalEvent).filter(LocalEvent.city == city.name).limit(5).all()
    challenges = db.query(CityChallenge).filter(CityChallenge.city_id == city.id).limit(5).all()
    tips = db.query(LocalTip).filter(LocalTip.city_id == city.id).limit(5).all()

    return {
        "success": True,
        "city": {
            "id": city.id,
            "slug": city.slug,
            "name": city.name,
            "state": city.state,
            "population": city.population,
            "landmark_image": city.landmark_image,
            "coordinates": city.coordinates
        },
        "news": [{"id": n.id, "title": n.title, "category": n.category} for n in news],
        "events": [{"id": e.id, "title": e.title, "date": e.date, "location": e.location} for e in events],
        "challenges": [{"id": c.id, "title": c.title, "reward_points": c.reward_points} for c in challenges],
        "tips": [{"id": t.id, "title": t.title, "rating": t.rating} for t in tips]
    }


@app.post("/api/city/{slug}/tips")
@limiter.limit("30/minute")
def submit_tip(
    request: Request,
    slug: str,
    title: str = "",
    description: str = "",
    location: str = "",
    rating: float = 5.0,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """💡 Submeter dica local sobre um lugar na cidade"""
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="Cidade não encontrada")

    tip = LocalTip(
        city_id=city.id,
        user_id=current_user.id,
        title=title,
        description=description,
        location=location,
        rating=min(5.0, max(0.0, rating))
    )
    db.add(tip)
    db.commit()

    return {"success": True, "tip_id": tip.id, "message": "Dica adicionada!"}


@app.get("/api/city/{slug}/challenges")
@limiter.limit("60/minute")
def get_challenges(request: Request, slug: str, db: Session = Depends(get_db)):
    """🎯 Listar desafios semanais de uma cidade"""
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="Cidade não encontrada")

    challenges = db.query(CityChallenge).filter(
        CityChallenge.city_id == city.id,
        CityChallenge.active == True
    ).all()

    return {
        "success": True,
        "city": city.name,
        "challenges": [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "reward_points": c.reward_points,
                "difficulty": c.difficulty,
                "submissions": db.query(ChallengeSubmission).filter(
                    ChallengeSubmission.challenge_id == c.id
                ).count()
            }
            for c in challenges
        ]
    }


@app.post("/api/city/{slug}/challenges/{challenge_id}/submit")
@limiter.limit("30/minute")
def submit_challenge(
    request: Request,
    slug: str,
    challenge_id: int,
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """📸 Submeter foto para desafio (prova de conclusão)"""
    challenge = db.query(CityChallenge).filter(CityChallenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafio não encontrado")

    import uuid
    file_ext = photo.filename.split('.')[-1]
    file_name = f"challenge_{challenge_id}_{current_user.id}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = f"uploads/challenges/{file_name}"

    import os
    os.makedirs("uploads/challenges", exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(photo.file.read())

    submission = ChallengeSubmission(
        challenge_id=challenge_id,
        user_id=current_user.id,
        photo_url=f"/{file_path}",
        approved=False  # Admin aprovação necessária
    )
    db.add(submission)
    db.commit()

    return {"success": True, "submission_id": submission.id, "message": "Foto submetida para aprovação!"}


@app.get("/api/city/{slug}/leaderboard")
@limiter.limit("60/minute")
def get_city_leaderboard(request: Request, slug: str, db: Session = Depends(get_db)):
    """🏆 Top 10 usuários mais engajados em uma cidade"""
    city = db.query(City).filter(City.slug == slug).first()
    if not city:
        raise HTTPException(status_code=404, detail="Cidade não encontrada")

    leaderboards = db.query(CityLeaderboard).filter(
        CityLeaderboard.city_id == city.id
    ).order_by(CityLeaderboard.engagement_score.desc()).limit(10).all()

    return {
        "success": True,
        "city": city.name,
        "leaderboard": [
            {
                "rank": idx + 1,
                "user_id": lb.user_id,
                "engagement_score": lb.engagement_score,
                "rank_position": lb.rank
            }
            for idx, lb in enumerate(leaderboards)
        ]
    }


@app.get("/api/user/badges")
@limiter.limit("60/minute")
def get_user_badges(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🏆 Listar badges desbloqueados do usuário"""
    badges = db.query(CityBadge).filter(CityBadge.user_id == current_user.id).all()

    return {
        "success": True,
        "user_id": current_user.id,
        "badges": [
            {
                "id": b.id,
                "badge_type": b.badge_type,
                "city_id": b.city_id,
                "unlocked_at": b.unlocked_at.isoformat() if b.unlocked_at else None
            }
            for b in badges
        ],
        "total_badges": len(badges)
    }


@app.get("/api/user/streak")
@limiter.limit("60/minute")
def get_user_streak(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🔥 Ver streak do usuário (dias consecutivos)"""
    streak = db.query(UserStreak).filter(UserStreak.user_id == current_user.id).first()

    if not streak:
        return {
            "success": True,
            "current_streak": 0,
            "longest_streak": 0,
            "message": "Comece seu streak visitando o app!"
        }

    return {
        "success": True,
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "last_activity": streak.last_activity_date.isoformat() if streak.last_activity_date else None
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TURMA ENDPOINTS - Reconnection pivot (cohort is the central unit)
# LGPD: default-ghost — public responses only return verified + visibility=visible
# ═══════════════════════════════════════════════════════════════════════════════

import re as _re_turma
import unicodedata as _ud_turma

def _turma_slugify(*parts) -> str:
    raw = "-".join(str(p) for p in parts if p)
    norm = _ud_turma.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    norm = norm.lower()
    norm = _re_turma.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    return norm[:200] or "turma"

def _turma_visible_members(db: Session, turma_id: int):
    """Default-ghost: only verified + visibility='visible' surface publicly."""
    return (
        db.query(TurmaMembership)
        .filter(
            TurmaMembership.turma_id == turma_id,
            TurmaMembership.status == "verified",
            TurmaMembership.visibility == "visible",
        )
        .all()
    )

def _turma_to_dict(t: Turma, db: Session, current_user: Optional[User] = None):
    visible = _turma_visible_members(db, t.id)
    visible_users = []
    if visible:
        user_ids = [m.user_id for m in visible]
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        umap = {u.id: u for u in users}
        for m in visible:
            u = umap.get(m.user_id)
            if not u:
                continue
            visible_users.append({
                "id": u.id,
                "full_name": u.full_name,
                "profile_photo": u.profile_photo,
                "is_founder": m.is_founder,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            })

    membership = None
    if current_user:
        membership = (
            db.query(TurmaMembership)
            .filter(
                TurmaMembership.turma_id == t.id,
                TurmaMembership.user_id == current_user.id,
            )
            .first()
        )

    return {
        "id": t.id,
        "slug": t.slug,
        "institution_id": t.institution_id,
        "institution_name": t.institution_name,
        "city": t.city,
        "state": t.state,
        "kind": t.kind,
        "cohort_year": t.cohort_year,
        "cohort_label": t.cohort_label,
        "founder_id": t.founder_id,
        "total_members": t.total_members,
        "total_verified": t.total_verified,
        "is_unlocked": t.is_unlocked,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "visible_members": visible_users,
        "visible_member_count": len(visible_users),
        "my_membership": (
            {
                "status": membership.status,
                "visibility": membership.visibility,
                "is_founder": membership.is_founder,
                "verified_by_vouches": membership.verified_by_vouches,
            }
            if membership else None
        ),
    }


@app.get("/api/turmas/search")
@limiter.limit("60/minute")
def turmas_search(
    request: Request,
    q: Optional[str] = Query(None, description="institution name fragment"),
    year: Optional[int] = Query(None, description="cohort year"),
    kind: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """🔍 Buscar turmas. Resposta pública NÃO expõe membros ghost — apenas contagens."""
    query = db.query(Turma)
    if q:
        query = query.filter(Turma.institution_name.ilike(f"%{q}%"))
    if year:
        query = query.filter(Turma.cohort_year == year)
    if kind:
        query = query.filter(Turma.kind == kind)
    if city:
        query = query.filter(Turma.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(Turma.state == state.upper())

    results = query.order_by(Turma.created_at.desc()).limit(50).all()
    return {
        "success": True,
        "count": len(results),
        "turmas": [
            {
                "id": t.id,
                "slug": t.slug,
                "institution_name": t.institution_name,
                "city": t.city,
                "state": t.state,
                "kind": t.kind,
                "cohort_year": t.cohort_year,
                "cohort_label": t.cohort_label,
                "total_members": t.total_members,
                "total_verified": t.total_verified,
                "is_unlocked": t.is_unlocked,
                "visible_member_count": len(_turma_visible_members(db, t.id)),
            }
            for t in results
        ],
    }


@app.get("/api/turmas/{slug}")
@limiter.limit("120/minute")
def turma_get(
    request: Request,
    slug: str,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """📚 Detalhes da turma. Membros ghost ficam escondidos."""
    t = db.query(Turma).filter(Turma.slug == slug).first()
    if not t:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    return {"success": True, "turma": _turma_to_dict(t, db, current_user)}


@app.post("/api/turmas")
@limiter.limit("10/minute")
def turma_create(
    request: Request,
    payload: dict,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """➕ Criar nova turma. Qualquer user autenticado pode (vira founder).
    Founder entra como verified+visible (criar é opt-in explícito)."""
    institution_name = (payload.get("institution_name") or "").strip()
    cohort_year = payload.get("cohort_year")
    kind = (payload.get("kind") or "").strip()
    if not institution_name or not cohort_year or not kind:
        raise HTTPException(
            status_code=400,
            detail="institution_name, cohort_year e kind são obrigatórios",
        )
    allowed_kinds = {"escola_fundamental", "escola_medio", "faculdade", "empresa", "bairro", "igreja"}
    if kind not in allowed_kinds:
        raise HTTPException(status_code=400, detail=f"kind deve ser um de {sorted(allowed_kinds)}")

    cohort_label = (payload.get("cohort_label") or "").strip() or None
    institution_id = payload.get("institution_id")
    city = (payload.get("city") or "").strip() or None
    state = (payload.get("state") or "").strip().upper() or None
    if state and len(state) != 2:
        raise HTTPException(status_code=400, detail="state deve ter 2 letras (UF)")

    base_slug = _turma_slugify(institution_name, cohort_year, cohort_label or "")
    slug = base_slug
    suffix = 2
    while db.query(Turma).filter(Turma.slug == slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    t = Turma(
        institution_id=institution_id,
        institution_name=institution_name,
        city=city,
        state=state,
        kind=kind,
        cohort_year=int(cohort_year),
        cohort_label=cohort_label,
        founder_id=current_user.id,
        total_members=1,
        total_verified=1,
        is_unlocked=False,
        slug=slug,
    )
    db.add(t)
    db.flush()

    m = TurmaMembership(
        turma_id=t.id,
        user_id=current_user.id,
        status="verified",
        visibility="visible",   # founder opted-in by creating
        is_founder=True,
        verified_by_vouches=0,
    )
    db.add(m)
    db.commit()
    db.refresh(t)
    track_event(current_user.id, "turma_created", {"slug": t.slug, "kind": t.kind})
    return {"success": True, "turma": _turma_to_dict(t, db, current_user)}


@app.post("/api/turmas/{slug}/join")
@limiter.limit("20/minute")
def turma_join(
    request: Request,
    slug: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🙋 Pedir entrada na turma. Cria membership 'pending' + 'ghost' (LGPD)."""
    # Gate 18+: turma reflete uma escola/série específica e historicamente
    # tem membros menores (colegas de classe que ainda são crianças hoje).
    # Bloqueia menores entrando em contextos com adultos. LGPD Art. 14 + ECA.
    require_18_plus(current_user)
    t = db.query(Turma).filter(Turma.slug == slug).first()
    if not t:
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    existing = (
        db.query(TurmaMembership)
        .filter(
            TurmaMembership.turma_id == t.id,
            TurmaMembership.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        return {
            "success": True,
            "already_member": True,
            "status": existing.status,
            "visibility": existing.visibility,
        }

    m = TurmaMembership(
        turma_id=t.id,
        user_id=current_user.id,
        status="pending",
        visibility="ghost",  # default-ghost
        is_founder=False,
        verified_by_vouches=0,
    )
    db.add(m)
    t.total_members = (t.total_members or 0) + 1
    db.commit()
    track_event(current_user.id, "turma_joined_pending", {"slug": t.slug})
    return {
        "success": True,
        "status": "pending",
        "visibility": "ghost",
        "message": "Pedido enviado. Você está em modo fantasma — só verifica após vouches.",
    }


@app.post("/api/turmas/{slug}/vouch/{user_id}")
@limiter.limit("30/minute")
def turma_vouch(
    request: Request,
    slug: str,
    user_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """🤝 Garantir que outro user fez parte desta turma.
    Voucher precisa estar verified. 2 vouches → membro vira verified.
    visibility permanece 'ghost' — verified ≠ visible (LGPD)."""
    t = db.query(Turma).filter(Turma.slug == slug).first()
    if not t:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode garantir a si mesmo")

    voucher_m = (
        db.query(TurmaMembership)
        .filter(
            TurmaMembership.turma_id == t.id,
            TurmaMembership.user_id == current_user.id,
            TurmaMembership.status == "verified",
        )
        .first()
    )
    if not voucher_m:
        raise HTTPException(status_code=403, detail="Apenas membros verificados podem garantir")

    vouched_m = (
        db.query(TurmaMembership)
        .filter(
            TurmaMembership.turma_id == t.id,
            TurmaMembership.user_id == user_id,
        )
        .first()
    )
    if not vouched_m:
        raise HTTPException(status_code=404, detail="Usuário não pediu para entrar nesta turma")

    dup = (
        db.query(TurmaVouch)
        .filter(
            TurmaVouch.turma_id == t.id,
            TurmaVouch.voucher_user_id == current_user.id,
            TurmaVouch.vouched_user_id == user_id,
        )
        .first()
    )
    if dup:
        return {
            "success": True,
            "already_vouched": True,
            "verified_by_vouches": vouched_m.verified_by_vouches,
        }

    db.add(TurmaVouch(
        turma_id=t.id,
        voucher_user_id=current_user.id,
        vouched_user_id=user_id,
    ))
    vouched_m.verified_by_vouches = (vouched_m.verified_by_vouches or 0) + 1

    promoted = False
    if vouched_m.status != "verified" and vouched_m.verified_by_vouches >= 2:
        vouched_m.status = "verified"
        # visibility stays 'ghost' — only user can opt in
        t.total_verified = (t.total_verified or 0) + 1
        promoted = True
        if t.total_members and (t.total_verified / max(t.total_members, 1)) >= 0.6:
            t.is_unlocked = True  # Mural unlocks at 60%+ verified

    db.commit()
    track_event(current_user.id, "turma_vouched", {
        "slug": t.slug, "for_user_id": user_id, "promoted": promoted,
    })
    return {
        "success": True,
        "verified_by_vouches": vouched_m.verified_by_vouches,
        "promoted_to_verified": promoted,
        "turma_unlocked": t.is_unlocked,
    }


# ===== DASHBOARDS =====
@app.get("/map", response_class=FileResponse)
async def map_dashboard():
    """🗺️ Mapa interativo com top 10 cidades e regiões metropolitanas"""
    return FileResponse("public/map-dashboard.html")

@app.get("/news", response_class=FileResponse)
async def news_dashboard():
    """📰 Dashboard de notícias locais por cidade"""
    return FileResponse("public/news-dashboard.html")

# DEPRECATED V2 PIVOT: was for events product, see POSITIONING_V2
# Will be removed after Phase 1 if no use case emerges
# @app.get("/events", response_class=FileResponse)
# async def events_dashboard():
#     """Dashboard de eventos locais"""
#     return FileResponse("public/events-dashboard.html")


# ===== LANDING PAGE & LEGAL DOCS =====
# ═══════════════════════════════════════════════════════════════════════════════
# LGPD — Art. 18 V (portabilidade) + Art. 18 VI (eliminação)
# ═══════════════════════════════════════════════════════════════════════════════
# Three endpoints:
#   GET    /api/me/lgpd-export             → full data dump as JSON download
#   POST   /api/me/lgpd-deletion-request   → soft-delete + 7-day cool-off
#   POST   /api/me/lgpd-deletion-cancel    → undo within the cool-off window
# Hard-delete after the cool-off is done by tunel_purge.purge_pending_account_deletions
# (apscheduler job, see lifespan). We deliberately mark deletion via a sentinel
# stored in User.bio (``__lgpd_deletion__:ISO_TS``) so we don't need a new column —
# this flow is low-traffic and the bio is unused once is_active=False.

from fastapi.responses import Response as _LGPDResponse
from fastapi.security import HTTPBearer  # for lgpd-deletion-cancel (deactivated user)
import json as _lgpd_json


@app.get("/api/me/lgpd-export")
@limiter.limit("3/day")
def lgpd_export_my_data(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """LGPD Art. 18 V — direito à portabilidade.

    Retorna TODOS os dados pessoais do usuário em JSON (download anexado).
    Inclui: perfil, turmas (membership + role), mensagens, uploads (metadata
    apenas — arquivos brutos não vão no JSON por tamanho; user pode baixá-los
    individualmente via preview_url), consentimentos, faces detectadas (sem
    embedding bruto — biometria é mantida server-side por design).

    Rate-limit: 3/dia (operação cara, não deve ser usada como API regular).
    """
    # Profile (drop password_hash + cpf_hash — não são "do usuário", são
    # credenciais do sistema, e expor é risco extra sem ganho LGPD).
    profile = {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "phone_verified": current_user.phone_verified,
        "profile_photo": current_user.profile_photo,
        "city": current_user.city,
        "profession": current_user.profession,
        "bio": current_user.bio,
        "is_discoverable": current_user.is_discoverable,
        "allow_reconnect_requests": current_user.allow_reconnect_requests,
        "ghost_mode_global": current_user.ghost_mode_global,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
        if current_user.created_at else None,
    }

    # Memberships (Rooms + Turmas).
    rooms = []
    try:
        for m in db.query(RoomMembership).filter(
            RoomMembership.user_id == current_user.id
        ).all():
            rooms.append({
                "room_id": m.room_id,
                "role": m.role,
                "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
    except Exception:
        pass

    turmas = []
    try:
        from database import TurmaMembership  # local import (model added later)
        for tm in db.query(TurmaMembership).filter(
            TurmaMembership.user_id == current_user.id
        ).all():
            turmas.append({
                "turma_id": tm.turma_id,
                "status": tm.status,
                "visibility": tm.visibility,
                "is_founder": tm.is_founder,
                "verified_by_vouches": tm.verified_by_vouches,
            })
    except Exception:
        pass

    # Messages.
    messages = []
    try:
        for msg in db.query(Message).filter(
            Message.user_id == current_user.id
        ).all():
            messages.append({
                "id": msg.id,
                "room_id": msg.room_id,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })
    except Exception:
        pass

    # Tunel uploads — metadata only.
    uploads = []
    try:
        from database import TunelUpload as _TU
        for u in db.query(_TU).filter(_TU.user_id == current_user.id).all():
            uploads.append({
                "id": u.id,
                "turma_id": u.turma_id,
                "file_path": u.file_path,  # so user can download separately
                "file_size_bytes": u.file_size_bytes,
                "mime_type": u.mime_type,
                "original_filename": u.original_filename,
                "photo_year_estimated": u.photo_year_estimated,
                "photo_context": u.photo_context,
                "faces_detected_count": u.faces_detected_count,
                "processing_status": u.processing_status,
                "exif_scrubbed": u.exif_scrubbed,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "deleted_at": u.deleted_at.isoformat() if u.deleted_at else None,
            })
    except Exception:
        pass

    # Faces — bbox + confidence, NO embedding (biométrico, mantido server-side).
    faces = []
    try:
        from database import TunelFace as _TF, TunelUpload as _TU
        user_upload_ids = [
            u.id for u in db.query(_TU).filter(
                _TU.user_id == current_user.id
            ).all()
        ]
        if user_upload_ids:
            for f in db.query(_TF).filter(
                _TF.upload_id.in_(user_upload_ids)
            ).all():
                faces.append({
                    "id": f.id,
                    "upload_id": f.upload_id,
                    "face_index": f.face_index,
                    "bbox": {"x": f.bbox_x, "y": f.bbox_y,
                             "w": f.bbox_w, "h": f.bbox_h},
                    "confidence": f.confidence,
                    "matched_user_id": f.matched_user_id,
                    "match_confidence": f.match_confidence,
                    # embedding propositalmente omitido (biometria server-side)
                })
    except Exception:
        pass

    # Consent audit trail (if consent_helpers table exists).
    consents = []
    try:
        from consent_helpers import list_user_consents
        consents = list_user_consents(db, current_user.id)
    except Exception:
        pass

    payload = {
        "_notice": (
            "Esse arquivo contém TODOS seus dados pessoais. Guarde-o com "
            "segurança — qualquer pessoa com acesso a ele pode reconstruir "
            "sua identidade nessa plataforma. Compartilhe apenas via canais "
            "seguros (criptografia ponta-a-ponta)."
        ),
        "_export_metadata": {
            "exported_at_utc": datetime.utcnow().isoformat(),
            "user_id": current_user.id,
            "lgpd_basis": "Art. 18, V — portabilidade dos dados",
            "embedding_data_omitted": True,
            "embedding_data_reason": (
                "Dado biométrico (LGPD Art. 11) — mantido server-side por "
                "segurança. Para apagar, use POST /api/me/lgpd-deletion-request."
            ),
        },
        "profile": profile,
        "rooms": rooms,
        "turmas": turmas,
        "messages": messages,
        "tunel_uploads": uploads,
        "tunel_faces": faces,
        "consents": consents,
    }

    body = _lgpd_json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    fname = f"timemates-lgpd-export-user{current_user.id}-{datetime.utcnow().date().isoformat()}.json"
    return _LGPDResponse(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.post("/api/me/lgpd-deletion-request")
@limiter.limit("3/day")
def lgpd_deletion_request(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """LGPD Art. 18 VI — direito à eliminação.

    Inicia um soft-delete da conta com COOL-OFF de 7 dias antes do hard-delete.
    Durante a janela, o user pode cancelar via /api/me/lgpd-deletion-cancel.
    Após 7 dias, o cron tunel_purge.purge_pending_account_deletions apaga
    tudo (perfil, uploads, faces, mensagens em cascade via FKs).

    Sentinel é gravado em User.bio (``__lgpd_deletion__:ISO_TS``) — coluna
    nova só pra isso seria over-engineering, e o user não acessa bio depois
    de is_active=False.
    """
    now = datetime.utcnow()
    current_user.is_active = False
    current_user.bio = f"__lgpd_deletion__:{now.isoformat()}"
    # Defense-in-depth: also flip ghost_mode_global so anyone querying the
    # platform during the cool-off window doesn't see the account.
    current_user.ghost_mode_global = True
    db.commit()
    return {
        "ok": True,
        "deletion_requested_at_utc": now.isoformat(),
        "scheduled_purge_at_utc": (now + timedelta(days=7)).isoformat(),
        "cool_off_days": 7,
        "cancel_endpoint": "POST /api/me/lgpd-deletion-cancel",
        "message": (
            "Sua conta foi desativada. Você tem 7 dias para cancelar a "
            "exclusão antes que seus dados sejam permanentemente apagados. "
            "Após o prazo, esse processo é IRREVERSÍVEL."
        ),
    }


@app.post("/api/me/lgpd-deletion-cancel")
@limiter.limit("5/day")
def lgpd_deletion_cancel(
    request: Request,
    credentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
):
    """Cancela um pedido de exclusão em andamento (dentro dos 7 dias).

    Reativa a conta e remove o sentinel. CRÍTICO: usa decode manual em vez de
    get_current_user_required porque o user está com is_active=False durante
    o cool-off — o dep padrão filtraria a row e o cancel seria impossível.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Faça login para continuar")
    try:
        from auth import decode_token
        payload = decode_token(credentials.credentials)
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")

    # NB: no is_active filter here — that's exactly what we're trying to undo.
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    # If the cool-off already expired the row was hard-deleted by the cron,
    # so this path can't be hit. If is_active is True, idempotent no-op.
    if (user.bio or "").startswith("__lgpd_deletion__:"):
        user.bio = None  # clear sentinel
    user.is_active = True
    user.ghost_mode_global = False
    db.commit()
    return {
        "ok": True,
        "message": "Pedido de exclusão cancelado. Sua conta está ativa novamente.",
    }


# CUTOVER 2026-06-12: raiz / agora serve homepage V2 (narrativa de saudade/reconexão)
# Old landing at public/landing/index.html ainda acessível via /landing
@app.get("/", response_class=FileResponse)
async def landing_page():
    return FileResponse("static/index_v2.html")

@app.get("/v2", response_class=FileResponse)
async def homepage_v2_compat():
    """Backwards-compat: /v2 continua servindo a mesma homepage V2."""
    return FileResponse("static/index_v2.html")

@app.get("/tunel", response_class=FileResponse)
async def tunel_page():
    """Túnel do Tempo: upload de foto antiga + reconexão via face match."""
    return FileResponse("static/tunel.html")

@app.get("/turma/{turma_slug}", response_class=FileResponse)
async def turma_page(turma_slug: str):
    """Turma Hub: page central da turma integrando Mural, Reunião, Cadê e Túnel."""
    return FileResponse("static/turma.html")

@app.get("/reuniao/nova", response_class=FileResponse)
async def reuniao_nova_page():
    """Reunião Button: criar nova reunião (vota datas com a turma)."""
    return FileResponse("static/reuniao.html")

@app.get("/reuniao/{reuniao_id:int}", response_class=FileResponse)
async def reuniao_detail_page(reuniao_id: int):
    """Reunião Button: detalhe da reunião (votação, RSVP, share)."""
    return FileResponse("static/reuniao.html")

@app.get("/mural", response_class=FileResponse)
@app.get("/mural/{turma_slug}", response_class=FileResponse)
async def mural_page(turma_slug: str = None):
    """Mural da Saudade: feed de memórias coletivas (cheiros, sons, lugares, pessoas)."""
    return FileResponse("static/mural.html")

@app.get("/privacy", response_class=FileResponse)
async def privacy_policy():
    return FileResponse("public/landing/privacy.html")

@app.get("/terms", response_class=FileResponse)
async def terms_of_service():
    return FileResponse("public/landing/terms.html")

# Mount landing folder as static files
app.mount("/landing", StaticFiles(directory="public/landing", html=True), name="landing")

from fastapi.responses import JSONResponse, PlainTextResponse

# Global exception handler — return JSON {detail} envelope for unhandled errors
# (replaces FastAPI/Starlette default plain-text "Internal Server Error")
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    # Let HTTPException pass through (FastAPI handles it)
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor", "path": request.url.path},
    )

# Proper robots.txt (was hitting SPA catch-all and returning HTML)
@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    body = "User-agent: *\nAllow: /\nSitemap: https://timemates.onrender.com/sitemap.xml\n"
    return PlainTextResponse(body, media_type="text/plain")

# Proper favicon: serve real file if it exists, otherwise return 204 (was 200 HTML)
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    for candidate in ("static/favicon.ico", "public/landing/favicon.ico"):
        if os.path.exists(candidate):
            return FileResponse(candidate, media_type="image/x-icon")
    return Response(status_code=204)

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    # Unknown /api/* paths must return JSON 404, NOT the SPA index.html.
    # Without this, every unknown API URL returned 200 + HTML, breaking
    # API clients, SEO, and 404-detection in monitoring.
    if full_path.startswith("api/") or full_path == "api":
        return JSONResponse(
            status_code=404,
            content={"detail": "Endpoint não encontrado", "path": "/" + full_path},
        )
    return FileResponse("static/index.html")
