"""Subprocess smoke test against the real .claude/hooks/obsidian_capture.sh
wrapper.

Catches silent import failures (obsidian_capture.sh drops stderr to /dev/null)
and exercises the exact production invocation path Claude Code uses at
SubagentStop. Must pass BOTH before AND after the Phase 9(d) parser refactor
— the adapter preserves legacy hook behaviour as an invariant.

Uses:
  - .sh wrapper (NOT `python3 obsidian_capture.py`): the wrapper is what
    production calls; testing it directly means we'd miss any stderr-related
    regression or wrapper-path bug.
  - agent_type = "smoke-test-agent-generic": a plain fallback name that is
    NOT in FOLDER_ROUTING, NOT in SKIP_AGENT_TYPES, and does not contain
    any of the early-exit substrings ("prompt_suggestion","compact","warmup").
    Routes through the default "agents/" subfolder — isolates the parser
    refactor from any routing-specific behaviour.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "tests" / "fixtures"
HOOK_SH = REPO_ROOT / ".claude" / "hooks" / "obsidian_capture.sh"


def _build_hook_input(agent_transcript: Path, agent_type: str) -> str:
    """Build a SubagentStop JSON payload matching what Claude Code emits."""
    return json.dumps({
        "agent_type": agent_type,
        "agent_id": "smoketestid12345678",
        "agent_transcript_path": str(agent_transcript),
        "last_assistant_message": "Smoke test run — no tickers.",
        "session_id": "smoke-session",
        "transcript_path": str(agent_transcript),
        "hook_event_name": "SubagentStop",
        "stop_hook_active": False,
        "cwd": str(REPO_ROOT),
        "permission_mode": "default",
    })


def _run_hook(tmp_path: Path, hook_input: str) -> subprocess.CompletedProcess:
    """Invoke the .sh wrapper from a foreign cwd with a temp HOME."""
    fake_home = tmp_path / "home"
    vault = fake_home / "Obsidian" / "EventTrader" / "Earnings" / "earnings-analysis"
    vault.mkdir(parents=True)
    (vault / ".ticker-whitelist.txt").write_text("AVGO\n")

    env = {**os.environ, "HOME": str(fake_home)}

    result = subprocess.run(
        ["bash", str(HOOK_SH)],
        input=hook_input,
        env=env,
        cwd=str(tmp_path),  # foreign cwd
        text=True,
        capture_output=True,
        timeout=15,
    )
    return result, fake_home


def test_hook_sh_wrapper_creates_note_with_learner_fixture_counts(tmp_path):
    """End-to-end: pipe real SubagentStop JSON through the real .sh wrapper,
    assert the output MD file has the frozen frontmatter counts."""
    hook_input = _build_hook_input(
        FIXTURES / "learner_session.jsonl", agent_type="smoke-test-agent-generic"
    )
    result, fake_home = _run_hook(tmp_path, hook_input)

    assert result.returncode == 0, (
        f"Hook crashed — stderr: {result.stderr!r}  stdout: {result.stdout!r}"
    )

    agents_dir = fake_home / "Obsidian/EventTrader/Earnings/earnings-analysis/agents"
    assert agents_dir.exists(), (
        f"Expected fallback 'agents/' folder to be created. "
        f"Listing vault: {list((fake_home / 'Obsidian').rglob('*'))}"
    )
    notes = list(agents_dir.glob("*.md"))
    assert len(notes) == 1, f"expected 1 note in agents/, got: {notes}"

    content = notes[0].read_text(encoding="utf-8")
    # Frozen baselines from the pre-refactor inline parse loop (2026-04-17)
    assert "thinking_blocks: 6" in content, f"wrong thinking count: {content[:500]}"
    assert "thinking_chars: 17682" in content, f"wrong thinking chars: {content[:500]}"
    assert "text_blocks: 9" in content, f"wrong text count: {content[:500]}"
    assert "tool_blocks: 21" in content, f"wrong tool count: {content[:500]}"


def test_hook_sh_wrapper_creates_note_with_guidance_redacted_fixture(tmp_path):
    """Guidance fixture is the key redacted-thinking test: 4 blocks, 0 chars."""
    hook_input = _build_hook_input(
        FIXTURES / "guidance_session.jsonl", agent_type="smoke-test-agent-generic"
    )
    result, fake_home = _run_hook(tmp_path, hook_input)

    assert result.returncode == 0, f"Hook crashed: {result.stderr!r}"

    notes = list(
        (fake_home / "Obsidian/EventTrader/Earnings/earnings-analysis/agents").glob("*.md")
    )
    assert len(notes) == 1
    content = notes[0].read_text(encoding="utf-8")
    # Redacted thinking counted AS thinking with 0 chars contribution
    assert "thinking_blocks: 4" in content, (
        f"redacted thinking was NOT counted in legacy shape: {content[:600]}"
    )
    assert "thinking_chars: 0" in content
    assert "text_blocks: 2" in content
    assert "tool_blocks: 7" in content
