# Known gaps

Answer key for the Telco BSS/OSS lab. Agents under test should not be given this file. Evaluation reads it.

Numbers are also recomputed into `metrics.json` when `python -m gap_agent.synthetic.generate` runs. If this page and that file disagree, trust the file and fix this page.

## Domains in the lab

| Layer | Systems |
| --- | --- |
| BSS | crm, product_catalog, order_management, billing |
| OSS | service_inventory, resource_inventory, assurance |
| BI | analytics |

## Identity

- Customer 101 is `Acme Corp` in CRM, `Acme Corporation` in Billing, and `ACME CORP` in Service Inventory / Analytics.
- CRM customers 106 (Northwind Trading) and 110 (Northwind Ltd) both use `ap@northwind.example`.

## Referential integrity

- Order Management orders 9001 and 9002 use `customer_id` 999. That party is not in CRM.
- Order 5013 uses `offer_id` `OFF-GHOST`, which is not in Product Catalog.
- CRM contact 7 uses `customer_id` 404. That customer does not exist.
- Service Inventory holds `SVC-ORPHAN` for customer 888, which is not in CRM.
- Resource Inventory `RES-GHOST` points at `SVC-DOES-NOT-EXIST`.
- Assurance ticket `TT-9000` points at `SVC-MISSING`.

## Completeness and coverage

- Billing `bill_email` is null for customer ids 102, 107, 112, 115, and 119. CRM still has those emails.
- CRM customer 118 (Nimbus Cloud) has no billing account.
- CRM customers 103 and 118 are absent from Analytics.
- Analytics customer 105 (Helios Medical) has null source CRM and billing ids.

## Semantic drift

- CRM `status`: `Active`, `Inactive`.
- Billing `account_status`: `A`, `I`.
- Service Inventory `service_state`: `IN_SERVICE`, `DESIGNED`.
- Analytics `status_code`: `1`, `0`.

## Freshness

- CRM `updated_at` is 2026-11-01. Billing `last_modified` is 2026-11-02. Analytics `as_of_date` is 2026-09-20.

## Shadow data

- Billing table `legacy_ar_dump` is not in `data/catalog/official_catalog.md`. It includes legacy id 8800 (Shadow Carrier), which is in no other party table.
