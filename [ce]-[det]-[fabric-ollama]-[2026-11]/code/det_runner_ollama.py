# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────
"""
Decision Economics Toolkit — Ollama local test runner

Runs the full DET loop against a local Ollama instance:
  classify → compress → LLM → quality probe → record → showback

Three test queries exercise each decision class:
  Class 1: simple NC lookup       → qwen2.5 (small tier)
  Class 2: aggregate summary      → qwen2.5 (small tier)
  Class 3: multi-hop root cause   → llama3.1 (large tier)

This mirrors the Azure Fabric production flow
([lam]-[context-engineering]-[2026-11]/code/de_lh_c_wired.py)
but with:
  - OpenAI-compatible Ollama API (no Azure credentials)
  - DuckDB local sink  (no Delta Lake / OneLake)
  - structlog console output  (no Azure Monitor OTel)
  - local_cost_usd = $0  + azure_equivalent_usd for FinOps reference

Usage:
  ollama serve
  ollama pull qwen2.5
  ollama pull llama3.1
  python det_runner_ollama.py
  python det_runner_ollama.py > trace.jsonl
"""
from __future__ import annotations

import asyncio
import hashlib
import time

import structlog
from openai import AsyncOpenAI

from det_core import (
    classify_query,
    compress_context,
    DecisionRecord,
    BudgetAlert,
    check_budget,
    run_quality_probe,
    load_quality_spec,
    write_local_record,
    print_showback,
    DecisionClass,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL_SMALL     = "qwen2.5"               # maps phi-4 on Azure
MODEL_LARGE     = "llama3.1"              # maps gpt-4o on Azure
OLLAMA_BASE_URL = "http://localhost:11434/v1"
DB_PATH         = "det.duckdb"
USE_CASE_ID     = "nc-agent"
ENGINEER_ID_RAW = "demo-engineer@lamresearch.com"

OLLAMA_MODEL_MAP = {"small": MODEL_SMALL, "large": MODEL_LARGE}

# ---------------------------------------------------------------------------
# Structlog — JSON lines to stdout (pipe to trace.jsonl for persistence)
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger()

# ---------------------------------------------------------------------------
# System prompt — identical to production agent
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are LAM Research's NC Closed-Loop Agent.
Your job is to cluster non-conformances (NCs) from LAM's quality system,
identify common process steps, supplier correlation, and suggest CAPA owners.

Rules:
- Always cite NC IDs (e.g. NC-20241) when referencing specific events.
- Do not speculate beyond the provided NC history.
- When suggesting CAPA owners, use role titles (Process Engineering, Quality,
  Supply Chain) not individual names.
- If the evidence is insufficient, say so explicitly.
"""

# ---------------------------------------------------------------------------
# NC corpus fixture — representative LAM quality system data
# ---------------------------------------------------------------------------

NC_CORPUS = """\
NC-20241 ALD step fail, supplier ACME-42, Platform 7, 2026-10-01, Critical.
Chamber found out of spec after PM window. Precursor flow rate drifted 8%
from nominal setpoint. MFC calibration certificate from ACME-42 September
batch found out of spec. Assigned to Process Engineering.

NC-20249 ALD pre-clean fail, supplier ACME-42, Platform 7, 2026-10-05, Major.
Root cause investigation ongoing. Preliminary analysis suggests same MFC
drift pattern as NC-20241. Escalated to process engineering team for CAPA
initiation. CAPA-449 opened 2026-10-06. Expected closure 2026-10-20.

NC-20261 CVD step OK, Platform 3, 2026-10-07, Observation.
Scheduled review completed without findings. No action required.

NC-20278 ALD step fail, supplier ACME-42, Platform 7, 2026-10-12, Critical.
Third ALD failure in 12 days on Platform 7. Pattern highly correlated with
ACME-42 MFC batch. Quality team engaged. Supply chain hold placed on ACME-42
MFC units from September shipment. Part #MFC-7721-B.

NC-20301 ALD step fail, supplier ACME-42, Platform 7, 2026-10-18, Critical.
Fourth failure. Same MFC drift signature confirmed by metrology. CAPA-449
scope expanded to cover incoming inspection protocol for all ACME-42 MFC
deliveries. Supply Chain Engineering assigned as CAPA owner.

NC-20315 CVD tungsten fill OK, Platform 2, 2026-10-19, Observation.
Routine inspection. No issues found.

NC-20322 ALD barrier layer thin, Platform 7, 2026-10-22, Major.
Barrier layer 12% below target. Tool recipe variation suspected. Separate
investigation opened. Not related to ACME-42 MFC issue. Quality assigned.
""" * 4   # repeat to simulate a full retrieval corpus (~1,800 tokens)

# ---------------------------------------------------------------------------
# Test queries — one per decision class
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    (
        "Class 1 — Retrieve+Format",
        "List the latest 3 NCs for Platform 7.",
    ),
    (
        "Class 2 — Aggregate+Explain",
        "How many Critical NCs occurred this quarter and which suppliers are involved?",
    ),
    (
        "Class 3/4 — Multi-hop Root Cause",
        "Why are ALD NCs recurring on Platform 7? Cluster the events and recommend CAPA owners.",
    ),
]

# ---------------------------------------------------------------------------
# Full DET flow for one query
# ---------------------------------------------------------------------------

async def run_det_query(
    query: str,
    nc_history_text: str,
    client: AsyncOpenAI,
    quality_spec,
) -> dict:
    eng_hash = hashlib.sha256(ENGINEER_ID_RAW.encode()).hexdigest()[:12]

    # Step 1 — Classify
    routing = classify_query(query, context_token_estimate=len(nc_history_text.split()))
    model_name = OLLAMA_MODEL_MAP[routing.model_tier]
    step_count = 3 if routing.decision_class >= DecisionClass.MULTI_HOP_REASON else 2

    log.info(
        "det.classify",
        decision_class=int(routing.decision_class),
        model_tier=routing.model_tier,
        model=model_name,
        confidence=routing.confidence,
        signals=routing.signals_matched,
        token_budget=routing.token_budget,
    )

    # Step 2 — Compress
    compression = compress_context(nc_history_text, int(routing.decision_class))
    log.info(
        "det.compress",
        original_tokens=compression.original_tokens,
        compressed_tokens=compression.compressed_tokens,
        ratio=compression.compression_ratio,
        method=compression.method,
    )

    # Step 3 — Call LLM via Ollama
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": (
            f"NC history (compressed, {compression.compressed_tokens} tokens):\n"
            f"{compression.compressed_text}\n\n"
            f"Question: {query}"
        )},
    ]

    t0 = time.monotonic()
    response = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.0,
        max_tokens=1_024,
    )
    duration_ms = int((time.monotonic() - t0) * 1000)

    answer        = response.choices[0].message.content or ""
    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    log.info(
        "det.llm",
        model=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_ms=duration_ms,
    )

    # Step 4 — Quality probe
    quality = await run_quality_probe(
        question=query,
        answer=answer,
        spec=quality_spec,
        model_tier=routing.model_tier,
        llm_client=client,
        probe_model=model_name,
    )
    log.info(
        "det.quality",
        passed=quality.passed,
        probe_type=quality.probe_type,
        structural_matched=quality.structural_matched,
        semantic_yes=quality.semantic_yes,
        flag=quality.as_flag,
        checks_failed=quality.checks_failed,
    )

    # Step 5 — Record
    record = DecisionRecord.new(
        use_case_id=USE_CASE_ID,
        decision_class=int(routing.decision_class),
        model_tier=routing.model_tier,
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        step_count=step_count,
        engineer_id=eng_hash,
        duration_ms=duration_ms,
        outcome_tag="nc-clustered",
        compression_ratio=compression.compression_ratio,
        quality_flag=quality.as_flag,
        quality_checks_failed=quality.failed_summary,
    )

    write_local_record(record, DB_PATH)

    alert: BudgetAlert | None = check_budget(record)
    log.info(
        "det.record",
        decision_id=record.decision_id,
        local_cost_usd=record.local_cost_usd,
        azure_equivalent_usd=record.azure_equivalent_usd,
        budget_alert=alert.overage_pct if alert else None,
    )

    return {
        "answer":               answer,
        "decision_class":       int(routing.decision_class),
        "model_tier":           routing.model_tier,
        "model_name":           model_name,
        "azure_equivalent_usd": record.azure_equivalent_usd,
        "quality_flag":         quality.as_flag,
        "compression_ratio":    compression.compression_ratio,
        "duration_ms":          duration_ms,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    client       = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    quality_spec = load_quality_spec(USE_CASE_ID)

    log.info("det.start", use_case=USE_CASE_ID, db=DB_PATH, queries=len(TEST_QUERIES))

    for label, query in TEST_QUERIES:
        log.info("det.query", label=label, question=query)

        result = await run_det_query(query, NC_CORPUS, client, quality_spec)

        separator = "=" * 60
        print(f"\n{separator}")
        print(f"[{label}]  Class {result['decision_class']} → {result['model_name']}")
        print(f"Azure equivalent: ${result['azure_equivalent_usd']:.6f}  |  "
              f"compression: {result['compression_ratio']:.2f}  |  "
              f"quality_flag: {result['quality_flag']}  |  "
              f"{result['duration_ms']}ms")
        print(f"{separator}")
        print(result["answer"])

    print_showback(DB_PATH)
    log.info("det.done", db=DB_PATH)


if __name__ == "__main__":
    asyncio.run(main())
