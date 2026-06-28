"""Database helpers for coding history."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import schemas
from ..database import to_storage_id
from ..models import normalize_history_doc


def _serialize_value(value: str | list | None) -> str | list | None:
    """Store structured data natively, but keep strings unchanged."""
    if value is None:
        return None
    return value


def create_history(db: Any, payload: schemas.CodeHistoryCreate) -> dict[str, Any]:
    """Create and persist a MongoDB history document."""
    collection = db["code_history"]
    document = {
        "user_id": to_storage_id(payload.user_id) if payload.user_id is not None else None,
        "prompt": payload.prompt,
        "language": payload.language,
        "action_type": payload.action_type,
        "input_code": payload.input_code,
        "generated_code": payload.generated_code,
        "explanation": payload.explanation,
        "time_complexity": payload.time_complexity,
        "space_complexity": payload.space_complexity,
        "suggestions": _serialize_value(payload.suggestions),
        "quality_breakdown": _serialize_value(payload.quality_breakdown),
        "top_improvements": _serialize_value(payload.top_improvements),
        "created_at": datetime.utcnow(),
    }
    result = collection.insert_one(document)
    saved = collection.find_one({"_id": result.inserted_id})
    normalized = normalize_history_doc(saved)
    if normalized is None:
        raise RuntimeError("Failed to persist history record.")
    return normalized


def list_history(db: Any, limit: int = 50) -> list[dict[str, Any]]:
    """Return the newest records first."""
    cursor = db["code_history"].find().sort("created_at", -1).limit(limit)
    history: list[dict[str, Any]] = []
    for document in cursor:
        normalized = normalize_history_doc(document)
        if normalized is not None:
            history.append(normalized)
    return history
