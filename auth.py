from datetime import datetime, timedelta
from typing import Optional
import hashlib, os, hmac
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, User

SECRET_KEY = os.getenv("SECRET_KEY", "timeMates_mude_esta_chave_em_producao_2024_segredo")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer(auto_error=False)

_ITERATIONS = 260000


def hash_password(value: str) -> str:
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), _ITERATIONS)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _, salt, dk_stored = hashed.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), _ITERATIONS)
        return hmac.compare_digest(dk.hex(), dk_stored)
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload.get("sub"))
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except Exception:
        return None


def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Faça login para continuar")
    try:
        payload = decode_token(credentials.credentials)
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


def validate_cpf(cpf: str) -> bool:
    cpf = "".join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    # First digit
    s = sum(int(cpf[i]) * (10 - i) for i in range(9))
    r = (s * 10) % 11
    if r == 10:
        r = 0
    if r != int(cpf[9]):
        return False
    # Second digit
    s = sum(int(cpf[i]) * (11 - i) for i in range(10))
    r = (s * 10) % 11
    if r == 10:
        r = 0
    if r != int(cpf[10]):
        return False
    return True
