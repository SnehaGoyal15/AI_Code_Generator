"""SQLAlchemy models for CodeMentor AI."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    """Store user profile information for future authentication work."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    login_otp_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    login_otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class CodeHistory(Base):
    """Persist prompts, outputs, and analysis for later review."""

    __tablename__ = "code_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    input_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    space_complexity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_improvements: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Feedback(Base):
    """Capture ratings for generated history items."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    history_id: Mapped[int] = mapped_column(ForeignKey("code_history.id"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
