# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────
"""
Decision Economics Toolkit (DET) — Ollama-compatible core

Standalone consolidation of all five DET modules adapted for local testing:
  - Classifier  (keyword regex, no LLM — identical to workbench)
  - Compressor  (pin-then-truncate, LLMLingua optional)
  - Cost tracker (local cost = $0; shows Azure equivalent for FinOps)
  - Quality probe (structural + sampled semantic, Ollama-compatible)
  - Local DuckDB sink (instead of OneLake Delta)

Production version (Azure Fabric + GPT-4o / Phi-4):
  [lam]-[context-engineering]-[2026-11]/code/de_*.py

Mapping from Azure to Ollama:
  phi-4   (small tier) → qwen2.5
  gpt-4o  (large tier) → llama3.1
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any, Literal

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

try:
    import tiktoken
    _enc = tiktoken.encoding_for_model("gpt-4o")
    def _count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except (ImportError, Exception):
    def _count_tokens(text: str) -> int:
        return int(len(text.split()) * 0.75)


# =============================================================================
# 1. CLASSIFIER
# =============================================================================

class DecisionClass(IntEnum):
    RETRIEVE_FORMAT   = 1
    AGGREGATE_EXPLAIN = 2
    MULTI_HOP_REASON  = 3
    ROOT_CAUSE_CAPA   = 4


# Tier names are abstract — model names are resolved by the runner
MODEL_TIER: dict[DecisionClass, str] = {
    DecisionClass.RETRIEVE_FORMAT:   "small",
    DecisionClass.AGGREGATE_EXPLAIN: "small",
    DecisionClass.MULTI_HOP_REASON:  "large",
    DecisionClass.ROOT_CAUSE_CAPA:   "large",
}

TOKEN_BUDGET: dict[DecisionClass, int | None] = {
    DecisionClass.RETRIEVE_FORMAT:   800,
    DecisionClass.AGGREGATE_EXPLAIN: 2_500,
    DecisionClass.MULTI_HOP_REASON:  8_000,
    DecisionClass.ROOT_CAUSE_CAPA:   None,
}

_CLASS_4 = re.compile(
    r"\b(root\s*cause|CAPA|corrective\s*action|recommend|generate\s*report|"
    r"failure\s*mode|FMEA|8D|prevent|recurring|action\s*plan)\b",
    re.IGNORECASE,
)
_CLASS_3 = re.compile(
    r"\b(why|correlation|trend|compare|across|multiple|relationship|pattern|"
    r"over\s*time|which\s*supplier|which\s*platform|root\s*cause|impact\s*of|"
    r"drove|caused)\b",
    re.IGNORECASE,
)
_CLASS_2 = re.compile(
    r"\b(how\s*many|count|total|average|rate|percentage|summarize|breakdown|"
    r"distribution|by\s*(week|month|quarter|platform|supplier)|aggregate|group)\b",
    re.IGNORECASE,
)
_CLASS_1 = re.compile(
    r"\b(show|list|get|fetch|latest|current|status|what\s*is|find|look\s*up|"
    r"display|retrieve|give\s*me)\b",
    re.IGNORECASE,
)
_ENTITY = re.compile(
    r"\b(NC[-_]?\d+|platform\s+\d+|tool\s+\w+|supplier\s+\w+|"
    r"process\s+step|material\s+\w+|BOM|CAPA[-_]?\d*|SPC|ALD|CVD|"
    r"Etch|CMP|Clean|Dep|CSBG)\b",
    re.IGNORECASE,
)


@dataclass
class RoutingDecision:
    decision_class:  DecisionClass
    model_tier:      str            # "small" | "large"
    token_budget:    int | None
    confidence:      float
    signals_matched: list[str]


def classify_query(query: str, context_token_estimate: int = 0) -> RoutingDecision:
    score = 1
    signals: list[str] = []

    if _CLASS_4.search(query):
        score = max(score, 4); signals.append("class-4-keyword")
    if _CLASS_3.search(query):
        score = max(score, 3); signals.append("class-3-keyword")
    if _CLASS_2.search(query):
        score = max(score, 2); signals.append("class-2-keyword")
    if _CLASS_1.search(query):
        signals.append("class-1-keyword")

    entities = _ENTITY.findall(query)
    entity_count = len({e[0] if isinstance(e, tuple) else e for e in entities})
    if entity_count >= 3:
        score = max(score, 3); signals.append(f"multi-entity:{entity_count}")
    elif entity_count == 2:
        score = max(score, 2); signals.append(f"dual-entity:{entity_count}")

    if context_token_estimate > 10_000:
        score = max(score, 3); signals.append(f"large-context:{context_token_estimate}")
    elif context_token_estimate > 4_000:
        score = max(score, 2); signals.append(f"medium-context:{context_token_estimate}")

    dc = DecisionClass(score)
    return RoutingDecision(
        decision_class=dc,
        model_tier=MODEL_TIER[dc],
        token_budget=TOKEN_BUDGET[dc],
        confidence=0.90 if len(signals) >= 2 else 0.65,
        signals_matched=signals,
    )


# =============================================================================
# 2. COMPRESSOR
# =============================================================================

_PRESERVE_PATTERNS = [
    r"NC[-_]\d{4,8}",
    r"\b(Critical|Major|Minor|Observation)\b",
    r"\b(ALD|CVD|Etch|CMP|Clean|Dep|PVD|Implant)\b",
    r"\d{4}-\d{2}-\d{2}",
    r"Supplier\s*:\s*\w+",
    r"CAPA[-_]?\d*",
    r"Platform\s+\d+",
    r"Tool\s+\w+",
    r"Part\s*#?\s*\w+",
]
_PRESERVE_RE = re.compile("|".join(_PRESERVE_PATTERNS), re.IGNORECASE)

_COMPRESS_BUDGET: dict[int, int | None] = {1: 400, 2: 1_500, 3: 6_000, 4: None}


@dataclass
class CompressionResult:
    original_tokens:   int
    compressed_tokens: int
    compression_ratio: float
    compressed_text:   str
    method:            str    # "truncation" | "none"


def compress_context(text: str, decision_class: int) -> CompressionResult:
    budget = _COMPRESS_BUDGET.get(decision_class)
    orig_tokens = _count_tokens(text)

    if budget is None or orig_tokens <= budget:
        return CompressionResult(
            original_tokens=orig_tokens,
            compressed_tokens=orig_tokens,
            compression_ratio=1.0,
            compressed_text=text,
            method="none",
        )

    pinned_lines, free_lines = [], []
    for line in text.splitlines():
        (pinned_lines if _PRESERVE_RE.search(line) else free_lines).append(line)

    pinned_text = "\n".join(pinned_lines)
    free_budget = max(50, budget - _count_tokens(pinned_text))
    compressed_free = _truncate(free_lines, free_budget)

    result = (pinned_text + "\n\n" + compressed_free).strip() if pinned_text else compressed_free
    comp_tokens = _count_tokens(result)

    return CompressionResult(
        original_tokens=orig_tokens,
        compressed_tokens=comp_tokens,
        compression_ratio=round(comp_tokens / max(orig_tokens, 1), 3),
        compressed_text=result,
        method="truncation",
    )


def _truncate(lines: list[str], budget: int) -> str:
    words = " ".join(lines).split()
    lo, hi = 0, len(words)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _count_tokens(" ".join(words[:mid])) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return " ".join(words[:lo])


# =============================================================================
# 3. COST TRACKER
# =============================================================================

# Azure model rates ($/M tokens, Nov 2026) — used for counterfactual only
_AZURE_RATES: dict[str, dict[str, float]] = {
    "phi-4":   {"input": 0.07,  "output": 0.14},
    "gpt-4o":  {"input": 2.50,  "output": 10.00},
}
_AZURE_TIER_TO_MODEL = {"small": "phi-4", "large": "gpt-4o"}

BUDGET_TARGETS: dict[str, dict[str, float]] = {
    "field-brief":    {"per_decision_usd": 0.025, "daily_cap_usd": 10.00},
    "supply-control": {"per_decision_usd": 0.150, "daily_cap_usd": 50.00},
    "nc-agent":       {"per_decision_usd": 0.080, "daily_cap_usd": 30.00},
}


def compute_azure_equivalent(
    model_tier: str,
    input_tokens: int,
    output_tokens: int,
    step_count: int = 1,
) -> float:
    """What this call would cost on Azure (phi-4 / gpt-4o rates)."""
    azure_model = _AZURE_TIER_TO_MODEL.get(model_tier, "gpt-4o")
    rates = _AZURE_RATES[azure_model]
    base = (
        (input_tokens  / 1_000_000) * rates["input"] +
        (output_tokens / 1_000_000) * rates["output"]
    )
    return round(base * step_count, 8)


@dataclass
class DecisionRecord:
    decision_id:           str
    timestamp:             str
    use_case_id:           str
    decision_class:        int
    model_tier:            str       # "small" | "large"
    model_name:            str       # actual Ollama model used
    input_tokens:          int
    output_tokens:         int
    step_count:            int
    local_cost_usd:        float     # always 0.0 (Ollama is free)
    azure_equivalent_usd:  float     # what this would cost on Azure
    duration_ms:           int
    engineer_id:           str
    outcome_tag:           str  = ""
    compression_ratio:     float = 1.0
    quality_flag:          bool  = False
    quality_checks_failed: str   = ""
    probe_cost_usd:        float = 0.0
    confirmed:             bool  = False
    referenced_ids:        str   = ""

    @classmethod
    def new(
        cls,
        use_case_id: str,
        decision_class: int,
        model_tier: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        step_count: int,
        engineer_id: str,
        duration_ms: int,
        **kwargs,
    ) -> "DecisionRecord":
        raw = f"{use_case_id}:{engineer_id}:{datetime.now(timezone.utc).isoformat()}"
        return cls(
            decision_id=hashlib.sha256(raw.encode()).hexdigest()[:16],
            timestamp=datetime.now(timezone.utc).isoformat(),
            use_case_id=use_case_id,
            decision_class=decision_class,
            model_tier=model_tier,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            step_count=step_count,
            local_cost_usd=0.0,
            azure_equivalent_usd=compute_azure_equivalent(
                model_tier, input_tokens, output_tokens, step_count
            ),
            duration_ms=duration_ms,
            engineer_id=engineer_id,
            **kwargs,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BudgetAlert:
    use_case_id: str
    actual_usd:  float
    target_usd:  float
    overage_pct: float


def check_budget(record: DecisionRecord) -> BudgetAlert | None:
    targets = BUDGET_TARGETS.get(record.use_case_id)
    if not targets:
        return None
    target = targets["per_decision_usd"]
    if record.azure_equivalent_usd > target:
        return BudgetAlert(
            use_case_id=record.use_case_id,
            actual_usd=record.azure_equivalent_usd,
            target_usd=target,
            overage_pct=round((record.azure_equivalent_usd / target - 1) * 100, 1),
        )
    return None


# =============================================================================
# 4. QUALITY PROBE
# =============================================================================

@dataclass
class QualitySpec:
    required_patterns:    list[str] = field(default_factory=list)
    min_patterns_matched: int       = 1
    semantic_probe_rate:  float     = 0.10
    probe_questions:      list[str] = field(default_factory=list)
    min_yes_to_pass:      int       = 2


@dataclass
class QualityResult:
    passed:               bool
    probe_type:           str
    structural_matched:   int        = 0
    structural_required:  int        = 0
    semantic_yes:         int | None = None
    semantic_total:       int | None = None
    checks_failed:        list[str]  = field(default_factory=list)
    probe_cost_usd:       float      = 0.0

    @property
    def as_flag(self) -> bool:
        return not self.passed

    @property
    def failed_summary(self) -> str:
        return ",".join(self.checks_failed[:5])


def run_structural_check(answer: str, spec: QualitySpec) -> QualityResult:
    if not spec.required_patterns:
        return QualityResult(passed=True, probe_type="structural")

    matched, failed = [], []
    for pattern in spec.required_patterns:
        if re.search(pattern, answer, re.IGNORECASE):
            matched.append(pattern)
        else:
            failed.append(f"missing:{pattern[:30]}")

    passed = len(matched) >= spec.min_patterns_matched
    return QualityResult(
        passed=passed,
        probe_type="structural",
        structural_matched=len(matched),
        structural_required=spec.min_patterns_matched,
        checks_failed=failed if not passed else [],
    )


_PROBE_SYSTEM = (
    "You are a quality checker for a semiconductor quality management system. "
    "Answer each numbered question ONLY with 'YES' or 'NO'. "
    "Format: '1: YES' or '1: NO'. One line per question. No explanation."
)


async def run_semantic_probe(
    question: str,
    answer: str,
    spec: QualitySpec,
    llm_client: Any,
    probe_model: str,
) -> QualityResult:
    numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(spec.probe_questions))
    prompt = (
        f"ORIGINAL QUESTION:\n{question}\n\n"
        f"AGENT ANSWER:\n{answer}\n\n"
        f"For each statement below, answer YES or NO:\n{numbered}"
    )

    response = await llm_client.chat.completions.create(
        model=probe_model,
        messages=[
            {"role": "system", "content": _PROBE_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.0,
        max_tokens=len(spec.probe_questions) * 10,
    )

    text = response.choices[0].message.content or ""
    yes_count, no_items = 0, []
    for line in text.strip().split("\n"):
        m = re.match(r"^(\d+)[:\.\)]\s*(YES|NO)", line.strip(), re.IGNORECASE)
        if m:
            if m.group(2).upper() == "YES":
                yes_count += 1
            else:
                no_items.append(f"q{m.group(1)}:no")

    passed = yes_count >= spec.min_yes_to_pass
    return QualityResult(
        passed=passed,
        probe_type="semantic",
        semantic_yes=yes_count,
        semantic_total=len(spec.probe_questions),
        checks_failed=no_items if not passed else [],
    )


async def run_quality_probe(
    question: str,
    answer: str,
    spec: QualitySpec,
    model_tier: str,
    llm_client: Any | None = None,
    probe_model: str = "qwen2.5",
    _sample_override: float | None = None,
) -> QualityResult:
    structural = run_structural_check(answer, spec)

    sample_roll  = _sample_override if _sample_override is not None else random.random()
    run_semantic = (
        model_tier == "small"
        and llm_client is not None
        and spec.probe_questions
        and sample_roll < spec.semantic_probe_rate
    )

    if not run_semantic:
        return QualityResult(
            passed=structural.passed,
            probe_type="structural",
            structural_matched=structural.structural_matched,
            structural_required=structural.structural_required,
            checks_failed=structural.checks_failed,
        )

    semantic = await run_semantic_probe(question, answer, spec, llm_client, probe_model)
    combined_passed = structural.passed and semantic.passed
    combined_failed = structural.checks_failed + semantic.checks_failed
    return QualityResult(
        passed=combined_passed,
        probe_type="structural+semantic",
        structural_matched=structural.structural_matched,
        structural_required=structural.structural_required,
        semantic_yes=semantic.semantic_yes,
        semantic_total=semantic.semantic_total,
        checks_failed=combined_failed if not combined_passed else [],
    )


def load_quality_spec(use_case_id: str, templates_dir: Path | None = None) -> QualitySpec:
    if not _YAML_AVAILABLE:
        raise ImportError("Run: pip install pyyaml")

    base = templates_dir or Path(__file__).parent / "de_templates"
    path = base / f"{use_case_id}.yaml"
    if not path.exists():
        return QualitySpec()

    with open(path) as f:
        config = yaml.safe_load(f)

    q          = config.get("quality", {})
    structural = q.get("structural", {})
    semantic   = q.get("semantic_probe", {})

    return QualitySpec(
        required_patterns    = structural.get("required_patterns", []),
        min_patterns_matched = structural.get("min_patterns_matched", 1),
        semantic_probe_rate  = semantic.get("rate", 0.10),
        probe_questions      = semantic.get("questions", []),
        min_yes_to_pass      = semantic.get("min_yes_to_pass", 2),
    )


# =============================================================================
# 5. LOCAL DUCKDB SINK
# =============================================================================

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS decisions (
    decision_id           TEXT,
    timestamp             TEXT,
    use_case_id           TEXT,
    decision_class        INTEGER,
    model_tier            TEXT,
    model_name            TEXT,
    input_tokens          INTEGER,
    output_tokens         INTEGER,
    step_count            INTEGER,
    local_cost_usd        DOUBLE,
    azure_equivalent_usd  DOUBLE,
    duration_ms           INTEGER,
    engineer_id           TEXT,
    outcome_tag           TEXT,
    compression_ratio     DOUBLE,
    quality_flag          BOOLEAN,
    quality_checks_failed TEXT,
    probe_cost_usd        DOUBLE,
    confirmed             BOOLEAN,
    referenced_ids        TEXT,
    date_partition        TEXT
)
"""


