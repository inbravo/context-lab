# CE Jev Hello World

**Concept:** Jev Engineering — context assembled on purpose, not accumulated by accident.

Based on design notes by Diogo Almeida (TypeSafe), September 2026.
Independent implementation for study. Not affiliated with or endorsed by TypeSafe.

---

## The thesis in one sentence

A cheap model deciding *what context to show* per turn is more effective than an expensive model
reading a growing transcript. Jev is that cheap model.

## The proof this demo runs

Two questions. Same codebase. Watch the assembly reports:

```
Query 1: "What does the auth module do?"
  → auth.py:  [●  full]      db.py: [✗ hidden]    api.py: [▸ short]
  → ~400 tokens sent to frontier model

Query 2: "Find the SQL injection risk in db.py"
  → auth.py:  [✗ hidden]    db.py: [●  full]     api.py: [▸ short]
  → ~350 tokens sent to frontier model
```

The frontier model never sees more than it needs. Context is assembled, not accumulated.

## Architecture

```
User query
    │
    ▼
[Jev — Haiku]  ←── chunk catalogue (ids + summaries)
    │ typed decisions: visibility map, model tier, tool pick, permit
    ▼
[Context Assembly]  ←── chunk store (auth.py, db.py, api.py, style_guide, tool outputs)
    │ lean, query-aware prompt
    ▼
[Frontier — Sonnet]  ←── only the schema for the tool Jev picked
    │ may call read_file or run_tests
    ▼
[Tool execution]
    │ result stored as new chunk (NOT appended to transcript)
    ▼
[Answer]
```

## Files

```
code/
├── chunk_store.py          — typed, addressable state (not a transcript)
├── jev.py                  — decision model: Haiku + structured output
├── context_assembly.py     — assembles prompt from Jev's visibility scores
├── tools.py                — tiered tool disclosure (snippets → schema → docs)
├── agent_loop.py           — the loop: Jev → assemble → frontier → tool → store
└── sample_codebase/
    ├── auth.py             — HMAC token auth (no SQL, scores hidden for DB queries)
    ├── db.py               — SQLite layer with a deliberate SQL injection bug
    ├── api.py              — handler layer wiring auth + db
    └── test_sample.py      — auth unit tests
```

## Quick start

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...

cd code/
python agent_loop.py
```

## What to look for in the output

After each turn, the **CONTEXT ASSEMBLY REPORT** prints which chunks were included and at
what visibility level. Compare the two reports — different chunks, different sizes, same store.

## The six problems Jev addresses

| Problem in current agents | Jev's fix |
|---|---|
| Routing fails — cheap model reloads full context | Route priced per context rebuild, not per token |
| Tools crowd context window | Tiered disclosure: snippets always, schema on demand |
| Compaction loses what matters | Visibility ladder per chunk per query |
| Sub-agents rarely worth spawning | Cheap context building makes them practical |
| Restart throws away good state | Reload only relevant chunks |
| Built-ins cost context forever | Near-zero cost when disclosed in tiers |
