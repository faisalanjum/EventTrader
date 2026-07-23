"""Phase-5 item 3 — multi-part anchor slice tokens (the _ident_tokens fix) +
the REAL CE $388M cross-filing recovery.

DATA-PINNED (read-only census 2026-07-23): the CE later 10-Q
`0001306830-25-000105` (created 2025-05-06, FYE Dec) carries the prior-year
comparative `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` =
388,000,000 usd for Q1-2024 (graph period 2024-01-01..2024-04-01, stored end
EXCLUSIVE -> claimed 2024-01-01..2024-03-31), dims
srt:StatementGeographicalAxis -> srt:NorthAmericaMember +
us-gaap:StatementBusinessSegmentsAxis -> ce:AcetylChainMember. The OLDER 10-Q
`0001306830-24-000098` states the same fact originally (graph fact_id
`f-1025`, unit `usd`); its inline HTML is cached locally at
inline_html_cache/0001306830-24-000098.htm — deterministic, no live reads.
"""
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locator import _ident_tokens, locate, rebuild_anchor  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from driver.core.driver_write_cli import run_event  # noqa: E402
from driver.core.prepared_fact import RunInputV1  # noqa: E402
from driver.core.test_driver_write_cli import FakeStore, audit_docs  # noqa: E402

SRC_CE = "0001306830-25-000105"
CONCEPT = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
# DURABLE tracked fixtures (the probe cache is git-ignored — a clean checkout
# must still run this test); integrity pinned by sha256 below
_FIX = os.path.join(os.path.dirname(__file__), "fixtures")
FIX_OLD = os.path.join(_FIX, "0001306830-24-000098.htm")
FIX_LATER = os.path.join(_FIX, "0001306830-25-000105.htm")
SHA_OLD = "2c0a5134a44e6b930c16e8b2a4013d10fb02373c7005652aa328e6b2df681825"
SHA_LATER = "a0114fbad66d39012cf257cad30374e6d45fc868e90a6663f6ceb69294a0c919"
# the REAL later-file row (Q1-2025 386, then the Q1-2024 comparative 388) —
# the birth quote is VERBATIM source text, never a composed citation
REAL_ROW_LATER = "North America 386 388"
# the recovered older-source evidence representation, pinned
SHA_EVIDENCE = ("6868bab3ed6990e2596670a3e2eb2b8fcf4571f997eda312bd1905b714f"
                "84e5a")


def _read_pinned(path, sha):
    import hashlib
    with open(path, "rb") as fh:
        data = fh.read()
    assert hashlib.sha256(data).hexdigest() == sha, f"fixture drifted: {path}"
    return data.decode("utf-8", errors="replace")


def test_ident_tokens_never_leak_kind_words():
    # THE :848 law: tokenize the VALUE of every kind:value part separately —
    # a later part's kind word must never become identity evidence
    assert _ident_tokens("geography:north_america;segment:acetyl_chain") == [
        "north", "america", "acetyl", "chain"]
    # single-part and measurement (comma-joined) behavior unchanged
    assert _ident_tokens("segment:automotive") == ["automotive"]
    assert _ident_tokens("adjusted,organic") == ["adjusted", "organic"]
    assert _ident_tokens(None) == []


