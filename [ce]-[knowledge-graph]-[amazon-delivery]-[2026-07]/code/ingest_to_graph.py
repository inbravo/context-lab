"""
Ingest — read raw delivery data from DuckDB, apply the guarantee trigger
rule extracted from the policy markdown, and write the connected graph
into Neo4j.

This is the actual "context building" step. bootstrap_source.py leaves
customers/orders/scans as flat, disconnected rows -- this script decides
which scans chain into a journey, which hub each scan happened at, and
-- critically -- which scans trigger a Guarantee node, based ONLY on
what ../contracts/guarantee_policy.md says. There is no hardcoded
`if scan_type == 'DEL' and condition == 'DAMAGED'` in this file: that
condition is parsed out of the policy document at runtime. Change the
policy's wording, rerun this script, and the graph changes without
touching this file's logic.

Run order:
    python bootstrap_source.py     — seed delivery.duckdb (once)
    python ingest_to_graph.py      — read DuckDB + policy, write to Neo4j
    python agent_graph_ollama.py   — ask questions against the graph

Usage:
    python ingest_to_graph.py
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import os
import re
import sys
import duckdb
from neo4j import GraphDatabase

DB_FILE     = "delivery.duckdb"
POLICY_FILE = "../contracts/guarantee_policy.md"
NEO4J_URI   = "bolt://localhost:7687"
NEO4J_AUTH  = ("neo4j", "password")


# ── 1. Parse the policy markdown -- no hand-written rule in this file ──
def parse_policy(md_text: str) -> dict:
    """
    Extract the scan-type glossary and the guarantee trigger rule from
    the policy document. This is a simple, explainable proxy for what a
    real system might do with a fuller parser or an LLM extraction step
    -- it works because the document consistently wraps system-meaningful
    values in backticks, exactly as many real internal ops docs do, so
    both humans and tooling can reliably find them.
    """
    glossary = {}
    for line in md_text.splitlines():
        m = re.match(r"\|\s*`([A-Z]+)`\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            glossary[m.group(1)] = m.group(2).strip()

    section_match = re.search(r"## Guarantee trigger rule\n(.*?)\n## ", md_text, re.DOTALL)
    section = section_match.group(1) if section_match else ""

    rule = {"scan_type": None, "condition": None, "guarantee_type": None, "rule_ref": None}
    for tok in re.findall(r"`([^`]+)`", section):
        if tok in glossary:
            rule["scan_type"] = tok
        elif ":" in tok:
            rule["rule_ref"] = tok
        elif tok.isupper():
            rule["condition"] = tok
        elif tok[:1].isupper():
            rule["guarantee_type"] = tok

    missing = [k for k, v in rule.items() if v is None]
    if missing:
        raise ValueError(f"Could not extract {missing} from {POLICY_FILE} -- check the policy wording.")

    return {"glossary": glossary, "rule": rule}


# ── 2. Read raw rows from DuckDB ─────────────────────────────────────
def load_source(db_path: str) -> dict:
    db = duckdb.connect(db_path, read_only=True)
    data = {
        "customers": db.execute("SELECT * FROM customers").fetchall(),
        "carriers":  db.execute("SELECT * FROM carriers").fetchall(),
        "orders":    db.execute("SELECT * FROM orders").fetchall(),
        "scans":     db.execute("SELECT * FROM scans ORDER BY order_id, scan_time").fetchall(),
    }
    db.close()
    return data


# ── 3. Write nodes, journey edges, and policy-driven TRIGGERS edges ──
CLEAR_CYPHER = """
MATCH (n) WHERE n:Customer OR n:Order OR n:Scan OR n:Hub OR n:Carrier OR n:Guarantee
DETACH DELETE n
"""
SEED_CUSTOMER = "MERGE (c:Customer {customer_id: $customer_id}) SET c.name = $name, c.city = $city"
SEED_CARRIER  = "MERGE (car:Carrier {carrier_id: $carrier_id}) SET car.name = $name"
SEED_ORDER = """
MATCH (c:Customer {customer_id: $customer_id})
MATCH (car:Carrier {carrier_id: $carrier_id})
MERGE (o:Order {order_id: $order_id})
SET o.product = $product, o.order_date = $order_date
MERGE (c)-[:PLACED]->(o)
MERGE (o)-[:HANDLED_BY]->(car)
"""
SEED_SCAN = """
MATCH (o:Order {order_id: $order_id})
MERGE (h:Hub {hub_id: $hub_id}) SET h.location = $hub_name
MERGE (s:Scan {scan_id: $scan_id})
SET s.scan_time = $scan_time, s.scan_type = $scan_type, s.condition = $condition
MERGE (o)-[:SCANNED_AT]->(s)
MERGE (s)-[:AT_LOCATION]->(h)
"""
LINK_NEXT_SCAN = """
MATCH (s1:Scan {scan_id: $prev_scan_id})
MATCH (s2:Scan {scan_id: $scan_id})
MERGE (s1)-[:NEXT]->(s2)
"""
TRIGGER_GUARANTEE = """
MATCH (s:Scan {scan_id: $scan_id})
MERGE (g:Guarantee {guarantee_type: $guarantee_type, rule_ref: $rule_ref})
MERGE (s)-[:TRIGGERS]->(g)
"""
COUNT_NODES = """
MATCH (n) WHERE n:Customer OR n:Order OR n:Scan OR n:Hub OR n:Carrier OR n:Guarantee
RETURN labels(n) AS labels, count(*) AS n ORDER BY labels
"""


def ingest(source: dict, policy: dict, driver: GraphDatabase.driver) -> None:
    rule = policy["rule"]
    triggered = 0

    with driver.session() as session:
        session.run(CLEAR_CYPHER)

        for customer_id, name, city in source["customers"]:
            session.run(SEED_CUSTOMER, customer_id=customer_id, name=name, city=city)
        for carrier_id, name in source["carriers"]:
            session.run(SEED_CARRIER, carrier_id=carrier_id, name=name)
        for order_id, customer_id, carrier_id, product, order_date in source["orders"]:
            session.run(SEED_ORDER, order_id=order_id, customer_id=customer_id,
                        carrier_id=carrier_id, product=product, order_date=order_date)

        for scan_id, order_id, prev_scan_id, scan_time, scan_type, condition, hub_id, hub_name in source["scans"]:
            session.run(SEED_SCAN, order_id=order_id, scan_id=scan_id, scan_time=scan_time,
                        scan_type=scan_type, condition=condition, hub_id=hub_id, hub_name=hub_name)
            if prev_scan_id:
                session.run(LINK_NEXT_SCAN, prev_scan_id=prev_scan_id, scan_id=scan_id)

            # The only place this rule is evaluated -- parsed straight out
            # of the policy document, not a hardcoded condition here.
            if scan_type == rule["scan_type"] and condition == rule["condition"]:
                session.run(TRIGGER_GUARANTEE, scan_id=scan_id,
                            guarantee_type=rule["guarantee_type"], rule_ref=rule["rule_ref"])
                triggered += 1

        node_counts = session.run(COUNT_NODES).data()

    print(f"Guarantee rule applied: scan_type={rule['scan_type']!r} AND condition={rule['condition']!r}"
          f" -> {rule['guarantee_type']} ({rule['rule_ref']})")
    print(f"Scans matching the rule: {triggered}")
    print()
    print("Graph nodes:")
    for row in node_counts:
        print(f"  {row['labels'][0]:<10} -> {row['n']}")


def main() -> None:
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    db_path     = os.path.join(script_dir, DB_FILE)
    policy_path = os.path.join(script_dir, POLICY_FILE)

    if not os.path.exists(db_path):
        print(f"ERROR: {db_path} not found — run bootstrap_source.py first.")
        sys.exit(1)
    if not os.path.exists(policy_path):
        print(f"ERROR: policy not found at {policy_path}")
        sys.exit(1)

    with open(policy_path) as f:
        policy = parse_policy(f.read())

    print(f"Parsed policy: {POLICY_FILE}")
    print(f"  Glossary : {list(policy['glossary'].keys())}")
    print(f"  Rule     : {policy['rule']}")
    print()

    source = load_source(db_path)

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: cannot reach Neo4j at {NEO4J_URI} — is the container running?")
        print(f"  {e}")
        sys.exit(1)

    ingest(source, policy, driver)
    driver.close()

    print()
    print("View it: http://localhost:7474  (neo4j / password)")
    print("  MATCH (n) RETURN n")


if __name__ == "__main__":
    main()
