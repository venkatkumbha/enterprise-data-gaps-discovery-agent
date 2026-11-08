# LinkedIn

Paste the article into LinkedIn’s article editor. Paste the feed post on your profile and attach the article. The public repository is:

https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

Do not describe this as a scan of a real company’s data.

## Article

**Title:** AI pilots stall when the data disagrees

**Body:**

Enterprise AI rarely dies in the model. It dies in the data.

The same customer has three names. An order points at a customer who does not exist. Status means Active in one system, A in another, and 1 in the warehouse. The extract the agent actually reads is weeks behind the system of record. A table exists, and the catalog does not mention it.

I built a home lab to practice the architect’s response: the Enterprise Data Gaps Discovery Agent.

A React page calls a Python API. LangGraph routes four specialists — schema, profile, reconciliation, and report. They read a synthetic CRM, ERP, and warehouse only through read-only tools. Results are capped. Every call is audited. Every finding on the screen includes the query and the rows.

One run reports the gaps on purpose: orphan orders, a shared email, a customer renamed across systems, null emails, a 42-day-stale warehouse, and a shadow table.

This is a lab with a few dozen rows, not a client dataset. The point is the design. The agent does not get a connection string. A finding without evidence does not count.

Code: https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

If you are taking an AI pilot into a real process, which shows up first: identity that does not match, extracts that are stale, or agents that can see more than they should?

## Feed post

Enterprise AI rarely dies in the model. It dies when the data disagrees.

I built a small lab, the Enterprise Data Gaps Discovery Agent, to make that problem visible.

A React page calls a Python API. LangGraph runs four specialists across a synthetic CRM, ERP, and warehouse. They use read-only tools, every call is audited, and every finding keeps its query and rows.

One run shows orphan orders, a shared email, status stored three ways, a shadow table, and a warehouse extract 42 days behind CRM.

It is a lab, not a client dataset. The design is the point: evidence, and a hard boundary on what the agent can touch.

Code: https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

Which gap shows up first in your estate?
