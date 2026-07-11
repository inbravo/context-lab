# CE Knowledge Graph Demo — Amazon UK Delivery (Neo4j)

**Semantic component:** Knowledge Graph (Component 4) — Neo4j, a local, open-source equivalent of Amazon Neptune.

---

## What this shows

- **A real three-stage context-building pipeline, not just a pre-loaded graph.** `bootstrap_source.py` seeds flat, disconnected rows into DuckDB — exactly how raw operational data actually looks. `ingest_to_graph.py` is the ETL step: it reads those rows *and* reads `contracts/guarantee_policy.md` — a prose policy document, not YAML — to decide which scans connect to a `Guarantee` node. Only then does the graph exist in Neo4j.
- **The guarantee rule is parsed out of the policy document at runtime, not hardcoded in Python.** `guarantee_policy.md` is written the way a real Fulfilment Policy actually is — headings, a defined-terms table, plain prose — and `ingest_to_graph.py` extracts the rule (`scan_type=DEL AND condition=DAMAGED → AtoZGuarantee`) from it. Change the policy's wording and rerun ingestion: the graph changes with zero code edits. That's the actual point of "governed" — the rule lives in the document Legal signed off on, not in someone's `if` statement.
- A small but real delivery network: **3 customers, 6 orders, 14 scan events across 5 hubs and 2 carriers** — connected nodes in a real graph database instead of flat, unrelated tables. This is the "How does this all fit together?" gap from the CE knowledge base's Amazon UK Delivery use case, now running as real code.
- Each order is a real **multi-hop journey** (dispatch → depot → hub), chained with `NEXT` edges — not a single scan. The agent calls **one tool** — `trace_order` — which walks `Customer -[:PLACED]-> Order -[:SCANNED_AT]-> Scan -[:AT_LOCATION]-> Hub`, returning the full journey in order. It never writes an ad-hoc join per question.
- The final scan of each journey uses the **same status vocabulary as the CE site's Business Glossary component**: `DEL` (Delivered), `ATT` (Attempted), `SAF` (Safe Place), `NEI` (Neighbour Drop), `LIT` (Lost in Transit). Intermediate hops use operational codes (`DISPATCHED`, `IN_TRANSIT`) — matching how carriers actually scan a parcel in transit versus at final delivery.
- Same query pattern as Amazon Neptune's **openCypher** endpoint — the `neo4j` Python driver code here is close to unchanged from what you'd write against Neptune. Swap the connection string, not the code.

**The six seeded orders:**

| Order | Customer | Product | Journey | Outcome |
|-------|----------|---------|---------|---------|
| 48213 | Sarah (Manchester) | Trainers | Leeds Warehouse → Sheffield Depot → Manchester Hub | `DEL` + `DAMAGED` → **Guarantee triggered** |
| 51890 | Sarah (Manchester) | Kettle | Leeds Warehouse → Sheffield Depot → Manchester Hub | `DEL`, condition OK → no guarantee |
| 60021 | Tom (London) | Book | London Depot → London Depot | `ATT` (attempted, no one home) |
| 60022 | Tom (London) | Headphones | London Depot → London Depot | `SAF` (left in safe place) |
| 60023 | Tom (London) | Phone Case | London Depot → London Depot | `NEI` (left with neighbour) |
| 71100 | Emma (Leeds) | Blender | Leeds Depot → Leeds Depot | `LIT` (lost in transit) |

---

## Prerequisites

```bash
docker run -d --name neo4j-delivery -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:5

pip install neo4j duckdb openai structlog
ollama serve && ollama pull qwen2.5
```

---

## Quick Start

```bash
cd code/
python3 bootstrap_source.py     # 1. seed raw, disconnected data into DuckDB
python3 ingest_to_graph.py      # 2. read DuckDB + parse the policy doc, write to Neo4j
python3 agent_graph_ollama.py   # 3. ask questions against the graph
```

**Prove the rule is really externalized** — edit `contracts/guarantee_policy.md`, change `DAMAGED` in the "Guarantee trigger rule" section to something else (e.g. `LATE`), then rerun step 2 only:
```bash
python3 ingest_to_graph.py
```
`Scans matching the rule: 0` — no code changed, only the prose. Revert the wording and rerun to restore the guarantee.

