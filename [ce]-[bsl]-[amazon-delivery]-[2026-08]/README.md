# CE Boring Semantic Layer — Amazon UK Delivery

**Semantic component:** Boring Semantic Layer (BSL) — YAML-governed metric contracts, Ibis translation, DuckDB execution.

---

## What this shows

- **The agent cannot write SQL.** It has two tools: `lookup_glossary` and `query_metric`. Every formula is locked in a YAML file that a non-engineer can read and approve. The agent selects which metric to call and optionally narrows it with a filter — it cannot invent a different formula.
- **Three-layer Galina Young architecture, running locally.** KB layer (`glossary/delivery_terms.yaml`) holds meaning. BSL layer (`metrics/*.yaml`) holds the executable contract. The metric layer (`code/metric_layer.py`) translates YAML to SQL. The agent sits on top without touching either layer directly.
- **Governance filters are enforced automatically.** The EDD metric YAML specifies `postcode_match = true` as a mandatory filter. The agent does not need to know this rule exists. Order 60021 (ATT, postcode mismatch) returns 0 rows from the EDD metric — silently, correctly, by contract.
- **The BSL step is transparent.** Running `python3 metric_layer.py edd order_id=48213` prints the generated SQL before executing it. Every query is derivable from the YAML — auditable without digging into Python.
- **Backend-portable by design.** The translation step in `metric_layer.py` calls `conn.sql()` via Ibis. Swap the `ibis.duckdb.connect()` call for `ibis.postgres.connect()` or `ibis.bigquery.connect()` and the YAML contracts and the agent are unchanged.

**The seeded data:**

| Order | Customer | Product | Status | EDD | EDD covered? |
|-------|----------|---------|--------|-----|--------------|
| 48213 | Sarah (C001) | Trainers | DEL | 2026-07-11 | Yes |
| 51890 | Sarah (C001) | Kettle | DEL | 2026-07-12 | Yes |
| 60021 | Tom (C002) | Book | ATT | — | **No** (postcode mismatch — governance filter) |
| 60022 | Tom (C002) | Headphones | SAF | 2026-07-11 | Yes |
| 60023 | Tom (C002) | Phone Case | NEI | 2026-07-11 | Yes |
| 71100 | Emma (C003) | Blender | LIT | 2026-07-15 | Yes |

---

## File layout

```
[ce]-[bsl]-[amazon-delivery]-[2026-08]/
├── glossary/
│   └── delivery_terms.yaml     # KB layer — meaning, exclusions, interpretation
├── metrics/
│   ├── edd.yaml                # Governed EDD metric contract (v2.1)
│   └── order_count.yaml        # Governed order count contract (v1.0)
└── code/
    ├── bootstrap_bsl.py        # Seeds delivery.duckdb (run once)
    ├── metric_layer.py         # BSL translation engine: YAML → SQL → Ibis
    └── agent_bsl_ollama.py     # Delivery support agent with two governed tools
```

---

## Prerequisites

```bash
pip3 install ibis-framework[duckdb] pyyaml openai
ollama serve && ollama pull qwen2.5
```

---

## Quick start

```bash
cd code/
python3 bootstrap_bsl.py                        # 1. seed DuckDB
python3 metric_layer.py                         # 2. list governed metrics
python3 metric_layer.py edd order_id=48213      # 3. test BSL translation (prints SQL)
python3 agent_bsl_ollama.py                     # 4. run the agent
```

---

## Try these questions

```bash
python3 agent_bsl_ollama.py "What does ATT mean for Tom's delivery?"
python3 agent_bsl_ollama.py "How many orders does Tom have?"
python3 agent_bsl_ollama.py "What is the EDD for order 60021?"
python3 agent_bsl_ollama.py "What is the EDD for order 51890?"
```

**Prove the governance filter works** — order 60021 is ATT with a postcode mismatch. Ask the agent for its EDD. The metric returns 0 rows because the YAML contract mandates `postcode_match = true`. The agent did not enforce this — the contract did.

**Prove the formula is locked** — the agent cannot call `query_metric` with a custom SQL expression. It can only pass a metric name and dimension filters. Open `metrics/edd.yaml`, change `processing_days` to `processing_days * 2`, rerun the agent, and watch the EDD shift — zero code changes.

---

## How BSL translation works

`metric_layer.py` reads the YAML and builds SQL in three passes:

1. **SELECT** — base columns + derived columns (date arithmetic via `INTERVAL` string for DuckDB portability)
2. **WHERE** — governance filters from YAML (always) + caller-supplied dimension filters (validated against the `dimensions:` list in YAML; unknown keys raise an error)
3. **GROUP BY** — only present for aggregation metrics

The resulting SQL string is passed to `conn.sql()` via Ibis. Ibis executes it against the configured backend and returns a DataFrame. `query_metric()` converts that to `list[dict]` — the only representation the agent ever sees.

---

## Connection to the broader CE stack

| Layer | This example |
|-------|--------------|
| Knowledge Base (KB) | `glossary/delivery_terms.yaml` |
| YAML / BSL contract | `metrics/edd.yaml`, `metrics/order_count.yaml` |
| Translation engine | `metric_layer.py` (`_build_sql` → `conn.sql()`) |
| Agent | `agent_bsl_ollama.py` (qwen2.5 via Ollama) |
| Backend | DuckDB (swap to Postgres/BigQuery: one line) |

This is the Galina Young / Boring Semantic Layer pattern: meaning in the KB, formula in the YAML, execution in the translation layer, reasoning in the agent — each layer separate, each reviewable independently.
