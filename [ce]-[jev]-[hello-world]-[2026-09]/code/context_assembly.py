"""
context_assembly.py — Build a lean, query-aware context from Jev's decisions.

This is NOT a transcript. It assembles only what Jev scored visible for this
specific query. The frontier model never sees more than it needs.
"""

from chunk_store import ChunkStore


_SECTION_HEADER = {
    "goal":        "## CURRENT TASK",
    "file":        "## SOURCE FILE",
    "tool_output": "## TOOL OUTPUT",
    "rule":        "## RULES",
    "reasoning":   "## PRIOR REASONING",
}


def assemble(store: ChunkStore, query: str) -> str:
    """
    Build the context string the frontier model will receive.
    Sections are ordered by chunk type so the prompt is always predictable.
    """
    type_order = ["goal", "rule", "file", "tool_output", "reasoning"]
    buckets: dict[str, list[str]] = {t: [] for t in type_order}

    for chunk_id in store.all_ids():
        chunk = store.get(chunk_id)
        rendered = chunk.render()
        if rendered is None:
            continue
        bucket_key = chunk.type.value if chunk.type.value in buckets else "reasoning"
        buckets[bucket_key].append(rendered)

    parts = []
    for t in type_order:
        if buckets[t]:
            parts.append(_SECTION_HEADER[t])
            parts.extend(buckets[t])

    parts.append("## USER QUERY")
    parts.append(query)

    return "\n\n".join(parts)


def token_estimate(text: str) -> int:
    """Rough token count: ~4 chars per token."""
    return len(text) // 4


def show_assembly_report(store: ChunkStore, context: str) -> None:
    """Print a summary of what Jev included and excluded — the proof."""
    print("\n" + "─" * 60)
    print("CONTEXT ASSEMBLY REPORT")
    print("─" * 60)
    for chunk_id in store.all_ids():
        chunk = store.get(chunk_id)
        vis   = chunk.resolved_vis().value
        icon  = {"hidden": "✗", "short": "▸", "long": "▸▸", "full": "●"}[vis]
        print(f"  {icon}  {chunk_id:<30} [{vis}]")
    print(f"\n  Total context: ~{token_estimate(context):,} tokens")
    print("─" * 60 + "\n")
