"""Tests for scripts/earnings/run_ledger.py — the 15 listed in
.claude/plans/run_ledger.md §11."""
from __future__ import annotations

import json
import re
import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "scripts" / "earnings") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "earnings"))


# ── Primitives (tests 1–4) ────────────────────────────────────────────────

def test_01_append_writes_valid_json_line_with_trailing_newline(tmp_path):
    from run_ledger import _append_row
    path = tmp_path / "ledger.jsonl"
    _append_row(path, {"run_id": "abc", "status": "running"})
    text = path.read_text()
    assert text.endswith("\n")
    parsed = json.loads(text.strip())
    assert parsed == {"run_id": "abc", "status": "running"}


def test_02_reader_skips_malformed_lines_silently(tmp_path):
    from run_ledger import _read_all_rows
    path = tmp_path / "ledger.jsonl"
    path.write_text(
        json.dumps({"run_id": "one", "status": "running"}) + "\n"
        "not-valid-json-line\n"
        + json.dumps({"run_id": "two", "status": "succeeded"}) + "\n"
        "\n"  # empty line
        "{torn partial\n"
    )
    rows = _read_all_rows(path)
    assert len(rows) == 2
    assert rows[0]["run_id"] == "one"
    assert rows[1]["run_id"] == "two"


def test_03_concurrent_writers_produce_no_corrupted_lines(tmp_path):
    """20 threads each appending 10 rows. All 200 rows must parse cleanly."""
    from run_ledger import _append_row, _read_all_rows
    path = tmp_path / "ledger.jsonl"
    errors = []

    def worker(wid: int):
        try:
            for i in range(10):
                _append_row(path, {
                    "run_id": f"w{wid}-{i}",
                    "status": "running",
                    "payload": "x" * 200,  # realistic row size
                })
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    rows = _read_all_rows(path)
    assert len(rows) == 200
    assert {r["run_id"] for r in rows} == {f"w{w}-{i}" for w in range(20) for i in range(10)}


def test_04_missing_ledger_returns_empty_list(tmp_path):
    from run_ledger import current_state
    path = tmp_path / "does-not-exist.jsonl"
    assert current_state(ledger_path=path) == []


# ── State collapse (tests 5–9) ────────────────────────────────────────────

def test_05_running_then_succeeded_collapses_to_succeeded(tmp_path):
    from run_ledger import _append_row, current_state
    path = tmp_path / "ledger.jsonl"
    _append_row(path, {"run_id": "r1", "component": "prediction",
                       "status": "running", "started_at": "2026-01-01T00:00:00Z"})
    _append_row(path, {"run_id": "r1", "component": "prediction",
                       "status": "succeeded", "started_at": "2026-01-01T00:00:00Z",
                       "finished_at": "2026-01-01T00:02:00Z"})
    state = current_state(ledger_path=path)
    assert len(state) == 1
    assert state[0]["status"] == "succeeded"
    assert state[0]["finished_at"] == "2026-01-01T00:02:00Z"


def test_06_running_only_collapses_to_running_crash_recovery(tmp_path):
    from run_ledger import _append_row, current_state
    path = tmp_path / "ledger.jsonl"
    _append_row(path, {"run_id": "r1", "component": "learning",
                       "status": "running", "started_at": "2026-01-01T00:00:00Z"})
    state = current_state(ledger_path=path)
    assert len(state) == 1
    assert state[0]["status"] == "running"


def test_07_multiple_interleaved_run_ids_collapse_correctly(tmp_path):
    from run_ledger import _append_row, current_state
    path = tmp_path / "ledger.jsonl"
    _append_row(path, {"run_id": "a", "component": "prediction",
                       "status": "running", "started_at": "2026-01-01T00:00:00Z"})
    _append_row(path, {"run_id": "b", "component": "learning",
                       "status": "running", "started_at": "2026-01-01T00:00:01Z"})
    _append_row(path, {"run_id": "a", "component": "prediction",
                       "status": "succeeded", "started_at": "2026-01-01T00:00:00Z"})
    _append_row(path, {"run_id": "c", "component": "guidance",
                       "status": "rate_limited", "started_at": "2026-01-01T00:00:02Z"})
    state = {r["run_id"]: r for r in current_state(ledger_path=path)}
    assert state["a"]["status"] == "succeeded"
    assert state["b"]["status"] == "running"
    assert state["c"]["status"] == "rate_limited"


