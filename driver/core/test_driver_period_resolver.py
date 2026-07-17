"""S3.2 — the 21 required period tests (GuidancePeriod.md §Required Tests) + new-law guards.

YTD/TTM windows were proven on paper for Dec AND non-Dec FYE before coding (the doc's
mandate); the pinned strings below ARE those proofs. Legislated deltas from the old
substrate (each anchored in consolidated law) are tested explicitly:
  - long_range scope retired -> exact_range (id/dates unchanged)     [95 #23 / FINAL §6.2]
  - quiet gp_UNDEF fallthrough forbidden -> raises                   [FINAL §6.2]
  - year-2000 month (missing fiscal_year) forbidden -> raises        [BUILD §10 hazard]
  - time_type REQUIRED, never defaulted; label hint never overrides  [FACT-18 / packet law]
"""
import pytest

from driver.core.driver_period_resolver import (
    PeriodResolutionError,
    ensure_driver_period,
)
from driver.core.driver_ids import build_id


def resolve(item, fye=12, **kw):
    kw.setdefault("fact_type", "guidance")
    return ensure_driver_period(item, fye_month=fye, **kw)


# ---- tests 2-5: quarter / annual / half / month ----

def test_2_quarter_dec_and_sep_fye():
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-07-01_2025-09-30"
    assert out["period_scope"] == "quarter" and out["time_type"] == "duration"
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"}, fye=9)
    assert out["period_u_id"] == "gp_2024-10-01_2024-12-31"  # doc-verified example


def test_3_annual():
    out = resolve({"fiscal_year": 2025, "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-01-01_2025-12-31"
    assert out["period_scope"] == "annual"
    out = resolve({"fiscal_year": 2025, "time_type": "duration"}, fye=9)
    assert out["period_u_id"] == "gp_2024-10-01_2025-09-30"


def test_4_half():
    out = resolve({"fiscal_year": 2025, "half": 1, "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-01-01_2025-06-30"
    assert out["period_scope"] == "half"


def test_5_month():
    out = resolve({"fiscal_year": 2025, "month": 7, "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-07-01_2025-07-31"
    assert out["period_scope"] == "monthly"


# ---- test 6: long-range (id/dates as old; scope legislated to exact_range) ----

def test_6_long_range_scope_remapped():
    out = resolve({"long_range_start_year": 2027, "long_range_end_year": 2030,
                   "time_type": "duration"})
    assert out["period_u_id"] == "gp_2027-01-01_2030-12-31"
    assert out["period_scope"] == "exact_range"  # 'long_range' is retired


# ---- test 7: sentinels, two-way invariant ----

@pytest.mark.parametrize("cls,gp", [
    ("short_term", "gp_ST"), ("medium_term", "gp_MT"),
    ("long_term", "gp_LT"), ("undefined", "gp_UNDEF"),
])
def test_7_sentinels(cls, gp):
    out = resolve({"sentinel_class": cls, "time_type": "duration"})
    assert out["period_u_id"] == gp
    assert out["period_scope"] == cls
    assert out["gp_start_date"] is None and out["gp_end_date"] is None


# ---- tests 8-9: instant handling ----

def test_8_instant_collapses_to_date_twice():
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "instant"})
    assert out["period_u_id"] == "gp_2025-09-30_2025-09-30"
    assert out["time_type"] == "instant" and out["period_scope"] == "quarter"


def test_9_known_instant_label_never_overrides_stated_time_type():
    # cash_and_equivalents is in KNOWN_INSTANT_LABELS; time_type stays authoritative (FACT-18)
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "duration",
                   "label_slug": "cash_and_equivalents"})
    assert out["time_type"] == "duration"
    assert out["period_u_id"] == "gp_2025-07-01_2025-09-30"


# ---- test 10: calendar override forces Dec + skips company lookups ----

def test_10_calendar_override_routes_before_lookups():
    poisoned = {
        "existing": lambda *a: pytest.fail("existing-period lookup must be skipped"),
        "sec": lambda *a: pytest.fail("SEC cache must be skipped"),
        "predict": lambda *a: pytest.fail("predict must be skipped"),
        "corrected_fye": lambda *a: pytest.fail("corrected-FYE must be skipped"),
    }
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration",
                   "calendar_override": True},
                  fye=9, ticker="OIL", lookups=poisoned)
    assert out["period_u_id"] == "gp_2025-01-01_2025-03-31"  # calendar Q1, not Sep-FYE Q1


# ---- test 11: fail closed on missing FYE ----

def test_11_missing_fye_raises_never_defaults_december():
    with pytest.raises(PeriodResolutionError):
        resolve({"fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"}, fye=None)


