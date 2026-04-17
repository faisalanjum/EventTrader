"""Tests for scripts/harvest_guidance_sessions.py — external post-hoc harvester.

Covers: first-user parsing, completion gate, idempotency, quarter derivation,
scan/one/watch modes, missing-watchdog path.

Zero-touch to guidance pipeline — this is an external tool only.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
for p in (REPO_ROOT, REPO_ROOT / "scripts", REPO_ROOT / "scripts" / "earnings"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest


# ── 1. parse_first_user_guidance ──────────────────────────────────────────

def _write_jsonl(path: Path, lines: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
    return path


def test_parse_first_user_slash_command_extract_guidance_write(tmp_path):
    """Real K8s worker shape (verified from session 8bcad9c0)."""
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {
            "type": "user",
            "message": {"content": (
                "<command-message>extract</command-message>\n"
                "<command-name>/extract</command-name>\n"
                "<command-args>BURL 8k 0001193125-26-092488 TYPE=guidance "
                "MODE=write PRIMARY_MODEL=sonnet ENRICHMENT_MODEL=sonnet "
                "RESULT_PATH=/tmp/foo.json</command-args>"
            )},
        },
    ])
    result = parse_first_user_guidance(p)
    assert result is not None
    assert result["ticker"] == "BURL"
    assert result["asset"] == "8k"
    assert result["source_id"] == "0001193125-26-092488"
    assert result["mode"] == "write"


def test_parse_first_user_transcript_dry_run(tmp_path):
    """Old interactive-CLI shape (verified from fixture 235cf379)."""
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {
            "type": "user",
            "message": {"content": (
                "<command-message>extract</command-message>\n"
                "<command-name>/extract</command-name>\n"
                "<command-args>BURL transcript BURL_2023-03-02T08.30 "
                "TYPE=guidance MODE=dry_run RESULT_PATH=/tmp/t.json"
                "</command-args>"
            )},
        },
    ])
    result = parse_first_user_guidance(p)
    assert result is not None
    assert result["asset"] == "transcript"
    assert result["source_id"] == "BURL_2023-03-02T08.30"
    assert result["mode"] == "dry_run"


def test_parse_first_user_non_guidance_type_returns_none(tmp_path):
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {
            "type": "user",
            "message": {"content": (
                "<command-message>extract</command-message>\n"
                "<command-name>/extract</command-name>\n"
                "<command-args>BURL 8k SID TYPE=news MODE=write</command-args>"
            )},
        },
    ])
    assert parse_first_user_guidance(p) is None


def test_parse_first_user_unrelated_session_returns_none(tmp_path):
    """A learner or predictor session — should NOT match guidance."""
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"content": "Post-event causal attribution for BURL Q4..."}},
    ])
    assert parse_first_user_guidance(p) is None


def test_parse_first_user_invalid_asset_returns_none(tmp_path):
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {
            "type": "user",
            "message": {"content": (
                "<command-message>extract</command-message>\n"
                "<command-name>/extract</command-name>\n"
                "<command-args>BURL FLIMFLAM SID TYPE=guidance MODE=write</command-args>"
            )},
        },
    ])
    assert parse_first_user_guidance(p) is None


def test_parse_first_user_no_user_message_returns_none(tmp_path):
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {"type": "attachment", "attachment": {}},
    ])
    assert parse_first_user_guidance(p) is None


def test_parse_first_user_list_content_shape(tmp_path):
    """Some SDK versions wrap content as [{type:text, text:...}]."""
    from harvest_guidance_sessions import parse_first_user_guidance
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {
            "type": "user",
            "message": {"content": [
                {"type": "text", "text": (
                    "<command-name>/extract</command-name>\n"
                    "<command-args>AAPL 10q SID TYPE=guidance MODE=write"
                    "</command-args>"
                )},
            ]},
        },
    ])
    result = parse_first_user_guidance(p)
    assert result is not None
    assert result["ticker"] == "AAPL"
    assert result["asset"] == "10q"


def test_parse_first_user_malformed_lines_skipped(tmp_path):
    from harvest_guidance_sessions import parse_first_user_guidance
    p = tmp_path / "s.jsonl"
    p.write_text(
        "not-json-garbage\n"
        + json.dumps({"type": "queue-operation"}) + "\n"
        + json.dumps({
            "type": "user",
            "message": {"content": (
                "<command-name>/extract</command-name>\n"
                "<command-args>BURL 8k SID TYPE=guidance MODE=write</command-args>"
            )},
        }) + "\n"
    )
    result = parse_first_user_guidance(p)
    assert result is not None
    assert result["ticker"] == "BURL"


def test_parse_first_user_against_real_fixtures():
    """End-to-end: run against the actual fixtures we committed in tests/fixtures/.
    Guidance fixture should match; predictor and learner fixtures should NOT.
    """
    from harvest_guidance_sessions import parse_first_user_guidance
    fixtures = Path(__file__).resolve().parents[1] / "scripts" / "earnings" / "tests" / "fixtures"

    gm = parse_first_user_guidance(fixtures / "guidance_session.jsonl")
    assert gm is not None, "guidance fixture must parse as guidance"
    assert gm["ticker"] == "BURL"
    assert gm["asset"] == "transcript"

    # Predictor fixture: `/earnings-prediction` skill, NOT guidance
    pm = parse_first_user_guidance(fixtures / "predictor_session.jsonl")
    assert pm is None

    # Learner fixture: not a /extract call
    lm = parse_first_user_guidance(fixtures / "learner_session.jsonl")
    assert lm is None


# ── 2. is_session_complete ────────────────────────────────────────────────

def test_is_session_complete_end_turn_marker(tmp_path):
    from harvest_guidance_sessions import is_session_complete
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"content": "hi"}},
        {"type": "assistant", "message": {"content": [], "stop_reason": "end_turn"}},
    ])
    assert is_session_complete(p) is True


def test_is_session_complete_last_prompt_marker(tmp_path):
    from harvest_guidance_sessions import is_session_complete
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"content": "hi"}},
        {"type": "assistant", "message": {"content": [], "stop_reason": "end_turn"}},
        {"type": "last-prompt", "lastPrompt": "x", "sessionId": "abc"},
    ])
    assert is_session_complete(p) is True


def test_is_session_complete_partial_session_returns_false(tmp_path):
    """Session that's still being written — no end_turn, no last-prompt."""
    from harvest_guidance_sessions import is_session_complete
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"content": "hi"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "mid..."}]}},
    ])
    assert is_session_complete(p) is False


