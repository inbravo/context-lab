"""
CE Knowledge Graph Demo — Amazon UK Delivery (Neo4j / Ollama qwen2.5)

What this demo shows:
  - Order, Scan, Hub, and Guarantee live as connected nodes in a real
    graph database (Neo4j) instead of flat, unrelated tables.
  - The agent calls one tool — trace_order — which runs a Cypher
    traversal instead of an ad-hoc join written per question.
  - Whether a TRIGGERS -> Guarantee edge exists depends on the scan's
    condition set at bootstrap time (DAMAGED vs IN_TRANSIT) — the agent
    reports what the graph actually contains, it does not guess.

Mirrors the "How does this all fit together?" check on the CE knowledge
base website (Amazon UK Delivery, AWS / Neptune version) — same instance
IDs, same story, running against a local Neo4j graph instead of Amazon
Neptune. The neo4j Python driver call shape here is close to unchanged
from what you'd write against Neptune's openCypher endpoint — swap the
connection string, not the code.

Run order:
    python bootstrap_graph.py
    python agent_graph_ollama.py

Usage:
    python agent_graph_ollama.py
    python agent_graph_ollama.py "Is order 51890 covered by a guarantee?"
"""
# ─────────────────────────────────────────────────────
# Author   : Amit Dixit
# GitHub   : https://github.com/inbravo
# Web      : https://inbravo.github.io
# LinkedIn : https://www.linkedin.com/in/inbravo/
# ─────────────────────────────────────────────────────

import sys
import json
import textwrap
import structlog
from openai import OpenAI
from neo4j import GraphDatabase

log = structlog.get_logger()

# ── Config ────────────────────────────────────────────────────────
OLLAMA_BASE  = "http://localhost:11434/v1"
OLLAMA_MODEL = "qwen2.5"
NEO4J_URI    = "bolt://localhost:7687"
NEO4J_AUTH   = ("neo4j", "password")

DEFAULT_QUESTION = (
    "Is order 48213 on its way, and if it arrived damaged, "
    "am I covered by a guarantee?"
)

TRACE_CYPHER = """
MATCH (c:Customer)-[:PLACED]->(o:Order {order_id: $order_id})
OPTIONAL MATCH (o)-[:HANDLED_BY]->(car:Carrier)
MATCH (o)-[:SCANNED_AT]->(s:Scan)-[:AT_LOCATION]->(h:Hub)
OPTIONAL MATCH (s)-[:TRIGGERS]->(g:Guarantee)
RETURN c.name AS customer_name, o.order_id AS order_id, o.product AS product,
       o.order_date AS order_date, car.name AS carrier_name,
       s.scan_id AS scan_id, s.scan_time AS scan_time,
       s.scan_type AS scan_type, s.condition AS condition,
       h.location AS hub_location,
       g.guarantee_type AS guarantee_type, g.rule_ref AS guarantee_rule_ref
ORDER BY s.scan_time
"""


# ── 1. Tool definition ───────────────────────────────────────────
def build_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "trace_order",
            "description": textwrap.dedent("""
                Traverse the delivery knowledge graph for one order: walks
                Customer -> Order -> every Scan in its journey, each Scan's
                Hub, and Scan -> Guarantee if (and only if) that scan
                triggered one. Returns the full multi-hop journey in scan
                order, not just the latest scan. A scan_type of DEL with
                condition DAMAGED is what triggers a guarantee -- DEL alone
                does not. A null guarantee_type on every scan means no
                guarantee applies to this order, not that one was missed.
            """).strip(),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to trace, e.g. '48213'."
                    }
                },
                "required": ["order_id"]
            }
        }
    }


# ── 2. Execute the Cypher traversal against Neo4j ────────────────
def trace_order(order_id: str, driver: GraphDatabase.driver) -> str:
    log.info("graph.trace", order_id=order_id)
    with driver.session() as session:
        rows = session.run(TRACE_CYPHER, order_id=order_id).data()
    if not rows or rows[0]["scan_id"] is None:
        return f"No scan found for order {order_id}."

    guarantee_rows = [r for r in rows if r["guarantee_type"]]
    journey = {
        "customer_name": rows[0]["customer_name"],
        "order_id": rows[0]["order_id"],
        "product": rows[0]["product"],
        "order_date": rows[0]["order_date"],
        "carrier_name": rows[0]["carrier_name"],
        "scan_count": len(rows),
        "journey": [
            {
                "scan_id": r["scan_id"], "scan_time": r["scan_time"],
                "scan_type": r["scan_type"], "condition": r["condition"],
                "hub_location": r["hub_location"],
            }
            for r in rows
        ],
        "guarantee_type": guarantee_rows[0]["guarantee_type"] if guarantee_rows else None,
        "guarantee_rule_ref": guarantee_rows[0]["guarantee_rule_ref"] if guarantee_rows else None,
    }
    return json.dumps(journey, indent=2)


# ── 3. Two-turn agent loop ────────────────────────────────────────
def ask(question: str, tool: dict, client: OpenAI, driver: GraphDatabase.driver) -> None:
    log.info("graph.question", q=question)

    t1_messages = [
        {
            "role": "system",
            "content": (
                "You are a delivery support assistant. Use the trace_order "
                "tool to look up what the knowledge graph actually knows "
                "about an order before answering. Do not assume a guarantee "
                "applies unless the tool result shows a guarantee_type."
            )
        },
        {"role": "user", "content": question}
    ]

    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=t1_messages,
        tools=[tool],
        tool_choice="auto"
    )
    msg = response.choices[0].message

    if not msg.tool_calls:
        print("\n" + "=" * 60)
        print(msg.content)
        print("=" * 60)
        return

    tool_call = msg.tool_calls[0]
    params    = json.loads(tool_call.function.arguments)
    order_id  = params.get("order_id", "")
    result    = trace_order(order_id, driver)
    log.info("graph.result", result=result[:200])

    t2_messages = t1_messages + [
        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
        {"role": "tool", "content": result, "tool_call_id": tool_call.id},
        {
            "role": "user",
            "content": (
                "Using the graph trace above, answer the question in plain "
                "English. If guarantee_type is null, say clearly that no "
                "guarantee is linked to this scan. Do not call any tools."
            )
        }
    ]

    final = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=t2_messages,
        tools=[tool],
        tool_choice="none"
    )
    answer = final.choices[0].message.content

    if not answer and final.choices[0].message.tool_calls:
        answer = "(Model issued a second tool call instead of answering — try a simpler question.)"
    if not answer:
        answer = "(No answer generated.)"

    print("\n" + "=" * 60)
    print(answer)
    print("=" * 60)
    print("\nGraph trace (Cypher result):")
    print(result)


# ── 4. Main ───────────────────────────────────────────────────────
def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: cannot reach Neo4j at {NEO4J_URI} — is the container running?")
        print(f"  {e}")
        sys.exit(1)

    tool   = build_tool()
    client = OpenAI(base_url=OLLAMA_BASE, api_key="ollama")

    ask(question, tool, client, driver)
    driver.close()


if __name__ == "__main__":
    main()
