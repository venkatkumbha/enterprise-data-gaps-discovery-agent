# Agent notes

This repository is **Enterprise Data Gaps Discovery Agent**, a home lab. Public wording lives in `README.md` and `docs/linkedin.md`. Do not describe the lab as a scan of a real enterprise.

The instructions that created it are in `docs/build-instructions.md`. Follow that brief. ADR 0001 is the accepted narrowing of it.

The running shape is a Python FastAPI backend, a LangGraph supervisor in `backend/gap_agent/graph`, and a React UI in `ui/`. The synthetic estate is a Telco BSS/OSS stack (ADR 0005). Phase 0 is done when `generate.py` rebuilds those systems, the SQL-guard and route tests pass, and `POST /api/discover` returns evidence-backed findings.

Do not give discovery agents the ground-truth file while they are searching. Do not add write tools. Do not point the MCP server at any database outside `data/systems`.

When behavior changes, update `docs/adr`, `data/ground_truth/known_gaps.md`, and this file’s phase note so they match the code.