# ---- test 12: pre-resolved id preserved ----

def test_12_existing_period_u_id_preserved():
    out = resolve({"period_u_id": "gp_2023-10-01_2023-12-31", "period_scope": "quarter",
                   "time_type": "duration"})
    assert out["period_u_id"] == "gp_2023-10-01_2023-12-31"
    assert out["gp_start_date"] == "2023-10-01" and out["gp_end_date"] == "2023-12-31"
    out = resolve({"period_u_id": "gp_LT", "period_scope": "long_term", "time_type": "duration"})
    assert out["gp_start_date"] is None


# ---- tests 13/15/19: identity integration with the ID law ----

def test_13_15_19_same_window_different_lanes_and_scope_token():
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"})
    gp = out["period_u_id"]
    src = "0000320193-24-000123"
    id_metric, scope_m = build_id(src, "revenue", period_id=gp)
    id_guid, _ = build_id(src, "revenue_guidance", period_id=gp)
    id_surp, _ = build_id(src, "revenue_surprise", period_id=gp,
                          surprise="actual_vs_consensus")
    assert len({id_metric, id_guid, id_surp}) == 3          # separate buckets (test 13)
    assert f"period={gp}" in scope_m                        # fact_scope carries it (test 15)
    # test 19: the HAS_PERIOD target id and the period= token come from the SAME resolver
    # output — one variable, asserted here as the single source both consumers use.
    assert scope_m.split("period=")[1].split("|")[0] == gp


# ---- test 14: periodless -> None ----

def test_14_periodless_returns_none():
    assert resolve({"quote": "CEO resigned"}, fact_type="action_event") is None


# ---- test 16: event-derived fields resolve like stated fields ----

def test_16_event_derived_fields_resolve():
    # the CLI derives {fiscal_year, fiscal_quarter} from report metadata, then calls us
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"},
                  fact_type="metric")
    assert out["period_u_id"] == "gp_2025-01-01_2025-03-31"


# ---- tests 17/18/21: YTD + TTM — the paper proofs, Dec AND Sep FYE ----

def test_17_ytd_fiscal_math_proofs():
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "ytd",
                   "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-01-01_2025-09-30"   # nine months, Dec FYE
    assert out["period_scope"] == "ytd"
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "ytd",
                   "time_type": "duration"}, fye=9)
    assert out["period_u_id"] == "gp_2024-10-01_2025-06-30"   # nine months, Sep FYE


def test_18_ttm_fiscal_math_proofs():
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "ttm",
                   "time_type": "duration"})
    assert out["period_u_id"] == "gp_2024-10-01_2025-09-30"   # exactly 12 months, Dec FYE
    assert out["period_scope"] == "ttm"
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 2, "period_scope": "ttm",
                   "time_type": "duration"}, fye=9)
    assert out["period_u_id"] == "gp_2024-04-01_2025-03-31"   # exactly 12 months, Sep FYE


