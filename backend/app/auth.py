"""Authentication helpers for CodeMentor AI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def generate_login_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def set_login_otp(user: models.User) -> tuple[str, datetime]:
    settings = get_settings()
    otp = generate_login_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.login_otp_expires_in_minutes)
    user.login_otp_hash = hash_password(otp)
    user.login_otp_expires_at = expires_at
    return otp, expires_at


def clear_login_otp(user: models.User) -> None:
    user.login_otp_hash = None
    user.login_otp_expires_at = None


def verify_login_otp(user: models.User, otp: str) -> bool:
    expires_at = user.login_otp_expires_at
    if expires_at is None or user.login_otp_hash is None:
        return False
    if expires_at < datetime.utcnow():
        return False
    return verify_password(otp, user.login_otp_hash)


def create_access_token(user_id: int, email: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_in_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    user = db.get(models.User, int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user
