"""S3.4a — FACT-16 validator suite + lane fixtures + OD-21 traps F1-F9 / static positives.

Layout: golden lane x shape matrix (every combination must validate clean), then one
focused failing test per validator rule, then the OD-21 set. Writer-side traps
(two-scenario collision, null-clobber) live in test_driver_writer.py (4b).
"""
import pytest

from driver.core.driver_validators import (
    apply_inline_correction,
    compose_surprise_scope,
    surprise_position,
    validate_fact,
)

SRC_TIME = "2025-11-01T16:05:00"
QP = "gp_2025-07-01_2025-09-30"       # ended before SRC_TIME
QP_OPEN = "gp_2025-10-01_2025-12-31"  # NOT ended at SRC_TIME

DRIVERS = {
    "revenue": {"name": "revenue", "fact_type": "metric"},
    "revenue_guidance": {"name": "revenue_guidance", "fact_type": "guidance"},
    "revenue_surprise": {"name": "revenue_surprise", "fact_type": "surprise"},
    "workforce_reduction": {"name": "workforce_reduction", "fact_type": "action_event"},
    "untyped": {"name": "untyped"},
}


def mk(lane="metric", shape="point", **over):
    """A minimal VALID fact for the lane x shape golden matrix."""
    name = {"metric": "revenue", "guidance": "revenue_guidance",
            "surprise": "revenue_surprise", "action_event": "workforce_reduction"}[lane]
    fact = {
        "driver_name": name, "driver_state": {"metric": "reported",
        "guidance": "unknown", "surprise": "beat", "action_event": "announced"}[lane],
        "quote": "verbatim source words", "date": SRC_TIME, "source_type": "8k",
        "event_time": SRC_TIME,
        "level_low": None, "level_high": None, "level_unit": None,
        "change_value": None, "change_unit": None,
        "comparison_low": None, "comparison_high": None, "comparison_baseline": None,
        "value_text": None, "conditions": None, "company_confirmed": None,
        "xbrl_qname": None, "fiscal_year": 2025, "fiscal_quarter": 3,
        "period_scope": "quarter", "time_type": "duration",
        "period_u_id": QP, "gp_start_date": "2025-07-01", "gp_end_date": "2025-09-30",
        "level_shape_hint": None, "comparison_shape_hint": None,
        "surprise_basis_hint": None, "surprise": None,
    }
    if shape == "point":
        fact.update(level_low=100.0, level_high=100.0, level_unit="m_usd",
                    level_shape_hint="point")
    elif shape == "range":
        fact.update(level_low=100.0, level_high=120.0, level_unit="m_usd",
                    level_shape_hint="range")
    elif shape == "floor":
        fact.update(level_low=100.0, level_high=None, level_unit="m_usd",
                    level_shape_hint="floor")
    elif shape == "ceiling":
        fact.update(level_low=None, level_high=120.0, level_unit="m_usd",
                    level_shape_hint="ceiling")
    elif shape == "delta-only":
        fact.update(change_value=12.0, change_unit="percent_yoy")
    # numberless: all value slots stay None
    if lane == "guidance":
        fact["company_confirmed"] = True
        if shape == "numberless":
            fact["value_text"] = "similar to last year"
    if lane == "surprise":
        fact.update(surprise="actual_vs_consensus", surprise_basis_hint="actual",
                    comparison_baseline="consensus", driver_state="beat")
    if lane == "action_event":
        fact.update(period_u_id=None, gp_start_date=None, gp_end_date=None,
                    period_scope=None, fiscal_year=None, fiscal_quarter=None,
                    driver_state="announced")
        if shape == "delta-only":
            fact.update(change_value=5000.0, change_unit="count")
    fact.update(over)
    return fact


def home_for(surprise_fact):
    """The matching same-event home fact for a surprise."""
    lane = "guidance" if surprise_fact["surprise"] == "guidance_vs_consensus" else "metric"
    home = mk(lane, "numberless")
    for k in ("level_low", "level_high", "level_unit", "period_u_id", "gp_start_date",
              "gp_end_date", "period_scope", "time_type"):
        home[k] = surprise_fact[k]
    if lane == "guidance":
        home["company_confirmed"] = True
    home["driver_state"] = "reported" if lane == "metric" else "unknown"
    home["level_shape_hint"] = surprise_fact.get("level_shape_hint")
    return home


