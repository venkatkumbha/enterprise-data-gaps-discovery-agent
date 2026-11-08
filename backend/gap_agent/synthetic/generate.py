"""Build a synthetic Telco BSS/OSS estate with intentional cross-domain gaps.

Domains covered (home-lab scale, TMF-shaped names):

BSS  crm, product_catalog, order_management, billing
OSS  service_inventory, resource_inventory, assurance
BI   analytics (stale extract of the customer/service view)

Gaps are fixed constants so discovery can be scored against known_gaps.md.
Running this script replaces every *.sqlite file under data/systems.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEMS_DIR = REPO_ROOT / "data" / "systems"
METRICS_PATH = REPO_ROOT / "data" / "ground_truth" / "metrics.json"

CRM_UPDATED = "2026-11-01"
BILLING_MODIFIED = "2026-11-02"
SERVICE_UPDATED = "2026-11-01"
ANALYTICS_AS_OF = "2026-09-20"

# Enterprise / wholesale parties. Per-domain name and status variants below.
CUSTOMERS = [
    (101, "Acme Corp", "billing@acme.example", "Active", "US"),
    (102, "Beta Industries", "finance@beta.example", "Active", "EU"),
    (103, "Gamma LLC", "ops@gamma.example", "Inactive", "US"),
    (104, "Delta Freight", "ap@delta-freight.example", "Active", "US"),
    (106, "Northwind Trading", "ap@northwind.example", "Active", "US"),
    (107, "Orbit Labs", "ops@orbit.example", "Active", "US"),
    (108, "Pioneer Health", "billing@pioneer.example", "Active", "US"),
    (109, "Quanta Retail", "ar@quanta.example", "Active", "EU"),
    (110, "Northwind Ltd", "ap@northwind.example", "Active", "EU"),
    (111, "Cedar Municipal", "it@cedar.example", "Active", "US"),
    (112, "Falcon Logistics", "ap@falcon.example", "Active", "US"),
    (113, "Iris Biotech", "science@iris.example", "Inactive", "EU"),
    (114, "Jade Telecom", "ops@jade.example", "Active", "APAC"),
    (115, "Kite Payments", "billing@kite.example", "Active", "US"),
    (116, "Lumen Foods", "ap@lumen.example", "Active", "US"),
    (117, "Maple Credit", "billing@maple.example", "Active", "US"),
    (118, "Nimbus Cloud", "it@nimbus.example", "Active", "US"),
    (119, "Oak Insurance", "claims@oak.example", "Inactive", "US"),
    (120, "Pixel Media", "ar@pixel.example", "Active", "US"),
]

BILLING_NULL_EMAIL_IDS = {102, 107, 112, 115, 119}
# New CRM party not yet provisioned in billing or service inventory.
NO_BILLING_ACCOUNT = {118}
# Analytics omits inactive Gamma and new Nimbus.
ANALYTICS_MISSING = {103, 118}
# Analytics-only party with no BSS/OSS source key.
HELIOS = (105, "Helios Medical", "billing@helios.example", "Active", "US")

CONTACTS = [
    (1, 101, "Priya Shah", "priya.shah@acme.example", "Billing"),
    (2, 104, "Owen Blake", "owen.blake@delta-freight.example", "Accounts payable"),
    (3, 106, "Mina Cho", "mina.cho@northwind.example", "Accounts payable"),
    (4, 110, "Elena Voss", "elena.voss@northwind.example", "Finance"),
    (5, 114, "Kenji Aoki", "kenji.aoki@jade.example", "Operations"),
    (6, 118, "Noah Idris", "noah.idris@nimbus.example", "IT"),
    (7, 404, "Unknown Owner", "orphan.contact@example.com", "Unknown"),
]

# Product Catalog offers (BSS PCAT).
OFFERS = [
    ("OFF-ETH-1G", "Enterprise Ethernet 1G", "CFS_ETH", 1200.0),
    ("OFF-MPLS", "MPLS VPN Access", "CFS_VPN", 800.0),
    ("OFF-DIA", "Dedicated Internet Access", "CFS_DIA", 1500.0),
    ("OFF-VOICE", "SIP Trunk 50", "CFS_VOICE", 400.0),
]

# Order Management. 9001/9002: ghost party. 5013: ghost offer.
ORDERS = [
    (5001, 101, "OFF-ETH-1G", "2026-10-02", "InProgress"),
    (5002, 102, "OFF-MPLS", "2026-10-03", "Completed"),
    (5003, 104, "OFF-DIA", "2026-10-04", "Completed"),
    (5004, 106, "OFF-ETH-1G", "2026-10-05", "InProgress"),
    (5005, 108, "OFF-VOICE", "2026-10-06", "Completed"),
    (5006, 109, "OFF-DIA", "2026-09-01", "Completed"),
    (5007, 110, "OFF-MPLS", "2026-10-08", "InProgress"),
    (5008, 111, "OFF-VOICE", "2026-10-09", "Completed"),
    (5009, 114, "OFF-ETH-1G", "2026-10-11", "InProgress"),
    (5010, 116, "OFF-DIA", "2026-10-12", "Completed"),
    (5011, 117, "OFF-MPLS", "2026-10-14", "InProgress"),
    (5012, 120, "OFF-VOICE", "2026-10-18", "Completed"),
    (9001, 999, "OFF-ETH-1G", "2026-10-20", "InProgress"),
    (9002, 999, "OFF-MPLS", "2026-10-21", "InProgress"),
    (5013, 101, "OFF-GHOST", "2026-10-22", "InProgress"),
]

# Service Inventory CFS instances. SVC-ORPHAN has no matching order/party path.
SERVICES = [
    ("SVC-101-ETH", 101, 5001, "OFF-ETH-1G", "IN_SERVICE", "2026-10-15"),
    ("SVC-102-VPN", 102, 5002, "OFF-MPLS", "IN_SERVICE", "2026-10-10"),
    ("SVC-104-DIA", 104, 5003, "OFF-DIA", "IN_SERVICE", "2026-10-12"),
    ("SVC-106-ETH", 106, 5004, "OFF-ETH-1G", "DESIGNED", "2026-10-16"),
    ("SVC-108-VOICE", 108, 5005, "OFF-VOICE", "IN_SERVICE", "2026-10-14"),
    ("SVC-114-ETH", 114, 5009, "OFF-ETH-1G", "IN_SERVICE", "2026-10-18"),
    ("SVC-120-VOICE", 120, 5012, "OFF-VOICE", "IN_SERVICE", "2026-10-20"),
    ("SVC-ORPHAN", 888, None, "OFF-ETH-1G", "IN_SERVICE", "2026-09-30"),
]

# Resource Inventory. RES-GHOST points at a service that does not exist.
RESOURCES = [
    ("CIR-ATL-01", "SVC-101-ETH", "OpticalCircuit", "ALLOCATED", "ATL-POP-1"),
    ("CIR-LON-02", "SVC-102-VPN", "OpticalCircuit", "ALLOCATED", "LON-POP-3"),
    ("PORT-DFW-9", "SVC-104-DIA", "AccessPort", "ALLOCATED", "DFW-EDGE-2"),
    ("CIR-SJC-04", "SVC-114-ETH", "OpticalCircuit", "ALLOCATED", "SJC-POP-1"),
    ("RES-IDLE", None, "SparePort", "AVAILABLE", "CHI-EDGE-1"),
    ("RES-GHOST", "SVC-DOES-NOT-EXIST", "OpticalCircuit", "ALLOCATED", "NYC-POP-2"),
]

# Assurance trouble tickets. TT-9000 references a missing service.
TICKETS = [
    ("TT-1001", "SVC-101-ETH", 101, "Open", "Degraded throughput", "2026-10-28"),
    ("TT-1002", "SVC-104-DIA", 104, "Closed", "Port flap", "2026-10-12"),
    ("TT-1003", "SVC-114-ETH", 114, "Open", "Latency breach", "2026-11-01"),
    ("TT-9000", "SVC-MISSING", 101, "Open", "No service found for ticket", "2026-11-02"),
]


def _billing_name(customer_id: int, name: str) -> str:
    if customer_id == 101:
        return "Acme Corporation"
    return name


def _service_party_name(customer_id: int, name: str) -> str:
    if customer_id == 101:
        return "ACME CORP"
    return name


def _billing_status(status: str) -> str:
    return "A" if status == "Active" else "I"


def _analytics_status(status: str) -> str:
    return "1" if status == "Active" else "0"


def _replace(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return sqlite3.connect(path)


def build_crm(path: Path) -> None:
    """BSS Customer Management."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                legal_name TEXT NOT NULL,
                email TEXT,
                status TEXT NOT NULL,
                region TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE contacts (
                contact_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT,
                role TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)",
            [(*row, CRM_UPDATED) for row in CUSTOMERS],
        )
        connection.executemany("INSERT INTO contacts VALUES (?, ?, ?, ?, ?)", CONTACTS)


