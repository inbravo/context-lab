"""
agent_hospitality_ollama.py — Operations intelligence agent for the
Hospitality Group, backed by an ontology-resolved cross-system metric layer.

Modelled on the real Compass Group data landscape (AWS-shared):

  EPOS          Oracle MICROS  site_id = "SITE-LDN-01"   ← caller always passes this
  WFM           Infor WFM      site_id = "GBR_SITE_0001"  ← resolved via SPARQL
  SAP Sales     SAP S/4HANA    cost_center = "CC-GBR-001" ← resolved via SPARQL
  HR & Payroll  SuccessFactors org_unit = "OU-GBR-001"    ← resolved via SPARQL
  Procurement   Coupa          (national catalogue — no site_id)

  Local (this file)               AWS equivalent
  ─────────────────               ──────────────
  Ollama qwen2.5                  Amazon Bedrock (Claude Sonnet 4.5)
  metric_layer.py tools           COA MCP server tools
  rdflib SPARQL resolution        COA Virtual Knowledge Graph (Ontop / Neptune)
  DuckDB                          S3 + Glue + Amazon Athena

Usage:
    python agent_hospitality_ollama.py
    python agent_hospitality_ollama.py "What is the labour cost per cover at SITE-LDN-01?"
    python agent_hospitality_ollama.py "What is the SAP revenue per cover at SITE-MAN-01?"
    python agent_hospitality_ollama.py "What is the headcount breakdown at SITE-LDN-02?"
    python agent_hospitality_ollama.py "Give me a full operational summary for SITE-LDN-01."
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import json
import logging
import sys
from openai import OpenAI

import logging_config
logging_config.setup()
log = logging.getLogger("hosp.agent")

import metric_layer

OLLAMA_BASE_URL  = "http://localhost:11434/v1"
MODEL            = "qwen2.5"
DEFAULT_QUESTION = (
    "Give me a full operational summary for SITE-LDN-01: "
    "labour cost per cover, revenue by category, SAP revenue per cover, "
    "and SuccessFactors headcount breakdown by contract type."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_labour_cost_per_cover",
            "description": (
                "Return labour cost per meal served (cover) by meal period. "
                "Joins Infor WFM shift costs (site_id format: GBR_SITE_0001) with "
                "Oracle MICROS EPOS transaction counts (site_id format: SITE-LDN-01). "
                "The site identity mismatch is resolved automatically via the ontology."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {
                        "type": "string",
                        "description": "Site ID in Oracle MICROS EPOS format, e.g. 'SITE-LDN-01', 'SITE-LDN-02', 'SITE-MAN-01'.",
                    }
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_by_category",
            "description": "Return Oracle MICROS EPOS revenue grouped by product category for a site.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {
                        "type": "string",
                        "description": "Site ID in EPOS format.",
                    }
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_food_margin_by_product",
            "description": (
                "Return gross margin per product: EPOS selling price minus "
                "the Coupa procurement contracted cost. The EPOS item code "
                "(format: EPOS-LATTE) to Coupa catalogue SKU (format: PROD-BEV-001) "
                "bridge is resolved automatically via the ontology."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {
                        "type": "string",
                        "description": "Site ID in EPOS format.",
                    }
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_per_cover",
            "description": (
                "Return SAP S/4HANA-invoiced net revenue per cover billed, by meal period. "
                "SAP uses cost_center_code (format: CC-GBR-001). "
                "The EPOS-to-SAP identity mismatch is resolved automatically via the ontology."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {
                        "type": "string",
                        "description": "Site ID in EPOS format.",
                    }
                },
                "required": ["epos_site_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_headcount_by_contract",
            "description": (
                "Return SAP SuccessFactors headcount and FTE by contract type "
                "(PERMANENT, PART_TIME, ZERO_HOURS, AGENCY). "
                "SuccessFactors uses org_unit_id (format: OU-GBR-001). "
                "The EPOS-to-SF identity mismatch is resolved automatically via the ontology."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "epos_site_id": {
                        "type": "string",
                        "description": "Site ID in EPOS format.",
                    }
                },
                "required": ["epos_site_id"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are an operations intelligence agent for a UK Hospitality Group (B&I catering).

You have access to five governed data sources via ontology-resolved tools:
  1. Oracle MICROS EPOS  — point-of-sale transactions   (site_id: SITE-LDN-01)
  2. Infor WFM           — workforce shifts/labour costs (site_id: GBR_SITE_0001)
  3. Coupa Procurement   — national product catalogue    (no site_id; 300k products, 20k suppliers/market)
  4. SAP S/4HANA         — client sales & invoicing      (cost_center: CC-GBR-001)
  5. SAP SuccessFactors  — HR & payroll records          (org_unit: OU-GBR-001)

Each system uses a different ID format for the same site. The identity
resolution is automatic via the OWL ontology layer — always pass the EPOS
site_id format (e.g. SITE-LDN-01) to your tools.

You have five tools:
  1. get_labour_cost_per_cover(epos_site_id)   — Infor WFM + EPOS
  2. get_revenue_by_category(epos_site_id)      — EPOS
  3. get_food_margin_by_product(epos_site_id)   — EPOS + Coupa
  4. get_revenue_per_cover(epos_site_id)        — SAP S/4HANA
  5. get_headcount_by_contract(epos_site_id)    — SAP SuccessFactors

Be concise. Lead with the headline finding.
Flag: labour cost per cover > £3.00, gross margin < £0.50,
      revenue per cover < £8.00, zero-hours/agency headcount > 30%.
"""


def dispatch(fn_name: str, args: dict):
    if fn_name == "get_labour_cost_per_cover":
        return metric_layer.labour_cost_per_cover(args["epos_site_id"])
    if fn_name == "get_revenue_by_category":
        return metric_layer.revenue_by_category(args["epos_site_id"])
    if fn_name == "get_food_margin_by_product":
        return metric_layer.food_margin_by_product(args["epos_site_id"])
    if fn_name == "get_revenue_per_cover":
        return metric_layer.revenue_per_cover(args["epos_site_id"])
    if fn_name == "get_headcount_by_contract":
        return metric_layer.headcount_by_contract(args["epos_site_id"])
    return {"error": f"Unknown tool: {fn_name}"}


def run_agent(question: str) -> None:
    log.info("Agent question: %s", question)
    client   = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": question},
    ]

    print(f"\nQuestion: {question}")
    print("=" * 65)

    for turn in range(15):
        log.debug("LLM turn %d — sending %d messages", turn + 1, len(messages))
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto"
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            log.info("Agent answer (turn %d): %s", turn + 1, (msg.content or "")[:200])
            print(f"\nAnswer:\n{msg.content}")
            print("=" * 65)
            return

        for tc in msg.tool_calls:
            args   = json.loads(tc.function.arguments)
            log.info("Tool call: %s  args=%s", tc.function.name, args)
            result = dispatch(tc.function.name, args)
            log.debug("Tool result: %s  rows=%s", tc.function.name,
                      len(result) if isinstance(result, list) else type(result).__name__)
            print(f"\n[tool] {tc.function.name}({json.dumps(args)})")
            print(f"       → {json.dumps(result, default=str)[:500]}")
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

    log.warning("Agent reached max turns without a final answer. question=%s", question[:80])
    print("\n[warn] Reached max turns.")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    run_agent(question)
