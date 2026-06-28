"""Application settings for CodeMentor AI."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os
from typing import List


def _load_env_file(path: Path) -> None:
    """Load a simple KEY=VALUE env file without extra dependencies."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


_load_env_file(Path(__file__).resolve().parents[2] / ".env")
_load_env_file(Path(".env"))


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "CodeMentor AI")
    environment: str = os.getenv("ENVIRONMENT", "development")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./code_mentor_ai.db")
    frontend_origins: str = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    brevo_api_key: str | None = os.getenv("BREVO_API_KEY") or None
    brevo_from: str | None = os.getenv("BREVO_FROM") or None
    email_send_timeout_seconds: float = float(os.getenv("EMAIL_SEND_TIMEOUT_SECONDS", "10"))
    login_otp_expires_in_minutes: int = int(os.getenv("LOGIN_OTP_EXPIRES_IN_MINUTES", "10"))
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-development")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expires_in_minutes: int = int(os.getenv("JWT_EXPIRES_IN_MINUTES", "1440"))

    def allowed_origins(self) -> List[str]:
        """Return the CORS origins as a clean list."""
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
