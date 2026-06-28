"""MongoDB document helpers for CodeMentor AI."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .database import to_public_id


def _normalize_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.utcnow()


def normalize_user_doc(document: dict[str, Any] | None, include_private: bool = False) -> dict[str, Any] | None:
    if not document:
        return None

    normalized = {
        "id": to_public_id(document.get("_id")),
        "name": document.get("name", ""),
        "email": document.get("email", ""),
        "created_at": _normalize_datetime(document.get("created_at")),
    }
    if include_private:
        normalized.update(
            {
                "password_hash": document.get("password_hash"),
                "login_otp_hash": document.get("login_otp_hash"),
                "login_otp_expires_at": document.get("login_otp_expires_at"),
            }
        )
    return normalized


def normalize_history_doc(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None

    return {
        "id": to_public_id(document.get("_id")),
        "user_id": to_public_id(document.get("user_id")),
        "prompt": document.get("prompt", ""),
        "language": document.get("language", ""),
        "action_type": document.get("action_type", ""),
        "input_code": document.get("input_code"),
        "generated_code": document.get("generated_code"),
        "explanation": document.get("explanation"),
        "time_complexity": document.get("time_complexity"),
        "space_complexity": document.get("space_complexity"),
        "suggestions": document.get("suggestions"),
        "quality_breakdown": document.get("quality_breakdown"),
        "top_improvements": document.get("top_improvements"),
        "created_at": _normalize_datetime(document.get("created_at")),
    }


def normalize_feedback_doc(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None

    return {
        "id": to_public_id(document.get("_id")),
        "history_id": to_public_id(document.get("history_id")),
        "rating": document.get("rating"),
        "comment": document.get("comment"),
        "created_at": _normalize_datetime(document.get("created_at")),
    }

