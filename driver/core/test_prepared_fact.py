"""PreparedFactV1 — the locked §11.4 input schema, pinned to the frozen packet
(15_CandidateFactPacket.md, sha aa7239ed) Block 2. Exact types only; unknown fields
reject; floats never accepted. TDD: written before the module."""
from decimal import Decimal

import pytest

from driver.core.prepared_fact import PreparedFactV1, RunInputV1, SchemaError


def minimal(**over):
    d = {"driver_name": "revenue", "driver_state": "reported",
         "quote": "iPhone revenue was $201,183 million"}
    d.update(over)
    return d


def test_minimal_fact_constructs_with_defaults():
    f = PreparedFactV1.from_dict(minimal())
    assert f.driver_name == "revenue" and f.level_low is None
    assert f.measurement_raw_spans == [] and f.slice_parts == []
    assert f.member_refs is None


def test_exact_numbers_accepted_floats_rejected():
    f = PreparedFactV1.from_dict(minimal(level_low=Decimal("201183"),
                                         level_high=201183))
    assert f.level_low == Decimal("201183") and f.level_high == 201183
    with pytest.raises(SchemaError, match="float"):
        PreparedFactV1.from_dict(minimal(level_low=201183.0))
    with pytest.raises(SchemaError, match="bool"):
        PreparedFactV1.from_dict(minimal(level_low=True))


def test_unknown_fields_reject():
    with pytest.raises(SchemaError, match="unknown"):
        PreparedFactV1.from_dict(minimal(surprise="actual_vs_consensus"))  # core-built
    with pytest.raises(SchemaError, match="unknown"):
        PreparedFactV1.from_dict(minimal(xbrl_qname="us-gaap:Revenues"))   # enrichment-only
    with pytest.raises(SchemaError, match="unknown"):
        PreparedFactV1.from_dict(minimal(id="du:x:y:z"))                   # CLI builds ids


def test_required_fields_enforced():
    for missing in ("driver_name", "driver_state", "quote"):
        d = minimal()
        del d[missing]
        with pytest.raises(SchemaError, match=missing):
            PreparedFactV1.from_dict(d)
    with pytest.raises(SchemaError, match="quote"):
        PreparedFactV1.from_dict(minimal(quote=""))


def test_typed_fields_enforced():
    with pytest.raises(SchemaError, match="fiscal_year"):
        PreparedFactV1.from_dict(minimal(fiscal_year="2025"))
    with pytest.raises(SchemaError, match="company_confirmed"):
        PreparedFactV1.from_dict(minimal(company_confirmed=1))
    with pytest.raises(SchemaError, match="slice_parts"):
        PreparedFactV1.from_dict(minimal(slice_parts="product:iphone"))
    ok = PreparedFactV1.from_dict(minimal(slice_parts=[["product", "iPhone"]],
                                          measurement_raw_spans=["Adjusted"]))
    assert ok.slice_parts == [("product", "iPhone")]


def xbrl(**over):
    """A complete all-or-nothing XBRL context bundle (owner 2026-07-17)."""
    d = {"xbrl_concept_raw": "us-gaap:Revenues", "member_refs": [],
         "time_type": "duration", "period_start_date": "2025-06-29",
         "period_end_date": "2025-09-27"}
    d.update(over)
    return d


def test_member_refs_typed_but_carried_for_the_deferral_fence():
    f = PreparedFactV1.from_dict(minimal(**xbrl(
        member_refs=[{"axis": "srt:StatementGeographicalAxis",
                      "member": "srt:EuropeMember", "slice_part": "geography:europe"}])))
    assert f.member_refs[0]["axis"].endswith("GeographicalAxis")
    with pytest.raises(SchemaError, match="member_refs"):
        PreparedFactV1.from_dict(minimal(**xbrl(member_refs=[{"member": "x"}])))


def test_run_input_wraps_source_and_facts():
    run = RunInputV1.from_dict({"source_id": "0000320193-24-000123",
                                "facts": [minimal()]})
    assert run.source_id == "0000320193-24-000123"
    assert run.calendar_override is False and len(run.facts) == 1
    with pytest.raises(SchemaError, match="source_id"):
        RunInputV1.from_dict({"facts": [minimal()]})
    with pytest.raises(SchemaError, match="unknown"):
        RunInputV1.from_dict({"source_id": "x", "facts": [], "ticker": "AAPL"})


def test_the_field_set_is_exactly_block2_plus_lane_transients():
    # pinned inventory — a change here = a schema amendment (owner review)
    assert sorted(PreparedFactV1.FIELDS) == sorted([
        "driver_name", "driver_state", "quote",
        "level_low", "level_high", "change_value", "comparison_low", "comparison_high",
        "comparison_baseline", "value_text", "conditions", "company_confirmed",
        "level_unit_raw", "change_unit_raw",
        "level_unit_kind_hint", "level_money_mode_hint",
        "change_unit_kind_hint", "change_money_mode_hint",
        "level_shape_hint", "comparison_shape_hint", "measurement_raw_spans",
        "period_start_date", "period_end_date", "fiscal_year", "fiscal_quarter",
        "half", "month", "long_range_start_year", "long_range_end_year",
        "sentinel_class", "time_type", "period_scope",
        "slice_parts", "member_refs", "surprise_basis_hint",
        "sequential_evidence", "has_favorability_wording", "polarity_proof",
        "xbrl_concept_raw",
    ])


# ---- corrected-round additions (each reproduced as a bug first) ----

def test_direct_construction_validates_too():
    with pytest.raises(SchemaError, match="float"):
        PreparedFactV1(driver_name="revenue", driver_state="reported", quote="q",
                       level_low=1.5)
    with pytest.raises(SchemaError, match="quote"):
        PreparedFactV1(driver_name="revenue", driver_state="reported", quote="   ")


