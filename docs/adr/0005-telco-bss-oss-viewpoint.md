# ADR 0005 — Frame the lab as a Telco BSS/OSS estate

## Status

Accepted

## Context

The first synthetic estate used CRM, ERP, and a warehouse. That showed cross-system disagreement, but it did not match the domain language of a Telco architect interview or of BSS/OSS integration work. Enterprise AI in a communications provider fails across Customer Management, Product Catalog, Order Management, Billing, Service Inventory, Resource Inventory, Assurance, and reporting extracts — not across a generic ERP alone.

## Decision

The home lab’s systems of record are a reduced Telco BSS/OSS stack:

- BSS: `crm`, `product_catalog`, `order_management`, `billing`
- OSS: `service_inventory`, `resource_inventory`, `assurance`
- BI: `analytics` (stale nightly extract)

Gaps stay planted and scored: party identity, missing billing accounts, orders without parties or offers, CFS without parties, resources and tickets without services, lifecycle-code drift, and undocumented tables.

Public wording (README, LinkedIn) describes the lab as a Telco BSS/OSS data-gap discovery home lab. It still must not claim access to a real operator’s production systems.

## Consequences

- The generator replaces older `erp` / `warehouse` files on every run.
- Specialists reconcile across commercial and operational domains, not only customer tables.
- Future ADRs can deepen one domain (for example TMF Open APIs or charging events) without renaming the project.

## Alternatives considered

Keeping CRM/ERP/warehouse would have been simpler and less relevant to Telco architect roles. Modelling every TMF Open API as its own database would have exploded the lab before the first evaluation harness existed. Eight systems is enough to show BSS-to-OSS breakages without drowning the UI.
