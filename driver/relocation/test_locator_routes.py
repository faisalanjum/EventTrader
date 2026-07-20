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
    inst_anchor = dict(ANCHOR, time_type='instant', wording=('Total widget cash',))
    xb2 = blob('us-gaap:Cash', [fact('86000000', {'instant': '2024-12-31'})])
    r2 = LOC.locate(inst_anchor, src([xb2], ["Total widget cash was 86,000,000 at year end"]))
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
    """Corrective-2 fixture update: the anchor must CARRY the slice (an aggregate anchor may
    never accept a dimensioned fact — pinned in test_28); the sliced anchor's tokens are
    source-proven and the full stored context survives exactly (padded unit stripped)."""
    us = dict(ANCHOR, slice='geography:united_states')
    f = fact('4000000000', D24, unit=' U_USD ',
             seg=[{'dimension': 'srt:StatementGeographicalAxis',
                   'value': 'x:UnitedStatesMember'}])
    r = LOC.locate(us, src([blob('us-gaap:Revenues', [f])],
                           ["United States total widget revenue was 4,000,000,000 for the year"]))
    assert len(r['items']) == 1
    x = r['items'][0]['xbrl']
    assert x == {'concept': 'us-gaap:Revenues',
                 'axis_members': [('srt:StatementGeographicalAxis', 'x:UnitedStatesMember')],
                 'period_start': '2024-01-01', 'period_end': '2024-12-31',
                 'ptype': 'duration', 'unit': 'U_USD'}
    assert r['items'][0]['quote'].startswith('United States')


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
            fact('4000000000', D24, seg=[{'dimension': 'x:A', 'value': 'x:WidgetMember'}]),
            fact('4000000000', D24, seg=[{'dimension': 'x:B', 'value': 'x:WidgetMember'}])])]),
        ('period', [blob('us-gaap:Revenues', [
            fact('4000000000', D24),
            fact('4000000000', {'startDate': '2024-01-01', 'endDate': '2024-06-30'})])]),
        ('unit', [blob('us-gaap:Revenues', [
            fact('4000000000', D24), fact('4000000000', D24, unit='usd')])]),
    ]
    for label, xbrls in variants:
        a = dict(ANCHOR, slice='segment:widget') if label == 'pairs' else ANCHOR
        r = LOC.locate(a, src(xbrls,
                              ["Total widget revenue was 4,000,000,000 for the year"]))
        assert r['items'] == [] and r['status'] == 'ambiguous', (label, r)


def test_8_r2_accepts_correctly_stamped_hint():
    s = src(texts=["Total widget revenue was $4,000,000,000 in the quarter"], sid='SRC-8K',
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
         'texts': ["CFO: Total widget revenue was 4,000,000,000 dollars this quarter."]}
    r = LOC.locate(ANCHOR, s, hints={'source_id': 'TR-1', 'value': 4000000000})
    assert r['status'] is None and len(r['items']) == 1 and 'xbrl' not in r['items'][0]


def test_12_honest_negative_no_proven_match():
    r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [fact('4000000000', D24)])],
                               ["Nothing relevant is printed here at all"]))
    assert r['items'] == [] and r['status'] == 'no_proven_match'
    r2 = LOC.locate(dict(ANCHOR, wording=()), src([], ["text"]))
    assert r2['items'] == [] and r2['status'] == 'insufficient_identity', \
        "an anchor with no usable wording clues cannot identify anything"


def test_14_sign_laws_positive_vs_negative_prints():
    xb = blob('us-gaap:OtherIncome', [fact('123000000', D24)])
    r = LOC.locate(dict(ANCHOR, wording=('Total widget revenue',)),
                   src([xb], ["Total widget revenue was (123,000,000) for the year"]))
    assert r['items'] == [], "a POSITIVE value must never bind a parenthesized-negative print"
    xb2 = blob('us-gaap:OtherIncome', [fact('-123000000', D24)])
    r2 = LOC.locate(ANCHOR, src([xb2],
                                ["Total widget revenue was 123,000,000 for the year"]))
    assert r2['items'] == [], "a NEGATIVE value must never bind an unsigned positive print"


