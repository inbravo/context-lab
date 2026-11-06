"""
chunk_store.py — Explicit, typed, addressable state.

This replaces the append-only transcript. Every piece of context is a named
chunk with a type, content, a short summary, and a default visibility level.
Jev scores each chunk per query and overrides visibility before assembly.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChunkType(str, Enum):
    GOAL        = "goal"        # the user's current task
    FILE        = "file"        # source file content
    TOOL_OUTPUT = "tool_output" # output from a previous tool call
    RULE        = "rule"        # style guide / constraint
    REASONING   = "reasoning"   # model's prior reasoning (stored, not re-sent by default)


class Visibility(str, Enum):
    HIDDEN = "hidden"   # not included in context
    SHORT  = "short"    # summary only (~1-2 sentences)
    LONG   = "long"     # first 600 chars of content
    FULL   = "full"     # entire content


@dataclass
class Chunk:
    id:          str
    type:        ChunkType
    content:     str
    summary:     str                        # used when visibility=SHORT
    default_vis: Visibility = Visibility.HIDDEN
    # set by Jev each turn; reverts to default_vis between turns
    current_vis: Optional[Visibility] = field(default=None, repr=False)

    def resolved_vis(self) -> Visibility:
        return self.current_vis if self.current_vis is not None else self.default_vis

    def render(self) -> Optional[str]:
        vis = self.resolved_vis()
        if vis == Visibility.HIDDEN:
            return None
        if vis == Visibility.SHORT:
            return f"[{self.id}] {self.summary}"
        if vis == Visibility.LONG:
            return f"[{self.id}]\n{self.content[:600]}" + ("…" if len(self.content) > 600 else "")
        return f"[{self.id}]\n{self.content}"


class ChunkStore:
    def __init__(self):
        self._chunks: dict[str, Chunk] = {}

    def add(self, chunk: Chunk) -> None:
        self._chunks[chunk.id] = chunk

    def get(self, chunk_id: str) -> Optional[Chunk]:
        return self._chunks.get(chunk_id)

    def all_ids(self) -> list[str]:
        return list(self._chunks.keys())

    def catalogue(self) -> str:
        """One-line description of every chunk — fed to Jev so it knows what exists."""
        lines = []
        for c in self._chunks.values():
            lines.append(f"  {c.id:<30} type={c.type.value:<12} default={c.default_vis.value}  | {c.summary}")
        return "\n".join(lines)

    def apply_decisions(self, visibility_map: dict[str, str]) -> None:
        """Apply Jev's per-turn visibility decisions."""
        for chunk_id, vis_str in visibility_map.items():
            if chunk_id in self._chunks:
                self._chunks[chunk_id].current_vis = Visibility(vis_str)

    def reset_visibility(self) -> None:
        """Clear per-turn overrides after a turn completes."""
        for c in self._chunks.values():
            c.current_vis = None

    def update_or_add(self, chunk: Chunk) -> None:
        """Store a new chunk (e.g. tool output) produced during a turn."""
        self._chunks[chunk.id] = chunk
