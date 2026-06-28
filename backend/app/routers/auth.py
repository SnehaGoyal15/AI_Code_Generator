"""Authentication endpoints for CodeMentor AI."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import (
    clear_login_otp,
    create_access_token,
    get_current_user,
    hash_password,
    set_login_otp,
    verify_login_otp,
    verify_password,
)
from ..database import get_db
from ..config import get_settings
from ..services.email_service import send_login_otp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=schemas.AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
    description="Create a new user account with a hashed password and return a JWT access token.",
)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)) -> schemas.AuthTokenResponse:
    email = payload.email.strip().lower()
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    user = models.User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return schemas.AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=schemas.LoginOtpChallengeResponse,
    summary="Login user",
    description="Verify credentials, send a one-time password to email, and return a login challenge.",
)
async def login(payload: schemas.UserLogin, db: Session = Depends(get_db)) -> schemas.LoginOtpChallengeResponse:
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    otp, _ = set_login_otp(user)
    db.commit()
    db.refresh(user)

    settings = get_settings()
    email_sent = await send_login_otp(
        name=user.name,
        email=user.email,
        otp=otp,
        expires_in_minutes=settings.login_otp_expires_in_minutes,
    )
    if not email_sent and settings.environment == "production":
        clear_login_otp(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send login OTP right now. Please try again later.",
        )

    debug_otp = otp if settings.environment != "production" else None
    return schemas.LoginOtpChallengeResponse(
        message="Login OTP sent",
        email=user.email,
        verification_required=True,
        expires_in_minutes=settings.login_otp_expires_in_minutes,
        debug_otp=debug_otp,
        email_sent=email_sent,
    )


@router.post(
    "/verify-login-otp",
    response_model=schemas.AuthTokenResponse,
    summary="Verify login OTP",
    description="Verify the login OTP and return a JWT access token for protected requests.",
)
def verify_login_otp_route(payload: schemas.UserLoginOtp, db: Session = Depends(get_db)) -> schemas.AuthTokenResponse:
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login challenge.")

    if not verify_login_otp(user, payload.otp.strip()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP.")

    clear_login_otp(user)
    db.commit()

    token = create_access_token(user.id, user.email)
    return schemas.AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserRead.model_validate(user),
    )


@router.get(
    "/me",
    response_model=schemas.UserRead,
    summary="Current user",
    description="Return the authenticated user's profile.",
)
def me(current_user: models.User = Depends(get_current_user)) -> schemas.UserRead:
    return schemas.UserRead.model_validate(current_user)
