"""Build three SQLite systems that disagree with each other on purpose.

The files stand in for a CRM, an ERP, and a warehouse. Gaps are fixed, not
random, so the discovery agent can be scored against a known list.
Running this script overwrites data/systems/*.sqlite and refreshes metrics.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEMS_DIR = REPO_ROOT / "data" / "systems"
METRICS_PATH = REPO_ROOT / "data" / "ground_truth" / "metrics.json"

# Dates are fixed so freshness gaps do not drift with the clock.
CRM_UPDATED = "2026-11-01"
ERP_MODIFIED = "2026-11-02"
WAREHOUSE_AS_OF = "2026-09-20"

# Canonical companies. Per-system variants are applied in the builders.
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

# ERP stores these emails as NULL even when CRM has them.
ERP_NULL_EMAIL_IDS = {102, 107, 112, 115, 119}

# Present in the warehouse extract only. No CRM or ERP key.
HELIOS = (105, "Helios Medical", "billing@helios.example", "Active", "US")

# Warehouse omits these CRM/ERP customers. Gamma is inactive; Nimbus is new.
WAREHOUSE_MISSING_IDS = {103, 118}

CONTACTS = [
    (1, 101, "Priya Shah", "priya.shah@acme.example", "Billing"),
    (2, 104, "Owen Blake", "owen.blake@delta-freight.example", "Accounts payable"),
    (3, 106, "Mina Cho", "mina.cho@northwind.example", "Accounts payable"),
    (4, 110, "Elena Voss", "elena.voss@northwind.example", "Finance"),
    (5, 114, "Kenji Aoki", "kenji.aoki@jade.example", "Operations"),
    (6, 118, "Noah Idris", "noah.idris@nimbus.example", "IT"),
    # Referential gap: contact points at a customer id that does not exist.
    (7, 404, "Unknown Owner", "orphan.contact@example.com", "Unknown"),
]

PRODUCTS = [
    ("SKU-NET-1", "Wavelength circuit", 1200.0),
    ("SKU-SUP-4", "Support retainer", 400.0),
    ("SKU-HW-9", "Edge appliance", 2500.0),
]

# 9001 and 9002 point at customer 999, which is in none of the systems.
ORDERS = [
    (5001, 101, "SKU-NET-1", 1200.0, "2026-10-02", "OPEN"),
    (5002, 102, "SKU-SUP-4", 400.0, "2026-10-03", "OPEN"),
    (5003, 104, "SKU-HW-9", 2500.0, "2026-10-04", "CLOSED"),
    (5004, 106, "SKU-NET-1", 2400.0, "2026-10-05", "OPEN"),
    (5005, 108, "SKU-SUP-4", 800.0, "2026-10-06", "CLOSED"),
    (5006, 109, "SKU-HW-9", 2500.0, "2026-09-01", "CLOSED"),
    (5007, 110, "SKU-NET-1", 1200.0, "2026-10-08", "OPEN"),
    (5008, 111, "SKU-SUP-4", 400.0, "2026-10-09", "OPEN"),
    (5009, 114, "SKU-HW-9", 5000.0, "2026-10-11", "OPEN"),
    (5010, 116, "SKU-NET-1", 1200.0, "2026-10-12", "CLOSED"),
    (5011, 117, "SKU-SUP-4", 400.0, "2026-10-14", "OPEN"),
    (5012, 120, "SKU-HW-9", 2500.0, "2026-10-18", "OPEN"),
    (9001, 999, "SKU-NET-1", 1200.0, "2026-10-20", "OPEN"),
    (9002, 999, "SKU-SUP-4", 800.0, "2026-10-21", "OPEN"),
]


def _status_erp(status: str) -> str:
    """ERP encodes the same concept as a one-letter code."""
    return "A" if status == "Active" else "I"


def _status_warehouse(status: str) -> str:
    """Warehouse encodes the same concept as a numeric string."""
    return "1" if status == "Active" else "0"


def _erp_name(customer_id: int, name: str) -> str:
    if customer_id == 101:
        return "Acme Corporation"
    return name


def _warehouse_name(customer_id: int, name: str) -> str:
    if customer_id == 101:
        return "ACME CORP"
    return name


def _replace(path: Path) -> sqlite3.Connection:
    """Drop any previous file so regeneration is deterministic."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return sqlite3.connect(path)


def build_crm(path: Path) -> None:
    """System of engagement. Cleaner names, plus one orphan contact."""
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