def _core_anchor(tmp_path):
    """Create the Driver from the LATER CE filing via the admissions handoff,
    then rebuild its complete two-part anchor from the planned stored fact."""
    # the birth quote is the REAL later-file row — proven present in the pinned
    # later fixture before use (verbatim-quote law, no composed citations)
    later_text = None
    import inline_html as IHM
    later_text = IHM.prepare(_read_pinned(FIX_LATER, SHA_LATER))["text"]
    assert REAL_ROW_LATER in later_text
    store = FakeStore(
        source={"date": "2025-05-06T16:12:38-04:00", "source_type": "10q",
                "ticker": "CE", "fye_month": 12},   # the report's EXACT created
        companies=["CE"], drivers={})       # genuinely NEW driver — CREATE legal
    fact = {"driver_name": "revenue", "driver_state": "reported",
            "quote": REAL_ROW_LATER,
            "slice_parts": [("geography", "North America"),
                            ("segment", "Acetyl Chain")],
            "level_low": Decimal("388"), "level_high": Decimal("388"),
            "level_unit_raw": "USD millions", "level_shape_hint": "point",
            "period_start_date": "2024-01-01", "period_end_date": "2024-03-31",
            "fiscal_year": 2024, "fiscal_quarter": 1, "time_type": "duration"}
    ri = RunInputV1.from_dict({"source_id": SRC_CE, "facts": [fact]})
    out = run_event(ri, store=store, audit_dir=str(tmp_path),
                    admissions={0: {"decision": "create",
                                    "driver_name": "revenue",
                                    "fact_type": "metric"}})
    assert out["items"][0]["decision"] == "written"
    doc = audit_docs(tmp_path)[0]
    props = next(op for pl in doc["plans"] for op in pl["ops"]
                 if op["op"] == "create_fact")["props"]
    p = out["driver_plans"][0]
    driver_node = {"name": p["name"], "fact_type": p["fact_type"],
                   "definitional_evidence": p["definitional_evidence"]}
    anchor, _ = rebuild_anchor(p["first_fact_id"], props, driver_node,
                               {SRC_CE: "CE"}, concept_resolutions=(CONCEPT,))
    assert anchor["slice"] == "geography:north_america;segment:acetyl_chain"
    assert anchor["series_unit"] == "m_usd"
    return anchor


def _older_source():
    """The OLDER filing's Route-A payload: the real cached inline HTML + the
    graph-shaped fact row (real fact_id, exclusive period, declared unit)."""
    html = _read_pinned(FIX_OLD, SHA_OLD)
    row = {"value": "388,000,000", "fact_id": "f-1025", "unitRef": "usd",
           "unit_name": "iso4217:USD", "is_divide": "0",
           "period": {"startDate": "2024-01-01", "endDate": "2024-04-01"},
           "segment": [{"explicitMember": [
               {"dimension": "srt:StatementGeographicalAxis",
                "$t": "srt:NorthAmericaMember"},
               {"dimension": "us-gaap:StatementBusinessSegmentsAxis",
                "$t": "ce:AcetylChainMember"}]}]}
    return {"inline_html": html, "company_cik": "1306830",
            "xbrls": [json.dumps({CONCEPT: [row]})]}


def test_real_ce_388m_recovered_via_rebuilt_anchor(tmp_path):
    anchor = _core_anchor(tmp_path)
    out = locate(anchor, _older_source())
    assert out["status"] is None, f"no recovery: {out['status']}"
    assert len(out["items"]) == 1
    item = out["items"][0]
    # the recovered fact retains: the exact concept, BOTH older-source
    # axis/member pairs, the exact claimed period, the declared unit, and the
    # element-local source evidence (the true printed row + scale header)
    x = item["xbrl"]
    assert x["concept"] == CONCEPT
    assert sorted(tuple(p) for p in x["axis_members"]) == [
        ("srt:StatementGeographicalAxis", "srt:NorthAmericaMember"),
        ("us-gaap:StatementBusinessSegmentsAxis", "ce:AcetylChainMember")]
    assert (x["period_start"], x["period_end"]) == ("2024-01-01", "2024-03-31")
    assert x["ptype"] == "duration" and x["unit"] == "usd"
    # printed 388 at scale 6 == the graph's 388,000,000
    assert item["value"] == Decimal("388")
    assert item["ix_evidence"]["scale"] == 6
    assert item["quote"] == "North America 388 365"      # the REAL table row
    assert x["source_evidence"]["quote_span"]
    # the evidence representation hash is PINNED — any silent change screams
    assert x["source_evidence"]["representation_sha256"] == SHA_EVIDENCE
    assert any(p["text"] == "(In $ millions)"
               for p in x["source_evidence"]["pieces"])
