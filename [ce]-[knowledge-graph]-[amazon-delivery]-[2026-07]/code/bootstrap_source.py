"""
Bootstrap — seed delivery.duckdb with RAW, flat Amazon UK delivery data.

This is deliberately the "before" state: customers, orders, and scans
sit in ordinary relational tables with plain foreign-key columns. There
is no graph here, and nothing decides which scans trigger a guarantee --
that decision lives in ../contracts/guarantee_policy.md, and only gets
applied when ingest_to_graph.py runs.

Run order:
    python bootstrap_source.py     — seed delivery.duckdb (once)
    python ingest_to_graph.py      — read DuckDB + policy, write to Neo4j
    python agent_graph_ollama.py   — ask questions against the graph

Usage:
    python bootstrap_source.py
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

CUSTOMERS = [
    ("cust:8842", "Sarah", "Manchester"),
    ("cust:5521", "Tom",   "London"),
    ("cust:3390", "Emma",  "Leeds"),
]

CARRIERS = [
    ("evri",       "Evri"),
    ("royal-mail", "Royal Mail"),
]

ORDERS = [
    ("48213", "cust:8842", "evri",       "Trainers",    "2026-07-08"),
    ("51890", "cust:8842", "evri",       "Kettle",      "2026-07-10"),
    ("60021", "cust:5521", "royal-mail", "Book",        "2026-07-05"),
    ("60022", "cust:5521", "royal-mail", "Headphones",  "2026-07-11"),
    ("60023", "cust:5521", "royal-mail", "Phone Case",  "2026-07-13"),
    ("71100", "cust:3390", "evri",       "Blender",     "2026-07-09"),
]

# Flat rows: order_id + prev_scan_id are plain columns, not graph edges.
# hub_id/hub_name are repeated inline per row, exactly like a raw carrier
# feed table would look before anyone normalises or connects it.
SCANS = [
    # scan_id, order_id, prev_scan_id, scan_time,             scan_type,    condition, hub_id,          hub_name
    ("9929", "48213", None,   "2026-07-08T14:10:00Z", "DISPATCHED", "OK",      "leeds-wh",       "Leeds Warehouse"),
    ("9930", "48213", "9929", "2026-07-09T02:30:00Z", "IN_TRANSIT", "OK",      "sheffield-depot", "Sheffield Depot"),
    ("9931", "48213", "9930", "2026-07-09T06:42:00Z", "DEL",        "DAMAGED", "manchester-hub",  "Manchester Hub"),

    ("4410", "51890", None,   "2026-07-10T09:15:00Z", "DISPATCHED", "OK", "leeds-wh",        "Leeds Warehouse"),
    ("4411", "51890", "4410", "2026-07-10T18:40:00Z", "IN_TRANSIT", "OK", "sheffield-depot",  "Sheffield Depot"),
    ("4412", "51890", "4411", "2026-07-11T08:05:00Z", "DEL",        "OK", "manchester-hub",   "Manchester Hub"),

    ("7701", "60021", None,   "2026-07-05T11:00:00Z", "DISPATCHED", "OK", "london-depot", "London Depot"),
    ("7702", "60021", "7701", "2026-07-06T10:20:00Z", "ATT",        "OK", "london-depot", "London Depot"),

    ("7710", "60022", None,   "2026-07-11T09:30:00Z", "DISPATCHED", "OK", "london-depot", "London Depot"),
    ("7711", "60022", "7710", "2026-07-12T13:15:00Z", "SAF",        "OK", "london-depot", "London Depot"),

    ("7720", "60023", None,   "2026-07-13T08:50:00Z", "DISPATCHED", "OK", "london-depot", "London Depot"),
    ("7721", "60023", "7720", "2026-07-14T15:05:00Z", "NEI",        "OK", "london-depot", "London Depot"),

    ("3301", "71100", None,   "2026-07-09T10:00:00Z", "DISPATCHED", "OK", "leeds-depot", "Leeds Depot"),
    ("3302", "71100", "3301", "2026-07-12T00:00:00Z", "LIT",        "OK", "leeds-depot", "Leeds Depot"),
]


def main() -> None:
    db = duckdb.connect(DB_FILE)

    db.execute("CREATE OR REPLACE TABLE customers (customer_id VARCHAR, name VARCHAR, city VARCHAR)")
    db.execute("CREATE OR REPLACE TABLE carriers  (carrier_id VARCHAR, name VARCHAR)")
    db.execute("""
        CREATE OR REPLACE TABLE orders (
            order_id VARCHAR, customer_id VARCHAR, carrier_id VARCHAR,
            product VARCHAR, order_date VARCHAR
        )
    """)
    db.execute("""
        CREATE OR REPLACE TABLE scans (
            scan_id VARCHAR, order_id VARCHAR, prev_scan_id VARCHAR,
            scan_time VARCHAR, scan_type VARCHAR, condition VARCHAR,
            hub_id VARCHAR, hub_name VARCHAR
        )
    """)

    db.executemany("INSERT INTO customers VALUES (?, ?, ?)", CUSTOMERS)
    db.executemany("INSERT INTO carriers VALUES (?, ?)", CARRIERS)
    db.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
    db.executemany("INSERT INTO scans VALUES (?, ?, ?, ?, ?, ?, ?, ?)", SCANS)

    counts = {
        t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("customers", "carriers", "orders", "scans")
    }
    db.close()

    print(f"Created : {DB_FILE}")
    print(f"Path    : {os.path.abspath(DB_FILE)}")
    print()
    print("Seeded (raw, flat -- no relationships yet):")
    for table, n in counts.items():
        print(f"  {table:<10} -> {n} rows")
    print()
    print("Nothing here decides which scans trigger a guarantee.")
    print("That rule lives in ../contracts/guarantee_policy.md")
    print("Run ingest_to_graph.py next to build the connected graph.")


if __name__ == "__main__":
    main()
