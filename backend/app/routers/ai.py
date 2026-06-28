"""AI action endpoints for CodeMentor AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, status

from .. import schemas
from ..ai_service import ai_service, validate_ai_json
from ..auth import get_current_user
from ..database import get_db
from ..prompt_templates import (
    debug_code_prompt,
    documentation_prompt,
    explain_code_prompt,
    generate_code_prompt,
    optimize_code_prompt,
    review_code_prompt,
)
from ..utils.static_analysis import analyze_static_checks
from ..services.history_service import create_history

router = APIRouter(prefix="", tags=["ai actions"])

SUPPORTED_LANGUAGES = {"python", "java", "c", "c++", "javascript", "sql"}
MAX_PROMPT_LENGTH = 4000
MAX_CODE_LENGTH = 30000


@dataclass(frozen=True)
class ActionSpec:
    action_type: str
    requires_prompt: bool
    requires_code: bool
    template_builder: Callable[[str, str], str]
    description: str


ACTION_SPECS = {
    "generate": ActionSpec(
        action_type="generate",
        requires_prompt=True,
        requires_code=False,
        template_builder=generate_code_prompt,
        description="Generate code from a natural-language prompt.",
    ),
    "explain": ActionSpec(
        action_type="explain",
        requires_prompt=False,
        requires_code=True,
        template_builder=explain_code_prompt,
        description="Explain existing code in beginner-friendly language.",
    ),
    "debug": ActionSpec(
        action_type="debug",
        requires_prompt=False,
        requires_code=True,
        template_builder=debug_code_prompt,
        description="Identify and fix syntax, logical, and runtime issues.",
    ),
    "optimize": ActionSpec(
        action_type="optimize",
        requires_prompt=False,
        requires_code=True,
        template_builder=optimize_code_prompt,
        description="Analyze and improve code performance and memory usage.",
    ),
    "review": ActionSpec(
        action_type="review",
        requires_prompt=False,
        requires_code=True,
        template_builder=review_code_prompt,
        description="Review code quality, maintainability, and security.",
    ),
    "documentation": ActionSpec(
        action_type="documentation",
        requires_prompt=False,
        requires_code=True,
        template_builder=documentation_prompt,
        description="Generate documentation and README content.",
    ),
}


def _normalize_text(value: str | None, preserve_formatting: bool = False) -> str | None:
    """Trim outer whitespace while preserving inner formatting."""
    if value is None:
        return None
    if preserve_formatting:
        return value.strip("\n\r")
    return value.strip()


def _validate_language(language: str) -> str:
    normalized = language.strip()
    if normalized.lower() not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language '{language}'. Supported languages are: Python, Java, C, C++, JavaScript, SQL.",
        )
    return normalized


def _validate_sizes(prompt: str | None, code: str | None) -> None:
    if prompt is not None and len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Prompt exceeds the maximum length of {MAX_PROMPT_LENGTH} characters.",
        )
    if code is not None and len(code) > MAX_CODE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Code exceeds the maximum length of {MAX_CODE_LENGTH} characters.",
        )


def _build_response_payload(action_type: str, history_id: int, normalized: dict) -> schemas.AIActionResponse:
    return schemas.AIActionResponse(
        history_id=history_id,
        action_type=action_type,
        code=normalized.get("code"),
        explanation=normalized.get("explanation"),
        time_complexity=normalized.get("time_complexity"),
        space_complexity=normalized.get("space_complexity"),
        issues=normalized.get("issues", []),
        static_checks=normalized.get("static_checks", []),
        suggestions=normalized.get("suggestions", []),
        quality_breakdown=normalized.get("quality_breakdown", []),
        quality_score=normalized.get("quality_score") if action_type == "review" else None,
        top_improvements=normalized.get("top_improvements", []),
        documentation=normalized.get("documentation"),
    )


def _merge_static_checks(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for check in group:
            message = check.get("message", "")
            severity = check.get("severity", "warning")
            key = (severity, message)
            if key in seen:
                continue
            seen.add(key)
            merged.append({"severity": severity, "message": message})
    return merged


async def _handle_action(
    action_key: str,
    payload: schemas.AIActionRequest,
    db,
    current_user,
) -> schemas.AIActionResponse:
    spec = ACTION_SPECS[action_key]

    language = _validate_language(payload.language)
    prompt_text = _normalize_text(payload.prompt)
    code_text = _normalize_text(payload.code, preserve_formatting=True)

    _validate_sizes(prompt_text, code_text)

    if spec.requires_prompt and not prompt_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt is required for this action.")

    if spec.requires_code and not code_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code is required for this action.")

    template_input = prompt_text if spec.requires_prompt else code_text
    assert template_input is not None
    input_checks = analyze_static_checks(code_text or "", language) if action_key in {"debug", "review"} else []
    ai_prompt = spec.template_builder(template_input, language)
    ai_result = await ai_service.call_ai(ai_prompt)
    normalized_result = validate_ai_json(ai_result)
    output_checks = analyze_static_checks(normalized_result.get("code") or "", language) if language.lower() == "sql" else []
    normalized_result["static_checks"] = _merge_static_checks(input_checks, output_checks)

    response_data = schemas.CodeHistoryCreate(
        user_id=current_user["id"],
        prompt=prompt_text or (code_text or ""),
        language=language,
        action_type=spec.action_type,
        input_code=code_text if spec.requires_code else None,
        generated_code=normalized_result.get("code"),
        explanation=normalized_result.get("explanation"),
        time_complexity=normalized_result.get("time_complexity"),
        space_complexity=normalized_result.get("space_complexity"),
        suggestions=normalized_result.get("suggestions", []),
        quality_breakdown=normalized_result.get("quality_breakdown", []),
        top_improvements=normalized_result.get("top_improvements", []),
    )
    record = create_history(db, response_data)

    return _build_response_payload(spec.action_type, record["id"], normalized_result)


@router.post(
    "/generate",
    response_model=schemas.AIActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate code",
    description="Generate beginner-friendly code from a natural-language prompt and save the result to history.",
)
async def generate_code_endpoint(
    payload: schemas.AIActionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> schemas.AIActionResponse:
    return await _handle_action("generate", payload, db, current_user)


@router.post(
    "/explain",
    response_model=schemas.AIActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Explain code",
    description="Explain existing code in beginner-friendly language and save the result to history.",
)
async def explain_code_endpoint(
    payload: schemas.AIActionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> schemas.AIActionResponse:
    return await _handle_action("explain", payload, db, current_user)


@router.post(
    "/debug",
    response_model=schemas.AIActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Debug code",
    description="Find syntax, logical, and runtime issues in code and save the corrected result to history.",
)
async def debug_code_endpoint(
    payload: schemas.AIActionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> schemas.AIActionResponse:
    return await _handle_action("debug", payload, db, current_user)


@router.post(
    "/optimize",
    response_model=schemas.AIActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Optimize code",
    description="Analyze and improve code performance, memory use, and structure, then save to history.",
)
async def optimize_code_endpoint(
    payload: schemas.AIActionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> schemas.AIActionResponse:
    return await _handle_action("optimize", payload, db, current_user)


@router.post(
    "/review",
    response_model=schemas.AIActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Review code",
    description="Review code quality, readability, maintainability, and security, then save to history.",
)
async def review_code_endpoint(
    payload: schemas.AIActionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> schemas.AIActionResponse:
    return await _handle_action("review", payload, db, current_user)


@router.post(
    "/documentation",
    response_model=schemas.AIActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate documentation",
    description="Generate function, class, README, and usage documentation from code and save to history.",
)
async def documentation_endpoint(
    payload: schemas.AIActionRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
) -> schemas.AIActionResponse:
    return await _handle_action("documentation", payload, db, current_user)
