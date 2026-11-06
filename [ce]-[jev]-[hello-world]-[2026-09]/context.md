# Context — CE Jev Hello World

**What this is:** A minimal implementation of the Jev Engineering pattern from the TypeSafe whitepaper
(Diogo Almeida, September 2026). Proves the core thesis: a cheap model deciding what context
to assemble per turn beats an expensive model reading a growing transcript.

## The one thing being proved

Given the same codebase and two different questions, the frontier model should receive a
different, lean context each time — assembled on purpose by Jev, not accumulated by accident.

## Source

"Jev Engineering for Coding Agents" — independent synthesis of TypeSafe design notes.
Not affiliated with or endorsed by TypeSafe.

## Knowledge files loaded

None — this is a self-contained hello world.

## Stack

- Python 3.11+
- Anthropic SDK (claude-haiku-4-5-20251001 for Jev decisions, claude-sonnet-5 for frontier)
- Structured output via tool_use / response schema
- No frameworks, no vector stores, no databases
