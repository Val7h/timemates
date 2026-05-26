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
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import (
    get_db, Base, engine, SessionLocal,
    User, Institution, Room, RoomMembership, Message,
    Photo, RememberedPerson, RememberedPersonConfirmation,
    InviteLink, Notification
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

@asynccontextmanager
async def lifespan(app):
    try:
        from seed_all import seed_db
        db = SessionLocal()
        try:
            seed_db(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[SEED] Erro no startup (nao critico): {e}")
    yield

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


# ─── Debug / Health ──────────────────────────────────────────────────────────

@app.get("/api/dbstatus")
def db_status():
    """Diagnóstico da conexão com o banco de dados."""
    from database import SQLALCHEMY_DATABASE_URL
    url_safe = SQLALCHEMY_DATABASE_URL
    # oculta senha
    try:
        import re
        url_safe = re.sub(r':[^:@]+@', ':***@', url_safe)
    except Exception:
        pass
    db_type = "postgresql" if "postgresql" in SQLALCHEMY_DATABASE_URL else "sqlite"
    try:
        with engine.connect() as conn:
            if db_type == "postgresql":
                result = conn.execute(__import__('sqlalchemy').text("SELECT version()"))
                version = result.scalar()
            else:
                result = conn.execute(__import__('sqlalchemy').text("SELECT sqlite_version()"))
                version = result.scalar()
        connected = True
    except Exception as e:
        connected = False
        version = str(e)
    return {
        "db_type": db_type,
        "url": url_safe,
        "connected": connected,
        "version_or_error": version,
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
            db.add(Notification(
                user_id=rp.created_by_id,
                type="remembered_found",
                title="Alguém que você lembrou entrou!",
                message=f"{user.full_name}, que você lembrava, acabou de entrar na sala!",
                related_room_id=room_id,
            ))
            creator = db.query(User).filter(User.id == rp.created_by_id).first()
            if creator and room:
                mail.send_remembered_found(
                    to_email=creator.email,
                    name=creator.full_name,
                    found_name=user.full_name,
                    room_name=f"{room.group_name} - {room.year}",
                )
    db.commit()


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register")
def register(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    cpf: str = Form(...),
    phone: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if not validate_cpf(cpf):
        raise HTTPException(status_code=400, detail="CPF inválido. Verifique os dígitos e tente novamente.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter no mínimo 6 caracteres")
    if db.query(User).filter(User.email == email.lower()).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    import hashlib
    cpf_clean = "".join(filter(str.isdigit, cpf))
    cpf_sha = hashlib.sha256(cpf_clean.encode()).hexdigest()
    if db.query(User).filter(User.cpf_hash == cpf_sha).first():
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
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
    db: Session = Depends(get_db),
):
    q = db.query(Institution).filter(Institution.approved == True)
    if type:
        q = q.filter(Institution.type == type)
    if state:
        q = q.filter(Institution.state == state)
    if search:
        q = q.filter(Institution.name.ilike(f"%{search}%"))

    result = []
    for inst in q.order_by(Institution.name).all():
        room_ids = [r.id for r in inst.rooms]
        member_count = (
            db.query(RoomMembership)
            .filter(RoomMembership.room_id.in_(room_ids), RoomMembership.status == "approved")
            .count()
            if room_ids else 0
        )
        result.append({
            "id": inst.id,
            "name": inst.name,
            "type": inst.type,
            "state": inst.state,
            "city": inst.city,
            "neighborhood": inst.neighborhood,
            "sector": inst.sector,
            "room_count": len(inst.rooms),
            "member_count": member_count,
        })
    return result


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

    db.add(RoomMembership(
        room_id=room_id, user_id=current_user.id,
        role="member", status="pending", message=message,
    ))
    db.commit()
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
    get_membership(room_id, current_user, db)
    msgs = (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.asc())
        .offset(offset).limit(limit).all()
    )
    return [{
        "id": m.id, "user_id": m.user_id,
        "user_name": m.user.full_name,
        "user_photo": m.user.profile_photo,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    } for m in msgs]


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
    current_user.city = city
    current_user.profession = profession
    current_user.bio = bio
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


# ─── Static / Invite page ─────────────────────────────────────────────────────

@app.get("/convite/{token}")
def invite_page(token: str):
    return FileResponse("static/index.html")


@app.get("/{full_path:path}")
def catch_all(full_path: str):
    return FileResponse("static/index.html")
