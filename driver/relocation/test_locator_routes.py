"""WP2 Chunk 2 — the neutral locate(anchor, source, hints=None) route proofs (RED-first).

R1 = own-source XBRL enumeration across ALL valid periods, every emission proven by an exact
target-source quote (label + number in-row); R2 = source_id-stamped known-value hint proven
from target-source text. Statuses: None on success; no_proven_match / ambiguous /
insufficient_identity on empty. Text items carry NO xbrl block; bare stored concepts are
never promoted; fixtures use FULL-MAGNITUDE prints (self-evident scale).

    venv/bin/python -m pytest driver/relocation/test_locator_routes.py -q
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import exact_numbers as XN
import locator as LOC

ANCHOR = {
    "source_id": "SYN-PRIOR", "company": "C1", "driver": "revenue", "slice": "",
    "measurement": "", "series_unit": "m_usd", "time_type": "duration",
    "fact_type": "metric", "wording": ("Total widget revenue",), "concept_clue": None,
}
D24 = {'startDate': '2024-01-01', 'endDate': '2024-12-31'}


def fact(value, period, unit='U_USD', seg=None):
    fc = {'value': value, 'period': period, 'unitRef': unit}
    if seg is not None:
        fc['segment'] = seg
    return fc


def blob(con, facts):
    return json.dumps({con: facts})


def src(xbrls=(), texts=(), sid='SYN-SRC-1', stype='10k'):
    return {'source_id': sid, 'source_type': stype, 'xbrls': list(xbrls),
            'texts': list(texts)}


def test_1_all_period_enumeration_q_ytd_fy_comparative_and_instant():
    xb = blob('us-gaap:Revenues', [
        fact('1000000000', {'startDate': '2024-10-01', 'endDate': '2024-12-31'}),   # Q
        fact('3000000000', {'startDate': '2024-01-01', 'endDate': '2024-09-30'}),   # YTD
        fact('4000000000', D24),                                                    # FY
        fact('3600000000', {'startDate': '2023-01-01', 'endDate': '2023-12-31'})])  # comparative
    texts = ["Total widget revenue was 1,000,000,000 in the fourth quarter. "
             "Total widget revenue reached 3,000,000,000 for the nine months. "
             "Total widget revenue was 4,000,000,000 for the year, versus total widget "
             "revenue of 3,600,000,000 a year earlier."]
    r = LOC.locate(ANCHOR, src([xb], texts))
    assert r['status'] is None and len(r['items']) == 4, r
    spans = {(i['xbrl']['period_start'], i['xbrl']['period_end']) for i in r['items']}
    assert spans == {('2024-10-01', '2024-12-31'), ('2024-01-01', '2024-09-30'),
                     ('2024-01-01', '2024-12-31'), ('2023-01-01', '2023-12-31')}
    inst_anchor = dict(ANCHOR, time_type='instant', wording=('Widget store count',))
    xb2 = blob('us-gaap:StoreCount', [fact('86', {'instant': '2024-12-31'}, unit='U_cnt')])
    r2 = LOC.locate(inst_anchor, src([xb2], ["Widget store count stood at 86 at year end"]))
    assert r2['status'] is None and len(r2['items']) == 1
    assert r2['items'][0]['xbrl']['ptype'] == 'instant'


def test_2_exact_duplicate_across_blobs_deduplicates():
    f = fact('4000000000', D24)
    r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [f]), blob('us-gaap:Revenues', [f])],
                               ["Total widget revenue was 4,000,000,000 for the year"]))
    assert r['status'] is None and len(r['items']) == 1, r


def test_3_invalid_fact_period_shapes_never_emit():
    shapes = [{'startDate': '2024-01-01'}, {'endDate': '2024-12-31'}, {},
              {'startDate': '2024-02-30', 'endDate': '2024-12-31'},
              {'instant': '2024-12-31', 'startDate': '2024-01-01', 'endDate': '2024-12-31'},
              'garbage', 7, None]
    for p in shapes:
        r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [fact('4000000000', p)])],
                                   ["Total widget revenue was 4,000,000,000 for the year"]))
        assert r['items'] == [] and r['status'] == 'no_proven_match', (p, r)


def test_4_incomplete_dimensions_never_masquerade_as_empty():
    bad = fact('4000000000', D24, seg=[{'dimension': '  ', 'value': 'x:M'}])
    r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [bad])],
                               ["Total widget revenue was 4,000,000,000 for the year"]))
    assert r['items'] == [], "an unparseable segment must never pose as undimensioned"
    good = fact('4000000000', D24)
    r2 = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [good])],
                                ["Total widget revenue was 4,000,000,000 for the year"]))
    assert len(r2['items']) == 1 and r2['items'][0]['xbrl']['axis_members'] == [], \
        "axis_members=[] is legal only for a VERIFIED-undimensioned fact"


def test_5_fully_stored_xbrl_context_survives_exactly():
    f = fact('4000000000', D24, unit=' U_USD ',
             seg=[{'dimension': 'x:GeoAxis', 'value': 'x:USMember'}])
    r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [f])],
                               ["Total widget revenue was 4,000,000,000 for the year"]))
    assert len(r['items']) == 1
    x = r['items'][0]['xbrl']
    assert x == {'concept': 'us-gaap:Revenues',
                 'axis_members': [('x:GeoAxis', 'x:USMember')],
                 'period_start': '2024-01-01', 'period_end': '2024-12-31',
                 'ptype': 'duration', 'unit': 'U_USD'}


def test_6_bare_stored_concept_emits_no_promoted_context():
    r = LOC.locate(ANCHOR, src([blob('Revenues', [fact('4000000000', D24)])],
                               ["Total widget revenue was 4,000,000,000 for the year"]))
    assert len(r['items']) == 1
    it = r['items'][0]
    assert 'xbrl' not in it, "a bare stored concept must NEVER be promoted into an identifier"
    assert it['quote'] and it['raw_label'] and it['value'] == XN.dec('4000000000')


def test_7_ambiguity_table_same_occurrence_identity_differences_abstain():
    base = dict(period=D24, unit='U_USD', seg=None)
    variants = [
        ('concept', [blob('us-gaap:Revenues', [fact('4000000000', D24)]),
                     blob('evil:Revenues', [fact('4000000000', D24)])]),
        ('pairs', [blob('us-gaap:Revenues', [
            fact('4000000000', D24, seg=[{'dimension': 'x:A', 'value': 'x:M'}]),
            fact('4000000000', D24, seg=[{'dimension': 'x:B', 'value': 'x:M'}])])]),
        ('period', [blob('us-gaap:Revenues', [
            fact('4000000000', D24),
            fact('4000000000', {'startDate': '2024-01-01', 'endDate': '2024-06-30'})])]),
        ('unit', [blob('us-gaap:Revenues', [
            fact('4000000000', D24), fact('4000000000', D24, unit='U_EUR')])]),
    ]
    for label, xbrls in variants:
        r = LOC.locate(ANCHOR, src(xbrls,
                                   ["Total widget revenue was 4,000,000,000 for the year"]))
        assert r['items'] == [] and r['status'] == 'ambiguous', (label, r)


def test_8_r2_accepts_correctly_stamped_hint():
    s = src(texts=["Total widget revenue was 4,000,000,000 in the quarter"], sid='SRC-8K',
            stype='8k')
    r = LOC.locate(ANCHOR, s, hints={'source_id': 'SRC-8K', 'value': 4000000000})
    assert r['status'] is None and len(r['items']) == 1
    it = r['items'][0]
    assert it['value'] == XN.dec('4000000000') and 'xbrl' not in it
    assert 'Total widget revenue' in it['quote']


def test_9_missing_and_foreign_hint_stamps_fail_closed():
    s = src(texts=["Total widget revenue was 4,000,000,000 in the quarter"], sid='SRC-8K')
    for h in ({'value': 4000000000}, {'source_id': 'OTHER-SRC', 'value': 4000000000},
              {'source_id': None, 'value': 4000000000}, 'not-a-mapping'):
        r = LOC.locate(ANCHOR, s, hints=h)
        assert r['items'] == [] and r['status'] == 'no_proven_match', (h, r)


def test_10_r2_multiple_distinct_occurrences_are_ambiguous():
    s = src(texts=["Total widget revenue was 4,000,000,000 in Q1. Later, total widget "
                   "revenue was 4,000,000,000 again."], sid='SRC-8K')
    r = LOC.locate(ANCHOR, s, hints={'source_id': 'SRC-8K', 'value': 4000000000})
    assert r['items'] == [] and r['status'] == 'ambiguous', r


def test_11_transcript_shaped_payload_resolves_through_r2():
    s = {'source_id': 'TR-1', 'source_type': 'transcript', 'xbrls': [],
         'texts': ["CFO: Total widget revenue was 4,000,000,000 this quarter, ahead of plan."]}
    r = LOC.locate(ANCHOR, s, hints={'source_id': 'TR-1', 'value': 4000000000})
    assert r['status'] is None and len(r['items']) == 1 and 'xbrl' not in r['items'][0]


def test_12_honest_negative_no_proven_match():
    r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [fact('4000000000', D24)])],
                               ["Nothing relevant is printed here at all"]))
    assert r['items'] == [] and r['status'] == 'no_proven_match'
    r2 = LOC.locate(dict(ANCHOR, wording=()), src([], ["text"]))
    assert r2['items'] == [] and r2['status'] == 'insufficient_identity', \
        "an anchor with no usable wording clues cannot identify anything"


def test_13_determinism_regardless_of_blob_order():
    b1 = blob('us-gaap:Revenues', [fact('1000000000',
                                        {'startDate': '2024-10-01', 'endDate': '2024-12-31'})])
    b2 = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    texts = ["Total widget revenue was 1,000,000,000 in the fourth quarter and total widget "
             "revenue was 4,000,000,000 for the year"]
    a = LOC.locate(ANCHOR, src([b1, b2], texts))
    b = LOC.locate(ANCHOR, src([b2, b1], texts))
    assert a == b and len(a['items']) == 2
