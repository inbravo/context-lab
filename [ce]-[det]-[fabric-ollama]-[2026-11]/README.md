# Decision Economics Toolkit — Azure Fabric → Ollama

A local proof-of-concept for the DET framework built for LAM Research's
AI agents on Microsoft Fabric. Runs the full classify → compress → LLM →
quality probe → record loop against a local Ollama model, with Azure cost
counterfactuals so the FinOps showback works without an Azure subscription.

```
det_core.py              — all five DET modules in one portable file
det_runner_ollama.py     — full demo: 3 queries across decision classes
de_templates/nc-agent.yaml  — quality spec (structural + semantic probe)
```

---

## Quick Start

```bash
# 1. Install Ollama and pull the models
brew install ollama && ollama serve
ollama pull qwen2.5     # small tier — maps to phi-4 on Azure
ollama pull llama3.1    # large tier — maps to gpt-4o on Azure

# 2. Install Python dependencies
cd code/
pip install openai duckdb structlog pyyaml

# 3. Run the demo (3 NC queries across decision classes)
python det_runner_ollama.py

# 4. Capture the full trace
python det_runner_ollama.py > trace.jsonl
```

---

## What It Demonstrates

Each query goes through the complete DET lifecycle:

```
Question
    │
    ▼
1. Classify — keyword regex → Decision Class 1–4 + model tier (small/large)
    │
    ▼
2. Compress — pin NC IDs / CAPA refs, truncate free text to class budget
    │
    ▼
3. Call LLM — qwen2.5 (small) or llama3.1 (large) via Ollama OpenAI API
    │
    ▼
4. Quality probe — structural regex check + sampled Ollama yes/no probe
    │
    ▼
5. Record — write DecisionRecord to det.duckdb
    │
    ▼
6. Showback — routing distribution, cost per class, compression savings
```

---

## Three Test Queries

| Query | Class | Azure Model | Local Model | Azure Cost |
|---|---|---|---|---|
| List latest 3 NCs for Platform 7 | 1 | phi-4 | qwen2.5 | ~$0.000003 |
| How many Critical NCs this quarter? | 2 | phi-4 | qwen2.5 | ~$0.000012 |
| Why are ALD NCs recurring? Recommend CAPA owners. | 3/4 | gpt-4o | llama3.1 | ~$0.000080 |

The Class 3/4 query costs **~27× more on Azure** than the Class 1 query —
exactly the routing pressure DET is designed to relieve.

---

## The Core Idea

Decision Economics treats every LLM call as a capital allocation:

- **Route** each query to the cheapest model that can answer it correctly.
- **Compress** retrieved context to the minimum tokens the class needs.
- **Measure** every call against a confirmed business outcome, not just an `outcome_tag`.
- **Govern** with weekly routing distribution checks (target: ≥70% small-model calls).

```
Cost per NC cluster closed = Σ(token cost × step_count) / confirmed NC clusters
```

No other framework (Azure Foundry Router, LiteLLM, RouteLLM) maps LLM token
spend to business outcomes. That gap is DET's unique layer.

---

## Azure vs. Local Mapping

| Azure (Production) | Local (This Demo) |
|---|---|
| `AsyncAzureOpenAI` | `AsyncOpenAI(base_url="http://localhost:11434/v1")` |
| phi-4 (small tier) | `qwen2.5` |
| gpt-4o (large tier) | `llama3.1` |
| Azure Monitor OTel | structlog → console |
| OneLake Delta table | DuckDB (`det.duckdb`) |
| Fabric Activator | manual `confirmed=True` flip |

The classifier, compressor, quality probe, and cost accounting logic are
identical in both environments.

---

## Sample Output

```
{"decision_class": 1, "model_tier": "small", "model": "qwen2.5",
 "confidence": 0.9, "signals": ["class-1-keyword"], "event": "det.classify", ...}
{"original_tokens": 1246, "compressed_tokens": 324, "ratio": 0.26,
 "method": "truncation", "event": "det.compress", ...}
{"input_tokens": 412, "output_tokens": 87, "duration_ms": 4231,
 "event": "det.llm", ...}
{"passed": true, "probe_type": "structural", "structural_matched": 3,
 "event": "det.quality", ...}
{"local_cost_usd": 0.0, "azure_equivalent_usd": 0.000004,
 "event": "det.record", ...}

============================================================
[Class 1 — Retrieve+Format]  Class 1 → qwen2.5
Azure equivalent: $0.000004  |  compression: 0.26  |  quality_flag: False  |  4231ms
============================================================
The latest 3 NCs for Platform 7 are:
1. NC-20301 — ALD step fail, Critical, 2026-10-18 ...
...

────────────────────────────────────────────────────────────
  DET Local Showback  (3 decision(s) in det.duckdb)
────────────────────────────────────────────────────────────

  Routing distribution (Azure equivalent cost):
    large     1 calls  ( 33.3%)   $0.000080
    small     2 calls  ( 66.7%)   $0.000016

  Cost per decision class (Azure equivalent):
    Class 1    1 calls   avg   412 tokens   $0.000004/call
    Class 2    1 calls   avg   890 tokens   $0.000012/call
    Class 3    1 calls   avg  3200 tokens   $0.000080/call

  Quality: 0/3 flagged (0.0%)  OK
────────────────────────────────────────────────────────────
```

