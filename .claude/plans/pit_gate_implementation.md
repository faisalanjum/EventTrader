# pit_gate.py Implementation Plan

**Status**: Implementation-ready
**Implements**: `.claude/plans/DataSubAgents.md` §4.4-4.5 (PIT gate spec)
**Replaces**: `validate_pit_hook.sh`, `validate_neo4j.sh`, `validate_perplexity.sh`
**Final word on integration behavior**: `.claude/plans/earnings-orchestrator.md` (per DataSubAgents §9:619). If any discrepancy is still ambiguous or conflicts with implementation reality, stop and ask the user before proceeding (per DataSubAgents §9:620).

---

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `.claude/hooks/pit_gate.py` | The gate script (~140 lines) |
| 2 | `.claude/hooks/test_pit_gate.py` | Test harness (~200 lines) |

No other files are created or modified. Hook wiring in `.claude/settings.json` is documented but NOT applied in this implementation pass — it requires agent rework first (agents must output the standard envelope before the gate can validate it).

---

## 1. Script Contract

- **Path**: `.claude/hooks/pit_gate.py`
- **Shebang**: `#!/usr/bin/env python3`
- **Runtime**: Python 3.9+ stdlib only. No pip packages. No uv.
- **Imports**: `json`, `sys`, `re`, `datetime` (from datetime), `pathlib` (Path), `os` (only for log)
- **Input**: Hook JSON on stdin with `tool_name`, `tool_input`, `tool_response`
- **Output**: `{}` (allow) or `{"decision":"block","reason":"<CODE>: <detail>"}` (block)
- **Exit code**: Always `0`. Never non-zero. Blocking is via stdout JSON.
- **Encoding**: UTF-8

---

## 2. Constants (hardcoded at module top, no config file dependency)

```python
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
```

### Compiled regexes (module-level)

```python
# Matches YYYY-MM-DD only (no time component)
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Strict ISO8601 datetime with required T separator and required timezone.
# Accepts: 2024-02-15T16:00:00-05:00, 2024-02-15T16:00:00Z, 2024-02-15T16:00:00.123+00:00
# Rejects: 2024-02-15 16:00:00-05:00 (space), 2024-02-15T16:00:00 (no tz), 2024-02-15 (date-only)
DATETIME_TZ_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"   # YYYY-MM-DDTHH:MM:SS
    r"(?:\.\d+)?"                                # optional fractional seconds
    r"(?:Z|[+-]\d{2}:\d{2})$"                   # required: Z or ±HH:MM
)

# Extracts --pit value from Bash command string
BASH_PIT_RE = re.compile(r"--pit[= ](\S+)")
```

---

## 3. Reason Codes

Every block reason starts with a stable machine-readable prefix. Agents can switch on the prefix for retry logic.

| Code | Meaning |
|------|---------|
| `PIT_PARSE_ERROR` | stdin is non-empty but not valid JSON, or internal gate error in PIT mode |
| `PIT_INVALID_PIT` | PIT timestamp found but not a valid ISO8601 datetime with timezone |
| `PIT_INVALID_JSON` | Tool output is not valid JSON (or empty) in PIT mode |
| `PIT_MISSING_ENVELOPE` | Parsed JSON lacks `data` key or `data` is not an array |
| `PIT_INVALID_ITEM_TYPE` | `data[i]` is not a JSON object |
| `PIT_MISSING_AVAILABLE_AT` | `data[i]` has no `available_at` field |
| `PIT_INVALID_AVAILABLE_AT_FORMAT` | `available_at` is date-only or doesn't match strict datetime+tz format |
| `PIT_MISSING_TZ` | `available_at` parses as datetime but has no timezone info |
| `PIT_INVALID_AVAILABLE_AT_SOURCE` | `available_at_source` missing or not in `VALID_SOURCES` |
| `PIT_VIOLATION_GT_CUTOFF` | `available_at > PIT` (temporal contamination) |
| `PIT_FORBIDDEN_FIELD` | Forbidden return-data key found in JSON structure |

Format: `{"decision":"block","reason":"<CODE>: <human-readable detail>"}`.
Example: `{"decision":"block","reason":"PIT_VIOLATION_GT_CUTOFF: data[2].available_at 2024-02-20T10:00:00-05:00 > PIT 2024-02-15T16:00:00-05:00"}`

