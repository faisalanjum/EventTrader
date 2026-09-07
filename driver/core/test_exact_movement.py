"""Guidance midpoint law, with expectations from exact integer arithmetic."""
import copy
import decimal
import random
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import product

import pytest

from driver.core.driver_validators import NUMERIC_FIELDS
from driver.core.test_driver_validators import check, mk

STATES = ("raised", "lowered", "reaffirmed")
ROUNDINGS = [getattr(decimal, name) for name in dir(decimal)
             if name.startswith("ROUND_")]
CASES = (
    (101, 101, 100, 100), (100, 100, 100, 100), (99, 99, 100, 100),
    (99, 99, 98, 98),
    (9007199254740993, 9007199254740993, 9007199254740992, 9007199254740992),
    (2**63 - 1, 2**63 - 1, 2**63 - 2, 2**63 - 2),
    (-2**63 + 1, -2**63 + 1, -2**63, -2**63),
    (-99, -99, -100, -100), (-1, 1, 0, 0), (0, 0, -1, 1),
    (90, 130, 100, 110), (90, 120, 100, 110), (90, 119, 100, 110),
    (10**80, 10**80 + 1, 10**80, 10**80),
    (-10**80, 10**80 + 1, -10**80, 10**80),
)


def _fact(values, state):
    lo, hi, clo, chi = values
    return mk("guidance", "point", driver_state=state,
              level_low=lo, level_high=hi,
              comparison_low=clo, comparison_high=chi,
              level_shape_hint="point" if lo == hi else "range",
              comparison_shape_hint="point" if clo == chi else "range",
              comparison_baseline="previous_guidance")


def _assert_states(values, expected):
    for state in STATES:
        fact = _fact(values, state)
        before = copy.deepcopy(fact)
        result = check(fact)
        assert [v.code for v in result] == ([] if state == expected else ["MOVEMENT"])
        assert fact == before


@pytest.mark.parametrize("precision", [1, 6, 28, 50])
@pytest.mark.parametrize("rounding", ROUNDINGS)
def test_movement_all_integer_decimal_combinations_and_contexts(precision, rounding):
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = precision, rounding
        ctx.Emin, ctx.Emax = -9, 9
        for signal in (decimal.Inexact, decimal.Rounded, decimal.Overflow,
                       decimal.Underflow, decimal.Subnormal, decimal.FloatOperation):
            ctx.traps[signal] = True
        ctx.clear_flags()
        before = ctx.copy()
        for coefficients in CASES:
            lo, hi, clo, chi = coefficients
            delta = lo + hi - clo - chi  # Independent integer oracle; no midpoint division.
            expected = "raised" if delta > 0 else "lowered" if delta < 0 else "reaffirmed"
            for decimal_mask in product((False, True), repeat=4):
                values = [Decimal(n) if use_decimal else n
                          for n, use_decimal in zip(coefficients, decimal_mask)]
                _assert_states(values, expected)
        assert ctx.flags == before.flags
        assert ctx.traps == before.traps
        assert (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax) == (
            before.prec, before.rounding, before.Emin, before.Emax)


@pytest.mark.parametrize("exponent", [-4093, -50, -9, 0, 50, 4094])
def test_fractional_and_large_values_and_reversing_the_comparison(exponent):
    # A common positive power of ten cannot change the ordering of the sums.
    with localcontext() as ctx:
        ctx.prec = 6
        for coefficients in ((101, 109, 100, 108), (100, 110, 101, 109),
                             (-101, 101, -100, 101)):
            for swapped in (False, True):
                ns = coefficients[2:] + coefficients[:2] if swapped else coefficients
                delta = ns[0] + ns[1] - ns[2] - ns[3]
                expected = "raised" if delta > 0 else "lowered" if delta < 0 else "reaffirmed"
                _assert_states([Decimal(f"{n}e{exponent}") for n in ns], expected)


@pytest.mark.parametrize("field", NUMERIC_FIELDS)
@pytest.mark.parametrize("bad", [True, 1.0, "1", Decimal("NaN"),
                                Decimal("sNaN"), Decimal("Infinity"),
                                Decimal("-Infinity")])
def test_bad_numbers_still_reject_before_movement(field, bad):
    fact = _fact((101, 101, 100, 100), "raised")
    assert check(fact) == []
    fact[field] = bad
    assert {v.code for v in check(fact)} == {"MALFORMED"}


@pytest.mark.parametrize("missing", ["level_low", "level_high",
                                    "comparison_low", "comparison_high"])
