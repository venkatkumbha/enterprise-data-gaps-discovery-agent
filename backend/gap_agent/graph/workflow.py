"""Supervisor graph.

The supervisor does no analysis. After each specialist it chooses the next
one from the flags on the state: schema, then profile, then reconciliation,
then the reporter. A blocked run skips straight to the reporter.
"""

from __future__ import annotations

from gap_agent.graph.nodes import profiler, reconciliation, reporter, schema_explorer
from gap_agent.graph.state import DiscoveryState


def route(state: DiscoveryState) -> str:
    """Pick the next node name. The graph maps these strings to nodes."""
    if state.get("blocked") and state.get("schema_done"):
        return "reporter"
    if not state.get("schema_done"):
        return "schema_explorer"
    if not state.get("profile_done"):
        return "profiler"
    if not state.get("reconcile_done"):
        return "reconciliation"
    return "reporter"


def supervisor(state: DiscoveryState) -> dict:
    """Passthrough. The conditional edge after this node is the decision."""
    return {}


def build_graph():
    """Compile the graph. LangGraph is imported here so route tests stay light."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(DiscoveryState)
    graph.add_node("supervisor", supervisor)
    graph.add_node("schema_explorer", schema_explorer)
    graph.add_node("profiler", profiler)
    graph.add_node("reconciliation", reconciliation)
    graph.add_node("reporter", reporter)
    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route,
        {
            "schema_explorer": "schema_explorer",
            "profiler": "profiler",
            "reconciliation": "reconciliation",
            "reporter": "reporter",
        },
    )
    # Specialists return to the supervisor instead of calling each other.
    graph.add_edge("schema_explorer", "supervisor")
    graph.add_edge("profiler", "supervisor")
    graph.add_edge("reconciliation", "supervisor")
    graph.add_edge("reporter", END)
    return graph.compile()


def run_discovery(focus: str = "bss_oss_party_and_service") -> dict:
    """Execute one full pass and return the report, findings, trace, and inventory."""
    result = build_graph().invoke(
        {
            "focus": focus,
            "findings": [],
            "trace": [],
            "systems": [],
            "schema_done": False,
            "profile_done": False,
            "reconcile_done": False,
            "blocked": False,
        }
    )
    return {
        "report": result.get("report") or {},
        "findings": result.get("findings") or [],
        "trace": result.get("trace") or [],
        "systems": result.get("systems") or [],
    }
