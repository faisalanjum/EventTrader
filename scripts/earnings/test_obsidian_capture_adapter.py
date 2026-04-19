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


# ── Fence-safe 2000-char tool_result truncation ───────────────────────────

def test_tool_result_2000_truncation_closes_unbalanced_fence(tmp_path):
    """Tool_result content is truncated at 2000 chars. If truncation cuts
    mid-code-fence, the hook's outer ```/``` wrapping would otherwise break.
    The adapter must close any unbalanced ``` within the truncated result."""
    import json
    from obsidian_capture_adapter import parse_transcript_for_hook
    p = tmp_path / "s.jsonl"
    # Tool_result content: opens ```python near char 1000, doesn't close in 2000
    long_code = "x = 1\n" * 500  # ~3000 chars of code
    fence_content = "prelude text " * 50 + "\n```python\n" + long_code + "\n```\ntail"
    p.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu_fence", "name": "Read",
                "input": {"file_path": "/tmp/x.py"},
            }]},
            "timestamp": "2026-01-01T00:00:00Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "tu_fence",
                "content": fence_content,
            }]},
            "timestamp": "2026-01-01T00:00:01Z",
        }) + "\n"
    )
    hb = parse_transcript_for_hook(p)
    assert len(hb.tool) == 1
    result = hb.tool[0]["result"]
    assert result is not None
    # The 2000-char truncation must close unbalanced fences
    assert result.count("```") % 2 == 0, (
        f"unbalanced fences after 2000-char truncation: count={result.count('```')}"
    )


def test_truncate_safe_fence_helper_balanced_input_untouched(tmp_path):
    from obsidian_capture_adapter import _truncate_safe_fence
    src = "abc\n```\ny\n```\nend"
    # Shorter than limit → untouched
    assert _truncate_safe_fence(src, 100) == src
    # Cut at exactly end → no change needed
    assert _truncate_safe_fence(src, len(src)) == src


def test_truncate_safe_fence_helper_closes_open_fence():
    from obsidian_capture_adapter import _truncate_safe_fence
    src = "before\n```python\n" + "y" * 2000
    out = _truncate_safe_fence(src, 50)
    assert out.count("```") % 2 == 0
    assert out.endswith("\n```")


# ── File-order invariant (clock-skew regression guard) ───────────────────
# Belt-and-suspenders: the learner fixture's 2-orphan baseline already proves
# file-order pairing indirectly, but this synthetic case makes the invariant
# explicit and survivable past fixture churn.

def test_adapter_preserves_file_order_orphan_on_clock_skew(tmp_path):
    """Synthetic case: tool_result appears earlier in FILE order than its
    matching tool_use, but has a LATER timestamp (simulating the learner
    fixture's ~7-9ms clock skew). Legacy hook orphans it because it processes
    in file order; adapter must reproduce that orphan — NOT pair via ts sort."""
    p = tmp_path / "skew.jsonl"
    p.write_text(
        # Line 1 (file order: first): tool_result with LATER ts
        json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "tu_skew",
                "content": "result-body-that-is-nonempty",
            }]},
            "timestamp": "2026-01-01T00:00:00.500Z",
        }) + "\n"
        # Line 2 (file order: second): tool_use with EARLIER ts
        + json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu_skew", "name": "Bash",
                "input": {"command": "echo x"},
            }]},
            "timestamp": "2026-01-01T00:00:00.000Z",
        }) + "\n"
    )
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(p)
    # Expect 2 tool entries: (a) orphan tool_result with ↳ prefix, (b) unpaired tool_use
    assert len(hb.tool) == 2
    orphans = [t for t in hb.tool if t["text"].startswith("\u21b3")]
    paired = [t for t in hb.tool if t.get("result") is not None]
    assert len(orphans) == 1, f"expected 1 orphan, got tool={hb.tool}"
    assert len(paired) == 0, f"expected 0 paired, got tool={hb.tool}"
    assert orphans[0]["text"] == "\u21b3 result-body-that-is-nonempty"


def test_adapter_pairs_when_file_order_matches_ts_order(tmp_path):
    """Control case: tool_use first in BOTH file and ts order → normal pairing."""
    p = tmp_path / "ok.jsonl"
    p.write_text(
        json.dumps({
            "type": "assistant",
            "message": {"content": [{
                "type": "tool_use", "id": "tu_ok", "name": "Bash",
                "input": {"command": "echo y"},
            }]},
            "timestamp": "2026-01-01T00:00:00.000Z",
        }) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": [{
                "type": "tool_result", "tool_use_id": "tu_ok",
                "content": "happy-path-result",
            }]},
            "timestamp": "2026-01-01T00:00:00.500Z",
        }) + "\n"
    )
    from obsidian_capture_adapter import parse_transcript_for_hook
    hb = parse_transcript_for_hook(p)
    assert len(hb.tool) == 1
    assert hb.tool[0]["result"] == "happy-path-result"
    assert not hb.tool[0]["text"].startswith("\u21b3")
