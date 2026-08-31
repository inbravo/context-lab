# CE Multi-Source Identity Resolution — Hospitality Group

**Semantic component:** Multi-source ontology with identity resolution — OWL ontology built from five heterogeneous source systems, SPARQL-powered cross-system joins, Ollama agent, live FastAPI dashboard.

**The new CE concept:** The Identity Problem. Every source system uses a different ID for the same real-world entity. An ontology resolves this — making cross-system queries possible without writing custom join logic per question.

---

## What is the Identity Resolution stage?

It is the step where you answer: *"What is the same real-world thing called in each source system?"*

Every enterprise system names the same physical entity differently — built by a different vendor, at a different time, with no shared key design:

```
London Canary Wharf site
  Oracle MICROS EPOS   →  SITE-LDN-01
  Infor WFM            →  GBR_SITE_0001
  SAP S/4HANA          →  CC-GBR-001
  SAP SuccessFactors   →  OU-GBR-001
```

Without resolving these, a JOIN across any two systems returns 0 rows — silently. There is no error; the query just finds no match.

**What it does:** Builds a canonical reference — one authoritative OWL individual per real-world entity — and attaches all system-specific IDs as datatype properties. One SPARQL query against that individual returns all four IDs at once. DuckDB then queries each system using the ID that system actually understands.

**Where it sits in the pipeline:**

```
Raw data in source systems
        ↓
  Identity Resolution     ← this stage  (OWL ontology / SPARQL)
        ↓
  Cross-system queries now possible
        ↓
  Metric layer / Agent
```

It runs *before* any analytical query. It is a prerequisite, not an optimisation — skip it and multi-system metrics do not exist.

**AWS COA equivalent:** The same stage is the **Virtual Knowledge Graph (VKG)** — built by the MODEL layer using Bedrock embeddings to align schemas across systems, then exposed as a SPARQL endpoint via Ontop on Amazon Neptune. The SPARQL query is identical; the construction is automated rather than hand-coded.

---

## The problem this demonstrates

A UK Hospitality Group (B&I catering) runs five operational systems. None share a key:

| System | Vendor | site_id / entity ID format | Rows |
|---|---|---|---|
| EPOS (point-of-sale) | Oracle MICROS | `SITE-LDN-01` | ~500 |
| WFM (workforce mgmt) | Infor WFM | `GBR_SITE_0001` | ~120 |
| SAP Sales & Invoicing | SAP S/4HANA | `CC-GBR-001` (cost centre) | ~150 |
| HR & Payroll | SAP SuccessFactors | `OU-GBR-001` (org unit) | ~45 |
| Procurement | Coupa (3rd-party) | national catalogue — no site_id | ~300k products, ~20k suppliers/market |

> Real scale: up to 40 EPOS providers per market, multiple WFM systems per country.

Four completely different site ID formats for the same three physical sites. Without resolving these identities:
- *"What is the labour cost per cover?"* — Infor WFM uses `GBR_SITE_0001`, EPOS uses `SITE-LDN-01`. No JOIN.
- *"What is the SAP revenue per cover?"* — SAP S/4HANA uses `CC-GBR-001`. No JOIN.
- *"What is the headcount breakdown?"* — SuccessFactors uses `OU-GBR-001`. No JOIN.

**The ontology resolves all four formats simultaneously.** One SPARQL query against the OWL graph returns all system IDs for a canonical site. DuckDB can then join across any combination of systems.

---

## Local stack vs AWS production stack

