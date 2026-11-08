"""Read-only MCP server over the synthetic CRM, ERP, and warehouse files.

Agents discover systems and run bounded SELECTs. Every call is appended
to a JSONL audit log. Writes are not exposed.

Run from the repo root after `pip install -e .`:

    python -m gap_agent.mcp.database_server
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from gap_agent.mcp.sql_guard import (
    DEFAULT_ROW_LIMIT,
    MAX_ROW_LIMIT,
    SqlRejected,
    clamp_limit,
    validate_identifier,
    validate_select,
)

# backend/gap_agent/mcp/database_server.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if not raw:
        return default
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


SYSTEMS_DIR = _env_path("SYSTEMS_DIR", REPO_ROOT / "data" / "systems")
AUDIT_LOG_PATH = _env_path("AUDIT_LOG_PATH", REPO_ROOT / "logs" / "mcp_audit.jsonl")


def list_system_names() -> list[str]:
    """SQLite files in SYSTEMS_DIR. The stem is the system name agents pass in."""
    if not SYSTEMS_DIR.is_dir():
        return []
    return sorted(path.stem for path in SYSTEMS_DIR.glob("*.sqlite"))


def system_path(system: str) -> Path:
    """Resolve a system name to its file. Reject path separators and unknown names."""
    validate_identifier(system)
    path = (SYSTEMS_DIR / f"{system}.sqlite").resolve()
    # Stay inside the systems directory even if a future caller bypasses the regex.
    if path.parent != SYSTEMS_DIR.resolve():
        raise SqlRejected("System path escapes the systems directory.")
    if not path.is_file():
        known = ", ".join(list_system_names()) or "(none — run the data generator)"
        raise SqlRejected(f"Unknown system '{system}'. Known systems: {known}")
    return path


def connect_readonly(system: str) -> sqlite3.Connection:
    """Open SQLite in read-only URI mode and force query_only as a second lock."""
    path = system_path(system)
    # as_uri() yields file:///C:/... which SQLite accepts with ?mode=ro.
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _rows(cursor: sqlite3.Cursor, limit: int) -> list[dict]:
    return [dict(row) for row in cursor.fetchmany(limit)]


def list_tables(system: str) -> list[str]:
    """User tables only. sqlite internal tables are omitted."""
    with connect_readonly(system) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]


def describe_table(system: str, table: str) -> list[dict]:
    """Column name, type, nullability, and primary-key flag for one table."""
    validate_identifier(table)
    if table not in list_tables(system):
        raise SqlRejected(f"Table '{table}' is not in system '{system}'.")
    with connect_readonly(system) as connection:
        # table was checked against sqlite_master, so quoting it is safe.
        cursor = connection.execute(f"PRAGMA table_info({table})")
        return [
            {
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "default": row[4],
                "pk": bool(row[5]),
            }
            for row in cursor.fetchall()
        ]


def profile_column(system: str, table: str, column: str) -> dict:
    """Null/blank rate, distinct count, and a few most common values."""
    validate_identifier(table)
    validate_identifier(column)
    columns = {col["name"] for col in describe_table(system, table)}
    if column not in columns:
        raise SqlRejected(f"Column '{column}' is not on {system}.{table}.")

    with connect_readonly(system) as connection:
        summary = connection.execute(
            f"""
            SELECT
                COUNT(*) AS row_count,
                SUM(CASE WHEN {column} IS NULL OR TRIM(CAST({column} AS TEXT)) = '' THEN 1 ELSE 0 END) AS null_or_blank,
                COUNT(DISTINCT {column}) AS distinct_count
            FROM {table}
            """
        ).fetchone()
        top = connection.execute(
            f"""
            SELECT CAST({column} AS TEXT) AS value, COUNT(*) AS n
            FROM {table}
            GROUP BY 1
            ORDER BY n DESC
            LIMIT 8
            """
        ).fetchall()

    row_count = int(summary["row_count"])
    null_or_blank = int(summary["null_or_blank"] or 0)
    return {
        "system": system,
        "table": table,
        "column": column,
        "row_count": row_count,
        "null_or_blank": null_or_blank,
        "null_or_blank_ratio": (null_or_blank / row_count) if row_count else 0.0,
        "distinct_count": int(summary["distinct_count"]),
        "top_values": [dict(row) for row in top],
    }


def sample_rows(system: str, table: str, limit: int = 20) -> list[dict]:
    """Return a bounded sample. This is not a random sample; order is undefined."""
    validate_identifier(table)
    if table not in list_tables(system):
        raise SqlRejected(f"Table '{table}' is not in system '{system}'.")
    capped = clamp_limit(limit, MAX_ROW_LIMIT)
    with connect_readonly(system) as connection:
        cursor = connection.execute(f"SELECT * FROM {table} LIMIT ?", (capped,))
        return _rows(cursor, capped)


def safe_query(system: str, sql: str, limit: int = DEFAULT_ROW_LIMIT) -> list[dict]:
    """Run one read-only statement and stop after `limit` rows."""
    statement = validate_select(sql)
    capped = clamp_limit(limit, MAX_ROW_LIMIT)
    with connect_readonly(system) as connection:
        try:
            cursor = connection.execute(statement)
        except sqlite3.Error as exc:
            raise SqlRejected(f"SQLite rejected the query: {exc}") from exc
        if cursor.description is None:
            raise SqlRejected("Query did not return rows.")
        return _rows(cursor, capped)


def audit(tool: str, arguments: dict, started: float, error: str | None, row_count: int | None) -> None:
    """Append one JSON line. Result payloads stay out of the log; the SQL is kept."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "arguments": arguments,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "row_count": row_count,
        "error": error,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, default=str) + "\n")


