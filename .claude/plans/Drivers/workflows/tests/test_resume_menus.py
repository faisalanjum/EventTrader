"""A2 per-chunk resume plan (resume_menus.py) — TDD, every edge case fail-close.

Fixtures use the REAL chunker (chunk_run) over real source files, so the §8.7c
byte-exact verify inside the planner runs against genuine artifacts.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from chunk_company_sources import chunk_run  # noqa: E402
from resume_menus import plan  # noqa: E402

PY = sys.executable


def source(run, ticker, n_events=1, content="hello world this is real text", kpis=()):
    (run / "sources").mkdir(parents=True, exist_ok=True)
    events = [{"source_id": f"{ticker}_e{i}", "source_type": "8-K", "date": "2026-01-01",
               "items": "2.02", "description": "d", "is_earnings": False, "ex991": None,
               "sections": [{"name": "Business", "content": f"{content} {i}"}]}
              for i in range(1, n_events + 1)]
    (run / "sources" / f"{ticker}.json").write_text(json.dumps(
        {"ticker": ticker, "fiscal_kpis": list(kpis), "events": events}))


def menu(run, cid, ticker=None, candidates=None, raw=None):
    (run / "menus").mkdir(exist_ok=True)
    if raw is not None:
        (run / "menus" / f"{cid}.json").write_text(raw)
        return
    cands = candidates if candidates is not None else [
        {"driver_name": "alpha_sales", "evidence_quote": "q", "source_type": "8-K",
         "source_id": "e1", "date": "2026-01-01"}]
    (run / "menus" / f"{cid}.json").write_text(json.dumps(
        {"ticker": ticker or cid.split("__")[0], "chunk_id": cid, "candidates": cands,
         "candidate_count": len(cands), "skipped_count": 0, "notes": []}))


def make_run(tmp_path, tickers=("AAA", "BBB"), budget=40_000):
    run = tmp_path / "run"
    run.mkdir()
    for tk in tickers:
        source(run, tk)
    chunk_run(run, budget=budget)
    return run


# ---------------------------------------------------------------- happy paths

def test_fresh_dir_everything_todo(tmp_path):
    run = make_run(tmp_path)
    p = plan(run)
    assert p["all"] == 2 and p["done"] == 0
    assert p["todo"] == ["AAA__chunk_001", "BBB__chunk_001"]
    assert p["done_counts"] == {} and p["tickers"] == ["AAA", "BBB"]


def test_all_valid_menus_nothing_todo(tmp_path):
    run = make_run(tmp_path)
    menu(run, "AAA__chunk_001")
    menu(run, "BBB__chunk_001")
    p = plan(run)
    assert p["todo"] == [] and p["done"] == 2
    assert p["done_counts"] == {"AAA": 1, "BBB": 1}


def test_partial_only_missing_in_todo(tmp_path):
    run = make_run(tmp_path)
    menu(run, "AAA__chunk_001")
    p = plan(run)
    assert p["todo"] == ["BBB__chunk_001"] and p["done"] == 1


def test_empty_candidates_menu_counts_as_done_with_zero(tmp_path):
    run = make_run(tmp_path)
    menu(run, "AAA__chunk_001", candidates=[])
    menu(run, "BBB__chunk_001")
    p = plan(run)
    assert p["todo"] == [] and p["done_counts"] == {"AAA": 0, "BBB": 1}


def test_blank_driver_name_not_counted_matches_build_seed_rule(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", candidates=[
        {"driver_name": "  ", "evidence_quote": "q", "source_type": "8-K",
         "source_id": "e1", "date": "2026-01-01"},
        {"driver_name": "real_name", "evidence_quote": "q", "source_type": "8-K",
         "source_id": "e2", "date": "2026-01-01"}])
    assert plan(run)["done_counts"] == {"AAA": 1}


def test_multi_chunk_ticker_counts_sum(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    source(run, "AAA", n_events=4, content="x" * 800)
    chunk_run(run, budget=1000)                      # tiny budget -> several chunks
    cids = sorted(p.stem for p in (run / "chunks").glob("*.json"))
    assert len(cids) >= 2
    for cid in cids:
        menu(run, cid)
    p = plan(run)
    assert p["done_counts"] == {"AAA": len(cids)} and p["todo"] == []


def test_kpi_only_chunk_in_plan_despite_zero_manifest_rows(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    source(run, "AAA")
    (run / "sources" / "KPI.json").write_text(json.dumps(
        {"ticker": "KPI", "fiscal_kpis": ["kpi_x"], "events": []}))   # zero events
    chunk_run(run)
    p = plan(run)
    assert "KPI__chunk_001" in p["todo"] and p["all"] == 2


# ---------------------------------------------------------------- fail-close invalid menus

@pytest.mark.parametrize("breaker", ["not json {{{", json.dumps(["list", "not", "dict"])])
def test_unparseable_or_nondict_menu_goes_back_to_todo(tmp_path, breaker):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=breaker)
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_wrong_chunk_id_in_file_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(
        {"ticker": "AAA", "chunk_id": "AAA__chunk_999", "candidates": []}))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_wrong_ticker_in_file_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", ticker="ZZZ")
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_candidates_not_a_list_or_nondict_items_go_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(
        {"ticker": "AAA", "chunk_id": "AAA__chunk_001", "candidates": "nope"}))
    assert plan(run)["todo"] == ["AAA__chunk_001"]
    menu(run, "AAA__chunk_001", raw=json.dumps(
        {"ticker": "AAA", "chunk_id": "AAA__chunk_001", "candidates": [["not", "a", "dict"]]}))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


# ---------------------------------------------------------------- hard fails

def test_incomplete_dir_hard_fails(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    with pytest.raises(SystemExit, match="not a completed"):
        plan(run)
    source(run, "AAA")                               # sources but no chunks yet
    with pytest.raises(SystemExit, match="not a completed"):
        plan(run)


def test_manifest_row_with_deleted_chunk_file_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA", "BBB"))
    (run / "chunks" / "BBB__chunk_001.json").unlink()
    with pytest.raises(SystemExit, match="corrupted"):
        plan(run)


def test_corrupted_chunk_content_fails_byte_exact_verify(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    cp = run / "chunks" / "AAA__chunk_001.json"
    ch = json.loads(cp.read_text())
    ch["events"][0]["content"] = "TAMPERED " + ch["events"][0]["content"]
    cp.write_text(json.dumps(ch))
    with pytest.raises(SystemExit) as exc:
        plan(run)
    assert exc.value.code == 1                       # the §8.7c verify's own loud exit


def test_stale_menu_for_unknown_chunk_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_777")                      # menu for a chunk that never existed
    with pytest.raises(SystemExit, match="stale"):
        plan(run)


# ---------------------------------------------------------------- CLI contract

def test_cli_prints_final_json_line(tmp_path):
    run = make_run(tmp_path)
    menu(run, "AAA__chunk_001")
    out = subprocess.run([PY, str(WORKFLOWS / "resume_menus.py"), str(run)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    final = json.loads(out.stdout.strip().splitlines()[-1])
    assert final["todo"] == ["BBB__chunk_001"] and final["done"] == 1
    assert "VERIFY OK" in out.stdout                 # §8.7c proof ran first


# ---------------------------------------------------------------- evidence-field strictness
# (review round: a reused menu must mirror the live MENU_SCHEMA closely enough that no
#  null/absent-evidence candidate can reach build_seed — fail at PLAN time, not at the
#  validator after readers were paid. Verified against all 68 real CAKE menus: 0 rejections.)

def full_menu(cid, ticker=None, candidates=None, count=None):
    cands = candidates if candidates is not None else [
        {"driver_name": "alpha_sales", "evidence_quote": "q", "source_type": "8-K",
         "source_id": "e1", "date": "2026-01-01"}]
    return {"ticker": ticker or cid.split("__")[0], "chunk_id": cid, "candidates": cands,
            "candidate_count": len(cands) if count is None else count,
            "skipped_count": 0, "notes": []}


def test_candidate_missing_evidence_fields_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(full_menu(
        "AAA__chunk_001", candidates=[{"driver_name": "bad_candidate"}])))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_candidate_null_evidence_fields_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(full_menu(
        "AAA__chunk_001", candidates=[{"driver_name": "x", "evidence_quote": None,
                                       "source_type": None, "source_id": None,
                                       "date": None}])))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_named_candidate_with_blank_evidence_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(full_menu(
        "AAA__chunk_001", candidates=[{"driver_name": "x", "evidence_quote": "  ",
                                       "source_type": "8-K", "source_id": "e1",
                                       "date": "2026-01-01"}])))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_lowercase_ticker_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(full_menu("AAA__chunk_001", ticker="aaa")))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_candidate_count_mismatch_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(full_menu("AAA__chunk_001", count=99)))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_missing_top_level_keys_goes_back_to_todo(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(
        {"ticker": "AAA", "chunk_id": "AAA__chunk_001", "candidates": []}))
    assert plan(run)["todo"] == ["AAA__chunk_001"]


def test_kpi_candidate_with_empty_date_still_valid(tmp_path):
    # guard against OVER-tightening: KPI evidence has date "" by contract
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw=json.dumps(full_menu(
        "AAA__chunk_001", candidates=[{"driver_name": "same_store_sales",
                                       "evidence_quote": "Raw KPI Label",
                                       "source_type": "fiscal.ai-kpi",
                                       "source_id": "fiscal_ai:AAA:ssg", "date": ""}])))
    p = plan(run)
    assert p["todo"] == [] and p["done_counts"] == {"AAA": 1}


# ---------------------------------------------------------------- stale extra CHUNK files
# (review round: a chunks/ file with no manifest rows is mixed-generation text UNLESS it is
#  the one legitimate shape — the KPI-only chunk_001 of a ticker whose source has no events.
#  A reader must NEVER be fanned out over stale text.)

def test_stale_extra_chunk_with_events_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "chunks" / "AAA__chunk_999.json").write_text(json.dumps(
        {"ticker": "AAA", "chunk_id": "AAA__chunk_999",
         "events": [{"source_id": "old_e9", "source_type": "8-K", "date": "2020-01-01",
                     "part_index": 1, "part_count": 1, "content": "STALE OLD TEXT"}]}))
    with pytest.raises(SystemExit, match="not a legitimate KPI-only chunk"):
        plan(run)


def test_stale_unreadable_extra_chunk_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "chunks" / "AAA__chunk_999.json").write_text("not json {{{")
    with pytest.raises(SystemExit, match="unreadable chunk"):
        plan(run)


def test_kpi_shaped_chunk_numbered_002_hard_fails(tmp_path):
    # the chunker can only ever emit a KPI-only chunk as chunk_001 — a later-numbered one is stale
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "chunks" / "AAA__chunk_002.json").write_text(json.dumps(
        {"ticker": "AAA", "chunk_id": "AAA__chunk_002", "events": [], "fiscal_kpis": ["k"]}))
    with pytest.raises(SystemExit, match="only chunk_001 may carry fiscal_kpis"):
        plan(run)


def test_kpi_only_chunk_for_ticker_without_source_hard_fails(tmp_path):
    # a KPI-only chunk for a ticker absent from sources/ = stale foreign-generation file
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "chunks" / "ZZZ__chunk_001.json").write_text(json.dumps(
        {"ticker": "ZZZ", "chunk_id": "ZZZ__chunk_001", "events": [], "fiscal_kpis": ["k"]}))
    with pytest.raises(SystemExit, match="no source file"):
        plan(run)


# ---------------------------------------------------------------- stale KPI content
# (review round: a row-less KPI-only chunk is legitimate ONLY if its fiscal_kpis EXACTLY
#  equal the source's — the chunker copies the list verbatim, so any difference = stale
#  generation. The "source has no text events" half is enforced by the §8.7c verify in the
#  same plan() call — proven below, no redundant code.)

def kpi_source(run, ticker, kpis):
    (run / "sources" / f"{ticker}.json").write_text(json.dumps(
        {"ticker": ticker, "fiscal_kpis": kpis, "events": []}))


def kpi_chunk(run, ticker, kpis):
    (run / "chunks" / f"{ticker}__chunk_001.json").write_text(json.dumps(
        {"ticker": ticker, "chunk_id": f"{ticker}__chunk_001", "events": [],
         "fiscal_kpis": kpis}))


def test_stale_kpi_chunk_when_source_has_no_kpis_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    kpi_source(run, "KPI", [])                       # current source: zero KPIs
    kpi_chunk(run, "KPI", ["OLD_STALE_KPI"])         # stale chunk from an older generation
    with pytest.raises(SystemExit, match="fiscal_kpis differ from source"):
        plan(run)


def test_stale_kpi_chunk_with_different_kpis_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    kpi_source(run, "KPI", ["NEW_KPI"])
    kpi_chunk(run, "KPI", ["OLD_STALE_KPI"])
    with pytest.raises(SystemExit, match="fiscal_kpis differ from source"):
        plan(run)


def test_matching_kpi_chunk_when_source_gained_text_events_hard_fails(tmp_path):
    # ChatGPT item 2: even with matching KPIs, a source that HAS text events cannot have a
    # row-less KPI-only chunk — the §8.7c verify catches the missing event parts.
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "sources" / "KPI.json").write_text(json.dumps(
        {"ticker": "KPI", "fiscal_kpis": ["k"],
         "events": [{"source_id": "KPI_e1", "source_type": "8-K", "date": "2026-01-01",
                     "items": "2.02", "description": "d", "is_earnings": False,
                     "ex991": None, "sections": [{"name": "Business", "content": "real text"}]}]}))
    kpi_chunk(run, "KPI", ["k"])
    with pytest.raises(SystemExit) as exc:
        plan(run)
    assert exc.value.code == 1                       # caught by the §8.7c verify (missing parts)


def test_exactly_matching_kpi_only_chunk_still_allowed(tmp_path):
    # over-tightening guard (his case c): genuine chunker output must keep working
    run = make_run(tmp_path, tickers=("AAA",))
    kpi_source(run, "KPI", ["kpi_x", "kpi_y"])
    kpi_chunk(run, "KPI", ["kpi_x", "kpi_y"])
    p = plan(run)
    assert "KPI__chunk_001" in p["todo"]


# ---------------------------------------------------------------- final-gate round fixes
# (9-reviewer commit gate: rows-bearing stale-KPI gap, orphaned chunks of a deleted source,
#  scope cross-check, invalid-menu unlink, clean errors on corrupt control files.)

def test_rows_bearing_chunk001_with_stale_kpis_hard_fails(tmp_path):
    # source has BOTH kpis and events -> chunk_001 carries manifest rows; tampering only its
    # fiscal_kpis leaves the events byte-exact (verify passes) — must still be caught.
    run = tmp_path / "run"
    run.mkdir()
    (run / "sources").mkdir()
    (run / "sources" / "AAA.json").write_text(json.dumps(
        {"ticker": "AAA", "fiscal_kpis": ["real_kpi"],
         "events": [{"source_id": "AAA_e1", "source_type": "8-K", "date": "2026-01-01",
                     "items": "2.02", "description": "d", "is_earnings": False, "ex991": None,
                     "sections": [{"name": "Business", "content": "real text"}]}]}))
    chunk_run(run)
    cp = run / "chunks" / "AAA__chunk_001.json"
    ch = json.loads(cp.read_text())
    assert ch["fiscal_kpis"] == ["real_kpi"]
    ch["fiscal_kpis"] = ["OLD_STALE_KPI"]
    cp.write_text(json.dumps(ch))
    with pytest.raises(SystemExit, match="fiscal_kpis differ from source"):
        plan(run)


def test_non_001_chunk_carrying_kpis_hard_fails(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    source(run, "AAA", n_events=4, content="x" * 800)
    chunk_run(run, budget=1000)
    cids = sorted(p.stem for p in (run / "chunks").glob("*.json"))
    assert len(cids) >= 2
    cp = run / "chunks" / f"{cids[1]}.json"
    ch = json.loads(cp.read_text())
    ch["fiscal_kpis"] = ["injected_stale"]
    cp.write_text(json.dumps(ch))
    with pytest.raises(SystemExit, match="only chunk_001 may carry fiscal_kpis"):
        plan(run)


def test_orphan_chunks_of_deleted_source_hard_fail(tmp_path):
    run = make_run(tmp_path, tickers=("AAA", "BBB"))
    (run / "sources" / "BBB.json").unlink()          # source deleted AFTER chunking
    with pytest.raises(SystemExit, match="no source file"):
        plan(run)


def test_scope_resolved_mismatch_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "scope_resolved.json").write_text(json.dumps({"tickers": ["AAA", "GONE"]}))
    with pytest.raises(SystemExit, match="scope_resolved"):
        plan(run)


def test_invalid_menu_file_is_unlinked_for_clean_rerun(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    menu(run, "AAA__chunk_001", raw="not json {{{")
    p = plan(run)
    assert p["todo"] == ["AAA__chunk_001"]
    assert not (run / "menus" / "AAA__chunk_001.json").exists()   # worthless file removed


def test_corrupt_manifest_clean_message(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "chunks_manifest.json").write_text("{corrupt")
    with pytest.raises(SystemExit, match="chunks_manifest.json unreadable"):
        plan(run)


def test_corrupt_chunk_file_clean_message(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    (run / "chunks" / "AAA__chunk_001.json").write_text("{corrupt")
    with pytest.raises(SystemExit, match="unreadable chunk"):
        plan(run)


def test_internal_chunk_id_mismatch_hard_fails(tmp_path):
    # the chunker always writes chunk_id == filename stem; a mismatch on a manifest-backed
    # chunk is corruption/mixed-generation — and the reader sees the chunk JSON directly.
    run = make_run(tmp_path, tickers=("AAA",))
    cp = run / "chunks" / "AAA__chunk_001.json"
    ch = json.loads(cp.read_text())
    ch["chunk_id"] = "AAA__chunk_999"
    cp.write_text(json.dumps(ch))
    with pytest.raises(SystemExit, match="internal chunk_id/ticker mismatch"):
        plan(run)


def test_internal_ticker_mismatch_hard_fails(tmp_path):
    run = make_run(tmp_path, tickers=("AAA",))
    cp = run / "chunks" / "AAA__chunk_001.json"
    ch = json.loads(cp.read_text())
    ch["ticker"] = "ZZZ"
    cp.write_text(json.dumps(ch))
    with pytest.raises(SystemExit, match="internal chunk_id/ticker mismatch"):
        plan(run)
