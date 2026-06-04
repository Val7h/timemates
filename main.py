import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

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
    Testimony, EmailLog, PushSubscription, DMConversation, DMMessage
)
from auth import (
    get_current_user, get_current_user_required,
    hash_password, verify_password, create_access_token, validate_cpf
)

try:
    Base.metadata.create_all(bind=engine)
except Exception as _e:
    print(f"[DB] create_all erro: {_e}")

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
    try:
        _run_email_sequence()
    except Exception as e:
        print(f"[EMAIL_SEQ] Erro (nao critico): {e}")

    yield


def _run_email_sequence():
    """Envia follow-up emails para usuários que ainda não os receberam."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        users = db.query(User).filter(User.is_active == True).all()
        sent = 0
        for u in users:
            # Ignora contas demo
            if "@demo.timemates" in u.email:
                continue
            days_since = (now - u.created_at).days
            already_sent = {
                log.email_type
                for log in db.query(EmailLog).filter(EmailLog.user_id == u.id).all()
            }
            if days_since >= 3 and "followup_day3" not in already_sent:
                mail.send_followup_day3(u.email, u.full_name)
                db.add(EmailLog(user_id=u.id, email_type="followup_day3"))
                sent += 1
            if days_since >= 7 and "followup_day7" not in already_sent:
                mail.send_followup_day7(u.email, u.full_name)
                db.add(EmailLog(user_id=u.id, email_type="followup_day7"))
                sent += 1
        if sent:
            db.commit()
            print(f"[EMAIL_SEQ] {sent} email(s) de follow-up enviados")
    finally:
        db.close()

app = FastAPI(title="TimeMates API", version="1.0.0", lifespan=lifespan)

# Tokens de recuperação de senha: { token: {"user_id": int, "expires": datetime} }
_reset_tokens: Dict[str, dict] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads/photos", exist_ok=True)
os.makedirs("uploads/avatars", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static_files")


# ─── WebSocket Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, ws: WebSocket, room_id: int):
        await ws.accept()
        self.connections.setdefault(room_id, []).append(ws)

    def disconnect(self, ws: WebSocket, room_id: int):
        if room_id in self.connections:
            try:
                self.connections[room_id].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, data: dict, room_id: int):
        for ws in list(self.connections.get(room_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                pass


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
def health_check():
    """Verifica saúde da aplicação e conexão com o banco."""
    from sqlalchemy import text as sa_text
    dialect = engine.dialect.name
    try:
        with engine.connect() as conn:
            q = "SELECT 1"
            conn.execute(sa_text(q))
        db_ok = True
    except Exception as e:
        db_ok = False
    return {"status": "ok", "db": dialect, "db_connected": db_ok}


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
    if len(q.strip()) < 2:
        return []
    limit = min(limit, 50)
    users = (
        db.query(User)
        .filter(User.full_name.ilike(f"%{q.strip()}%"), User.is_active == True)
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


@app.post("/api/auth/register")
def register(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    cpf: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
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
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user_to_dict(user)}


@app.post("/api/auth/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user_to_dict(user)}


@app.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user_required)):
    return user_to_dict(current_user)


@app.post("/api/auth/forgot-password")
def forgot_password(
    email: str = Form(...),
    db: Session = Depends(get_db),
):
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
    return {
        "id": inst.id, "name": inst.name, "type": inst.type,
        "state": inst.state, "city": inst.city,
        "neighborhood": inst.neighborhood, "sector": inst.sector,
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

        await manager.connect(websocket, room_id)
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
            manager.disconnect(websocket, room_id)
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
    import re as _re
    for tag in ("og:title", "og:description", "og:url", "twitter:title", "twitter:description"):
        html = _re.sub(rf'<meta property="{tag}"[^/]*/>', "", html)
        html = _re.sub(rf'<meta name="{tag}"[^/]*/>', "", html)
    # Insere logo após <meta name="theme-color"...>
    html = _re.sub(
        r'(<meta name="theme-color"[^/]*/>)',
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




@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return FileResponse("static/index.html")