def test_08_filter_by_component(tmp_path):
    from run_ledger import _append_row, current_state
    path = tmp_path / "ledger.jsonl"
    _append_row(path, {"run_id": "a", "component": "prediction", "status": "succeeded",
                       "started_at": "2026-01-01T00:00:00Z"})
    _append_row(path, {"run_id": "b", "component": "learning", "status": "succeeded",
                       "started_at": "2026-01-01T00:00:01Z"})
    _append_row(path, {"run_id": "c", "component": "guidance", "status": "succeeded",
                       "started_at": "2026-01-01T00:00:02Z"})
    preds = current_state(component="prediction", ledger_path=path)
    assert [r["run_id"] for r in preds] == ["a"]


def test_09_filter_by_status_and_limit(tmp_path):
    from run_ledger import _append_row, current_state
    path = tmp_path / "ledger.jsonl"
    for i in range(5):
        _append_row(path, {"run_id": f"r{i}", "component": "prediction",
                           "status": "running",
                           "started_at": f"2026-01-01T00:00:{i:02d}Z"})
    running = current_state(status="running", limit=3, ledger_path=path)
    assert len(running) == 3
    # Sorted reverse-chrono by started_at
    assert [r["run_id"] for r in running] == ["r4", "r3", "r2"]


# ── API behaviour (tests 10–14) ───────────────────────────────────────────

def test_10_open_run_returns_uuid4_and_appends_running_row(tmp_path):
    from run_ledger import open_run, _read_all_rows
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "index.md"
    rid = open_run("prediction", ticker="BURL", quarter_label="Q3_FY2025",
                   ledger_path=ledger, index_path=index)
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", rid)
    rows = _read_all_rows(ledger)
    assert len(rows) == 1
    assert rows[0]["run_id"] == rid
    assert rows[0]["status"] == "running"
    assert rows[0]["component"] == "prediction"
    assert rows[0]["ticker"] == "BURL"


def test_11_close_run_appends_terminal_row_with_same_run_id(tmp_path):
    from run_ledger import open_run, close_run, _read_all_rows
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "index.md"
    rid = open_run("prediction", ticker="BURL", quarter_label="Q3_FY2025",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "succeeded",
              sdk_session_id="sid-xyz",
              result_path="/tmp/result.json",
              summary={"direction": "long", "confidence_score": 68},
              ledger_path=ledger, index_path=index)
    rows = _read_all_rows(ledger)
    assert len(rows) == 2
    assert rows[1]["run_id"] == rid
    assert rows[1]["status"] == "succeeded"
    assert rows[1]["sdk_session_id"] == "sid-xyz"
    assert rows[1]["summary"]["direction"] == "long"
    # Identifying fields carried forward from the opening row
    assert rows[1]["component"] == "prediction"
    assert rows[1]["ticker"] == "BURL"
    # Elapsed computed
    assert rows[1]["elapsed_seconds"] is not None


def test_12_rate_limited_is_accepted_terminal_status(tmp_path):
    from run_ledger import open_run, close_run, current_state
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "index.md"
    rid = open_run("guidance", ticker="BURL", source_id="acc-1", source_asset="8k",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "rate_limited", error="Rate limit; payload requeued",
              ledger_path=ledger, index_path=index)
    state = current_state(ledger_path=ledger)
    assert len(state) == 1
    assert state[0]["status"] == "rate_limited"
    # Invalid terminal status rejected
    with pytest.raises(ValueError):
        close_run(rid, "running", ledger_path=ledger, index_path=index)


def test_13_refresh_index_writes_four_sections_with_timestamp(tmp_path):
    from run_ledger import open_run, close_run, refresh_index
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    # Seed one run per component
    rid_p = open_run("prediction", ticker="BURL", quarter_label="Q3_FY2025",
                     ledger_path=ledger, index_path=index)
    close_run(rid_p, "succeeded",
              summary={"direction": "long", "confidence_score": 68,
                       "magnitude_bucket": "large",
                       "expected_move_range_pct": [3.0, 6.5]},
              ledger_path=ledger, index_path=index)
    rid_l = open_run("learning", ticker="BURL", quarter_label="Q3_FY2025",
                     ledger_path=ledger, index_path=index)
    close_run(rid_l, "succeeded",
              summary={"direction_correct": False, "actual_daily_stock_pct": -12.16,
                       "magnitude_error_pct": 15.16,
                       "primary_driver_category": "peer_comp_gap_share_loss"},
              ledger_path=ledger, index_path=index)
    rid_g = open_run("guidance", ticker="AVGO", source_id="acc-g1", source_asset="transcript",
                     ledger_path=ledger, index_path=index)
    close_run(rid_g, "succeeded",
              summary={"items_extracted": 13, "items_written": 13,
                       # must be a valid ENRICHMENT_STATUSES enum value,
                       # matching the enum defined in extraction_worker.py
                       "enrichment_status": "enriched"},
              ledger_path=ledger, index_path=index)
    rid_flight = open_run("prediction", ticker="AVGO", quarter_label="Q1_FY2024",
                          ledger_path=ledger, index_path=index)

    refresh_index(ledger_path=ledger, index_path=index)
    text = index.read_text()
    assert "# Run Index" in text
    assert "Last regenerated:" in text
    assert "## In Flight (status = running)" in text
    assert "## Recent Predictions (last 50)" in text
    assert "## Recent Learners (last 50)" in text
    assert "## Recent Extractions (last 50)" in text
    # In flight row should be present
    assert rid_flight[:8] in text
    # Completed predictor row present
    assert rid_p[:8] in text
    # Learner row
    assert rid_l[:8] in text
    # Guidance row
    assert rid_g[:8] in text