def test_17b_ytd_exact_dates_win():
    out = resolve({"period_start_date": "2025-01-01", "period_end_date": "2025-09-30",
                   "period_scope": "ytd", "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-01-01_2025-09-30"
    assert out["period_scope"] == "ytd"


# ---- test 20: exact dates beat computed fiscal math ----

def test_20_exact_dates_win_over_fiscal_shorthand():
    # 52/53-week filer: XBRL quarter end 2025-09-27 vs month-boundary 2025-09-30
    out = resolve({"period_start_date": "2025-06-29", "period_end_date": "2025-09-27",
                   "fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "duration"})
    assert out["period_u_id"] == "gp_2025-06-29_2025-09-27"
    # scope pin AMENDED (period-audit round): a declared quarter is "quarter" on every
    # path — the old exact_range pin was the reproduced scope-divergence bug itself
    assert out["period_scope"] == "quarter"


def test_20b_exact_instant_single_date():
    out = resolve({"period_end_date": "2025-09-27", "time_type": "instant"},
                  fact_type="metric")
    assert out["period_u_id"] == "gp_2025-09-27_2025-09-27"
    assert out["time_type"] == "instant"


# ---- test 1: parity with the old substrate (pure lane; ticker=None skips A/B/C) ----

def test_1_parity_old_ensure_period_vs_new():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                           / ".claude/skills/earnings-orchestrator/scripts"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from guidance_write_cli import _ensure_period

    cases = [
        {"fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "duration"},
        {"fiscal_year": 2025, "time_type": "duration"},
        {"fiscal_year": 2025, "half": 2, "time_type": "duration"},
        {"fiscal_year": 2025, "month": 2, "time_type": "duration"},
        {"sentinel_class": "long_term", "time_type": "duration"},
        {"long_range_end_year": 2030, "time_type": "duration"},
        {"fiscal_year": 2025, "fiscal_quarter": 4, "time_type": "instant"},
    ]
    for case in cases:
        old = _ensure_period(dict(case), 12, ticker=None)
        new = ensure_driver_period(dict(case), fact_type="guidance", fye_month=12)
        assert new["period_u_id"] == old["period_u_id"], case
        assert new["gp_start_date"] == old["gp_start_date"], case
        assert new["gp_end_date"] == old["gp_end_date"], case
        assert new["time_type"] == old["time_type"], case
        if old["period_scope"] == "long_range":   # legislated retirement, the ONE delta
            assert new["period_scope"] == "exact_range"
        else:
            assert new["period_scope"] == old["period_scope"], case


# ---- cascade A/B/C behavior with injected lookups ----

def test_cascade_order_existing_then_sec_then_predict():
    calls = []
    lookups = {
        "existing": lambda t, fy, fq: calls.append("A") or None,
        "sec": lambda t, fy, sfx: calls.append("B") or {"start": "2025-06-29", "end": "2025-09-27"},
        "predict": lambda t, fy, fq: pytest.fail("must stop at SEC hit"),
        "corrected_fye": lambda t: pytest.fail("must stop at SEC hit"),
    }
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "duration"},
                  ticker="AAPL", lookups=lookups)
    assert calls == ["A", "B"]
    assert out["period_u_id"] == "gp_2025-06-29_2025-09-27"   # real filing dates win
    assert out["period_scope"] == "quarter"


def test_cascade_skipped_for_instants_and_nonstandard():
    poisoned = {"existing": lambda *a: pytest.fail("A must be skipped for instants"),
                "sec": lambda *a: pytest.fail("B must be skipped"),
                "predict": lambda *a: pytest.fail("C must be skipped"),
                "corrected_fye": lambda t: None}
    out = resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "time_type": "instant"},
                  ticker="AAPL", lookups=poisoned)
    assert out["period_u_id"] == "gp_2025-09-30_2025-09-30"


# ---- new-law fail-closed guards ----

def test_month_without_year_raises_no_year_2000():
    with pytest.raises(PeriodResolutionError):
        resolve({"month": 7, "time_type": "duration"})


def test_quiet_undef_fallthrough_forbidden():
    with pytest.raises(PeriodResolutionError):
        resolve({"half": 1, "time_type": "duration"})          # half without fiscal_year
    with pytest.raises(PeriodResolutionError):
        resolve({"fiscal_quarter": 3, "time_type": "duration"})  # quarter without year


def test_time_type_required_never_defaulted():
    with pytest.raises(PeriodResolutionError):
        resolve({"fiscal_year": 2025, "fiscal_quarter": 3})


def test_duration_with_equal_exact_dates_rejected():
    with pytest.raises(PeriodResolutionError):
        resolve({"period_start_date": "2025-09-27", "period_end_date": "2025-09-27",
                 "time_type": "duration"})


def test_instant_with_conflicting_exact_dates_rejected():
    with pytest.raises(PeriodResolutionError):
        resolve({"period_start_date": "2025-06-29", "period_end_date": "2025-09-27",
                 "time_type": "instant"})


def test_exact_dates_half_specified_rejected():
    with pytest.raises(PeriodResolutionError):
        resolve({"period_start_date": "2025-06-29", "time_type": "duration"})


def test_ytd_ttm_require_duration_and_fiscal_year():
    with pytest.raises(PeriodResolutionError):
        resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "ytd",
                 "time_type": "instant"})
    with pytest.raises(PeriodResolutionError):
        resolve({"period_scope": "ttm", "time_type": "duration"})


def test_bad_input_scope_rejected():
    with pytest.raises(PeriodResolutionError):
        resolve({"fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "quarter",
                 "time_type": "duration"})   # input scope may only be ytd/ttm


# ---- path convergence: same declared shape -> same scope on EVERY dated path ----
# (reproduced divergence: exact XBRL dates stamped exact_range while the SEC/math paths
#  said quarter for the IDENTICAL window -> the OD-21 surprise↔home scope match broke)