---

## Stack

| Layer | Component | Notes |
|---|---|---|
| Classifier | Keyword regex | No LLM — deterministic, no cost |
| Compressor | Pin-then-truncate | LLMLingua-2 optional (`pip install llmlingua`) |
| LLM | Ollama / qwen2.5 + llama3.1 | OpenAI-compatible API at localhost:11434 |
| Quality probe | Same Ollama model | Structural regex + sampled semantic yes/no |
| Sink | DuckDB (`det.duckdb`) | Portable local Delta equivalent |
| Observability | structlog | JSON to console; pipe to `.jsonl` for persistence |

---

## Agent Governance Harness

DET is the **cost-accounting middleware layer**. It needs an agent execution
harness above it that provides lifecycle hooks (pre/post model call), tool
orchestration, and audit logging. On Azure the right choice is Semantic Kernel.

### Why Semantic Kernel

Semantic Kernel (SK) is the only major Azure-native framework with a
**filter architecture** — interceptors that fire before and after every model
call, without changing the agent code. DET plugs in as two filters:

```
Semantic Kernel Agent Loop
  │
  ├── IPromptRenderFilter (Pre)      ← DET: classify() + compress()
  │       sets model, token budget, compression before the call
  │
  ├── Azure AI Foundry / Azure OpenAI   model call with routed model
  │
  └── IAutoFunctionInvocationFilter (Post) ← DET: quality_probe() + write_record()
          quality check, DecisionRecord written to Delta / DuckDB
```

Every agent (NC Closed-Loop, Field Brief, Supply Control) automatically gets
DET governance by inheriting the filter chain — not by being written
differently. One filter registration covers all three lighthouses.

```python
# Registration (Semantic Kernel 1.x)
kernel.add_filter(FilterTypes.PROMPT_RENDERING, DETPreFilter(classifier, compressor))
kernel.add_filter(FilterTypes.AUTO_FUNCTION_INVOCATION, DETPostFilter(tracker, sink))
```

---

### Best Fit vs. Alternatives on Azure

The table below covers the full Azure agent governance landscape across five
governance dimensions DET cares about.

| Framework | Pre/Post hooks | Budget enforcement | Quality / safety checks | Audit logging | Azure-native | Multi-agent | DET fit |
|---|---|---|---|---|---|---|---|
| **Semantic Kernel** ✅ | Filter API — first-class | Plugin can block call | Content filters + custom | OTel built-in | Native (Microsoft OSS) | ProcessFramework | Slots in as a filter |
| **Azure AI Foundry Agent Service** | Limited (run lifecycle only) | Token limits on run | Azure AI Content Safety | Thread/run logs in Foundry | Fully managed PaaS | Handoffs (beta) | Wraps around DET; hooks are coarse |
| **AutoGen 0.4** | Middleware hooks in AgentChat | Manual, not built-in | Custom via middleware | OTel optional | Azure OpenAI compatible | First-class (GroupChat, Teams) | Good for multi-agent swarms; overkill for 3-step linear agents |
| **Microsoft AGT** _(Agent Governance Toolkit)_ | Policy-as-code (not hooks) | Policy rules | Policy rules | Policy audit log | Azure-first | N/A — policy layer only | Complements SK; not an execution harness |
| **Prompt Flow** | Node pre/post (DAG only) | None | Evaluation flows | Run logs in AML | Azure ML Studio | No | Good for batch eval; not real-time governance |
| **LangGraph on Azure** | Node entry/exit hooks | Manual | Custom nodes | LangSmith (separate) | Azure OpenAI compatible | Graph edges | Good for complex branching state; heavy dep, non-Microsoft |

### Governance dimension definitions

| Dimension | What it means for DET |
|---|---|
| **Pre/Post hooks** | Can DET intercept every model call without wrapping agent code? |
| **Budget enforcement** | Can the harness block a call that would breach `per_decision_usd`? |
| **Quality / safety checks** | Can DET's quality probe result prevent or flag the response before it reaches the user? |
| **Audit logging** | Does every tool call and model response get an immutable, structured record? |
| **Azure-native** | Does the framework run without non-Microsoft infrastructure (LangSmith, etc.)? |
| **Multi-agent** | Does it coordinate multiple specialized agents in one workflow? |

### Decision rule

```
Single-agent, Azure Fabric, need DET hooks → Semantic Kernel
Multi-agent swarm (agent-to-agent handoffs) → AutoGen 0.4 + SK for governance layer
Batch evaluation / offline quality scoring → Prompt Flow
Policy-as-code audit trail (compliance) → AGT alongside SK
```

For LAM: Semantic Kernel for all three lighthouses (NC Agent, Field Brief,
Supply Control), with AGT layered on for compliance audit if required by
Sudarshan's quality org.

---

## CE Series

| Example | What it shows |
|---|---|
| [CE Hello World](../[ce]-[hello-world]-[2026-05]/README.md) | Data contract → agent → SQL → answer |
| **[CE DET Fabric→Ollama](../[ce]-[det]-[fabric-ollama]-[2026-11]/README.md) (this)** | Decision Economics: classify, compress, govern, record |
