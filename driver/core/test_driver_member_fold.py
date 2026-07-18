"""The FIVE FS-18 pinned test cases, exactly as ruled (STATUS R9 2026-07-17:
same-kind fold · cross-kind separate · unknown-vs-known separate ·
Europe≠EuropeSegment · same member on different axes = separate exact
axis/member links). Fold equality = the complete kind:norm(value) token, exact,
within one company (FINAL_DESIGN §5.2 FS-18) — the shared FORMAT-ONLY
normalizer, never stemming or suffix-stripping. Case 5 pins the MAPS_TO_MEMBER
op carrying BOTH axis and member (FINAL_DESIGN:178) so equal member labels on
different axes stay two distinct exact links."""
from decimal import Decimal

from driver.core.driver_ids import encode_unknown_axis
from driver.core.driver_member_fold import fold_target, member_token
from driver.core.driver_writer import FakeGraph, plan_event_write

SRC = "0000320193-26-000042"
QP = "gp_2025-07-01_2025-09-30"


def test_case1_same_kind_exact_token_folds():
    menu = {"geography:international", "segment:consumer"}
    tok = member_token("geography", "International")
    assert tok == "geography:international"
    # fold = the link clips onto the EXISTING value; no new value is coined
    assert fold_target(menu, tok) == "geography:international"


def test_case2_cross_kind_equal_value_never_folds():
    menu = {"geography:international"}
    tok = member_token("segment", "International")
    assert tok == "segment:international"
    assert fold_target(menu, tok) is None      # equal strings, different kinds


def test_case3_unknown_vs_known_never_folds():
    menu = {"geography:international"}
    tok = encode_unknown_axis("acme:MysteryAxis", "International")
    assert tok.startswith("unknown:xbrlaxis_")  # the sentinel IS its own kind
    assert fold_target(menu, tok) is None


def test_case4_no_suffix_stripping_europesegment_is_not_europe():
    menu = {"segment:europe"}
    tok = member_token("segment", "EuropeSegment")
    assert tok == "segment:europesegment"       # format-only normalization
    assert fold_target(menu, tok) is None


def _fact_with_two_axes_same_member():
    return {
        "id": f"du:{SRC}:revenue:period={QP}",
        "fact_scope": f"period={QP}", "driver_name": "revenue",
        "driver_state": "reported", "quote": "q",
        "date": "2025-11-01T16:05:00", "source_type": "8k",
        "level_low": 100, "level_high": 100, "level_unit": "m_usd",
        "change_value": None, "change_unit": None,
        "comparison_low": None, "comparison_high": None,
        "comparison_baseline": None, "value_text": None, "conditions": None,
        "company_confirmed": None, "xbrl_qname": None,
        "fiscal_year": 2025, "fiscal_quarter": 3,
        "period_scope": "quarter", "time_type": "duration",
        "period_u_id": QP, "gp_start_date": "2025-07-01",
        "gp_end_date": "2025-09-30",
        "member_refs": [
            {"axis": "srt:StatementGeographicalAxis",
             "member": "country:US", "slice_part": "geography:us"},
            {"axis": "us-gaap:StatementBusinessSegmentsAxis",
             "member": "country:US", "slice_part": "segment:us"}],
    }


def test_case5_same_member_on_different_axes_two_exact_axis_member_links():
    res = plan_event_write([_fact_with_two_axes_same_member()], FakeGraph())
    assert res[0].outcome == "created"
    edges = [op for op in res[0].ops if op.get("type") == "MAPS_TO_MEMBER"]
    # axis is part of the edge IDENTITY (top level) — two axes with one member
    # stay two distinct links and can never overwrite each other
    assert [(e["to"], e["axis"], e["props"]["slice_part"]) for e in edges] == [
        ("country:US", "srt:StatementGeographicalAxis", "geography:us"),
        ("country:US", "us-gaap:StatementBusinessSegmentsAxis", "segment:us")]
    assert len({(e["from"], e["type"], e["to"], e["axis"]) for e in edges}) == 2