---

## 4. Functions — Signatures, Behavior, Edge Cases

### 4.1 `_log(msg: str) -> None`

Append one timestamped line to `LOG_PATH`. Best-effort: wrapped in try/except that silently passes on any error. Never raises. Never blocks.

Format: `[YYYY-MM-DDTHH:MM:SS] <msg>\n`

### 4.2 `_allow() -> None`

Write `{}\n` to stdout and flush. One call site abstraction.

### 4.3 `_block(code: str, detail: str) -> None`

Write `{"decision":"block","reason":"<code>: <detail>"}\n` to stdout and flush. Uses `json.dumps` to ensure valid JSON output.

### 4.4 `parse_iso8601(s: str) -> datetime | None`

Parse a strict ISO8601 datetime string with timezone.

Steps:
1. If `s` is falsy or not a string → return `None`
2. Strip whitespace
3. If matches `DATE_ONLY_RE` → return `None` (date-only not allowed — caller uses specific reason code)
4. If does NOT match `DATETIME_TZ_RE` → return `None` (format enforcement before parsing — deterministic across Python versions)
5. If ends with `"Z"` → replace with `"+00:00"` (Python < 3.11 compat)
6. Call `datetime.fromisoformat(s)` inside try/except → on error return `None`
7. If `dt.tzinfo is None` → return `None` (defensive — regex should have caught this, but belt-and-suspenders)
8. Return `dt`

### 4.5 `extract_pit(tool_input: dict) -> str | None`

Extract PIT timestamp string from tool input. Does NOT parse it (caller does).

Priority order (first non-empty match wins):
1. `tool_input.get("parameters")` → if dict → `.get("pit")` — plan-preferred nested path
2. `tool_input.get("pit")` — flat path, practical for MCP tools
3. `tool_input.get("command")` → regex `BASH_PIT_RE` → group(1) — Bash wrapper `--pit` flag

Each candidate: check `isinstance(str)` and non-empty after `.strip()`.

If no match → return `None` (= open mode).

### 4.6 `extract_payload(tool_response: Any) -> str | None`

Extract the tool output as a string for JSON parsing.

Logic:
1. If `tool_response` is `dict`:
   a. If `"stdout"` key exists → return `str(tool_response["stdout"])` (Bash pattern). Return `None` if stdout is empty/falsy.
   b. Else → return `json.dumps(tool_response)` (already-parsed MCP response or other dict)
2. If `tool_response` is `str` → return it if non-empty after strip, else `None`
3. Otherwise → return `None`

### 4.7 `scan_forbidden_keys(obj: Any, depth: int = 0) -> str | None`

Recursively scan parsed JSON for forbidden keys. Returns first match or `None`.

Logic:
1. If `depth > 50` → return `None` (stack overflow guard)
2. If `obj` is `dict`:
   a. For each key: if `isinstance(key, str)` and `key.lower() in FORBIDDEN_KEYS` → return `key`
   b. Recurse into each value
3. If `obj` is `list`:
   a. Recurse into each element
4. Return `None`

Match type: **exact** (case-insensitive). Scans **keys only**, never string values. Reason: substring matching causes false positives on article text; exact key match targets actual Neo4j return-data field names.

### 4.8 `validate_item(item: Any, pit_dt: datetime, idx: int) -> tuple[str, str] | None`

Validate one `data[i]` item. Returns `(reason_code, detail)` on failure, `None` on success.

Steps (short-circuit on first failure):
1. If `not isinstance(item, dict)` → return `(PIT_INVALID_ITEM_TYPE, "data[{idx}] is not an object")`
2. `available_at = item.get("available_at")`. If falsy or not str → return `(PIT_MISSING_AVAILABLE_AT, "data[{idx}] missing available_at")`
3. Strip `available_at`. If matches `DATE_ONLY_RE` → return `(PIT_INVALID_AVAILABLE_AT_FORMAT, "data[{idx}] available_at is date-only: {available_at}")`
4. If does NOT match `DATETIME_TZ_RE` → distinguish:
   a. Try parsing with `datetime.fromisoformat` (after Z→+00:00 replacement). If succeeds and `tzinfo is None` → return `(PIT_MISSING_TZ, "data[{idx}] available_at missing timezone: {available_at}")`
   b. Else → return `(PIT_INVALID_AVAILABLE_AT_FORMAT, "data[{idx}] unparseable available_at: {available_at}")`
