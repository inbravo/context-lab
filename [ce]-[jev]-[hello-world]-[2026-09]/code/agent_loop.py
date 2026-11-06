"""
agent_loop.py — The Jev agent loop.

One turn:
  1. Jev decides  — cheap Haiku call → typed decisions (chunk visibility, model, tool, permit)
  2. Assemble     — build lean context from Jev's chunk scores
  3. Frontier     — Sonnet/Haiku call with assembled context + tiered tool schema
  4. Execute tool — if the model called a tool
  5. Store result — tool output becomes a new chunk; NOT appended to transcript

What this proves: two different queries against the same codebase produce two
different, lean contexts. Print the assembly report after each turn to see this.
"""

import os
import anthropic

from chunk_store import ChunkStore, Chunk, ChunkType, Visibility
import jev as jev_module
from context_assembly import assemble, show_assembly_report
from tools import TOOL_SNIPPETS, get_schema_for, run_tool

FRONTIER_MODEL = "claude-sonnet-5"
CHEAP_MODEL    = "claude-haiku-4-5-20251001"

MODEL_MAP = {
    "frontier": FRONTIER_MODEL,
    "cheap":    CHEAP_MODEL,
}

_FRONTIER_SYSTEM = """\
You are a coding assistant. Answer the user's query using the context provided.
The context was assembled specifically for this query — trust it.
If you need to read a file or run tests, call the appropriate tool.
Be concise. No preamble.

{tool_snippets}
"""


def run_turn(query: str, store: ChunkStore, client: anthropic.Anthropic, turn_n: int) -> str:
    print(f"\n{'═' * 60}")
    print(f"TURN {turn_n}  ▶  {query}")
    print('═' * 60)

    # ── Step 1: Jev decides ───────────────────────────────────────────────────
    print("\n[Jev] Scoring chunks…")
    decision = jev_module.decide(query, store.catalogue(), client)
    print(f"[Jev] {decision.reasoning}")
    print(f"[Jev] model_tier={decision.model_tier}  tool={decision.tool_pick}  permit={decision.permit}")

    if not decision.permit:
        return "Jev denied this action."

    # ── Step 2: Apply visibility + assemble context ───────────────────────────
    store.apply_decisions(decision.chunk_visibility)
    context = assemble(store, query)
    show_assembly_report(store, context)

    # ── Step 3: Frontier call — with only the tool Jev picked ─────────────────
    model   = MODEL_MAP.get(decision.model_tier, FRONTIER_MODEL)
    tools   = []
    schema  = get_schema_for(decision.tool_pick)
    if schema:
        tools.append(schema)

    system_prompt = _FRONTIER_SYSTEM.format(tool_snippets=TOOL_SNIPPETS)

    messages = [{"role": "user", "content": context}]

    print(f"[Frontier → {model}] Thinking…")
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        tools=tools if tools else anthropic.NOT_GIVEN,
        messages=messages,
    )

    # ── Step 4: Execute tool if called ───────────────────────────────────────
    answer = ""
    while response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")
        tool_name  = tool_block.name
        tool_input = tool_block.input

        print(f"[Tool] {tool_name}({tool_input})")
        result = run_tool(tool_name, tool_input)
        print(f"[Tool] result: {result[:120]}…" if len(result) > 120 else f"[Tool] result: {result}")

        # Store tool output as a chunk (NOT appended to a growing transcript)
        store.update_or_add(Chunk(
            id          = f"tool_out_{turn_n}",
            type        = ChunkType.TOOL_OUTPUT,
            content     = result,
            summary     = f"Output of {tool_name}({list(tool_input.values())})",
            default_vis = Visibility.SHORT,
        ))

        # Continue the conversation with tool result
        messages = messages + [
            {"role": "assistant", "content": response.content},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": result}]},
        ]
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

    answer = next((b.text for b in response.content if hasattr(b, "text")), "")

    # Store reasoning as a chunk so future turns can reference it if Jev scores it visible
    store.update_or_add(Chunk(
        id          = f"reasoning_{turn_n}",
        type        = ChunkType.REASONING,
        content     = answer,
        summary     = answer[:120] + "…" if len(answer) > 120 else answer,
        default_vis = Visibility.HIDDEN,
    ))

    # ── Step 5: Reset per-turn visibility ─────────────────────────────────────
    store.reset_visibility()

    print(f"\n[Answer]\n{answer}")
    return answer


def build_store() -> ChunkStore:
    """Seed the chunk store with the sample codebase and rules."""
    from pathlib import Path
    store       = ChunkStore()
    code_dir    = Path(__file__).parent / "sample_codebase"

    store.add(Chunk(
        id="style_guide",
        type=ChunkType.RULE,
        content="- Max line length: 88\n- No bare except clauses\n- All public functions need a docstring\n- SQL queries must use parameterised inputs",
        summary="Code style rules: line length 88, no bare except, docstrings required, parameterised SQL",
        default_vis=Visibility.HIDDEN,
    ))

    for py_file in sorted(code_dir.glob("*.py")):
        if py_file.name.startswith("test_"):
            continue
        content = py_file.read_text()
        store.add(Chunk(
            id          = py_file.name,
            type        = ChunkType.FILE,
            content     = content,
            summary     = f"Source file: {py_file.name} ({len(content.splitlines())} lines)",
            default_vis = Visibility.HIDDEN,
        ))

    return store


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    client = anthropic.Anthropic(api_key=api_key)
    store  = build_store()

    # ── Two queries — watch Jev assemble different contexts each time ─────────
    queries = [
        "What does the auth module do? Explain the token validation logic.",
        "There is a SQL injection risk in db.py — find it and show the fix.",
    ]

    for i, q in enumerate(queries, 1):
        run_turn(q, store, client, i)

    print("\n" + "═" * 60)
    print("DONE — compare the two assembly reports above.")
    print("Same codebase. Different queries. Different contexts. That is Jev.")
    print("═" * 60)


if __name__ == "__main__":
    main()