def build_erp(path: Path) -> None:
    """System of record for orders. Adds null emails, renamed columns, and a shadow table."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE customers (
                cust_id INTEGER PRIMARY KEY,
                customer_name TEXT NOT NULL,
                email_address TEXT,
                account_status TEXT NOT NULL,
                region_code TEXT NOT NULL,
                last_modified TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE products (
                sku TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                list_price REAL NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                cust_id INTEGER NOT NULL,
                product_sku TEXT NOT NULL,
                amount REAL NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )
        # Undocumented extract. Left out of data/catalog/official_catalog.md on purpose.
        connection.execute(
            """
            CREATE TABLE legacy_cust_dump (
                legacy_id INTEGER PRIMARY KEY,
                nm TEXT,
                em TEXT,
                st TEXT
            )
            """
        )
        erp_customers = []
        for customer_id, name, email, status, region in CUSTOMERS:
            erp_email = None if customer_id in ERP_NULL_EMAIL_IDS else email
            erp_customers.append(
                (
                    customer_id,
                    _erp_name(customer_id, name),
                    erp_email,
                    _status_erp(status),
                    region,
                    ERP_MODIFIED,
                )
            )
        connection.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)", erp_customers)
        connection.executemany("INSERT INTO products VALUES (?, ?, ?)", PRODUCTS)
        connection.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", ORDERS)
        connection.executemany(
            "INSERT INTO legacy_cust_dump VALUES (?, ?, ?, ?)",
            [
                (101, "Acme", "billing@acme.example", "OPEN"),
                (104, "Delta", None, "OPEN"),
                (8800, "Shadow Retail", "ar@shadow.example", "HOLD"),
            ],
        )


def build_warehouse(path: Path) -> None:
    """Stale analytics extract. Drops two customers and adds one with no source key."""
    with _replace(path) as connection:
        connection.execute(
            """
            CREATE TABLE dim_customer (
                customer_key INTEGER PRIMARY KEY,
                source_crm_id INTEGER,
                source_erp_id INTEGER,
                display_name TEXT NOT NULL,
                email TEXT,
                status_code TEXT NOT NULL,
                as_of_date TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE fact_order (
                order_key INTEGER PRIMARY KEY,
                customer_key INTEGER,
                sku TEXT,
                amount REAL,
                order_date TEXT
            )
            """
        )
        rows = []
        for customer_id, name, email, status, _region in CUSTOMERS:
            if customer_id in WAREHOUSE_MISSING_IDS:
                continue
            rows.append(
                (
                    customer_id,
                    customer_id,
                    customer_id,
                    _warehouse_name(customer_id, name),
                    email,
                    _status_warehouse(status),
                    WAREHOUSE_AS_OF,
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
                _status_warehouse(helios_status),
                WAREHOUSE_AS_OF,
            )
        )
        connection.executemany(
            "INSERT INTO dim_customer VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        # The warehouse load dropped the two orders that point at customer 999.
        fact_rows = [
            (order_id, customer_id, sku, amount, order_date)
            for order_id, customer_id, sku, amount, order_date, _status in ORDERS
            if customer_id != 999
        ]
        connection.executemany("INSERT INTO fact_order VALUES (?, ?, ?, ?, ?)", fact_rows)


def write_metrics() -> dict:
    """Recompute the gaps from the files so the JSON cannot drift from the SQL."""
    crm = sqlite3.connect(SYSTEMS_DIR / "crm.sqlite")
    erp = sqlite3.connect(SYSTEMS_DIR / "erp.sqlite")
    warehouse = sqlite3.connect(SYSTEMS_DIR / "warehouse.sqlite")
    try:
        orphan_orders = erp.execute(
            """
            SELECT COUNT(*) FROM orders
            WHERE cust_id NOT IN (SELECT cust_id FROM customers)
            """
        ).fetchone()[0]
        order_count = erp.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        null_emails = erp.execute(
            "SELECT COUNT(*) FROM customers WHERE email_address IS NULL"
        ).fetchone()[0]
        erp_customer_count = erp.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        shared = crm.execute(
            """
            SELECT email, COUNT(*) AS n
            FROM customers
            WHERE email IS NOT NULL
            GROUP BY email
            HAVING n > 1
            """
        ).fetchall()
        orphan_contacts = crm.execute(
            """
            SELECT COUNT(*) FROM contacts c
            WHERE NOT EXISTS (
                SELECT 1 FROM customers k WHERE k.customer_id = c.customer_id
            )
            """
        ).fetchone()[0]
        warehouse_only = warehouse.execute(
            """
            SELECT COUNT(*) FROM dim_customer
            WHERE source_crm_id IS NULL AND source_erp_id IS NULL
            """
        ).fetchone()[0]
        crm_ids = {row[0] for row in crm.execute("SELECT customer_id FROM customers")}
        wh_ids = {
            row[0]
            for row in warehouse.execute(
                "SELECT source_crm_id FROM dim_customer WHERE source_crm_id IS NOT NULL"
            )
        }
        catalog_tables = {"customers", "products", "orders", "contacts", "dim_customer", "fact_order"}
        erp_tables = {row[0] for row in erp.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        metrics = {
            "project": "Enterprise Data Gaps Discovery Agent",
            "crm_customers": len(crm_ids),
            "erp_customers": erp_customer_count,
            "orphan_orders": orphan_orders,
            "erp_orders": order_count,
            "erp_null_emails": null_emails,
            "shared_emails": [{"email": row[0], "customer_count": row[1]} for row in shared],
            "orphan_contacts": orphan_contacts,
            "warehouse_only_customers": warehouse_only,
            "crm_ids_missing_from_warehouse": sorted(crm_ids - wh_ids),
            "erp_tables_absent_from_catalog": sorted(erp_tables - catalog_tables),
            "status_encodings": {
                "crm": ["Active", "Inactive"],
                "erp": ["A", "I"],
                "warehouse": ["1", "0"],
            },
            "as_of": {
                "crm_updated_at": CRM_UPDATED,
                "erp_last_modified": ERP_MODIFIED,
                "warehouse_as_of_date": WAREHOUSE_AS_OF,
            },
            "name_variants_customer_101": ["Acme Corp", "Acme Corporation", "ACME CORP"],
        }
    finally:
        crm.close()
        erp.close()
        warehouse.close()

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def main() -> None:
    SYSTEMS_DIR.mkdir(parents=True, exist_ok=True)
    build_crm(SYSTEMS_DIR / "crm.sqlite")
    build_erp(SYSTEMS_DIR / "erp.sqlite")
    build_warehouse(SYSTEMS_DIR / "warehouse.sqlite")
    metrics = write_metrics()
    print(f"Wrote systems under {SYSTEMS_DIR}")
    print(f"Wrote {METRICS_PATH}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
