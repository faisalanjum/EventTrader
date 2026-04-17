#!/usr/bin/env python3
"""PreToolUse Write hook: validates attribution/result.json before disk write.

Calls the SAME canonical validator from validate_attribution.py (stdlib-only).
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

    # Only validate attribution result files
    if not file_path.endswith("/attribution/result.json"):
        print("{}")
        return

    content = hook_input.get("tool_input", {}).get("content", "")
    if not content:
        print(json.dumps({"decision": "block", "reason": "attribution/result.json content is empty"}))
        return

    # Parse JSON content
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as e:
        print(json.dumps({"decision": "block", "reason": f"attribution/result.json is not valid JSON: {e}"}))
        return

    if not isinstance(payload, dict):
        print(json.dumps({"decision": "block", "reason": "attribution/result.json must be a JSON object"}))
        return

    # Extract expected ticker/quarter from the payload itself
    expected_ticker = str(payload.get("ticker", ""))
    expected_quarter = str(payload.get("quarter_label", ""))

    if not expected_ticker or not expected_quarter:
        print(json.dumps({"decision": "block", "reason": "attribution/result.json missing ticker or quarter_label"}))
        return

    # Import the canonical validator (stdlib-only, no heavy deps)
    # FAIL CLOSED: if import fails, block the write — do NOT allow bad output through
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    # Amendment 2026-04-17: project_dir must be on sys.path BEFORE scripts/earnings,
    # because validate_attribution now imports `from config.canonical_sectors import ...`
    # and `config/` lives at the repo root.
    sys.path.insert(0, project_dir)
    sys.path.insert(0, os.path.join(project_dir, "scripts", "earnings"))

    try:
        from validate_attribution import validate_attribution_result
    except ImportError as e:
        print(json.dumps({
            "decision": "block",
            "reason": f"attribution validator import failed (fail-closed): {e}"
        }))
        return

    try:
        errors = validate_attribution_result(payload, expected_ticker, expected_quarter)
    except Exception as e:
        # Fail CLOSED on any validator execution error
        print(json.dumps({"decision": "block", "reason": f"attribution validator crashed (fail-closed): {e}"}))
        return

    if errors:
        reason = "; ".join(errors[:3])  # first 3 errors to keep message compact
        if len(errors) > 3:
            reason += f" (and {len(errors) - 3} more)"
        print(json.dumps({"decision": "block", "reason": f"attribution validation failed: {reason}"}))
    else:
        print("{}")


if __name__ == "__main__":
    main()