def test_is_session_complete_tool_result_only_returns_false(tmp_path):
    """Assistant using tools but not yet done — stop_reason != end_turn."""
    from harvest_guidance_sessions import is_session_complete
    p = _write_jsonl(tmp_path / "s.jsonl", [
        {"type": "user", "message": {"content": "hi"}},
        {"type": "assistant", "message": {"content": [], "stop_reason": "tool_use"}},
    ])
    assert is_session_complete(p) is False


def test_is_session_complete_against_real_fixtures():
    """Real guidance fixture (235cf379) has end_turn + last-prompt → complete."""
    from harvest_guidance_sessions import is_session_complete
    fixtures = Path(__file__).resolve().parents[1] / "scripts" / "earnings" / "tests" / "fixtures"
    assert is_session_complete(fixtures / "guidance_session.jsonl") is True
    assert is_session_complete(fixtures / "learner_session.jsonl") is True  # also ends cleanly
    assert is_session_complete(fixtures / "predictor_session.jsonl") is True


def test_is_session_complete_missing_file_returns_false(tmp_path):
    from harvest_guidance_sessions import is_session_complete
    assert is_session_complete(tmp_path / "does-not-exist.jsonl") is False


# ── 3. is_already_harvested (idempotency via frontmatter sdk_session_id) ──