def test_15_plain_number_never_accepts_percent_print():
    xb = blob('us-gaap:Ratio', [fact('86', D24)])
    r = LOC.locate(dict(ANCHOR, wording=('Widget margin',)),
                   src([xb], ["Widget margin was 86% for the year"]))
    assert r['items'] == [], "a plain number must never accept a percent-marked print"


def test_16_untied_concept_never_attaches_context():
    xb = blob('us-gaap:OperatingIncomeLoss', [fact('4000000000', D24)])
    r = LOC.locate(ANCHOR, src([xb],
                               ["Total widget revenue was 4,000,000,000 for the year"]))
    assert len(r['items']) == 1 and 'xbrl' not in r['items'][0], \
        "OperatingIncomeLoss can never ride a revenue quote — context omitted, item text-only"


def test_17_slice_and_measurement_identity_gates():
    us = dict(ANCHOR, slice='geography:united_states')
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24,
              seg=[{'dimension': 'srt:StatementGeographicalAxis', 'value': 'country:GB'}])])
    r = LOC.locate(us, src([xb],
                           ["United Kingdom total widget revenue was 4,000,000,000"]))
    assert r['items'] == [], "a US-slice anchor must never accept UK evidence"
    adj = dict(ANCHOR, measurement='adjusted')
    xb2 = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    r2 = LOC.locate(adj, src([xb2],
                             ["Total widget revenue was 4,000,000,000 for the year"]))
    assert r2['items'] == [], "an ADJUSTED anchor must never accept a plain/GAAP quote"
    r3 = LOC.locate(adj, src([xb2],
                             ["Adjusted total widget revenue was 4,000,000,000 for the year"]))
    assert len(r3['items']) == 1, "the adjusted quote satisfies the measurement gate"


def test_18_money_anchor_rejects_shares_unit():
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24, unit='U_shares')])
    r = LOC.locate(ANCHOR, src([xb],
                               ["Total widget revenue was 4,000,000,000 for the year"]))
    assert r['items'] == [], "a money anchor (series_unit m_usd) must never accept shares"


def test_19_period_word_contradiction_abstains():
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24)])          # FULL-YEAR fact
    r = LOC.locate(ANCHOR, src([xb],
                               ["Total widget revenue was 4,000,000,000 in the quarter"]))
    assert r['items'] == [], "full-year XBRL vs a quote saying 'quarter' must abstain"


def test_20_leading_qualifier_survives_in_raw_label():
    """Corrective-2 rewrite (reviewer order): the anchor must be ADJUSTED — a plain anchor
    accepting adjusted evidence is the wrong expected result (pinned in test_28)."""
    adj = dict(ANCHOR, measurement='adjusted')
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    r = LOC.locate(adj, src([xb],
                            ["Adjusted total widget revenue was 4,000,000,000 for the year"]))
    assert len(r['items']) == 1
    assert r['items'][0]['raw_label'].startswith('Adjusted'), \
        "leading qualifiers are MEANING — the raw label keeps them untouched"
    assert r['items'][0]['quote'].startswith('Adjusted')


def test_21_r1_r2_same_evidence_one_item_xbrl_wins():
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    s = src([xb], ["Total widget revenue was $4,000,000,000 for the year"], sid='S1')
    r = LOC.locate(ANCHOR, s, hints={'source_id': 'S1', 'value': 4000000000})
    assert len(r['items']) == 1, "R1+R2 on the same evidence must emit ONE item"
    assert 'xbrl' in r['items'][0], "the stronger XBRL-backed item wins the dedup"


def test_22_malformed_source_stamps_fail_closed():
    s = src(texts=["Total widget revenue was 4,000,000,000 in the quarter"], sid='S1')
    for h in ({'source_id': '', 'value': 4000000000},
              {'source_id': ' S1 ', 'value': 4000000000},
              {'source_id': 7, 'value': 4000000000}):
        r = LOC.locate(ANCHOR, s, hints=h)
        assert r['items'] == [], (h, r)
    bad_src = dict(s, source_id=' S1 ')
    r2 = LOC.locate(ANCHOR, bad_src, hints={'source_id': ' S1 ', 'value': 4000000000})
    assert r2['items'] == [], "a padded SOURCE-side stamp is malformed too"