# ---- the same five cases END-TO-END through run_event (owner order: no
# bypass — refs carried through the CLI, fence removed, menu PIT-fetched) ----

from driver.core.test_driver_write_cli import (FakeStore, audit_docs,  # noqa: E402
                                               enabled_run, fact, run)

_USED = ["period=gp_2025-01-01_2025-03-31|slice=geography:international"]


def _row(dims):
    # a CURRENT-filing verification row matching the default fact() claim
    # (duration 2025-06-29..2025-09-27 inclusive -> stored end EXCLUSIVE)
    return {"period_type": "duration", "start_date": "2025-06-29",
            "end_date": "2025-09-28", "dims": [dict(d) for d in dims]}


def _menu_store(used=_USED, dims=()):
    # dims = the current filing's fact-level dimension set the refs must match
    return FakeStore(slice_menu={"xbrl_members": [], "used_scopes": list(used)},
                     xbrl_facts={"us-gaap:Revenues": [_row(dims)]})


def _first_fold(tmp_path):
    return audit_docs(tmp_path)[0]["member_menu"]["folds"]["0"][0]


def test_e2e_case1_same_kind_exact_token_folds(tmp_path):
    out = run(tmp_path, [fact(
        slice_parts=[("geography", "International")],
        member_refs=[{"axis": "srt:StatementGeographicalAxis",
                      "member": "country:XX",
                      "slice_part": "geography:international"}],
        xbrl_concept_raw="us-gaap:Revenues")],
        _menu_store(dims=[{"axis": "srt:StatementGeographicalAxis",
                           "member": "country:XX", "label": "International"}]))
    assert out["items"][0]["decision"] == "written"
    assert _first_fold(tmp_path)["fold"] is True           # clips onto the menu value


def test_e2e_case2_cross_kind_equal_value_never_folds(tmp_path):
    out = run(tmp_path, [fact(
        slice_parts=[("segment", "International")],
        member_refs=[{"axis": "us-gaap:StatementBusinessSegmentsAxis",
                      "member": "acme:InternationalMember",
                      "slice_part": "segment:international"}],
        xbrl_concept_raw="us-gaap:Revenues")],
        _menu_store(dims=[{"axis": "us-gaap:StatementBusinessSegmentsAxis",
                           "member": "acme:InternationalMember",
                           "label": "International"}]))
    assert out["items"][0]["decision"] == "written"
    assert _first_fold(tmp_path)["fold"] is False          # geography ≠ segment


def test_e2e_case3_unknown_axis_provisional_never_folds_with_known(tmp_path):
    part = encode_unknown_axis("acme:MysteryAxis", "International")
    out = run(tmp_path, [fact(
        slice_parts=[("unknown", part.split(":", 1)[1])],
        member_refs=[{"axis": "acme:MysteryAxis",
                      "member": "acme:InternationalMember", "slice_part": part}],
        xbrl_concept_raw="us-gaap:Revenues")],
        _menu_store(dims=[{"axis": "acme:MysteryAxis",
                           "member": "acme:InternationalMember",
                           "label": "International"}]))
    assert out["items"][0]["decision"] == "written"        # provisional, never dropped
    assert _first_fold(tmp_path)["fold"] is False


def test_e2e_case4_no_suffix_stripping_europesegment_is_not_europe(tmp_path):
    out = run(tmp_path, [fact(
        slice_parts=[("segment", "EuropeSegment")],
        member_refs=[{"axis": "us-gaap:StatementBusinessSegmentsAxis",
                      "member": "acme:EuropeSegmentMember",
                      "slice_part": "segment:europesegment"}],
        xbrl_concept_raw="us-gaap:Revenues")],
        _menu_store(["period=gp_2025-01-01_2025-03-31|slice=segment:europe"],
                    dims=[{"axis": "us-gaap:StatementBusinessSegmentsAxis",
                           "member": "acme:EuropeSegmentMember",
                           "label": "EuropeSegment"}]))
    assert out["items"][0]["decision"] == "written"
    assert _first_fold(tmp_path)["fold"] is False          # format-only normalizer