def test_is_already_harvested_same_session_id_returns_true(tmp_path):
    from harvest_guidance_sessions import is_already_harvested
    vault = tmp_path / "vault"
    comp = vault / "BURL" / "events" / "Q4_FY2025" / "guidance"
    comp.mkdir(parents=True)
    # Prior harvest left a thinking_8k.md with this sdk_session_id
    (comp / "thinking_8k.md").write_text(
        "---\n"
        "autogenerated: true\n"
        "sdk_session_id: abc-123-def\n"
        "---\n"
        "# Thinking"
    )
    assert is_already_harvested(
        vault, "BURL", "Q4_FY2025", "8k", "abc-123-def"
    ) is True


def test_is_already_harvested_different_session_id_returns_false(tmp_path):
    from harvest_guidance_sessions import is_already_harvested
    vault = tmp_path / "vault"
    comp = vault / "BURL" / "events" / "Q4_FY2025" / "guidance"
    comp.mkdir(parents=True)
    (comp / "thinking_8k.md").write_text(
        "---\nsdk_session_id: old-session-xyz\n---\n# Thinking"
    )
    assert is_already_harvested(
        vault, "BURL", "Q4_FY2025", "8k", "new-session-abc"
    ) is False


def test_is_already_harvested_no_target_file_returns_false(tmp_path):
    from harvest_guidance_sessions import is_already_harvested
    vault = tmp_path / "vault"
    # vault doesn't even exist
    assert is_already_harvested(
        vault, "BURL", "Q4_FY2025", "8k", "any-sid"
    ) is False


def test_is_already_harvested_matches_per_asset_shard(tmp_path):
    """thinking_8k.md is the 8k shard; thinking_transcript.md is unrelated."""
    from harvest_guidance_sessions import is_already_harvested
    vault = tmp_path / "vault"
    comp = vault / "BURL" / "events" / "Q4_FY2025" / "guidance"
    comp.mkdir(parents=True)
    (comp / "thinking_transcript.md").write_text(
        "---\nsdk_session_id: transcript-sid-789\n---\n"
    )
    # 8k shard doesn't exist → not harvested
    assert is_already_harvested(vault, "BURL", "Q4_FY2025", "8k", "transcript-sid-789") is False
    # transcript shard DOES exist with matching sid → harvested
    assert is_already_harvested(vault, "BURL", "Q4_FY2025", "transcript", "transcript-sid-789") is True


# ── 4. derive_quarter_label_for_guidance ──────────────────────────────────

def test_derive_quarter_news_returns_none():
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    assert derive_quarter_label_for_guidance(mgr, "news", "bzNews_1") is None
    mgr.execute_cypher_query_all.assert_not_called()


def test_derive_quarter_unknown_asset_returns_none():
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    assert derive_quarter_label_for_guidance(mgr, "xml_sitemap", "id") is None


def test_derive_quarter_transcript_direct_fq_fy():
    """Transcript.fiscal_quarter/year is populated; direct read."""
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    mgr.execute_cypher_query_all.return_value = [{"fq": "4", "fy": "2,025"}]
    assert derive_quarter_label_for_guidance(
        mgr, "transcript", "BURL_2026-03-05T06.50"
    ) == "Q4_FY2025"


def test_derive_quarter_10q_direct_fq_fy_then_fallback():
    """10-Q first tries direct fq/fy; if NULL, falls back to period_to_fiscal."""
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    # Direct path returns populated — no fallback
    mgr.execute_cypher_query_all.return_value = [{
        "fq": "2", "fy": "2,024", "por": "2024-07-31", "ft": "10-Q"
    }]
    assert derive_quarter_label_for_guidance(
        mgr, "10q", "acc-id"
    ) == "Q2_FY2024"


def test_derive_quarter_10k_direct():
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    mgr.execute_cypher_query_all.return_value = [{
        "fq": "4", "fy": "2,023", "por": "2024-01-31", "ft": "10-K"
    }]
    assert derive_quarter_label_for_guidance(
        mgr, "10k", "acc-id"
    ) == "Q4_FY2023"


