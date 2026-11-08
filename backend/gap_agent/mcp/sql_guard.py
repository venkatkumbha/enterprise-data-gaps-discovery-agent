"""Fail-closed checks for agent-submitted SQL.

The MCP database server is allowed to run a single read-only query.
These checks reject writes, attached databases, and chained statements
before SQLite parses the text. The connection is still opened read-only,
so a missed pattern cannot update the file.
"""

from __future__ import annotations

import re

# Statements an agent is allowed to start. WITH covers common table expressions
# that still have to be a read (INSERT/UPDATE inside WITH is rejected below).
_ALLOWED_START = re.compile(r"^(select|with)\b", re.IGNORECASE)

# Whole-word denial list. Matching inside a string literal can false-reject;
# that is acceptable because the tool fails closed.
_FORBIDDEN = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|attach|detach|pragma|create|replace|"
    r"vacuum|reindex|grant|revoke|truncate|into|load_extension|begin|commit|"
    r"rollback|savepoint"
    r")\b",
    re.IGNORECASE,
)

DEFAULT_ROW_LIMIT = 100
MAX_ROW_LIMIT = 200
MAX_SQL_CHARS = 4_000


class SqlRejected(ValueError):
    """The agent query is outside the read-only contract."""


def validate_select(sql: str) -> str:
    """Return stripped SQL or raise SqlRejected.

    One statement only. Comments are not stripped, so a semicolon hidden
    in a comment still fails. That is intentional.
    """
    if sql is None or not str(sql).strip():
        raise SqlRejected("Query is empty. Submit one SELECT statement.")

    text = str(sql).strip()
    if len(text) > MAX_SQL_CHARS:
        raise SqlRejected(f"Query exceeds {MAX_SQL_CHARS} characters.")

    # A trailing semicolon is still a second-statement risk. Reject any semicolon.
    if ";" in text:
        raise SqlRejected("Multiple statements are not allowed.")

    if not _ALLOWED_START.match(text):
        raise SqlRejected("Only a single SELECT or WITH ... SELECT is allowed.")

    found = _FORBIDDEN.search(text)
    if found:
        raise SqlRejected(f"Keyword '{found.group(0)}' is not allowed in a read-only query.")

    return text


def clamp_limit(limit: int, maximum: int = MAX_ROW_LIMIT) -> int:
    """Force the row cap into 1..maximum so a tool call cannot dump a table."""
    try:
        value = int(limit)
    except (TypeError, ValueError) as exc:
        raise SqlRejected("Row limit must be an integer.") from exc
    if value < 1:
        raise SqlRejected("Row limit must be at least 1.")
    return min(value, maximum)


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(name: str) -> str:
    """Allow a bare SQL identifier and nothing else.

    Table and column names are interpolated only after this check and only
    after the name is confirmed to exist in sqlite_master or pragma output.
    """
    if not name or not _IDENTIFIER.match(name):
        raise SqlRejected("Identifier must be a single bare name (letters, digits, underscore).")
    return name
