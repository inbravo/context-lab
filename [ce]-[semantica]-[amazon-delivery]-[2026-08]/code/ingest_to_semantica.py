"""
ingest_to_semantica.py — Read raw delivery data from DuckDB, apply the
guarantee trigger rule extracted from the policy markdown, and write
the connected graph into a Semantica ContextGraph.

This is a direct rebuild of Example 11 (ingest_to_graph.py → Neo4j) using
Semantica instead of Neo4j. The same three things are true here:

  1. The policy rule is parsed from guarantee_policy.md at runtime —
     no hardcoded `if scan_type == 'DEL'` anywhere in this file.
  2. The graph is queryable in Python without a database server or Cypher.
  3. The guarantee trigger is recorded as a governed decision with full
     W3C PROV-O provenance — the thing Example 11 could not do.

What changed vs Example 11:
  Neo4j / Cypher             →  Semantica ContextGraph Python API
  Docker required            →  No Docker needed (in-memory + save_to_file)
  TRIGGERS edge only         →  TRIGGERS edge + record_decision() provenance
  No audit trail             →  Decision: who triggered it, reasoning, confidence,
                                entities linked, traceability to policy:4.2

Run order:
    python bootstrap_source.py        — seed delivery.duckdb (once, same as Ex 11)
    python ingest_to_semantica.py     — read DuckDB + policy, write Semantica graph
    python agent_semantica_ollama.py  — ask questions against the graph

Usage:
    python ingest_to_semantica.py
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
from semantica.context import ContextGraph

DB_FILE     = "delivery.duckdb"
POLICY_FILE = "../contracts/guarantee_policy.md"
GRAPH_FILE  = "delivery_graph.json"


# ── 1. Parse the policy markdown — identical to Example 11 ────────────────
def parse_policy(md_text: str) -> dict:
    """
    Extract the scan-type glossary and the guarantee trigger rule from
    the policy document.  Same parser as Example 11: backtick convention
    makes the values machine-extractable without an LLM.
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
        raise ValueError(f"Could not extract {missing} from policy — check the wording.")

    return {"glossary": glossary, "rule": rule}


# ── 2. Read raw rows from DuckDB — identical to Example 11 ───────────────
def load_source(db_path: str) -> dict:
    db = duckdb.connect(db_path, read_only=True)
    data = {
        "customers": db.execute("SELECT * FROM customers").fetchall(),
        "carriers":  db.execute("SELECT * FROM carriers").fetchall(),
        "orders":    db.execute("SELECT * FROM orders").fetchall(),
        "scans":     db.execute(
            "SELECT * FROM scans ORDER BY order_id, scan_time"
        ).fetchall(),
    }
    db.close()
    return data


