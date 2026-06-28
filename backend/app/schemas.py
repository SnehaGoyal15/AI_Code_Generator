"""Pydantic schemas for CodeMentor AI."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    success: bool = True
    message: str
    environment: str


class CodeRequest(BaseModel):
    prompt: str = Field(min_length=1)
    language: str = Field(min_length=1)


class AIActionRequest(BaseModel):
    prompt: str | None = None
    language: str = Field(min_length=1)
    code: str | None = None


class UserRegister(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserLoginOtp(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    otp: str = Field(min_length=6, max_length=6)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class LoginOtpChallengeResponse(BaseModel):
    message: str
    email: str
    verification_required: bool = True
    expires_in_minutes: int
    debug_otp: str | None = None
    email_sent: bool = False


class AIActionResponse(BaseModel):
    history_id: int
    action_type: str
    code: str | None = None
    explanation: str | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    issues: list[Any] = Field(default_factory=list)
    static_checks: list[dict[str, str]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    quality_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: int | None = None
    top_improvements: list[str] = Field(default_factory=list)
    documentation: str | None = None


class CodeHistoryBase(BaseModel):
    prompt: str = Field(min_length=1)
    language: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    input_code: str | None = None
    generated_code: str | None = None
    explanation: str | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    suggestions: str | list[Any] | None = None
    quality_breakdown: str | list[Any] | None = None
    top_improvements: str | list[Any] | None = None


class CodeHistoryCreate(CodeHistoryBase):
    user_id: int | None = None


class CodeHistoryRead(CodeHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    created_at: datetime


class FeedbackBase(BaseModel):
    history_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackRead(FeedbackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
