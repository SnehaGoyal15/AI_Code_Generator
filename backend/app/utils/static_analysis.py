"""Lightweight static checks for debug and review actions.

These checks are intentionally conservative and pattern-based. They never
execute user-submitted code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SUPPORTED_SQL_DANGEROUS_WORDS = {"DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE"}
SUPPORTED_SQL_DATA_CHANGING_WORDS = {"INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "TRUNCATE", "ALTER", "GRANT", "REVOKE", "EXEC", "EXECUTE"}
COMMON_CONTROL_PREFIXES = (
    "if ",
    "if(",
    "for ",
    "for(",
    "while ",
    "while(",
    "elif ",
    "else",
    "except",
    "def ",
    "class ",
    "try",
    "with ",
)


@dataclass(frozen=True)
class StaticCheck:
    """Normalized static analysis finding."""

    severity: str
    message: str


def _count_balanced(text: str, left: str, right: str) -> tuple[int, int]:
    return text.count(left), text.count(right)


def _append(checks: list[StaticCheck], severity: str, message: str) -> None:
    checks.append(StaticCheck(severity=severity, message=message))


def _check_java(code: str, checks: list[StaticCheck]) -> None:
    open_braces, close_braces = _count_balanced(code, "{", "}")
    if open_braces != close_braces:
        _append(checks, "error", "Unmatched braces detected in Java code.")

    lines = code.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.endswith((";", "{", "}", ":")):
            continue
        if re.search(r"\b(return|break|continue|throw)\b", stripped):
            _append(checks, "warning", "Possible missing semicolon in Java code.")
            break
        if re.match(r"^[A-Za-z0-9_().\[\]\s+\-*/%<>=!,?&|^]+$", stripped) and not stripped.endswith((")", "]")):
            _append(checks, "warning", "Possible missing semicolon in Java code.")
            break

    if re.search(r"public\s+class\s+\w+", code) and "public static void main" not in code:
        _append(checks, "warning", "Likely main class structure issue: no obvious 'main' method found.")

    array_decl = re.search(r"(?P<name>[A-Za-z_]\w*)\s*=\s*\{(?P<body>[^}]*)\}", code)
    if array_decl:
        array_name = array_decl.group("name")
        items = [item.strip() for item in array_decl.group("body").split(",") if item.strip()]
        literal_indices = {
            int(match.group("index"))
            for match in re.finditer(rf"\b{re.escape(array_name)}\[(?P<index>\d+)\]", code)
        }
        for index in literal_indices:
            if index >= len(items):
                _append(
                    checks,
                    "warning",
                    f"Possible array index risk: {array_name}[{index}] is outside the obvious literal array size.",
                )
                break


def _check_python(code: str, checks: list[StaticCheck]) -> None:
    lines = code.splitlines()
    indent_levels: list[int] = []
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if "\t" in line[:indent]:
            _append(checks, "warning", "Indentation inconsistency detected: tabs and spaces may be mixed.")
            break
        indent_levels.append(indent)

    non_empty = [line.rstrip() for line in lines if line.strip()]
    if len({level % 4 for level in indent_levels if level > 0}) > 1:
        _append(checks, "warning", "Indentation inconsistency detected in Python code.")

    opens = sum(code.count(token) for token in ("(", "[", "{"))
    closes = sum(code.count(token) for token in (")", "]", "}"))
    if opens != closes:
        _append(checks, "error", "Unmatched brackets detected in Python code.")

    for line in non_empty:
        stripped = line.strip()
        if stripped.startswith(("if ", "elif ", "for ", "while ", "def ", "class ", "with ", "try", "except", "else")):
            if not stripped.endswith(":"):
                _append(checks, "warning", "Possible missing colon after a Python control structure.")
                break


def _check_c_like(code: str, checks: list[StaticCheck]) -> None:
    open_braces, close_braces = _count_balanced(code, "{", "}")
    if open_braces != close_braces:
        _append(checks, "error", "Unmatched braces detected in C/C++ code.")

    if re.search(r"scanf\s*\(\s*\"[^\"]*%[^\"]*\"", code) and "&" not in code:
        _append(checks, "warning", "Suspicious scanf format usage detected; verify argument addresses.")

    for line in code.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "#include")):
            continue
        if stripped.endswith((";", "{", "}", ":")):
            continue
        if re.search(r"\b(return|break|continue|goto)\b", stripped) or re.match(r"^[A-Za-z_][\w\[\]\s,*&=()+\-*/%<>=!?.]*$", stripped):
            _append(checks, "warning", "Possible missing semicolon in C/C++ code.")
            break


def _check_sql(code: str, checks: list[StaticCheck]) -> None:
    upper = code.upper()
    stripped = upper.strip()
    is_select_like = bool(re.match(r"^(WITH|SELECT|EXPLAIN|SHOW|DESCRIBE|PRAGMA)\b", stripped))
    has_data_change = any(re.search(rf"\b{word}\b", upper) for word in SUPPORTED_SQL_DATA_CHANGING_WORDS)

    if is_select_like:
        _append(checks, "warning", "Classification: read-only query.")
        if "SELECT *" in upper:
            _append(checks, "warning", "Performance concern: SELECT * can fetch unnecessary columns.")
        if " WHERE " not in upper and "WHERE\n" not in upper and "WHERE\t" not in upper:
            _append(checks, "warning", "Performance concern: no WHERE clause is visible for a large-table scenario.")
        if " JOIN " in upper and not re.search(r"\b(ON|USING)\b", upper):
            _append(checks, "warning", "Performance concern: JOIN conditions look unclear; verify the join predicate.")
        _append(checks, "warning", "Text recommendation: add indexes on filtered and joined columns only if the query pattern supports it.")
        return

    if has_data_change:
        _append(checks, "warning", "Classification: write/destructive query.")
        _append(checks, "warning", "Possible impact: this query may change or remove data, or alter schema or permissions.")
        if re.search(r"\b(DELETE|UPDATE)\b", upper) and " WHERE " not in upper:
            _append(checks, "warning", "Potentially Destructive Query: DELETE or UPDATE without WHERE clause.")
        if any(word in upper for word in SUPPORTED_SQL_DANGEROUS_WORDS):
            _append(checks, "warning", "Potentially Destructive Query: contains DROP, TRUNCATE, ALTER, GRANT, or REVOKE.")
        if re.search(r"\b(DELETE|UPDATE|INSERT|MERGE)\b", upper):
            _append(checks, "warning", "Safer preview: use a SELECT query to inspect the affected rows before making changes.")
        return

    _append(checks, "warning", "Classification: SQL text detected, but no clear read-only or data-changing pattern was found.")


def analyze_static_checks(code: str, language: str) -> list[dict[str, str]]:
    """Return conservative static findings for selected languages."""
    checks: list[StaticCheck] = []
    language_key = language.strip().lower()
    source_code = code or ""

    if language_key == "java":
        _check_java(source_code, checks)
    elif language_key == "python":
        _check_python(source_code, checks)
    elif language_key in {"c", "c++"}:
        _check_c_like(source_code, checks)
    elif language_key == "sql":
        _check_sql(source_code, checks)

    return [check.__dict__ for check in checks]
