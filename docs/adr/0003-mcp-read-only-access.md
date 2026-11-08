# ADR 0003 — Give agents MCP tools, not connections

## Status

Accepted

## Context

A data-gap agent has to read schemas and rows. Giving it a connection string, or an `execute_sql` that can write, is the failure mode enterprises are trying to avoid: an agent with more privilege than the question requires, and no record of what it ran.

Model Context Protocol is the integration style this project is practicing. The model sees tools with names, arguments, and descriptions. The process that serves those tools holds the file path.

## Decision

`gap_agent.mcp.database_server` exposes six tools: `list_systems`, `tables`, `describe`, `profile`, `sample`, and `query`.

Controls, all of them on by default:

- SQLite URI `mode=ro` and `PRAGMA query_only`
- `query` accepts one `SELECT` or `WITH ... SELECT`
- write keywords, `ATTACH`, `PRAGMA`, and any semicolon are rejected in process, before SQLite
- identifiers used by `describe`, `profile`, and `sample` must be bare names that exist in that database
- at most 200 rows leave a tool
- every call appends a JSON line to `logs/mcp_audit.jsonl` with the tool name, arguments, duration, row count, and error if any

Result payloads are not copied into the audit log.

## Consequences

- Cross-system comparison is the agent’s job. There is no tool that opens two databases in one statement, which would have required `ATTACH`.
- Free-form `query` is a conscious compromise. Typed tools are safer, and a later ADR can remove `query` if the specialists can work without it. Until then the guard and the read-only connection are mandatory.
- Audit logs can contain SQL text and column values that were passed as arguments. They stay local and are gitignored.

## Alternatives considered

Direct sqlite3 inside the agent is shorter and leaves no boundary to draw. A single `execute_sql` with a prompt that says “please only read” is not a control. A warehouse-only agent would miss the cross-system gaps this project exists to show.