5. Parse with `parse_iso8601(available_at)`. If `None` → return `(PIT_INVALID_AVAILABLE_AT_FORMAT, ...)` (defensive — regex should catch, but belt-and-suspenders)
6. `source = item.get("available_at_source")`. If falsy, not str, or `source.strip() not in VALID_SOURCES` → return `(PIT_INVALID_AVAILABLE_AT_SOURCE, "data[{idx}] invalid available_at_source: {source!r}")`
7. If `dt > pit_dt` → return `(PIT_VIOLATION_GT_CUTOFF, "data[{idx}].available_at {available_at} > PIT {pit_dt.isoformat()}")`
8. Return `None` (valid)

### 4.9 `main() -> None`

The top-level orchestration function. Entire body wrapped in try/except.

```
pit_detected = False
tool_name = "unknown"

try:
    # ── Read stdin ──
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        _allow(); return

    # ── Parse hook JSON ──
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
        _allow(); return

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
            _allow(); return

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
        _allow(); return

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
```

---

## 5. What pit_gate.py Does NOT Do

These are explicit non-goals. Do not implement them.

1. **Retry logic** — agents handle retries using the block reason. Retry cap is in `rules.json:max_retries` (=2), read by agents, not the gate.
2. **Neo4j write blocking** — separate PreToolUse hook: `echo '{"decision":"block","reason":"Neo4j writes forbidden"}'` on matcher `mcp__neo4j-cypher__write_neo4j_cypher`.
3. **PIT propagation enforcement** — if agents forget to put PIT in tool_input, gate sees open mode and allows. This is validated by integration tests, not gate code.
4. **Source-specific field mapping** — gate only reads `available_at` and `available_at_source`. Mapping from `created`, `conference_datetime`, etc. is the agent's job.
5. **Config file reading** — no dependency on `rules.json` or any other file. All constants hardcoded.
6. **Content date filtering** — gate validates PUBLICATION dates (`available_at`), not dates mentioned in article text. Per DataSubAgents §4.2.

---

## 6. Hook Wiring Reference (DO NOT APPLY YET)

This section documents how pit_gate.py will be wired into `.claude/settings.json`. **Do not add these hooks during this implementation pass** — agents must first be reworked to output the standard JSON envelope (DataSubAgents Phase 2-4). Adding hooks before agent rework would block all data retrieval.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__neo4j-cypher__read_neo4j_cypher",
        "hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"}]
      },
      {
        "matcher": "mcp__perplexity__perplexity_search",
        "hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"}]
      },
      {
        "matcher": "mcp__perplexity__perplexity_ask",
        "hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"}]
      },
      {
        "matcher": "mcp__perplexity__perplexity_research",
        "hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"}]
      },
      {
        "matcher": "mcp__perplexity__perplexity_reason",
        "hooks": [{"type": "command", "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/pit_gate.py"}]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "mcp__neo4j-cypher__write_neo4j_cypher",
        "hooks": [{"type": "command", "command": "echo '{\"decision\":\"block\",\"reason\":\"Neo4j writes are forbidden\"}'"}]
      }
    ]
  }
}
```

Notes:
- No global Bash matcher. Bash is only matched when wrapper-only adapter agents are built and standardized.
- Each Perplexity tool gets its own matcher (no wildcard — specific matchers per DataSubAgents §4.5).
- Command uses relative path (settings.json is in `.claude/`; hook runs from project root).

---

## 7. Test Harness — `.claude/hooks/test_pit_gate.py`

Standalone test script. Runs pit_gate.py as a subprocess, feeding test cases via stdin and checking stdout.

### Structure

```python
#!/usr/bin/env python3
"""Test harness for pit_gate.py. Run: python3 .claude/hooks/test_pit_gate.py"""

import json
import subprocess
import sys
from pathlib import Path

GATE = str(Path(__file__).resolve().parent / "pit_gate.py")

