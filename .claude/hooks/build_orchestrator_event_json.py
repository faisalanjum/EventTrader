#!/usr/bin/env -S uv run --script

# /// script
# dependencies = []
# ///

"""
Claude Code hook: build/refresh a per-ticker earnings events manifest after discovery.

Trigger: PostToolUse on Bash. We only act when the Bash command includes
``get_quarterly_filings.py``.

Input: hook JSON on stdin (tool_input.command, tool_response.stdout).
Output: always prints ``{}`` and exits 0 (never blocks the agent).

Design: this is a THIN WRAPPER around the shared helpers in
``.claude/skills/earnings-orchestrator/scripts/event_json_manifest.py``.
All parsing, manifest building, and atomic write logic lives there so the
orchestrator's auto-regen path (which cannot depend on Claude Code's hook
runner) produces byte-identical output.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Optional

# Path to the shared helper module — same repo layout on the production machine.
_REPO_ROOT = Path("/home/faisal/EventMarketDB")
_SHARED_HELPERS_DIR = _REPO_ROOT / ".claude" / "skills" / "earnings-orchestrator" / "scripts"
if str(_SHARED_HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_HELPERS_DIR))

from event_json_manifest import (  # noqa: E402
    COMPANIES_DIR,
    atomic_write_json,
    build_manifest,
    parse_column_table,
    parse_pipe_table,
)

TARGET_SCRIPT_BASENAME = "get_quarterly_filings.py"
TARGET_CMD_BASENAME = "get_quarterly_filings"


def _json_ok() -> None:
    # Claude expects JSON output from hooks.
    sys.stdout.write("{}")


def _extract_ticker_from_command(command: str) -> Optional[str]:
    try:
        parts = shlex.split(command)
    except Exception:
        parts = command.split()

    for i, p in enumerate(parts):
        base = Path(p).name
        if base in (TARGET_SCRIPT_BASENAME, TARGET_CMD_BASENAME):
            if i + 1 < len(parts):
                t = parts[i + 1]
                if t.startswith("-"):
                    return None
                return t.strip().upper()
    return None


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _json_ok()
            return

        hook = json.loads(raw)
        command = (hook.get("tool_input") or {}).get("command") or ""
        ticker = _extract_ticker_from_command(command)
        if not ticker:
            _json_ok()
            return

        stdout = (hook.get("tool_response") or {}).get("stdout") or ""
        table = parse_pipe_table(stdout) or parse_column_table(stdout)
        if not table:
            _json_ok()
            return

        manifest = build_manifest(ticker, table)
        out_path = COMPANIES_DIR / ticker / "events" / "event.json"
        atomic_write_json(out_path, manifest)
        _json_ok()
    except Exception:
        # Never block/interrupt the agent. Best-effort only.
        _json_ok()


if __name__ == "__main__":
    main()
