# Golden questions

Ask these of the agent once it can call the MCP tools. A good answer names the BSS/OSS systems, cites rows or counts, and does not invent a gap that is not in [known_gaps.md](../data/ground_truth/known_gaps.md).

1. Which product orders have no matching CRM customer, and what are their ids?
2. Which order references a product offering that is not in the catalog?
3. Which CRM contacts point at a customer that does not exist?
4. Which CRM customers have no billing account?
5. How does customer 101’s name differ across CRM, Billing, Service Inventory, and Analytics?
6. Which email address is shared by more than one CRM customer?
7. Which customer-facing services have no CRM party?
8. Which resources point at a service that does not exist?
9. Which trouble tickets reference a missing service?
10. How stale is Analytics relative to CRM?
11. Which billing tables are missing from the official catalog?
12. What lifecycle status values appear in CRM, Billing, Service Inventory, and Analytics?

Pass condition for a later automated runner: each question’s expected ids or table names appear in the answer, and the answer includes the tool or SQL that produced them.
