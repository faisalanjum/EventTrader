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
    assert out["period_scope"] == "exact_range"


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