def test_23_retrieval_tokens_from_label_portion_only():
    a = dict(ANCHOR, time_type='instant',
             wording=('International Stores 86 at fiscal year end',))
    xb = blob('us-gaap:StoreCount', [fact('91000000', {'instant': '2025-12-31'})])
    r = LOC.locate(a, src([xb], ["International Stores totaled 91,000,000 at period close"]))
    assert len(r['items']) == 1, \
        "the changed target wording must still retrieve — old prose words are never required"


def test_24_concept_clue_narrows_retrieval_never_proves():
    xbrls = [blob('us-gaap:Revenues', [fact('4000000000', D24)]),
             blob('us-gaap:DeferredRevenue', [fact('4000000000', D24)])]
    texts = ["Total widget revenue was 4,000,000,000 for the year"]
    r = LOC.locate(ANCHOR, src(xbrls, texts))
    assert r['items'] == [] and r['status'] == 'ambiguous', \
        "without a clue, two identity-distinct candidates for one occurrence stay ambiguous"
    clued = dict(ANCHOR, concept_clue='us-gaap:Revenues')
    r2 = LOC.locate(clued, src(xbrls, texts))
    assert len(r2['items']) == 1 and r2['items'][0]['xbrl']['concept'] == 'us-gaap:Revenues', \
        "the clue narrows retrieval; the quote remains the proof"
    r3 = LOC.locate(clued, src([xbrls[0]], ["Nothing relevant printed here"]))
    assert r3['items'] == [], "a clue alone can never prove — no quote, no item"


def test_13_determinism_regardless_of_blob_order():
    b1 = blob('us-gaap:Revenues', [fact('1000000000',
                                        {'startDate': '2024-10-01', 'endDate': '2024-12-31'})])
    b2 = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    texts = ["Total widget revenue was 1,000,000,000 in the fourth quarter and total widget "
             "revenue was 4,000,000,000 for the year"]
    a = LOC.locate(ANCHOR, src([b1, b2], texts))
    b = LOC.locate(ANCHOR, src([b2, b1], texts))
    assert a == b and len(a['items']) == 2

def test_27_unit_class_law_positive_match_required():
    """Corrective 2: the fact unit's CLASS must equal the anchor's series-unit class; UNKNOWN
    (opaque) abstains. Graph-verified: U_EUR=1,229 facts; Unit12 maps to FIVE incompatible
    meanings (USD 41,984 · shares 506 · pure 126 · employee 15) — an opaque id proves nothing."""
    for bad in ('U_EUR', 'Unit12'):
        xb = blob('us-gaap:Revenues', [fact('4000000000', D24, unit=bad)])
        r = LOC.locate(ANCHOR, src([xb],
                                   ["Total widget revenue was 4,000,000,000 for the year"]))
        assert r['items'] == [], (bad, r)
    # corrective-3 ORDERED REVERSAL: dollar-per-share units SUPPORT the usd meaning (per-X
    # lives in the metric NAME - the owner's locked ruling; 327,402 real USDshares facts)
    ps = blob('us-gaap:EarningsPerShareDiluted',
              [fact('4000000000', D24, unit='U_UnitedStatesOfAmericaDollarsShare')])
    rp = LOC.locate(ANCHOR, src([ps],
                                ["Total widget revenue was 4,000,000,000 for the year"]))
    assert len(rp['items']) == 1, 'dollar-per-share is USD money and must support m_usd'
    # share-only units are COUNTS and support count anchors (692,129 real shares facts)
    cnt = dict(ANCHOR, series_unit='count', wording=('Widget shares outstanding',))
    sh = blob('us-gaap:SharesOutstanding', [fact('91000000', D24, unit='shares')])
    rs = LOC.locate(cnt, src([sh],
                             ["Widget shares outstanding were 91,000,000 for the year"]))
    assert len(rs['items']) == 1, 'plain shares must support a count anchor'
    cnt = dict(ANCHOR, series_unit='count', wording=('Widget store count',))
    xb2 = blob('us-gaap:StoreCount', [fact('91', D24, unit='U_USD')])
    r2 = LOC.locate(cnt, src([xb2], ["Widget store count was 91 for the year"]))
    assert r2['items'] == [], "a count anchor must never accept a money unit"