| Layer | This example (local) | AWS production stack |
|---|---|---|
| **Source data** | DuckDB — 5 tables, 5 systems, ~800 rows | S3 (CSV/Parquet) — 5 systems, millions of rows |
| **Schema discovery** | `generate_ontology.py` — DuckDB schema introspection | AWS Glue Data Catalog — crawlers auto-register schemas |
| **Ontology construction** | rdflib — programmatic OWL class hierarchy + identity properties | AWS Context Ontology Accelerator (COA) MODEL layer — automated ontology induction via Bedrock + embedding similarity |
| **Identity resolution** | SPARQL on rdflib graph (`hosp:eposSiteId` → `hosp:inforSiteCode`) | COA Virtual Knowledge Graph (VKG / Ontop) — SPARQL endpoint over all sources |
| **Cross-system join** | Python: SPARQL resolves IDs → DuckDB executes per-system queries | COA Tier-2 agentic SQL — VKG compiles SPARQL to federated SQL |
| **Agent** | Ollama qwen2.5 | Amazon Bedrock (Claude Sonnet 4.5) |
| **Agent tools surface** | Python function calls in `agent_hospitality_ollama.py` | COA MCP server — agent discovers tools automatically |
| **Infrastructure** | Laptop, no cloud required | S3 + Glue + Neptune + OpenSearch Serverless + Bedrock + CDK |
| **Ontology storage** | `hospitality_ontology.ttl` (Turtle file) | Amazon Neptune (property graph + RDF) |
| **Cost** | £0 | ~$900–1,200/month idle (Neptune + OpenSearch Serverless) |
| **Setup time** | 5 minutes (`pip install`, run 3 scripts) | 1–2 week engineering sprint |

**The concept is identical.** The ontology resolves identity fragmentation across source systems. What this example makes explicit and hand-crafted, AWS COA automates via Bedrock embeddings and inference.

---

## What the ontology does

`generate_ontology.py` introspects all five DuckDB schemas and builds a Turtle OWL file with **8 classes, 17+ properties, and 13 individuals**.

The key properties are the **identity bridges** — four site ID formats on every canonical site individual:

```turtle
inst:site/gbr-lnd-01
    a hosp:HospitalitySite ;
    hosp:siteName         "London Canary Wharf" ;
    hosp:eposSiteId       "SITE-LDN-01" ;    # ← Oracle MICROS EPOS (hyphens, prefix)
    hosp:inforSiteCode    "GBR_SITE_0001" ;  # ← Infor WFM (country-prefix, underscore)
    hosp:sapCostCenter    "CC-GBR-001" ;     # ← SAP S/4HANA (cost centre code)
    hosp:sfOrgUnitId      "OU-GBR-001" .     # ← SAP SuccessFactors (org unit)

inst:product/prod_bev_001
    a hosp:Product ;
    hosp:eposItemId         "EPOS-LATTE" ;     # ← Oracle MICROS item code
    hosp:procProductId      "PROD-BEV-001" ;   # ← Coupa catalogue SKU
    hosp:contractedPriceGBP 2.10 .
```

One SPARQL query resolves **all four system IDs** simultaneously before any DuckDB query runs:

```sparql
PREFIX hosp: <http://hospitality.example.org/ontology#>
SELECT ?epos_id ?infor_code ?sap_cc ?sf_org ?site_name WHERE {
    ?site hosp:eposSiteId    ?epos_id ;
          hosp:inforSiteCode ?infor_code ;
          hosp:sapCostCenter ?sap_cc ;
          hosp:sfOrgUnitId   ?sf_org ;
          hosp:siteName      ?site_name .
    FILTER(?epos_id = "SITE-LDN-01")
}
→ infor_code="GBR_SITE_0001"  sap_cc="CC-GBR-001"  sf_org="OU-GBR-001"  site_name="London Canary Wharf"
```

In AWS COA this SPARQL runs against the Virtual Knowledge Graph (Ontop). Here it runs against rdflib. Same query, same result.

---

## File layout

```
[ce]-[multi-source]-[hospitality]-[2026-08]/
├── ontology/
│   └── hospitality_ontology.ttl    — generated OWL ontology (Turtle format)
├── code/
│   ├── bootstrap_hospitality.py    — seeds DuckDB with 5 source systems + ID mismatches
│   ├── generate_ontology.py        — introspects schemas, builds OWL TTL via rdflib
│   ├── metric_layer.py             — cross-system metrics: SPARQL resolves IDs → DuckDB joins
│   ├── agent_hospitality_ollama.py — qwen2.5 agent with 5 governed metric tools (CLI)
│   └── dashboard_server.py         — FastAPI live dashboard, http://localhost:8765
└── reports/
    ├── aws-presentation.html       — AWS Architect presentation (data sources, tech stack, demo)
    └── kpi-reports.html            — Interactive KPI report with Chart.js, 3 site tabs
```

---

## Prerequisites

```bash
pip3 install duckdb rdflib openai fastapi uvicorn
ollama serve && ollama pull qwen2.5
```

---

## Quick start

