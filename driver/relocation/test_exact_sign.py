"""Exact sign application: source value, reconciliation, and full binding."""
import decimal
from decimal import Decimal, localcontext

import pytest

from driver.relocation.inline_html import printed_value, reconcile
from driver.relocation.test_bind_graph_fact import _bind, _doc, _NUM_DOT_DECIMAL

ROUNDINGS = [getattr(decimal, name) for name in dir(decimal)
             if name.startswith("ROUND_")]
VALUES = ("1", "98", "1234567.890123456789012345678901",
          "10000000000000000000000000001", "9" * 80,
          "0." + "0" * 79 + "1", "0", "0.000")


@pytest.mark.parametrize("precision", [1, 6, 28, 50])
@pytest.mark.parametrize("rounding", ROUNDINGS)
@pytest.mark.parametrize("formatted", [False, True])
def test_signed_value_preserves_every_digit_without_using_decimal_context(
        precision, rounding, formatted):
    fmt = _NUM_DOT_DECIMAL if formatted else None
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = precision, rounding
        ctx.Emin, ctx.Emax = -9, 9
        for signal in (decimal.Inexact, decimal.Rounded, decimal.Overflow,
                       decimal.Underflow, decimal.Subnormal):
            ctx.traps[signal] = True
        ctx.clear_flags()
        before = ctx.copy()
        for text in VALUES:
            for sign in (None, "", "-"):
                # Independent expectation: exact string construction, no negation.
                expected = Decimal(("-" if sign == "-" else "") + text)
                actual = printed_value(text, fmt, sign)
                assert actual == expected
                if expected:
                    assert actual.as_tuple() == expected.as_tuple()
        assert ctx.flags == before.flags
        assert ctx.traps == before.traps
        assert (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax) == (
            before.prec, before.rounding, before.Emin, before.Emax)


@pytest.mark.parametrize("precision", [6, 28, 50])
@pytest.mark.parametrize("sign", ["", "-"])
@pytest.mark.parametrize("scale", [0, 6])
def test_exact_signed_value_and_one_digit_distractor_through_full_binding(
        precision, sign, scale):
    for digits in (1, 6, 7, 28, 29, 50, 80):
        coefficient = 10 ** (digits - 1) + 1
        signed = -coefficient if sign else coefficient  # Python integers are exact.
        raw = format(signed * 10 ** scale, ",")
        wrong = format((signed - 1 if sign else signed + 1) * 10 ** scale, ",")
        doc = _doc(shown=str(coefficient), sign=sign, scale=str(scale))
        with localcontext() as ctx:
            ctx.prec = precision
            bound, why = _bind(doc, raw_value=raw)
            assert bound is not None, why
            assert bound["printed_value"] == Decimal(signed)
            assert _bind(doc, raw_value=wrong) == (None, "value_does_not_reconcile")


@pytest.mark.parametrize("sign", ["", "-"])
def test_reconciliation_catches_the_original_rounding_collision(sign):
    shown = "10000000000000000000000000001"
    exact = sign + "10,000,000,000,000,000,000,000,000,001,000,000"
    rounded = sign + "10,000,000,000,000,000,000,000,000,000,000,000"
    with localcontext() as ctx:
        ctx.prec = 28
        assert reconcile(shown, _NUM_DOT_DECIMAL, 6, sign, exact)
        assert not reconcile(shown, _NUM_DOT_DECIMAL, 6, sign, rounded)


def test_signed_zero_is_numerically_zero_and_invalid_signs_still_refuse():
    for text in ("0", "+0", "-0", "0.000"):
        for sign in (None, "", "-"):
            assert printed_value(text, None, sign) == Decimal(0)
    for fmt in (None, _NUM_DOT_DECIMAL):
        assert printed_value("98", fmt, "-") == Decimal("-98")
        for sign in ("+", " - ", "x", 0, False):
            assert printed_value("98", fmt, sign) is None


def test_no_format_invalid_numbers_and_fixed_zero_keep_their_rules():
    fixed_zero = (_NUM_DOT_DECIMAL[0], "fixed-zero")
    for sign in (None, "", "-"):
        assert printed_value("123.45", None, sign) is not None
        for text in ("", "-1", "NaN", "Infinity", "1e3", "1_000"):
            assert printed_value(text, None, sign) is None
        assert printed_value("anything", fixed_zero, sign) == Decimal(0)
    assert printed_value("anything", fixed_zero, " - ") is None


def test_locator_emits_exact_negative_and_refuses_rounded_graph_value():
    from driver.relocation.test_route_a import ANCHOR, LOC, ROW_390, doc, fact, src

    n = 10000000000000000000000000001
    html = doc(ROW_390.replace(">390<", ">" + str(n) + "<").replace(
        'scale="6"', 'scale="6" sign="-"'))
    with localcontext() as ctx:
        ctx.prec = 28
        result = LOC.locate(ANCHOR, src([fact(format(-n * 10**6, ","))], html))
        assert len(result["items"]) == 1
        assert result["items"][0]["value"] == Decimal(-n)
        wrong = format(-(n - 1) * 10**6, ",")
        assert LOC.locate(ANCHOR, src([fact(wrong)], html))["items"] == []