def build_product_catalog(path: Path) -> None:
    """BSS Product Catalog."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE product_offering (
                offer_id TEXT PRIMARY KEY,
                offer_name TEXT NOT NULL,
                cfs_spec TEXT NOT NULL,
                list_price REAL NOT NULL
            )
            """
        )
        connection.executemany("INSERT INTO product_offering VALUES (?, ?, ?, ?)", OFFERS)


def build_order_management(path: Path) -> None:
    """BSS Order Management / Product Ordering."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE product_order (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                offer_id TEXT NOT NULL,
                order_date TEXT NOT NULL,
                order_state TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO product_order VALUES (?, ?, ?, ?, ?)",
            ORDERS,
        )


def build_billing(path: Path) -> None:
    """BSS Billing Account Management."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE billing_account (
                billing_account_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                account_name TEXT NOT NULL,
                bill_email TEXT,
                account_status TEXT NOT NULL,
                currency TEXT NOT NULL,
                last_modified TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE charge (
                charge_id INTEGER PRIMARY KEY,
                billing_account_id INTEGER NOT NULL,
                offer_id TEXT NOT NULL,
                amount REAL NOT NULL,
                charge_date TEXT NOT NULL
            )
            """
        )
        # Undocumented extract left out of the official catalog on purpose.
        connection.execute(
            """
            CREATE TABLE legacy_ar_dump (
                legacy_id INTEGER PRIMARY KEY,
                nm TEXT,
                em TEXT,
                st TEXT
            )
            """
        )
        accounts = []
        for customer_id, name, email, status, _region in CUSTOMERS:
            if customer_id in NO_BILLING_ACCOUNT:
                continue
            accounts.append(
                (
                    customer_id,
                    customer_id,
                    _billing_name(customer_id, name),
                    None if customer_id in BILLING_NULL_EMAIL_IDS else email,
                    _billing_status(status),
                    "USD",
                    BILLING_MODIFIED,
                )
            )
        connection.executemany(
            "INSERT INTO billing_account VALUES (?, ?, ?, ?, ?, ?, ?)",
            accounts,
        )
        connection.executemany(
            "INSERT INTO charge VALUES (?, ?, ?, ?, ?)",
            [
                (1, 101, "OFF-ETH-1G", 1200.0, "2026-10-31"),
                (2, 102, "OFF-MPLS", 800.0, "2026-10-31"),
                (3, 104, "OFF-DIA", 1500.0, "2026-10-31"),
                (4, 108, "OFF-VOICE", 400.0, "2026-10-31"),
            ],
        )
        connection.executemany(
            "INSERT INTO legacy_ar_dump VALUES (?, ?, ?, ?)",
            [
                (101, "Acme", "billing@acme.example", "OPEN"),
                (104, "Delta", None, "OPEN"),
                (8800, "Shadow Carrier", "ar@shadow.example", "HOLD"),
            ],
        )


def build_service_inventory(path: Path) -> None:
    """OSS Service Inventory (CFS instances)."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE customer_facing_service (
                service_id TEXT PRIMARY KEY,
                customer_id INTEGER,
                order_id INTEGER,
                offer_id TEXT NOT NULL,
                party_name TEXT,
                service_state TEXT NOT NULL,
                activated_at TEXT NOT NULL
            )
            """
        )
        by_id = {row[0]: row for row in CUSTOMERS}
        rows = []
        for service_id, customer_id, order_id, offer_id, state, activated in SERVICES:
            base = by_id.get(customer_id)
            party_name = _service_party_name(customer_id, base[1]) if base else "UNKNOWN PARTY"
            rows.append((service_id, customer_id, order_id, offer_id, party_name, state, activated))
        connection.executemany(
            "INSERT INTO customer_facing_service VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def build_resource_inventory(path: Path) -> None:
    """OSS Resource Inventory."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE resource (
                resource_id TEXT PRIMARY KEY,
                service_id TEXT,
                resource_type TEXT NOT NULL,
                operational_state TEXT NOT NULL,
                site_code TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO resource VALUES (?, ?, ?, ?, ?)",
            RESOURCES,
        )