def test_14_refresh_index_is_atomic_no_tmp_left_behind(tmp_path):
    from run_ledger import refresh_index
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    ledger.write_text("")  # empty
    refresh_index(ledger_path=ledger, index_path=index)
    refresh_index(ledger_path=ledger, index_path=index)  # second call, idempotent
    siblings = list(tmp_path.iterdir())
    # Only two files — no stray .tmp.* artifact
    tmp_artifacts = [p for p in siblings if ".tmp" in p.name]
    assert tmp_artifacts == []
    assert index.exists()


# ── End-to-end (test 15) ──────────────────────────────────────────────────

def test_15_in_flight_populated_on_open_cleared_on_close(tmp_path):
    """Simulates the key user-facing guarantee:
    when a pipeline is in-flight, the Run Index "In Flight" section shows it;
    after close, it moves to the per-component section and leaves In Flight."""
    from run_ledger import open_run, close_run
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"

    rid = open_run("learning", ticker="BURL", quarter_label="Q3_FY2025",
                   accession_8k="acc-q3",
                   ledger_path=ledger, index_path=index)
    # Immediately after open — In Flight section contains this run
    text = index.read_text()
    assert rid[:8] in text
    # Parse out only the In Flight section and verify rid is there
    in_flight_start = text.index("## In Flight")
    next_section = text.index("## Recent Predictions")
    in_flight_block = text[in_flight_start:next_section]
    assert rid[:8] in in_flight_block, "rid should be in the In Flight section"
    assert "No runs in flight" not in in_flight_block

    close_run(rid, "failed", error="Simulated failure",
              ledger_path=ledger, index_path=index)
    # After close — In Flight is empty, run appears in Recent Learners
    text2 = index.read_text()
    in_flight_start = text2.index("## In Flight")
    next_section = text2.index("## Recent Predictions")
    in_flight_block2 = text2[in_flight_start:next_section]
    assert "No runs in flight" in in_flight_block2, "In Flight should be empty after close"
    learners_start = text2.index("## Recent Learners")
    learners_end = text2.index("## Recent Extractions")
    learners_block = text2[learners_start:learners_end]
    assert rid[:8] in learners_block, "run should now appear in Recent Learners"


# ── Schema-shape tests (summaries must match renderer keys) ──────────────
# These are the guardrails for the 2 bugs ChatGPT identified after Round 1:
# if someone changes the renderer keys or the writer-summary keys without
# updating the other, these tests fail loudly.

def _learner_summary_example() -> dict:
    """A realistic learner summary exactly as the orchestrator writes."""
    return {
        "direction_correct":       True,
        "magnitude_error_pct":     0.42,
        "primary_driver_category": "guidance_revision",
        "actual_daily_stock_pct":  -2.17,
    }


def _guidance_summary_example(enrichment_status: str = "enriched") -> dict:
    """A realistic guidance summary exactly as the extraction worker writes."""
    return {
        "items_extracted":     14,
        "items_written":       14,
        "enrichment_status":   enrichment_status,
        "items_enriched":      3,
        "items_new_secondary": 2,
    }


def test_16_learner_summary_has_exactly_the_four_renderer_keys(tmp_path):
    """Renderer at run_ledger.py::_render_learners_section reads 4 keys:
    direction_correct, actual_daily_stock_pct, magnitude_error_pct,
    primary_driver_category. The writer summary must contain all 4.
    This test is the contract between writer and renderer."""
    from run_ledger import open_run, close_run, current_state
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    rid = open_run("learning", ticker="BURL", quarter_label="Q3_FY2025",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "succeeded", summary=_learner_summary_example(),
              ledger_path=ledger, index_path=index)
    rows = current_state(ledger_path=ledger)
    assert len(rows) == 1
    s = rows[0]["summary"]
    required = {"direction_correct", "actual_daily_stock_pct",
                "magnitude_error_pct", "primary_driver_category"}
    assert required.issubset(s.keys()), (
        f"missing renderer keys: {required - s.keys()}"
    )
    # Index must render both the numeric cells (not em-dashes)
    index_text = index.read_text()
    # actual_return column: -2.17% rendered as "-2.17%"
    assert "-2.17%" in index_text
    # magnitude_error column: 0.42 rendered as "0.42pp"
    assert "0.42pp" in index_text
    assert "guidance_revision" in index_text


