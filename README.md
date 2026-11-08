# Enterprise Data Gaps Discovery Agent

AI pilots stall when enterprise data disagrees with itself. This project is a small, runnable lab for that problem.

A React console asks a Python API to run one LangGraph workflow. Four specialists look across a synthetic CRM, an ERP, and a warehouse. Every finding is backed by the query and the rows. The agents never receive a database login.

There is no company data here. The gaps are planted, and the answer key is in [data/ground_truth/known_gaps.md](data/ground_truth/known_gaps.md).

## What a run is meant to show

| Gap | Example in this lab |
| --- | --- |
| Identity | Customer 101 is Acme Corp, Acme Corporation, and ACME CORP. Two customers share one email. |
| Broken references | Two ERP orders point at customer 999. One CRM contact points at customer 404. |
| Completeness | Five ERP customers have no email. CRM still has those addresses. |
| Meaning | Status is `Active` / `Inactive`, `A` / `I`, and `1` / `0`. The customer key has three column names. |
| Freshness | The warehouse extract is 42 days behind CRM. |
| Coverage | Two CRM customers are missing from the warehouse. One warehouse customer has no source id. |
| Shadow data | `legacy_cust_dump` exists in ERP and is missing from the official catalog. |

## Architecture

```text
React UI  ->  FastAPI  ->  LangGraph supervisor
                              |-> schema explorer
                              |-> profiler
                              |-> reconciliation
                              |-> reporter
                           read-only tools  ->  crm / erp / warehouse
                                             ->  audit log
```

The supervisor only chooses the next specialist. Specialists return to the supervisor. The reporter ranks evidence and does not query again.

Access rules:

- SQLite opens read-only.
- A free-form query must be one `SELECT`.
- Writes, attached databases, and chained statements are rejected.
- Results stop at 200 rows.
- Each tool call is appended to `logs/mcp_audit.jsonl`.

The same tools back an MCP server, so an external client gets the same contract as the workflow. Decision records are in [docs/adr](docs/adr).

## Run it

Python 3.11+ and Node.js. From this folder:

```powershell
.\scripts\bootstrap.ps1
.\scripts\run-backend.ps1
.\scripts\run-ui.ps1
```

Open `http://127.0.0.1:5173` and choose **Run discovery**.

On macOS or Linux, use `python -m venv .venv`, install with `pip install -e ".[dev]"`, generate data with `python -m gap_agent.synthetic.generate`, then start Uvicorn on port 8000 and `npm run dev` inside `ui/`.

## LinkedIn

The short post for this project is [docs/linkedin.md](docs/linkedin.md). Add a repository link there only after this folder is public.

## What this does not claim

This is a home lab with a few dozen rows. It is not a scan of a production estate. The claim is the design: name the data defects, force evidence, and keep the agent inside a read-only tool boundary.