def check(fact, driver=None, homes=None):
    return validate_fact(fact, driver=driver or DRIVERS[fact["driver_name"]],
                         home_facts=homes)


def codes(violations):
    return {v.code for v in violations}


# ---- the golden lane x shape matrix ----

@pytest.mark.parametrize("lane", ["metric", "guidance", "surprise", "action_event"])
@pytest.mark.parametrize("shape", ["point", "range", "floor", "ceiling", "numberless",
                                   "delta-only"])
def test_golden_matrix_validates_clean(lane, shape):
    fact = mk(lane, shape)
    homes = [home_for(fact)] if lane == "surprise" else None
    assert check(fact, homes=homes) == [], f"{lane}/{shape}"


# ---- per-rule failing tests ----

def test_untyped_driver_rejected():
    assert "DRIVER" in codes(check(mk(), driver=DRIVERS["untyped"]))


def test_state_outside_lane_hard_fails():
    assert "STATE" in codes(check(mk("metric", "point", driver_state="raised")))
    assert "STATE" in codes(check(mk("guidance", "numberless", driver_state="beat")))


def test_quote_required_all_lanes():
    assert "QUOTE" in codes(check(mk(quote="")))


def test_shape_hint_missing_or_mismatched():
    assert "SHAPE" in codes(check(mk("metric", "point", level_shape_hint=None)))
    assert "SHAPE" in codes(check(mk("metric", "point", level_shape_hint="point",
                                     level_high=None, level_low=100.0)))  # point-as-low-only
    assert "SHAPE" in codes(check(mk("metric", "range", level_low=120.0, level_high=100.0)))


def test_sign_rule_increased_needs_positive():
    bad = mk("metric", "delta-only", driver_state="increased", change_value=-5.0)
    assert "SIGN" in codes(check(bad))
    ok = mk("metric", "delta-only", driver_state="increased", change_value=5.0)
    assert check(ok) == []


def test_sign_rule_excludes_beat_missed_P8():
    # P8: a lower-is-better beat (negative delta) must NOT be sign-rejected
    fact = mk("surprise", "point", driver_state="beat", change_value=None)
    fact.update(comparison_low=110.0, comparison_high=110.0, comparison_shape_hint="point")
    assert "SIGN" not in codes(check(fact, homes=[home_for(fact)]))


def test_baseline_enum_and_lane_rules():
    assert "BASELINE" in codes(check(mk(comparison_baseline="street")))
    assert "BASELINE" in codes(check(mk(comparison_baseline="consensus")))      # metric
    assert "BASELINE" in codes(check(mk(comparison_baseline="previous_guidance")))  # metric
    g = mk("guidance", "point", comparison_baseline="consensus")
    assert "BASELINE" in codes(check(g))


def test_units_required_with_numbers():
    assert "UNIT" in codes(check(mk("metric", "point", level_unit=None)))
    assert "UNIT" in codes(check(mk("metric", "delta-only", change_unit=None)))
    assert "UNIT" in codes(check(mk("metric", "point", level_unit="dollars")))
    assert "UNIT" in codes(check(mk("metric", "delta-only",
                                    change_unit="percent_sequential",
                                    period_scope="annual",
                                    period_u_id="gp_2025-01-01_2025-12-31",
                                    gp_start_date="2025-01-01", gp_end_date="2025-12-31")))


def test_period_symmetry_and_scope_pairing():
    assert "PERIOD_SYM" in codes(check(mk(period_u_id=None)))  # scope says quarter, no period
    assert "SCOPE_PAIR" in codes(check(mk(period_u_id="gp_ST", gp_start_date=None,
                                          gp_end_date=None)))  # dated scope, sentinel id
    ok = mk("guidance", "numberless", period_u_id="gp_ST", gp_start_date=None,
            gp_end_date=None, period_scope="short_term", fiscal_year=None,
            fiscal_quarter=None)
    assert "SCOPE_PAIR" not in codes(check(ok))
    assert "SCOPE_PAIR" in codes(check(mk(period_scope="long_range")))  # retired value


