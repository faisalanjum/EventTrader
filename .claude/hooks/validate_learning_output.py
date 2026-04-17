#!/usr/bin/env python3
"""PreToolUse Write hook: validates learning/result.json before disk write.

Renamed from validate_attribution_output.py (2026-04-17). The match path
updated from /attribution/result.json to /learning/result.json alongside
the folder rename. The validator FUNCTION name
``validate_attribution_result`` is UNCHANGED (schema strings stay).

Calls the SAME canonical validator from validate_learning.py (stdlib-only).
No duplicated schema logic — single source of truth.
Fails CLOSED: if the validator cannot be imported, the write is BLOCKED.

Hook contract:
  stdin:  hook JSON with tool_input.file_path and tool_input.content
  stdout: {} (allow) or {"decision":"block","reason":"..."} (block)
  exit:   always 0
"""
import json
import sys
import os


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        print("{}")
        return

    file_path = hook_input.get("tool_input", {}).get("file_path", "")

    # Match the learning/ path literal (post-rename). Old attribution/ path
    # falls through (returns allow) — the migration's --apply renames the
    # dir atomically, so any attribution/result.json write during the
    # migration window is on a pre-rename file and is harmless.
    if not file_path.endswith("/learning/result.json"):
        print("{}")
        return

    content = hook_input.get("tool_input", {}).get("content", "")
    if not content:
        print(json.dumps({"decision": "block", "reason": "learning/result.json content is empty"}))
        return

    # Parse JSON content
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as e:
        print(json.dumps({"decision": "block", "reason": f"learning/result.json is not valid JSON: {e}"}))
        return

    if not isinstance(payload, dict):
        print(json.dumps({"decision": "block", "reason": "learning/result.json must be a JSON object"}))
        return

    # Extract expected ticker/quarter from the payload itself
    expected_ticker = str(payload.get("ticker", ""))
    expected_quarter = str(payload.get("quarter_label", ""))

    if not expected_ticker or not expected_quarter:
        print(json.dumps({"decision": "block", "reason": "learning/result.json missing ticker or quarter_label"}))
        return

    # Import the canonical validator (stdlib-only, no heavy deps)
    # FAIL CLOSED: if import fails, block the write — do NOT allow bad output through.
    # project_dir must be on sys.path BEFORE scripts/earnings, because
    # validate_learning imports `from config.canonical_sectors import ...`
    # and `config/` lives at the repo root.
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    sys.path.insert(0, project_dir)
    sys.path.insert(0, os.path.join(project_dir, "scripts", "earnings"))

    try:
        # Module renamed to validate_learning; function name UNCHANGED
        # (validate_attribution_result maps to schema attribution_result.v2).
        from validate_learning import validate_attribution_result
    except ImportError as e:
        print(json.dumps({
            "decision": "block",
            "reason": f"learning validator import failed (fail-closed): {e}"
        }))
        return

    try:
        errors = validate_attribution_result(payload, expected_ticker, expected_quarter)
    except Exception as e:
        # Fail CLOSED on any validator execution error
        print(json.dumps({"decision": "block", "reason": f"learning validator crashed (fail-closed): {e}"}))
        return

    if errors:
        reason = "; ".join(errors[:3])  # first 3 errors to keep message compact
        if len(errors) > 3:
            reason += f" (and {len(errors) - 3} more)"
        print(json.dumps({"decision": "block", "reason": f"learning validation failed: {reason}"}))
    else:
        print("{}")


if __name__ == "__main__":
    main()
