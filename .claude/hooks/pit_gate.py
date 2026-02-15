#!/usr/bin/env python3
"""
pit_gate.py — Deterministic PIT gate for data subagent hooks.

PostToolUse hook. Reads hook JSON from stdin.
Outputs {} (allow) or {"decision":"block","reason":"..."} (block).
Exit code: always 0.

Spec: .claude/plans/DataSubAgents.md §4.4-4.5
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Constants (hardcoded, no config file dependency) ─────────────────

VALID_SOURCES: frozenset[str] = frozenset({
    "neo4j_created",
    "edgar_accepted",
    "time_series_timestamp",
    "provider_metadata",
})

FORBIDDEN_KEYS: frozenset[str] = frozenset({
    "daily_stock", "hourly_stock", "session_stock",
    "daily_return",
    "daily_macro", "daily_industry", "daily_sector",
    "hourly_macro", "hourly_industry", "hourly_sector",
})

WRAPPER_SCRIPTS: tuple[str, ...] = ("pit_fetch.py",)

LOG_PATH: Path = Path(__file__).resolve().parent / "pit_gate.log"

# ── Compiled regexes ─────────────────────────────────────────────────

DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DATETIME_TZ_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)

BASH_PIT_RE = re.compile(r"--pit[= ](\S+)")

# ── Reason codes ─────────────────────────────────────────────────────

PIT_PARSE_ERROR = "PIT_PARSE_ERROR"
PIT_INVALID_PIT = "PIT_INVALID_PIT"
PIT_INVALID_JSON = "PIT_INVALID_JSON"
PIT_MISSING_ENVELOPE = "PIT_MISSING_ENVELOPE"
PIT_INVALID_ITEM_TYPE = "PIT_INVALID_ITEM_TYPE"
PIT_MISSING_AVAILABLE_AT = "PIT_MISSING_AVAILABLE_AT"
PIT_INVALID_AVAILABLE_AT_FORMAT = "PIT_INVALID_AVAILABLE_AT_FORMAT"
PIT_MISSING_TZ = "PIT_MISSING_TZ"
PIT_INVALID_AVAILABLE_AT_SOURCE = "PIT_INVALID_AVAILABLE_AT_SOURCE"
PIT_VIOLATION_GT_CUTOFF = "PIT_VIOLATION_GT_CUTOFF"
PIT_FORBIDDEN_FIELD = "PIT_FORBIDDEN_FIELD"

# ── Helpers ──────────────────────────────────────────────────────────


def _log(msg: str) -> None:
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _allow() -> None:
    sys.stdout.write("{}\n")
    sys.stdout.flush()


def _block(code: str, detail: str) -> None:
    out = {"decision": "block", "reason": f"{code}: {detail}"}
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()


# ── Core functions ───────────────────────────────────────────────────


def parse_iso8601(s: str) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if DATE_ONLY_RE.match(s):
        return None
    if not DATETIME_TZ_RE.match(s):
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        return None
    return dt


def extract_pit(tool_input: dict) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    # 1. tool_input.parameters.pit (generic nested — keep for non-Neo4j tools)
    parameters = tool_input.get("parameters")
    if isinstance(parameters, dict):
        pit = parameters.get("pit")
        if isinstance(pit, str) and pit.strip():
            return pit.strip()
    # 2. tool_input.params.pit (Neo4j MCP Cypher parameter dict)
    params = tool_input.get("params")
    if isinstance(params, dict):
        pit = params.get("pit")
        if isinstance(pit, str) and pit.strip():
            return pit.strip()
    # 3. tool_input.pit (flat fallback)
    pit = tool_input.get("pit")
    if isinstance(pit, str) and pit.strip():
        return pit.strip()
    # 4. Bash --pit flag
    command = tool_input.get("command")
    if isinstance(command, str):
        m = BASH_PIT_RE.search(command)
        if m:
            return m.group(1).strip().strip("\"'")
    return None


def extract_payload(tool_response: object) -> str | None:
    # MCP response: [{"type":"text","text":"..."}]
    if isinstance(tool_response, list) and tool_response:
        first = tool_response[0]
        if isinstance(first, dict) and "text" in first:
            return first["text"]
    if isinstance(tool_response, dict):
        # MCP wrapped: {"result":[{"type":"text","text":"..."}]}
        result = tool_response.get("result")
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict) and "text" in first:
                return first["text"]
        if "stdout" in tool_response:
            v = tool_response["stdout"]
            if not v:
                return None
            return json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        return json.dumps(tool_response)
    if isinstance(tool_response, str):
        return tool_response if tool_response.strip() else None
    return None


def scan_forbidden_keys(obj: object, depth: int = 0) -> str | None:
    if depth > 50:
        return None
    if isinstance(obj, dict):
        for key in obj:
            if isinstance(key, str) and key.lower() in FORBIDDEN_KEYS:
                return key
            found = scan_forbidden_keys(obj[key], depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = scan_forbidden_keys(item, depth + 1)
            if found:
                return found
    return None


def validate_item(
    item: object, pit_dt: datetime, idx: int
) -> tuple[str, str] | None:
    if not isinstance(item, dict):
        return (PIT_INVALID_ITEM_TYPE, f"data[{idx}] is not an object")

    available_at = item.get("available_at")
    if not available_at or not isinstance(available_at, str):
        return (PIT_MISSING_AVAILABLE_AT, f"data[{idx}] missing available_at")
    available_at = available_at.strip()

    if DATE_ONLY_RE.match(available_at):
        return (
            PIT_INVALID_AVAILABLE_AT_FORMAT,
            f"data[{idx}] available_at is date-only: {available_at}",
        )

    if not DATETIME_TZ_RE.match(available_at):
        # Distinguish missing-tz from unparseable
        try:
            test_s = available_at
            if test_s.endswith("Z"):
                test_s = test_s[:-1] + "+00:00"
            test_dt = datetime.fromisoformat(test_s)
            if test_dt.tzinfo is None:
                return (
                    PIT_MISSING_TZ,
                    f"data[{idx}] available_at missing timezone: {available_at}",
                )
        except (ValueError, TypeError):
            pass
        return (
            PIT_INVALID_AVAILABLE_AT_FORMAT,
            f"data[{idx}] unparseable available_at: {available_at}",
        )

    dt = parse_iso8601(available_at)
    if dt is None:
        return (
            PIT_INVALID_AVAILABLE_AT_FORMAT,
            f"data[{idx}] unparseable available_at: {available_at}",
        )

    source = item.get("available_at_source")
    if (
        not source
        or not isinstance(source, str)
        or source.strip() not in VALID_SOURCES
    ):
        return (
            PIT_INVALID_AVAILABLE_AT_SOURCE,
            f"data[{idx}] invalid available_at_source: {source!r}",
        )

    if dt > pit_dt:
        return (
            PIT_VIOLATION_GT_CUTOFF,
            f"data[{idx}].available_at {available_at} > PIT {pit_dt.isoformat()}",
        )

    return None


# ── Entry point ──────────────────────────────────────────────────────


def main() -> None:
    pit_detected = False
    tool_name = "unknown"

    try:
        raw = sys.stdin.read()
        if not raw or not raw.strip():
            _allow()
            return

        try:
            hook = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            _log("BLOCK stdin unparseable")
            _block(PIT_PARSE_ERROR, "Hook input is not valid JSON")
            return

        tool_name = hook.get("tool_name", "unknown")
        tool_input = hook.get("tool_input") or {}
        tool_response = hook.get("tool_response")

        # ── Extract PIT ──
        pit_str = extract_pit(tool_input)
        if not pit_str:
            _log(f"ALLOW tool={tool_name} (open mode)")
            _allow()
            return

        pit_detected = True

        # ── Parse PIT timestamp ──
        pit_dt = parse_iso8601(pit_str)
        if pit_dt is None:
            _log(f"BLOCK tool={tool_name} invalid_pit={pit_str}")
            _block(PIT_INVALID_PIT, f"Unparseable PIT timestamp: {pit_str}")
            return

        # ── Bash belt-and-suspenders ──
        if "Bash" in tool_name or "bash" in tool_name:
            command = tool_input.get("command", "")
            if not any(w in command for w in WRAPPER_SCRIPTS):
                _log(f"ALLOW tool={tool_name} (non-wrapper Bash)")
                _allow()
                return

        # ── Extract payload ──
        payload_str = extract_payload(tool_response)
        if not payload_str or not payload_str.strip():
            _log(f"BLOCK tool={tool_name} empty payload")
            _block(PIT_INVALID_JSON, "Empty tool output in PIT mode")
            return

        # ── Parse payload JSON ──
        try:
            payload = json.loads(payload_str)
        except (json.JSONDecodeError, TypeError):
            _log(f"BLOCK tool={tool_name} json parse fail")
            _block(PIT_INVALID_JSON, "Tool output is not valid JSON in PIT mode")
            return

        # Unwrap single-record Cypher result: [{"data":[...],...}] → {"data":...}
        if isinstance(payload, list):
            if (
                len(payload) == 1
                and isinstance(payload[0], dict)
                and "data" in payload[0]
            ):
                payload = payload[0]
            else:
                _block(
                    PIT_MISSING_ENVELOPE,
                    "Tool output is array"
                    + (" (multi-record)" if len(payload) > 1 else "")
                    + "; expected single-record envelope",
                )
                return

        if not isinstance(payload, dict):
            _block(PIT_INVALID_JSON, "Tool output is not a JSON object")
            return

        # ── Forbidden keys (defense-in-depth) ──
        forbidden = scan_forbidden_keys(payload)
        if forbidden:
            _log(f"BLOCK tool={tool_name} forbidden_key={forbidden}")
            _block(PIT_FORBIDDEN_FIELD, f"Forbidden return-data field: {forbidden}")
            return

        # ── Validate envelope ──
        data = payload.get("data")
        if data is None:
            _log(f"BLOCK tool={tool_name} missing data[]")
            _block(PIT_MISSING_ENVELOPE, "Missing data[] in response envelope")
            return

        if not isinstance(data, list):
            _block(PIT_MISSING_ENVELOPE, "data is not an array")
            return

        if len(data) == 0:
            _log(f"ALLOW tool={tool_name} items=0 (clean gap)")
            _allow()
            return

        # ── Per-item validation ──
        for i, item in enumerate(data):
            result = validate_item(item, pit_dt, i)
            if result is not None:
                code, detail = result
                _log(f"BLOCK tool={tool_name} {code}: {detail}")
                _block(code, detail)
                return

        _log(f"ALLOW tool={tool_name} items={len(data)}")
        _allow()

    except Exception as e:
        if pit_detected:
            _log(f"BLOCK tool={tool_name} unexpected: {e}")
            _block(PIT_PARSE_ERROR, f"Internal gate error: {e}")
        else:
            _log(f"ALLOW tool={tool_name} unexpected: {e}")
            _allow()


if __name__ == "__main__":
    main()
