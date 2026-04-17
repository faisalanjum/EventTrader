"""Tests for thinking_blocks.parse_session_blocks().

Shared block-parser extracted from .claude/hooks/obsidian_capture.py so
the hook + harvester use one code path. Zero behaviour change for the
hook (invariant).
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts" / "earnings") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "earnings"))

FIXTURES = Path(__file__).parent / "tests" / "fixtures"


# ── Learner fixture (EMBED-visible pattern: rich visible thinking) ─────────

def test_learner_fixture_has_6_thinking_blocks_17682_chars():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "learner_session.jsonl")
    thinking = [b for b in blocks if b["kind"] == "thinking"]
    assert len(thinking) == 6
    total_chars = sum(len(b["content"]) for b in thinking)
    assert total_chars == 17682


def test_learner_fixture_zero_redacted():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "learner_session.jsonl")
    redacted = [b for b in blocks if b["kind"] == "thinking_redacted"]
    assert len(redacted) == 0


def test_learner_fixture_has_6_agent_tool_uses():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "learner_session.jsonl")
    agent_calls = [
        b for b in blocks
        if b["kind"] == "tool_use" and b["meta"].get("name") == "Agent"
    ]
    assert len(agent_calls) == 6


# ── Guidance fixture (EMBED-redacted pattern) ──────────────────────────────

def test_guidance_fixture_has_4_redacted_thinking_blocks():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "guidance_session.jsonl")
    redacted = [b for b in blocks if b["kind"] == "thinking_redacted"]
    assert len(redacted) == 4


def test_guidance_fixture_has_zero_visible_thinking():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "guidance_session.jsonl")
    visible = [b for b in blocks if b["kind"] == "thinking"]
    assert len(visible) == 0


def test_guidance_fixture_redacted_block_has_empty_content_and_signature_meta():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "guidance_session.jsonl")
    redacted = [b for b in blocks if b["kind"] == "thinking_redacted"]
    assert all(r["content"] == "" for r in redacted)
    assert all(r["meta"].get("signature") is True for r in redacted)


def test_guidance_fixture_has_2_agent_tool_uses():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "guidance_session.jsonl")
    agent_calls = [
        b for b in blocks
        if b["kind"] == "tool_use" and b["meta"].get("name") == "Agent"
    ]
    assert len(agent_calls) == 2


# ── Predictor fixture (FORK pattern in primary) ────────────────────────────

def test_predictor_primary_has_2_thinking_177_chars():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "predictor_session.jsonl")
    thinking = [b for b in blocks if b["kind"] == "thinking"]
    assert len(thinking) == 2
    total_chars = sum(len(b["content"]) for b in thinking)
    assert total_chars == 177


def test_predictor_primary_has_1_skill_tool_use():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "predictor_session.jsonl")
    skill_calls = [
        b for b in blocks
        if b["kind"] == "tool_use" and b["meta"].get("name") == "Skill"
    ]
    assert len(skill_calls) == 1
    assert skill_calls[0]["meta"]["input"].get("skill") == "earnings-prediction"


def test_predictor_primary_has_zero_agent_tool_uses():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "predictor_session.jsonl")
    agent_calls = [
        b for b in blocks
        if b["kind"] == "tool_use" and b["meta"].get("name") == "Agent"
    ]
    assert len(agent_calls) == 0


# ── Predictor skill-fork JSONL (FORK pattern - content source) ─────────────

def test_predictor_skill_fork_has_4_text_blocks_largest_1926_chars():
    from thinking_blocks import parse_session_blocks
    fork_path = FIXTURES / "predictor_session" / "subagents" / "agent-a9f59960218dbbe88.jsonl"
    assert fork_path.exists(), "predictor fork fixture missing"
    blocks = parse_session_blocks(fork_path)
    text_blocks = [b for b in blocks if b["kind"] == "text"]
    assert len(text_blocks) == 4
    largest = max(len(b["content"]) for b in text_blocks)
    assert largest == 1926


def test_predictor_skill_fork_has_zero_thinking():
    from thinking_blocks import parse_session_blocks
    fork_path = FIXTURES / "predictor_session" / "subagents" / "agent-a9f59960218dbbe88.jsonl"
    blocks = parse_session_blocks(fork_path)
    thinking = [b for b in blocks if b["kind"] == "thinking"]
    assert len(thinking) == 0


# ── Timestamp ordering ────────────────────────────────────────────────────

def test_blocks_are_timestamp_ordered():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "learner_session.jsonl")
    timestamps = [b["ts"] for b in blocks if b["ts"]]
    assert timestamps == sorted(timestamps), "blocks must be in strict timestamp order"


# ── Block shape contract ──────────────────────────────────────────────────

def test_every_block_has_kind_ts_content_meta_keys():
    from thinking_blocks import parse_session_blocks
    blocks = parse_session_blocks(FIXTURES / "predictor_session.jsonl")
    for b in blocks:
        assert set(b.keys()) >= {"kind", "ts", "content", "meta"}


def test_valid_kind_values_only():
    from thinking_blocks import parse_session_blocks
    valid_kinds = {"thinking", "thinking_redacted", "text", "tool_use", "tool_result"}
    for fixture in ("learner_session.jsonl", "guidance_session.jsonl", "predictor_session.jsonl"):
        blocks = parse_session_blocks(FIXTURES / fixture)
        kinds = {b["kind"] for b in blocks}
        assert kinds <= valid_kinds, f"unexpected kinds in {fixture}: {kinds - valid_kinds}"


# ── Malformed input robustness ────────────────────────────────────────────

def test_malformed_jsonl_line_is_skipped_not_crash(tmp_path):
    from thinking_blocks import parse_session_blocks
    p = tmp_path / "bad.jsonl"
    p.write_text(
        '{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]},"timestamp":"2026-01-01T00:00:00Z"}\n'
        'not-valid-json-line\n'
        '{"type":"assistant","message":{"content":[{"type":"text","text":"ok2"}]},"timestamp":"2026-01-01T00:00:01Z"}\n'
    )
    blocks = parse_session_blocks(p)
    texts = [b for b in blocks if b["kind"] == "text"]
    assert len(texts) == 2
    assert texts[0]["content"] == "ok"
    assert texts[1]["content"] == "ok2"


def test_missing_file_raises_filenotfound(tmp_path):
    from thinking_blocks import parse_session_blocks
    import pytest
    with pytest.raises(FileNotFoundError):
        parse_session_blocks(tmp_path / "does-not-exist.jsonl")


# ── preserve_file_order kwarg (for the hook adapter) ──────────────────────

def test_preserve_file_order_true_keeps_jsonl_order_when_ts_and_file_differ(tmp_path):
    """Default (preserve_file_order=False) sorts by ts; True preserves JSONL
    write order. Synthetic case: later ts listed first in file."""
    import json as _json
    from thinking_blocks import parse_session_blocks
    p = tmp_path / "swap.jsonl"
    # Line 1 has LATER ts, line 2 has EARLIER ts
    p.write_text(
        _json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "FIRST_IN_FILE"}]},
            "timestamp": "2026-01-01T00:00:00.500Z",
        }) + "\n"
        + _json.dumps({
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "SECOND_IN_FILE"}]},
            "timestamp": "2026-01-01T00:00:00.000Z",
        }) + "\n"
    )
    # Default: ts-sorted → SECOND_IN_FILE (earlier ts) comes first
    default_order = [b["content"] for b in parse_session_blocks(p)]
    assert default_order == ["SECOND_IN_FILE", "FIRST_IN_FILE"]
    # preserve_file_order=True → file order retained
    file_order = [b["content"] for b in parse_session_blocks(p, preserve_file_order=True)]
    assert file_order == ["FIRST_IN_FILE", "SECOND_IN_FILE"]