**Try it against the ungoverned order** (no guarantee edge exists):
```bash
python3 agent_graph_ollama.py "Is order 51890 covered by a guarantee?"
```

**Expected output of `ingest_to_graph.py`:**
```
Parsed policy: ../contracts/guarantee_policy.md
  Glossary : ['DEL', 'ATT', 'SAF', 'NEI', 'LIT']
  Rule     : {'scan_type': 'DEL', 'condition': 'DAMAGED', 'guarantee_type': 'AtoZGuarantee', 'rule_ref': 'policy:4.2'}

Guarantee rule applied: scan_type='DEL' AND condition='DAMAGED' -> AtoZGuarantee (policy:4.2)
Scans matching the rule: 1

Graph nodes:
  Carrier    -> 2
  Customer   -> 3
  Guarantee  -> 1
  Hub        -> 5
  Order      -> 6
  Scan       -> 14
```

**Expected output of `agent_graph_ollama.py`:**
```
============================================================
The journey of order 48213 has been traced as follows:

- July 8th, 14:10 UTC: dispatched from Leeds Warehouse (DISPATCHED, OK)
- July 9th: in transit via Sheffield Depot (IN_TRANSIT, OK)
- July 9th, 06:42 UTC: arrived at Manchester Hub (DEL, DAMAGED)

This final scan triggers the AtoZGuarantee (policy:4.2) — you're covered.
============================================================

Graph trace (Cypher result):
{
  "customer_name": "Sarah",
  "order_id": "48213",
  "product": "Trainers",
  "order_date": "2026-07-08",
  "carrier_name": "Evri",
  "scan_count": 3,
  "journey": [
    {"scan_id": "9929", "scan_time": "2026-07-08T14:10:00Z", "scan_type": "DISPATCHED", "condition": "OK", "hub_location": "Leeds Warehouse"},
    {"scan_id": "9930", "scan_time": "2026-07-09T02:30:00Z", "scan_type": "IN_TRANSIT", "condition": "OK", "hub_location": "Sheffield Depot"},
    {"scan_id": "9931", "scan_time": "2026-07-09T06:42:00Z", "scan_type": "DEL", "condition": "DAMAGED", "hub_location": "Manchester Hub"}
  ],
  "guarantee_type": "AtoZGuarantee",
  "guarantee_rule_ref": "policy:4.2"
}
```

**More questions to try:**
```bash
python3 agent_graph_ollama.py "Is order 51890 covered by a guarantee?"
python3 agent_graph_ollama.py "What happened to Tom's order 60021?"
python3 agent_graph_ollama.py "Where is order 71100 right now?"
```

---

## See the graph visually

Neo4j ships a browser UI that Neptune doesn't give you without extra tooling:

