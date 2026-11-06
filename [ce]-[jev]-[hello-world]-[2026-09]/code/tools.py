"""
tools.py — Tiered tool disclosure (Section VII of the whitepaper).

Tier 1  SNIPPETS   — one-line descriptions, always in system prompt
Tier 2  SCHEMA     — full argument schema, loaded when Jev picks this tool
Tier 3  DOCS       — extended usage notes, loaded only if model asks

The frontier model never sees all schemas at once. Jev picks the tool;
only that tool's full schema is included in the context.
"""

import subprocess
from pathlib import Path


# ── Tier 1: snippets (always shown in system prompt) ─────────────────────────
TOOL_SNIPPETS = """\
Available tools (request by name):
  read_file   — read a source file from the sample codebase
  run_tests   — run the test suite and return pass/fail + output
"""

# ── Tier 2: schemas (loaded on demand by Jev's tool_pick) ────────────────────
TOOL_SCHEMAS = {
    "read_file": {
        "name": "read_file",
        "description": "Read a file from the sample codebase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename relative to sample_codebase/, e.g. 'auth.py'",
                }
            },
            "required": ["filename"],
        },
    },
    "run_tests": {
        "name": "run_tests",
        "description": "Run the sample test suite. Returns pass/fail counts and any failures.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

CODEBASE_DIR = Path(__file__).parent / "sample_codebase"


def get_schema_for(tool_name: str) -> dict | None:
    return TOOL_SCHEMAS.get(tool_name)


def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "read_file":
        return _read_file(tool_input.get("filename", ""))
    if tool_name == "run_tests":
        return _run_tests()
    return f"Unknown tool: {tool_name}"


def _read_file(filename: str) -> str:
    path = CODEBASE_DIR / filename
    if not path.exists():
        available = [f.name for f in CODEBASE_DIR.glob("*.py")]
        return f"File not found: {filename}\nAvailable: {available}"
    return path.read_text()


def _run_tests() -> str:
    result = subprocess.run(
        ["python", "-m", "pytest", str(CODEBASE_DIR / "test_sample.py"), "-v", "--tb=short"],
        capture_output=True, text=True, cwd=str(CODEBASE_DIR)
    )
    output = result.stdout + result.stderr
    return output[:3000] if len(output) > 3000 else output
