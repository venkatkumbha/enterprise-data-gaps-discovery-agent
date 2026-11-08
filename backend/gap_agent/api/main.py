"""HTTP API the React UI calls.

The API does not open SQLite itself. Discovery goes through the LangGraph
workflow, and that workflow uses the read-only tool functions.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gap_agent.graph.workflow import run_discovery
from gap_agent.mcp.database_server import list_system_names, list_tables

app = FastAPI(
    title="Enterprise Data Gaps Discovery Agent",
    version="0.1.0",
    summary="LangGraph specialists that report evidence-backed data gaps.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class DiscoverRequest(BaseModel):
    focus: str = Field(default="bss_oss_party_and_service", max_length=80)


@app.get("/api/health")
def health() -> dict:
    """Liveness for the UI and for a local process check."""
    return {"status": "ok", "service": "Enterprise Data Gaps Discovery Agent"}


@app.get("/api/systems")
def systems() -> dict:
    """Inventory the SQLite files without running the agent graph."""
    inventory = []
    for name in list_system_names():
        inventory.append({"name": name, "tables": list_tables(name)})
    return {"systems": inventory}


@app.post("/api/discover")
def discover(body: DiscoverRequest | None = None) -> dict:
    """Run the supervisor graph once and return its report."""
    focus = body.focus if body else "bss_oss_party_and_service"
    return run_discovery(focus=focus)
