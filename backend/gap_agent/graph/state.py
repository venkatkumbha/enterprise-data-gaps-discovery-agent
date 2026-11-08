"""Shared state for one discovery run.

LangGraph passes this dict from node to node. Each specialist returns a
partial update. Flags tell the supervisor which specialist has already run.
"""

from __future__ import annotations

from typing import TypedDict


class DiscoveryState(TypedDict, total=False):
    focus: str
    systems: list[dict]
    findings: list[dict]
    trace: list[dict]
    report: dict
    schema_done: bool
    profile_done: bool
    reconcile_done: bool
    blocked: bool
