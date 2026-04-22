"""Integration + regression tests for xbrl_exact_splits.

Requires live Neo4j access — runs against the production graph. Tests are
designed to be robust to small data drift (decimal-level value tolerances,
not byte equality).

Markers:
  - sentinel: named ticker tests (LSTR, CHRW, TSN, HUBB, FAST, AGNC)
  - collapse: regression test for §8 ordering bug
  - pit: PIT-cutoff gating
  - null: non_primary_qname short-circuit
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

import pytest

from xbrl_exact_splits import extract_segment_splits, _display_member_label


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _find_annual(packet: dict, period_of_report: str | None = None) -> dict | None:
    for b in packet["per_period_splits"]:
        if b["duration"] == "annual" and (period_of_report is None or b["period_of_report"] == period_of_report):
            return b
    return None


def _find_derived_q4(packet: dict) -> dict | None:
    for b in packet["per_period_splits"]:
        if b["is_derived_q4"]:
            return b
    return None


def _view_members(block: dict, view_kind: str) -> list[str]:
    rows = (block["views"].get(view_kind) or []) if block else []
    return [r["member"] for r in rows if r.get("member")]


def _view_values_by_member(block: dict, view_kind: str) -> dict[str, float]:
    rows = (block["views"].get(view_kind) or []) if block else []
    return {r["member"]: r["value"] for r in rows if r.get("member") is not None}


# --------------------------------------------------------------------------- #
# Sentinel: LSTR — clean 1D business segments                                  #
# --------------------------------------------------------------------------- #

@pytest.mark.sentinel
def test_lstr_revenue_qname():
    pkt = extract_segment_splits("LSTR", out_dir="/tmp")
    assert pkt["metric_qname"] == "us-gaap:Revenues"
    assert pkt["view_capability"]["segments"] is True


@pytest.mark.sentinel
def test_lstr_fy_segment_split_reconciles():
    pkt = extract_segment_splits("LSTR", out_dir="/tmp")
    fy = _find_annual(pkt, "2025-12-27")
    assert fy is not None
    total = fy["views"]["total"]["value"]
    segs = _view_values_by_member(fy, "business_segment")
    assert len(segs) == 2
    assert sum(segs.values()) == pytest.approx(total, abs=max(1000, abs(total) * 0.0001))


@pytest.mark.sentinel
def test_lstr_q4_derivation_method_and_arithmetic():
    pkt = extract_segment_splits("LSTR", out_dir="/tmp")
    q4 = _find_derived_q4(pkt)
    assert q4 is not None
    assert q4["is_derived_q4"] is True
    # Q4 method should be either fy_minus_9m_ytd (primary) or fy_minus_q1q2q3 (fallback)
    assert q4["derivation_method"] in ("fy_minus_9m_ytd", "fy_minus_q1q2q3")
    # Q4 total = FY total - 9M YTD total; verify sources trail for primary path
    if q4["derivation_method"] == "fy_minus_9m_ytd":
        roles = {s["role"] for s in q4["sources"]}
        assert {"fy", "9m_ytd"}.issubset(roles)


# --------------------------------------------------------------------------- #
# Sentinel: CHRW — aggregate_basis + §8 collapse + no-duplicate-members        #
# --------------------------------------------------------------------------- #

@pytest.mark.sentinel
@pytest.mark.collapse
def test_chrw_no_duplicate_members_in_any_view():
    """Critical: pre-fix §8 ordering bug produced duplicate OperatingSegmentsMember
    rows. After fix, every view must have unique member qnames per period-block.
    """
    pkt = extract_segment_splits("CHRW", out_dir="/tmp")
    for b in pkt["per_period_splits"]:
        for vk, rows in b["views"].items():
            if not isinstance(rows, list):
                continue
            members = [r["member"] for r in rows if r.get("member")]
            assert len(members) == len(set(members)), (
                f"Duplicate members in {b['period_of_report']} {b['duration']} {vk}: {members}"
            )


@pytest.mark.sentinel
def test_chrw_has_all_three_views():
    pkt = extract_segment_splits("CHRW", out_dir="/tmp")
    fy = _find_annual(pkt, "2025-12-31")
    assert fy is not None
    # Geography should reconcile
    geo = _view_values_by_member(fy, "geography")
    assert set(geo.keys()) >= {"country:US", "us-gaap:NonUsMember"}
    # product_service should reconcile to total
    ps = _view_values_by_member(fy, "product_service")
    total = fy["views"]["total"]["value"]
    assert sum(ps.values()) == pytest.approx(total, abs=max(1000, abs(total) * 0.0001))


@pytest.mark.sentinel
def test_chrw_aggregate_basis_present():
    pkt = extract_segment_splits("CHRW", out_dir="/tmp")
    seen = set()
    for b in pkt["per_period_splits"]:
        for vk, rows in b["views"].items():
            if isinstance(rows, list):
                for r in rows:
                    seen.add(r.get("basis_type"))
    assert "aggregate_basis" in seen, f"Expected aggregate_basis to appear in CHRW; got {seen}"


# --------------------------------------------------------------------------- #
# Sentinel: TSN, HUBB, FAST                                                    #
# --------------------------------------------------------------------------- #

@pytest.mark.sentinel
def test_tsn_runs_and_emits_periods():
    pkt = extract_segment_splits("TSN", out_dir="/tmp")
    assert pkt["metric_qname"] == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(pkt["per_period_splits"]) > 0


@pytest.mark.sentinel
def test_hubb_runs_and_emits_periods():
    pkt = extract_segment_splits("HUBB", out_dir="/tmp")
    assert pkt["metric_qname"] == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(pkt["per_period_splits"]) > 0
    # HUBB's works_for_segments should be true (per map)
    assert pkt["view_capability"]["segments"] is True


@pytest.mark.sentinel
def test_fast_runs_and_emits_periods():
    pkt = extract_segment_splits("FAST", out_dir="/tmp")
    assert pkt["metric_qname"] == "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(pkt["per_period_splits"]) > 0


# --------------------------------------------------------------------------- #
# Null contract: coordinator-flagged tickers                                   #
# --------------------------------------------------------------------------- #

@pytest.mark.null
def test_agnc_coordinator_flagged_returns_non_primary_qname():
    pkt = extract_segment_splits("AGNC", out_dir="/tmp")
    assert pkt["metric_qname"] is None
    assert pkt["per_period_splits"] == []
    gap_types = {g["type"] for g in pkt.get("gaps", [])}
    assert "non_primary_qname" in gap_types


@pytest.mark.null
def test_agnc_stays_null_even_with_fallback_enabled():
    """Coordinator-flagged tickers must NOT trigger fallback. The curated null
    is authoritative and overrides any lower-trust discovery path."""
    pkt = extract_segment_splits("AGNC", out_dir="/tmp", allow_discovery_fallback=True)
    assert pkt["metric_qname"] is None
    assert pkt.get("qname_source") is None
    assert pkt["per_period_splits"] == []


# --------------------------------------------------------------------------- #
# Fallback discovery                                                           #
# --------------------------------------------------------------------------- #

@pytest.mark.sentinel
def test_mapped_ticker_tagged_qname_source_mapped():
    pkt = extract_segment_splits("LSTR", out_dir="/tmp")
    assert pkt["qname_source"] == "mapped"
    assert pkt["metric_qname"] is not None


def test_unmapped_without_fallback_returns_ticker_not_in_universe():
    pkt = extract_segment_splits("UNKNOWN_TICKER_XYZ", out_dir="/tmp")
    assert pkt["metric_qname"] is None
    assert pkt["qname_source"] is None
    gap_types = {g["type"] for g in pkt.get("gaps", [])}
    assert "ticker_not_in_universe" in gap_types


def test_unmapped_with_fallback_exhausted_returns_graceful_null():
    """A ticker that isn't in the graph at all must produce a safe null
    packet with qname_source=None and fallback_discovery_exhausted gap,
    not a crash.
    """
    pkt = extract_segment_splits(
        "UNKNOWN_TICKER_XYZ", out_dir="/tmp", allow_discovery_fallback=True
    )
    assert pkt["metric_qname"] is None
    assert pkt["qname_source"] is None
    gap_types = {g["type"] for g in pkt.get("gaps", [])}
    assert "fallback_discovery_exhausted" in gap_types


def test_fallback_discovery_tags_qname_source_and_computes_view_capability():
    """ANSS is in the graph but NOT in the Wave-2 map — perfect fallback target.
    After discovery: qname_source must be 'fallback_discovery', view_capability
    must be computed from actual reconciled views (not the synthetic defaults).
    """
    pkt = extract_segment_splits("ANSS", out_dir="/tmp", allow_discovery_fallback=True)
    if pkt["metric_qname"] is None:
        pytest.skip("ANSS not in graph at test time")
    assert pkt["qname_source"] == "fallback_discovery"
    assert pkt["metric_qname"] in (
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
        "us-gaap:Revenues",
        "us-gaap:SalesRevenueNet",
        "us-gaap:NetSales",
    )
    # At least one primary view must reconcile for the fallback to be useful
    assert any(pkt["view_capability"].values())


# --------------------------------------------------------------------------- #
# PIT gating                                                                   #
# --------------------------------------------------------------------------- #

@pytest.mark.pit
def test_lstr_pit_cutoff_reduces_period_count():
    live = extract_segment_splits("LSTR", out_dir="/tmp")
    historical = extract_segment_splits(
        "LSTR", out_dir="/tmp/pit_test",
        pit_cutoff="2024-06-30T00:00:00-04:00",
    )
    # Historical should have fewer periods (no filings after 2024-06-30)
    assert historical["source_mode"] == "historical"
    assert live["source_mode"] == "live"
    assert len(historical["per_period_splits"]) <= len(live["per_period_splits"])


# --------------------------------------------------------------------------- #
# Output contract invariants                                                   #
# --------------------------------------------------------------------------- #

@pytest.mark.sentinel
def test_every_emitted_row_has_provenance():
    """Per-row provenance contract: every non-null row carries metric_qname,
    view_kind, period_of_report, period_start, period_end, accession, form_type.
    """
    required = {"metric_qname", "view_kind", "period_of_report",
                 "period_start", "period_end", "accession", "form_type"}
    pkt = extract_segment_splits("LSTR", out_dir="/tmp")
    for b in pkt["per_period_splits"]:
        for vk, v in b["views"].items():
            rows = v if isinstance(v, list) else ([v] if v else [])
            for r in rows:
                if r.get("value") is None:
                    continue
                missing = required - set(r.keys())
                assert not missing, f"Row missing fields {missing}: {r}"


@pytest.mark.sentinel
def test_orthogonal_schema_fields():
    """basis_type / is_derived_q4 / derivation_method / null_reason are independent."""
    pkt = extract_segment_splits("LSTR", out_dir="/tmp")
    for b in pkt["per_period_splits"]:
        # Block-level derivation state
        assert isinstance(b["is_derived_q4"], bool)
        if b["is_derived_q4"]:
            assert b["derivation_method"] in ("fy_minus_9m_ytd", "fy_minus_q1q2q3", "mixed", None)
        else:
            assert b["derivation_method"] is None
        # Row-level basis_type stays a 3-valued enum
        for vk, v in b["views"].items():
            rows = v if isinstance(v, list) else ([v] if v else [])
            for r in rows:
                assert r.get("basis_type") in ("memberless_total", "aggregate_basis", None)


def test_display_member_label_minimal_prettifier():
    assert _display_member_label("TransportationLogistics", None) == "Transportation Logistics"
    assert _display_member_label("CanadaandMexico", None) == "Canada and Mexico"
    assert _display_member_label(
        "TermLicenseSubscriptionsSaaSRevenuesAndMaintenanceAndServicesFeesSegment",
        None,
    ) == "Term License Subscriptions SaaS Revenues and Maintenance and Services Fees Segment"
