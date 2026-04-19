"""Tests for .claude/skills/earnings-orchestrator/scripts/event_json_manifest.py.

Covers the 4 semantic regen decisions for ``ensure_event_json_for_target``:
  1. File missing → regen
  2. File present but invalid JSON → regen
  3. File present + valid + target quarter ABSENT → regen
  4. File present + valid + target quarter PRESENT → no regen

Plus primitives: atomic_write_json, build_manifest shape, parse_pipe_table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_HELPERS_DIR = REPO_ROOT / ".claude" / "skills" / "earnings-orchestrator" / "scripts"
if str(_HELPERS_DIR) not in sys.path:
    sys.path.insert(0, str(_HELPERS_DIR))


# ── Primitive helpers ─────────────────────────────────────────────────────

def test_atomic_write_json_writes_file_and_cleans_tmp(tmp_path):
    from event_json_manifest import atomic_write_json
    target = tmp_path / "nested" / "event.json"
    atomic_write_json(target, {"hello": "world", "n": 42})
    assert target.exists()
    assert json.loads(target.read_text()) == {"hello": "world", "n": 42}
    # tmp file should have been replaced, not left as a sibling
    assert [p.name for p in tmp_path.rglob("*.tmp*")] == []


def test_parse_pipe_table_happy_path():
    from event_json_manifest import parse_pipe_table
    stdout = (
        "some noise above\n"
        "accession_8k|filed_8k|market_session_8k|accession_10q|filed_10q|"
        "market_session_10q|form_type|fiscal_year|fiscal_quarter|lag\n"
        "acc-1|2025-01-01|pre_market|acc-10q-1|2025-02-01|"
        "pre_market|10-Q|2025|Q1|7d\n"
    )
    tbl = parse_pipe_table(stdout)
    assert tbl is not None
    assert tbl.headers[0] == "accession_8k"
    assert len(tbl.rows) == 1
    assert tbl.rows[0][0] == "acc-1"


def test_parse_pipe_table_returns_none_on_no_header():
    from event_json_manifest import parse_pipe_table
    assert parse_pipe_table("no header here\n") is None
    assert parse_pipe_table("") is None


def test_build_manifest_shape():
    from event_json_manifest import ParsedTable, build_manifest
    tbl = ParsedTable(
        headers=["accession_8k", "filed_8k", "market_session_8k", "accession_10q",
                 "filed_10q", "market_session_10q", "form_type", "fiscal_year",
                 "fiscal_quarter", "lag"],
        rows=[["acc-1", "2025-01-01", "pre_market", "acc-10q-1", "2025-02-01",
               "pre_market", "10-Q", "2025", "Q1", "7d"]],
    )
    m = build_manifest("BURL", tbl)
    assert m["schema_version"] == 1
    assert m["ticker"] == "BURL"
    assert len(m["events"]) == 1
    e = m["events"][0]
    assert e["quarter_label"] == "Q1_FY2025"
    assert e["accession_8k"] == "acc-1"
    assert e["fiscal_year"] == 2025
    assert e["fiscal_quarter"] == "Q1"


# ── refresh_event_json (with injected fetch_stdout to bypass Neo4j) ───────

_FAKE_STDOUT = (
    "accession_8k|filed_8k|market_session_8k|accession_10q|filed_10q|"
    "market_session_10q|form_type|fiscal_year|fiscal_quarter|lag\n"
    "acc-Q1|2025-01-01|pre_market|acc-10q-1|2025-02-01|"
    "pre_market|10-Q|2025|Q1|7d\n"
    "acc-Q2|2025-04-01|pre_market|acc-10q-2|2025-05-01|"
    "pre_market|10-Q|2025|Q2|7d\n"
)


def test_refresh_event_json_happy_path(tmp_path):
    from event_json_manifest import refresh_event_json
    manifest = refresh_event_json(
        "burl",  # lowercased — function upcases
        out_dir=tmp_path,
        fetch_stdout=lambda t: _FAKE_STDOUT,
    )
    # Writes to tmp_path/BURL/events/event.json atomically
    written = tmp_path / "BURL" / "events" / "event.json"
    assert written.exists()
    loaded = json.loads(written.read_text())
    assert loaded == manifest
    assert manifest["ticker"] == "BURL"
    assert [e["quarter_label"] for e in manifest["events"]] == ["Q1_FY2025", "Q2_FY2025"]


def test_refresh_event_json_raises_on_error_output(tmp_path):
    from event_json_manifest import refresh_event_json
    with pytest.raises(RuntimeError, match="get_earnings_with_10q failed"):
        refresh_event_json(
            "BURL", out_dir=tmp_path,
            fetch_stdout=lambda t: "ERROR|neo4j connection refused",
        )


# ── ensure_event_json_for_target — the 4 regen decisions ──────────────────

def _write_manifest(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": 1, "ticker": "BURL",
        "built_at": "2026-04-19T00:00:00",
        "events": events,
    }))


def _counting_refresh(tmp_path, events):
    """Fake refresh_fn that writes the given events list to the manifest path
    and counts invocations."""
    counter = {"n": 0}
    def _fn(ticker: str):
        counter["n"] += 1
        path = tmp_path / ticker.upper() / "events" / "event.json"
        _write_manifest(path, events)
    return _fn, counter


def test_decision_missing_file_triggers_regen(tmp_path):
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"
    assert not path.exists()
    fake_refresh, counter = _counting_refresh(
        tmp_path,
        [{"quarter_label": "Q3_FY2025", "accession_8k": "acc-Q3"}],
    )
    data, idx = ensure_event_json_for_target(
        path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=fake_refresh,
    )
    assert counter["n"] == 1
    assert idx == 0
    assert data["events"][0]["quarter_label"] == "Q3_FY2025"


def test_decision_invalid_json_triggers_regen(tmp_path):
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not json")
    fake_refresh, counter = _counting_refresh(
        tmp_path,
        [{"quarter_label": "Q3_FY2025", "accession_8k": "acc-Q3"}],
    )
    data, idx = ensure_event_json_for_target(
        path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=fake_refresh,
    )
    assert counter["n"] == 1
    assert idx == 0


def test_decision_target_absent_triggers_regen(tmp_path):
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"
    _write_manifest(path, [
        {"quarter_label": "Q1_FY2025", "accession_8k": "acc-Q1"},
        {"quarter_label": "Q2_FY2025", "accession_8k": "acc-Q2"},
    ])
    fake_refresh, counter = _counting_refresh(
        tmp_path,
        [
            {"quarter_label": "Q1_FY2025", "accession_8k": "acc-Q1"},
            {"quarter_label": "Q2_FY2025", "accession_8k": "acc-Q2"},
            {"quarter_label": "Q3_FY2025", "accession_8k": "acc-Q3"},  # added
        ],
    )
    data, idx = ensure_event_json_for_target(
        path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=fake_refresh,
    )
    assert counter["n"] == 1
    assert idx == 2  # Q3 is 3rd after regen


def test_decision_target_present_does_not_trigger_regen(tmp_path):
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"
    _write_manifest(path, [
        {"quarter_label": "Q1_FY2025", "accession_8k": "acc-Q1"},
        {"quarter_label": "Q2_FY2025", "accession_8k": "acc-Q2"},
        {"quarter_label": "Q3_FY2025", "accession_8k": "acc-Q3"},
    ])
    fake_refresh, counter = _counting_refresh(tmp_path, [])  # would blow away — test ensures this isn't called
    data, idx = ensure_event_json_for_target(
        path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=fake_refresh,
    )
    assert counter["n"] == 0  # fast path — no regen
    assert idx == 2


def test_decision_matches_by_accession_when_quarter_label_missing(tmp_path):
    """Target-match rule uses OR: quarter_label OR accession_8k.
    Mirrors the existing orchestrator logic at line 3234."""
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"
    _write_manifest(path, [
        # Row has different quarter_label but matching accession
        {"quarter_label": "8K_UNKNOWN", "accession_8k": "acc-Q3"},
    ])
    fake_refresh, counter = _counting_refresh(tmp_path, [])
    data, idx = ensure_event_json_for_target(
        path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=fake_refresh,
    )
    assert counter["n"] == 0  # accession match is sufficient
    assert idx == 0


def test_decision_regen_fails_to_include_target_raises(tmp_path):
    """If regen succeeds (file written) but still doesn't contain the target,
    raise with a clear message (likely means Neo4j has not ingested the 8-K)."""
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"
    _write_manifest(path, [{"quarter_label": "Q1_FY2025", "accession_8k": "acc-Q1"}])
    # Regen writes a new manifest but the target still isn't there
    fake_refresh, counter = _counting_refresh(
        tmp_path,
        [{"quarter_label": "Q1_FY2025", "accession_8k": "acc-Q1"}],  # unchanged
    )
    with pytest.raises(RuntimeError, match="still not found after regen"):
        ensure_event_json_for_target(
            path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=fake_refresh,
        )
    assert counter["n"] == 1  # regen was attempted once


def test_decision_regen_fails_to_write_raises(tmp_path):
    """If regen_fn itself fails to create the manifest (e.g., Neo4j down), raise."""
    from event_json_manifest import ensure_event_json_for_target
    path = tmp_path / "BURL" / "events" / "event.json"  # doesn't exist
    def broken_refresh(ticker):
        # simulate refresh that raises (Neo4j error) — propagates
        raise RuntimeError("Neo4j unavailable")
    with pytest.raises(RuntimeError, match="Neo4j unavailable"):
        ensure_event_json_for_target(
            path, "BURL", "Q3_FY2025", "acc-Q3", refresh_fn=broken_refresh,
        )
