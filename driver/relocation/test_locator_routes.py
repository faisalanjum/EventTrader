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


def test_3_invalid_fact_period_shapes_never_emit():
    shapes = [{'startDate': '2024-01-01'}, {'endDate': '2024-12-31'}, {},
              {'startDate': '2024-02-30', 'endDate': '2024-12-31'},
              {'instant': '2024-12-31', 'startDate': '2024-01-01', 'endDate': '2024-12-31'},
              'garbage', 7, None]
    for p in shapes:
        r = LOC.locate(ANCHOR, src([blob('us-gaap:Revenues', [fact('4000000000', p)])],
                                   ["Total widget revenue was 4,000,000,000 for the year"]))
        assert r['items'] == [] and r['status'] == 'no_proven_match', (p, r)


def test_9_missing_and_foreign_hint_stamps_fail_closed():
    s = src(texts=["Total widget revenue was 4,000,000,000 in the quarter"], sid='SRC-8K')
    for h in ({'value': 4000000000}, {'source_id': 'OTHER-SRC', 'value': 4000000000},
              {'source_id': None, 'value': 4000000000}, 'not-a-mapping'):
        r = LOC.locate(ANCHOR, s, hints=h)
        assert r['items'] == [] and r['status'] == 'no_proven_match', (h, r)


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


def test_32_large_number_overflow_class_abstains_never_crashes():
    """The WP1 round-13/14 invalid_value law: the 1e309 class is Decimal-finite but
    float-infinite — candidacy and hints must abstain cleanly, never crash or bind."""
    xb = blob('us-gaap:Revenues', [fact('1e309', D24)])
    r = LOC.locate(ANCHOR, src([xb], ["Total widget revenue was 1e309 for the year"]))
    assert r['items'] == []
    s = src(texts=["Total widget revenue was 4,000,000,000 in the quarter"], sid='S1')
    r2 = LOC.locate(ANCHOR, s, hints={'source_id': 'S1', 'value': '1e309'})
    assert r2['items'] == []


FY_TEXT = ["Total widget revenue was 4,000,000,000 for the year"]


def pfact(v):
    return blob('us-gaap:MarginChange', [fact(v, D24, unit='pure')])


# ─── Phase 3 migrated attack pins (2026-07-22): the two strongest retired attack
# shapes re-land on their recorded destination — prose NEVER binds; the locator
# abstains honestly (Route E). The 45 retired prose-machinery pins are NAMED in
# the Phase-3 close commit.

def test_migrated_r2_hint_never_binds_from_text():
    hint = {'value': '4000000000', 'quote': 'Total widget revenue was '
            '4,000,000,000 for the year', 'source': 'driver_memory'}
    xb = blob('us-gaap:Revenues', [fact('4000000000', D24)])
    out = LOC.locate(ANCHOR, src([xb], [hint['quote']]), hints=[hint])
    assert out['items'] == [] and out['status'] == 'no_proven_match', out


def test_migrated_transcript_shaped_payload_abstains():
    texts = ["Great quarter everyone. Total widget revenue was 4,000,000,000 "
             "for the year, ahead of plan."]
    out = LOC.locate(ANCHOR, src((), texts, stype='transcript'))
    assert out['items'] == [] and out['status'] == 'no_proven_match', out
