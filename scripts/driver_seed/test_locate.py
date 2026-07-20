"""R1 step 3: locate() = ONE reusable two-mode entry. Channel-neutral (no fiscal.ai shapes).

    venv/bin/python -m pytest scripts/driver_seed/test_locate.py -q
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'relocate_probe'))
import locate

# a consolidated (undimensioned) revenue fact, value 6,707M, FY2024.
_AGG_BLOB = json.dumps({"RevenueFromContractWithCustomerExcludingAssessedTax": [
    {"value": "6707000000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
     "unitRef": "usd"}]})   # corrective: numeric candidacy requires a nonblank unit (census:
                            # 88,236 real numeric gate facts, ZERO unit-less — fixtures mirror
                            # reality, the round-28 modernization law)
_CONCEPT = "RevenueFromContractWithCustomerExcludingAssessedTax"


def test_value_known_finds_the_printed_quote():
    # value in hand -> find WHERE it is PRINTED. The raw xbrl block rides along as evidence, but the QUOTE
    # must always be text a human wrote. (This test previously asserted a hit with NO text at all, which was
    # only reachable via the fabricated XBRL-metadata quote — it was pinning the bug.)
    # '(in millions)' = the section's scale declaration (round-13: a bare SCALED print like '6,707'
    # for 6.707B binds only when the containing text shows its scale)
    r = locate.locate({'xbrls': [_AGG_BLOB], 'texts': ['(in millions) Total revenue 6,707 for the year'],
                       'name': 'Total Revenue', 'value': 6707000000, 'fmt': None, 'period': '2024-12-31'})
    assert r['hit'] is not None and r['hit']['tier'] == 'T1-xbrl', r
    assert r['hit']['quote'] == 'Total revenue 6,707', r['hit']
    assert r['hit']['quote_source'] == 'section'
    assert r['hit']['xbrl']['concept'] == _CONCEPT


def test_value_unknown_resolves_the_value():
    # fingerprint only (no number) -> find the value (returns a 'value').
    r = locate.locate({'xbrls': [_AGG_BLOB], 'concept': _CONCEPT, 'members': [],
                       'period_start': '2024-01-01', 'period_end': '2024-12-31'})
    assert r['value'] == 6707000000, r


def test_never_emits_a_synthetic_xbrl_quote():
    """ChannelContract §3: `quote` is REQUIRED, verbatim, never paraphrased. When XBRL matches but no
    printed evidence can be located (no exact-cell, no text label), the old code fabricated a quote out of
    XBRL metadata — 'OperatingIncomeLoss [Member] [a..b] = 123' — which no human wrote and no design rule
    authorises. There is no fake-quote fallback: fall to the LLM tier instead."""
    r = locate.locate_by_value({'xbrls': [_AGG_BLOB], 'texts': [], 'name': 'Total Revenue',
                                'value': 6707000000, 'fmt': None, 'period': '2024-12-31'})
    hit = r['hit']
    assert hit is None or hit.get('quote_source') != 'xbrl_fact', \
        f"fabricated an XBRL-metadata quote: {hit.get('quote')!r}"


# --- #5 + N1: the number-form matcher must FIND a labeled small/decimal/zero value and ABSTAIN on a generic
# one. Tested through the FULL locator (locate_by_value), never value_ok alone. Precision must come from the
# KPI label sitting next to the number (row_quote), NOT from a magnitude/length threshold. ---
def _vk(name, val, fmt, txt):
    return locate.locate_by_value({'xbrls': [], 'texts': [txt], 'name': name, 'value': val,
                                   'fmt': fmt, 'period': '2024-12-31'})


def test_labeled_ratio_decimal_resolves():
    r = _vk('Bauxite Production', 38.3, 'ratio', 'Bauxite Production 38.3 for the fiscal year')
    assert r['hit'] is not None and '38.3' in r['hit']['quote'], r


def test_labeled_small_value_resolves():
    r = _vk('International Stores', 86, 'number', 'International Stores 86 at fiscal year end')
    assert r['hit'] is not None and '86' in r['hit']['quote'], r


def test_labeled_zero_resolves():
    r = _vk('Total Fee Related Earnings', 0, 'number', 'Total Fee Related Earnings 0 for the segment')
    assert r['hit'] is not None and '0' in r['hit']['quote'], r


def test_trailing_evidence_preserved_and_gated():
    """Round-12 (reviewer, confirmed): the crop used to CUT OFF the very '%' and ')' the gates
    need. The quote must retain immediate trailing sign/unit evidence, and the gates must act on it
    THROUGH the full locator: plain 86 never accepts 86% / 86 percent; +123 never accepts (123);
    -123 does; a scaled print keeps its unit word in the quote."""
    assert _vk('International Stores', 86, 'number', 'International Stores 86% at year end')['hit'] is None
    assert _vk('International Stores', 86, 'number', 'International Stores 86 percent at year end')['hit'] is None
    r = _vk('International Stores', 86, 'number', 'International Stores 86 at fiscal year end')
    assert r['hit'] is not None                                       # the plain print still resolves
    assert _vk('Operating Income', 123, 'number', 'Operating income (123) for the quarter')['hit'] is None
    neg = _vk('Operating Income', -123, 'number', 'Operating income (123) for the quarter')
    assert neg['hit'] is not None and ')' in neg['hit']['quote']      # closing paren kept in evidence
    big = _vk('Total Revenue', 5432000000, 'number', 'Total revenue $ 5,432 million for the year')
    assert big['hit'] is not None and big['hit']['quote'].rstrip().endswith('million')


def test_generic_small_decimal_or_zero_abstains():
    # the number is present but the KPI label is NOT next to it -> must NOT resolve (hand to the LLM tier)
    assert _vk('International Stores', 86, 'number', 'the firm operates in 86 countries')['hit'] is None
    assert _vk('Bauxite Production', 38.3, 'ratio', 'operating margin rose 38.3 points in banking')['hit'] is None
    assert _vk('Total Fee Related Earnings', 0, 'number', 'there were 0 recalls during the year')['hit'] is None


def test_dispatch_by_presence_of_value():
    vk = locate.locate({'xbrls': [_AGG_BLOB], 'texts': [], 'name': 'Total Revenue',
                        'value': 6707000000, 'fmt': None, 'period': '2024-12-31'})
    vu = locate.locate({'xbrls': [_AGG_BLOB], 'concept': _CONCEPT, 'members': [],
                        'period_start': '2024-01-01', 'period_end': '2024-12-31'})
    assert 'hit' in vk and 'value' in vu   # value present -> value-known; absent -> value-unknown


def test_invalid_value_abstains_not_crash():
    """Round-13 (live-reproduced): 'N/A' / '-331x' crashed the public locator with ValueError.
    A malformed vendor number must ABSTAIN cleanly — never raise."""
    for bad in ('N/A', '-331x', '', '1e309', '-1e309'):   # round-14: Decimal-finite but float-inf
        r = locate.locate({'xbrls': [], 'texts': ['Revenue was 5 million'], 'name': 'Revenue',
                           'value': bad, 'fmt': None, 'period': '2025-01-01'})
        assert r == {'hit': None, 'snips': []}, (bad, r)
    print("[ok] malformed value -> clean abstain, never a crash (incl. float-overflow class)")


def test_fingerprint_forwards_unit_args(monkeypatch):
    """Round-13: the public value-unknown lane dropped unit_ref/expected_unit on the floor —
    a shares fact could satisfy a money request. They must be forwarded to xbrl_lane.resolve."""
    import xbrl_lane
    seen = {}

    def fake(xbrls, concept, members, ps, pe, unit_ref=None, expected_unit=None, pairs=None):
        seen.update(unit_ref=unit_ref, expected_unit=expected_unit, pairs=pairs,
                    members=members)
        return None
    monkeypatch.setattr(xbrl_lane, 'resolve', fake)
    r = locate.locate({'xbrls': [], 'concept': 'us-gaap:Revenues', 'members': [],
                       'period_start': '2024-01-01', 'period_end': '2024-12-31',
                       'unit_ref': 'usd', 'expected_unit': 'money'})
    assert r == {'value': None}
    assert seen == {'unit_ref': 'usd', 'expected_unit': 'money', 'pairs': None,
                    'members': []}, seen
    # corrective: req['pairs'] is FORWARDED and the legacy member input is NOT also sent
    locate.locate({'xbrls': [], 'concept': 'us-gaap:Revenues', 'members': ['x:M'],
                   'pairs': [('x:A', 'x:M')],
                   'period_start': '2024-01-01', 'period_end': '2024-12-31'})
    assert seen['pairs'] == [('x:A', 'x:M')] and seen['members'] is None, seen
    print("[ok] fingerprint lane forwards unit identity AND full pairs to xbrl_lane")


def test_scale_gate_blocks_naked_scaled_number():
    """Round-13: '1,200' for a 1.2B value with NO scale evidence anywhere must not bind; a section
    marker ('in millions'), an immediate scale tail ('1.2 billion'), or the full-magnitude print
    are each sufficient evidence."""
    naked = {'xbrls': [], 'texts': ['Segment alpha revenue 1,200 for the year'],
             'name': 'Segment Alpha Revenue', 'value': 1200000000, 'fmt': None, 'period': '2024-12-31'}
    assert locate.locate(naked)['hit'] is None
    marked = dict(naked, texts=['(in millions) Segment alpha revenue 1,200 for the year'])
    assert locate.locate(marked)['hit'] is not None
    tagged = dict(naked, texts=['Segment alpha revenue was 1.2 billion this year'])
    assert locate.locate(tagged)['hit'] is not None
    full = dict(naked, texts=['Segment alpha revenue 1,200,000,000 for the year'])
    assert locate.locate(full)['hit'] is not None
    print("[ok] bare scaled prints need scale evidence; tagged/full-magnitude self-evident")
