# Context — CE Semantica (Amazon UK Delivery)

## What this is
Example 13 in the my-hello-worlds Context Engineering series. A direct
rebuild of Example 11 (Neo4j knowledge graph) using Semantica instead of
Neo4j. Same domain, same data, same policy doc, same guarantee logic —
different infrastructure, richer provenance.

## What it shows
- **No Docker required** — Semantica ContextGraph is in-memory, saved to
  `delivery_graph.json`. Example 11 required a running Neo4j container.
- **Same three invariants** as Example 11:
  1. Policy rule parsed from `guarantee_policy.md` at runtime — no hardcoded `if`
  2. Change the policy wording, rerun ingestion, graph changes with zero code edits
  3. Agent cannot write queries — it calls two governed tools
- **New vs Example 11**: every guarantee trigger also calls `record_decision()`
  — a W3C PROV-O provenance record with full reasoning, entities, policy
  reference, confidence, and decision_maker. Example 11 had a TRIGGERS edge
  but no audit record for why it was created.
- **Python API instead of Cypher** — `get_neighbors()`, `find_node()`,
  `get_nodes_by_label()` replace Cypher traversals. Same conceptual operations,
  no query language.

## Run order
1. `python3 bootstrap_source.py`       — seed DuckDB (same as Ex 11, once)
2. `python3 ingest_to_semantica.py`    — read DuckDB + policy, write Semantica graph
3. `python3 agent_semantica_ollama.py` — ask questions

## Key files
- `contracts/guarantee_policy.md`  — same policy doc as Example 11
- `code/bootstrap_source.py`       — same DuckDB seeder as Example 11
- `code/ingest_to_semantica.py`    — Semantica graph builder (replaces ingest_to_graph.py)
- `code/agent_semantica_ollama.py` — agent with trace_order + get_guarantee_status tools
- `code/delivery_graph.json`       — serialised ContextGraph (generated, not committed)

## Side-by-side with Example 11
| Aspect | Example 11 (Neo4j) | Example 13 (Semantica) |
|--------|-------------------|------------------------|
| Storage | Neo4j (Docker) | In-memory + JSON file |
| Query language | Cypher | Python API |
| Guarantee trigger | TRIGGERS edge only | Edge + record_decision() |
| Audit trail | None | W3C PROV-O decision record |
| Guarantee check in agent | Cypher MATCH | find_node() + get_neighbors() |

## Data
3 customers, 2 carriers, 6 orders, 14 scans, 5 hubs — identical to Ex 11.
Guarantee triggered by scan 9931 (DEL + DAMAGED) on order 48213 (Sarah, Trainers).
