"""
bootstrap_bsl.py — Seed DuckDB with Amazon UK Delivery data.

Creates delivery.duckdb with four tables:
  customers  — 3 customers
  carriers   — 2 carriers
  orders     — 6 orders, each with EDD components and current status
  scans      — latest scan per order (for status lookup)

Run once before agent_bsl_ollama.py.

Usage:
    python bootstrap_bsl.py
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import os
import duckdb

DB_FILE = "delivery.duckdb"


def main() -> None:
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    db = duckdb.connect(DB_FILE)

    # ── customers ──────────────────────────────────────────────────────────
    db.execute("""
        CREATE TABLE customers (
            customer_id   TEXT PRIMARY KEY,
            name          TEXT NOT NULL,
            city          TEXT NOT NULL
        )
    """)
    db.executemany("INSERT INTO customers VALUES (?, ?, ?)", [
        ("C001", "Sarah",   "Manchester"),
        ("C002", "Tom",     "London"),
        ("C003", "Emma",    "Leeds"),
    ])

    # ── carriers ───────────────────────────────────────────────────────────
    db.execute("""
        CREATE TABLE carriers (
            carrier_id  TEXT PRIMARY KEY,
            name        TEXT NOT NULL
        )
    """)
    db.executemany("INSERT INTO carriers VALUES (?, ?)", [
        ("CAR01", "Evri"),
        ("CAR02", "Royal Mail"),
    ])

    # ── orders ─────────────────────────────────────────────────────────────
    # EDD components:
    #   edd_date = order_date + processing_days + transit_days + weekend_adjustment
    # postcode_match: false for ATT orders (EDD filter excludes them)
    db.execute("""
        CREATE TABLE orders (
            order_id            TEXT PRIMARY KEY,
            customer_id         TEXT NOT NULL,
            carrier_id          TEXT NOT NULL,
            product             TEXT NOT NULL,
            order_date          DATE NOT NULL,
            processing_days     INTEGER NOT NULL,
            transit_days        INTEGER NOT NULL,
            weekend_adjustment  INTEGER NOT NULL,
            current_status      TEXT NOT NULL,
            postcode_match      BOOLEAN NOT NULL
        )
    """)
    db.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            # order_id, customer, carrier, product, order_date,
            # proc, transit, weekend_adj, status, postcode_match
            ("48213", "C001", "CAR01", "Trainers",    "2026-07-08", 1, 2, 0, "DEL", True),
            ("51890", "C001", "CAR01", "Kettle",      "2026-07-09", 1, 2, 1, "DEL", True),
            ("60021", "C002", "CAR02", "Book",        "2026-07-10", 1, 1, 0, "ATT", False),
            ("60022", "C002", "CAR02", "Headphones",  "2026-07-10", 1, 1, 0, "SAF", True),
            ("60023", "C002", "CAR02", "Phone Case",  "2026-07-11", 1, 1, 0, "NEI", True),
            ("71100", "C003", "CAR01", "Blender",     "2026-07-12", 1, 3, 0, "LIT", True),
        ],
    )

    # ── scans (latest scan per order, for status detail) ──────────────────
    db.execute("""
        CREATE TABLE scans (
            scan_id       TEXT PRIMARY KEY,
            order_id      TEXT NOT NULL,
            scan_time     TIMESTAMP NOT NULL,
            scan_type     TEXT NOT NULL,
            condition     TEXT,
            hub_location  TEXT NOT NULL
        )
    """)
    db.executemany(
        "INSERT INTO scans VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("S001", "48213", "2026-07-09 06:42:00", "DEL",        "DAMAGED",  "Manchester Hub"),
            ("S002", "51890", "2026-07-11 14:10:00", "DEL",        "OK",       "Manchester Hub"),
            ("S003", "60021", "2026-07-11 10:05:00", "ATT",        None,       "London Depot"),
            ("S004", "60022", "2026-07-11 11:30:00", "SAF",        None,       "London Depot"),
            ("S005", "60023", "2026-07-12 09:15:00", "NEI",        None,       "London Depot"),
            ("S006", "71100", "2026-07-13 08:00:00", "IN_TRANSIT", None,       "Sheffield Depot"),
        ],
    )

    db.close()

    print(f"Created {DB_FILE}")
    print("  customers : 3 rows")
    print("  carriers  : 2 rows")
    print("  orders    : 6 rows")
    print("  scans     : 6 rows")
    print()
    print("EDD components seeded:")
    print("  edd_date = order_date + processing_days + transit_days + weekend_adjustment")
    print("  postcode_match = false for ATT orders → filtered out by EDD metric")


if __name__ == "__main__":
    main()
