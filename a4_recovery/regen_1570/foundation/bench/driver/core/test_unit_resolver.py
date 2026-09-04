"""
test_unit_resolver.py — tests for the SHARED unit_resolver.

Asserts BOTH the canonical_unit AND the scaled_value (unit-only checks are blind
to the cents-crash and the glued-$B x1000 drop — ChatGPT #4). Also covers:
 - per-X prices resolve to 'usd' when the name carries the denominator (ChatGPT #1)
 - the denominator LINT warns (does NOT auto-convert to 'unknown')
 - cents-on-aggregate is SURFACED as an error (not silently None — ChatGPT #5)
 - glued '$B' is normalized so the value scales correctly
 - PARITY: for clean tokens, resolve_unit == production build_guidance_ids(v2)

Run:  /usr/bin/python3 test_unit_resolver.py   (also pytest-discoverable)
"""
import math
import sys

from driver.core.unit_resolver import resolve_unit, resolve_driverupdate_units, real_source
import guidance_ids as _gid


def _close(a, b):
    if a is None or b is None:
        return a is b
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)


# (driver_name, unit_raw, value, kwargs, expected_unit, expected_value)
CASES = [
    # ── guidance (home turf) ──
    ("revenue", "million", 1130, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 1130.0),
    ("revenue", "B", 1.5, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 1500.0),
    ("eps", "$", 1.10, dict(unit_kind_hint="money", money_mode_hint="price_like"), "usd", 1.10),
    ("eps", "$", 1.10, {}, "usd", 1.10),  # name 'eps' -> price_like via label, no hint
    ("operating_margin", "%", 45, dict(unit_kind_hint="ratio"), "percent", 45.0),
    ("revenue_growth", "% yoy", 12, dict(unit_kind_hint="ratio"), "percent_yoy", 12.0),
    ("capex", "billion", 2.0, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 2000.0),
    # ── surprise ──
    ("eps_surprise", "$", 0.05, dict(unit_kind_hint="money", money_mode_hint="price_like"), "usd", 0.05),
    ("revenue_surprise", "million", 50, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 50.0),
    ("margin_surprise", "bps", 120, dict(unit_kind_hint="ratio"), "basis_points", 120.0),
    # ── metric ──
    ("same_store_sales", "%", 3, dict(unit_kind_hint="ratio"), "percent", 3.0),
    ("occupancy_rate", "%", 92, dict(unit_kind_hint="ratio"), "percent", 92.0),
    ("headcount", "", 50000, dict(unit_kind_hint="count"), "count", 50000.0),
    ("store_count", "stores", 1500, dict(unit_kind_hint="count"), "count", 1500.0),
    ("net_leverage", "x", 2.5, dict(unit_kind_hint="multiplier"), "x", 2.5),
    ("margin_expansion", "pp", 2, dict(unit_kind_hint="ratio"), "percent_points", 2.0),
    # ── action_event ──
    ("dividend_per_share", "$", 0.50, {}, "usd", 0.50),  # name per_share -> usd, no hint
    ("dividend", "$", 0.50, dict(unit_kind_hint="money", money_mode_hint="price_like"), "usd", 0.50),
    ("share_repurchase", "billion", 2.0, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 2000.0),
    ("asset_impairment", "billion", 1.2, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 1200.0),
    ("workforce_reduction", "employees", 5000, dict(unit_kind_hint="count"), "count", 5000.0),
    # ── ChatGPT #1: per-X price, denominator IN the name -> usd (no hint) ──
    ("fuel_cost_per_barrel", "$/barrel", 80, {}, "usd", 80.0),
    ("sales_per_square_foot", "$/sq ft", 450, {}, "usd", 450.0),
    ("revenue_per_available_room", "$ per room", 95, {}, "usd", 95.0),
    # per-X with name lacking denominator, rescued by hint -> usd
    ("oil_price", "$/barrel", 80, dict(money_mode_hint="price_like"), "usd", 80.0),
    # renamed per-X happy path: NAME carries the denominator -> usd with NO hint
    ("oil_price_per_barrel", "$/barrel", 80, {}, "usd", 80.0),
    ("steel_cost_per_ton", "$/ton", 700, {}, "usd", 700.0),
    # corpus glued-$B value traps: must scale x1000 (not silently drop it)
    ("asset_impairment", "$B", 1.2, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 1200.0),
    ("senior_notes_offering", "$B", 1, dict(unit_kind_hint="money", money_mode_hint="aggregate"), "m_usd", 1000.0),
]