def test_instant_duration_legality():
    assert "INSTANT" in codes(check(mk(time_type="instant")))  # window id but instant
    ok = mk(time_type="instant", period_u_id="gp_2025-09-30_2025-09-30",
            gp_start_date="2025-09-30", gp_end_date="2025-09-30")
    assert "INSTANT" not in codes(check(ok))
    assert "INSTANT" in codes(check(mk(period_u_id="gp_2025-09-30_2025-09-30",
                                       gp_start_date="2025-09-30",
                                       gp_end_date="2025-09-30")))  # duration, one day


def test_value_text_lint():
    assert "VALUE_TEXT" in codes(check(mk("metric", "numberless",
                                          value_text="flat")))          # lane
    g = mk("guidance", "point", value_text="around $5B")
    assert "VALUE_TEXT" in codes(check(g))                              # not numberless
    g2 = mk("guidance", "numberless", value_text="roughly 15% higher")
    assert "VALUE_TEXT" in codes(check(g2))                             # numeric value inside
    g3 = mk("guidance", "numberless", value_text="similar to 2024 levels")
    assert "VALUE_TEXT" not in codes(check(g3))                         # year anchor allowed
    g4 = mk("guidance", "numberless", value_text="x" * 201)
    assert "VALUE_TEXT" in codes(check(g4))


def test_conditions_guidance_only_and_in_quote():
    m = mk("metric", "point", conditions="absent further tariffs")
    assert "CONDITIONS" in codes(check(m))
    g = mk("guidance", "numberless", value_text="modest growth",
           conditions="absent further tariffs",
           quote="we see modest growth absent further tariffs")
    assert "CONDITIONS" not in codes(check(g))
    g_bad = mk("guidance", "numberless", value_text="modest growth",
               conditions="absent further tariffs")
    assert "CONDITIONS" in codes(check(g_bad))


def test_company_confirmed_lane_rules():
    assert "LANE" in codes(check(mk("guidance", "numberless", company_confirmed=None)))
    assert "LANE" in codes(check(mk("metric", "point", company_confirmed=True)))


def test_xbrl_qname_metric_only():
    assert "LANE" in codes(check(mk("guidance", "numberless",
                                    xbrl_qname="us-gaap:Revenues")))


def test_movement_midpoint_rule():
    raised_ok = mk("guidance", "range", driver_state="raised",
                   comparison_low=90.0, comparison_high=100.0,
                   comparison_shape_hint="range", comparison_baseline="previous_guidance")
    assert "MOVEMENT" not in codes(check(raised_ok))
    raised_bad = mk("guidance", "range", driver_state="raised",
                    comparison_low=120.0, comparison_high=140.0,
                    comparison_shape_hint="range", comparison_baseline="previous_guidance")
    assert "MOVEMENT" in codes(check(raised_bad))
    unknown_skipped = mk("guidance", "range", driver_state="unknown",
                         comparison_low=120.0, comparison_high=140.0,
                         comparison_shape_hint="range",
                         comparison_baseline="previous_guidance")
    assert "MOVEMENT" not in codes(check(unknown_skipped))


def test_derivable_surprise_delta_never_stored():
    s = mk("surprise", "point", change_value=-10.0, change_unit="m_usd",
           comparison_low=110.0, comparison_high=110.0, comparison_shape_hint="point")
    assert "DERIVABLE" in codes(check(s, homes=[home_for(s)]))


def test_unknown_stored_field_rejected_dormant_xbrl_off():
    assert "UNKNOWN_FIELD" in codes(check(mk(origin="xbrl_link")))


def test_fabricated_period_token():
    fact = mk()
    fact["fact_scope_period_token"] = "gp_2020-01-01_2020-03-31"   # differs from period_u_id
    assert "PERIOD_SYM" in codes(check(fact))


# ---- OD-21: composition, F-traps, static positives ----

