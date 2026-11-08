# Build instructions

These are the instructions used to create this repository. They were given on 8 Nov 2026 in a Cursor chat that was still open on the eBonding workspace. This folder did not have its own chat history yet, which is why the sidebar here looked empty.

The accepted narrowing of that brief is [ADR 0001](adr/0001-name-and-scope.md). A future document-retrieval or knowledge-assistant feature needs its own ADR.

## Instructions after the brief

1. Create a new workspace for this home project, separate from the eBonding middleware.
2. Name it **Enterprise Data Gaps Discovery Agent**.
3. Use Python for the backend, React for the UI, and LangGraph for the agent.
4. After the machine upgrade, continue from the last unfinished step.
5. Make the project visible in the Cursor project panel, and refresh this workspace so it is the one on screen.

## Brief

Home project for an enterprise-architect career. It should be home-based, use AI tools, follow enterprise standards, and produce work that is useful in future architect roles.

The starting idea was a private, enterprise-grade agentic RAG and multi-agent knowledge platform: a personal home “Enterprise AI Knowledge OS”. It should be low-cost, use modern AI tools, and mirror enterprise standards: security, governance, observability, auditability, and cost control. It should feel current (agentic workflows and emerging protocols) and produce the artifacts architects are judged on: architecture decisions, diagrams, trade-offs, and operational thinking.

Hiring managers look for privacy, cost control, observability, evaluation, and enterprise concerns, not a demo chatbot. RAG is the common enterprise pattern. Multi-agent systems and the Model Context Protocol (MCP) are the current frontier. The portfolio should emphasize production patterns (evals, tracing, guardrails, citations) over a tutorial clone.

Practice the architect’s job: define scope, choose an orchestration pattern, document decisions, consider failure modes, and apply governance.

### What the system should do

- Ingest documents (architecture notes, policies, PDFs, code, or simulated enterprise docs).
- Answer with citations and provenance.
- Use specialized agents (retriever, validator or compliance checker, synthesizer, planner).
- Enforce home-lab controls that match enterprise practice: audit logging, a basic access simulation, prompt-injection defenses, cost and latency tracking, and evaluation.
- Document it as a proposal inside a company.

### Layers

- Interface: FastAPI, or a simple UI, with streaming.
- Orchestration: LangGraph (stateful, conditional routing, loops). Optional supervisor plus specialists.
- Knowledge: chunking, embeddings, and a vector store, with hybrid search and reranking.
- Tools: MCP servers for governed access (files, search, calculator, or mock enterprise tools).
- Governance and observability: audit logs, traces (Langfuse or OpenTelemetry), an evaluation harness (RAGAS or DeepEval), cost tracking, and basic guardrails.
- Deployment: Docker Compose, with an optional later path to Kubernetes.

### Patterns to include

- Citations and source provenance.
- An evaluation suite with golden questions and metrics (faithfulness, relevancy, hallucination rate).
- Human-in-the-loop or approval gates for higher-risk actions.
- Structured logs of agent decisions and tool calls.
- Explicit trade-offs: local model versus API, single agent versus multi-agent, and which vector database.

### Suggested stack

- LLM: Ollama (Llama 3.1, Qwen, or Phi), with an optional stronger API model.
- Orchestration: LangGraph.
- Vector store: Qdrant, Chroma, or PostgreSQL with pgvector.
- Embeddings: local sentence-transformers, or an API.
- API: FastAPI.
- Tools: MCP (FastMCP or the official SDKs).
- Observability: Langfuse, or structured logs and a simple dashboard.
- Evaluation: RAGAS or DeepEval.
- Infra: Docker Compose.
- Docs: Mermaid or PlantUML, plus Markdown ADRs.

### Phases from the brief

Phase 1, a solid RAG foundation: ingest, chunk, embed, retrieve, and answer with citations. Add a small evaluation set.

Phase 2, make it agentic: move to LangGraph. Add planning, tool use, and at least one specialist (a validator that checks citations or flags low-confidence answers).

Phase 3, enterprise hardening: audit logging, basic guardrails, traces, cost and latency metrics, and MCP. Write 4–6 ADRs (model, vector store, orchestration, security, and related choices).

Phase 4, documentation: C4 context and container diagrams, sequence diagrams, a README written as an architecture brief, an evaluation results table, and a short lessons-learned note.

Portfolio presentation: problem statement, diagrams, ADRs, evaluation results, tech choices with rationale, and how to run it. Talk about governance more than the model. In interviews, talk about failure modes found during evaluation. Ship a working, documented system before adding maximum complexity.

### Enterprise problems this is meant to show

The three problems called out in the brief:

1. Scaling AI from pilots to production and realizing ROI. Architects answer this with a production reference architecture, evaluation, tracing, cost tracking, quality gates, incremental rollout, ADRs, and model routing or caching.
2. Data quality, readiness, and integration with legacy systems. Architects answer this with systems of record, shared definitions, governed pipelines, lineage, access control, and clean integration (APIs, events, MCP) before wide agent deployment.
3. Governance, security, risk, and accountability. Architects answer this with security-by-design, audit logs, tool allow-lists, human gates, prompt-injection defenses, permission models, ownership, observability, and standards such as the NIST AI RMF.

Daily architect artifacts: C4 and sequence diagrams, ADRs, reusable reference architectures, and non-functional requirements treated as design constraints.

### MCP for a database

MCP is how agents call tools and read data without a raw connection string. The home version is a Python MCP server over SQLite.

Required practices:

- Read-only by default (`mode=ro`, or a SELECT-only database user).
- Parameterized queries. Do not concatenate agent input into SQL.
- Row limits and timeouts.
- Prefer specific tools (`list_tables`, `describe_table`, `safe_query`) over a free-form `execute_sql`.
- Audit every query.
- No raw write tools. If a write is ever required, it is a narrow typed tool, and this project does not add one.
- Log every tool call. Document “why MCP instead of a direct database login” in an ADR.
- Keep any future vector store separate from these SQLite systems.

Sketch the brief included with those rules:

```python
def query(sql: str, limit: int = 100) -> list[dict]:
    sql_clean = sql.strip().lower()
    if not sql_clean.startswith("select") and not sql_clean.startswith("with"):
        raise ToolError("Only SELECT / WITH queries are allowed")
    if ";" in sql:
        raise ToolError("Multiple statements are not allowed")
```

### Discovering hidden data gaps

Agents find gaps by exploring schemas, profiling rows, and cross-checking systems. Static rules miss what only shows up when systems are compared.

| Agent | Job | Gaps |
| --- | --- | --- |
| Schema explorer | Read metadata, tables, columns, relationships | Missing keys, unused columns, shadow tables, inconsistent names |
| Profiler | Null rates, distributions, uniqueness, freshness | Nulls in critical fields, unexpected ranges, stale data, duplicates |
| Reconciliation | Compare one entity across CRM, ERP, and the warehouse | Conflicting customers, mismatched ids, incomplete golden records |
| Semantic | Interpret names, descriptions, and samples | One concept stored several ways (`status` versus `state`) |
| Reporter | Correlate findings, rank by impact, attach evidence | Which gaps matter for downstream AI or processes |

Access is through governed read-only tools. Every finding cites the query or the sample rows. A person reviews high-impact findings before any remediation.

Gaps to plant and then find:

- Referential integrity: orders that point at customers who do not exist.
- Semantic drift: “Active”, “A”, and “1” for the same idea.
- Completeness: critical fields often null.
- Identity fragmentation: one real entity, several records, no clear match.
- Freshness and coverage: current in one system, stale in the system agents actually read.
- Shadow data: tables that exist and are missing from the catalog.

### Home design without enterprise data

Build 2–4 small databases that stand in for enterprise systems:

- CRM: customers and contacts.
- ERP: orders and products.
- Warehouse or analytics: a partially cleaned copy.
- Optional later: a document store of policies or notes.

Plant the gaps on purpose:

| Gap | How to create it |
| --- | --- |
| Identity fragmentation | Same customer, slightly different name or email |
| Missing relationships | Orders pointing at customer ids that do not exist |
| Completeness | Critical fields null on a large share of rows |
| Semantic inconsistency | Status encoded differently in each system |
| Stale data | One system’s dates weeks behind the others |
| Orphan records | A row in one system with no counterpart in the others |

About 30–50 rows is enough. Save them as separate SQLite files. Generate them in Python so the gaps are fixed and can be scored later.

Workflow:

1. Schema explorer lists tables and columns across systems.
2. Profiler checks nulls, distinct values, and date ranges.
3. Reconciliation compares customers (and similar entities) across systems.
4. Reporter summarizes findings with sample rows and the queries used.

Example findings the report should be able to state:

- A customer has several name variations across systems.
- Some orders have no matching customer.
- Status has several encodings.
- Each finding lists sample rows and the query behind it.

Interview line from the brief: a multi-agent data-gap discovery system that identifies identity, completeness, and semantic inconsistencies across simulated enterprise systems, using MCP-governed access.

Minimal start the brief asked for:

1. Two or more SQLite files with inconsistent customers and orders.
2. The read-only MCP database server.
3. One agent that lists tables and profiles columns.
4. A second agent that compares customer tables and reports differences.
