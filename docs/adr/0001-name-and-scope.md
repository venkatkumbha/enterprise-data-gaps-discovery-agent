# ADR 0001 — Name the project for data-gap discovery

## Status

Accepted

## Context

The original home-lab idea was a private agentic RAG platform: citations, multi-agent orchestration, evaluation, and governance. That scope is a full product. The enterprise problem this work is meant to show is narrower and more common: data is not ready for agents, and nobody can point at the gaps with evidence.

Architect interviews reward a bounded system with decision records more than a wide demo that never finishes.

## Decision

The project is **Enterprise Data Gaps Discovery Agent**.

Phase 0 is three synthetic systems, a read-only MCP tool layer, an audit log, and a written ground truth. Specialist agents and an evaluation runner come next. Retrieval over documents is out of scope until a gap report can be scored.

## Consequences

- The repo, the workspace file, and the Python package (`gap_agent`) use this name and this job.
- A future RAG or knowledge-assistant feature needs its own ADR. It does not get folded in by default.
- Portfolio language stays specific: identity, completeness, semantic drift, freshness, referential integrity, and shadow tables across simulated systems of record.

## Alternatives considered

A general “enterprise AI knowledge OS” would have matched a longer roadmap and would have delayed the first measurable result. Building against a live company database was rejected in ADR 0002.