1. Open [http://localhost:7474](http://localhost:7474)
2. Log in with `neo4j` / `password` (first login may prompt you to set a new password — reuse `password` or update `NEO4J_AUTH` in both files to match)
3. Run:
   ```cypher
   MATCH (n) RETURN n
   ```
4. You'll see **31 nodes** (3 `Customer`, 6 `Order`, 14 `Scan`, 5 `Hub`, 2 `Carrier`, 1 `Guarantee`) drawn as an actual connected network — Sarah's two orders fanning out to their own journeys, Tom's three orders converging on the same London Depot, order `48213`'s path reaching all the way to the lone `Guarantee` node while every other order's path stops short. Click any node to see its properties in the side panel.

Trace one order's full multi-hop journey, in the exact shape the agent's `trace_order` tool returns it:
```cypher
MATCH (c:Customer)-[:PLACED]->(o:Order {order_id: '48213'})
MATCH (o)-[:SCANNED_AT]->(s:Scan)-[:AT_LOCATION]->(h:Hub)
OPTIONAL MATCH (s)-[:TRIGGERS]->(g:Guarantee)
RETURN c, o, s, h, g
```

See the scan sequence as an actual chain (dispatch → depot → hub):
```cypher
MATCH p = (:Scan {scan_id: '9929'})-[:NEXT*]->(:Scan)
RETURN p
```

Compare against an order with no guarantee, to see the missing edge directly:
```cypher
MATCH (c:Customer)-[:PLACED]->(o:Order {order_id: '51890'})
MATCH (o)-[:SCANNED_AT]->(s:Scan)-[:AT_LOCATION]->(h:Hub)
OPTIONAL MATCH (s)-[:TRIGGERS]->(g:Guarantee)
RETURN c, o, s, h, g
```
No `Guarantee` node appears in the result — because no `TRIGGERS` edge exists for any scan on this order.

See Tom's order history as a pattern, not three isolated lookups:
```cypher
MATCH (c:Customer {name: 'Tom'})-[:PLACED]->(o:Order)-[:SCANNED_AT]->(s:Scan)
WHERE NOT (s)-[:NEXT]->()
RETURN c.name, o.order_id, o.product, s.scan_type
```

---

## Architecture

**Stage 1 & 2 — context building (this is the part that used to not exist):**

```
┌───────────────────────────┐        ┌──────────────────────────────────┐
│   bootstrap_source.py      │  ──►   │   delivery.duckdb                  │
│   (raw, flat rows)         │        │   customers · carriers · orders ·  │
└───────────────────────────┘        │   scans  (plain FK columns only)   │
                                       └─────────────────┬──────────────────┘
                                                          │ read
┌───────────────────────────┐                            ▼
│  contracts/                │        ┌──────────────────────────────────┐
│  guarantee_policy.md       │  ──►   │      ingest_to_graph.py            │
│  (prose, Legal-signed-off) │  read  │  parse_policy() extracts the rule  │
└───────────────────────────┘        │  from prose -- no hardcoded `if`   │
                                       └─────────────────┬──────────────────┘
                                                          │ write
                                                          ▼
                                       ┌──────────────────────────────────┐
                                       │              Neo4j                 │
                                       │  Customer -[:PLACED]-> Order        │
                                       │  Order -[:SCANNED_AT]-> Scan (x N)  │
                                       │  Scan -[:NEXT]-> Scan (journey)     │
                                       │  Scan -[:AT_LOCATION]-> Hub         │
                                       │  Scan -[:TRIGGERS]-> Guarantee?     │
                                       │     (only if policy rule matches)   │
                                       └──────────────────────────────────┘
```

**Stage 3 — querying the graph:**

```
┌────────────────────────────┐
│        The Question         │
│  "Is my order covered?"     │
└──────────────┬───────────────┘
               ▼
┌────────────────────────────┐
│    LLM Agent (qwen2.5)      │  decides to call trace_order
└──────────────┬───────────────┘
               │ tool call: trace_order(order_id)
               ▼
┌────────────────────────────┐
│  trace_order() — Cypher     │
└──────────────┬───────────────┘
               ▼
┌────────────────────────────┐
│           Neo4j              │  (already built by Stage 1 & 2)
└──────────────┬───────────────┘
               ▼
┌────────────────────────────────────────────────┐
│  "Dispatched -> in transit -> arrived DAMAGED    │
│   at Manchester Hub -> triggers the AtoZ         │
│   Guarantee (policy:4.2). You're covered."       │
└────────────────────────────────────────────────┘
```

---

## Stack

| Layer     | Component                                               |
|-----------|----------------------------------------------------------|
| Source data | DuckDB (`delivery.duckdb`) — flat, disconnected tables |
| Policy    | `contracts/guarantee_policy.md` — prose, not YAML, parsed at ingest time |
| Ingestion | `ingest_to_graph.py` — reads DuckDB + policy, writes Neo4j |
| Data scale | 3 customers, 6 orders, 14 scans, 5 hubs, 2 carriers      |
| Graph DB  | Neo4j 5 (Community, Docker) — local Amazon Neptune equivalent |
| Query     | Cypher (same language family as Neptune's openCypher)    |
| LLM       | Ollama qwen2.5 (Anthropic Claude variant planned)         |
| Transport | OpenAI-compatible tool call                               |
| Domain    | Amazon UK Delivery — Order / Scan / Hub / Guarantee       |

---

## Related

This mirrors the "How does this all fit together?" check and the technical solution design page on the CE Knowledge Base site — same Amazon UK Delivery story, same instance IDs (`Order #48213`, `Scan #9931`, `Hub #204`), running as real code against a real local graph instead of an HTML diagram of AWS Neptune.

---

## Author

```
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────
```
