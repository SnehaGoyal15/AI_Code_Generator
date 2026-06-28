"""Reusable prompt builders for CodeMentor AI.

Every prompt in this module instructs the model to return strictly valid JSON
only, with no Markdown outside the JSON object.
"""

from __future__ import annotations

from textwrap import dedent

SUPPORTED_LANGUAGES = ["Python", "Java", "C", "C++", "JavaScript", "SQL"]

JSON_RESPONSE_SCHEMA = dedent(
    """
    {
      "code": "string or null",
      "explanation": "string or null",
      "time_complexity": "string or null",
      "space_complexity": "string or null",
      "issues": [
        {
          "type": "Syntax Error | Runtime Error | Logical Error | Style Issue | Security Issue",
          "severity": "Critical | High | Medium | Low | Suggestion",
          "line_hint": "string",
          "message": "string",
          "fix": "string"
        }
      ],
      "suggestions": ["string"],
      "quality_breakdown": [
        {
          "category": "string",
          "score": 0,
          "max_score": 2,
          "notes": "string"
        }
      ],
      "quality_score": 0,
      "top_improvements": ["string"],
      "documentation": "string or null"
    }
    """
).strip()

# Example input:
# generate_code_prompt("Write a function that reverses a string", "Python")
# Example output format expected from the model:
# {"code":"...","explanation":"...","time_complexity":"...","space_complexity":"...","issues":[],"suggestions":["..."],"quality_score":8,"documentation":null}


def _base_instructions(task_name: str, language: str) -> str:
    """Return shared system instructions for JSON-only responses."""
    return dedent(
        f"""
        You are CodeMentor AI, an expert coding assistant for academic projects.
        Task: {task_name}
        Target language: {language}

        Return strictly valid JSON only.
        Do not return Markdown, headings, code fences, or any text outside JSON.
        Do not use triple backticks inside JSON values.
        Use double quotes for all JSON strings.
        Keep strings concise but helpful.
        """
    ).strip()


def _json_contract(details: str) -> str:
    """Return the shared JSON response contract with task-specific guidance."""
    return dedent(
        f"""
        The response must follow this JSON structure where applicable:

        {JSON_RESPONSE_SCHEMA}

        Additional task rules:
        {details}
        """
    ).strip()


def _sql_safety_instructions() -> str:
    return dedent(
        """
        SQL safety mode:
        - Treat SQL as text only. Never imply execution against a real database.
        - Do not recommend or describe executing queries.
        - If the SQL is destructive or data-changing, clearly classify it as write/destructive and explain the possible impact in simple terms.
        - If relevant, suggest a safer read-only preview query, such as a SELECT preview of affected rows.
        - If the SQL is read-only, classify it as read-only and mention obvious performance concerns when visible.
        - For SELECT queries, warn about SELECT *, missing WHERE clauses on large-table scenarios, and unclear JOIN conditions when obvious.
        """
    ).strip()


def _compose_prompt(task_name: str, language: str, body: str, details: str) -> str:
    sql_section = f"\n\n{_sql_safety_instructions()}" if language.strip().lower() == "sql" else ""
    return dedent(
        f"""
        {_base_instructions(task_name, language)}{sql_section}

        {body}

        {_json_contract(details)}
        """
    ).strip()


def generate_code_prompt(user_prompt: str, language: str) -> str:
    """Build a prompt for generating beginner-friendly code."""
    details = dedent(
        """
        - Generate correct and beginner-friendly code.
        - Follow conventions for the selected language.
        - Include minimal useful comments.
        - Handle normal edge cases.
        - Provide time and space complexity.
        - Suggest one alternative approach.
        - Put the final code in the "code" field.
        - Put a plain-language walkthrough in the "explanation" field.
        - Put any noteworthy code quality or correctness issues in the "issues" array.
        - Put improvement ideas and the alternative approach in "suggestions".
        - Leave "documentation" as null unless it is directly relevant.
        """
    ).strip()

    return _compose_prompt(
        "Generate code",
        language,
        f"User request:\n{user_prompt}",
        details,
    )


