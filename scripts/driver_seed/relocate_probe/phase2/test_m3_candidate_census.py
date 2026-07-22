"""Focused pins for the M3 candidate census (reviewer order 2026-07-22).

Real-data, read-only. Pins: exact-Decimal-only matching, the honest identity
ledger (period START unproven — end-date-only conflates Q4/FY), zero confirmed
same-facts, and complete denominators.

    venv/bin/python -m pytest scripts/driver_seed/relocate_probe/phase2/test_m3_candidate_census.py -q
"""
import json
import os
import sys
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..')))

OUT = os.path.join(_HERE, 'm3_candidate_census.json')


def _out():
    return json.load(open(OUT))


def test_zero_confirmed_and_honest_wording():
    o = _out()
    assert o['confirmed_same_fact'] == 0
    assert 'NOT twins' in o['census']
    assert 'none is yet confirmed' in o['honest_result']


def test_identity_ledger_never_overclaims():
    for r in _out()['ledger']:
        led = r['identity_ledger']
        assert led['period_start'].startswith('UNPROVEN'), led
        assert 'family_only' in led['unit'] or 'family' in led['unit'], led
        assert led['metric'].startswith('UNPROVEN')
        assert led['slice'].startswith('UNPROVEN')
        assert led['measurement'].startswith('UNPROVEN')
        assert r['status'] in ('possible_match_unconfirmed',
                               'no_same_value_candidate_found')


def test_denominators_sum_to_population():
    o = _out()
    assert sum(d['facts'] for d in o['denominators_by_lane'].values()) == 40
    for d in o['denominators_by_lane'].values():
        assert d['facts'] == d['with_exact_candidates'] + d['without']


def test_exact_matching_is_decimal_only():
    # live pin on one real record: string-exact Decimal comparison, no floats
    from m3_candidate_census import census
    from m1_canonical_selector import _driver
    rec = None
    for l in open(os.path.join(_HERE, '..', '..', '..', '..', 'data',
                               'driver_catalog_seed', 'wp1',
                               'code_resolved.jsonl')):
        r = json.loads(l, parse_float=Decimal)
        if r.get('source_type') == '8k' and r['ticker'] == 'AA' \
                and r['raw_label'] == 'Total Revenue':
            rec = r
            break
    assert rec is not None
    drv = _driver()
    with drv.session() as s:
        row = census(s, rec)
    drv.close()
    assert row['exact_value_candidates'] >= 1
    assert row['status'] == 'possible_match_unconfirmed'
    assert isinstance(rec['value'], (int, Decimal))  # parse_float=Decimal law


def test_real_81_3_decimal_exactness():
    # THE float-poison case (reviewer order): the 81.3 Load Factor record must
    # arrive as EXACT Decimal('81.3') — a float round-trip would break equality
    rec = None
    for l in open(os.path.join(_HERE, '..', '..', '..', '..', 'data',
                               'driver_catalog_seed', 'wp1',
                               'code_resolved.jsonl')):
        r = json.loads(l, parse_float=Decimal)
        if r.get('source_type') == '8k' \
                and r['raw_label'] == 'Passenger Load Factor (Percent)':
            rec = r
            break
    assert rec is not None
    assert isinstance(rec['value'], Decimal)
    assert rec['value'] == Decimal('81.3')
    assert str(rec['value']) == '81.3'
    assert Decimal(str(float(rec['value']))) == Decimal('81.3')  # printed form survives
    assert Decimal(float(rec['value'])) != Decimal('81.3')       # the hazard is real