def test_derive_quarter_8k_uses_resolve_quarter_info(monkeypatch):
    """8-K: must use resolve_quarter_info (Report.fq/fy are typically NULL)."""
    from harvest_guidance_sessions import derive_quarter_label_for_guidance

    mgr = MagicMock()
    # First call: look up ticker via PRIMARY_FILER
    mgr.execute_cypher_query_all.return_value = [{"ticker": "BURL"}]

    # Patch resolve_quarter_info so we don't need live Neo4j
    fake_module = type(sys)("quarter_identity")
    fake_module.resolve_quarter_info = lambda ticker, acc: {
        "quarter_label": "Q4_FY2025",
        "ticker": ticker,
        "accession_8k": acc,
    }
    monkeypatch.setitem(sys.modules, "quarter_identity", fake_module)

    assert derive_quarter_label_for_guidance(
        mgr, "8k", "0001193125-26-092488"
    ) == "Q4_FY2025"


def test_derive_quarter_8k_returns_none_when_no_ticker():
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    mgr.execute_cypher_query_all.return_value = []  # no PRIMARY_FILER match
    assert derive_quarter_label_for_guidance(mgr, "8k", "unknown-id") is None


def test_derive_quarter_neo4j_exception_returns_none():
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    mgr = MagicMock()
    mgr.execute_cypher_query_all.side_effect = Exception("neo4j down")
    assert derive_quarter_label_for_guidance(mgr, "transcript", "id") is None


def test_derive_quarter_mgr_none_returns_none():
    from harvest_guidance_sessions import derive_quarter_label_for_guidance
    assert derive_quarter_label_for_guidance(None, "8k", "id") is None


# ── 5. harvest_one_session — orchestration for a single session ──────────

def _write_guidance_jsonl_complete(path: Path, ticker, asset, source_id, *, mode="write"):
    """Write a minimal 'complete' guidance session JSONL."""
    entries = [
        {
            "type": "user",
            "timestamp": "2026-04-17T00:00:00Z",
            "message": {"content": (
                f"<command-message>extract</command-message>\n"
                f"<command-name>/extract</command-name>\n"
                f"<command-args>{ticker} {asset} {source_id} "
                f"TYPE=guidance MODE={mode}</command-args>"
            )},
        },
        {
            "type": "assistant",
            "timestamp": "2026-04-17T00:05:00Z",
            "message": {
                "content": [{"type": "text", "text": "done"}],
                "stop_reason": "end_turn",
            },
        },
        {"type": "last-prompt", "lastPrompt": "", "sessionId": path.stem},
    ]
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")


def test_harvest_one_session_skips_incomplete(tmp_path, caplog):
    """Partial session → skip with log, no harvest call."""
    import logging
    from harvest_guidance_sessions import harvest_one_session
    sid = "incomplete-sid"
    p = tmp_path / f"{sid}.jsonl"
    p.write_text(json.dumps({"type": "user", "message": {"content": "partial"}}) + "\n")

    harvest_called = [False]
    def _fake_harvest(**kwargs):
        harvest_called[0] = True

    with patch("harvest_guidance_sessions._harvest_impl", side_effect=_fake_harvest):
        with caplog.at_level(logging.INFO):
            result = harvest_one_session(
                jsonl_path=p,
                vault_root=tmp_path / "vault",
                projects_root=tmp_path,
                mgr=None,
            )
    assert result == "skipped_incomplete"
    assert harvest_called[0] is False


def test_harvest_one_session_skips_non_guidance(tmp_path):
    """Non-guidance session (e.g., prediction) → skip."""
    from harvest_guidance_sessions import harvest_one_session
    sid = "some-prediction-sid"
    p = tmp_path / f"{sid}.jsonl"
    # Complete session BUT first user is NOT /extract guidance
    entries = [
        {"type": "user", "message": {"content": "Run /earnings-prediction ..."}},
        {"type": "assistant", "message": {"content": [], "stop_reason": "end_turn"}},
    ]
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    result = harvest_one_session(
        jsonl_path=p, vault_root=tmp_path / "vault",
        projects_root=tmp_path, mgr=None,
    )
    assert result == "skipped_not_guidance"