@pytest.mark.parametrize("fields,start,end,scope", [
    ({"fiscal_year": 2025, "fiscal_quarter": 4},              # 52/53-wk: dates ≠ month math
     "2025-06-29", "2025-09-27", "quarter"),
    ({"fiscal_year": 2025}, "2024-09-29", "2025-09-27", "annual"),   # 364d, 52-wk year
    ({"fiscal_year": 2025, "half": 2}, "2025-03-30", "2025-09-27", "half"),
    ({"fiscal_year": 2025, "month": 7}, "2025-07-01", "2025-07-31", "monthly"),
    ({"long_range_start_year": 2025, "long_range_end_year": 2030},
     "2025-01-01", "2030-12-31", "exact_range"),
    ({}, "2025-06-29", "2025-09-27", "exact_range"),          # no framing: stays honest
])
def test_exact_dates_scope_matches_declared_fields(fields, start, end, scope):
    out = resolve({"period_start_date": start, "period_end_date": end,
                   "time_type": "duration", **fields})
    assert out["period_u_id"] == f"gp_{start}_{end}"          # exact dates always win
    assert out["period_scope"] == scope


# ---- INTERIM GUARD (NOT P14 — dormant until materializer): contradictions PARK ----

def test_interim_guard_parks_contradictory_framing():
    # ChatGPT-audit case: fq declared on a six-month window — never label it quarter
    with pytest.raises(PeriodResolutionError, match="contradictory"):
        resolve({"period_start_date": "2025-01-01", "period_end_date": "2025-06-30",
                 "fiscal_year": 2025, "fiscal_quarter": 2, "time_type": "duration"})
    with pytest.raises(PeriodResolutionError, match="contradictory"):
        resolve({"period_start_date": "2025-01-01", "period_end_date": "2025-06-30",
                 "period_scope": "ttm", "time_type": "duration"})


def test_interim_guard_passes_real_52_53_week_windows():
    # 13-week (91d) and 14-week (98d) quarters both label quarter, no park
    for start, end in (("2025-06-29", "2025-09-27"), ("2024-09-29", "2025-01-04")):
        out = resolve({"period_start_date": start, "period_end_date": end,
                       "fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"})
        assert out["period_scope"] == "quarter"
    out = resolve({"period_start_date": "2023-12-31", "period_end_date": "2025-01-04",
                   "period_scope": "ttm", "time_type": "duration"})   # 371d, 53-wk year
    assert out["period_scope"] == "ttm"


def test_interim_guard_passes_irregular_quarter_filers():
    # KR 16-week Q1 = 112d; COST 12-week quarter = 84d; COST 53-week-year Q4 = 17 weeks
    # = 119d — all real quarters, never park
    for start, end in (("2025-02-02", "2025-05-24"), ("2025-02-17", "2025-05-11"),
                       ("2025-05-05", "2025-08-31")):
        out = resolve({"period_start_date": start, "period_end_date": end,
                       "fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"})
        assert out["period_scope"] == "quarter"


def test_interim_guard_passes_29_week_half():
    # 12-week + 17-week quarters (53-week year) = a real 203-day half — never park
    out = resolve({"period_start_date": "2025-02-10", "period_end_date": "2025-08-31",
                   "fiscal_year": 2025, "half": 2, "time_type": "duration"})
    assert out["period_scope"] == "half"


def test_interim_guard_passes_full_year_ytd():
    # Q4-YTD = the whole fiscal year (365d calendar / 371d 53-week) — legal ytd
    for start, end in (("2025-01-01", "2025-12-31"), ("2023-12-31", "2025-01-04")):
        out = resolve({"period_start_date": start, "period_end_date": end,
                       "fiscal_year": 2025, "fiscal_quarter": 4, "period_scope": "ytd",
                       "time_type": "duration"})
        assert out["period_scope"] == "ytd"


def test_conflicting_shape_fields_park_on_every_path():
    for extra in ({"month": 1}, {"half": 1}):
        with pytest.raises(PeriodResolutionError, match="conflicting"):
            resolve({"period_start_date": "2025-01-01", "period_end_date": "2025-03-31",
                     "fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration",
                     **extra})
    with pytest.raises(PeriodResolutionError, match="conflicting"):   # math path too
        resolve({"fiscal_year": 2025, "fiscal_quarter": 1, "month": 1,
                 "time_type": "duration"})


def test_out_of_range_shape_values_park():
    for bad in ({"fiscal_quarter": 5}, {"fiscal_quarter": 0}, {"half": 3},
                {"month": 13}, {"fiscal_quarter": True}):
        with pytest.raises(PeriodResolutionError, match="out of range"):
            resolve({"fiscal_year": 2025, "time_type": "duration", **bad})


