"""CRUD endpoints for code history."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.history_service import create_history as persist_history

router = APIRouter(prefix="/history", tags=["history"])


def _owned_history_query(db: Session, user_id: int):
    return db.query(models.CodeHistory).filter(models.CodeHistory.user_id == user_id)


@router.post("", response_model=schemas.CodeHistoryRead, status_code=status.HTTP_201_CREATED)
def create_history(
    payload: schemas.CodeHistoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.CodeHistory:
    """Create a code history record and return the saved row."""
    return persist_history(
        db,
        schemas.CodeHistoryCreate(
            user_id=current_user.id,
            prompt=payload.prompt,
            language=payload.language,
            action_type=payload.action_type,
            input_code=payload.input_code,
            generated_code=payload.generated_code,
            explanation=payload.explanation,
            time_complexity=payload.time_complexity,
            space_complexity=payload.space_complexity,
            suggestions=payload.suggestions,
            quality_breakdown=payload.quality_breakdown,
            top_improvements=payload.top_improvements,
        ),
    )


@router.get("", response_model=list[schemas.CodeHistoryRead])
def list_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.CodeHistory]:
    """Return newest history items first."""
    return (
        _owned_history_query(db, current_user.id)
        .order_by(models.CodeHistory.created_at.desc())
        .all()
    )


@router.get("/{history_id}", response_model=schemas.CodeHistoryRead)
def get_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.CodeHistory:
    """Fetch a single history record or raise 404 if it does not exist."""
    record = _owned_history_query(db, current_user.id).filter(models.CodeHistory.id == history_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found.")
    return record


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Response:
    """Delete a history record and return no content."""
    record = _owned_history_query(db, current_user.id).filter(models.CodeHistory.id == history_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found.")

    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
