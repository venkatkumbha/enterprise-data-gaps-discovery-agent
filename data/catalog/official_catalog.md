# Official data catalog

This is the catalog a steward would hand an integration team. It is incomplete. The discovery agent should notice what is missing, not be limited to this list.

| System | Table | Grain | Notes in the catalog |
| --- | --- | --- | --- |
| crm | customers | one row per customer | `customer_id` is the business key. `status` is Active or Inactive. |
| crm | contacts | one row per person | `customer_id` should reference `customers`. |
| erp | customers | one row per customer | `cust_id` matches CRM `customer_id` when both exist. |
| erp | products | one row per SKU | List price only. |
| erp | orders | one row per order | `cust_id` should reference ERP customers. |
| warehouse | dim_customer | one row per customer in the nightly extract | `source_crm_id` and `source_erp_id` point back at the operational keys. |
| warehouse | fact_order | one row per order in the nightly extract | `customer_key` points at `dim_customer.customer_key`. |

The catalog does not mention column-name differences, status encodings, or load time. Those are left for profiling to discover.

Last reviewed in this fiction: 2026-08-01. The warehouse file is as of 2026-09-20. Operational systems were touched in November 2026.
