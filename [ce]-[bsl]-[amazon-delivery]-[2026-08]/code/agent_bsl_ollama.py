"""
agent_bsl_ollama.py — Boring Semantic Layer agent (Ollama / qwen2.5).

The agent has exactly TWO tools:

  lookup_glossary(term)
      → reads ../glossary/delivery_terms.yaml
      → returns the meaning, exclusions, and interpretation guidance
        for a delivery status code or metric name
      → this is the Knowledge Base (KB) layer

  query_metric(metric_name, filters)
      → calls metric_layer.query_metric()
      → translates the governed YAML definition into an Ibis expression
      → executes against DuckDB and returns rows
      → this is the BSL (executable contract) layer

The agent CANNOT write SQL.
It can only call these two governed tools.

The invariant: every metric has one definition.  The agent selects and
parameterises it.  It cannot invent a different formula.

Usage:
    python agent_bsl_ollama.py
    python agent_bsl_ollama.py "When will Sarah's order arrive?"
    python agent_bsl_ollama.py "What does ATT mean?"
    python agent_bsl_ollama.py "How many orders does Tom have?"
    python agent_bsl_ollama.py "What is the EDD for order 60021?"
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import json
import sys
import yaml
from pathlib import Path
from openai import OpenAI

import metric_layer

# ── Config ─────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL           = "qwen2.5"
GLOSSARY_FILE   = Path(__file__).parent.parent / "glossary" / "delivery_terms.yaml"
DEFAULT_QUESTION = (
    "Sarah placed order 48213 for Trainers. "
    "What does her current delivery status mean, "
    "and what is her Estimated Delivery Date?"
)

# ── Tool definitions (what the LLM sees) ──────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_glossary",
            "description": (
                "Look up the meaning of a delivery status code or metric name "
                "from the governed Business Glossary (Knowledge Base layer). "
                "Use this BEFORE quoting any status or metric to the user. "
                "Returns the definition, exclusions, owner, and how to interpret it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": (
                            "The term to look up, e.g. 'DEL', 'ATT', 'SAF', "
                            "'NEI', 'LIT', or 'EDD'."
                        ),
                    }
                },
                "required": ["term"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_metric",
            "description": (
                "Execute a governed metric by name and return the result rows. "
                "You MUST use this instead of writing SQL. "
                "The metric formula is defined in a governed YAML file — "
                "you cannot change it, only call it with optional filters. "
                "Available metrics: 'edd' (Estimated Delivery Date), "
                "'order_count' (number of orders)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "description": "Name of the metric to execute, e.g. 'edd' or 'order_count'.",
                    },
                    "filters": {
                        "type": "object",
                        "description": (
                            "Optional key-value filters to narrow results. "
                            "Valid keys: 'order_id', 'customer_id', 'current_status'. "
                            "Example: {\"order_id\": \"48213\"}"
                        ),
                    },
                },
                "required": ["metric_name"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a delivery support agent for Amazon UK.

You have two governed tools:

1. lookup_glossary(term)
   Use this to understand what a delivery status code or metric name means
   before you explain it to a customer.  Always look up a status before
   quoting it.

2. query_metric(metric_name, filters)
   Use this to retrieve governed metric results — Estimated Delivery Date (EDD),
   order counts, etc.  You CANNOT write SQL.  You MUST call this tool
   to get any computed value.

Rules:
- Always look up a status code via lookup_glossary before interpreting it.
- Always use query_metric for any calculated value — never guess or compute it yourself.
- When explaining EDD to a customer, include the date AND the interpretation
  guidance from the glossary (e.g. what ATT means for their EDD).
- Be concise and customer-friendly.
"""


# ── Tool implementations ───────────────────────────────────────────────────

def lookup_glossary(term: str) -> dict:
    """Read the governed glossary and return the entry for a term."""
    with open(GLOSSARY_FILE) as f:
        glossary = yaml.safe_load(f)

    term_upper = term.upper()
    terms = glossary.get("terms", {})

    if term_upper in terms:
        entry = terms[term_upper]
        return {
            "term":             term_upper,
            "label":            entry.get("label", ""),
            "definition":       entry.get("definition", "").strip(),
            "excludes":         entry.get("excludes", []),
            "owner":            entry.get("owner", ""),
            "how_to_interpret": entry.get("how_to_interpret", "").strip(),
            "triggers":         entry.get("triggers", None),
        }

    # Fuzzy: search by label
    for key, entry in terms.items():
        if term.lower() in entry.get("label", "").lower():
            return lookup_glossary(key)

    available = list(terms.keys())
    return {
        "error": f"Term '{term}' not found in glossary.",
        "available_terms": available,
    }


def run_query_metric(metric_name: str, filters: dict | None = None) -> dict:
    """Delegate to metric_layer.query_metric and return structured result."""
    try:
        rows = metric_layer.query_metric(metric_name, filters or None)
        meta = metric_layer.list_metrics()
        label = next(
            (m["label"] for m in meta if m["metric"] == metric_name),
            metric_name,
        )
        return {
            "metric":      metric_name,
            "label":       label,
            "row_count":   len(rows),
            "rows":        rows,
            "note": (
                "Formula governed by YAML contract in metrics/. "
                "The agent cannot modify this formula."
            ),
        }
    except ValueError as e:
        return {"error": str(e)}


# ── Agentic tool-call loop ─────────────────────────────────────────────────

def run_agent(question: str) -> None:
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": question},
    ]

    print(f"\nQuestion: {question}")
    print("=" * 60)

    for turn in range(8):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg)

        # No tool call — final answer
        if not msg.tool_calls:
            print(f"\nAnswer:\n{msg.content}")
            print("=" * 60)
            return

        # Execute each tool call
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            args    = json.loads(tc.function.arguments)

            print(f"\n[tool] {fn_name}({json.dumps(args)})")

            if fn_name == "lookup_glossary":
                result = lookup_glossary(args["term"])
            elif fn_name == "query_metric":
                result = run_query_metric(
                    args["metric_name"],
                    args.get("filters"),
                )
            else:
                result = {"error": f"Unknown tool: {fn_name}"}

            print(f"       → {json.dumps(result, default=str)[:200]}")

            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      json.dumps(result, default=str),
            })

    print("\n[warn] Reached max turns without a final answer.")


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    run_agent(question)