def explain_code_prompt(code: str, language: str) -> str:
    """Build a prompt for explaining existing code."""
    details = dedent(
        """
        - Explain the code in beginner-friendly language.
        - Keep the original code intact in the "code" field.
        - Focus on what each part does, why it exists, and the overall flow.
        - Include time and space complexity if they can be reasonably inferred.
        - If complexity cannot be inferred, use null.
        - Keep "issues" empty unless a clear problem is visible.
        - Add helpful learning suggestions in "suggestions".
        - Leave "documentation" as null unless you are producing doc content.
        """
    ).strip()

    return _compose_prompt(
        "Explain code",
        language,
        f"Code to explain:\n{code}",
        details,
    )


def debug_code_prompt(code: str, language: str) -> str:
    """Build a prompt for debugging code."""
    details = dedent(
        """
        - Identify syntax, logical, and runtime errors.
        - Explain root causes simply.
        - Provide corrected code in the "code" field.
        - Do not claim an error is certain unless it is clearly visible.
        - If a possible issue is uncertain, describe it as a likely problem in the "issues" array.
        - Include normal complexity estimates when they are relevant to the corrected code.
        - Add practical fixes in each issue object.
        - Put any broader debugging tips in "suggestions".
        """
    ).strip()

    return _compose_prompt(
        "Debug code",
        language,
        f"Code to debug:\n{code}",
        details,
    )


def optimize_code_prompt(code: str, language: str) -> str:
    """Build a prompt for optimizing code."""
    details = dedent(
        """
        - Analyze unnecessary loops, duplicate computation, memory usage, and algorithm choice.
        - Preserve the original functionality.
        - Explain whether optimization is actually needed.
        - Return the improved code in the "code" field if an improvement exists.
        - If no meaningful optimization is needed, keep the code close to the original and explain why.
        - Include time and space complexity for the optimized version.
        - Put concrete optimization observations in "issues" if relevant.
        - Suggest one alternative approach in "suggestions".
        """
    ).strip()

    return _compose_prompt(
        "Optimize code",
        language,
        f"Code to optimize:\n{code}",
        details,
    )


def review_code_prompt(code: str, language: str) -> str:
    """Build a prompt for reviewing code quality."""
    details = dedent(
        """
        - Check naming, duplication, nesting, validation, readability, maintainability, comments, and security concerns.
        - Score each rubric category from 0 to 2 and include a structured "quality_breakdown" array with these categories:
          1. Correctness and potential bugs
          2. Readability and naming
          3. Efficiency
          4. Maintainability and structure
          5. Documentation and comments
        - Add the total out of 10 in the "quality_score" field.
        - Include a "top_improvements" array with the top 3 refactoring suggestions.
        - Explain the biggest quality risks in simple terms using wording like "potential issue", "likely issue", and "consider improving".
        - Keep the original code in the "code" field unless a small fix is necessary.
        - Use the "issues" array for concrete problems found during review and assign a severity value to each issue.
        - Use severity labels from this set only: Critical, High, Medium, Low, Suggestion.
        - Add improvement suggestions that are practical and specific without changing program behavior unless required.
        - Complexity fields can be null if they are not relevant to a review.
        """
    ).strip()

    return _compose_prompt(
        "Review code quality",
        language,
        f"Code to review:\n{code}",
        details,
    )


def documentation_prompt(code: str, language: str) -> str:
    """Build a prompt for generating documentation and README content."""
    details = dedent(
        """
        - Produce function/class descriptions, parameters, return values, usage example, inline comment suggestions, and README content.
        - Put the main documentation text in the "documentation" field.
        - Keep the "code" field as the provided code or a lightly formatted version if needed.
        - If the code is insufficient to document fully, infer only what is clearly visible.
        - Add brief suggestions for improving docs coverage or structure.
        - Complexity fields may be null unless they are useful to mention.
        """
    ).strip()

    return _compose_prompt(
        "Generate documentation",
        language,
        f"Code or project context:\n{code}",
        details,
    )


# Backward-compatible templates for older imports.
CODE_GENERATION_TEMPLATE = (
    "Use generate_code_prompt(user_prompt, language) instead of this legacy template."
)
DEBUG_TEMPLATE = "Use debug_code_prompt(code, language) instead of this legacy template."
DOCUMENTATION_TEMPLATE = (
    "Use documentation_prompt(code, language) instead of this legacy template."
)