def test_compose_surprise_scope_all_valid_mappings_P6():
    assert compose_surprise_scope("actual", "consensus") == "actual_vs_consensus"
    assert compose_surprise_scope("actual", "previous_guidance") == "actual_vs_guidance"
    assert compose_surprise_scope("guidance", "consensus") == "guidance_vs_consensus"


def test_F5_guide_vs_own_prior_is_movement_not_surprise():
    with pytest.raises(ValueError, match="movement"):
        compose_surprise_scope("guidance", "previous_guidance")


def test_F1_surprise_slot_missing():
    s = mk("surprise", "point", surprise=None)
    assert "F1" in codes(check(s, homes=[home_for(mk('surprise', 'point'))]))


def test_F2_surprise_slot_on_other_lane():
    assert "F2" in codes(check(mk("metric", "point", surprise="actual_vs_consensus")))


def test_F3_basis_hint_required_and_lane_bound():
    s = mk("surprise", "point", surprise_basis_hint=None)
    assert "F3" in codes(check(s, homes=[home_for(s)]))
    assert "F3" in codes(check(mk("metric", "point", surprise_basis_hint="actual")))


def test_F4_baseline_required_on_surprise():
    s = mk("surprise", "point", comparison_baseline=None)
    assert "F4" in codes(check(s, homes=[home_for(s)]))


def test_F1_composition_mismatch():
    s = mk("surprise", "point", surprise="actual_vs_guidance")  # hint says consensus
    assert "F1" in codes(check(s, homes=[home_for(s)]))


def test_F6_missing_home_parks_whole_event():
    s = mk("surprise", "point")
    v = [x for x in check(s, homes=[]) if x.code == "F6"]
    assert v and v[0].action == "PARK" and "whole event" in v[0].message


def test_F7_actual_surprise_before_period_end_rejected():
    s = mk("surprise", "point", period_u_id=QP_OPEN, gp_start_date="2025-10-01",
           gp_end_date="2025-12-31")
    home = home_for(s)
    v = [x for x in check(s, homes=[home]) if x.code == "F7"]
    assert v and v[0].action == "REJECT"


def test_F7_guidance_vs_consensus_allowed_on_open_period():
    s = mk("surprise", "point", surprise="guidance_vs_consensus",
           surprise_basis_hint="guidance", period_u_id=QP_OPEN,
           gp_start_date="2025-10-01", gp_end_date="2025-12-31")
    assert "F7" not in codes(check(s, homes=[home_for(s)]))


def test_F8_ungrounded_results_beat_parks():
    s = mk("surprise", "numberless")
    v = [x for x in check(s, homes=[]) if x.code in ("F6", "F8")]
    assert v and all(x.action == "PARK" for x in v)


@pytest.mark.parametrize("break_key,mutate", [
    ("family", lambda h: h.update(driver_name="eps")),
    ("period", lambda h: h.update(period_u_id="gp_2025-04-01_2025-06-30",
                                  gp_start_date="2025-04-01", gp_end_date="2025-06-30")),
    ("period_scope", lambda h: h.update(period_scope="ytd")),
    ("slice", lambda h: h.update(slice_parts=[("product", "iphone")])),
    ("measurement", lambda h: h.update(measurement_tokens=["adjusted"])),
    ("value", lambda h: h.update(level_low=999.0, level_high=999.0)),
    ("unit", lambda h: h.update(level_unit="usd")),
])
def test_F9_each_home_key_tested_separately(break_key, mutate):
    s = mk("surprise", "point")
    home = home_for(s)
    mutate(home)
    v = [x for x in check(s, homes=[home]) if x.code == "F9"]
    assert v and v[0].action == "PARK" and break_key in v[0].message


def test_P5_numberless_surprise_with_numberless_home():
    s = mk("surprise", "numberless")
    home = home_for(s)
    assert check(s, homes=[home]) == []


# ---- surprise position + in_line (P3 / correction law) ----

def test_P3_guide_range_containing_consensus_is_in_line():
    pos = surprise_position(100.0, 120.0, 110.0, 110.0,   # guide range vs consensus point
                            value_is_guide=True)
    assert pos == "inside"
    assert apply_inline_correction("beat", pos, has_favorability_wording=False) == "in_line"