def test_strict_shape_check_rejects_mixed_and_incomplete_framing():
    cases = [
        {"period_start_date": "2025-01-01", "period_end_date": "2025-06-30",
         "fiscal_year": 2025, "half": 1, "period_scope": "ytd"},       # cumulative+half
        {"fiscal_year": 2025, "month": 2, "period_scope": "ttm"},      # cumulative+month
        {"sentinel_class": "long_term", "fiscal_year": 2025},          # sentinel+fiscal
        {"sentinel_class": "short_term", "period_end_date": "2025-06-30"},  # sentinel+dated
        {"long_range_start_year": 2027},                               # incomplete range
        {"long_range_start_year": 2030, "long_range_end_year": 2027},  # reversed range
        {"fiscal_year": 205},                                          # invalid year
    ]
    for c in cases:
        with pytest.raises(PeriodResolutionError):
            resolve({**c, "time_type": "duration"})


def test_zero_values_are_validated_not_treated_as_absent():
    # fiscal_quarter=0 used to fall through `any()` truthiness as "no period fields"
    with pytest.raises(PeriodResolutionError, match="out of range"):
        resolve({"fiscal_quarter": 0, "time_type": "duration"})


def test_short_ytd_has_no_minimum_duration():
    out = resolve({"period_start_date": "2025-01-01", "period_end_date": "2025-01-31",
                   "fiscal_year": 2025, "period_scope": "ytd", "time_type": "duration"})
    assert out["period_scope"] == "ytd"          # January year-to-date is real data


def test_invalid_dates_park_cleanly_never_crash():
    with pytest.raises(PeriodResolutionError, match="invalid ISO date"):
        resolve({"period_start_date": "2025-01-01", "period_end_date": "2025-13-45",
                 "fiscal_year": 2025, "fiscal_quarter": 1, "time_type": "duration"})
    with pytest.raises(PeriodResolutionError, match="invalid ISO date"):
        resolve({"period_start_date": "2025-02-30", "period_end_date": "2025-06-30",
                 "time_type": "duration"})                     # Feb 30 doesn't exist
    with pytest.raises(PeriodResolutionError):                 # reversed order parks too
        resolve({"period_start_date": "2025-09-27", "period_end_date": "2025-06-29",
                 "time_type": "duration"})


def test_same_window_same_scope_across_xbrl_and_sec_paths():
    lk = {"existing": lambda *a: None,
          "sec": lambda t, fy, fp: {"start": "2025-06-29", "end": "2025-09-27"},
          "predict": lambda *a: None, "corrected_fye": lambda t: None}
    via_dates = resolve({"period_start_date": "2025-06-29", "period_end_date": "2025-09-27",
                         "fiscal_year": 2025, "fiscal_quarter": 4, "time_type": "duration"},
                        fye=9, ticker="AAPL", lookups=lk)
    via_sec = resolve({"fiscal_year": 2025, "fiscal_quarter": 4, "time_type": "duration"},
                      fye=9, ticker="AAPL", lookups=lk)
    assert via_dates == via_sec              # one real fact -> one id AND one scope


def test_exact_date_instant_scope_matches_pure_math_label():
    out = resolve({"period_end_date": "2025-09-27", "fiscal_year": 2025,
                   "fiscal_quarter": 4, "time_type": "instant"})
    assert out["period_u_id"] == "gp_2025-09-27_2025-09-27"
    assert out["period_scope"] == "quarter"  # pure-math instant quarter says "quarter" too


def test_exact_dates_ytd_ttm_scope_still_preserved():
    out = resolve({"period_start_date": "2024-09-29", "period_end_date": "2025-06-28",
                   "fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "ytd",
                   "time_type": "duration"})                   # 273d Q3-YTD
    assert out["period_scope"] == "ytd"      # cumulative label beats the quarter fields
    out = resolve({"period_start_date": "2024-06-30", "period_end_date": "2025-06-28",
                   "fiscal_year": 2025, "fiscal_quarter": 3, "period_scope": "ttm",
                   "time_type": "duration"})                   # 364d trailing window
    assert out["period_scope"] == "ttm"


def test_pure_lane_never_imports_the_heavy_substrate():
    # dry-run purity: a ticker-less resolution must not import guidance_write_cli
    # (whose import chain pulls the writer + graph libraries)
    import subprocess, sys
    code = (
        "import sys; from driver.core.driver_period_resolver import ensure_driver_period; "
        "out = ensure_driver_period({'fiscal_year': 2025, 'fiscal_quarter': 1, "
        "'time_type': 'duration'}, fact_type='metric', fye_month=12); "
        "assert out['period_u_id'] == 'gp_2025-01-01_2025-03-31'; "
        "assert 'guidance_write_cli' not in sys.modules, 'heavy import leaked'"
    )
    subprocess.run([sys.executable, "-c", code], check=True,
                   cwd=str(__import__("pathlib").Path(__file__).resolve().parents[2]))
