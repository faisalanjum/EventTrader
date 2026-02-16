#!/usr/bin/env python3
"""
Test harness for pit_gate.py.
Run: python3 .claude/hooks/test_pit_gate.py

All 37 test cases (32 from .claude/plans/pit_gate_implementation.md §7 + 5 from fluffy-churning-bee MCP/params.pit).
Table-driven. Each test feeds hook JSON via stdin and checks stdout.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

GATE = str(Path(__file__).resolve().parent / "pit_gate.py")
PIT = "2024-02-15T16:00:00-05:00"


def run_gate(hook_input: dict | str | None) -> dict:
    """Feed hook_input to pit_gate.py via stdin, return parsed output."""
    if hook_input is None:
        stdin_data = ""
    elif isinstance(hook_input, str):
        stdin_data = hook_input
    else:
        stdin_data = json.dumps(hook_input)
    proc = subprocess.run(
        [sys.executable, GATE],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert proc.returncode == 0, f"Exit code {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout.strip())


def is_allow(result: dict) -> bool:
    return result == {}


def is_block(result: dict, expected_code: str | None = None) -> bool:
    if result.get("decision") != "block":
        return False
    if expected_code and not result.get("reason", "").startswith(expected_code):
        return False
    return True


def envelope(data: list | None = None, gaps: list | None = None) -> str:
    """Build a standard JSON envelope string."""
    obj: dict = {}
    if data is not None:
        obj["data"] = data
    if gaps is not None:
        obj["gaps"] = gaps
    return json.dumps(obj)


def clean_item(
    ts: str = "2024-02-10T10:00:00-05:00", source: str = "neo4j_created", **extra
) -> dict:
    """Build a valid data[] item."""
    item = {"available_at": ts, "available_at_source": source}
    item.update(extra)
    return item


def hook(
    pit: str | None = PIT,
    tool_name: str = "mcp__neo4j-cypher__read_neo4j_cypher",
    response: str | dict | None = None,
    tool_input_extra: dict | None = None,
    use_params_pit: bool = False,
    use_cypher_params_pit: bool = False,
    bash_command: str | None = None,
) -> dict:
    """Build a hook input dict."""
    ti: dict = {}
    if bash_command is not None:
        ti["command"] = bash_command
        tool_name = "Bash"
    else:
        ti["query"] = "MATCH (n:News) RETURN n"
    if pit is not None:
        if use_params_pit:
            ti["parameters"] = {"pit": pit}
        elif use_cypher_params_pit:
            ti.setdefault("params", {})["pit"] = pit
        else:
            ti["pit"] = pit
    if tool_input_extra:
        ti.update(tool_input_extra)
    tr = response if response is not None else envelope([])
    return {"tool_name": tool_name, "tool_input": ti, "tool_response": tr}


# ── Test cases ───────────────────────────────────────────────────────

TESTS: list[dict] = [
    # ── Group 1: Open mode ──
    {
        "name": "T01 No PIT → allow",
        "input": hook(pit=None, response="some response"),
        "expect": "allow",
    },
    {
        "name": "T02 Empty stdin → allow",
        "input": None,  # empty string
        "expect": "allow",
    },
    # ── Group 2: PIT detection priority ──
    {
        "name": "T03 PIT in parameters.pit → allow (empty data)",
        "input": hook(use_params_pit=True, response=envelope([])),
        "expect": "allow",
    },
    {
        "name": "T04 PIT in flat pit → allow (empty data)",
        "input": hook(response=envelope([])),
        "expect": "allow",
    },
    {
        "name": "T05 PIT in Bash --pit flag → allow (empty data)",
        "input": hook(
            bash_command=f"python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --pit {PIT} --source av",
            response={"stdout": envelope([])},
        ),
        "expect": "allow",
    },
    # ── Group 3: PIT validation failures ──
    {
        "name": "T06 Invalid PIT format → block",
        "input": hook(pit="not-a-date", response=envelope([])),
        "expect": "block",
        "code": "PIT_INVALID_PIT",
    },
    {
        "name": "T07 Date-only PIT → block",
        "input": hook(pit="2024-02-15", response=envelope([])),
        "expect": "block",
        "code": "PIT_INVALID_PIT",
    },
    # ── Group 4: Bash belt-and-suspenders ──
    {
        "name": "T08 Bash non-wrapper with PIT → allow",
        "input": {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la", "pit": PIT},
            "tool_response": {"stdout": "file1.txt\nfile2.txt"},
        },
        "expect": "allow",
    },
    {
        "name": "T09 Bash wrapper with PIT + valid data → allow",
        "input": hook(
            bash_command=f"python3 .claude/skills/earnings-orchestrator/scripts/pit_fetch.py --pit {PIT} --source av",
            response={"stdout": envelope([clean_item()])},
        ),
        "expect": "allow",
    },
    # ── Group 5: Payload parsing ──
    {
        "name": "T10 Empty payload in PIT mode → block",
        "input": hook(response=""),
        "expect": "block",
        "code": "PIT_INVALID_JSON",
    },
    {
        "name": "T11 Non-JSON payload in PIT mode → block",
        "input": hook(response="This is not JSON"),
        "expect": "block",
        "code": "PIT_INVALID_JSON",
    },
    {
        "name": "T12 JSON array (not object) → block",
        "input": hook(response="[1, 2, 3]"),
        "expect": "block",
        "code": "PIT_MISSING_ENVELOPE",
    },
    # ── Group 6: Envelope validation ──
    {
        "name": "T13 Missing data key → block",
        "input": hook(response=json.dumps({"gaps": ["no news"]})),
        "expect": "block",
        "code": "PIT_MISSING_ENVELOPE",
    },
    {
        "name": "T14 data is not array → block",
        "input": hook(response=json.dumps({"data": "not an array"})),
        "expect": "block",
        "code": "PIT_MISSING_ENVELOPE",
    },
    {
        "name": "T15 Empty data array → allow (clean gap)",
        "input": hook(response=envelope([])),
        "expect": "allow",
    },
    # ── Group 7: Per-item validation ──
    {
        "name": "T16 Item not object → block",
        "input": hook(response=envelope(["string_item"])),
        "expect": "block",
        "code": "PIT_INVALID_ITEM_TYPE",
    },
    {
        "name": "T17 Missing available_at → block",
        "input": hook(
            response=envelope([{"available_at_source": "neo4j_created"}])
        ),
        "expect": "block",
        "code": "PIT_MISSING_AVAILABLE_AT",
    },
    {
        "name": "T18 Date-only available_at → block",
        "input": hook(
            response=envelope(
                [{"available_at": "2024-02-15", "available_at_source": "neo4j_created"}]
            )
        ),
        "expect": "block",
        "code": "PIT_INVALID_AVAILABLE_AT_FORMAT",
    },
    {
        "name": "T19 Missing timezone on available_at → block",
        "input": hook(
            response=envelope(
                [
                    {
                        "available_at": "2024-02-15T16:00:00",
                        "available_at_source": "neo4j_created",
                    }
                ]
            )
        ),
        "expect": "block",
        "code": "PIT_MISSING_TZ",
    },
    {
        "name": "T20 Invalid available_at_source → block",
        "input": hook(
            response=envelope(
                [
                    {
                        "available_at": "2024-02-15T10:00:00-05:00",
                        "available_at_source": "unknown",
                    }
                ]
            )
        ),
        "expect": "block",
        "code": "PIT_INVALID_AVAILABLE_AT_SOURCE",
    },
    {
        "name": "T21 available_at > PIT → block",
        "input": hook(
            response=envelope(
                [
                    {
                        "available_at": "2024-02-20T10:00:00-05:00",
                        "available_at_source": "neo4j_created",
                    }
                ]
            )
        ),
        "expect": "block",
        "code": "PIT_VIOLATION_GT_CUTOFF",
    },
    {
        "name": "T22 All items clean → allow",
        "input": hook(
            response=envelope(
                [
                    clean_item("2024-02-10T10:00:00-05:00"),
                    clean_item("2024-02-14T08:00:00-05:00"),
                ]
            )
        ),
        "expect": "allow",
    },
    # ── Group 8: Forbidden patterns ──
    {
        "name": "T23 Forbidden key in data item → block",
        "input": hook(
            response=envelope(
                [
                    {
                        "available_at": "2024-02-10T10:00:00-05:00",
                        "available_at_source": "neo4j_created",
                        "daily_stock": 5.2,
                    }
                ]
            )
        ),
        "expect": "block",
        "code": "PIT_FORBIDDEN_FIELD",
    },
    {
        "name": "T24 Forbidden key nested deeper → block",
        "input": hook(
            response=envelope(
                [
                    {
                        "available_at": "2024-02-10T10:00:00-05:00",
                        "available_at_source": "neo4j_created",
                        "result": {"daily_return": 3.1},
                    }
                ]
            )
        ),
        "expect": "block",
        "code": "PIT_FORBIDDEN_FIELD",
    },
    {
        "name": "T25 Forbidden word in string VALUE (not key) → allow",
        "input": hook(
            response=envelope(
                [
                    clean_item(
                        title="Company daily_stock performance improves"
                    )
                ]
            )
        ),
        "expect": "allow",
    },
    # ── Group 9: Timezone handling ──
    {
        "name": "T26 Z suffix on available_at → allow",
        "input": hook(
            pit="2024-02-15T21:00:00+00:00",
            response=envelope(
                [clean_item("2024-02-15T20:00:00Z")]
            ),
        ),
        "expect": "allow",
    },
    {
        "name": "T27 Cross-timezone equal instant → allow",
        "input": hook(
            pit="2024-02-15T16:00:00-05:00",
            response=envelope(
                [clean_item("2024-02-15T22:00:00+01:00")]
            ),
        ),
        "expect": "allow",
    },
    {
        "name": "T28 Cross-timezone 1 minute over → block",
        "input": hook(
            pit="2024-02-15T16:00:00-05:00",
            response=envelope(
                [clean_item("2024-02-15T22:01:00+01:00")]
            ),
        ),
        "expect": "block",
        "code": "PIT_VIOLATION_GT_CUTOFF",
    },
    # ── Group 10: Edge cases ──
    {
        "name": "T29 Unparseable stdin → block",
        "input": "not json at all",  # raw string, not dict
        "expect": "block",
        "code": "PIT_PARSE_ERROR",
    },
    {
        "name": "T30 First clean + second violates → block index 1",
        "input": hook(
            response=envelope(
                [
                    clean_item("2024-02-10T10:00:00-05:00"),
                    {
                        "available_at": "2024-02-20T10:00:00-05:00",
                        "available_at_source": "neo4j_created",
                    },
                ]
            )
        ),
        "expect": "block",
        "code": "PIT_VIOLATION_GT_CUTOFF",
        "check_index": 1,
    },
    {
        "name": "T31 Fractional seconds → allow",
        "input": hook(
            response=envelope(
                [clean_item("2024-02-10T10:00:00.123-05:00")]
            )
        ),
        "expect": "allow",
    },
    # ── Group 11: Integration guard ──
    {
        "name": "T32 No PIT propagated (agent forgot) → allow (open mode)",
        "input": {
            "tool_name": "mcp__neo4j-cypher__read_neo4j_cypher",
            "tool_input": {"query": "MATCH (n:News) RETURN n"},
            "tool_response": "raw cypher output",
        },
        "expect": "allow",
    },
    # ── Group 12: MCP format + params.pit ──
    {
        "name": "T33 PIT in params.pit (Neo4j Cypher) → allow",
        "input": hook(use_cypher_params_pit=True, response=envelope([clean_item()])),
        "expect": "allow",
    },
    {
        "name": "T34 MCP TextContent wrapping → allow",
        "input": hook(
            response=[
                {
                    "type": "text",
                    "text": json.dumps(
                        [{"data": [clean_item()], "gaps": []}]
                    ),
                }
            ],
        ),
        "expect": "allow",
    },
    {
        "name": "T35 MCP TextContent wrapping with violation → block",
        "input": hook(
            response=[
                {
                    "type": "text",
                    "text": json.dumps(
                        [
                            {
                                "data": [
                                    {
                                        "available_at": "2024-02-20T10:00:00-05:00",
                                        "available_at_source": "neo4j_created",
                                    }
                                ],
                                "gaps": [],
                            }
                        ]
                    ),
                }
            ],
        ),
        "expect": "block",
        "code": "PIT_VIOLATION_GT_CUTOFF",
    },
    {
        "name": "T36 Single-record Cypher array unwrap → allow",
        "input": hook(
            response=json.dumps([{"data": [clean_item()], "gaps": []}]),
        ),
        "expect": "allow",
    },
    {
        "name": "T37 Multi-record Cypher array → block",
        "input": hook(
            response=json.dumps(
                [
                    {"data": [clean_item()], "gaps": []},
                    {"data": [clean_item()], "gaps": []},
                ]
            ),
        ),
        "expect": "block",
        "code": "PIT_MISSING_ENVELOPE",
    },
    # ── Group 13: Stringified MCP wrapper unwrap ──
    {
        "name": "T38 Stringified MCP wrapper with valid data → allow",
        "input": hook(
            response=json.dumps(
                {
                    "result": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                [{"data": [clean_item()], "gaps": []}]
                            ),
                        }
                    ]
                }
            ),
        ),
        "expect": "allow",
    },
    {
        "name": "T39 Stringified MCP wrapper with future data → block",
        "input": hook(
            response=json.dumps(
                {
                    "result": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                [
                                    {
                                        "data": [
                                            {
                                                "available_at": "2024-02-20T10:00:00-05:00",
                                                "available_at_source": "neo4j_created",
                                            }
                                        ],
                                        "gaps": [],
                                    }
                                ]
                            ),
                        }
                    ]
                }
            ),
        ),
        "expect": "block",
        "code": "PIT_VIOLATION_GT_CUTOFF",
    },
    {
        "name": "T40 Stringified MCP wrapper with bare array → block",
        "input": hook(
            response=json.dumps(
                {
                    "result": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                [
                                    {"data": [clean_item()], "gaps": []},
                                    {"data": [clean_item()], "gaps": []},
                                ]
                            ),
                        }
                    ]
                }
            ),
        ),
        "expect": "block",
        "code": "PIT_MISSING_ENVELOPE",
    },
    {
        "name": "T41 Malformed result key does not trigger unwrap → block",
        "input": hook(
            response=json.dumps({"result": "not_a_list"}),
        ),
        "expect": "block",
        "code": "PIT_MISSING_ENVELOPE",
    },
]


def main() -> None:
    passed = 0
    failed = 0
    errors: list[str] = []

    for t in TESTS:
        name = t["name"]
        try:
            result = run_gate(t["input"])

            if t["expect"] == "allow":
                if is_allow(result):
                    print(f"  PASS: {name}")
                    passed += 1
                else:
                    msg = f"  FAIL [{name}]: expected allow, got {result}"
                    print(msg)
                    errors.append(msg)
                    failed += 1
            else:
                code = t.get("code")
                if is_block(result, code):
                    # Optional: check index in reason string
                    if "check_index" in t:
                        idx_str = f"data[{t['check_index']}]"
                        reason = result.get("reason", "")
                        if idx_str not in reason:
                            msg = (
                                f"  FAIL [{name}]: expected '{idx_str}' in "
                                f"reason, got: {reason}"
                            )
                            print(msg)
                            errors.append(msg)
                            failed += 1
                            continue
                    print(f"  PASS: {name}")
                    passed += 1
                else:
                    msg = (
                        f"  FAIL [{name}]: expected block"
                        f"{f' with {code}' if code else ''}, got {result}"
                    )
                    print(msg)
                    errors.append(msg)
                    failed += 1

        except Exception as e:
            msg = f"  ERROR [{name}]: {e}"
            print(msg)
            errors.append(msg)
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"{passed} passed, {failed} failed out of {len(TESTS)} tests")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