def test_actual_range_bracketing_expectation_is_the_unclear_case():
    # asymmetry per §4.3: an ACTUAL range overlapping the expectation unclearly stays
    # unknown unless the source states favorability — never auto-in_line
    pos = surprise_position(4.9, 5.0, 4.95, 4.95, value_is_guide=False)
    assert pos == "overlap"
    assert apply_inline_correction("unknown", pos, has_favorability_wording=False) == "unknown"


def test_wordless_unknown_inside_becomes_in_line():
    assert apply_inline_correction("unknown", "inside",
                                   has_favorability_wording=False) == "in_line"
    assert apply_inline_correction("unknown", "above",
                                   has_favorability_wording=False) == "unknown"


def test_wordless_inside_closed_range_corrected_stated_wording_kept():
    assert apply_inline_correction("beat", "inside", has_favorability_wording=True) == "beat"
    assert apply_inline_correction("missed", "above", has_favorability_wording=False) == "missed"


# ---- the 2026-07-16 hardening round (adjudicated external review) ----

def test_guidance_requires_a_period():
    g = mk("guidance", "numberless", period_u_id=None, gp_start_date=None,
           gp_end_date=None, period_scope=None, fiscal_year=None, fiscal_quarter=None)
    assert "PERIOD_LANE" in codes(check(g))


def test_guidance_vs_consensus_requires_target_period():
    s = mk("surprise", "numberless", surprise="guidance_vs_consensus",
           surprise_basis_hint="guidance", period_u_id=None, gp_start_date=None,
           gp_end_date=None, period_scope=None, fiscal_year=None, fiscal_quarter=None)
    assert "PERIOD_LANE" in codes(check(s, homes=[home_for(s)]))


@pytest.mark.parametrize("lane", ["metric", "surprise", "action_event"])
def test_sentinel_horizons_illegal_outside_guidance(lane):
    fact = mk(lane, "numberless", period_u_id="gp_LT", gp_start_date=None,
              gp_end_date=None, period_scope="long_term", fiscal_year=None,
              fiscal_quarter=None)
    homes = [home_for(fact)] if lane == "surprise" else None
    assert "PERIOD_LANE" in codes(check(fact, homes=homes))


def test_malformed_numbers_reject_cleanly_never_crash():
    got = check(mk("metric", "point", level_low="abc", level_high="abc"))
    assert "MALFORMED" in codes(got)
    got = check(mk("metric", "delta-only", change_value="12%",
                   driver_state="increased"))
    assert "MALFORMED" in codes(got)
    assert "MALFORMED" in codes(check(mk("metric", "point", level_low=True,
                                         level_high=True)))


def test_full_timestamp_required():
    assert "ISO" in codes(check(mk(date=None)))
    assert "ISO" in codes(check(mk(date="not-a-time")))


def test_exact_driver_match_required():
    assert "DRIVER" in codes(check(mk(), driver={"name": "eps", "fact_type": "metric"}))


def test_company_confirmed_false_is_reserved_and_type_exact():
    assert "LANE" in codes(check(mk("guidance", "numberless", company_confirmed=False)))
    assert "LANE" in codes(check(mk("guidance", "numberless", company_confirmed=1)))


def test_producers_never_supply_xbrl_qname():
    assert "LANE" in codes(check(mk("metric", "point", xbrl_qname="us-gaap:Revenues")))


def test_home_check_cannot_be_bypassed():
    s = mk("surprise", "point")
    v = [x for x in check(s, homes=None) if x.code == "F6"]
    assert v and v[0].action == "PARK"


def test_named_numberless_surprise_missing_home_is_F6_whole_event():
    s = mk("surprise", "numberless")
    v = [x for x in check(s, homes=[]) if x.code == "F6"]
    assert v and "whole event" in v[0].message


def test_reversed_range_with_invalid_hint_rejected():
    got = check(mk("metric", "range", level_low=120.0, level_high=100.0,
                   level_shape_hint="invalid"))
    assert "SHAPE" in codes(got)


