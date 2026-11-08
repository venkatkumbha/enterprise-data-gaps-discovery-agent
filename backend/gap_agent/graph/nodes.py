"""Specialist steps used by the LangGraph supervisor.

Each function reads the synthetic Telco BSS/OSS systems through the same
guarded tools as the MCP server, appends evidence-backed findings, and marks
itself done so the supervisor cannot call it twice.
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
CATALOG = {
    "crm": {"customers", "contacts"},
    "product_catalog": {"product_offering"},
    "order_management": {"product_order"},
    "billing": {"billing_account", "charge"},
    "service_inventory": {"customer_facing_service"},
    "resource_inventory": {"resource"},
    "assurance": {"trouble_ticket"},
    "analytics": {"dim_customer", "fact_service"},
}

DOMAIN_LAYER = {
    "crm": "BSS",
    "product_catalog": "BSS",
    "order_management": "BSS",
    "billing": "BSS",
    "service_inventory": "OSS",
    "resource_inventory": "OSS",
    "assurance": "OSS",
    "analytics": "BI",
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
    """List BSS/OSS systems and compare tables with the official catalog."""
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
                "No BSS/OSS systems are loaded",
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
    shadow = []
    key_rows = []
    expected_keys = {
        "crm": ("customers", "customer_id"),
        "billing": ("billing_account", "customer_id"),
        "order_management": ("product_order", "customer_id"),
        "service_inventory": ("customer_facing_service", "customer_id"),
        "analytics": ("dim_customer", "customer_key"),
    }

    for name in names:
        tables, table_error = _tool("tables", {"system": name}, lambda name=name: list_tables(name))
        tables = tables or []
        inventory.append(
            {
                "name": name,
                "layer": DOMAIN_LAYER.get(name, "unknown"),
                "tables": tables,
                "error": table_error,
            }
        )
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
                columns = [col["name"] for col in (described or [])]
                key_rows.append(
                    {
                        "system": name,
                        "layer": DOMAIN_LAYER.get(name, "unknown"),
                        "table": table,
                        "party_key": column if column in columns else columns[:1],
                    }
                )

    layers = sorted({item["layer"] for item in inventory if item["layer"] != "unknown"})
    if shadow:
        findings.append(
            _finding(
                "shadow-tables",
                "schema_explorer",
                "shadow_data",
                "medium",
                "Tables exist that the official BSS/OSS catalog does not list",
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

    if len(key_rows) >= 3:
        findings.append(
            _finding(
                "party-key-spread",
                "schema_explorer",
                "semantic_drift",
                "medium",
                "The same party concept is keyed differently across BSS, OSS, and BI",
                "Customer / billing / service / analytics tables expose overlapping party identifiers with different table and column names. Cross-domain joins have to be designed, not assumed.",
                [
                    {
                        "system": row["system"],
                        "tool": "describe",
                        "detail": row["table"],
                        "rows": [row],
                    }
                    for row in key_rows
                ],
            )
        )

    added = len(findings) - len(state.get("findings") or [])
    return {
        "systems": inventory,
        "findings": findings,
        "trace": list(state.get("trace") or [])
        + [
            _trace(
                "schema_explorer",
                f"Catalogued {len(inventory)} systems across {', '.join(layers) or 'unknown'} layers.",
                started,
                added,
            )
        ],
        "schema_done": True,
    }


def profiler(state: DiscoveryState) -> dict:
    """Profile bill email completeness, status encodings, and analytics freshness."""
    started = time.perf_counter()
    if state.get("blocked"):
        return {"profile_done": True}
    findings = list(state.get("findings") or [])
    before = len(findings)

    email_profile, _ = _tool(
        "profile",
        {"system": "billing", "table": "billing_account", "column": "bill_email"},
        lambda: profile_column("billing", "billing_account", "bill_email"),
    )
    if email_profile and email_profile["null_or_blank"] > 0:
        missing, _ = _tool(
            "query",
            {
                "system": "billing",
                "sql": "SELECT billing_account_id, customer_id, account_name FROM billing_account WHERE bill_email IS NULL",
            },
            lambda: safe_query(
                "billing",
                "SELECT billing_account_id, customer_id, account_name FROM billing_account WHERE bill_email IS NULL",
                50,
            ),
        )
        ratio = round(email_profile["null_or_blank_ratio"] * 100, 1)
        findings.append(
            _finding(
                "billing-null-emails",
                "profiler",
                "completeness",
                "medium",
                f"{email_profile['null_or_blank']} billing accounts have no bill email ({ratio}%)",
                "bill_email is null on accounts CRM still has an address for. Invoice delivery and collection agents will drop these parties.",
                [
                    {
                        "system": "billing",
                        "tool": "profile",
                        "detail": "billing_account.bill_email",
                        "rows": [email_profile],
                    },
                    {
                        "system": "billing",
                        "tool": "query",
                        "detail": "SELECT billing_account_id, customer_id, account_name FROM billing_account WHERE bill_email IS NULL",
                        "rows": missing or [],
                    },
                ],
            )
        )

    status_targets = [
        ("crm", "customers", "status"),
        ("billing", "billing_account", "account_status"),
        ("service_inventory", "customer_facing_service", "service_state"),
        ("analytics", "dim_customer", "status_code"),
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
                "Lifecycle status is encoded differently across BSS, OSS, and BI",
                "Active, A, IN_SERVICE, and 1 all mean 'live' in different domains. A filter written for CRM will misread billing, service inventory, and analytics.",
                status_evidence,
            )
        )

    date_queries = [
        ("crm", "SELECT MIN(updated_at) AS min_date, MAX(updated_at) AS max_date FROM customers"),
        ("billing", "SELECT MIN(last_modified) AS min_date, MAX(last_modified) AS max_date FROM billing_account"),
        ("analytics", "SELECT MIN(as_of_date) AS min_date, MAX(as_of_date) AS max_date FROM dim_customer"),
    ]
    date_rows = []
    for system, sql in date_queries:
        rows, _ = _tool("query", {"system": system, "sql": sql}, lambda system=system, sql=sql: safe_query(system, sql, 5))
        if rows:
            date_rows.append({"system": system, "tool": "query", "detail": sql, "rows": rows})
    stamps = {item["system"]: item["rows"][0].get("max_date") for item in date_rows}
    if stamps.get("analytics") and stamps.get("crm") and stamps["analytics"] < stamps["crm"]:
        analytics_day = date.fromisoformat(stamps["analytics"])
        crm_day = date.fromisoformat(stamps["crm"])
        lag_days = (crm_day - analytics_day).days
        findings.append(
            _finding(
                "analytics-stale",
                "profiler",
                "freshness",
                "medium",
                f"The analytics extract is {lag_days} days behind CRM",
                f"Analytics as-of date is {stamps['analytics']}. CRM was updated {stamps['crm']}. Assurance and commercial agents that read BI are not seeing the current BSS record.",
                date_rows,
            )
        )

    added = len(findings) - before
    return {
        "findings": findings,
        "trace": list(state.get("trace") or [])
        + [_trace("profiler", "Profiled billing completeness, lifecycle codes, and BI freshness.", started, added)],
        "profile_done": True,
    }


def reconciliation(state: DiscoveryState) -> dict:
    """Compare party, order, catalog, service, resource, and ticket links across BSS/OSS."""
    started = time.perf_counter()
    if state.get("blocked"):
        return {"reconcile_done": True}
    findings = list(state.get("findings") or [])
    before = len(findings)

    crm_sql = "SELECT customer_id, legal_name, email, status FROM customers"
    billing_sql = "SELECT billing_account_id, customer_id, account_name, bill_email, account_status FROM billing_account"
    order_sql = "SELECT order_id, customer_id, offer_id, order_state FROM product_order"
    offer_sql = "SELECT offer_id, offer_name FROM product_offering"
    service_sql = (
        "SELECT service_id, customer_id, order_id, offer_id, party_name, service_state "
        "FROM customer_facing_service"
    )
    resource_sql = "SELECT resource_id, service_id, resource_type, operational_state FROM resource"
    ticket_sql = "SELECT ticket_id, service_id, customer_id, ticket_state, summary FROM trouble_ticket"
    analytics_sql = (
        "SELECT customer_key, source_crm_id, source_billing_id, display_name, email, status_code "
        "FROM dim_customer"
    )

    crm_rows, _ = _tool("query", {"system": "crm", "sql": crm_sql}, lambda: safe_query("crm", crm_sql, 200))
    billing_rows, _ = _tool(
        "query", {"system": "billing", "sql": billing_sql}, lambda: safe_query("billing", billing_sql, 200)
    )
    order_rows, _ = _tool(
        "query",
        {"system": "order_management", "sql": order_sql},
        lambda: safe_query("order_management", order_sql, 200),
    )
    offer_rows, _ = _tool(
        "query",
        {"system": "product_catalog", "sql": offer_sql},
        lambda: safe_query("product_catalog", offer_sql, 200),
    )
    service_rows, _ = _tool(
        "query",
        {"system": "service_inventory", "sql": service_sql},
        lambda: safe_query("service_inventory", service_sql, 200),
    )
    resource_rows, _ = _tool(
        "query",
        {"system": "resource_inventory", "sql": resource_sql},
        lambda: safe_query("resource_inventory", resource_sql, 200),
    )
    ticket_rows, _ = _tool(
        "query", {"system": "assurance", "sql": ticket_sql}, lambda: safe_query("assurance", ticket_sql, 200)
    )
    analytics_rows, _ = _tool(
        "query", {"system": "analytics", "sql": analytics_sql}, lambda: safe_query("analytics", analytics_sql, 200)
    )

    crm_rows = crm_rows or []
    billing_rows = billing_rows or []
    order_rows = order_rows or []
    offer_rows = offer_rows or []
    service_rows = service_rows or []
    resource_rows = resource_rows or []
    ticket_rows = ticket_rows or []
    analytics_rows = analytics_rows or []

    crm_ids = {row["customer_id"] for row in crm_rows}
    offer_ids = {row["offer_id"] for row in offer_rows}
    service_ids = {row["service_id"] for row in service_rows}
    billing_by_customer = {row["customer_id"]: row for row in billing_rows}

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
                "BSS Customer Management contacts point at a party that does not exist.",
                [{"system": "crm", "tool": "query", "detail": contact_sql, "rows": bad_contacts}],
            )
        )

    orphan_orders = [row for row in order_rows if row["customer_id"] not in crm_ids]
    if orphan_orders:
        findings.append(
            _finding(
                "orphan-orders",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(orphan_orders)} product orders point at a customer that does not exist",
                "Order Management references customer_id values missing from CRM. Fulfilment and billing cannot attach these orders to a party.",
                [{"system": "order_management", "tool": "query", "detail": order_sql, "rows": orphan_orders}],
            )
        )

    ghost_offers = [row for row in order_rows if row["offer_id"] not in offer_ids]
    if ghost_offers:
        findings.append(
            _finding(
                "unknown-offers",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(ghost_offers)} orders reference a product offering missing from the catalog",
                "Product Ordering accepted an offer_id that Product Catalog does not sell. Activation and rating have no commercial definition.",
                [
                    {
                        "system": "order_management",
                        "tool": "query",
                        "detail": "orders whose offer_id is absent from product_offering",
                        "rows": ghost_offers,
                    }
                ],
            )
        )

    missing_billing = [row for row in crm_rows if row["customer_id"] not in billing_by_customer]
    if missing_billing:
        findings.append(
            _finding(
                "crm-without-billing",
                "reconciliation",
                "coverage",
                "high",
                f"{len(missing_billing)} CRM customers have no billing account",
                "BSS Customer Management has a live party that Billing Account Management never created. Revenue assurance will miss them.",
                [{"system": "crm", "tool": "query", "detail": crm_sql, "rows": missing_billing}],
            )
        )

    orphan_services = [row for row in service_rows if row["customer_id"] not in crm_ids]
    if orphan_services:
        findings.append(
            _finding(
                "orphan-services",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(orphan_services)} customer-facing services have no CRM party",
                "Service Inventory holds a CFS instance for a customer_id that Customer Management does not know.",
                [
                    {
                        "system": "service_inventory",
                        "tool": "query",
                        "detail": service_sql,
                        "rows": orphan_services,
                    }
                ],
            )
        )

    ghost_resources = [
        row for row in resource_rows if row.get("service_id") and row["service_id"] not in service_ids
    ]
    if ghost_resources:
        findings.append(
            _finding(
                "orphan-resources",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(ghost_resources)} resources point at a service that does not exist",
                "Resource Inventory allocates network resources to a service_id missing from Service Inventory. Assurance and capacity planning will treat capacity as used when no CFS exists.",
                [
                    {
                        "system": "resource_inventory",
                        "tool": "query",
                        "detail": resource_sql,
                        "rows": ghost_resources,
                    }
                ],
            )
        )

    ghost_tickets = [row for row in ticket_rows if row.get("service_id") not in service_ids]
    if ghost_tickets:
        findings.append(
            _finding(
                "orphan-tickets",
                "reconciliation",
                "referential_integrity",
                "high",
                f"{len(ghost_tickets)} trouble tickets reference a missing service",
                "Assurance opened tickets against a service_id that Service Inventory does not hold. NOC workflows cannot correlate fault to inventory.",
                [{"system": "assurance", "tool": "query", "detail": ticket_sql, "rows": ghost_tickets}],
            )
        )

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
                "Matching on email alone would collapse distinct enterprise parties into a single identity across BSS.",
                [{"system": "crm", "tool": "query", "detail": crm_sql, "rows": flat}],
            )
        )

    variant_rows = []
    analytics_by_crm = {
        row["source_crm_id"]: row for row in analytics_rows if row.get("source_crm_id") is not None
    }
    service_names = {}
    for row in service_rows:
        if row.get("customer_id") in crm_ids and row.get("party_name"):
            service_names.setdefault(row["customer_id"], set()).add(row["party_name"])
    for row in crm_rows:
        names = {row["legal_name"]}
        billing_row = billing_by_customer.get(row["customer_id"])
        analytics_row = analytics_by_crm.get(row["customer_id"])
        if billing_row:
            names.add(billing_row["account_name"])
        if analytics_row:
            names.add(analytics_row["display_name"])
        names.update(service_names.get(row["customer_id"], set()))
        if len(names) > 1:
            variant_rows.append(
                {
                    "customer_id": row["customer_id"],
                    "crm": row["legal_name"],
                    "billing": billing_row["account_name"] if billing_row else None,
                    "service_inventory": sorted(service_names.get(row["customer_id"], [])) or None,
                    "analytics": analytics_row["display_name"] if analytics_row else None,
                }
            )
    if variant_rows:
        findings.append(
            _finding(
                "name-variants",
                "reconciliation",
                "identity",
                "high",
                f"{len(variant_rows)} parties have different names across BSS/OSS systems",
                "The party id matches, but CRM, Billing, Service Inventory, and Analytics disagree on the legal or display name.",
                [
                    {
                        "system": "crm",
                        "tool": "query",
                        "detail": "cross-domain party name comparison",
                        "rows": variant_rows,
                    }
                ],
            )
        )

    missing_analytics = [row for row in crm_rows if row["customer_id"] not in analytics_by_crm]
    if missing_analytics:
        findings.append(
            _finding(
                "missing-from-analytics",
                "reconciliation",
                "coverage",
                "medium",
                f"{len(missing_analytics)} CRM customers are missing from analytics",
                "Operational BSS parties have no dim_customer row, so BI and any agent on the warehouse cannot see them.",
                [{"system": "crm", "tool": "query", "detail": crm_sql, "rows": missing_analytics}],
            )
        )

    analytics_only = [
        row
        for row in analytics_rows
        if row.get("source_crm_id") is None and row.get("source_billing_id") is None
    ]
    if analytics_only:
        findings.append(
            _finding(
                "analytics-only",
                "reconciliation",
                "coverage",
                "medium",
                f"{len(analytics_only)} analytics customers have no BSS source id",
                "The BI extract contains a party that cannot be traced back to CRM or Billing.",
                [{"system": "analytics", "tool": "query", "detail": analytics_sql, "rows": analytics_only}],
            )
        )

    added = len(findings) - before
    return {
        "findings": findings,
        "trace": list(state.get("trace") or [])
        + [
            _trace(
                "reconciliation",
                "Compared party, order, catalog, service, resource, and ticket links across BSS/OSS.",
                started,
                added,
            )
        ],
        "reconcile_done": True,
    }


def _structured_summary(findings: list[dict]) -> str:
    counts = {level: sum(1 for item in findings if item["severity"] == level) for level in ("high", "medium", "low")}
    if not findings:
        return "The specialists finished and did not report a gap."
    headlines = "; ".join(item["title"] for item in findings[:3])
    return (
        f"{counts['high']} high, {counts['medium']} medium, and {counts['low']} low findings across the Telco BSS/OSS lab. "
        f"Leading evidence: {headlines}."
    )


def _ollama_narrative(summary: str, findings: list[dict]) -> str | None:
    """Ask a local model to rewrite the summary. Absent config or a failed call returns None."""
    model = os.environ.get("OLLAMA_MODEL", "").strip()
    if not model:
        return None
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    prompt = (
        "You are writing for a Telco BSS/OSS enterprise architect. In four sentences, explain the "
        "data gaps below. Use only the titles given. Do not invent systems, counts, or causes.\n\n"
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
        "title": "Telco BSS/OSS data gap report",
        "focus": state.get("focus") or "bss_oss_party_and_service",
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
