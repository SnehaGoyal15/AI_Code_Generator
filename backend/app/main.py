"""FastAPI entrypoint for CodeMentor AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine, ensure_sqlite_history_columns, ensure_sqlite_user_columns
from .models import CodeHistory, Feedback, User  # noqa: F401 - ensures model registration
from .routers.ai import router as ai_router
from .routers.auth import router as auth_router
from .routers.history import router as history_router
from .routers.health import router as health_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Create the SQLite tables automatically whenever the backend starts.
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_history_columns()
    ensure_sqlite_user_columns()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "CodeMentor AI backend is running."}


app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(history_router, prefix=settings.api_prefix)
