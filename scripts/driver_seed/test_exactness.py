"""WP1 Step-1 RED battery — exactness defects pinned at their source (link_lib / xbrl_lane).

Every RED case reproduces a defect verified during the v5.5 design reviews; GREEN guards pin
behavior that must survive the fixes. Shapes mirror REAL graph storage (checked live 2026-07-18):
concept keys are BARE local names; units are filer-local `unitRef` codes (e.g. 'U_USD');
instants are {'instant': date}; values are strings.

    venv/bin/python -m pytest scripts/driver_seed/test_exactness.py -q
"""
import os, sys, json
import pytest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
import link_lib as L
import xbrl_lane


def blob(concept, facts):
    return json.dumps({concept: facts})


def fact(value, start=None, end=None, instant=None, unit='U_USD', seg=None):
    p = {'instant': instant} if instant else {'startDate': start, 'endDate': end}
    fc = {'value': value, 'period': p, 'unitRef': unit}
    if seg:
        fc['segment'] = seg
    return fc


# ---------------- tier1: Decimal-exact value matching (RED: int-truncation conflates) ----------
# fixtures use a concept that legally passes concept_ok/concept_type_ok ('Revenues' + a 'total
# revenue' name) so the tests isolate EXACTLY the value-comparison logic (tier1 L353/L373).
def test_tier1_decimal_never_matches_a_different_decimal():
    """2.34 must NOT bind a 2.01 fact. Today tier1 truncates both to '2' and matches."""
    b = blob('Revenues', [fact('2.01', '2024-01-01', '2024-12-31')])
    r = L.tier1([b], 'total revenue', 2.34, '2024-12-31')
    assert r is None, f"2.34 bound a 2.01 fact: {r}"


def test_tier1_exact_decimal_still_matches_itself():
    b = blob('Revenues', [fact('2.34', '2024-01-01', '2024-12-31')])
    r = L.tier1([b], 'total revenue', 2.34, '2024-12-31')
    assert r is not None, "exact decimal failed to match itself"


# ---------------- value_ok: % class guard + fractional rounding (RED: both reproduced) ----------
def test_value_ok_number_never_accepts_percent_token():
    assert not L.value_ok(86, 'number', 'utilization was 86% in Q4'), \
        "a plain number bound a %-marked token"


def test_value_ok_number_still_accepts_plain_token():
    assert L.value_ok(86, 'number', 'International Stores 86 at fiscal year end')


def test_value_ok_fractional_never_accepts_integer_rounded_print():
    assert not L.value_ok(2.34, '%', 'gross margin was 2% for the year'), \
        "2.34 accepted the integer-rounded print '2%'"


def test_value_ok_fractional_accepts_one_decimal_and_exact():
    assert L.value_ok(2.34, '%', 'gross margin was 2.3% for the year')
    assert L.value_ok(2.34, '%', 'gross margin was 2.34% for the year')


def test_value_ok_integral_percent_keeps_bare_form():
    assert L.value_ok(2.0, '%', 'gross margin was 2% for the year')


# ---------------- negatives / parentheses: GREEN guards (must survive the fixes) ---------------
def test_sign_guards_survive():
    assert not L.value_ok(123, 'number', 'operating income (123)')     # positive vs printed-negative
    assert L.value_ok(-123, 'number', 'operating income (123)')
    assert L.value_ok(-123, 'number', 'operating income -123')


# ---------------- substring invariant: emitted quotes are RAW source slices (RED: _tidy) -------
def test_row_quote_is_exact_substring_of_source():
    t = 'Segment results\nInternational Stores\n  86   at fiscal year end'
    q = L.row_quote([t], ['International', 'Stores'], 86, 'number')
    assert q is not None
    assert q in t, f"emitted quote is not a raw slice of the source: {q!r}"


def test_scan_text_snips_are_exact_substrings_of_source():
    t = 'Overview\nTotal   revenue was\n $ 6,707 for the year ended December 31, 2024.'
    strict, snips = L.scan_text([t], 'total revenue', 6707, 'number')
    for s in snips:
        assert s in t, f"snippet is not a raw slice of the source: {s!r}"
    if strict is not None:
        assert strict in t, f"strict quote is not a raw slice: {strict!r}"


# ---------------- xbrl_lane: Decimal-exact · instant · exact dates · unit conflicts ------------
def test_resolve_returns_exact_decimal_not_rounded():
    b = blob('Revenues', [fact('2.34', '2024-01-01', '2024-12-31')])
    got = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31')
    assert got == Decimal('2.34'), f"decimal destroyed: {got!r}"