def test_17_guidance_summary_has_renderer_keys_and_enum_value(tmp_path):
    """Renderer _render_extractions_section reads items_extracted,
    items_written, enrichment_status. Writer must supply exactly those,
    and enrichment_status must be one of the enum values."""
    from run_ledger import open_run, close_run, current_state
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    rid = open_run("guidance", ticker="BURL",
                   source_id="BURL_2025-01-30T17.00", source_asset="transcript",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "succeeded", summary=_guidance_summary_example("enriched"),
              ledger_path=ledger, index_path=index)
    rows = current_state(ledger_path=ledger)
    s = rows[0]["summary"]
    assert "items_extracted" in s and s["items_extracted"] == 14
    assert "items_written"   in s and s["items_written"]   == 14
    assert "enrichment_status" in s
    assert s["enrichment_status"] in {"enriched", "no_enrichment", "no_primary", None}
    index_text = index.read_text()
    assert "enriched" in index_text
    # Renderer wrote the numeric cells, not em-dashes
    ext_start = index_text.index("## Recent Extractions")
    ext_block = index_text[ext_start:]
    assert "| 14 | 14 |" in ext_block


@pytest.mark.parametrize("enum_value", ["enriched", "no_enrichment", "no_primary"])
def test_18_enrichment_status_enum_round_trips(tmp_path, enum_value):
    from run_ledger import open_run, close_run, current_state
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    rid = open_run("guidance", ticker="X", source_id="X_1", source_asset="8k",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "succeeded", summary=_guidance_summary_example(enum_value),
              ledger_path=ledger, index_path=index)
    assert current_state(ledger_path=ledger)[0]["summary"]["enrichment_status"] == enum_value


def test_19_close_run_accepts_skipped_and_renders_correct_emoji(tmp_path):
    """`skipped` is a valid terminal status — the ledger must accept it and
    the renderer must use the ⏭ emoji (_STATUS_EMOJI). Ensures the learner
    caller can distinguish environmental skips from pipeline failures."""
    from run_ledger import open_run, close_run
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    rid = open_run("learning", ticker="NEWCO", quarter_label="Q1_FY2025",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "skipped", error="skipped_no_prediction",
              ledger_path=ledger, index_path=index)
    text = index.read_text()
    assert "⏭ skipped" in text
    # The error string must appear nowhere in the rendered cells (it's not a
    # rendered column for learners) — but must be in the raw jsonl.
    raw = ledger.read_text()
    assert "skipped_no_prediction" in raw


def test_20_skipped_rejected_as_non_terminal_for_close_run():
    """`running` is not a terminal status — close_run must refuse it."""
    from run_ledger import close_run
    with pytest.raises(ValueError, match="close_run status must be terminal"):
        close_run("any-id", "running")


def test_21_guidance_summary_no_primary_enum(tmp_path):
    from run_ledger import open_run, close_run, current_state
    ledger = tmp_path / "ledger.jsonl"
    index = tmp_path / "Run Index.md"
    rid = open_run("guidance", ticker="X", source_id="X_1", source_asset="10q",
                   ledger_path=ledger, index_path=index)
    close_run(rid, "succeeded",
              summary={"items_extracted": 0, "items_written": 0,
                       "enrichment_status": "no_primary",
                       "items_enriched": 0, "items_new_secondary": 0},
              ledger_path=ledger, index_path=index)
    s = current_state(ledger_path=ledger)[0]["summary"]
    assert s["enrichment_status"] == "no_primary"
    assert s["items_extracted"] == 0


# ── Drift guard: every fixture in this file must use a valid enum value ──

def test_22_all_enrichment_status_fixtures_use_valid_enum_values():
    """Catches future test-fixture drift. If someone writes a new test with
    ``enrichment_status: "completed"`` (the old, invalid value), this test
    fails and points at the regression before it lands."""
    valid = {"enriched", "no_enrichment", "no_primary", None}
    this_file = Path(__file__).read_text()
    # Find every string-valued "enrichment_status": ... literal in this file
    string_hits = re.findall(r'"enrichment_status":\s*"([^"]+)"', this_file)
    null_hits   = re.findall(r'"enrichment_status":\s*None\b', this_file)
    seen = set(string_hits) | ({None} if null_hits else set())
    invalid = seen - valid
    assert not invalid, (
        f"Invalid enrichment_status fixtures in test_run_ledger.py: {invalid}. "
        f"Valid values: {valid}. See extraction_worker.py::ENRICHMENT_STATUSES."
    )
