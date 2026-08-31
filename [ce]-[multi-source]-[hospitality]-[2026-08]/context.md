# Context — CE Multi-Source Identity Resolution (Hospitality Group)

## What this workbench is

Example 14 of the `my-hello-worlds` learning series.

Demonstrates the **Identity Problem** in context engineering: five operational source systems use four different ID formats for the same real-world entity. An OWL ontology resolves all of them — making cross-system queries possible without hardcoding join logic per question.

Modelled on the real data landscape as shared by AWS:

| System | Vendor | site_id / entity ID |
|---|---|---|
| EPOS | Oracle MICROS | `SITE-LDN-01` |
| WFM | Infor WFM | `GBR_SITE_0001` |
| SAP Sales | SAP S/4HANA | `CC-GBR-001` (cost centre) |
| HR & Payroll | SAP SuccessFactors | `OU-GBR-001` (org unit) |
| Procurement | Coupa (3rd-party) | national catalogue — no site_id |

## Run order

```bash
cd code/
python3 bootstrap_hospitality.py          # 1. seed DuckDB — 5 systems, deliberate ID mismatches
python3 generate_ontology.py              # 2. introspect schemas → build OWL TTL
python3 metric_layer.py                   # 3. list available cross-system metrics
python3 metric_layer.py labour_cost_per_cover SITE-LDN-01   # 4. verify identity resolution
python3 agent_hospitality_ollama.py       # 5. run the Ollama agent (CLI)
python3 dashboard_server.py              # 6. live dashboard — open http://localhost:8765
```

## Key files

| File | Purpose |
|---|---|
| `code/bootstrap_hospitality.py` | Seeds DuckDB with 5 source systems (~800 rows, 30 days) and deliberately mismatched IDs |
| `code/generate_ontology.py` | Introspects DuckDB schemas, builds OWL class hierarchy + identity-bridging properties, writes TTL |
| `ontology/hospitality_ontology.ttl` | Generated OWL ontology — 8 classes, 17+ properties, 13 individuals |
| `code/metric_layer.py` | SPARQL → DuckDB pipeline: resolves IDs before executing cross-system queries |
| `code/agent_hospitality_ollama.py` | qwen2.5 agent with 5 governed metric tools (CLI) |
| `code/dashboard_server.py` | FastAPI live dashboard — fires semantic queries to the LLM/metric layer, renders Chart.js charts from API response |
| `reports/aws-presentation.html` | AWS Architect presentation — 6-section story: data sources, schemas, tech stack, NLP queries, KPIs, architecture |
| `reports/kpi-reports.html` | Interactive KPI report — 3 site tabs × 5 Chart.js charts each, dark/light theme toggle |

## The identity resolution chain

```
Agent asks: "operational summary for SITE-LDN-01"
  ↓
metric_layer.resolve_site("SITE-LDN-01")   ← one call, one SPARQL query
  ↓ SPARQL on rdflib graph
  returns: {
    epos_site_id:     "SITE-LDN-01",
    infor_site_code:  "GBR_SITE_0001",
    sap_cost_center:  "CC-GBR-001",
    sf_org_unit_id:   "OU-GBR-001",
    site_name:        "London Canary Wharf"
  }
  ↓
DuckDB: wfm_shifts WHERE site_id = "GBR_SITE_0001"              ← Infor WFM ID
DuckDB: epos_transactions WHERE site_id = "SITE-LDN-01"         ← EPOS ID
DuckDB: sap_sales WHERE cost_center_code = "CC-GBR-001"         ← SAP S/4HANA cost centre
DuckDB: hr_employees WHERE org_unit_id = "OU-GBR-001"           ← SF org unit
  ↓
All five cross-system metrics computable from a single EPOS site_id
```

Without the ontology, 4 out of 5 metrics return 0 rows and silently fail.

## CE component mapping

| CE Component | Implementation |
|---|---|
| Ontology | `hospitality_ontology.ttl` — 8 OWL classes, 17+ properties (4 site ID bridges + 2 product ID bridges) |
| Semantic Model / VKG | `metric_layer.py` — one SPARQL call resolves all IDs, DuckDB executes per system |
| Metric Layer | `labour_cost_per_cover`, `revenue_by_category`, `food_margin_by_product`, `revenue_per_cover`, `headcount_by_contract` |
| Agent | Ollama qwen2.5, tool-use loop, 5 governed tools |

## AWS equivalent

| Layer | Local | AWS |
|---|---|---|
| Schema discovery | DuckDB DESCRIBE introspection | AWS Glue Crawlers + Glue Data Catalog |
| Ontology construction | rdflib (explicit OWL) | AWS COA MODEL layer (Bedrock embeddings) |
| Identity resolution | SPARQL on rdflib TTL | COA Virtual Knowledge Graph (Ontop/SPARQL) |
| Cross-system join | Python SPARQL → DuckDB SQL | COA Tier-2 agentic SQL |
| Agent | Ollama qwen2.5 | Amazon Bedrock (Claude Sonnet 4.5) |
| Dashboard | FastAPI + Chart.js | Amazon QuickSight / custom React app |

## Dependencies

```bash
pip3 install duckdb rdflib openai fastapi uvicorn
ollama serve && ollama pull qwen2.5
```

## Relationship to other examples

| Example | What it adds |
|---|---|
| Example 11 — `[ce]-[neo4j]-[amazon-delivery]-[2026-08]` | Graph context + Cypher traversal |
| Example 12 — `[ce]-[bsl]-[amazon-delivery]-[2026-08]` | Metric contracts in YAML (no SQL by agent) |
| Example 13 — `[ce]-[semantica]-[amazon-delivery]-[2026-08]` | In-memory graph, provenance via `record_decision()` |
| **Example 14 — this workbench** | Multi-source identity resolution via OWL ontology + SPARQL |
