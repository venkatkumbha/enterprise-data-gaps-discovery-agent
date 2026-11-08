# Official BSS/OSS data catalog

This is the catalog a Telco data steward would hand an integration team. It is incomplete on purpose. The discovery agent should notice what is missing.

| Layer | System | Table | Grain | Notes in the catalog |
| --- | --- | --- | --- | --- |
| BSS | crm | customers | one row per enterprise party | `customer_id` is the commercial party key. `status` is Active or Inactive. |
| BSS | crm | contacts | one row per person | `customer_id` should reference `customers`. |
| BSS | product_catalog | product_offering | one row per sellable offer | `offer_id` is used by Order Management and Service Inventory. |
| BSS | order_management | product_order | one row per product order | `customer_id` and `offer_id` should resolve to CRM and the catalog. |
| BSS | billing | billing_account | one row per billing account | `customer_id` should match CRM. |
| BSS | billing | charge | one row per rated charge | Points at a billing account and an offer. |
| OSS | service_inventory | customer_facing_service | one CFS instance | Should trace to a party and usually to an order. |
| OSS | resource_inventory | resource | one network resource | `service_id` should reference Service Inventory when allocated. |
| OSS | assurance | trouble_ticket | one ticket | `service_id` should reference Service Inventory. |
| BI | analytics | dim_customer | nightly party extract | `source_crm_id` / `source_billing_id` point back at BSS. |
| BI | analytics | fact_service | nightly service extract | Used by reporting, not by fulfilment. |

The catalog does not mention column-name differences, lifecycle encodings, or load lag. Those are left for profiling to discover.

Last reviewed in this fiction: 2026-08-01. Analytics is as of 2026-09-20. Operational BSS/OSS systems were touched in November 2026.