def test_harvest_one_session_skips_already_harvested(tmp_path):
    """Same sdk_session_id already in vault frontmatter → skip."""
    from harvest_guidance_sessions import harvest_one_session
    sid = "abc-sid-123"
    p = tmp_path / f"{sid}.jsonl"
    _write_guidance_jsonl_complete(p, "BURL", "8k", "0001-acc")

    vault = tmp_path / "vault"
    comp = vault / "BURL" / "events" / "Q4_FY2025" / "guidance"
    comp.mkdir(parents=True)
    (comp / "thinking_8k.md").write_text(f"---\nsdk_session_id: {sid}\n---\n")

    mgr = MagicMock()
    mgr.execute_cypher_query_all.return_value = [{"ticker": "BURL"}]
    with patch("harvest_guidance_sessions.resolve_quarter_info", create=True,
               new=lambda t, a: {"quarter_label": "Q4_FY2025"}):
        # Also patch the in-function import
        import sys as _sys
        fake_mod = type(_sys)("quarter_identity")
        fake_mod.resolve_quarter_info = lambda t, a: {"quarter_label": "Q4_FY2025"}
        _sys.modules["quarter_identity"] = fake_mod
        result = harvest_one_session(
            jsonl_path=p, vault_root=vault, projects_root=tmp_path, mgr=mgr,
        )
    assert result == "skipped_already_harvested"


def test_harvest_one_session_skips_when_quarter_not_derivable(tmp_path):
    """Quarter derivation returns None → skip with log."""
    from harvest_guidance_sessions import harvest_one_session
    sid = "sid-no-quarter"
    p = tmp_path / f"{sid}.jsonl"
    _write_guidance_jsonl_complete(p, "BURL", "news", "bzNews_99")

    mgr = MagicMock()
    # news returns None from derivation
    result = harvest_one_session(
        jsonl_path=p, vault_root=tmp_path / "vault",
        projects_root=tmp_path, mgr=mgr,
    )
    assert result == "skipped_no_quarter"