def run_tool(tool: str, arguments: dict, fn):
    """Audit a tool call. MCP tools and LangGraph nodes both use this wrapper."""
    return _call(tool, arguments, fn)


def _call(tool: str, arguments: dict, fn):
    """Time a tool, audit success and failure, and surface SqlRejected as a tool error."""
    started = time.perf_counter()
    try:
        result = fn()
    except SqlRejected as exc:
        audit(tool, arguments, started, str(exc), None)
        raise
    except Exception as exc:
        audit(tool, arguments, started, f"{type(exc).__name__}: {exc}", None)
        raise
    count = len(result) if isinstance(result, list) else 1
    audit(tool, arguments, started, None, count)
    return result


def build_server():
    """Create the FastMCP server. Imported lazily so SQL tests do not need the mcp package."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("enterprise-data-gaps")

    @mcp.tool()
    def list_systems() -> list[str]:
        """List synthetic enterprise systems available to this server."""
        return _call("list_systems", {}, list_system_names)

    @mcp.tool()
    def tables(system: str) -> list[str]:
        """List tables in one system. system is crm, erp, or warehouse."""
        return _call("tables", {"system": system}, lambda: list_tables(system))

    @mcp.tool()
    def describe(system: str, table: str) -> list[dict]:
        """Describe columns for one table in one system."""
        return _call(
            "describe",
            {"system": system, "table": table},
            lambda: describe_table(system, table),
        )

    @mcp.tool()
    def profile(system: str, table: str, column: str) -> dict:
        """Profile one column: null rate, distinct count, and top values."""
        return _call(
            "profile",
            {"system": system, "table": table, "column": column},
            lambda: profile_column(system, table, column),
        )

    @mcp.tool()
    def sample(system: str, table: str, limit: int = 20) -> list[dict]:
        """Return up to `limit` rows from one table. Maximum is 200."""
        return _call(
            "sample",
            {"system": system, "table": table, "limit": limit},
            lambda: sample_rows(system, table, limit),
        )

    @mcp.tool()
    def query(system: str, sql: str, limit: int = DEFAULT_ROW_LIMIT) -> list[dict]:
        """Run one read-only SELECT against one system. Results are row-capped."""
        return _call(
            "query",
            {"system": system, "sql": sql, "limit": limit},
            lambda: safe_query(system, sql, limit),
        )

    return mcp


def main() -> None:
    """stdio transport, which Cursor and the MCP inspector both launch as a subprocess."""
    build_server().run()


if __name__ == "__main__":
    main()
