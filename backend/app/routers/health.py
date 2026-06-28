"""Health endpoint router."""

from fastapi import APIRouter

from ..config import get_settings
from ..schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        message="CodeMentor AI backend is running.",
        environment=settings.environment,
    )