# ── 3. Build the Semantica ContextGraph ───────────────────────────────────
def ingest(source: dict, policy: dict) -> ContextGraph:
    """
    Build a Semantica ContextGraph from the raw delivery data.

    Node types:   Customer, Carrier, Order, Scan, Hub, Guarantee
    Edge types:   PLACED, HANDLED_BY, SCANNED_AT, AT_LOCATION, NEXT, TRIGGERS

    The guarantee trigger does two things at once:
      (a) adds a Guarantee node + TRIGGERS edge  (graph traversal, same as Ex 11)
      (b) calls graph.record_decision()          (provenance, new in this example)

    Swap (a) is the graph pattern.  (b) is the audit record.
    Both are generated from the same rule parsed out of the policy doc.
    """
    graph   = ContextGraph()
    rule    = policy["rule"]
    triggered = 0
    decision_ids: dict[str, str] = {}   # scan_id → decision_id

    # ── Customers ─────────────────────────────────────────────────────────
    for customer_id, name, city in source["customers"]:
        graph.add_node(f"customer:{customer_id}", "Customer", name=name, city=city)

    # ── Carriers ──────────────────────────────────────────────────────────
    for carrier_id, name in source["carriers"]:
        graph.add_node(f"carrier:{carrier_id}", "Carrier", name=name)

    # ── Orders ────────────────────────────────────────────────────────────
    for order_id, customer_id, carrier_id, product, order_date in source["orders"]:
        graph.add_node(f"order:{order_id}", "Order",
                       order_id=order_id, product=product, order_date=order_date)
        graph.add_edge(f"customer:{customer_id}", f"order:{order_id}", "PLACED")
        graph.add_edge(f"order:{order_id}", f"carrier:{carrier_id}", "HANDLED_BY")

    # ── Scans + journey chain ─────────────────────────────────────────────
    for scan_id, order_id, prev_scan_id, scan_time, scan_type, condition, hub_id, hub_name in source["scans"]:
        graph.add_node(f"scan:{scan_id}", "Scan",
                       scan_id=scan_id, scan_type=scan_type,
                       condition=condition, scan_time=scan_time)
        graph.add_node(f"hub:{hub_id}", "Hub", hub_id=hub_id, location=hub_name)

        graph.add_edge(f"order:{order_id}", f"scan:{scan_id}", "SCANNED_AT")
        graph.add_edge(f"scan:{scan_id}", f"hub:{hub_id}", "AT_LOCATION")

        if prev_scan_id:
            graph.add_edge(f"scan:{prev_scan_id}", f"scan:{scan_id}", "NEXT")

        # ── Guarantee trigger (same rule as Example 11) ───────────────────
        if scan_type == rule["scan_type"] and condition == rule["condition"]:
            g_id = f"guarantee:{order_id}"
            graph.add_node(g_id, "Guarantee",
                           guarantee_type=rule["guarantee_type"],
                           rule_ref=rule["rule_ref"],
                           triggered_by_scan=scan_id)
            graph.add_edge(f"scan:{scan_id}", g_id, "TRIGGERS")

            # (b) Provenance record — what Example 11 could NOT do.
            # This creates a W3C PROV-O compatible decision record:
            # who triggered it, why, which policy reference, confidence.
            dec_id = graph.record_decision(
                category="guarantee_eligibility",
                scenario=f"Order {order_id}: scan {scan_id} is {scan_type} with condition {condition}",
                reasoning=(
                    f"Policy {rule['rule_ref']} states: scan_type={rule['scan_type']} "
                    f"AND condition={rule['condition']} triggers {rule['guarantee_type']}. "
                    f"Scan {scan_id} matches both criteria. No LLM involved — this is a "
                    f"deterministic rule parsed from the policy document at ingestion time."
                ),
                outcome=f"eligible:{rule['guarantee_type']}",
                confidence=1.0,
                entities=[f"scan:{scan_id}", f"order:{order_id}", g_id],
                decision_maker="guarantee-policy-engine",
                metadata={"policy_doc": POLICY_FILE, "rule_ref": rule["rule_ref"]},
            )
            decision_ids[scan_id] = dec_id
            triggered += 1

    return graph, triggered, decision_ids


# ── 4. Main ───────────────────────────────────────────────────────────────
def main() -> None:
    script_dir  = os.path.dirname(os.path.abspath(__file__))
    db_path     = os.path.join(script_dir, DB_FILE)
    policy_path = os.path.join(script_dir, POLICY_FILE)
    graph_path  = os.path.join(script_dir, GRAPH_FILE)

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
    graph, triggered, decision_ids = ingest(source, policy)

    graph.save_to_file(graph_path)

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"Guarantee rule applied: scan_type={policy['rule']['scan_type']!r} "
          f"AND condition={policy['rule']['condition']!r} "
          f"-> {policy['rule']['guarantee_type']} ({policy['rule']['rule_ref']})")
    print(f"Scans matching the rule: {triggered}")
    print()

    stats = graph.stats()
    print("Graph summary:")
    print(f"  Nodes  : {stats.get('nodes', len(graph.nodes))}")
    print(f"  Edges  : {stats.get('edges', len(graph.edges))}")
    print()

    for label in ("Customer", "Carrier", "Order", "Scan", "Hub", "Guarantee"):
        nodes = graph.get_nodes_by_label(label)
        print(f"  {label:<10} -> {len(nodes)}")

    print()
    print(f"Graph saved : {graph_path}")
    if decision_ids:
        print()
        print("Provenance decisions recorded (new vs Example 11):")
        for scan_id, dec_id in decision_ids.items():
            print(f"  scan:{scan_id} -> decision:{dec_id}")
        print("  Each decision is a W3C PROV-O record: reasoning, entities,")
        print("  policy reference, confidence, decision_maker.")
    print()
    print("Prove the rule is externalized — same test as Example 11:")
    print(f"  Edit {policy_path}")
    print("  Change 'DAMAGED' to something else, rerun this script:")
    print("  Scans matching the rule: 0  — zero code changes, only the policy wording")


if __name__ == "__main__":
    main()
