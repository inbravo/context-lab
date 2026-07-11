# Context — CE Knowledge Graph Demo (Amazon UK Delivery)

## What this is
A local, runnable version of the "How does this all fit together?" gap
from the CE Knowledge Base website's Amazon UK Delivery use case — a small
but real delivery network (3 customers, 6 orders, 14 scans, 5 hubs, 2
carriers) as connected nodes in a real graph database (Neo4j) instead of
a diagram or flat tables.

## What it shows
- A real three-stage context-building pipeline: `bootstrap_source.py`
  seeds flat, disconnected rows into DuckDB; `ingest_to_graph.py` reads
  those rows *and* `contracts/guarantee_policy.md` (prose, not YAML) to
  decide which scans connect to a Guarantee node
- The guarantee rule is parsed out of the policy document's prose at
  runtime — there is no hardcoded `if scan_type == 'DEL'` in
  `ingest_to_graph.py`. Change the policy wording, rerun ingestion, the
  graph changes with zero code edits
- Each order is a real multi-hop journey (dispatch -> depot -> hub),
  chained with `NEXT` edges — not a single scan
- The final scan of each journey uses the same DEL/ATT/SAF/NEI/LIT
  vocabulary as the CE site's Business Glossary component; intermediate
  hops use operational codes (DISPATCHED/IN_TRANSIT)
- A Cypher traversal (`trace_order`) replaces an ad-hoc join per question
- Same Python driver pattern (`neo4j.GraphDatabase.driver`) used to query
  Amazon Neptune's openCypher endpoint — only the connection string differs

## Run order
1. `docker run ... neo4j:5`            — start Neo4j locally (see README)
2. `python bootstrap_source.py`        — seed raw, flat data into DuckDB (once)
3. `python ingest_to_graph.py`         — parse the policy + build the graph
4. `python agent_graph_ollama.py`      — run with Ollama/qwen2.5

## Try these questions
```
python agent_graph_ollama.py
python agent_graph_ollama.py "Is order 51890 covered by a guarantee?"
python agent_graph_ollama.py "What happened to Tom's order 60021?"
python agent_graph_ollama.py "Where is order 71100 right now?"
```

## Stack
| Layer      | Component                                             |
|------------|--------------------------------------------------------|
| Source     | DuckDB (`delivery.duckdb`) — flat, disconnected tables  |
| Policy     | `contracts/guarantee_policy.md` — prose, parsed at ingest time |
| Graph      | Neo4j 5 (Community)                                    |
| Query      | Cypher                                                 |
| LLM        | Ollama qwen2.5                                         |
| Data       | 3 Customers, 6 Orders, 14 Scans, 5 Hubs, 2 Carriers, 1 Guarantee |
| Transport  | OpenAI-compatible tool call                            |

## Series position
Sibling to the existing BFSI series — same CE progression (contract →
semantic model → ontology → knowledge graph → metrics), applied to the
Amazon UK Delivery domain instead of Basel III capital adequacy, and
focused specifically on the Knowledge Graph component this time.

| Domain | Folder | Semantic component |
|--------|--------|---------------------|
| BFSI | `[ce]-[ontology]-[bfsi]-[2026-05]` | Ontology (OWL/SKOS + rdflib) |
| BFSI | `[ce]-[metrics]-[bfsi]-[2026-05]` | Metric layer (dbt MetricFlow) |
| **Amazon Delivery** | **`[ce]-[knowledge-graph]-[amazon-delivery]-[2026-07]`** | **Knowledge Graph (Neo4j)** |