def test_e2e_case5_two_axes_same_member_two_links_written(tmp_path):
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [_row([
        {"axis": "srt:StatementGeographicalAxis", "member": "country:US",
         "label": "US"},
        {"axis": "us-gaap:StatementBusinessSegmentsAxis",
         "member": "country:US", "label": "US"}])]})
    out = enabled_run(tmp_path, [fact(
        slice_parts=[("geography", "US"), ("segment", "US")],
        member_refs=[
            {"axis": "srt:StatementGeographicalAxis",
             "member": "country:US", "slice_part": "geography:us"},
            {"axis": "us-gaap:StatementBusinessSegmentsAxis",
             "member": "country:US", "slice_part": "segment:us"}],
        xbrl_concept_raw="us-gaap:Revenues")], store)
    assert out["status"] == "committed"
    assert out["items"][0]["decision"] == "written"
    edges = [o for o in store.applied if o.get("type") == "MAPS_TO_MEMBER"]
    assert sorted((e["axis"], e["to"]) for e in edges) == [
        ("srt:StatementGeographicalAxis", "country:US"),
        ("us-gaap:StatementBusinessSegmentsAxis", "country:US")]
    assert len({(e["from"], e["type"], e["to"], e["axis"]) for e in edges}) == 2


def test_e2e_fused_fragments_inherit_the_one_claim(tmp_path):
    # two fragments of ONE fact (level + change) — the XBRL fragment carries the
    # ref; the prose fragment carries none (None = no claim, inherited).
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [_row(
        [{"axis": "srt:StatementGeographicalAxis", "member": "country:US",
          "label": "US"}])]})
    a = fact(slice_parts=[("geography", "US")],
             member_refs=[{"axis": "srt:StatementGeographicalAxis",
                           "member": "country:US", "slice_part": "geography:us"}],
             xbrl_concept_raw="us-gaap:Revenues")
    b = fact(level_low=None, level_high=None, level_unit_raw=None,
             level_shape_hint=None, change_value=Decimal("12"),
             change_unit_raw="%", slice_parts=[("geography", "US")])
    out = enabled_run(tmp_path, [a, b], store)
    assert out["status"] == "committed"
    assert [i["decision"] for i in out["items"]] == ["written", "written"]
    assert out["items"][0]["fact_id"] == out["items"][1]["fact_id"]  # fused
    edges = [o for o in store.applied if o.get("type") == "MAPS_TO_MEMBER"]
    assert [(e["to"], e["axis"]) for e in edges] == [
        ("country:US", "srt:StatementGeographicalAxis")]   # inherited, exactly once


def test_e2e_fusion_verified_empty_vs_refs_parks_both(tmp_path):
    # the filing REALLY carries both shapes (a dimensionless total AND a sliced
    # row) — each fragment's claim verifies, so the CONTRADICTION reaches fusion
    store = FakeStore(xbrl_facts={"us-gaap:Revenues": [_row([]), _row(
        [{"axis": "srt:StatementGeographicalAxis", "member": "country:US",
          "label": "US"}])]})
    a = fact(slice_parts=[("geography", "US")], member_refs=[],
             xbrl_concept_raw="us-gaap:Revenues")          # VERIFIED zero dims
    b = fact(level_low=None, level_high=None, level_unit_raw=None,
             level_shape_hint=None, change_value=Decimal("12"),
             change_unit_raw="%", slice_parts=[("geography", "US")],
             member_refs=[{"axis": "srt:StatementGeographicalAxis",
                           "member": "country:US", "slice_part": "geography:us"}],
             xbrl_concept_raw="us-gaap:Revenues")
    out = run(tmp_path, [a, b], store)
    assert [i["decision"] for i in out["items"]] == ["parked", "parked"]
    assert all(i["codes"] == ["FUSION_AMBIGUOUS"] for i in out["items"])
    assert "member_refs conflict" in out["items"][0]["detail"]