def test_28_full_identity_aggregate_and_measurement_both_directions():
    agg = ANCHOR                                       # slice='' = the AGGREGATE series
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24,
              seg=[{'dimension': 'srt:StatementGeographicalAxis', 'value': 'country:GB'}])])
    r = LOC.locate(agg, src([xb],
                            ["United Kingdom total widget revenue was 4,000,000,000"]))
    assert r['items'] == [], "an aggregate anchor must never accept a DIMENSIONED fact"
    xb2 = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    r2 = LOC.locate(ANCHOR, src([xb2],
                                ["Adjusted total widget revenue was 4,000,000,000 for the year"]))
    assert r2['items'] == [], \
        "a PLAIN anchor must never accept ADJUSTED evidence (unexplained qualifier)"
    adj = dict(ANCHOR, measurement='adjusted')
    r3 = LOC.locate(adj, src([xb2],
                             ["adjusted total widget revenue was 4,000,000,000 for the year"]))
    assert len(r3['items']) == 1, "lowercase 'adjusted' evidence must satisfy an adjusted anchor"


def test_29_generic_word_never_attaches_context():
    for con, text in (('us-gaap:OperatingIncomeLoss',
                       "Operating widget revenue was 4,000,000,000 for the year"),
                      ('us-gaap:AssetsCurrent',
                       "Current widget revenue was 4,000,000,000 for the year")):
        xb = blob(con, [fact('4000000000', D24)])
        a = dict(ANCHOR, wording=(text.split(' was')[0],))
        r = LOC.locate(a, src([xb], [text]))
        assert len(r['items']) == 1 and 'xbrl' not in r['items'][0], (con, r)


def test_30_period_wording_either_side_and_three_months_fiscal_year():
    xb_fy = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    for text in ("For the quarter, total widget revenue was 4,000,000,000",
                 "Total widget revenue was 4,000,000,000 for the three months"):
        r = LOC.locate(ANCHOR, src([xb_fy], [text]))
        assert r['items'] == [], (text, r)
    xb_q = blob('us-gaap:Revenues', [fact('1000000000',
                {'startDate': '2024-10-01', 'endDate': '2024-12-31'})])
    r2 = LOC.locate(ANCHOR, src([xb_q],
                                ["For the fiscal year, total widget revenue was 1,000,000,000"]))
    assert r2['items'] == [], "a quarterly fact must never ride full-fiscal-year wording"


def test_31_equal_q_and_fy_values_resolve_by_period_wording():
    """Equal-valued Q and FY facts, separately printed with their own period wording, must
    produce TWO correctly bound items — never a lazy ambiguous."""
    xb = blob('us-gaap:Revenues', [
        fact('4000000000', {'startDate': '2024-10-01', 'endDate': '2024-12-31'}),
        fact('4000000000', D24)])
    texts = ["Total widget revenue was 4,000,000,000 in the quarter. "
             "Total widget revenue was 4,000,000,000 for the full year."]
    r = LOC.locate(ANCHOR, src([xb], texts))
    assert r['status'] is None and len(r['items']) == 2, r
    spans = {(i['xbrl']['period_start'], i['xbrl']['period_end']) for i in r['items']}
    assert spans == {('2024-10-01', '2024-12-31'), ('2024-01-01', '2024-12-31')}


def test_32_large_number_overflow_class_abstains_never_crashes():
    """The WP1 round-13/14 invalid_value law: the 1e309 class is Decimal-finite but
    float-infinite — candidacy and hints must abstain cleanly, never crash or bind."""
    xb = blob('us-gaap:Revenues', [fact('1e309', D24)])
    r = LOC.locate(ANCHOR, src([xb], ["Total widget revenue was 1e309 for the year"]))
    assert r['items'] == []
    s = src(texts=["Total widget revenue was 4,000,000,000 in the quarter"], sid='S1')
    r2 = LOC.locate(ANCHOR, s, hints={'source_id': 'S1', 'value': '1e309'})
    assert r2['items'] == []