def run_cases():
    fails = []
    for name, uraw, val, kw, exp_u, exp_v in CASES:
        r = resolve_unit(name, uraw, val, **kw)
        if r.canonical_unit != exp_u or not _close(r.scaled_value, exp_v):
            fails.append(f"{name} {uraw!r} {kw}: got unit={r.canonical_unit} value={r.scaled_value} "
                         f"(want unit={exp_u} value={exp_v}) warn={r.warnings} err={r.error}")
    return fails


def check_glued_dollar_fix():
    """'$B' must scale to 1500 (not silently 1.5) AND emit a normalization warning."""
    r = resolve_unit("revenue", "$B", 1.5, unit_kind_hint="money", money_mode_hint="aggregate")
    assert r.canonical_unit == "m_usd", r
    assert _close(r.scaled_value, 1500.0), f"glued $B value not fixed: {r.scaled_value}"
    assert any("normalized" in w for w in r.warnings), "expected a normalization warning"


def check_cents_surfaced():
    """cents on aggregate money must SURFACE an error, not return a silent None."""
    r = resolve_unit("revenue", "cents", 50.0, unit_kind_hint="money", money_mode_hint="aggregate")
    assert r.error is not None and "cents" in r.error, f"cents error not surfaced: {r}"
    assert r.scaled_value is None
    raised = False
    try:
        resolve_unit("revenue", "cents", 50.0, unit_kind_hint="money",
                     money_mode_hint="aggregate", strict=True)
    except ValueError:
        raised = True
    assert raised, "strict=True must re-raise the cents error"


def check_denominator_lint():
    """per-X with neither name nor hint carrying the denominator -> WARN (not 'unknown')."""
    r = resolve_unit("oil_price", "$/barrel", 80)  # no hint, name lacks 'per'
    assert r.canonical_unit != "unknown", "must NOT auto-convert to unknown (ChatGPT #1)"
    assert r.canonical_unit == "m_usd", f"expected aggregate fallback, got {r.canonical_unit}"
    assert any("per-unit price" in w for w in r.warnings), f"expected denominator lint, got {r.warnings}"


def check_lint_hint_blind():
    """The naming lint must fire on USD per-X even WITH a price_like hint (hint-blind).

    A price_like hint fixes the unit (-> usd) but NOT the name collision in the
    series key, so the hint must not be able to mute the rename warning.
    """
    from driver.core.unit_resolver import lint_per_x_naming
    # standalone, no value/hints at all
    assert lint_per_x_naming("oil_price", "$/barrel"), "should flag USD per-X with no _per_ in name"
    assert lint_per_x_naming("oil_price", "$ per ton"), "should flag ' per ' form too"
    assert lint_per_x_naming("oil_price", "usd per unit"), "should flag the 'usd per' word form"
    assert lint_per_x_naming("oil_price_per_barrel", "$/barrel") is None, "good name -> no flag"
    assert lint_per_x_naming("revenue", "$B") is None, "no per-denominator -> no flag"
    assert lint_per_x_naming("eps", "$") is None, "bare $ -> no flag"
    # non-money 'per' surfaces must NOT be flagged (scope = USD money per-X only)
    assert lint_per_x_naming("growth_rate", "% per year") is None, "ratio per-X -> no flag"
    assert lint_per_x_naming("widgets", "units per store") is None, "count per-X -> no flag"
    assert lint_per_x_naming("oil_price", "€/barrel") is None, "non-USD per-X -> no flag (already unknown)"
    # the ChatGPT #3 regression: a price_like hint must NOT suppress the warning
    r = resolve_unit("oil_price", "$/barrel", 80, money_mode_hint="price_like")
    assert r.canonical_unit == "usd", f"hint should still fix the unit, got {r.canonical_unit}"
    assert any("per-unit price" in w for w in r.warnings), \
        f"price_like hint must NOT mute the naming lint, got warnings={r.warnings}"


