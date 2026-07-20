"""The neutral matcher's pin battery (WP2 — the v4-promised RED pins, written after the
reviewer's audit of 3150655; the process miss of building the matcher without them first is
owned in the record). Every reproduced bug class from that audit is pinned here.

    venv/bin/python -m pytest driver/relocation/test_match_facts.py -q
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed', 'relocate_probe'))
sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
import exact_numbers as XN
import locator as LOC
import xbrl_lane

D = {'startDate': '2024-01-01', 'endDate': '2024-12-31'}


def blob(con, facts):
    return json.dumps({con: facts})


def fact(value='100', period=D, unit='U_USD', seg=None):
    fc = {'value': value, 'period': period, 'unitRef': unit}
    if seg is not None:
        fc['segment'] = seg
    return fc


def mf(blobs, concept='us-gaap:Revenues', pairs=(), **kw):
    return LOC.match_facts(blobs, concept, pairs, '2024-01-01', '2024-12-31', **kw)


def test_wrong_axis_swapped_pairs_and_order():
    b = blob('Revenues', [fact(seg=[{'dimension': 'x:GeoAxis', 'value': 'x:USMember'}])])
    assert mf([b], pairs=[('x:GeoAxis', 'x:USMember')]) == XN.dec('100')
    assert mf([b], pairs=[('x:SegAxis', 'x:USMember')]) is None, \
        "a right member under a WRONG axis must never match"
    two = blob('Revenues', [fact(seg=[{'dimension': 'x:A', 'value': 'x:M1'},
                                      {'dimension': 'x:B', 'value': 'x:M2'}])])
    assert mf([two], pairs=[('x:A', 'x:M1'), ('x:B', 'x:M2')]) == XN.dec('100')
    assert mf([two], pairs=[('x:B', 'x:M2'), ('x:A', 'x:M1')]) == XN.dec('100'), \
        "pair ORDER must not matter"
    assert mf([two], pairs=[('x:A', 'x:M2'), ('x:B', 'x:M1')]) is None, \
        "SWAPPED members across axes are a different identity"


def test_concept_identity_matrix():
    assert mf([blob('Revenues', [fact()])], 'us-gaap:Revenues') == XN.dec('100')   # prefixed->bare
    assert mf([blob('Revenues', [fact()])], 'Revenues') == XN.dec('100')           # bare<->bare
    assert mf([blob('us-gaap:Revenues', [fact()])], 'us-gaap:Revenues') == XN.dec('100')
    assert mf([blob('evil:Revenues', [fact()])], 'us-gaap:Revenues') is None       # prefix mismatch
    assert mf([blob('evil:Revenues', [fact()])], 'Revenues') is None, \
        "a BARE request must never accept prefixed storage (the evil:Revenues class)"


def test_unit_normalization_conflict_and_malformed():
    same = [blob('Revenues', [fact(unit='U_USD')]), blob('Revenues', [fact(unit='u_usd')])]
    assert mf(same) == XN.dec('100'), "U_USD ≡ u_usd — case must not split into a fake conflict"
    assert mf(same, unit_ref='  U_USD ') == XN.dec('100'), "request unit normalizes too"
    conflict = [blob('Revenues', [fact(unit='U_USD')]), blob('Revenues', [fact(unit='U_EUR')])]
    assert mf(conflict) is None, "same value under genuinely conflicting units abstains"
    assert mf([blob('Revenues', [fact(unit=['U_USD'])])]) is None, \
        "a list unitRef is malformed — never a candidate, NEVER a crash"
    assert mf([blob('Revenues', [fact(unit='   ')])]) is None, "blank unit is malformed"
    assert mf([blob('Revenues', [fact(unit=None)])]) == XN.dec('100'), \
        "a unit-less fact stays legal"


def test_fact_side_malformed_periods_never_candidates():
    shapes = [{'startDate': '2024-01-01'},                       # start-only
              {'endDate': '2024-12-31'},                         # end-only
              {},                                                # blank
              {'startDate': '2024-02-30', 'endDate': '2024-12-31'},   # impossible date
              {'instant': '2024-12-31', 'startDate': '2024-01-01',
               'endDate': '2024-12-31'}]                         # mixed instant+duration
    for p in shapes:
        assert mf([blob('Revenues', [fact(period=p)])]) is None, f"shape {p} must not bind"


def test_float_values_rejected_raw_strings_exact():
    floaty = blob('Revenues', [{'value': 6707000000.0, 'period': D, 'unitRef': 'U_USD'}])
    assert mf([floaty]) is None, "a stored FLOAT value must be rejected, never str()-laundered"
    frac = blob('Revenues', [fact(value='1.23')])
    got = mf([frac])
    assert got == XN.dec('1.23') and str(got) == '1.23'


def test_explain_reasons():
    ex = lambda blobs, **kw: LOC.match_facts_explain(blobs, 'us-gaap:Revenues',
                                                     kw.pop('pairs', ()), '2024-01-01',
                                                     '2024-12-31', **kw)
    assert ex([blob('Revenues', [fact()])])[1] == 'ok'
    assert ex([])[1] == 'no_candidate'
    assert ex([blob('Revenues', [fact(value='100')]),
               blob('Revenues', [fact(value='200')])])[1] == 'ambiguous_values'
    assert ex([blob('Revenues', [fact(unit='U_USD')]),
               blob('Revenues', [fact(unit='U_EUR')])])[1] == 'unit_conflict'
    assert ex([blob('Revenues', [fact(value='garbage')])])[1] == 'nonnumeric_value'
    assert LOC.match_facts_explain([], 'us-gaap:Revenues', (), 'bad', 'dates')[1] == \
        'bad_request_period'
    assert ex([blob('Revenues', [fact()])], unit_ref=['U_USD'])[1] == 'bad_request_unit'


def test_adapter_dimensioned_member_only_always_abstains():
    b = blob('Revenues', [fact(seg=[{'dimension': 'x:OnlyAxis', 'value': 'x:USMember'}])])
    assert xbrl_lane.resolve([b], 'us-gaap:Revenues', ['x:USMember'],
                             '2024-01-01', '2024-12-31') is None, \
        "an axis must NEVER be inferred — not even when the pairing is unique"
    assert xbrl_lane.resolve([b], 'us-gaap:Revenues', None, '2024-01-01', '2024-12-31',
                             pairs=[('x:OnlyAxis', 'x:USMember')]) == XN.dec('100')
    assert xbrl_lane.resolve([blob('Revenues', [fact()])], 'us-gaap:Revenues', [],
                             '2024-01-01', '2024-12-31') == XN.dec('100'), \
        "dimensionless [] is fully specified and stays legal"
    with pytest.raises(ValueError, match="never both"):
        xbrl_lane.resolve([b], 'us-gaap:Revenues', ['x:USMember'], '2024-01-01', '2024-12-31',
                          pairs=[('x:OnlyAxis', 'x:USMember')])
