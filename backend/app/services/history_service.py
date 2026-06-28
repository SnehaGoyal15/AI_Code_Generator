"""Database helpers for coding history."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .. import models, schemas


def _serialize_suggestions(value: str | list | None) -> str | None:
    """Store suggestions as JSON when they are structured data."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def create_history(db: Session, payload: schemas.CodeHistoryCreate) -> models.CodeHistory:
    """Create and persist a history row."""
    record = models.CodeHistory(
        user_id=payload.user_id,
        prompt=payload.prompt,
        language=payload.language,
        action_type=payload.action_type,
        input_code=payload.input_code,
        generated_code=payload.generated_code,
        explanation=payload.explanation,
        time_complexity=payload.time_complexity,
        space_complexity=payload.space_complexity,
        suggestions=_serialize_suggestions(payload.suggestions),
        quality_breakdown=_serialize_suggestions(payload.quality_breakdown),
        top_improvements=_serialize_suggestions(payload.top_improvements),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_history(db: Session, limit: int = 50) -> list[models.CodeHistory]:
    """Return the newest records first."""
    return db.query(models.CodeHistory).order_by(models.CodeHistory.created_at.desc()).limit(limit).all()
