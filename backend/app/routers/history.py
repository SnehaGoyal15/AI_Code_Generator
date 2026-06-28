"""CRUD endpoints for code history."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .. import schemas
from ..auth import get_current_user
from ..database import get_db, to_storage_id
from ..models import normalize_history_doc
from ..services.history_service import create_history as persist_history

router = APIRouter(prefix="/history", tags=["history"])


def _owned_history_query(db, user_id: str):
    return db["code_history"].find({"user_id": to_storage_id(user_id)})


@router.post("", response_model=schemas.CodeHistoryRead, status_code=status.HTTP_201_CREATED)
def create_history(
    payload: schemas.CodeHistoryCreate,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Create a code history record and return the saved row."""
    return persist_history(
        db,
        schemas.CodeHistoryCreate(
            user_id=current_user["id"],
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
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """Return newest history items first."""
    return [
        normalized
        for document in _owned_history_query(db, current_user["id"]).sort("created_at", -1)
        if (normalized := normalize_history_doc(document)) is not None
    ]


@router.get("/{history_id}", response_model=schemas.CodeHistoryRead)
def get_history(
    history_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """Fetch a single history record or raise 404 if it does not exist."""
    record = db["code_history"].find_one({"_id": to_storage_id(history_id), "user_id": to_storage_id(current_user["id"])})
    normalized = normalize_history_doc(record)
    if normalized is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found.")
    return normalized


@router.delete("/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(
    history_id: str,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """Delete a history record and return no content."""
    result = db["code_history"].delete_one({"_id": to_storage_id(history_id), "user_id": to_storage_id(current_user["id"])})
    if getattr(result, "deleted_count", 0) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History record not found.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

