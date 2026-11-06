# [ce]-[det]-[fabric-ollama]-[2026-11]

## Active Knowledge

knowledge:
  - technologies/context-fabric
  - domains/bfsi

## Engagement Summary

- **Customer:** LAM Research — Impetus reference implementation
- **Work:** Decision Economics Toolkit (DET) — local Ollama proof of concept
- **Date:** 2026-11
- **Objective:** Prove the full DET loop (classify → compress → LLM → quality probe → record) runs against a local Ollama model, with Azure cost counterfactuals for FinOps showback
- **Deliverables:** det_core.py, det_runner_ollama.py, nc-agent.yaml, det.duckdb (runtime)

## Stack

| Layer | Tool |
|---|---|
| Classifier | Keyword regex — pure Python, no LLM |
| Compressor | Pin-then-truncate fallback (LLMLingua-2 optional) |
| LLM | Ollama / qwen2.5 (small tier) + llama3.1 (large tier) |
| Quality Probe | Same Ollama model — yes/no fact-checking against its own output |
| Local Sink | DuckDB (`det.duckdb`) |
| Observability | structlog → console / `trace.jsonl` |

## Decision Class Taxonomy

| Class | Label | Azure Model | Token Budget | Local Model |
|---|---|---|---|---|
| 1 | Retrieve + Format | phi-4 | 800t | qwen2.5 |
| 2 | Aggregate + Explain | phi-4 | 2,500t | qwen2.5 |
| 3 | Multi-hop Reason | gpt-4o | 8,000t | llama3.1 |
| 4 | Root Cause + CAPA | gpt-4o | no cap | llama3.1 |

## Run Order

```bash
cd code/
pip install openai duckdb structlog pyyaml

# Start Ollama (must be running)
ollama serve
ollama pull qwen2.5
ollama pull llama3.1   # optional — used for Class 3/4 queries

# Run the full DET demo (3 queries across decision classes)
python det_runner_ollama.py

# Capture the trace
python det_runner_ollama.py > trace.jsonl
```