def test_nonfinite_decimal_rejected():
    for bad in (Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(SchemaError, match="finite"):
            PreparedFactV1.from_dict(minimal(level_low=bad))


def test_malformed_packets_reject_cleanly_never_crash():
    for bad in (None, [], "x", 42):
        with pytest.raises(SchemaError):
            PreparedFactV1.from_dict(bad)
    with pytest.raises(SchemaError):
        RunInputV1.from_dict({"source_id": "x", "facts": [None]})
    with pytest.raises(SchemaError):
        RunInputV1.from_dict(None)


def test_sequential_evidence_carried_and_typed():
    assert PreparedFactV1.from_dict(minimal()).sequential_evidence is False
    ok = PreparedFactV1.from_dict(minimal(sequential_evidence=True))
    assert ok.sequential_evidence is True                 # 'up 5% from last quarter'
    with pytest.raises(SchemaError, match="sequential_evidence"):
        PreparedFactV1.from_dict(minimal(sequential_evidence="yes"))


def test_surprise_evidence_fields():
    ok = PreparedFactV1.from_dict(minimal(
        has_favorability_wording=False,
        polarity_proof={"polarity": "higher_favorable", "basis": "source_framing",
                        "evidence": "came in ahead of plan", "sentence": "one line"}))
    assert ok.has_favorability_wording is False
    with pytest.raises(SchemaError, match="polarity"):     # pinned two-value enum
        PreparedFactV1.from_dict(minimal(
            polarity_proof={"polarity": "favorable", "basis": "source_framing",
                            "evidence": "e", "sentence": "s"}))
    with pytest.raises(SchemaError, match="basis"):
        PreparedFactV1.from_dict(minimal(
            polarity_proof={"polarity": "favorable", "basis": "gut_feeling",
                            "evidence": "e", "sentence": "s"}))
    with pytest.raises(SchemaError, match="polarity_proof"):
        PreparedFactV1.from_dict(minimal(polarity_proof={"polarity": "favorable"}))


def test_xbrl_concept_raw_is_transient_evidence_only():
    ok = PreparedFactV1.from_dict(minimal(**xbrl()))
    assert ok.xbrl_concept_raw == "us-gaap:Revenues"      # feeds UNIT resolution only
    with pytest.raises(SchemaError, match="unknown"):
        PreparedFactV1.from_dict(minimal(xbrl_qname="us-gaap:Revenues"))  # stored: never


def test_member_refs_tristate_semantics():
    non_xbrl = PreparedFactV1.from_dict(minimal())
    verified_empty = PreparedFactV1.from_dict(minimal(**xbrl(member_refs=[])))
    assert non_xbrl.member_refs is None                    # non-XBRL item
    assert verified_empty.member_refs == []                # VERIFIED-empty dimensions


# ---- owner 2026-07-17: XBRL all-or-nothing + blanket blank rejection ----

def test_xbrl_context_is_all_or_nothing():
    assert PreparedFactV1.from_dict(minimal(**xbrl())).time_type == "duration"
    partials = [
        {k: v for k, v in xbrl().items() if k != "member_refs"},         # concept only
        {k: v for k, v in xbrl().items() if k != "xbrl_concept_raw"},    # refs only
        {k: v for k, v in xbrl().items() if k != "period_end_date"},     # no end date
        {k: v for k, v in xbrl().items() if k != "period_start_date"},   # duration, no start
        {k: v for k, v in xbrl().items() if k != "time_type"},           # no time_type
    ]
    for p in partials:
        with pytest.raises(SchemaError, match="all-or-nothing"):
            PreparedFactV1.from_dict(minimal(**p))
    instant = PreparedFactV1.from_dict(minimal(**xbrl(
        time_type="instant", period_start_date=None, period_end_date="2025-09-27")))
    assert instant.period_start_date is None               # instants need end only
    with pytest.raises(SchemaError, match="ONLY period_end_date"):
        PreparedFactV1.from_dict(minimal(**xbrl(time_type="instant")))  # start conflicts


def test_member_refs_reject_hidden_extra_fields():
    with pytest.raises(SchemaError, match="EXACTLY"):
        PreparedFactV1.from_dict(minimal(**xbrl(member_refs=[
            {"axis": "a", "member": "m", "slice_part": "s", "sneaky": "x"}])))


def test_exact_dates_alone_stay_non_xbrl_legal():
    ok = PreparedFactV1.from_dict(minimal(
        period_start_date="2025-06-29", period_end_date="2025-09-27",
        time_type="duration"))                             # e.g. SEC-sourced dates
    assert ok.xbrl_concept_raw is None and ok.member_refs is None


def test_blank_strings_rejected_everywhere_none_when_absent():
    for field in ("value_text", "conditions", "level_unit_raw", "period_end_date"):
        with pytest.raises(SchemaError, match="blank"):
            PreparedFactV1.from_dict(minimal(**{field: "   "}))
        with pytest.raises(SchemaError, match="blank"):
            PreparedFactV1.from_dict(minimal(**{field: ""}))
    with pytest.raises(SchemaError, match="measurement_raw_spans"):
        PreparedFactV1.from_dict(minimal(measurement_raw_spans=["Adjusted", " "]))
    with pytest.raises(SchemaError, match="slice_parts"):
        PreparedFactV1.from_dict(minimal(slice_parts=[["product", "   "]]))
    with pytest.raises(SchemaError, match="member_refs"):
        PreparedFactV1.from_dict(minimal(**xbrl(
            member_refs=[{"axis": " ", "member": "m", "slice_part": "s"}])))
    assert PreparedFactV1.from_dict(minimal(value_text=None)).value_text is None