def build_assurance(path: Path) -> None:
    """OSS Assurance / Trouble Ticketing."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE trouble_ticket (
                ticket_id TEXT PRIMARY KEY,
                service_id TEXT,
                customer_id INTEGER,
                ticket_state TEXT NOT NULL,
                summary TEXT NOT NULL,
                opened_at TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO trouble_ticket VALUES (?, ?, ?, ?, ?, ?)",
            TICKETS,
        )


def build_analytics(path: Path) -> None:
    """Stale BI extract used by reporting agents."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE dim_customer (
                customer_key INTEGER PRIMARY KEY,
                source_crm_id INTEGER,
                source_billing_id INTEGER,
                display_name TEXT NOT NULL,
                email TEXT,
                status_code TEXT NOT NULL,
                as_of_date TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE fact_service (
                service_key TEXT PRIMARY KEY,
                customer_key INTEGER,
                offer_id TEXT,
                service_state TEXT
            )
            """
        )
        rows = []
        for customer_id, name, email, status, _region in CUSTOMERS:
            if customer_id in ANALYTICS_MISSING:
                continue
            rows.append(
                (
                    customer_id,
                    customer_id,
                    None if customer_id in NO_BILLING_ACCOUNT else customer_id,
                    "ACME CORP" if customer_id == 101 else name,
                    email,
                    _analytics_status(status),
                    ANALYTICS_AS_OF,
                )
            )
        helios_id, helios_name, helios_email, helios_status, _region = HELIOS
        rows.append(
            (
                helios_id,
                None,
                None,
                helios_name,
                helios_email,
                _analytics_status(helios_status),
                ANALYTICS_AS_OF,
            )
        )
        connection.executemany(
            "INSERT INTO dim_customer VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        fact_rows = [
            (service_id, customer_id, offer_id, state)
            for service_id, customer_id, _order_id, offer_id, state, _activated in SERVICES
            if customer_id != 888
        ]
        connection.executemany(
            "INSERT INTO fact_service VALUES (?, ?, ?, ?)",
            fact_rows,
        )


def write_metrics() -> dict:
    """Recompute planted-gap counts from the files so metrics cannot drift."""
    paths = {path.stem: path for path in SYSTEMS_DIR.glob("*.sqlite")}
    conns = {name: sqlite3.connect(path) for name, path in paths.items()}
    try:
        crm = conns["crm"]
        billing = conns["billing"]
        oms = conns["order_management"]
        pcat = conns["product_catalog"]
        service = conns["service_inventory"]
        resource = conns["resource_inventory"]
        assurance = conns["assurance"]
        analytics = conns["analytics"]

        crm_ids = {row[0] for row in crm.execute("SELECT customer_id FROM customers")}
        orphan_order_rows = [
            row
            for row in oms.execute("SELECT order_id, customer_id, offer_id FROM product_order")
            if row[1] not in crm_ids
        ]
        catalog_offers = {row[0] for row in pcat.execute("SELECT offer_id FROM product_offering")}
        ghost_offers = [
            row
            for row in oms.execute("SELECT order_id, offer_id FROM product_order")
            if row[1] not in catalog_offers
        ]
        billing_ids = {row[0] for row in billing.execute("SELECT customer_id FROM billing_account")}
        null_bill_emails = billing.execute(
            "SELECT COUNT(*) FROM billing_account WHERE bill_email IS NULL"
        ).fetchone()[0]
        service_ids = {row[0] for row in service.execute("SELECT service_id FROM customer_facing_service")}
        orphan_services = [
            row
            for row in service.execute("SELECT service_id, customer_id FROM customer_facing_service")
            if row[1] not in crm_ids
        ]
        ghost_resources = [
            row
            for row in resource.execute("SELECT resource_id, service_id FROM resource")
            if row[1] is not None and row[1] not in service_ids
        ]
        ghost_tickets = [
            row
            for row in assurance.execute("SELECT ticket_id, service_id FROM trouble_ticket")
            if row[1] not in service_ids
        ]
        shared = crm.execute(
            """
            SELECT email, COUNT(*) AS n FROM customers
            WHERE email IS NOT NULL GROUP BY email HAVING n > 1
            """
        ).fetchall()
        orphan_contacts = crm.execute(
            """
            SELECT COUNT(*) FROM contacts c
            WHERE NOT EXISTS (SELECT 1 FROM customers k WHERE k.customer_id = c.customer_id)
            """
        ).fetchone()[0]
        billing_tables = {
            row[0] for row in billing.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        catalog_tables = {
            "customers",
            "contacts",
            "product_offering",
            "product_order",
            "billing_account",
            "charge",
            "customer_facing_service",
            "resource",
            "trouble_ticket",
            "dim_customer",
            "fact_service",
        }
        metrics = {
            "project": "Enterprise Data Gaps Discovery Agent",
            "viewpoint": "Telco BSS/OSS",
            "systems": sorted(paths),
            "crm_customers": len(crm_ids),
            "billing_accounts": len(billing_ids),
            "crm_without_billing_account": sorted(crm_ids - billing_ids),
            "orphan_orders": len(orphan_order_rows),
            "orders_with_unknown_offer": [row[0] for row in ghost_offers],
            "billing_null_emails": null_bill_emails,
            "shared_emails": [{"email": row[0], "customer_count": row[1]} for row in shared],
            "orphan_contacts": orphan_contacts,
            "orphan_services": [row[0] for row in orphan_services],
            "resources_with_missing_service": [row[0] for row in ghost_resources],
            "tickets_with_missing_service": [row[0] for row in ghost_tickets],
            "crm_ids_missing_from_analytics": sorted(
                crm_ids
                - {
                    row[0]
                    for row in analytics.execute(
                        "SELECT source_crm_id FROM dim_customer WHERE source_crm_id IS NOT NULL"
                    )
                }
            ),
            "analytics_only_customers": analytics.execute(
                """
                SELECT COUNT(*) FROM dim_customer
                WHERE source_crm_id IS NULL AND source_billing_id IS NULL
                """
            ).fetchone()[0],
            "billing_tables_absent_from_catalog": sorted(billing_tables - catalog_tables),
            "status_encodings": {
                "crm": ["Active", "Inactive"],
                "billing": ["A", "I"],
                "service_inventory": ["IN_SERVICE", "DESIGNED"],
                "analytics": ["1", "0"],
            },
            "as_of": {
                "crm_updated_at": CRM_UPDATED,
                "billing_last_modified": BILLING_MODIFIED,
                "service_inventory_updated": SERVICE_UPDATED,
                "analytics_as_of_date": ANALYTICS_AS_OF,
            },
            "name_variants_customer_101": ["Acme Corp", "Acme Corporation", "ACME CORP"],
        }
    finally:
        for connection in conns.values():
            connection.close()

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    SYSTEMS_DIR.mkdir(parents=True, exist_ok=True)
    # Drop previous lab files so a CRM/ERP/warehouse run cannot linger.
    for stale in SYSTEMS_DIR.glob("*.sqlite"):
        stale.unlink()

    build_crm(SYSTEMS_DIR / "crm.sqlite")
    build_product_catalog(SYSTEMS_DIR / "product_catalog.sqlite")
    build_order_management(SYSTEMS_DIR / "order_management.sqlite")
    build_billing(SYSTEMS_DIR / "billing.sqlite")
    build_service_inventory(SYSTEMS_DIR / "service_inventory.sqlite")
    build_resource_inventory(SYSTEMS_DIR / "resource_inventory.sqlite")
    build_assurance(SYSTEMS_DIR / "assurance.sqlite")
    build_analytics(SYSTEMS_DIR / "analytics.sqlite")
    metrics = write_metrics()
    print(f"Wrote BSS/OSS systems under {SYSTEMS_DIR}")
    print(f"Wrote {METRICS_PATH}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