def test_date_without_time_rejected():
    assert "ISO" in codes(check(mk(date="2025-11-01")))


def test_numberless_fact_with_unit_rules():
    assert "UNIT" in codes(check(mk("metric", "numberless", level_unit="dollars")))
    assert "UNIT" in codes(check(mk("metric", "numberless", level_unit="m_usd")))
    ok = mk("guidance", "numberless", level_unit="percent_yoy",
            value_text="double-digit growth")   # OD-11 numberless-growth framing
    assert "UNIT" not in codes(check(ok))
    assert "UNIT" in codes(check(mk("metric", "numberless",
                                    change_unit="percent_yoy")))  # unit w/o change_value


def test_nan_rejects_cleanly():
    got = check(mk("metric", "point", level_low=float("nan"), level_high=float("nan")))
    assert "MALFORMED" in codes(got)


def test_P4_old_guide_restated_after_period_end_stays_gvc():
    s = mk("surprise", "point", surprise="guidance_vs_consensus",
           surprise_basis_hint="guidance")          # QP ended before event_time
    assert check(s, homes=[home_for(s)]) == []


def test_P8_lower_is_better_beat_with_stated_negative_delta():
    # cost came in BELOW guidance by a stated $10M -> beat with a negative delta;
    # neither sign-rejected nor derivable-rejected (floor comparison = not derivable)
    s = mk("surprise", "numberless", driver_state="beat",
           change_value=-10.0, change_unit="m_usd",
           comparison_low=110.0, comparison_high=None, comparison_shape_hint="floor")
    got = check(s, homes=[home_for(s)])
    assert "SIGN" not in codes(got) and "DERIVABLE" not in codes(got)


def test_sentinel_periods_store_null_dates_and_need_time_type():
    bad = mk("guidance", "numberless", period_u_id="gp_ST", period_scope="short_term",
             gp_start_date="2025-01-01", gp_end_date=None,
             fiscal_year=None, fiscal_quarter=None)
    assert "SCOPE_PAIR" in codes(check(bad))
    bad2 = mk("guidance", "numberless", period_u_id="gp_ST", period_scope="short_term",
              gp_start_date=None, gp_end_date=None, time_type=None,
              fiscal_year=None, fiscal_quarter=None)
    assert "INSTANT" in codes(check(bad2))


def test_dated_period_dates_must_match_the_gp_id():
    bad = mk(gp_start_date="2025-01-01")           # id says 2025-07-01
    assert "PERIOD_SYM" in codes(check(bad))
    bad2 = mk(gp_start_date=None, gp_end_date=None)  # dated id with missing dates
    assert "PERIOD_SYM" in codes(check(bad2))


def test_F9_value_match_survives_float_representation_dirt():
    s = mk("surprise", "point", level_low=570.0, level_high=570.0)
    home = home_for(s)
    home["level_low"] = home["level_high"] = 570.0000000000001
    assert check(s, homes=[home]) == []            # same real value — never a mismatch


def test_id_and_scope_rebuild_agreement():
    fact = mk()
    fact["id"] = f"du:0000320193-24-000123:revenue:period={QP}"
    fact["fact_scope"] = f"period={QP}"
    assert "ID" not in codes(check(fact))
    fact["fact_scope"] = "period=gp_2020-01-01_2020-03-31"
    assert "ID" in codes(check(fact))
    fact2 = mk()
    fact2["id"] = "du:0000320193-24-000123:eps:period=" + QP   # wrong driver segment
    assert "ID" in codes(check(fact2))


def test_position_boundaries_and_open_shapes():
    assert surprise_position(110.0, 110.0, 100.0, 120.0) == "inside"
    assert surprise_position(120.0, 120.0, 100.0, 120.0) == "inside"   # exact boundary
    assert surprise_position(130.0, 130.0, 100.0, 120.0) == "above"
    assert surprise_position(90.0, 90.0, 100.0, 120.0) == "below"
    assert surprise_position(100.0, 100.0, 100.0, None) == "at_floor"
    assert surprise_position(120.0, 120.0, None, 120.0) == "at_ceiling"
