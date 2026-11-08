# LinkedIn

Paste the article into LinkedIn’s article editor. Paste the feed post on your profile and attach the article. Cover image: [assets/linkedin-article-cover.jpg](assets/linkedin-article-cover.jpg). The public repository is:

https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

Do not describe this as a scan of a real operator’s BSS/OSS data.

## Article

**Title:** AI pilots stall when BSS and OSS disagree

**Body:**

Enterprise AI in Telco rarely dies in the model. It dies when Customer Management, Billing, Order Management, Service Inventory, Resource Inventory, and Assurance tell different stories about the same party and the same service.

The same enterprise customer has three names. A product order points at a party that does not exist, or at an offer the catalog does not sell. A CFS instance has no CRM party. A circuit and a trouble ticket point at a service that is missing. Billing has no account for a live CRM customer. Lifecycle means Active in CRM, A in Billing, IN_SERVICE in Service Inventory, and 1 in Analytics. The BI extract the agent actually reads is weeks behind the BSS record.

I built a home lab to practice the architect’s response: the Enterprise Data Gaps Discovery Agent, framed for Telco BSS/OSS.

A React page calls a Python API. LangGraph routes four specialists — schema, profile, reconciliation, and report — across synthetic CRM, Product Catalog, Order Management, Billing, Service Inventory, Resource Inventory, Assurance, and Analytics. They use read-only tools only. Results are capped. Every call is audited. Every finding keeps the query and the rows.

One run reports the gaps on purpose: orphan orders, a ghost offer, missing billing accounts, orphan services, resources and tickets without services, status-code drift, a 42-day-stale analytics extract, and a shadow AR table.

This is a lab with a few dozen rows, not an operator dataset. The point is the design. The agent does not get a connection string. A finding without evidence does not count.

Code: https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

If you are taking an AI pilot into BSS/OSS, which shows up first: party identity, order-to-service breaks, or agents that can see more than they should?

## Feed post

Enterprise AI in Telco rarely dies in the model. It dies when BSS and OSS disagree.

I built a small lab, the Enterprise Data Gaps Discovery Agent, to make that problem visible across Customer Management, Product Catalog, Order Management, Billing, Service Inventory, Resource Inventory, Assurance, and Analytics.

A React page calls a Python API. LangGraph runs four specialists. They use read-only tools, every call is audited, and every finding keeps its query and rows.

One run shows orphan orders, a ghost catalog offer, missing billing accounts, CFS/resource/ticket breaks, status stored four ways, and analytics 42 days behind CRM.

It is a lab, not an operator dataset. The design is the point: evidence, and a hard boundary on what the agent can touch.

Code: https://github.com/venkatkumbha/enterprise-data-gaps-discovery-agent

Which BSS/OSS gap shows up first in your estate?
