"""Authentication endpoints for CodeMentor AI."""

from __future__ import annotations

from datetime import datetime

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..auth import (
    clear_login_otp,
    create_access_token,
    get_current_user,
    hash_password,
    set_login_otp,
    verify_login_otp,
    verify_password,
)
from ..config import get_settings
from ..database import get_db, to_storage_id
from ..models import normalize_user_doc
from ..services.email_service import send_login_otp

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post(
    "/register",
    response_model=schemas.AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
    description="Create a new user account with a hashed password and return a JWT access token.",
)
def register(payload: schemas.UserRegister, db=Depends(get_db)) -> schemas.AuthTokenResponse:
    users = db["users"]
    email = payload.email.strip().lower()
    existing = users.find_one({"email": email})
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

    user_doc = {
        "name": payload.name.strip(),
        "email": email,
        "password_hash": hash_password(payload.password),
        "login_otp_hash": None,
        "login_otp_expires_at": None,
        "created_at": datetime.utcnow(),
    }
    result = users.insert_one(user_doc)
    saved_user = users.find_one({"_id": result.inserted_id})
    normalized_user = normalize_user_doc(saved_user)
    token = create_access_token(normalized_user["id"], normalized_user["email"])
    return schemas.AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserRead.model_validate(normalized_user),
    )


@router.post(
    "/login",
    response_model=schemas.LoginOtpChallengeResponse,
    summary="Login user",
    description="Verify credentials, send a one-time password to email, and return a login challenge.",
)
async def login(payload: schemas.UserLogin, db=Depends(get_db)) -> schemas.LoginOtpChallengeResponse:
    users = db["users"]
    email = payload.email.strip().lower()
    user_doc = users.find_one({"email": email})
    if user_doc is None or not verify_password(payload.password, user_doc["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    otp, _ = set_login_otp(user_doc)
    users.replace_one({"_id": user_doc["_id"]}, user_doc)

    settings = get_settings()
    email_sent = await send_login_otp(
        name=user_doc["name"],
        email=user_doc["email"],
        otp=otp,
        expires_in_minutes=settings.login_otp_expires_in_minutes,
    )
    if not email_sent:
        logger.warning(
            "Login OTP was generated but could not be delivered for %s.",
            user_doc["email"],
        )

    debug_otp = otp if settings.environment != "production" else None
    return schemas.LoginOtpChallengeResponse(
        message="Login OTP sent",
        email=user_doc["email"],
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
def verify_login_otp_route(payload: schemas.UserLoginOtp, db=Depends(get_db)) -> schemas.AuthTokenResponse:
    users = db["users"]
    email = payload.email.strip().lower()
    user_doc = users.find_one({"email": email})
    if user_doc is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login challenge.")

    if not verify_login_otp(user_doc, payload.otp.strip()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP.")

    clear_login_otp(user_doc)
    users.replace_one({"_id": user_doc["_id"]}, user_doc)
    normalized_user = normalize_user_doc(user_doc)
    token = create_access_token(normalized_user["id"], normalized_user["email"])
    return schemas.AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserRead.model_validate(normalized_user),
    )


@router.get(
    "/me",
    response_model=schemas.UserRead,
    summary="Current user",
    description="Return the authenticated user's profile.",
)
def me(current_user=Depends(get_current_user)) -> schemas.UserRead:
    return schemas.UserRead.model_validate(current_user)
