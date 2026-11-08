# Enterprise Data Gaps Discovery Agent

AI pilots in Telco stall when BSS and OSS disagree. This project is a small, runnable lab for that problem.

A React console asks a Python API to run one LangGraph workflow. Four specialists look across a synthetic BSS/OSS estate: Customer Management, Product Catalog, Order Management, Billing, Service Inventory, Resource Inventory, Assurance, and a stale Analytics extract. Every finding is backed by the query and the rows. The agents never receive a database login.

There is no operator production data here. The gaps are planted, and the answer key is in [data/ground_truth/known_gaps.md](data/ground_truth/known_gaps.md).

## Domains in the lab

| Layer | Systems |
| --- | --- |
| BSS | `crm`, `product_catalog`, `order_management`, `billing` |
| OSS | `service_inventory`, `resource_inventory`, `assurance` |
| BI | `analytics` |

## What a run is meant to show

| Gap | Example in this lab |
| --- | --- |
| Identity | Customer 101 is Acme Corp, Acme Corporation, and ACME CORP across CRM, Billing, and Service Inventory. Two parties share one email. |
| Broken commercial links | Product orders 9001 and 9002 point at customer 999. Order 5013 sells `OFF-GHOST`, which is not in the catalog. |
| Broken operational links | `SVC-ORPHAN` has no CRM party. `RES-GHOST` and ticket `TT-9000` point at missing services. |
| Completeness | Five billing accounts have no bill email. Nimbus Cloud has CRM but no billing account. |
| Meaning | Lifecycle is `Active` / `A` / `IN_SERVICE` / `1` depending on the domain. |
| Freshness | Analytics is 42 days behind CRM. |
| Shadow data | `legacy_ar_dump` exists in Billing and is missing from the official catalog. |

## Architecture

```text
React UI  ->  FastAPI  ->  LangGraph supervisor
                              |-> schema explorer
                              |-> profiler
                              |-> reconciliation
                              |-> reporter
                           read-only tools  ->  BSS / OSS / BI SQLite systems
                                             ->  audit log
```

The supervisor only chooses the next specialist. Specialists return to the supervisor. The reporter ranks evidence and does not query again.

Access rules:

- SQLite opens read-only.
- A free-form query must be one `SELECT`.
- Writes, attached databases, and chained statements are rejected.
- Results stop at 200 rows.
- Each tool call is appended to `logs/mcp_audit.jsonl`.

The same tools back an MCP server. Decision records are in [docs/adr](docs/adr), including [ADR 0005](docs/adr/0005-telco-bss-oss-viewpoint.md) for the Telco viewpoint.

## Run it

Python 3.11+ and Node.js. From this folder:

```powershell
.\scripts\bootstrap.ps1
.\scripts\run-backend.ps1
.\scripts\run-ui.ps1
```

Open `http://127.0.0.1:5173` and choose **Run discovery**.

## LinkedIn

The short post is [docs/linkedin.md](docs/linkedin.md). Cover image: [docs/assets/linkedin-article-cover.jpg](docs/assets/linkedin-article-cover.jpg).

Public repository:

https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

## What this does not claim

This is a home lab with a few dozen rows. It is not a scan of a real Telco estate. The claim is the design: name the BSS/OSS defects, force evidence, and keep the agent inside a read-only tool boundary.