def test_harvest_one_session_success_calls_harvest(tmp_path, monkeypatch):
    """Full success path: parse + gate + derive + call harvest()."""
    from harvest_guidance_sessions import harvest_one_session
    sid = "abc-sid-success"
    p = tmp_path / f"{sid}.jsonl"
    _write_guidance_jsonl_complete(p, "BURL", "transcript", "BURL_2026-01-01T09.00")

    mgr = MagicMock()
    mgr.execute_cypher_query_all.return_value = [{"fq": "4", "fy": "2,025"}]

    captured = {}
    def _fake_harvest(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("harvest_guidance_sessions._harvest_impl", _fake_harvest)
    result = harvest_one_session(
        jsonl_path=p, vault_root=tmp_path / "vault",
        projects_root=tmp_path, mgr=mgr,
    )
    assert result == "harvested"
    assert captured["thinking_type"] == "guidance"
    assert captured["ticker"] == "BURL"
    assert captured["quarter"] == "Q4_FY2025"
    assert captured["session_id"] == sid
    assert captured["source_asset"] == "transcript"
    assert captured["source_id"] == "BURL_2026-01-01T09.00"


# ── 6. cmd_scan — one-shot reconciliation ────────────────────────────────

def test_cmd_scan_finds_recent_guidance_sessions(tmp_path, monkeypatch):
    """--scan --since-hours N iterates over recent top-level *.jsonl files."""
    from harvest_guidance_sessions import cmd_scan

    projects = tmp_path / "projects"
    projects.mkdir()
    # Three sessions: one guidance, one non-guidance, one too old
    for name, is_guidance, age_hours in [
        ("fresh-guidance", True, 0),
        ("fresh-prediction", False, 0),
        ("stale-guidance", True, 48),
    ]:
        p = projects / f"{name}.jsonl"
        if is_guidance:
            _write_guidance_jsonl_complete(p, "BURL", "transcript", "sid")
        else:
            p.write_text(json.dumps({
                "type": "user", "message": {"content": "not guidance"},
            }) + "\n")
        # Set mtime
        import time as _t
        mtime = _t.time() - (age_hours * 3600)
        os.utime(p, (mtime, mtime))

    # Subagents subfolder (non-top-level) should NOT be scanned
    subs = projects / "fresh-guidance" / "subagents"
    subs.mkdir(parents=True)
    (subs / "agent-xyz.jsonl").write_text(json.dumps({
        "type": "user", "message": {"content": "subagent — must be ignored"},
    }) + "\n")

    seen: list[str] = []
    def _fake_harvest_one(**kwargs):
        seen.append(kwargs["jsonl_path"].stem)
        return "harvested"

    monkeypatch.setattr("harvest_guidance_sessions.harvest_one_session", _fake_harvest_one)

    args = argparse.Namespace(
        since_hours=24, projects_root=projects, vault_root=tmp_path / "vault",
    )
    cmd_scan(args)
    # Only fresh-guidance is visited (non-guidance is parsed but skipped; stale is filtered out; subagent JSONL is not top-level)
    assert "fresh-guidance" in seen
    assert "stale-guidance" not in seen
    # Non-guidance is visited by the scan but harvest_one_session returns 'skipped_not_guidance'
    # (we don't filter semantically in cmd_scan; harvest_one_session does)
    # Subagent JSONL must NEVER be visited — it's not at top level
    assert "agent-xyz" not in seen


# ── 7. cmd_one — manual single-session harvest ───────────────────────────

def test_cmd_one_invokes_harvest_one_session(tmp_path, monkeypatch):
    from harvest_guidance_sessions import cmd_one

    projects = tmp_path / "projects"
    projects.mkdir()
    sid = "my-session-id"
    p = projects / f"{sid}.jsonl"
    _write_guidance_jsonl_complete(p, "BURL", "8k", "0001-acc")

    captured = {}
    def _fake_harvest_one(**kwargs):
        captured.update(kwargs)
        return "harvested"

    monkeypatch.setattr("harvest_guidance_sessions.harvest_one_session", _fake_harvest_one)

    args = argparse.Namespace(
        session_id=sid, projects_root=projects, vault_root=tmp_path / "vault",
    )
    cmd_one(args)
    assert captured["jsonl_path"].stem == sid


def test_cmd_one_nonexistent_session_raises_clean_error(tmp_path):
    from harvest_guidance_sessions import cmd_one
    args = argparse.Namespace(
        session_id="does-not-exist", projects_root=tmp_path,
        vault_root=tmp_path / "vault",
    )
    with pytest.raises(SystemExit):
        cmd_one(args)


# ── 8. cmd_watch — missing-watchdog path (zero dep needed) ───────────────

def test_cmd_watch_missing_watchdog_exits_clearly(tmp_path, monkeypatch, capsys):
    """When watchdog is not installed, --watch must exit with code 2 +
    clear message telling user how to install it. This test works WITHOUT
    watchdog installed — it simulates the ImportError.
    """
    from harvest_guidance_sessions import cmd_watch

    # Block import of watchdog by poisoning sys.modules
    import builtins
    real_import = builtins.__import__

    def _poisoned_import(name, *a, **kw):
        if name.startswith("watchdog"):
            raise ImportError(f"No module named {name!r} (simulated for test)")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _poisoned_import)

    args = argparse.Namespace(
        projects_root=tmp_path, vault_root=tmp_path / "vault",
        debounce_seconds=5,
    )
    with pytest.raises(SystemExit) as exc_info:
        cmd_watch(args)
    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "watchdog" in err.lower()
    assert "pip install" in err.lower()


# ── argparse imported at top of file for test namespace objects ─────────

import argparse  # noqa: E402 — test-only
