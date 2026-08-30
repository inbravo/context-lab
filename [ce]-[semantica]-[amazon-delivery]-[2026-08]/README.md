# CE Semantica — Amazon UK Delivery

**Semantic component:** Knowledge Graph via Semantica ContextGraph — in-memory graph + W3C PROV-O decision provenance.

A direct rebuild of [Example 11 (Neo4j)](../[ce]-[knowledge-graph]-[amazon-delivery]-[2026-07]/README.md) using Semantica instead of Neo4j. Same domain. Same data. Same guarantee policy. Zero Docker.

---

## What changed vs Example 11

| | Example 11 — Neo4j | Example 13 — Semantica |
|---|---|---|
| Graph storage | Neo4j container (Docker required) | In-memory ContextGraph + `save_to_file()` |
| Query language | Cypher (`MATCH`, `MERGE`, pattern traversal) | Python API (`get_neighbors`, `find_node`, `get_nodes_by_label`) |
| Guarantee trigger | `MERGE (s)-[:TRIGGERS]->(g:Guarantee)` only | Same edge + `record_decision()` provenance record |
| Audit trail | None — TRIGGERS edge has no reasoning | W3C PROV-O: reasoning, entities, policy_ref, confidence, decision_maker |
| Agent tools | `trace_order` (Cypher) | `trace_order` + `get_guarantee_status` (Python API) |

## What stayed the same

- **The policy is the rule.** `guarantee_policy.md` is parsed at runtime. Change "DAMAGED" to anything else in the policy, rerun ingestion, the guarantee disappears — zero code edits.
- **The agent cannot write queries.** Two tools only: `trace_order` and `get_guarantee_status`. The graph traversal is in the tool implementation, not the agent.
- **Same data.** 3 customers, 2 carriers, 6 orders, 14 scans, 5 hubs — identical to Example 11.

---

## File layout

```
[ce]-[semantica]-[amazon-delivery]-[2026-08]/
├── contracts/
│   └── guarantee_policy.md          # Policy doc — same as Example 11
└── code/
    ├── bootstrap_source.py          # Seeds delivery.duckdb (identical to Example 11)
    ├── ingest_to_semantica.py       # Builds ContextGraph + records guarantee decisions
    └── agent_semantica_ollama.py    # Agent with Python graph traversal tools
```

---

## Prerequisites

```bash
pip install semantica duckdb openai
ollama serve && ollama pull qwen2.5
```

No Docker. No Neo4j. No Cypher.

---

## Quick start

```bash
cd code/
python3 bootstrap_source.py           # 1. seed DuckDB (once)
python3 ingest_to_semantica.py        # 2. parse policy + build Semantica graph
python3 agent_semantica_ollama.py     # 3. ask questions
```

---

## Try these questions

```bash
python3 agent_semantica_ollama.py "Where is order 48213?"
python3 agent_semantica_ollama.py "Is Sarah covered by a guarantee?"
python3 agent_semantica_ollama.py "What happened to Tom's book (order 60021)?"
python3 agent_semantica_ollama.py "Which orders triggered a guarantee?"
```

---

## Prove the rule is still externalized

Same test as Example 11 — the teaching point hasn't changed:

1. Open `contracts/guarantee_policy.md`
2. Change `DAMAGED` to `LATE` in the "Guarantee trigger rule" section
3. Rerun:
```bash
python3 ingest_to_semantica.py
```
`Scans matching the rule: 0` — no code changed, only the policy wording.

Revert and rerun to restore the guarantee.

---

## What the provenance record looks like

When scan 9931 (DEL + DAMAGED) triggers the A-to-Z Guarantee, Semantica's
`record_decision()` creates:

```
category:       guarantee_eligibility
scenario:       Order 48213: scan 9931 is DEL with condition DAMAGED
reasoning:      Policy policy:4.2 states: scan_type=DEL AND condition=DAMAGED
                triggers AtoZGuarantee. Scan 9931 matches both criteria.
                No LLM involved — deterministic rule parsed from the policy doc.
outcome:        eligible:AtoZGuarantee
confidence:     1.0
entities:       [scan:9931, order:48213, guarantee:48213]
decision_maker: guarantee-policy-engine
metadata:       {policy_doc: ../contracts/guarantee_policy.md, rule_ref: policy:4.2}
```

This is what a regulator, auditor, or SLA review would want to see. Example 11
had the TRIGGERS edge — the *fact* that the guarantee was triggered. This adds
the *why*.

---

## Connection to the CE stack

| Layer | This example |
|---|---|
| Knowledge Graph | Semantica ContextGraph — Customer, Order, Scan, Hub, Carrier, Guarantee nodes |
| Knowledge Base | `guarantee_policy.md` — parsed at runtime, same as Example 11 |
| Provenance | `record_decision()` — W3C PROV-O record per guarantee trigger |
| Agent | qwen2.5 via Ollama — two Python-API tools, no Cypher |

The Semantica ContextGraph is the local, Docker-free equivalent of what
Amazon Neptune provides on AWS for property-graph workloads — same concepts,
different connection string.
