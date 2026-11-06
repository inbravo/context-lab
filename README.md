# This lab is my place to keep the Context Engineering stuff
Minimal, working examples across the agentic AI stack — MCP servers, agent frameworks, context pipelines, and the scaffolding nobody documents properly.

---

## Repository Structure

This repository contains **fifteen examples** organized in separate folders, each introducing a new semantic component in the Context Engineering ladder:

### 📂 Directory Listing

| # | Folder | Semantic Component | Description |
|---|---|---|---|
| 1 | [[ce]-[hello-world]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bhello-world%5D-%5B2026-05%5D) | Hand-written YAML contract | CE baseline — agent reads a data contract and writes its own SQL |
| 2 | [[ce]-[slayer]-[hello-world]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bslayer%5D-%5Bhello-world%5D-%5B2026-05%5D) | Semantic model — generic | Agent queries a live semantic layer via REST. No SQL written by the agent |
| 3 | [[ce]-[slayer]-[bfsi]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bslayer%5D-%5Bbfsi%5D-%5B2026-05%5D) | Semantic model — BFSI domain | Real datasource registered into a semantic layer. BFSI capital adequacy use case |
| 4 | [[ce]-[odcs]-[bfsi]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bodcs%5D-%5Bbfsi%5D-%5B2026-05%5D) | Formal ODCS contract (Bitol 0.9.3) | Upgrades the YAML contract to a governed standard — adds ownership, quality checks, SLA, and freshness metadata |
| 5 | [[ce]-[odps]-[trade]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bodps%5D-%5Btrade%5D-%5B2026-05%5D) | Data product (ODPS 2.0) | Steps up from table governance to product governance — ports, use cases, SLAs. New domain: Trade Finance |
| 6 | [[ce]-[slayer]-[mcp]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bslayer%5D-%5Bmcp%5D-%5B2026-05%5D) | Semantic layer via MCP — generic | Transport upgrade — same semantic layer, now accessed via MCP stdio. Claude Desktop is the agent. No Python |
| 7 | [[ce]-[slayer]-[mcp]-[bfsi]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bslayer%5D-%5Bmcp%5D-%5Bbfsi%5D-%5B2026-05%5D) | Semantic layer via MCP — BFSI | Same Basel III/IV capital adequacy data as Example 3, now over MCP. Zero agent code |
| 8 | [[ce]-[ontology]-[bfsi]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bontology%5D-%5Bbfsi%5D-%5B2026-05%5D) | OWL/SKOS domain ontology | 15-class BFSI ontology parsed by rdflib. Agent understands concept hierarchy, Basel III articles, and formulas — domain-aware, not just schema-aware |
| 9 | [[ce]-[metrics]-[bfsi]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bmetrics%5D-%5Bbfsi%5D-%5B2026-05%5D) | dbt Metric Layer (MetricFlow) | 5 named governed metrics — cet1_ratio, buffer_headroom, rwa, cet1_capital, combined_buffer. Agent calls mf query, never writes SQL |
| 10 | [[ce]-[agentic]-[full-stack]-[2026-05]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bagentic%5D-%5Bfull-stack%5D-%5B2026-05%5D) | Full stack comparison | One question through all 9 context layers. Scored side-by-side table proves CE has a measurable effect on answer quality |
| 11 | [[ce]-[knowledge-graph]-[amazon-delivery]-[2026-07]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bknowledge-graph%5D-%5Bamazon-delivery%5D-%5B2026-07%5D) | Knowledge Graph — Neo4j, new domain | Real three-stage context-building pipeline: raw DuckDB rows + a prose policy document are ingested into a Neo4j graph. New domain: Amazon UK Delivery (order tracking, A-to-Z Guarantee) — local, open-source equivalent of Amazon Neptune |
| 12 | [[ce]-[bsl]-[amazon-delivery]-[2026-08]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bbsl%5D-%5Bamazon-delivery%5D-%5B2026-08%5D) | Boring Semantic Layer (BSL) — YAML metric contracts | YAML-governed metric contracts translated to SQL by Ibis. Agent has two tools (glossary + query_metric) and cannot write SQL. Same Amazon UK Delivery domain as Example 11 — compare the graph approach vs. the metric contract approach |
| 13 | [[ce]-[semantica]-[amazon-delivery]-[2026-08]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bsemantica%5D-%5Bamazon-delivery%5D-%5B2026-08%5D) | Semantica ContextGraph — same domain, no Docker | Direct rebuild of Example 11 using Semantica instead of Neo4j. No Cypher, no Docker. Adds W3C PROV-O provenance via record_decision() — every guarantee trigger has a full audit record |
| 14 | [[ce]-[multi-source]-[hospitality]-[2026-08]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bmulti-source%5D-%5Bhospitality%5D-%5B2026-08%5D) | OWL ontology — multi-source identity resolution | Three source systems with deliberately mismatched IDs. OWL ontology + SPARQL resolve identities before any cross-system DuckDB join. New domain: UK Hospitality Group (B&I catering). Local equivalent of AWS COA + Neptune |
| 15 | [[ce]-[det]-[fabric-ollama]-[2026-11]](https://github.com/inbravo/my-hello-worlds/tree/main/%5Bce%5D-%5Bdet%5D-%5Bfabric-ollama%5D-%5B2026-11%5D) | Decision Economics Toolkit — Azure Fabric → Ollama | Agent governance layer: classify every query by complexity, route to cheapest capable model, compress context to class budget, run a quality probe on the answer, and record every token against a confirmed business outcome. Local Ollama proof-of-concept for the DET framework built for Microsoft Fabric |

---

## Semantics and Context Engineering

If you have understood the purpose of the Semantic layer, Context Engineering follows naturally — it is the discipline of designing, structuring, and governing the business context delivered to the LLM, at the right time and in the right format, so it reasons and acts correctly on your data. CE is not a one-time activity. The outcome it continuously produces and maintains is the semantic layer itself — a living, structured representation of the business meaning of your data. Put simply: **good Context Engineering produces good semantics.**

Semantic is a broader term including these components:

---

| # | Component | What it captures | Examples |
|---|---|---|---|
| 1 | **Data Contract** | Schema, ownership, SLAs, freshness, lineage | YAML contracts (Databricks/Snowflake), Bitol ODCS |
| 2 | **Ontology** | Concepts, relationships, classifications in a domain | FIBO (banking), SNOMED (healthcare), OWL/RDF, OBML |
| 3 | **Semantic Model** | Business definitions mapped to physical data | LookML, MetricFlow, Cube schema, SLayer |
| 4 | **Knowledge Graph** | Entities, relationships, traversable connections | Neo4j, AWS Neptune, Google KG |
| 5 | **Metric Layer** | Named, governed business metrics with formulas | Databricks Metric views, dbt Metrics, Cube measures, AtScale |

---

**How they relate:**

- A **data contract** says: *"this table exists, has these columns, owned by this team, refreshed daily"*
- An **ontology** says: *"CET1 Capital is a subclass of Regulatory Capital, which is governed by Basel III"*
- A **semantic model** says: *"cet1_ratio_pct = CET1 Capital ÷ RWA × 100, display as percentage"*
- A **knowledge graph** says: *"BANK_HOLDCO → holds → BANK_SUBSIDIARY → reports → CET1 position"*
- A **metric layer** says: *"CET1 Headroom = cet1_ratio_pct − combined_buffer, flagged if < 1pp"*

The principle is simple — **the better the CE, the better the semantics, and the more trustworthy the AI.**

---

## 🎯 Overview of Examples

### Example 1: Hand-written YAML Data Contract

**Semantic component:** Data Contract (Component 1 — informal)

**What it shows:**
- An AI agent reads a hand-written YAML data contract describing a bank's capital position, writes its own SQL, and answers a Basel III question. No hardcoded prompts. No vector store. No fine-tuning.
- The friction of writing and maintaining SQL against a changing regulatory schema is replaced by a structured contract and a two-turn agent loop.

**Quick Start:**
```bash
git clone https://github.com/inbravo/my-hello-worlds
cd my-hello-worlds/[ce]-[hello-world]-[2026-05]/code
pip install duckdb structlog pyyaml anthropic
python bootstrap.py && python agent_ollama.py
```

**Options:** Anthropic API (`agent.py`) or Ollama (`agent_ollama.py`)

---

### Example 2: Semantic Layer — Generic (SLayer + Jaffle Shop)

**Semantic component:** Semantic Model (Component 3 — generic dataset)

**What it shows:**
- Agent queries a live SLayer semantic layer via REST API. Discovers the data model at startup. Never writes SQL — the semantic layer compiles it.
- Uses the built-in Jaffle Shop demo dataset (orders, stores, customers).

**Quick Start:**
```bash
pip install 'motley-slayer[all]'
slayer serve --demo
cd my-hello-worlds/[ce]-[slayer]-[hello-world]-[2026-05]/code
pip install openai requests structlog
ollama serve && ollama pull qwen2.5
python agent_slayer_ollama_hw.py
```

**Options:** Anthropic API (`agent_slayer_hw.py`) or Ollama (`agent_slayer_ollama_hw.py`)

---

### Example 3: Semantic Layer — BFSI Domain (SLayer + Capital Position)

**Semantic component:** Semantic Model (Component 3 — domain-specific)

**What it shows:**
- Registers a real DuckDB datasource into SLayer and runs a capital adequacy agent against it.
- The agent discovers the `capital_position` model at runtime and answers CET1 / buffer headroom questions. SLayer logs the SQL it compiled — the observable trace.

**Quick Start:**
```bash
pip install 'motley-slayer[all]'
slayer serve --demo
cd my-hello-worlds/[ce]-[slayer]-[bfsi]-[2026-05]/code
pip install openai requests duckdb structlog
ollama serve && ollama pull qwen2.5
python bootstrap_bfsi.py && python setup_bfsi.py && python agent_slayer_bfsi_ollama.py
```

**Options:** Anthropic API (`agent_slayer_bfsi.py`) or Ollama (`agent_slayer_bfsi_ollama.py`)

---

### Example 4: Formal ODCS Data Contract — Bitol 0.9.3

**Semantic component:** Data Contract (Component 1 — governed, standard-compliant)

**What it shows:**
- Upgrades the hand-written YAML from Example 1 to a formal **Bitol/ACRYL ODCS 0.9.3** contract — same concept, done the right way.
- The contract adds ownership, quality checks (SodaCL), freshness SLAs, usage terms, and retention policy. The agent answers both data and governance questions from the same contract.
- Example 1 answers: *"What is our CET1 ratio?"* Example 4 answers: *"What is our CET1 ratio — is this data certified, how fresh is it, and who owns it?"*

**Quick Start:**
```bash
cd my-hello-worlds/[ce]-[odcs]-[bfsi]-[2026-05]/code
pip install openai duckdb pyyaml structlog
ollama serve && ollama pull qwen2.5
python bootstrap_odcs.py && python agent_odcs_ollama.py
```

**Options:** Anthropic API (`agent_odcs.py`) or Ollama (`agent_odcs_ollama.py`)

---

### Example 5: Data Product — ODPS 2.0 (Trade Finance)

**Semantic component:** Data Product (above Component 1 — product governance)

**What it shows:**
- Steps up from table-level governance (ODCS) to **product-level governance** using the Open Data Product Standard (ODPS 2.0).
- The agent reads a full product definition — input ports, output ports, use cases, SLAs, quality rules, and ownership — and answers exposure, settlement risk, and governance questions.
- New domain: **Trade Finance** (counterparty exposure, settlement risk, credit concentration) — shows CE is not BFSI capital adequacy-specific.
- ODPS is to data products what OpenAPI is to REST APIs — a standard spec that makes data products discoverable, understandable, and governable.

**Quick Start:**
```bash
cd my-hello-worlds/[ce]-[odps]-[trade]-[2026-05]/code
pip install openai duckdb pyyaml structlog
ollama serve && ollama pull qwen2.5
python bootstrap_odps.py && python agent_odps_ollama.py
```

**Options:** Anthropic API (`agent_odps.py`) or Ollama (`agent_odps_ollama.py`)

---

### Example 6: Semantic Layer via MCP — Generic (Jaffle Shop)

**Semantic component:** Semantic Model (Component 3) via MCP transport

**What it shows:**
- The same semantic layer from Examples 2 & 3 — but the transport changes from REST to **MCP stdio**. No Python agent code. Claude Desktop connects directly and auto-discovers the Jaffle Shop model.
- Demonstrates that the semantic context is transport-independent. You switch from REST to MCP; the business definitions stay the same.

**Quick Start:**
```bash
# No Python agent needed — Claude Desktop IS the agent
# Add to Claude Desktop config:
{
  "mcpServers": {
    "slayer": {
      "command": "uvx",
      "args": ["--from", "motley-slayer[all]", "slayer", "mcp", "--demo"]
    }
  }
}
# Restart Claude Desktop, then ask: "What are total orders by store?"
```

**Options:** Claude Desktop (Jaffle Shop demo data) or Claude Code CLI (`claude mcp add slayer -- uvx --from 'motley-slayer[all]' slayer mcp --demo`)

---

### Example 7: Semantic Layer via MCP — BFSI (Capital Adequacy)

**Semantic component:** Semantic Model (Component 3) via MCP — BFSI domain

**What it shows:**
- The same Basel III/IV capital adequacy data from Example 3 — but accessed via MCP, not the REST API.
- No Python agent. No tool definitions. Claude Desktop is the agent. SLayer MCP auto-discovers the `capital_position` model and Claude answers CET1 and buffer headroom questions directly.
- The transport switches from HTTP REST to MCP stdio. The semantic context — same data, same model, same business meaning — does not change.

**Quick Start:**
```bash
cd my-hello-worlds/[ce]-[slayer]-[mcp]-[bfsi]-[2026-05]/code
pip install requests duckdb
python bootstrap_mcp_bfsi.py
uvx --from 'motley-slayer[all]' slayer serve   # register only
python setup_mcp_bfsi.py                        # then Ctrl+C to stop serve
# Add config/claude_desktop_bfsi.json to Claude Desktop, restart, and ask:
# "What is our current CET1 ratio and buffer headroom?"
```

**Also works in Claude Code:**
```bash
claude mcp add slayer -- uvx --from 'motley-slayer[all]' slayer mcp
```

---

### Example 8: OWL/SKOS Domain Ontology — BFSI

**Semantic component:** Ontology (Component 2 — OWL/SKOS + OBML-style annotations)

**What it shows:**
- A 15-class BFSI capital adequacy ontology in Turtle format, parsed at runtime by `rdflib`. The agent's tool description is built dynamically from the ontology — not hand-crafted.
- The agent understands the full concept hierarchy (`CET1Capital ⊂ Tier1Capital ⊂ RegulatoryCapital`), Basel III article references, formulas, minimum requirements, and OBML-style column-to-concept mappings.
- Previous examples made the agent schema-aware. This makes it **domain-aware** — it can answer regulatory and conceptual questions without querying the database at all.

**Quick Start:**
```bash
cd my-hello-worlds/[ce]-[ontology]-[bfsi]-[2026-05]/code
pip install duckdb rdflib openai structlog
ollama serve && ollama pull qwen2.5
python3 bootstrap_ontology.py && python3 agent_ontology_ollama.py
```

**Try domain questions:**
```
python3 agent_ontology_ollama.py "Is CET1 Capital a subset of Tier 1 Capital?"
python3 agent_ontology_ollama.py "What regulation governs the combined buffer requirement?"
python3 agent_ontology_ollama.py "What is our CET1 ratio vs the Basel III minimum?"
```

**Options:** Anthropic API (`agent_ontology.py`) or Ollama (`agent_ontology_ollama.py`)

---

## 📈 Learning Progression

Run the examples in this order for the clearest learning curve:

| Step | Example | What you learn |
|---|---|---|
| 1 | Example 1 — YAML contract | How a data contract gives an LLM context to write its own SQL. The CE baseline. |
| 2 | Example 2 — SLayer (generic) | How a semantic layer works. Agent queries via REST, never writes SQL. |
| 3 | Example 3 — SLayer (BFSI) | How to register a real datasource into a semantic layer and run a domain agent. |
| 4 | Example 4 — ODCS (Bitol) | How a governed, standard-compliant contract adds ownership, quality, and SLA context. |
| 5 | Example 5 — ODPS (Trade Finance) | How a data product definition governs at the capability level — ports, use cases, pricing. |
| 6 | Example 6 — SLayer MCP (Jaffle Shop) | How MCP replaces the REST agent loop entirely. Claude Desktop becomes the agent. |
| 7 | Example 7 — SLayer MCP (BFSI) | Same semantic model, same data — zero Python. MCP transport changes everything about the client, nothing about the semantics. |
| 8 | Example 8 — OWL/SKOS Ontology | How a formal domain ontology makes the agent domain-aware — it understands Basel III concept hierarchy, formulas, and regulatory articles, not just column names. |
| 9 | Example 9 — dbt Metric Layer | How named, governed business metrics (MetricFlow) replace raw SQL — the metric layer enforces the formula, the agent just asks by name. |
| 10 | Example 10 — Full Stack Comparison | One question, five agents, scored — CE's measurable payoff. The capstone. |
| 11 | Example 11 — Knowledge Graph (Neo4j) | How a real ingestion pipeline builds a graph from raw data + a prose policy document — and how editing the policy's wording, not the code, changes what the graph connects. |
| 12 | Example 12 — Boring Semantic Layer (BSL) | How YAML metric contracts lock business formulas so no agent can rewrite them — the metric layer translates YAML to SQL, the agent never sees either. |
| 13 | Example 13 — Semantica ContextGraph | Same delivery graph as Example 11, rebuilt with Semantica — no Docker, Python API instead of Cypher, and a W3C PROV-O audit record for every guarantee decision. |
| 14 | Example 14 — OWL Identity Resolution (Hospitality) | How an OWL ontology resolves cross-system ID mismatches — SPARQL bridges three systems before any DuckDB join is possible. Local equivalent of AWS Context Ontology Accelerator + Neptune. |
| 15 | Example 15 — Decision Economics Toolkit (DET) | How to govern every LLM call as a capital allocation — classify complexity, route to the cheapest capable model, compress context, run a quality probe, and record cost per confirmed business outcome. The agent governance layer above the semantic layer. |

---

## 🏗️ Architecture

### Example 1: Hand-written YAML Contract

```
┌──────────────────┐
│  YAML Contract   │  (informal, hand-written)
│  table + columns │
│  + description   │
└──────┬───────────┘
       │  injected into tool description
       ▼
┌──────────────────┐        ┌─────────────┐
│   LLM Agent      │◄──────►│   DuckDB    │
│  (generates SQL) │        │ (executes)  │
└──────┬───────────┘        └─────────────┘
       │
       ▼
 ┌─────────────────┐
 │  Business Answer │
 └─────────────────┘
```

---

### Example 2 & 3: Semantic Layer (SLayer REST API)

```
┌──────────────────┐
│  Business Query  │
│   (plain text)   │
└──────┬───────────┘
       ▼
┌──────────────────┐
│   LLM Agent      │  discovers model at startup via GET /models
└──────┬───────────┘
       ▼
┌──────────────────────────┐
│   SLayer Semantic Model  │  POST /query (REST / MCP)
│  measures, dimensions    │
└──────┬───────────────────┘
       ▼
┌──────────────────┐        ┌─────────────┐
│  Semantic Layer  │◄──────►│   DuckDB    │
│  (compiles SQL)  │        │             │
└──────┬───────────┘        └─────────────┘
       ▼
 ┌──────────────────┐
 │  Governed Answer  │  + SQL trace logged
 └──────────────────┘
```

**Key difference from Example 1:** The agent never writes SQL. The semantic layer compiles it — more controlled, auditable, and reliable.

---

### Example 4: ODCS Formal Data Contract (Bitol 0.9.3)

```
┌─────────────────────────────────────────────────┐
│            ODCS Contract (Bitol 0.9.3)          │
│  ┌───────────┐  ┌─────────┐  ┌───────────────┐  │
│  │   info    │  │ models  │  │    quality    │  │
│  │  owner    │  │ fields  │  │  SodaCL checks│  │
│  │  status   │  │ descrip.│  │               │  │
│  └───────────┘  └─────────┘  └───────────────┘  │
│  ┌───────────┐  ┌─────────┐  ┌───────────────┐  │
│  │  servers  │  │  terms  │  │ servicelevels │  │
│  │  (DuckDB) │  │  usage  │  │ SLA/freshness │  │
│  └───────────┘  └─────────┘  └───────────────┘  │
└───────────────────────┬─────────────────────────┘
                        │  all sections injected into tool description
                        ▼
         ┌──────────────────────────┐
         │        LLM Agent         │
         │  (data + governance Q's) │
         └──────────┬───────────────┘
                    │  generates SQL
                    ▼
         ┌──────────────────┐
         │     DuckDB       │
         └──────────┬───────┘
                    ▼
         ┌──────────────────────────────────────┐
         │  "CET1 is 14.83%. Data is active,    │
         │   owned by Treasury Risk Team,        │
         │   refreshed within 5 days of QE."    │
         └──────────────────────────────────────┘
```

---

### Example 5: ODPS Data Product (2.0)

```
┌──────────────────────────────────────────────────────┐
│              ODPS Product Definition (2.0)           │
│  ┌──────────────┐  ┌───────────┐  ┌───────────────┐  │
│  │    product   │  │ inputPorts│  │ outputPorts   │  │
│  │  name, domain│  │  source   │  │ DuckDB table  │  │
│  │  owner, SLA  │  │  cadence  │  │ + columns     │  │
│  └──────────────┘  └───────────┘  └───────────────┘  │
│  ┌──────────────┐  ┌───────────┐  ┌───────────────┐  │
│  │   useCases   │  │  quality  │  │    terms      │  │
│  │ approved Q's │  │  checks   │  │ usage/pricing │  │
│  └──────────────┘  └───────────┘  └───────────────┘  │
└──────────────────────────┬───────────────────────────┘
                           │  product-aware tool description
                           ▼
            ┌──────────────────────────┐
            │        LLM Agent         │
            │ (data + product + use    │
            │  case questions)         │
            └──────────┬───────────────┘
                       │  generates SQL
                       ▼
            ┌──────────────────┐
            │     DuckDB       │
            └──────────┬───────┘
                       ▼
            ┌──────────────────────────────────────┐
            │  "Goldman Sachs exposure: $790M.      │
            │   3 trades settle within 30 days.     │
            │   Data owned by Trade Finance Risk,   │
            │   updated T+1 by 08:00 GMT."          │
            └──────────────────────────────────────┘
```

**Key difference from Example 4:** ODCS governs a table. ODPS governs a business capability — the agent understands what problem the data product is built to solve, for whom, and under what SLA.

---

### Examples 6 & 7: Semantic Layer via MCP

```
┌──────────────────────────────────────────┐
│           Claude Desktop / Claude Code   │
│  (LLM + MCP client — no Python needed)  │
└──────────────────┬───────────────────────┘
                   │  MCP stdio
                   │  auto-discovers model
                   ▼
┌──────────────────────────────────────────┐
│        SLayer MCP Server                 │
│   uvx ... slayer mcp [--demo]            │
│                                          │
│   Reads: ~/.local/share/slayer           │
│   Finds: datasource + model              │
│   Exposes: model as MCP tools            │
└──────────────────┬───────────────────────┘
                   │  compiles SQL
                   ▼
┌──────────────────────────────────────────┐
│   DuckDB                                 │
│   (Jaffle Shop or capital_bfsi.duckdb)   │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  Answer in Claude Desktop chat           │
│  No Python. No agent loop. No tools.     │
└──────────────────────────────────────────┘
```

**How SLayer storage is shared:**
```
slayer serve  ──writes──►  ~/.local/share/slayer/  ◄──reads──  slayer mcp
```
Run `setup_mcp_bfsi.py` once against the REST server — the MCP server picks up the datasource automatically. No further config needed.

**Key difference from Examples 2 & 3:** REST requires a Python agent with an explicit tool loop. MCP exposes the same semantic model as native Claude tools — Claude Desktop calls them directly. Zero agent code.

---

### Example 8: OWL/SKOS Domain Ontology

```
┌──────────────────────────────────────────────────────┐
│           OWL/SKOS Ontology — bfsi_capital.ttl       │
│                                                      │
│  CET1Capital ⊂ Tier1Capital ⊂ RegulatoryCapital      │
│  Formula: CET1 ÷ RWA × 100                          │
│  Min requirement: 4.5% (Basel III Article 92)        │
│  DB column: cet1_ratio_pct  (OBML annotation)        │
└──────────────────────┬───────────────────────────────┘
                       │  rdflib parses at startup
                       ▼
       ┌───────────────────────────────────┐
       │   Tool Description (built once)   │
       │   15 concepts · regulations ·     │
       │   formulas · column mappings      │
       └──────────────────┬────────────────┘
                          │  injected into tool
                          ▼
       ┌───────────────────────────────────┐
       │          LLM Agent               │
       │  Domain-aware: knows Basel III    │
       │  hierarchy, not just schema       │
       └─────────┬─────────────┬──────────┘
                 │             │
         data Qs │    domain Qs│ (answered from
                 │             │  ontology, no DB)
                 ▼             ▼
       ┌──────────────┐   ┌──────────────────────────┐
       │    DuckDB    │   │  "CET1 ⊂ Tier1 ⊂         │
       │  capital_    │   │   RegulatoryCapital.      │
       │  position    │   │   Min 4.5% per Art. 92." │
       └──────────────┘   └──────────────────────────┘
```

**Key difference from Example 4 (ODCS):** ODCS adds governance metadata to a schema. An ontology encodes the domain knowledge itself — the agent knows *what* CET1 Capital *is*, not just that the column exists.

---

### Example 9: dbt Metric Layer — BFSI (MetricFlow)

**Semantic component:** Metric Layer (Component 5 — named, governed business metrics)

**What it shows:**
- Five Basel III metrics defined in MetricFlow YAML: `cet1_ratio`, `combined_buffer_requirement`, `cet1_capital`, `rwa`, and `buffer_headroom` (a derived metric: `cet1_ratio − combined_buffer_requirement`).
- The agent calls `mf query` via subprocess — it never writes SQL. MetricFlow compiles the SQL, enforces the formula, and returns typed results.
- Every consumer of `cet1_ratio` gets the same number from the same governed definition. One metric. One truth.

**Quick Start:**
```bash
pip install dbt-core dbt-duckdb dbt-metricflow openai structlog
ollama pull qwen2.5
cd my-hello-worlds/[ce]-[metrics]-[bfsi]-[2026-05]/code
python3 bootstrap_metrics.py   # dbt run + mf validate-configs
python3 agent_metrics_ollama.py
```

**Or query metrics directly from the CLI (no agent needed):**
```bash
cd my-hello-worlds/[ce]-[metrics]-[bfsi]-[2026-05]/dbt_project
mf query --metrics cet1_ratio,buffer_headroom --group-by metric_time__month
```

---

### Example 9: Architecture

```
┌─────────────────────────────────────────────────────┐
│           schema.yml — MetricFlow Catalogue         │
│  cet1_ratio      (simple · min 4.5% · Art. 92)     │
│  buffer_headroom (derived: cet1_ratio − buffer)     │
│  cet1_capital    (simple · Art. 26-50)              │
│  rwa             (simple · Basel III)               │
│  combined_buffer (simple · Art. 128-131)            │
└──────────────────────┬──────────────────────────────┘
                       │  read at startup → tool description
                       ▼
       ┌───────────────────────────────────┐
       │          LLM Agent               │
       │  Knows metric definitions,       │
       │  ownership, Basel III thresholds │
       └──────────────┬────────────────────┘
                      │  tool call: query_metric
                      │  {metrics: ["cet1_ratio","buffer_headroom"],
                      │   group_by: ["metric_time__month"]}
                      ▼
       ┌───────────────────────────────────┐
       │   mf query (subprocess)          │
       │   MetricFlow compiles SQL        │
       │   Runs against DuckDB            │
       └──────────────┬────────────────────┘
                      ▼
       metric_time__month  cet1_ratio  buffer_headroom
       2025-09-01          14.39        4.64
       2025-12-01          14.66        4.91
       2026-03-01          14.83        5.08
```

**Key difference from Example 8 (Ontology):** The ontology says what CET1 Ratio *is*. The metric layer governs how it is *computed and consumed* — MetricFlow enforces the formula for every consumer, not the agent or analyst.

---

### Example 11: Knowledge Graph — Neo4j (Amazon UK Delivery)

**Semantic component:** Knowledge Graph (Component 4) — new domain

**What it shows:**
- A real three-stage context-building pipeline, not a pre-loaded graph. `bootstrap_source.py` seeds raw, flat rows into DuckDB. `ingest_to_graph.py` reads those rows *and* a prose policy document (`contracts/guarantee_policy.md` — not YAML) to decide which scans connect to a `Guarantee` node, and only then writes the graph into Neo4j.
- The guarantee rule is **parsed out of the policy document's prose at runtime** — there is no hardcoded `if scan_type == 'DEL'` anywhere in the ingestion code. Change the policy's wording, rerun ingestion, and the graph changes with zero code edits — the same way a real governed rule change would work.
- New domain: **Amazon UK Delivery** (multi-hop carrier scans, A-to-Z Guarantee eligibility) — shows the graph component isn't BFSI-specific, the same way Example 5 showed data products aren't either.
- Uses **Neo4j** — a local, open-source, Cypher-native equivalent of Amazon Neptune. The same `neo4j` Python driver call shape works against Neptune's openCypher endpoint with just a connection-string change.

**Quick Start:**
```bash
docker run -d --name neo4j-delivery -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:5
cd my-hello-worlds/[ce]-[knowledge-graph]-[amazon-delivery]-[2026-07]/code
pip install neo4j duckdb openai structlog
ollama serve && ollama pull qwen2.5
python3 bootstrap_source.py && python3 ingest_to_graph.py && python3 agent_graph_ollama.py
```

**Options:** Ollama (`agent_graph_ollama.py`) — Anthropic Claude variant planned.

---

### Example 11: Architecture

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
                                       │  Scan -[:TRIGGERS]-> Guarantee?     │
                                       │     (only if policy rule matches)   │
                                       └─────────────────┬──────────────────┘
                                                          │ tool call: trace_order
                                                          ▼
                                       ┌──────────────────────────────────┐
                                       │        LLM Agent (qwen2.5)         │
                                       └─────────────────┬──────────────────┘
                                                          ▼
                                        "Dispatched -> in transit -> arrived
                                         DAMAGED -> triggers the AtoZ
                                         Guarantee. You're covered."
```

**Key difference from Example 8 (Ontology):** the ontology encodes domain knowledge as a class hierarchy parsed from a Turtle file; this example encodes it as a **traversable graph built by a real ingestion pipeline** — raw source data and a governed policy document go in, a connected graph comes out.

---

### Example 12: Boring Semantic Layer (BSL) — Amazon UK Delivery

**Semantic component:** Boring Semantic Layer (BSL) — YAML-governed metric contracts, Ibis translation, backend-agnostic execution.

**What it shows:**
- The agent has exactly two tools: `lookup_glossary` (Knowledge Base layer) and `query_metric` (BSL layer). It cannot write SQL or access the database directly.
- Business metric formulas live in YAML files that a non-engineer can read, review, and approve. The agent selects which metric to call and passes optional dimension filters — it cannot change the formula.
- `metric_layer.py` translates a metric YAML contract into SQL via three passes (SELECT → WHERE → GROUP BY), then executes via `ibis.Backend.sql()`. The generated SQL is printed by the CLI — fully auditable.
- Governance filters in the YAML (e.g. `postcode_match = true`) are enforced automatically — the agent does not know they exist.
- Same Amazon UK Delivery domain as Example 11 — a direct comparison: graph traversal vs. metric contract, same data, two different CE approaches.

**Quick Start:**
```bash
pip3 install ibis-framework[duckdb] pyyaml openai
ollama serve && ollama pull qwen2.5
cd my-hello-worlds/[ce]-[bsl]-[amazon-delivery]-[2026-08]/code
python3 bootstrap_bsl.py
python3 metric_layer.py edd order_id=48213
python3 agent_bsl_ollama.py
```

---

### Example 12: Architecture

```
┌──────────────────────────────────────────────────┐
│         Knowledge Base (KB) Layer                 │
│         glossary/delivery_terms.yaml              │
│   DEL/ATT/SAF/NEI/LIT/EDD — meaning, exclusions, │
│   interpretation guidance, owner                 │
└───────────────────────┬──────────────────────────┘
                        │  tool: lookup_glossary
                        ▼
┌──────────────────────────────────────────────────┐
│         BSL Contract Layer (YAML)                 │
│   metrics/edd.yaml          v2.1                  │
│   metrics/order_count.yaml  v1.0                  │
│   formula, filters, dimensions, owner, SLA        │
└───────────────────────┬──────────────────────────┘
                        │  tool: query_metric → metric_layer.py
                        ▼
┌──────────────────────────────────────────────────┐
│         BSL Translation Engine                    │
│         code/metric_layer.py                      │
│   _build_sql():  YAML → SQL string               │
│   conn.sql():    ibis executes against backend   │
│   query_metric() → list[dict] → agent           │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼
┌───────────────┐    ┌──────────────────────────────┐
│   DuckDB      │    │  Swap to: Postgres / BigQuery │
│  delivery.duckdb   │  (change one connect() call)  │
└───────┬───────┘    └──────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│          LLM Agent (qwen2.5 via Ollama)           │
│   Calls lookup_glossary → reads KB meaning       │
│   Calls query_metric → receives list[dict]       │
│   Cannot write SQL, cannot modify formulas       │
└──────────────────────────────────────────────────┘
```

**Key difference from Example 11 (Knowledge Graph):** Example 11 connects entities into a traversable graph to answer *relational* questions (who placed what, what path did the parcel take, is there a guarantee edge). Example 12 governs *metric computation* — how EDD is calculated, which rows qualify, who approved the formula. Different CE components; same domain; same data.

---

### Example 13: Semantica ContextGraph — Amazon UK Delivery

**Semantic component:** Knowledge Graph via Semantica ContextGraph — in-memory graph, Python traversal API, W3C PROV-O decision provenance.

**What it shows:**
- A direct rebuild of Example 11 (Neo4j) using Semantica instead of Neo4j — same domain, same data, same guarantee policy, zero Docker. The Semantica ContextGraph is in-memory and serialised to `delivery_graph.json`.
- **The policy invariant holds.** `guarantee_policy.md` is still parsed at runtime. Change "DAMAGED" to anything else, rerun ingestion, the guarantee disappears — zero code edits, same as Example 11.
- **Python API replaces Cypher.** `get_neighbors(node_id, relationship_types=["SCANNED_AT"])` does what `MATCH (o)-[:SCANNED_AT]->(s)` did. No query language to learn; the traversal logic is plain Python in the tool implementation.
- **Provenance is new.** Every guarantee trigger also calls `record_decision()` — a W3C PROV-O audit record with reasoning, policy reference, entities, confidence, and decision_maker. Example 11 had the TRIGGERS edge (the *fact*). This adds the *why* — what a regulator, auditor, or SLA review actually needs.
- **Close to Neo4j and Amazon Neptune.** Semantica ContextGraph uses the same property-graph model — typed nodes, typed edges, multi-hop traversal. The patterns map directly to Neo4j Cypher and to Amazon Neptune's openCypher/property-graph deployment. Swap the connection string, not the mental model.

**Quick Start:**
```bash
pip install semantica duckdb openai
ollama serve && ollama pull qwen2.5
cd my-hello-worlds/[ce]-[semantica]-[amazon-delivery]-[2026-08]/code
python3 bootstrap_source.py          # seed DuckDB (same as Example 11)
python3 ingest_to_semantica.py       # build Semantica graph + record provenance decisions
python3 agent_semantica_ollama.py    # ask questions
```

**Side-by-side with Example 11:**

| | Example 11 — Neo4j | Example 13 — Semantica |
|---|---|---|
| Storage | Neo4j (Docker required) | In-memory + `save_to_file()` |
| Query language | Cypher | Python API |
| Guarantee trigger | TRIGGERS edge only | Edge + `record_decision()` provenance |
| Audit trail | None | W3C PROV-O record |

**Semantica repo:** https://github.com/semantica-agi/semantica

---

### Example 13: Architecture

```
┌──────────────────────────────────────────────────────┐
│   bootstrap_source.py — same as Example 11           │
│   DuckDB: customers · carriers · orders · scans      │
│   (raw, flat, no relationships yet)                  │
└──────────────────────┬───────────────────────────────┘
                       │ read
┌──────────────────────┴───────────────────────────────┐
│   contracts/guarantee_policy.md                       │
│   "scan_type=DEL AND condition=DAMAGED →              │
│    AtoZGuarantee (policy:4.2)"                        │
│   (same policy doc as Example 11)                    │
└──────────────────────┬───────────────────────────────┘
                       │ parse_policy() — no hardcoded `if`
                       ▼
┌──────────────────────────────────────────────────────┐
│   ingest_to_semantica.py                              │
│                                                      │
│   graph.add_node('order:48213', 'Order', ...)        │
│   graph.add_edge('scan:9931', 'guarantee:48213',     │
│                  'TRIGGERS')                         │
│                                                      │
│   graph.record_decision(                  ← NEW      │
│     category='guarantee_eligibility',               │
│     reasoning='Policy policy:4.2 states…',          │
│     confidence=1.0,                                  │
│     entities=['scan:9931', 'order:48213']            │
│   )   → W3C PROV-O audit record                     │
└──────────────────────┬───────────────────────────────┘
                       │ save_to_file('delivery_graph.json')
                       ▼
┌──────────────────────────────────────────────────────┐
│   Semantica ContextGraph  (in-memory, no Docker)     │
│                                                      │
│   Customer -[:PLACED]-> Order                        │
│   Order -[:SCANNED_AT]-> Scan (x N)                 │
│   Scan -[:NEXT]-> Scan  (journey chain)              │
│   Scan -[:TRIGGERS]-> Guarantee  (policy-driven)    │
│   + Decision provenance record per Guarantee        │
└──────────────────────┬───────────────────────────────┘
                       │ tools: trace_order · get_guarantee_status
                       ▼
┌──────────────────────────────────────────────────────┐
│   LLM Agent (qwen2.5 via Ollama)                     │
│   get_neighbors() · find_node() — Python, not Cypher │
└──────────────────────────────────────────────────────┘
```

**Key difference from Example 11:** same graph shape, same nodes, same edges — but no Docker, and the guarantee trigger is now a first-class auditable decision, not just a graph edge. The *why* is as queryable as the *what*.

**Key difference from Example 12 (BSL):** Example 12 governs *how metrics are computed* (formula locked in YAML). Example 13 governs *what happened and why* (entity relationships + decision provenance). Different CE layers; same domain; same data.

---

### Example 14: OWL Ontology — Multi-Source Identity Resolution (Hospitality Group)

**Semantic component:** OWL ontology as an identity resolution layer — three source systems with mismatched IDs, SPARQL-powered cross-system joins, local equivalent of AWS Context Ontology Accelerator.

**What it shows:**
- A UK Hospitality Group (B&I catering) runs three operational systems — EPOS, WFM (workforce), and Procurement — and none of them share a key. EPOS calls a site `SITE-LDN-01`; WFM calls the same site `LDN01`. Without resolving these identities, the question "What is the labour cost per cover?" is unanswerable — the WFM query and the EPOS query will never JOIN.
- `generate_ontology.py` introspects the DuckDB schemas (the local equivalent of AWS Glue Data Catalog / COA SCAN) and builds an OWL Turtle file. Key properties — `hosp:eposSiteId`, `hosp:wfmSiteId`, `hosp:eposItemId`, `hosp:procProductId` — are the identity bridges.
- `metric_layer.py` calls `resolve_site(epos_site_id)` before every cross-system query. That call runs a SPARQL query on the rdflib graph and returns both IDs. DuckDB can then join. The ontology is load-bearing — comment it out and the metric silently returns wrong data.
- New domain: **UK Hospitality Group (B&I catering)** — shows the OWL identity-resolution pattern is not BFSI-specific.
- Local equivalent of **AWS Context Ontology Accelerator (COA)**: COA's SCAN→MODEL→SERVE pipeline automates what `generate_ontology.py` does explicitly. The SPARQL query runs against the COA Virtual Knowledge Graph (Ontop) in production; here it runs against rdflib. Same concept, visible mechanics.

**Quick Start:**
```bash
pip3 install duckdb rdflib openai
ollama serve && ollama pull qwen2.5
cd my-hello-worlds/[ce]-[multi-source]-[hospitality]-[2026-08]/code
python3 bootstrap_hospitality.py   # seed DuckDB (3 systems, ~550 rows, deliberate ID mismatches)
python3 generate_ontology.py       # build OWL TTL (6 classes, 13 properties, 8 individuals)
python3 metric_layer.py labour_cost_per_cover SITE-LDN-01   # verify identity resolution
python3 agent_hospitality_ollama.py
```

**Try these questions:**
```bash
python3 agent_hospitality_ollama.py "What is the labour cost per cover at SITE-LDN-01?"
python3 agent_hospitality_ollama.py "Which categories drive the most revenue at SITE-MAN-01?"
python3 agent_hospitality_ollama.py "What is the food margin by product at SITE-LDN-02?"
```

**Local stack vs AWS:**

| Layer | This example (local) | AWS production stack |
|---|---|---|
| Schema discovery | DuckDB introspection (`DESCRIBE`) | AWS Glue Crawlers + Glue Data Catalog |
| Ontology construction | rdflib (explicit OWL) | AWS COA MODEL — Bedrock embeddings + similarity |
| Identity resolution | SPARQL on rdflib TTL | COA Virtual Knowledge Graph (Ontop / SPARQL endpoint) |
| Cross-system join | Python: SPARQL → DuckDB SQL | COA Tier-2 agentic SQL (VKG compiles SPARQL to federated SQL) |
| Agent | Ollama qwen2.5 | Amazon Bedrock (Claude Sonnet 4.5) |
| Ontology storage | `hospitality_ontology.ttl` | Amazon Neptune (RDF + property graph) |

---

### Example 14: Architecture

```
┌──────────────────────────────────────────────────────┐
│   bootstrap_hospitality.py                            │
│   DuckDB — 3 source systems, deliberate ID mismatches │
│                                                      │
│   epos_transactions   site_id = "SITE-LDN-01"        │
│   wfm_shifts          site_id = "LDN01"  ← different! │
│   procurement_products  (no site_id — national cat.) │
└──────────────────────┬───────────────────────────────┘
                       │ DESCRIBE introspection
┌──────────────────────┴───────────────────────────────┐
│   generate_ontology.py  (COA SCAN + MODEL, local)    │
│                                                      │
│   inst:site/lnd-01                                   │
│       hosp:eposSiteId    "SITE-LDN-01"  ← EPOS ID    │
│       hosp:wfmSiteId     "LDN01"        ← WFM ID     │
│                                                      │
│   inst:product/prod_bev_001                          │
│       hosp:eposItemId    "EPOS-LATTE"                │
│       hosp:procProductId "PROD-BEV-001"              │
└──────────────────────┬───────────────────────────────┘
                       │ writes hospitality_ontology.ttl
                       ▼
┌──────────────────────────────────────────────────────┐
│   metric_layer.py  — resolve before every query      │
│                                                      │
│   resolve_site("SITE-LDN-01")                        │
│     SPARQL → { wfm_site_id: "LDN01", name: "LDN CW" }│
│                                                      │
│   DuckDB: WFM query uses "LDN01"                     │
│   DuckDB: EPOS query uses "SITE-LDN-01"              │
│   → cross-system JOIN is possible                    │
└──────────────────────┬───────────────────────────────┘
                       │ tools: 3 governed metrics
                       ▼
┌──────────────────────────────────────────────────────┐
│   LLM Agent (qwen2.5 via Ollama)                     │
│   3 tools: labour_cost_per_cover · revenue_by_cat    │
│            food_margin_by_product                    │
│   Cannot query systems directly                      │
└──────────────────────────────────────────────────────┘
```

**Key difference from Example 8 (BFSI Ontology):** Example 8's ontology encodes domain knowledge — what CET1 Capital *is* conceptually. This example's ontology solves an operational problem — it bridges the ID formats used by different systems for the same real-world entity. Different jobs for the same W3C technology.

**Key difference from Example 11 (Knowledge Graph):** Example 11 uses the graph to represent relationships between entities (Customer → Order → Scan → Guarantee). This example uses the ontology as a translation layer — the graph is not the answer; it is the key that makes the SQL possible.

---

### Example 15: Decision Economics Toolkit — Azure Fabric → Ollama

**Semantic component:** Agent governance — cost-per-outcome accounting above the semantic layer

**What it shows:**
- Every LLM call is treated as a **capital allocation**. Before the call: a keyword classifier routes it to the cheapest model tier that can answer correctly and compresses context to the minimum token budget for that class. After the call: a two-tier quality probe (structural regex + sampled Ollama yes/no) catches routing miscalibration. Every call is recorded with its Azure cost equivalent.
- The core insight the DET fills: no existing framework (Azure Foundry Router, LiteLLM, RouteLLM) maps LLM token spend to confirmed business outcomes. DET adds that layer.
- Three test queries exercise each decision class. Class 1 (simple NC lookup) costs ~$0.0003 Azure equivalent. Class 4 (root-cause + CAPA recommendation) costs ~$0.025 — an 85× difference. The routing and compression exist to prevent Class 1 questions from paying Class 4 prices.
- Local version: Ollama (`qwen2.5` for small tier, `llama3.1` for large tier), DuckDB instead of OneLake Delta, structlog instead of Azure Monitor. The classifier, compressor, quality probe, and cost accounting are identical to the production version on Microsoft Fabric.

**Quick Start:**
```bash
# 1. Install Ollama and pull the models
brew install ollama && ollama serve
ollama pull qwen2.5     # small tier — maps to phi-4 on Azure
ollama pull llama3.1    # large tier — maps to gpt-4o on Azure

# 2. Install Python dependencies
cd my-hello-worlds/[ce]-[det]-[fabric-ollama]-[2026-11]/code
pip install openai duckdb structlog pyyaml

# 3. Run the demo (3 NC queries across decision classes)
python3 det_runner_ollama.py

# 4. Capture the trace
python3 det_runner_ollama.py > trace.jsonl

# 5. Query the decision log
python3 -c "
import duckdb
con = duckdb.connect('det.duckdb')
print(con.execute('SELECT decision_class, model_name, azure_equivalent_usd FROM decisions').fetchall())
"
```

---

### Example 15: Architecture

```
                     ┌──────────────────────────────────┐
                     │        Incoming NC Query          │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  1. Classifier (keyword regex)    │
                     │     Class 1–4 · small/large tier  │
                     │     NO LLM — deterministic, free  │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  2. Compressor                    │
                     │     Pin NC/CAPA IDs               │
                     │     Truncate free text to budget  │
                     │     Class 1: 400t  Class 3: 6000t │
                     └──────────────┬───────────────────┘
                                    │
               ┌────────────────────▼────────────────────┐
               │            LLM Call                      │
               │  small tier → qwen2.5 / phi-4            │
               │  large tier → llama3.1 / gpt-4o          │
               └────────────────────┬────────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  3. Quality Probe (two-tier)      │
                     │     Structural: regex patterns    │
                     │     Semantic:   yes/no Ollama     │
                     │                (10% sample rate)  │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  4. DecisionRecord                │
                     │     local_cost_usd    = $0.00     │
                     │     azure_equiv_usd   = $0.0003   │
                     │     quality_flag      = False     │
                     │     confirmed         = False     │
                     │     → DuckDB (local)              │
                     │     → Delta/OneLake (Azure prod)  │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  5. Showback                      │
                     │     Routing distribution          │
                     │     Cost per class                │
                     │     Compression savings           │
                     │     Quality flag rate             │
                     └──────────────────────────────────┘
```

**Azure vs. Local mapping:**

| Azure (Production) | Local (This Demo) |
|---|---|
| `AsyncAzureOpenAI` | `AsyncOpenAI(base_url="http://localhost:11434/v1")` |
| phi-4 (small tier) | `qwen2.5` |
| gpt-4o (large tier) | `llama3.1` |
| Azure Monitor OTel | structlog → console / `.jsonl` |
| OneLake Delta table | DuckDB (`det.duckdb`) |
| Fabric Activator confirmation | manual `confirmed=True` flip |

**Agent Governance Harness (production):**

In production on Azure, Semantic Kernel is the execution harness. DET registers as two filters and governs every agent automatically — no per-agent changes needed:

```
Semantic Kernel Agent Loop
  ├── IPromptRenderFilter (Pre)         ← DET: classify() + compress()
  ├── Azure AI Foundry / Azure OpenAI      model call, routed model
  └── IAutoFunctionInvocationFilter (Post) ← DET: quality_probe() + write_record()
```

**Key difference from all other examples:** Examples 1–14 answer *how to give the LLM the right context*. Example 15 answers *how to govern what the LLM costs and whether its answer was any good* — the FinOps and quality layer above the semantic layer. These two concerns are independent but complementary: good CE reduces token usage; DET measures whether that reduction happened and whether the saved cost was worth the answer quality.

---

## 🔍 Debugging Ollama

All Ollama-backed examples (Examples 1–5, 8–11) send requests to the local `qwen2.5` model. Enable debug logging to see every request, response, and token count in real time:

```bash
# 1 — Enable verbose logging (persists until reboot or explicit unset)
launchctl setenv OLLAMA_DEBUG 2

# 2 — Restart Ollama to pick up the env var
pkill ollama && ollama serve &

# 3 — Follow the log while any example runs
tail -f ~/.ollama/logs/server.log
```

What to look for in the log:

| Entry | Meaning |
|---|---|
| `POST /v1/chat/completions` | Each LLM turn — Turn 1 (tool decision) and Turn 2 (final answer) |
| `"tool_calls"` in response | Which tool and arguments the model chose |
| `prompt_eval_count` | Tokens consumed by the system prompt — grows with each CE layer added |
| `eval_count` | Tokens in the model's response |

**Token growth is the cost of richer context.** In Example 10, `prompt_eval_count` rises from ~400 (Agent 1, schema only) to 8 000+ (Agent 5, all layers). The debug log makes this visible per request.

To disable:

```bash
launchctl unsetenv OLLAMA_DEBUG
pkill ollama && ollama serve &
```

> See [Example 10 README](./[ce]-[agentic]-[full-stack]-[2026-05]/README.md#debugging-ollama) for a per-agent breakdown of what each log entry shows.

---

## 📚 Glossary

| Term | Definition |
|------|-----------|
| **AI Agent** | An autonomous system that understands natural language and takes actions (writing SQL, querying data, reasoning) to find answers. |
| **Context Engineering (CE)** | The discipline of designing, structuring, and governing the business context delivered to the LLM — at the right time and in the right format. |
| **Data Contract** | A file that documents what a dataset means, who owns it, SLAs, freshness, and lineage. Bridges semantic and technical layers. |
| **ODCS** | Open Data Contract Standard (Bitol/ACRYL). Formal spec for data contracts — schema, quality, SLAs, ownership, usage terms. |
| **ODPS** | Open Data Product Standard. Formal spec for data products — input/output ports, use cases, SLAs, pricing, governance. Think OpenAPI for data products. |
| **Data Product** | A governed, reusable business capability that exposes data through defined interfaces with ownership, SLAs, and quality guarantees. |
| **Semantic Layer** | A governed abstraction over raw data that defines what metrics and dimensions mean in business terms. |
| **SLayer** | Open-source semantic layer (motley-slayer). Compiles business metric queries into SQL via REST/MCP API. |
| **DuckDB** | In-process analytical SQL database. Used across all demos for fast, local query execution. |
| **Ollama** | Local LLM inference engine. Runs models like qwen2.5 on your machine without cloud APIs. |
| **MCP** | Model Context Protocol. Open standard for agents to discover and query semantic models and tools. |
| **LLM** | Large Language Model (Claude, GPT-4, Qwen). Powers the agent's reasoning and language understanding. |
| **Ontology** | A formal, machine-readable representation of domain knowledge — concepts, relationships, and properties. OWL and SKOS are the W3C standards for building ontologies. |
| **OWL** | Web Ontology Language. W3C standard for defining class hierarchies, logical relationships, and properties in machine-readable form. |
| **SKOS** | Simple Knowledge Organisation System. W3C standard for human-readable concept labels, definitions, and broader/narrower relationships. |
| **rdflib** | Python library for parsing and querying RDF/OWL/SKOS ontologies in Turtle (.ttl) and other RDF formats. |
| **OBML** | Ontology-Based Markup Language. Annotates data columns with ontology concept URIs, bridging the database schema and the domain model. |
| **Metric Layer** | A governed catalogue of named business metrics with defined formulas, owners, and thresholds — enforced for every consumer. Sits above the semantic layer. |
| **MetricFlow** | Open-source metric framework (Apache 2.0) that powers the dbt Semantic Layer. Compiles metric queries into SQL. CLI: `mf query`. |
| **dbt** | Data build tool. Transforms raw data into governed models and metrics. `dbt-duckdb` adapter enables fully local usage with DuckDB. |
| **YAML** | Human-readable data format. Used for data contracts and configuration. |
| **Knowledge Graph** | A network of entities (nodes) and their relationships (edges) that makes connected context traversable — e.g. Customer → Order → Scan → Guarantee. Amazon Neptune's property-graph equivalent, run locally. |
| **Neo4j** | Open-source, Cypher-native graph database. Local, open-source equivalent of Amazon Neptune's property-graph (openCypher/Gremlin) deployment mode. |
| **Cypher** | Neo4j's declarative graph query language (`MATCH`, `MERGE`, pattern traversal). Also supported by Amazon Neptune via its openCypher endpoint — same query shape, different connection string. |
| **BSL** | Boring Semantic Layer. A metric governance pattern: business formulas are written in human-readable YAML contracts, translated to SQL by a translation layer, and executed via a backend-agnostic query engine. The agent calls a named metric; it cannot modify the formula. |
| **Ibis** | Python library providing a unified query interface across DuckDB, PostgreSQL, BigQuery, Snowflake, Redshift, and others. Backend-agnostic: the same Python expression compiles to SQL for any registered backend. |
| **Metric contract** | A YAML file that defines a named business metric — base table, selected columns, derived columns, governance filters, valid dimension filters, owner, version, and approval status. The BSL translation engine reads this and generates SQL. |

| **Semantica** | Open-source in-memory property-graph library (Python). Typed nodes and edges, multi-hop traversal, W3C PROV-O provenance via `record_decision()`. No Docker, no Cypher — same graph model as Neo4j and Amazon Neptune. GitHub: https://github.com/semantica-agi/semantica |
| **SPARQL** | W3C query language for RDF/OWL graphs. Declarative, like SQL for ontologies. Used in Example 14 to resolve cross-system IDs from the OWL ontology before any DuckDB join. |
| **VKG** | Virtual Knowledge Graph. An abstraction layer (e.g. Ontop) that exposes relational data as a SPARQL endpoint without materialising triples — the same pattern AWS COA uses to serve its ontology over source systems. |
| **morph-KGC** | Open-source RDF mapping engine. Generates RDF individuals from relational data via YARRRML/RML mappings — the production equivalent of `generate_ontology.py` in Example 14. |
| **AWS COA** | AWS Context Ontology Accelerator. A managed pipeline (SCAN → MODEL → SERVE) that auto-generates OWL ontologies from Glue Data Catalog schemas using Bedrock embeddings, and exposes them as a VKG (Ontop SPARQL endpoint) backed by Neptune. |
| **Decision Economics (DET)** | An agent governance framework that treats every LLM call as a capital allocation: classify query complexity, route to the cheapest capable model, compress context to the minimum needed tokens, run a quality probe on the answer, and record every token spend against a confirmed business outcome. |
| **Decision Class** | A complexity tier (1–4) assigned to a query by the DET classifier. Class 1 = simple retrieval (small model, ~400 tokens). Class 4 = root cause + CAPA recommendation (large model, up to 20 000 tokens). The class determines model routing and context compression budget. |
| **Semantic Kernel (SK)** | Microsoft's open-source agent framework with a first-class filter architecture — `IPromptRenderFilter` and `IAutoFunctionInvocationFilter` intercept every model call. DET registers as two SK filters, applying governance to all agents without changing agent code. |
| **Azure AI Foundry** | Microsoft's managed platform for building, deploying, and monitoring AI agents. Provides the Model Router (balanced/cost/quality modes), Azure OpenAI deployments, and agent service (threads, runs, tools). |
| **Quality Probe** | A two-tier DET check run after every LLM call. Tier 1: structural regex check (always, free). Tier 2: sampled yes/no Ollama/Phi-4 probe against specific verifiable facts in the answer (10% of small-model calls). Result written as `quality_flag` on the DecisionRecord. |
| **Confirmed outcome** | A DecisionRecord field set by an external confirmation event (e.g. a CAPA status change in the quality system). `confirmed=False` at write time; flipped to `True` by Fabric Activator when the downstream outcome is verified. Query 3 in the showback returns zero rows until confirmation is wired — intentional, to prevent vanity metrics. |
| **Compression ratio** | The ratio of compressed context tokens to original context tokens (1.0 = no compression; 0.6 = 40% reduction). DET compresses by pinning structured fields (NC IDs, dates, severity codes) and truncating free-text narratives to the class budget. |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

```
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────
```