```bash
cd code/
python3 bootstrap_hospitality.py          # 1. seed DuckDB (5 systems, deliberate ID mismatches)
python3 generate_ontology.py              # 2. build OWL ontology with identity bridges
python3 metric_layer.py                   # 3. list cross-system metrics
python3 metric_layer.py labour_cost_per_cover SITE-LDN-01   # 4. test identity resolution
python3 agent_hospitality_ollama.py       # 5. run the agent (CLI)
python3 dashboard_server.py              # 6. live dashboard — open http://localhost:8765
```

---

## Try these questions

```bash
python3 agent_hospitality_ollama.py "What is the labour cost per cover at SITE-LDN-01?"
python3 agent_hospitality_ollama.py "Which categories drive the most revenue at SITE-MAN-01?"
python3 agent_hospitality_ollama.py "What are the food margins at SITE-LDN-02?"
python3 agent_hospitality_ollama.py "What is the SAP revenue per cover at SITE-LDN-01?"
python3 agent_hospitality_ollama.py "What is the headcount breakdown at SITE-MAN-01?"
python3 agent_hospitality_ollama.py "Give me a full operational summary for SITE-LDN-01."
```

---

## Prove the identity resolution is doing real work

Run any metric — the CLI output prints all four resolved IDs:

```
Metric  : revenue_per_cover
Site    : SITE-LDN-01
  EPOS (Oracle MICROS) : SITE-LDN-01
  WFM  (Infor)         : GBR_SITE_0001    ← Infor WFM's ID for the same site
  SAP  (S/4HANA)       : CC-GBR-001       ← SAP cost centre for the same site
  SF   (SuccessFactors): OU-GBR-001       ← SF org unit for the same site
```

To see what breaks without resolution: open `metric_layer.py`, comment out `resolve_site()` and hardcode `infor_site_code = epos_site_id`. The WFM query returns 0 rows (`GBR_SITE_0001` ≠ `SITE-LDN-01`), the SAP query returns 0 rows (`CC-GBR-001` ≠ `SITE-LDN-01`), the SF query returns 0 rows. All cross-system metrics silently fail. The ontology is load-bearing.

---

## Inspect the generated ontology

```bash
python3 generate_ontology.py --show-sparql   # prints the resolution SPARQL query
cat ../ontology/hospitality_ontology.ttl     # read the full OWL Turtle file
```

The TTL is human-readable. An ontologist, data steward, or architect can review and amend it directly — the same way `guarantee_policy.md` was the reviewable artefact in Examples 11–13.

---

## Open source tools used

| Tool | Role | AWS COA equivalent |
|---|---|---|
| **rdflib** (Python) | Parse, query, and build OWL/Turtle graphs; run SPARQL | Amazon Neptune + Ontop VKG |
| **DuckDB** | Execute SQL against each source system after identity resolution | Amazon Athena / Redshift |
| **Ollama + qwen2.5** | Local LLM for the agent loop | Amazon Bedrock (Claude Sonnet 4.5) |
| **FastAPI + uvicorn** | Live dashboard API | AWS Lambda / ECS |
| **Chart.js** | Browser-side chart rendering | Amazon QuickSight |

**morph-KGC** (not used here but mentioned for completeness): an open source RDF mapping engine that generates RDF individuals from relational data via YARRRML/RML mappings — the open source equivalent of COA's SCAN layer. Production teams building a fully automated ontology generation pipeline would replace `generate_ontology.py` with morph-KGC mappings.

---

## Connection to the CE stack

| CE Component | This example |
|---|---|
| Data Contract | Implicit in DuckDB schemas (column names, types) across 5 systems |
| Ontology | `hospitality_ontology.ttl` — 8 OWL classes, 17+ properties, identity bridges for all 4 site ID formats |
| Semantic Model / VKG | `metric_layer.py` — one SPARQL call resolves all IDs, DuckDB executes per system |
| Metric Layer | `labour_cost_per_cover`, `revenue_by_category`, `food_margin_by_product`, `revenue_per_cover`, `headcount_by_contract` |
| Agent | qwen2.5 — 5 governed tools, cannot query systems directly |

This is the pattern that sits beneath a production data mesh: the ontology is the durable asset. Agents, BI tools, and ML pipelines all consume it. The source system IDs change over time; the canonical ontology individuals do not.
