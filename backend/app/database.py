"""Database configuration and session helpers."""

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

engine_kwargs = {"connect_args": {"check_same_thread": False}} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_history_columns() -> None:
    """Add new history columns when an older SQLite database is already present."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "code_history" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("code_history")}
    with engine.begin() as connection:
        if "quality_breakdown" not in columns:
            connection.execute(text("ALTER TABLE code_history ADD COLUMN quality_breakdown TEXT"))
        if "top_improvements" not in columns:
            connection.execute(text("ALTER TABLE code_history ADD COLUMN top_improvements TEXT"))


def ensure_sqlite_user_columns() -> None:
    """Add login OTP columns when an older SQLite users table already exists."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "login_otp_hash" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN login_otp_hash TEXT"))
        if "login_otp_expires_at" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN login_otp_expires_at DATETIME"))


def get_db():
    """Yield a database session for request handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
