# Golden questions

Ask these of the agent once it can call the MCP tools. A good answer names the systems, cites rows or counts, and does not invent a gap that is not in [known_gaps.md](../data/ground_truth/known_gaps.md).

1. Which ERP orders have no matching customer, and what are their ids?
2. Which CRM contacts point at a customer that does not exist?
3. Which email address is shared by more than one CRM customer?
4. How does customer 101’s name differ across CRM, ERP, and the warehouse?
5. What share of ERP customers have a null email, and which ids are they?
6. What values does customer status take in each system?
7. Which CRM customers are missing from the warehouse?
8. Which warehouse customers have no source system id?
9. How stale is the warehouse relative to CRM?
10. Which ERP tables are missing from the official catalog?

Pass condition for a later automated runner: each question’s expected ids or table names appear in the answer, and the answer includes the tool or SQL that produced them. Extra unsupported gaps fail the case.