def check_range_value_not_scaled():
    """A range value ('94-97') must fail loudly (warn + scaled None), never silently scale."""
    r = resolve_unit("revenue", "$ B", "94-97", unit_kind_hint="money", money_mode_hint="aggregate")
    assert r.canonical_unit == "m_usd", r
    assert r.scaled_value is None, f"range must not scale to a number, got {r.scaled_value}"
    assert any("range" in w.lower() for w in r.warnings), f"expected a range warning, got {r.warnings}"


def check_separate_level_change():
    """DriverUpdate calls resolver separately for level_* and change_*."""
    out = resolve_driverupdate_units(
        "revenue", level_value=1.5, level_unit_raw="B",
        change_value=12, change_unit_raw="% yoy",
        unit_kind_hint=None, money_mode_hint=None)
    # level needs a money hint to be aggregate; without it 'revenue' has no money surface on 'B'
    lvl = resolve_unit("revenue", "B", 1.5, unit_kind_hint="money", money_mode_hint="aggregate")
    assert _close(lvl.scaled_value, 1500.0)
    assert out["change"].canonical_unit == "percent_yoy" and _close(out["change"].scaled_value, 12.0)


def check_parity_with_production():
    """For CLEAN tokens, resolve_unit must equal production build_guidance_ids(v2)."""
    parity = [
        ("revenue", "million", 1130.0, "money", "aggregate"),
        ("eps", "$", 1.10, "money", "price_like"),
        ("operating_margin", "%", 45.0, "ratio", None),
        ("dividend_per_share", "$", 0.50, None, None),
    ]
    for name, uraw, val, kh, mmh in parity:
        prod = _gid.build_guidance_ids(
            label=name, source_id="SRC", period_u_id="FY2025", basis_norm="unknown",
            low=val, unit_raw=uraw, unit_kind_hint=kh, money_mode_hint=mmh,
            resolution_mode="v2")
        r = resolve_unit(name, uraw, val, unit_kind_hint=kh, money_mode_hint=mmh)
        assert r.canonical_unit == prod["canonical_unit"], \
            f"parity unit mismatch {name}: {r.canonical_unit} vs {prod['canonical_unit']}"
        assert _close(r.scaled_value, prod["canonical_low"]), \
            f"parity value mismatch {name}: {r.scaled_value} vs {prod['canonical_low']}"


# pytest entry points
def test_cases():
    assert run_cases() == []


def test_glued_dollar_fix():
    check_glued_dollar_fix()


def test_cents_surfaced():
    check_cents_surfaced()


def test_denominator_lint():
    check_denominator_lint()


def test_lint_hint_blind():
    check_lint_hint_blind()


def test_range_value_not_scaled():
    check_range_value_not_scaled()


def test_separate_level_change():
    check_separate_level_change()


def test_parity_with_production():
    check_parity_with_production()


if __name__ == "__main__":
    print("=== provenance ===")
    src = real_source()
    print(f"  imports: {src['guidance_ids_file']}")
    print(f"  sha256:  {src['guidance_ids_sha256']}")
    print(f"  reimplemented: {src['reimplemented']}")
    print()
    failed = 0
    case_fails = run_cases()
    print(f"[cases]            {len(CASES) - len(case_fails)}/{len(CASES)} passed (unit AND value)")
    for f in case_fails:
        print("   FAIL:", f); failed += 1
    for fn in (check_glued_dollar_fix, check_cents_surfaced, check_denominator_lint,
               check_lint_hint_blind, check_range_value_not_scaled,
               check_separate_level_change, check_parity_with_production):
        try:
            fn()
            print(f"[{fn.__name__}] PASS")
        except AssertionError as e:
            print(f"[{fn.__name__}] FAIL: {e}"); failed += 1
    print()
    if failed:
        print(f"RESULT: {failed} failure(s)")
        sys.exit(1)
    print("RESULT: ALL PASS")