def test_resolve_instant_fact_via_gp_date_date():
    b = blob('CashAndCashEquivalentsAtCarryingValue', [fact('1138000000', instant='2024-12-31')])
    got = xbrl_lane.resolve([b], 'us-gaap:CashAndCashEquivalentsAtCarryingValue', [],
                            '2024-12-31', '2024-12-31')
    assert got == Decimal('1138000000'), f"instant fact not resolved: {got!r}"


def test_resolve_rejects_mixed_convention_dates():
    """inclusive start + exclusive-style end must NOT match an inclusive request (reproduced)."""
    b = blob('Revenues', [fact('5000', '2024-01-01', '2025-01-01')])
    got = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31')
    assert got is None, f"mixed-convention fact accepted: {got!r}"


def test_resolve_rejects_neighboring_period_end():
    """a fact ending one day later is a DIFFERENT period — no ±1-day tolerance."""
    b = blob('Revenues', [fact('5000', '2024-01-01', '2025-01-01')])
    got = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2025-01-01')
    assert got == Decimal('5000')                      # exact same dates still match…
    got2 = xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-02', '2025-01-01')
    assert got2 is None, "start off by one day matched"


def test_resolve_concept_local_name_exact_only():
    """storage is BARE local names (verified live): request prefixes strip deterministically;
    a DIFFERENT local name never matches (green guard on exactness)."""
    b = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31')])
    assert xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31') is not None
    assert xbrl_lane.resolve([b], 'us-gaap:OtherRevenues', [], '2024-01-01', '2024-12-31') is None


def test_resolve_rejects_wrong_prefix_when_stored_prefixed():
    """Round-12: evil:Revenues must NOT satisfy us-gaap:Revenues. Storage is normally BARE
    (verified live) and a bare key still matches by local name; but when the stored key CARRIES a
    prefix, it must match the requested prefix exactly."""
    b = blob('evil:Revenues', [fact('5000', '2024-01-01', '2024-12-31')])
    assert xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31') is None
    g = blob('us-gaap:Revenues', [fact('5000', '2024-01-01', '2024-12-31')])
    assert xbrl_lane.resolve([g], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31') == Decimal('5000')


def test_resolve_expected_unit_class():
    """Round-12: shares must never satisfy a money request (and vice versa)."""
    b = blob('SomeThing', [fact('100', '2024-01-01', '2024-12-31', unit='U_shares')])
    assert xbrl_lane.resolve([b], 'SomeThing', [], '2024-01-01', '2024-12-31',
                             expected_unit='money') is None
    m = blob('SomeThing', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert xbrl_lane.resolve([m], 'SomeThing', [], '2024-01-01', '2024-12-31',
                             expected_unit='money') == Decimal('100')
    assert xbrl_lane.resolve([m], 'SomeThing', [], '2024-01-01', '2024-12-31',
                             expected_unit='nonmoney') is None


def test_tier1_unit_class_guard():
    """Round-12: a currency KPI (is_currency=1) must not bind a shares-tagged fact."""
    sh = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_shares')])
    assert L.tier1([sh], 'total revenue', 5000, '2024-12-31', is_currency=1) is None
    us = blob('Revenues', [fact('5000', '2024-01-01', '2024-12-31', unit='U_USD')])
    assert L.tier1([us], 'total revenue', 5000, '2024-12-31', is_currency=1) is not None


def test_resolve_unit_conflict_abstains():
    """same identity+value under TWO different unitRefs = ambiguous → abstain (RED: no unit logic)."""
    b = blob('SomeCount', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD'),
                           fact('100', '2024-01-01', '2024-12-31', unit='U_shares')])
    got = xbrl_lane.resolve([b], 'SomeCount', [], '2024-01-01', '2024-12-31')
    assert got is None, f"unitRef conflict silently resolved: {got!r}"


def test_resolve_unit_filter_when_caller_supplies_it():
    b = blob('SomeCount', [fact('100', '2024-01-01', '2024-12-31', unit='U_USD'),
                           fact('200', '2024-01-01', '2024-12-31', unit='U_shares')])
    got = xbrl_lane.resolve([b], 'SomeCount', [], '2024-01-01', '2024-12-31', unit_ref='U_shares')
    assert got == Decimal('200'), f"unit filter missing: {got!r}"


# ---------------- zero: labeled findable, generic abstains (full-locator level exists too) -----
def test_value_forms_zero_exists():
    forms = L.value_forms(0, 'number')
    assert any(f == '0' or f.endswith(' 0') or f == '$0' or f == '$ 0' for f in forms), forms
