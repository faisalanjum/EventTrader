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


def test_unit_case_sensitivity_strip_only_nonblank_required():
    """Units are CASE-SENSITIVE (XBRL unitRef is an XML IDREF; corpus-live: 7 PSEG filings
    carry usdPerMWh vs usdPerMwh as DIFFERENT units). Normalization = strip ONLY. A numeric
    candidate must carry a nonblank string unit (census: 88,236 numeric gate facts, zero
    missing/blank/malformed — zero recall cost)."""
    variants = [blob('Revenues', [fact(unit='U_USD')]), blob('Revenues', [fact(unit='u_usd')])]
    assert mf(variants) is None, \
        "U_USD vs u_usd are DIFFERENT units — same value under both must abstain as a conflict"
    assert mf([blob('Revenues', [fact(unit='U_USD')])], unit_ref='u_usd') is None, \
        "a request unit must match the raw id CASE-EXACTLY"
    assert mf([blob('Revenues', [fact(unit=' U_USD ')])], unit_ref='U_USD') == XN.dec('100'), \
        "strip (padding) still normalizes — case does not"
    conflict = [blob('Revenues', [fact(unit='U_USD')]), blob('Revenues', [fact(unit='U_EUR')])]
    assert mf(conflict) is None, "same value under genuinely conflicting units abstains"
    assert mf([blob('Revenues', [fact(unit=['U_USD'])])]) is None, \
        "a list unitRef is malformed — never a candidate, NEVER a crash"
    assert mf([blob('Revenues', [fact(unit='   ')])]) is None, "blank unit is malformed"
    assert mf([blob('Revenues', [fact(unit=None)])]) is None, \
        "a NUMERIC fact with no unit is never a candidate (nonblank-unit law)"
    assert mf([blob('Revenues', [fact(unit='USD')])], expected_unit='money') == XN.dec('100'), \
        "the money heuristic casefolds LOCALLY — uppercase USD units must still match it"
    assert mf([blob('Revenues', [fact(unit='usd')])], expected_unit='money') == XN.dec('100')


def test_request_pairs_validated_never_crash_never_collapse():
    """Reproduced before fixing: unhashable pair items crashed TypeError; a repeated-axis
    request silently collapsed via frozenset; then a VALID pair failed after
    json.dumps/json.loads because JSON turns tuples into inner LISTS. Valid JSON pair arrays
    are accepted and canonicalized; malformed and repeated-axis content still abstains."""
    b = blob('Revenues', [fact(seg=[{'dimension': 'x:A', 'value': 'x:M'}])])
    ex = lambda pairs: LOC.match_facts_explain([b], 'us-gaap:Revenues', pairs,
                                               '2024-01-01', '2024-12-31')
    for bad in ("x:A=x:M", 3, None, [('x:A',)], [('x:A', 'x:M', 'extra')],
                [('x:A', 3)], [(' x:A', 'x:M')], [('x:A', 'x:M'), ('x:A', 'x:N')],
                [('x:A', 'x:M'), ('x:A', 'x:M')], ['x:A=x:M'], [{'x:A': 'x:M'}]):
        got, reason = ex(bad)
        assert got is None and reason == 'bad_request_pairs', f"{bad!r} -> {reason}"
    assert ex([('x:A', 'x:M')])[0] == XN.dec('100'), "a valid tuple pair list matches"
    roundtrip = json.loads(json.dumps([('x:A', 'x:M')]))
    assert roundtrip == [['x:A', 'x:M']]
    assert ex(roundtrip)[0] == XN.dec('100'), \
        "a JSON round-tripped pair array (inner LISTS) must be accepted and canonicalized"


