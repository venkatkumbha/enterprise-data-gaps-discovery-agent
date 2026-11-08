# ADR 0004 — Python API, React UI, LangGraph supervisor

## Status

Accepted

## Context

The lab needed a shape a hiring manager can recognize: a backend, a UI, and an agent workflow with an explicit control flow. A single script that calls SQLite and prints JSON would find the same gaps and would not show orchestration, a tool boundary, or an operator experience.

The specialists do not need a model to detect the planted gaps. They need a fixed order, shared state, and evidence. A model is useful later for the narrative, and it should be optional so the lab still runs offline.

## Decision

- The backend is Python. FastAPI in `backend/gap_agent/api` exposes `/api/health`, `/api/systems`, and `/api/discover`.
- The UI is React (JavaScript) in `ui/`, built with Vite. It calls the API and renders the trace, the counts, and the evidence tables.
- Orchestration is a LangGraph `StateGraph`. A supervisor node routes, in order, to the schema explorer, the profiler, the reconciliation agent, and the reporter. Specialists do not call each other.
- Specialists call `run_tool`, the same audited read-only functions the MCP server exposes. They do not open ad-hoc connections.
- The reporter writes a structured summary. If `OLLAMA_MODEL` is set and a local Ollama server answers, that text replaces the summary. A failed or absent model does not fail the run.

## Consequences

- Two processes: Uvicorn on port 8000 and Vite on port 5173. Vite proxies `/api`.
- LangGraph is a required dependency. The route function itself stays pure and is unit-tested without compiling the graph.
- Adding another specialist means a node, a flag, and a branch in `route`. It does not mean a new HTTP endpoint.
- The ground-truth file is still not a tool. Scoring a run against `metrics.json` remains a later evaluation harness.

## Alternatives considered

One LangChain agent with a free-form SQL tool would be shorter and harder to explain when it loops or writes. Putting the React app in the same process as the agents would hide the API boundary. Requiring a cloud model for every run would make the home lab depend on a key and a bill before the control flow was visible.
