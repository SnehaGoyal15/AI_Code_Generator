"""AI service for CodeMentor AI.

This module keeps provider access isolated, validates model output, and falls
back safely when the provider is unavailable or returns invalid JSON.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import get_settings

from .prompt_templates import (
    debug_code_prompt,
    documentation_prompt,
    explain_code_prompt,
    generate_code_prompt,
    optimize_code_prompt,
    review_code_prompt,
)

logger = logging.getLogger(__name__)

AI_TIMEOUT_SECONDS = 30.0
GEMINI_GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

EXPECTED_AI_FIELDS = (
    "code",
    "explanation",
    "time_complexity",
    "space_complexity",
    "issues",
    "suggestions",
    "quality_score",
    "documentation",
)


class AIIssue(BaseModel):
    """Normalized issue entry returned by the AI provider."""

    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="")
    severity: str = Field(default="Medium")
    line_hint: str = Field(default="")
    message: str = Field(default="")
    fix: str = Field(default="")


class AIResponsePayload(BaseModel):
    """Validated AI response shape used by the application."""

    model_config = ConfigDict(extra="ignore")

    code: str | None = None
    explanation: str | None = None
    time_complexity: str | None = None
    space_complexity: str | None = None
    issues: list[AIIssue] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    quality_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: int | None = Field(default=None, ge=0, le=10)
    top_improvements: list[str] = Field(default_factory=list)
    documentation: str | None = None


def _fallback_response(message: str) -> dict[str, Any]:
    """Return a predictable error object with the expected fields present."""
    return {
        "code": None,
        "explanation": None,
        "time_complexity": None,
        "space_complexity": None,
        "issues": [],
        "suggestions": [],
        "quality_breakdown": [],
        "quality_score": 0,
        "top_improvements": [],
        "documentation": None,
        "error": message,
    }


def validate_ai_json(payload: Any) -> dict[str, Any]:
    """Validate and normalize AI JSON into the expected response contract."""
    try:
        if isinstance(payload, str):
            payload = json.loads(payload)

        if not isinstance(payload, dict):
            raise TypeError("AI response is not a JSON object.")

        validated = AIResponsePayload.model_validate(payload)
        normalized = validated.model_dump()
        normalized["issues"] = [issue.model_dump() for issue in validated.issues]
        return normalized
    except (json.JSONDecodeError, TypeError, ValidationError, ValueError) as exc:
        logger.warning("Invalid AI JSON received: %s", exc)
        return _fallback_response("Invalid JSON returned by AI provider.")


def _build_gemini_request(prompt: str) -> dict[str, Any]:
    """Build a Gemini request that asks for JSON-only output."""
    return {
        "system_instruction": {
            "parts": [
                {
                    "text": (
                        "Return strictly valid JSON only. Do not include Markdown, "
                        "backticks, or extra commentary."
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }


async def _call_gemini(prompt: str, api_key: str, model: str) -> dict[str, Any]:
    """Send a request to Gemini's generateContent endpoint."""
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = _build_gemini_request(prompt)
    url = GEMINI_GENERATE_CONTENT_URL.format(model=model)

    async with httpx.AsyncClient(timeout=httpx.Timeout(AI_TIMEOUT_SECONDS)) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    text = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text")
    )
    if text is None:
        raise ValueError("Provider response did not include text content.")
    return validate_ai_json(text)


async def call_ai(prompt: str) -> dict[str, Any]:
    """Call the configured AI provider and return a validated JSON response.

    The function never raises provider-specific errors to the FastAPI layer.
    It logs failures without exposing secrets and returns a safe fallback object.
    """
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    model = (settings.gemini_model or "").strip() or "gemini-2.5-flash"

    if not api_key:
        logger.warning("GEMINI_API_KEY is not configured.")
        return _fallback_response("AI API key is not configured.")

    try:
        return await _call_gemini(prompt, api_key, model)
    except httpx.HTTPStatusError as exc:
        status_code = getattr(exc.response, "status_code", "unknown")
        logger.exception("AI provider request failed with HTTP status %s.", status_code)
        return _fallback_response("AI provider request failed.")
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.exception("AI provider request failed: %s", exc.__class__.__name__)
        return _fallback_response("AI provider request timed out or was unreachable.")
    except Exception as exc:  # noqa: BLE001 - intentionally contained to prevent crashes
        logger.exception("Unexpected AI service failure: %s", exc.__class__.__name__)
        return _fallback_response("Unexpected AI service failure.")


class AIService:
    """Convenience wrapper for prompt building and AI calls."""

    async def call_ai(self, prompt: str) -> dict[str, Any]:
        return await call_ai(prompt)

    def build_code_prompt(self, user_prompt: str, language: str) -> str:
        return generate_code_prompt(user_prompt, language)

    def build_explain_prompt(self, code: str, language: str) -> str:
        return explain_code_prompt(code, language)

    def build_debug_prompt(self, code: str, language: str) -> str:
        return debug_code_prompt(code, language)

    def build_optimize_prompt(self, code: str, language: str) -> str:
        return optimize_code_prompt(code, language)

    def build_review_prompt(self, code: str, language: str) -> str:
        return review_code_prompt(code, language)

    def build_documentation_prompt(self, code: str, language: str) -> str:
        return documentation_prompt(code, language)

    async def generate_code(self, user_prompt: str, language: str) -> dict[str, Any]:
        return await call_ai(self.build_code_prompt(user_prompt, language))

    async def explain_code(self, code: str, language: str) -> dict[str, Any]:
        return await call_ai(self.build_explain_prompt(code, language))

    async def debug_code(self, code: str, language: str) -> dict[str, Any]:
        return await call_ai(self.build_debug_prompt(code, language))

    async def optimize_code(self, code: str, language: str) -> dict[str, Any]:
        return await call_ai(self.build_optimize_prompt(code, language))

    async def review_code(self, code: str, language: str) -> dict[str, Any]:
        return await call_ai(self.build_review_prompt(code, language))

    async def generate_docs(self, code: str, language: str) -> dict[str, Any]:
        return await call_ai(self.build_documentation_prompt(code, language))


ai_service = AIService()
