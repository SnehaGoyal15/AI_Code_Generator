from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB_PATH = Path("/private/tmp/codementor_ai_tests.db")

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "codementor-ai-test-secret-key-123456"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_EXPIRES_IN_MINUTES"] = "60"
os.environ["GEMINI_API_KEY"] = "mock-key"
os.environ["GEMINI_MODEL"] = "mock-model"
os.environ["BREVO_API_KEY"] = ""
os.environ["BREVO_FROM"] = ""
os.environ["LOGIN_OTP_EXPIRES_IN_MINUTES"] = "10"
os.environ["FRONTEND_ORIGINS"] = "http://localhost:5173"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import ai_service as ai_service_module
from app import database as database_module
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    database_module.Base.metadata.drop_all(bind=database_module.engine)
    database_module.Base.metadata.create_all(bind=database_module.engine)
    database_module.ensure_sqlite_history_columns()
    yield
    database_module.Base.metadata.drop_all(bind=database_module.engine)


@pytest.fixture
def client(monkeypatch):
    def fake_ai_call(prompt: str) -> dict:
        prompt_upper = prompt.upper()
        if "REVIEW" in prompt_upper:
            return {
                "code": "reviewed code",
                "explanation": "Potential issues were reviewed.",
                "time_complexity": "O(n)",
                "space_complexity": "O(1)",
                "issues": [
                    {
                        "type": "Style Issue",
                        "severity": "Low",
                        "line_hint": "Line 1",
                        "message": "Potential issue in naming.",
                        "fix": "Consider improving the name.",
                    }
                ],
                "suggestions": ["Consider improving structure."],
                "quality_breakdown": [
                    {
                        "category": "Correctness and potential bugs",
                        "score": 1,
                        "max_score": 2,
                        "notes": "Potential issue only; no guaranteed bug detected.",
                    },
                    {
                        "category": "Readability and naming",
                        "score": 1,
                        "max_score": 2,
                        "notes": "Consider improving naming consistency.",
                    },
                    {
                        "category": "Efficiency",
                        "score": 1,
                        "max_score": 2,
                        "notes": "Potential issue with repeated work.",
                    },
                    {
                        "category": "Maintainability and structure",
                        "score": 1,
                        "max_score": 2,
                        "notes": "Consider improving structure.",
                    },
                    {
                        "category": "Documentation and comments",
                        "score": 1,
                        "max_score": 2,
                        "notes": "Consider improving comments.",
                    },
                ],
                "quality_score": 5,
                "top_improvements": [
                    "Consider improving naming consistency.",
                    "Consider improving structure.",
                    "Consider improving comments.",
                ],
                "documentation": None,
            }
        if "SQL" in prompt_upper:
            return {
                "code": "DELETE FROM users;",
                "explanation": "Potential issue detected.",
                "time_complexity": None,
                "space_complexity": None,
                "issues": [],
                "suggestions": ["Consider improving with a read-only preview first."],
                "quality_breakdown": [],
                "quality_score": None,
                "top_improvements": [],
                "documentation": None,
            }
        return {
            "code": "print('hello')",
            "explanation": "Mock AI output.",
            "time_complexity": "O(1)",
            "space_complexity": "O(1)",
            "issues": [],
            "suggestions": ["Consider improving the structure."],
            "quality_breakdown": [],
            "quality_score": None,
            "top_improvements": [],
            "documentation": None,
        }

    async def async_fake_ai_call(prompt: str) -> dict:
        return fake_ai_call(prompt)

    monkeypatch.setattr(ai_service_module.ai_service, "call_ai", async_fake_ai_call)

    with TestClient(app) as test_client:
        yield test_client