def test_open_shapes_do_not_invent_a_midpoint(missing):
    fact = _fact((101, 101, 100, 100), "reaffirmed")
    assert [v.code for v in check(fact)] == ["MOVEMENT"]
    fact[missing] = None
    prefix = missing.rsplit("_", 1)[0]
    fact[prefix + "_shape_hint"] = "ceiling" if missing.endswith("low") else "floor"
    assert "MOVEMENT" not in [v.code for v in check(fact)]


def test_unstated_movement_is_not_inferred_and_reversed_ranges_still_reject():
    fact = _fact((101, 101, 100, 100), "reaffirmed")
    assert [v.code for v in check(fact)] == ["MOVEMENT"]
    fact["driver_state"] = "unknown"
    assert check(fact) == []
    fact = _fact((110, 100, 99, 99), "raised")
    assert "SHAPE" in [v.code for v in check(fact)]


def test_compact_large_decimals_do_not_need_integer_string_conversion():
    _assert_states([Decimal("2e5000"), Decimal("2e5000"),
                    Decimal("1e5000"), Decimal("1e5000")], "raised")
    _assert_states([Decimal("-0e-5000"), Decimal("0e5000"),
                    Decimal("0"), Decimal("-0")], "reaffirmed")
    with localcontext() as ctx:
        ctx.traps[decimal.Rounded] = True
        _assert_states([Decimal("0e-5000"), Decimal("1"),
                        Decimal("0"), Decimal("1")], "reaffirmed")


def test_unequal_decimal_exponents_against_an_independent_rational_oracle():
    rng = random.Random(20260907)
    cases = [[Decimal("1e80"), Decimal("0.01"), Decimal("1e80"), Decimal("0")]]
    for _ in range(1000):
        cases.append([Decimal(f"{rng.randrange(-10**40, 10**40)}e{rng.randrange(-80, 81)}")
                      for _ in range(4)])
    for i, values in enumerate(cases):
        values = sorted(values[:2]) + sorted(values[2:])
        delta = sum(map(Fraction, values[:2])) - sum(map(Fraction, values[2:]))
        expected = "raised" if delta > 0 else "lowered" if delta < 0 else "reaffirmed"
        with localcontext() as ctx:
            ctx.prec = 1 + i % 50
            ctx.rounding = ROUNDINGS[i % len(ROUNDINGS)]
            ctx.clamp = i % 2
            ctx.traps[decimal.Inexact] = True
            ctx.traps[decimal.Rounded] = True
            _assert_states(values, expected)


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("precision", [6, 28])
def test_guidance_movement_through_both_event_routes(tmp_path, version, precision):
    from driver.core.driver_write_cli import run_event
    from driver.core.test_driver_write_cli import FakeStore, fact, run
    from driver.core.test_v2_attacks import slot
    from driver.core.test_v2_event_route import _reply, _text_event, _text_fact

    drivers = {"revenue_guidance": {"name": "revenue_guidance", "fact_type": "guidance"}}
    current, previous = 9007199254740993, 9007199254740992
    with localcontext() as ctx:
        ctx.prec = precision
        for state in ("raised", "reaffirmed"):
            common = dict(driver_name="revenue_guidance", driver_state=state,
                          comparison_baseline="previous_guidance",
                          comparison_shape_hint="point")
            path = tmp_path / state
            if version == 1:
                store = FakeStore(drivers=drivers)
                inp = fact(**common, level_low=current, level_high=current,
                           level_unit_raw="count", comparison_low=previous,
                           comparison_high=previous, company_confirmed=True)
                result = run(path, [inp], store)
            else:
                event = _text_event("ev-exact", [
                    "Revenue guidance raised to 9007199254740993 from 9007199254740992."])
                store = FakeStore(drivers=drivers, companies=["X"], source={
                    "date": event["event_time"], "source_type": "8k",
                    "ticker": "X", "fye_month": 12})
                inp = _text_fact(event, event["items"][0], **common,
                                 fact_type="guidance", level_unit="count",
                                 level_shape_hint="point", company_confirmed=True,
                                 time_type="duration",
                                 fiscal_year=2026, period_start_date="2026-01-01",
                                 period_end_date="2026-12-31",
                                 level_low=slot(current), level_high=slot(current),
                                 comparison_low=slot(previous), comparison_high=slot(previous))
                result = run_event(event, store=store, audit_dir=str(path),
                                   reader=lambda **kw: _reply("ev-exact", [inp]),
                                   enable_writes=False)
            row, = result["items"]
            assert result["status"] == "dry_run"
            assert row["decision"] == ("written" if state == "raised" else "rejected"), row
            assert row["codes"] == ([] if state == "raised" else ["MOVEMENT"])
            assert store.applied == []