def test_exact_unit_ref_is_authoritative_over_expected_unit():
    """Reproduced before fixing: unit_ref='Unit12' matched alone but adding
    expected_unit='money' vetoed it (the broad heuristic ran BEFORE exact equality). When
    unit_ref is supplied, exact equality is AUTHORITATIVE; expected_unit applies only when
    no unit_ref exists (opaque raw ids like Unit12 are exactly why)."""
    b = blob('Revenues', [fact(value='93100000', unit='Unit12')])
    a1 = LOC.match_facts_explain([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31',
                                 unit_ref='Unit12')
    assert a1 == (XN.dec('93100000'), 'ok')
    a2 = LOC.match_facts_explain([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31',
                                 unit_ref='Unit12', expected_unit='money')
    assert a2 == (XN.dec('93100000'), 'ok'), \
        "expected_unit must NOT veto an exact unit_ref match"
    a3 = LOC.match_facts_explain([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31',
                                 expected_unit='money')
    assert a3[0] is None, "without unit_ref the money heuristic still applies (Unit12 opaque)"


def test_nonmoney_needs_positive_evidence_opaque_abstains():
    """Sibling of the Unit12-money case, reproduced through the PRODUCTION fingerprint path:
    expected_unit='nonmoney' + stored Unit12 bound 93100000. An OPAQUE unit can be certified
    NEITHER money NOR nonmoney. Census over the 88,236-numeric-fact gate corpus: EVERY genuine
    nonmoney unit is a shares variant (shares / U_shares / Share / Unit_shares /
    Unit_Standard_shares_*), the opaque ids Unit12/Unit1/Unit16 cover 527 facts, and foreign
    currencies (cny, eur, U_AUD) also currently leaked through nonmoney. KNOWN COARSE-FILTER
    LIMIT (flagged, pinned below): U_UnitedStatesOfAmericaDollarsShare — dollars-per-share
    with no 'usd' substring — still passes the shares marker; the heuristic is a pre-filter,
    never proof."""
    sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
    import locate

    def prod(unit, expected):
        b = blob('Revenues', [fact(value='93100000', unit=unit)])
        return locate.locate({'xbrls': [b], 'concept': 'us-gaap:Revenues', 'members': [],
                              'period_start': '2024-01-01', 'period_end': '2024-12-31',
                              'expected_unit': expected})['value']
    assert prod('Unit12', 'nonmoney') is None, \
        "opaque Unit12 must NEVER satisfy a nonmoney ask (the reproduced production bind)"
    assert prod('U_shares', 'nonmoney') == XN.dec('93100000'), "positive shares case preserved"
    assert prod('shares', 'nonmoney') == XN.dec('93100000')
    assert prod('cny', 'nonmoney') is None, "a foreign CURRENCY is never nonmoney"
    assert prod('Unit12', 'money') is None, "opaque stays out of money too"
    assert prod('U_USD', 'money') == XN.dec('93100000')
    assert prod('U_UnitedStatesOfAmericaDollarsShare', 'nonmoney') == XN.dec('93100000'), \
        "KNOWN LIMIT pinned: dollars-per-share evades both substring heuristics (documented)"


COLLISION_EVIDENCE_QUERY = """
MATCH (f:Fact)-[:HAS_UNIT]->(un:Unit) WHERE f.unit_ref IN [$a, $b]
WITH split(f.id, '_')[0] AS rep, collect(DISTINCT f.unit_ref) AS us,
     collect(DISTINCT un.name) AS names
WHERE size(us) = 2
RETURN count(*) AS n, collect(rep)[..3] AS sample, collect(names)[..2] AS nm
"""
# Captured read-only results (2026-07-20, this graph):
#   {a:'usdPerMWh',  b:'usdPerMwh'}  -> n=7, sample=[.../pseg-20230331, .../pseg-20230630,
#     .../pseg-20230930], names=[['iso4217:USDutr:MWh','iso4217:USDpseg:mwh'], ...]
#   {a:'usdPerMMBTU', b:'usdPerMMBTu'} -> n=2, sample=[.../eog-20231231, .../eog-20241231],
#     names=[['iso4217:USDutr:MMBTU','iso4217:USDeog:mMBTu'], ...]
# 7 + 2 = the nine filings: same raw spelling apart from case, DIFFERENT semantic Units.


def test_real_corpus_collision_names_case_exact():
    """The REAL collision ids, pinned durably — the COMPLETE executable evidence query and
    its captured nine-filing results are preserved above (COLLISION_EVIDENCE_QUERY)."""
    for ua, ub in (('usdPerMWh', 'usdPerMwh'), ('usdPerMMBTU', 'usdPerMMBTu')):
        both = [blob('Revenues', [fact(value='42', unit=ua)]),
                blob('Revenues', [fact(value='42', unit=ub)])]
        got, reason = LOC.match_facts_explain(both, 'us-gaap:Revenues', [],
                                              '2024-01-01', '2024-12-31')
        assert got is None and reason == 'unit_conflict', \
            f"{ua}/{ub} same value must be a unit CONFLICT, never merged: {reason}"
        sel = LOC.match_facts([both[1]], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31',
                              unit_ref=ub)
        assert sel == XN.dec('42')
        assert LOC.match_facts([both[1]], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31',
                               unit_ref=ua) is None, \
            f"unit_ref={ua} must NOT match a {ub} fact — case is identity"


def test_malformed_stored_period_containers_abstain_never_crash():
    """Reproduced before fixing: string/int/list period containers crashed AttributeError."""
    for p in ('garbage', 7, ['x'], None):
        assert mf([blob('Revenues', [fact(period=p)])]) is None, f"period={p!r} must not bind"


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
    assert ex([])[1] == 'concept_missing', "nothing matched the concept at all"
    assert ex([blob('OtherConcept', [fact()])])[1] == 'concept_missing'
    wrong_period = blob('Revenues', [fact(period={'startDate': '2020-01-01',
                                                  'endDate': '2020-12-31'})])
    assert ex([wrong_period])[1] == 'no_candidate', \
        "concept matched but later filters emptied the field"
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
    with pytest.raises(ValueError, match="never both"):
        xbrl_lane.resolve([b], 'us-gaap:Revenues', [], '2024-01-01', '2024-12-31',
                          pairs=[('x:OnlyAxis', 'x:USMember')])   # [] is STILL a supplied input