def run_gate(hook_input: dict) -> dict:
    """Feed hook_input to pit_gate.py, return parsed output."""
    proc = subprocess.run(
        [sys.executable, GATE],
        input=json.dumps(hook_input),
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode == 0, f"Exit code {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout.strip())

def assert_allow(result: dict, label: str) -> None:
    assert result == {}, f"FAIL [{label}]: expected allow, got {result}"
    print(f"  PASS: {label}")

def assert_block(result: dict, label: str, expected_code: str = None) -> None:
    assert "decision" in result and result["decision"] == "block", \
        f"FAIL [{label}]: expected block, got {result}"
    if expected_code:
        assert result["reason"].startswith(expected_code), \
            f"FAIL [{label}]: expected reason starting with {expected_code}, got {result['reason']}"
    print(f"  PASS: {label}")
```

### Test cases (table-driven)

Each test case is a dict with: `name`, `hook_input`, `expect` ("allow" or "block"), and optional `expected_code`.

#### Group 1: Open mode (no PIT)

```python
# T01: No PIT anywhere in tool_input → allow
{"tool_name": "mcp__neo4j-cypher__read_neo4j_cypher",
 "tool_input": {"query": "MATCH (n:News) RETURN n"},
 "tool_response": "some response"}
# → ALLOW

# T02: Empty stdin → allow
# (feed empty string to subprocess)
# → ALLOW
```

#### Group 2: PIT detection priority

```python
# T03: PIT in parameters.pit (priority 1)
{"tool_name": "mcp__neo4j-cypher__read_neo4j_cypher",
 "tool_input": {"query": "MATCH ...", "parameters": {"pit": "2024-02-15T16:00:00-05:00"}},
 "tool_response": json.dumps({"data": [], "gaps": []})}
# → ALLOW (empty data, valid envelope)

# T04: PIT in flat pit (priority 2)
{"tool_name": "mcp__neo4j-cypher__read_neo4j_cypher",
 "tool_input": {"query": "MATCH ...", "pit": "2024-02-15T16:00:00-05:00"},
 "tool_response": json.dumps({"data": [], "gaps": []})}
# → ALLOW

# T05: PIT in Bash --pit flag (priority 3)
{"tool_name": "Bash",
 "tool_input": {"command": "python3 scripts/pit_fetch.py --pit 2024-02-15T16:00:00-05:00 --source alphavantage"},
 "tool_response": {"stdout": json.dumps({"data": [], "gaps": []})}}
# → ALLOW
```

#### Group 3: PIT validation failures

```python
# T06: Invalid PIT format → block PIT_INVALID_PIT
{"tool_input": {"pit": "not-a-date"}, ...}

# T07: Date-only PIT → block PIT_INVALID_PIT
{"tool_input": {"pit": "2024-02-15"}, ...}
```

#### Group 4: Bash belt-and-suspenders

```python
# T08: Bash non-wrapper command with PIT → allow (not a data call)
{"tool_name": "Bash",
 "tool_input": {"command": "ls -la", "pit": "2024-02-15T16:00:00-05:00"},
 "tool_response": {"stdout": "file1.txt\nfile2.txt"}}
# → ALLOW

# T09: Bash wrapper command with PIT and valid data → allow
# (pit_fetch.py in command, valid envelope in stdout)
# → ALLOW
```

#### Group 5: Payload parsing

```python
# T10: Empty payload in PIT mode → block PIT_INVALID_JSON
{"tool_input": {"pit": "2024-02-15T16:00:00-05:00"},
 "tool_response": ""}

# T11: Non-JSON payload in PIT mode → block PIT_INVALID_JSON
{"tool_input": {"pit": "2024-02-15T16:00:00-05:00"},
 "tool_response": "This is not JSON"}

# T12: JSON but not object → block PIT_INVALID_JSON
{"tool_input": {"pit": "..."}, "tool_response": "[1, 2, 3]"}
```

#### Group 6: Envelope validation

```python
# T13: Missing data key → block PIT_MISSING_ENVELOPE
{"data_in_response": {"gaps": ["no news found"]}}

# T14: data is not array → block PIT_MISSING_ENVELOPE
{"data_in_response": {"data": "not an array"}}

# T15: Empty data array → allow (clean gap)
{"data_in_response": {"data": []}}
```

#### Group 7: Per-item validation

```python
# T16: Item is not object → block PIT_INVALID_ITEM_TYPE
{"data": ["string_item"]}

# T17: Missing available_at → block PIT_MISSING_AVAILABLE_AT
{"data": [{"available_at_source": "neo4j_created"}]}

# T18: Date-only available_at → block PIT_INVALID_AVAILABLE_AT_FORMAT
{"data": [{"available_at": "2024-02-15", "available_at_source": "neo4j_created"}]}

# T19: Missing timezone on available_at → block PIT_MISSING_TZ
{"data": [{"available_at": "2024-02-15T16:00:00", "available_at_source": "neo4j_created"}]}

# T20: Invalid available_at_source → block PIT_INVALID_AVAILABLE_AT_SOURCE
{"data": [{"available_at": "2024-02-15T10:00:00-05:00", "available_at_source": "unknown"}]}

# T21: available_at > PIT → block PIT_VIOLATION_GT_CUTOFF
# PIT = 2024-02-15T16:00:00-05:00
{"data": [{"available_at": "2024-02-20T10:00:00-05:00", "available_at_source": "neo4j_created"}]}

# T22: All items clean → allow
# PIT = 2024-02-15T16:00:00-05:00
{"data": [
  {"available_at": "2024-02-10T10:00:00-05:00", "available_at_source": "neo4j_created", "title": "..."},
  {"available_at": "2024-02-14T08:00:00-05:00", "available_at_source": "neo4j_created", "title": "..."}
]}
```

#### Group 8: Forbidden patterns

```python
# T23: Forbidden key in data item → block PIT_FORBIDDEN_FIELD
{"data": [{"available_at": "...", "available_at_source": "neo4j_created", "daily_stock": 5.2}]}

# T24: Forbidden key nested deeper → block PIT_FORBIDDEN_FIELD
{"data": [{"available_at": "...", "available_at_source": "neo4j_created",
           "result": {"daily_return": 3.1}}]}

# T25: Forbidden word in string VALUE (not key) → allow (not a key match)
{"data": [{"available_at": "...", "available_at_source": "neo4j_created",
           "title": "Company daily_stock performance improves"}]}
```

#### Group 9: Timezone handling

```python
# T26: Z suffix on available_at → parses as UTC, allow if <= PIT
# PIT = 2024-02-15T21:00:00+00:00, available_at = 2024-02-15T20:00:00Z
# → ALLOW (20:00 UTC < 21:00 UTC)

# T27: Cross-timezone comparison
# PIT = 2024-02-15T16:00:00-05:00 (= 21:00 UTC)
# available_at = 2024-02-15T22:00:00+01:00 (= 21:00 UTC, same instant)
# → ALLOW (equal, not greater)

# T28: Cross-timezone violation
# PIT = 2024-02-15T16:00:00-05:00 (= 21:00 UTC)
# available_at = 2024-02-15T22:01:00+01:00 (= 21:01 UTC, 1 minute later)
# → BLOCK
```

#### Group 10: Edge cases

```python
# T29: Unparseable stdin (non-empty garbage) → block PIT_PARSE_ERROR
# Feed "not json at all" as stdin

# T30: First item clean, second item violates → block on second item
# Verifies short-circuit reports correct index

# T31: available_at with fractional seconds → allow if format valid
# "2024-02-15T16:00:00.123-05:00" → should parse and validate correctly
```

#### Group 11: Integration guard (PIT propagation)

```python
# T32: Simulate a historical-mode retrieval where agent FORGOT to propagate PIT
# tool_input has only {"query": "MATCH ..."} — no pit field
# → ALLOW (open mode) — gate cannot catch this; test documents the gap
# NOTE: This test exists to prove the systemic risk. The fix is agent-level,
# not gate-level. A separate integration test (outside this harness) should
# run a real neo4j-news agent with --pit and verify every tool call carries PIT.
```

### Test runner

```python
def main():
    tests = [...]  # all test cases above as dicts
    passed = failed = 0
    for t in tests:
        try:
            result = run_gate(t["hook_input"])
            if t["expect"] == "allow":
                assert_allow(result, t["name"])
            else:
                assert_block(result, t["name"], t.get("expected_code"))
            passed += 1
        except AssertionError as e:
            print(f"  {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
```

---

## 8. Implementation Sequence

The implementing bot should follow these steps in order:

### Step 1: Create `.claude/hooks/pit_gate.py`

Write the complete gate script following §2-4 exactly. Structure:

```
#!/usr/bin/env python3
"""..."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ── Constants ──
(all from §2)

# ── Reason codes ──
(all from §3, as string constants)

# ── Helpers: _log, _allow, _block ──
(from §4.1-4.3)

# ── Core functions ──
parse_iso8601      (§4.4)
extract_pit        (§4.5)
extract_payload    (§4.6)
scan_forbidden_keys (§4.7)
validate_item      (§4.8)

# ── Entry point ──
main               (§4.9)

if __name__ == "__main__":
    main()
```

Total: ~140 lines.

### Step 2: Make executable

```bash
chmod +x .claude/hooks/pit_gate.py
```

### Step 3: Create `.claude/hooks/test_pit_gate.py`

Write the test harness following §7 exactly. All 32 test cases. Table-driven. Each test is a dict with name, hook_input, expect, expected_code.

### Step 4: Run tests

```bash
python3 .claude/hooks/test_pit_gate.py
```

All 32 tests must pass. If any fail, fix pit_gate.py and re-run. Do not proceed until all pass.

### Step 5: Verify no external dependencies

```bash
# Must succeed with no pip packages installed
python3 -c "import json, sys, re; from datetime import datetime; from pathlib import Path; print('OK')"
```

### Step 6: Verify exit code behavior

```bash
# Empty stdin → allow, exit 0
echo "" | python3 .claude/hooks/pit_gate.py; echo "exit: $?"
# Should print: {}  exit: 0

# Garbage stdin → block, exit 0
echo "not json" | python3 .claude/hooks/pit_gate.py; echo "exit: $?"
# Should print: {"decision":"block","reason":"PIT_PARSE_ERROR: ..."} exit: 0
```

---

## 9. What NOT to Do

1. **Do not modify `.claude/settings.json`** — hook wiring happens after agent rework, not now.
2. **Do not modify any agent files** — agent rework is DataSubAgents Phase 2-4.
3. **Do not read from `rules.json`** — all constants are hardcoded in pit_gate.py.
4. **Do not delete old validators** — `validate_neo4j.sh`, `validate_perplexity.sh`, `validate_pit_hook.sh` stay until all agents are migrated and hooks are wired.
5. **Do not add retry logic** — agents handle retries, not the gate.
6. **Do not add `import` for anything outside stdlib** — no pip, no uv, no third-party.
7. **Do not create any other files** — only pit_gate.py and test_pit_gate.py.

---

## 10. Extensibility Contract (New Data Sources)

When a new data source is added, pit_gate.py requires **zero changes** if the source agent:

1. Emits standard JSON envelope with `data[]` array
2. Maps provider timestamp → `available_at` (full ISO8601 datetime with timezone)
3. Sets `available_at_source` to one of `VALID_SOURCES` (use `provider_metadata` for new sources)
4. Propagates PIT into tool_input when PIT mode is active

The only change needed outside pit_gate.py is adding a PostToolUse hook matcher in `.claude/settings.json` for the new tool name.

If a new source requires a new `available_at_source` value (rare), add it to `VALID_SOURCES` frozenset — one line change.

---

---

## 11. Phase 2 Integration Test Requirement (PIT Propagation)

pit_gate.py cannot enforce that agents propagate PIT into tool_input (T32 documents this gap). The gate validates only when PIT is present; if agents forget, it silently allows (open mode).

**Required deliverable for DataSubAgents Phase 2 (agent rework)**:
- Run each reworked agent (starting with neo4j-news) in historical mode with `--pit`.
- Capture all PostToolUse hook inputs for matched tools.
- Verify every matched retrieval call carries PIT in `tool_input` (`parameters.pit`, `pit`, or Bash `--pit`).
- If any call is missing PIT, the agent prompt must be fixed before the agent is considered PIT-compliant.

This test validates the system (agent + gate), not just the gate. It is outside the scope of `test_pit_gate.py` (which tests the gate in isolation).

---

*Plan version 1.1 | 2026-02-09 | Post-review fixes: cross-doc rule, hook path, extract_payload defensive handling, quote stripping, Phase 2 integration test note*
