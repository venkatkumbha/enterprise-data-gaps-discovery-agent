"""Specialist steps used by the LangGraph supervisor.

Each function reads the synthetic systems through the same guarded tools as
the MCP server, appends evidence-backed findings, and marks itself done so
the supervisor cannot call it twice.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import date

from gap_agent.graph.state import DiscoveryState
from gap_agent.mcp.database_server import (
    describe_table,
    list_system_names,
    list_tables,
    profile_column,
    run_tool,
    safe_query,
    sample_rows,
)
from gap_agent.mcp.sql_guard import SqlRejected

# Tables a steward would expect from data/catalog/official_catalog.md.
# Anything else on disk is shadow data.
CATALOG = {
    "crm": {"customers", "contacts"},
    "erp": {"customers", "products", "orders"},
    "warehouse": {"dim_customer", "fact_order"},
}

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _tool(tool: str, arguments: dict, fn):
    """Run one audited read. A rejected query becomes a trace note, not a crash."""
    try:
        return run_tool(tool, arguments, fn), None
    except SqlRejected as exc:
        return None, str(exc)


def _finding(
    finding_id: str,
    agent: str,
    category: str,
    severity: str,
    title: str,
    summary: str,
    evidence: list[dict],
) -> dict:
    return {
        "id": finding_id,
        "agent": agent,
        "category": category,
        "severity": severity,
        "title": title,
        "summary": summary,
        "evidence": evidence,
    }


def _trace(agent: str, summary: str, started: float, finding_count: int) -> dict:
    return {
        "agent": agent,
        "summary": summary,
        "finding_count": finding_count,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def schema_explorer(state: DiscoveryState) -> dict:
    """List every system and compare its tables and keys with the catalog."""
    started = time.perf_counter()
    findings = list(state.get("findings") or [])
    names, error = _tool("list_systems", {}, list_system_names)
    if error or not names:
        findings.append(
            _finding(
                "no-systems",
                "schema_explorer",
                "coverage",
                "high",
                "No enterprise systems are loaded",
                "The systems directory has no SQLite files. Generate the lab data before asking the agents to search.",
                [{"system": None, "tool": "list_systems", "detail": error or "empty directory", "rows": []}],
            )
        )
        return {
            "systems": [],
            "findings": findings,
            "trace": list(state.get("trace") or [])
            + [_trace("schema_explorer", "Stopped because no systems were found.", started, 1)],
            "schema_done": True,
            "profile_done": True,
            "reconcile_done": True,
            "blocked": True,
        }

    inventory = []
    expected_keys = {
        "crm": ("customers", "customer_id"),
        "erp": ("customers", "cust_id"),
        "warehouse": ("dim_customer", "customer_key"),
    }
    key_rows = []
    shadow = []

    for name in names:
        tables, table_error = _tool("tables", {"system": name}, lambda name=name: list_tables(name))
        tables = tables or []
        inventory.append({"name": name, "tables": tables, "error": table_error})
        extras = sorted(set(tables) - CATALOG.get(name, set()))
        for table in extras:
            rows, _ = _tool(
                "sample",
                {"system": name, "table": table, "limit": 5},
                lambda name=name, table=table: sample_rows(name, table, 5),
            )
            shadow.append({"system": name, "table": table, "rows": rows or []})

        if name in expected_keys:
            table, column = expected_keys[name]
            if table in tables:
                described, _ = _tool(
                    "describe",
                    {"system": name, "table": table},
                    lambda name=name, table=table: describe_table(name, table),
                )
                pk = [col["name"] for col in (described or []) if col.get("pk")]
                key_rows.append({"system": name, "table": table, "primary_key": pk or [column]})

    if shadow:
        findings.append(
            _finding(
                "shadow-tables",
                "schema_explorer",
                "shadow_data",
                "medium",
                "Tables exist that the official catalog does not list",
                "The schema explorer compared sqlite_master with the catalog. These tables are queryable and undocumented.",
                [
                    {
                        "system": item["system"],
                        "tool": "sample",
                        "detail": item["table"],
                        "rows": item["rows"],
                    }
                    for item in shadow
                ],
            )
        )

    pk_names = {row["primary_key"][0] for row in key_rows if row["primary_key"]}
    if len(pk_names) > 1:
        findings.append(
            _finding(
                "customer-key-names",
                "schema_explorer",
                "semantic_drift",
                "medium",
                "The customer key has a different name in each system",
                "The same concept is stored as "
                + ", ".join(sorted(pk_names))
                + ". A join that assumes one column name will miss records.",
                [{"system": row["system"], "tool": "describe", "detail": row["table"], "rows": [row]} for row in key_rows],
            )
        )

    added = len(findings) - len(state.get("findings") or [])
    return {
        "systems": inventory,
        "findings": findings,
        "trace": list(state.get("trace") or [])
        + [_trace("schema_explorer", f"Catalogued {len(inventory)} systems.", started, added)],
        "schema_done": True,
    }


def profiler(state: DiscoveryState) -> dict:
    """Measure nulls, status encodings, and how old each extract is."""
    started = time.perf_counter()
    if state.get("blocked"):
        return {"profile_done": True}
    findings = list(state.get("findings") or [])
    before = len(findings)

    email_profile, _ = _tool(
        "profile",
        {"system": "erp", "table": "customers", "column": "email_address"},
        lambda: profile_column("erp", "customers", "email_address"),
    )
    if email_profile and email_profile["null_or_blank"] > 0:
        missing, _ = _tool(
            "query",
            {"system": "erp", "sql": "SELECT cust_id, customer_name FROM customers WHERE email_address IS NULL"},
            lambda: safe_query(
                "erp",
                "SELECT cust_id, customer_name FROM customers WHERE email_address IS NULL",
                50,
            ),
        )
        ratio = round(email_profile["null_or_blank_ratio"] * 100, 1)
        findings.append(
            _finding(
                "erp-null-emails",
                "profiler",
                "completeness",
                "medium",
                f"{email_profile['null_or_blank']} ERP customers have no email ({ratio}%)",
                "email_address is null on records the CRM still has an address for. Downstream agents that match on email will drop these customers.",
                [
                    {
                        "system": "erp",
                        "tool": "profile",
                        "detail": "customers.email_address",
                        "rows": [email_profile],
                    },
                    {
                        "system": "erp",
                        "tool": "query",
                        "detail": "SELECT cust_id, customer_name FROM customers WHERE email_address IS NULL",
                        "rows": missing or [],
                    },
                ],
            )
        )

    status_targets = [
        ("crm", "customers", "status"),
        ("erp", "customers", "account_status"),
        ("warehouse", "dim_customer", "status_code"),
    ]
    status_evidence = []
    encodings = []
    for system, table, column in status_targets:
        profile, _ = _tool(
            "profile",
            {"system": system, "table": table, "column": column},
            lambda system=system, table=table, column=column: profile_column(system, table, column),
        )
        if not profile:
            continue
        values = [item.get("value") for item in profile["top_values"]]
        encodings.append(set(values))
        status_evidence.append(
            {
                "system": system,
                "tool": "profile",
                "detail": f"{table}.{column}",
                "rows": profile["top_values"],
            }
        )
    if len(encodings) > 1 and len({frozenset(item) for item in encodings}) > 1:
        findings.append(
            _finding(
                "status-encodings",
                "profiler",
                "semantic_drift",
                "medium",
                "Customer status is encoded differently in each system",
                "Active and inactive are stored as words, letters, or digits. A filter written for one system will misread the others.",
                status_evidence,
            )
        )

    date_queries = [
        ("crm", "SELECT MIN(updated_at) AS min_date, MAX(updated_at) AS max_date FROM customers"),
        ("erp", "SELECT MIN(last_modified) AS min_date, MAX(last_modified) AS max_date FROM customers"),
        ("warehouse", "SELECT MIN(as_of_date) AS min_date, MAX(as_of_date) AS max_date FROM dim_customer"),
    ]
    date_rows = []
    for system, sql in date_queries:
        rows, _ = _tool("query", {"system": system, "sql": sql}, lambda system=system, sql=sql: safe_query(system, sql, 5))
        if rows:
            date_rows.append({"system": system, "tool": "query", "detail": sql, "rows": rows})
    stamps = {item["system"]: item["rows"][0].get("max_date") for item in date_rows}
    if stamps.get("warehouse") and stamps.get("crm") and stamps["warehouse"] < stamps["crm"]:
        warehouse_day = date.fromisoformat(stamps["warehouse"])
        crm_day = date.fromisoformat(stamps["crm"])
        lag_days = (crm_day - warehouse_day).days
        findings.append(
            _finding(
                "warehouse-stale",
                "profiler",
                "freshness",
                "medium",
                f"The warehouse extract is {lag_days} days behind CRM",
                f"Warehouse as-of date is {stamps['warehouse']}. CRM was updated {stamps['crm']}. Agents that read the warehouse are not seeing the current operational record.",
                date_rows,
            )
        )

    added = len(findings) - before
    return {
        "findings": findings,
        "trace": list(state.get("trace") or [])
        + [_trace("profiler", "Profiled email, status, and freshness.", started, added)],
        "profile_done": True,
    }


def reconciliation(state: DiscoveryState) -> dict:
    """Compare customers and child records across CRM, ERP, and the warehouse."""
    started = time.perf_counter()
    if state.get("blocked"):
        return {"reconcile_done": True}
    findings = list(state.get("findings") or [])
    before = len(findings)

    orphan_sql = (
        "SELECT order_id, cust_id, product_sku, amount, order_date "
        "FROM orders WHERE cust_id NOT IN (SELECT cust_id FROM customers)"
    )
    orphans, _ = _tool("query", {"system": "erp", "sql": orphan_sql}, lambda: safe_query("erp", orphan_sql, 50))
    if orphans:
        findings.append(
            _finding(
                "orphan-orders",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(orphans)} orders point at a customer that does not exist",
                "ERP orders reference cust_id values missing from the ERP customer table.",
                [{"system": "erp", "tool": "query", "detail": orphan_sql, "rows": orphans}],
            )
        )

    contact_sql = (
        "SELECT contact_id, customer_id, full_name, email FROM contacts c "
        "WHERE NOT EXISTS (SELECT 1 FROM customers k WHERE k.customer_id = c.customer_id)"
    )
    bad_contacts, _ = _tool(
        "query",
        {"system": "crm", "sql": contact_sql},
        lambda: safe_query("crm", contact_sql, 50),
    )
    if bad_contacts:
        findings.append(
            _finding(
                "orphan-contacts",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(bad_contacts)} CRM contacts have no customer",
                "contacts.customer_id does not match any customers.customer_id.",
                [{"system": "crm", "tool": "query", "detail": contact_sql, "rows": bad_contacts}],
            )
        )

    crm_sql = "SELECT customer_id, legal_name, email, status FROM customers"
    erp_sql = "SELECT cust_id, customer_name, email_address, account_status FROM customers"
    wh_sql = (
        "SELECT customer_key, source_crm_id, source_erp_id, display_name, email, status_code "
        "FROM dim_customer"
    )
    crm_rows, _ = _tool("query", {"system": "crm", "sql": crm_sql}, lambda: safe_query("crm", crm_sql, 200))
    erp_rows, _ = _tool("query", {"system": "erp", "sql": erp_sql}, lambda: safe_query("erp", erp_sql, 200))
    wh_rows, _ = _tool("query", {"system": "warehouse", "sql": wh_sql}, lambda: safe_query("warehouse", wh_sql, 200))
    crm_rows = crm_rows or []
    erp_rows = erp_rows or []
    wh_rows = wh_rows or []

    by_email: dict[str, list] = {}
    for row in crm_rows:
        if row.get("email"):
            by_email.setdefault(row["email"], []).append(row)
    shared = [rows for rows in by_email.values() if len(rows) > 1]
    if shared:
        flat = [row for group in shared for row in group]
        findings.append(
            _finding(
                "shared-email",
                "reconciliation",
                "identity",
                "high",
                "One email address is used by more than one CRM customer",
                "Matching on email alone would collapse distinct customers into a single identity.",
                [{"system": "crm", "tool": "query", "detail": crm_sql, "rows": flat}],
            )
        )

    erp_by_id = {row["cust_id"]: row for row in erp_rows}
    wh_by_source = {row["source_crm_id"]: row for row in wh_rows if row.get("source_crm_id") is not None}
    variant_rows = []
    for row in crm_rows:
        names = {row["legal_name"]}
        erp_row = erp_by_id.get(row["customer_id"])
        wh_row = wh_by_source.get(row["customer_id"])
        if erp_row:
            names.add(erp_row["customer_name"])
        if wh_row:
            names.add(wh_row["display_name"])
        if len(names) > 1:
            variant_rows.append(
                {
                    "customer_id": row["customer_id"],
                    "crm": row["legal_name"],
                    "erp": erp_row["customer_name"] if erp_row else None,
                    "warehouse": wh_row["display_name"] if wh_row else None,
                }
            )
    if variant_rows:
        findings.append(
            _finding(
                "name-variants",
                "reconciliation",
                "identity",
                "high",
                f"{len(variant_rows)} customers have different names across systems",
                "The identifier matches, but the display name does not. Exact-name joins will treat these as different companies.",
                [{"system": "crm", "tool": "query", "detail": "name comparison on customer id", "rows": variant_rows}],
            )
        )

    wh_source_ids = set(wh_by_source)
    missing = [row for row in crm_rows if row["customer_id"] not in wh_source_ids]
    if missing:
        findings.append(
            _finding(
                "missing-from-warehouse",
                "reconciliation",
                "coverage",
                "medium",
                f"{len(missing)} CRM customers are missing from the warehouse",
                "These operational customers have no dim_customer row, so analytics and any agent on the warehouse cannot see them.",
                [{"system": "crm", "tool": "query", "detail": crm_sql, "rows": missing}],
            )
        )

    warehouse_only = [row for row in wh_rows if row.get("source_crm_id") is None and row.get("source_erp_id") is None]
    if warehouse_only:
        findings.append(
            _finding(
                "warehouse-only",
                "reconciliation",
                "coverage",
                "medium",
                f"{len(warehouse_only)} warehouse customers have no source-system id",
                "The extract contains a customer that cannot be traced back to CRM or ERP.",
                [{"system": "warehouse", "tool": "query", "detail": wh_sql, "rows": warehouse_only}],
            )
        )

    added = len(findings) - before
    return {
        "findings": findings,
        "trace": list(state.get("trace") or [])
        + [_trace("reconciliation", "Compared customers, orders, and contacts across systems.", started, added)],
        "reconcile_done": True,
    }


def _structured_summary(findings: list[dict]) -> str:
    counts = {level: sum(1 for item in findings if item["severity"] == level) for level in ("high", "medium", "low")}
    if not findings:
        return "The specialists finished and did not report a gap."
    headlines = "; ".join(item["title"] for item in findings[:3])
    return (
        f"{counts['high']} high, {counts['medium']} medium, and {counts['low']} low findings. "
        f"Leading evidence: {headlines}."
    )


def _ollama_narrative(summary: str, findings: list[dict]) -> str | None:
    """Ask a local model to rewrite the summary. Absent config or a failed call returns None."""
    model = os.environ.get("OLLAMA_MODEL", "").strip()
    if not model:
        return None
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    prompt = (
        "You are writing for an enterprise architect. In four sentences, explain the data gaps "
        "below. Use only the titles given. Do not invent systems, counts, or causes.\n\n"
        + "\n".join(f"- {item['severity']}: {item['title']}" for item in findings)
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    text = str(payload.get("response") or "").strip()
    return text or None


def reporter(state: DiscoveryState) -> dict:
    """Rank the evidence and publish the report. Does not query the databases."""
    started = time.perf_counter()
    findings = sorted(
        list(state.get("findings") or []),
        key=lambda item: (SEVERITY_RANK.get(item["severity"], 9), item["title"]),
    )
    summary = _structured_summary(findings)
    narrative = _ollama_narrative(summary, findings)
    report = {
        "title": "Enterprise data gap report",
        "focus": state.get("focus") or "customers",
        "summary": narrative or summary,
        "narrative_source": "ollama" if narrative else "structured",
        "counts": {
            "high": sum(1 for item in findings if item["severity"] == "high"),
            "medium": sum(1 for item in findings if item["severity"] == "medium"),
            "low": sum(1 for item in findings if item["severity"] == "low"),
            "total": len(findings),
        },
    }
    return {
        "findings": findings,
        "report": report,
        "trace": list(state.get("trace") or [])
        + [
            _trace(
                "reporter",
                "Ranked findings. Narrative source: " + report["narrative_source"] + ".",
                started,
                len(findings),
            )
        ],
    }
