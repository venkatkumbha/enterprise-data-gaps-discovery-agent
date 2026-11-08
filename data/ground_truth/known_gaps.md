# Known gaps

Answer key for Enterprise Data Gaps Discovery Agent. Agents under test should not be given this file. Evaluation reads it.

Numbers are also recomputed into `metrics.json` when `python -m gap_agent.synthetic.generate` runs. If this page and that file disagree, trust the file and fix this page.

## Identity

- Customer 101 is `Acme Corp` in CRM, `Acme Corporation` in ERP, and `ACME CORP` in the warehouse.
- CRM customers 106 (Northwind Trading) and 110 (Northwind Ltd) both use `ap@northwind.example`.

## Referential integrity

- ERP orders 9001 and 9002 use `cust_id` 999. That customer is not in ERP, CRM, or the warehouse.
- CRM contact 7 uses `customer_id` 404. That customer does not exist.

## Completeness

- ERP `email_address` is null for customer ids 102, 107, 112, 115, and 119. CRM still has those emails.

## Semantic drift

- CRM `status`: `Active`, `Inactive`.
- ERP `account_status`: `A`, `I`.
- Warehouse `status_code`: `1`, `0`.
- The customer key is `customer_id`, `cust_id`, and `customer_key` depending on the system.

## Freshness and coverage

- CRM `updated_at` is 2026-11-01. ERP `last_modified` is 2026-11-02. Warehouse `as_of_date` is 2026-09-20.
- CRM customers 103 (Gamma LLC) and 118 (Nimbus Cloud) are absent from `dim_customer`.
- Warehouse customer 105 (Helios Medical) has null `source_crm_id` and `source_erp_id`.
- The warehouse `fact_order` table does not contain orders 9001 and 9002.

## Shadow data

- ERP table `legacy_cust_dump` is not in `data/catalog/official_catalog.md`. It has three rows, including legacy id 8800 (Shadow Retail), which is in no other customer table.
