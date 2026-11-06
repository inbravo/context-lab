"""
jev.py — The decision model.

Jev is NOT the code writer. It is a cheap, fast model that answers per-turn
questions about context, routing, and tool selection — returning typed answers,
not prose. The frontier model never decides what it sees; Jev does.

Decision questions (from Table I of the whitepaper):
  Context   — How visible should each chunk be for this query?
  Cache     — Reuse existing context or rebuild from scratch?
  Routing   — Which model tier should handle this subtask?
  Tools     — Which tool fits this intent?
  Permit    — Should this action run?
"""

import json
import os
from dataclasses import dataclass

import anthropic

JEV_MODEL = "claude-haiku-4-5-20251001"   # cheap + fast — Jev's job is decisions, not generation

VISIBILITY_OPTIONS = ["hidden", "short", "long", "full"]
MODEL_TIERS        = ["frontier", "cheap"]
TOOL_OPTIONS       = ["read_file", "run_tests", "none"]


@dataclass
class JevDecision:
    chunk_visibility: dict[str, str]   # chunk_id → "hidden"|"short"|"long"|"full"
    model_tier:       str              # "frontier" | "cheap"
    tool_pick:        str              # "read_file" | "run_tests" | "none"
    permit:           bool             # whether the chosen action is safe to run
    reasoning:        str              # Jev's one-line rationale (not sent to frontier)


_JEV_TOOL = {
    "name": "jev_decide",
    "description": "Return per-turn decisions about context visibility, model tier, tool, and permission.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chunk_visibility": {
                "type": "object",
                "description": "Map of chunk_id to visibility level for this query.",
                "additionalProperties": {
                    "type": "string",
                    "enum": VISIBILITY_OPTIONS,
                }
            },
            "model_tier": {
                "type": "string",
                "enum": MODEL_TIERS,
                "description": "Which model tier should handle the frontier call.",
            },
            "tool_pick": {
                "type": "string",
                "enum": TOOL_OPTIONS,
                "description": "Which tool the frontier model will likely need.",
            },
            "permit": {
                "type": "boolean",
                "description": "Whether the action is safe to proceed.",
            },
            "reasoning": {
                "type": "string",
                "description": "One-sentence rationale. Not shown to frontier model.",
            },
        },
        "required": ["chunk_visibility", "model_tier", "tool_pick", "permit", "reasoning"],
    },
}

_SYSTEM = """\
You are Jev — a context and routing decision engine for a coding agent.
You are NOT the model that writes code. You make fast, typed decisions.

Your job each turn:
1. Score every available chunk's visibility for the current query (hidden/short/long/full).
   - full:   the chunk is central to answering this query
   - long:   useful background, show first 600 chars
   - short:  exists but peripheral — show summary only
   - hidden: irrelevant to this query — omit entirely
2. Decide which model tier to use (frontier for complex reasoning, cheap for simple edits).
3. Pick the most relevant tool, or "none".
4. Decide whether the action is safe to permit.

Principle: the frontier model should see the minimum context needed — nothing more.
Every token you include that isn't necessary is waste.
"""


def decide(query: str, chunk_catalogue: str, client: anthropic.Anthropic) -> JevDecision:
    """
    One cheap Jev call per turn. Returns typed decisions.
    chunk_catalogue: output of ChunkStore.catalogue() — one line per chunk.
    """
    user_msg = f"""Current query: {query}

Available chunks:
{chunk_catalogue}

Decide visibility for every chunk listed above. Score aggressively — most chunks
should be hidden or short for any given query."""

    response = client.messages.create(
        model=JEV_MODEL,
        max_tokens=512,
        system=_SYSTEM,
        tools=[_JEV_TOOL],
        tool_choice={"type": "tool", "name": "jev_decide"},
        messages=[{"role": "user", "content": user_msg}],
    )

    tool_input = next(b.input for b in response.content if b.type == "tool_use")
    return JevDecision(
        chunk_visibility = tool_input["chunk_visibility"],
        model_tier       = tool_input["model_tier"],
        tool_pick        = tool_input["tool_pick"],
        permit           = tool_input["permit"],
        reasoning        = tool_input["reasoning"],
    )
