"""
agent_semantica_ollama.py — Delivery support agent backed by a Semantica
ContextGraph instead of Neo4j (compare with Example 11's agent_graph_ollama.py).

The agent has the same two responsibilities as Example 11's agent:
  1. Trace an order's delivery journey
  2. Report guarantee eligibility

What changed vs Example 11:
  Neo4j + Cypher traversal  →  Semantica ContextGraph Python API
  TRIGGERS edge lookup      →  ContextGraph node lookup + decision provenance
  No audit chain visible    →  get_decision_chain() shows full reasoning trail

The tools are drop-in compatible at the question level:
  "Where is order 48213?"     — same question, same answer
  "Is order 48213 covered?"   — same answer + adds provenance detail

Usage:
    python agent_semantica_ollama.py
    python agent_semantica_ollama.py "Where is order 48213?"
    python agent_semantica_ollama.py "Is Sarah's order covered by a guarantee?"
    python agent_semantica_ollama.py "What is the journey for order 60021?"
    python agent_semantica_ollama.py "Which orders triggered a guarantee?"
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import json
import sys
from pathlib import Path
from openai import OpenAI
from semantica.context import ContextGraph

# ── Config ─────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434/v1"
MODEL           = "qwen2.5"
GRAPH_FILE      = Path(__file__).parent / "delivery_graph.json"
DEFAULT_QUESTION = (
    "Sarah placed order 48213 for Trainers. What happened to it, "
    "and is she covered by a guarantee?"
)

# ── Load the Semantica graph ───────────────────────────────────────────────
if not GRAPH_FILE.exists():
    print(f"ERROR: {GRAPH_FILE} not found — run ingest_to_semantica.py first.")
    sys.exit(1)

graph = ContextGraph()
graph.load_from_file(str(GRAPH_FILE))


# ── Tool implementations ───────────────────────────────────────────────────

def trace_order(order_id: str) -> dict:
    """
    Walk the Semantica graph to reconstruct the delivery journey for an order.

    Graph traversal (Semantica API):
      1. Find the Order node
      2. get_neighbors(SCANNED_AT) → all Scan nodes
      3. For each Scan: get_neighbors(AT_LOCATION) → Hub
      4. Sort by scan_time

    This replaces the Example 11 Cypher:
      MATCH (o:Order {order_id:$id})-[:SCANNED_AT]->(s)-[:AT_LOCATION]->(h)
    """
    order_node_id = f"order:{order_id}"
    order_node = graph.find_node(order_node_id)
    if not order_node:
        return {"error": f"Order {order_id!r} not found in graph."}

    order_meta = order_node.get("metadata", {})

    # Scans for this order
    scan_neighbors = graph.get_neighbors(
        order_node_id, relationship_types=["SCANNED_AT"]
    )

    journey = []
    for scan_nb in scan_neighbors:
        scan_id   = scan_nb["id"]
        scan_node = graph.find_node(scan_id)
        scan_meta = scan_node.get("metadata", {}) if scan_node else {}

        # Hub for this scan — get_neighbors returns id only; fetch node for metadata
        hub_neighbors = graph.get_neighbors(scan_id, relationship_types=["AT_LOCATION"])
        hub_location = "Unknown"
        if hub_neighbors:
            hub_node = graph.find_node(hub_neighbors[0]["id"])
            if hub_node:
                hub_location = hub_node.get("metadata", {}).get("location", "Unknown Hub")

        journey.append({
            "scan_id":      scan_meta.get("scan_id", scan_id),
            "scan_time":    scan_meta.get("scan_time", ""),
            "scan_type":    scan_meta.get("scan_type", ""),
            "condition":    scan_meta.get("condition", ""),
            "hub_location": hub_location,
        })

    journey.sort(key=lambda s: s["scan_time"])

    # Customer
    customer_neighbors = graph.get_neighbors(
        order_node_id,
        relationship_types=["PLACED"],
    )
    # PLACED is Customer→Order so we need reverse — check edges differently
    # get_neighbors from Customer side instead
    customer_name = None
    for cust_node in graph.get_nodes_by_label("Customer"):
        cust_neighbors = graph.get_neighbors(cust_node["id"], relationship_types=["PLACED"])
        if any(n["id"] == order_node_id for n in cust_neighbors):
            customer_name = cust_node["metadata"].get("name")
            break

    return {
        "order_id":     order_id,
        "product":      order_meta.get("product", ""),
        "order_date":   order_meta.get("order_date", ""),
        "customer":     customer_name,
        "journey_hops": len(journey),
        "journey":      journey,
        "final_status": journey[-1]["scan_type"] if journey else "UNKNOWN",
    }


def get_guarantee_status(order_id: str) -> dict:
    """
    Check whether a guarantee was triggered for an order.

    Graph lookup:  find Guarantee node for this order
    Provenance:    retrieve the record_decision() audit record

    Example 11 equivalent:
      MATCH (o:Order {order_id:$id})<-[:SCANNED_AT]-(s)-[:TRIGGERS]->(g:Guarantee)
      RETURN g

    Here we also return the decision reasoning — traceable to policy:4.2.
    """
    g_node_id = f"guarantee:{order_id}"
    g_node = graph.find_node(g_node_id)

    if not g_node:
        return {
            "order_id":  order_id,
            "eligible":  False,
            "reason":    "No Guarantee node found — order did not meet the trigger conditions in the policy.",
        }

    g_meta = g_node.get("metadata", {})

    # Retrieve matching decisions from provenance
    try:
        decisions = graph.find_similar_decisions(
            scenario=f"Order {order_id}",
            category="guarantee_eligibility",
            limit=1,
        )
    except Exception:
        decisions = []

    provenance = None
    if decisions:
        d = decisions[0]
        provenance = {
            "reasoning":      d.get("reasoning", ""),
            "policy_ref":     d.get("metadata", {}).get("rule_ref", ""),
            "confidence":     d.get("confidence", 1.0),
            "decision_maker": d.get("decision_maker", ""),
        }

    return {
        "order_id":       order_id,
        "eligible":       True,
        "guarantee_type": g_meta.get("guarantee_type", ""),
        "rule_ref":       g_meta.get("rule_ref", ""),
        "triggered_by":   g_meta.get("triggered_by_scan", ""),
        "provenance":     provenance,
    }


# ── Tool definitions (what the LLM sees) ──────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "trace_order",
            "description": (
                "Retrieve the full delivery journey for an order from the Semantica "
                "context graph — all scan events, locations, and final status. "
                "Use this to answer 'where is my order', 'what happened to order X', "
                "or 'what is the delivery status of order X'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID, e.g. '48213'.",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_guarantee_status",
            "description": (
                "Check whether an order triggered an A-to-Z Guarantee under "
                "the fulfilment policy. Returns eligibility, the guarantee type, "
                "the policy reference, and the full provenance reasoning. "
                "Use this to answer 'is this order covered', 'does X qualify for a guarantee'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID, e.g. '48213'.",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are a delivery support agent for Amazon UK.

You have access to a Semantica knowledge graph that contains the full
delivery journey for every order, including scan history, hub locations,
and guarantee eligibility decisions.

You have two tools:

1. trace_order(order_id)
   Returns the complete scan-by-scan delivery journey — scan type, condition,
   hub location, and timestamp for each hop.

2. get_guarantee_status(order_id)
   Returns whether the order qualifies for an A-to-Z Guarantee, which policy
   rule triggered it, and the full provenance reasoning chain.

Always call trace_order first to understand what happened to the order,
then call get_guarantee_status if the customer asks about coverage.
Be concise and customer-friendly.
"""


# ── Agentic loop ───────────────────────────────────────────────────────────

def run_agent(question: str) -> None:
    client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": question},
    ]

    print(f"\nQuestion: {question}")
    print("=" * 60)

    for _turn in range(8):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            print(f"\nAnswer:\n{msg.content}")
            print("=" * 60)
            return

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            args    = json.loads(tc.function.arguments)

            print(f"\n[tool] {fn_name}({json.dumps(args)})")

            if fn_name == "trace_order":
                result = trace_order(args["order_id"])
            elif fn_name == "get_guarantee_status":
                result = get_guarantee_status(args["order_id"])
            else:
                result = {"error": f"Unknown tool: {fn_name}"}

            print(f"       → {json.dumps(result, default=str)[:300]}")

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