def write_local_record(record: DecisionRecord, db_path: str = "det.duckdb") -> None:
    import duckdb
    con = duckdb.connect(db_path)
    con.execute(_CREATE_TABLE)
    d = record.to_dict()
    d["date_partition"] = record.timestamp[:10]
    con.execute(
        "INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            d["decision_id"], d["timestamp"], d["use_case_id"],
            d["decision_class"], d["model_tier"], d["model_name"],
            d["input_tokens"], d["output_tokens"], d["step_count"],
            d["local_cost_usd"], d["azure_equivalent_usd"], d["duration_ms"],
            d["engineer_id"], d["outcome_tag"], d["compression_ratio"],
            d["quality_flag"], d["quality_checks_failed"], d["probe_cost_usd"],
            d["confirmed"], d["referenced_ids"], d["date_partition"],
        ]
    )
    con.close()


def read_local_records(db_path: str = "det.duckdb", n: int = 20) -> list[dict]:
    import duckdb
    con = duckdb.connect(db_path)
    rows = con.execute(
        "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", [n]
    ).fetchall()
    cols = [c[0] for c in con.execute("DESCRIBE decisions").fetchall()]
    con.close()
    return [dict(zip(cols, row)) for row in rows]


def print_showback(db_path: str = "det.duckdb") -> None:
    """Print a mini FinOps showback to console — mirrors de_showback.sql logic."""
    import duckdb
    con = duckdb.connect(db_path)

    total = con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    if total == 0:
        print("\n[DET Showback] No records yet.")
        return

    print(f"\n{'─'*60}")
    print(f"  DET Local Showback  ({total} decision(s) in {db_path})")
    print(f"{'─'*60}")

    # Routing distribution
    rows = con.execute("""
        SELECT
            model_tier,
            COUNT(*) AS calls,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct,
            ROUND(SUM(azure_equivalent_usd), 6) AS azure_usd
        FROM decisions
        GROUP BY model_tier
        ORDER BY model_tier
    """).fetchall()
    print("\n  Routing distribution (Azure equivalent cost):")
    for tier, calls, pct, usd in rows:
        print(f"    {tier:<8}  {calls:>3} calls  ({pct:>5}%)   ${usd:.6f}")

    # Per-class breakdown
    rows = con.execute("""
        SELECT
            decision_class,
            COUNT(*) AS calls,
            ROUND(AVG(input_tokens + output_tokens), 0) AS avg_tokens,
            ROUND(AVG(azure_equivalent_usd), 6) AS avg_azure_usd
        FROM decisions
        GROUP BY decision_class
        ORDER BY decision_class
    """).fetchall()
    print("\n  Cost per decision class (Azure equivalent):")
    for cls, calls, avg_tok, avg_usd in rows:
        print(f"    Class {cls}  {calls:>3} calls   avg {int(avg_tok):>5} tokens   ${avg_usd:.6f}/call")

    # Compression savings
    row = con.execute("""
        SELECT
            ROUND(AVG(compression_ratio), 3) AS avg_ratio,
            ROUND(SUM(azure_equivalent_usd), 6) AS actual_usd,
            ROUND(SUM(azure_equivalent_usd / compression_ratio), 6) AS uncompressed_usd
        FROM decisions WHERE compression_ratio < 1.0
    """).fetchone()
    if row and row[0]:
        actual, uncompressed = row[1], row[2]
        savings_pct = round((1 - actual / max(uncompressed, 0.0001)) * 100, 1)
        print(f"\n  Compression savings: avg ratio {row[0]:.2f} → "
              f"${actual:.6f} actual vs ${uncompressed:.6f} uncompressed "
              f"({savings_pct}% saved)")

    # Quality probe summary
    flags = con.execute(
        "SELECT COUNT(*) FROM decisions WHERE quality_flag = TRUE"
    ).fetchone()[0]
    flag_pct = round(100 * flags / max(total, 1), 1)
    print(f"\n  Quality: {flags}/{total} flagged ({flag_pct}%)  "
          f"{'REVIEW CLASSIFIER' if flag_pct > 5 else 'OK'}")

    print(f"{'─'*60}\n")
    con.close()
