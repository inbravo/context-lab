# Context — CE Boring Semantic Layer (Amazon UK Delivery)

## What this is
Example 12 in the my-hello-worlds Context Engineering series. A local,
runnable implementation of the Boring Semantic Layer (BSL) architecture
described in Galina Young's three-layer semantic model: KB → YAML/BSL
contract → materialization. Uses the same Amazon UK Delivery domain as
the Knowledge Graph example (Example 11) so both can be compared directly.

## What it shows
- The agent has exactly two tools: `lookup_glossary` (KB layer) and
  `query_metric` (BSL layer). It cannot write SQL or access the database
  directly — metric formulas are locked in YAML files that non-engineers
  can review and approve
- `metric_layer.py` translates a metric YAML contract into a SQL SELECT
  string, then executes it via `ibis.Backend.sql()` — backend-agnostic,
  swappable by changing one `connect()` call
- Governance filters defined in the YAML (`postcode_match = true`,
  `current_status NOT IN ('CANCELLED', 'RETURNED')`) are enforced
  automatically — the agent does not know they exist
- Two governed metrics: EDD (Estimated Delivery Date, v2.1, date
  arithmetic across four integer columns) and order_count (aggregation
  with GROUP BY)
- The BSL translation step is transparent: the CLI prints the generated
  SQL before executing, making the YAML → SQL derivation auditable

## Run order
1. `python3 bootstrap_bsl.py`                    — seed DuckDB (once)
2. `python3 metric_layer.py`                      — list governed metrics
3. `python3 metric_layer.py edd order_id=48213`  — test BSL translation
4. `python3 agent_bsl_ollama.py`                  — run the agent

## Key files
- `glossary/delivery_terms.yaml` — KB layer (DEL/ATT/SAF/NEI/LIT/EDD definitions)
- `metrics/edd.yaml`             — EDD metric contract (v2.1, Priya Sharma, 2026-07-01)
- `metrics/order_count.yaml`     — order count contract (v1.0)
- `code/metric_layer.py`         — BSL translator: YAML → SQL → Ibis → list[dict]
- `code/agent_bsl_ollama.py`     — qwen2.5 agent via Ollama

## Relation to CE stack
Demonstrates Component 3 (Semantic Layer / BSL) and Component 1 (Knowledge
Base / Glossary) of the Context Engineering five-layer stack. The agent
is the consumer; neither layer is modified by the agent at runtime.

## Data
3 customers, 2 carriers, 6 orders, 6 scans. Order 60021 (ATT, Tom, Book)
has `postcode_match = false` — intentionally excluded from EDD by the
governance filter in the metric YAML.
