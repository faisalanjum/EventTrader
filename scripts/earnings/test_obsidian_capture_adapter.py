"""Regression tests for the hook-side adapter over parse_session_blocks.

Freezes the legacy bucket-shape behaviour captured from the pre-refactor
inline parse loop in .claude/hooks/obsidian_capture.py. Any change that
moves a count must be intentional — this suite is the safety net.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "earnings") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "earnings"))

FIXTURES = Path(__file__).parent / "tests" / "fixtures"


# ── Fixture baselines (captured from untouched inline loop, 2026-04-17) ────

def test_learner_baseline_counts():
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(FIXTURES / "learner_session.jsonl")
    assert len(hb.thinking) == 6
    assert hb.total_thinking_chars == 17682
    assert len(hb.text) == 9
    assert len(hb.tool) == 21


def test_guidance_redacted_counted_in_thinking_legacy_shape():
    """KEY regression guard: redacted thinking MUST still appear in the
    legacy thinking bucket (with empty text, 0 char contribution).
    Dropping this would silently halve the guidance session's thinking count."""
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(FIXTURES / "guidance_session.jsonl")
    assert len(hb.thinking) == 4
    assert hb.total_thinking_chars == 0
    assert all(t["text"] == "" for t in hb.thinking)


def test_predictor_baseline_counts():
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(FIXTURES / "predictor_session.jsonl")
    assert len(hb.thinking) == 2
    assert hb.total_thinking_chars == 177
    assert len(hb.text) == 1
    assert len(hb.tool) == 1


# ── Pairing / orphan accounting ────────────────────────────────────────────

def test_learner_pairs_17_tool_results_into_21_tool_uses():
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(FIXTURES / "learner_session.jsonl")
    paired = sum(1 for t in hb.tool if t.get("result") is not None)
    assert paired == 17


def test_learner_has_2_orphan_tool_results():
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(FIXTURES / "learner_session.jsonl")
    orphans = [t for t in hb.tool if t["text"].startswith("\u21b3")]
    assert len(orphans) == 2


def test_guidance_all_tool_results_paired():
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(FIXTURES / "guidance_session.jsonl")
    paired = sum(1 for t in hb.tool if t.get("result") is not None)
    orphans = [t for t in hb.tool if t["text"].startswith("\u21b3")]
    assert paired == 7
    assert orphans == []


# ── Tool-use summary rendering ─────────────────────────────────────────────

def test_bash_summary_format_and_500_truncation(tmp_path):
    from obsidian_capture_adapter import parse_transcript_for_hook
    p = tmp_path / "s.jsonl"
    long_cmd = "x" * 600
    p.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{
            "type": "tool_use", "id": "tu1", "name": "Bash",
            "input": {"command": long_cmd},
        }]},
        "timestamp": "2026-01-01T00:00:00Z",
    }) + "\n")
    hb = parse_transcript_for_hook(p)
    assert len(hb.tool) == 1
    assert hb.tool[0]["text"] == f"Bash: {'x' * 500}"


def test_nonbash_summary_uses_json_dumps_and_500_truncation(tmp_path):
    from obsidian_capture_adapter import parse_transcript_for_hook
    p = tmp_path / "s.jsonl"
    big_input = {"k": "y" * 600}
    p.write_text(json.dumps({
        "type": "assistant",
        "message": {"content": [{
            "type": "tool_use", "id": "tu1", "name": "Read",
            "input": big_input,
        }]},
        "timestamp": "2026-01-01T00:00:00Z",
    }) + "\n")
    hb = parse_transcript_for_hook(p)
    assert len(hb.tool) == 1
    expected_prefix = f"Read({json.dumps(big_input)[:500]})"
    assert hb.tool[0]["text"] == expected_prefix


# ── tool_result truncation + cleaning ──────────────────────────────────────

def test_tool_result_truncated_at_2000(tmp_path):
    from obsidian_capture_adapter import parse_transcript_for_hook
    p = tmp_path / "s.jsonl"
    huge = "z" * 3000
    # Emit a paired tool_use + tool_result across two entries
    p.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu42", "name": "Bash",
                "input": {"command": "echo hi"},
            }]},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "tu42", "content": huge,
            }]},
            "timestamp": "2026-01-01T00:00:01Z",
        }) + "\n"
    )
    hb = parse_transcript_for_hook(p)
    assert len(hb.tool) == 1
    assert hb.tool[0]["result"] == "z" * 2000


def test_clean_mcp_envelope_unwrapped():
    from obsidian_capture_adapter import clean_tool_result
    envelope = json.dumps({"result": [{"type": "text", "text": "INNER"}]})
    assert clean_tool_result(envelope) == "INNER"


def test_clean_persisted_output_replaced():
    from obsidian_capture_adapter import clean_tool_result
    src = "<persisted-output>\n  Output too large (900 KB)"
    assert clean_tool_result(src) == "[output too large \u2014 900 KB]"


def test_clean_tool_use_error_prefixed():
    from obsidian_capture_adapter import clean_tool_result
    src = "prelude <tool_use_error>BOOM: invalid input</tool_use_error> tail"
    assert clean_tool_result(src) == "ERROR: BOOM: invalid input"


# ── Silent-fail contract ──────────────────────────────────────────────────

def test_missing_file_returns_empty_never_raises():
    from obsidian_capture_adapter import parse_transcript_for_hook, HookBlocks
    hb = parse_transcript_for_hook("/nope/does-not-exist.jsonl")
    assert hb == HookBlocks([], [], [], 0)


def test_none_path_returns_empty_never_raises():
    from obsidian_capture_adapter import parse_transcript_for_hook, HookBlocks
    hb = parse_transcript_for_hook(None)
    assert hb == HookBlocks([], [], [], 0)


def test_empty_string_path_returns_empty_never_raises():
    from obsidian_capture_adapter import parse_transcript_for_hook, HookBlocks
    hb = parse_transcript_for_hook("")
    assert hb == HookBlocks([], [], [], 0)
