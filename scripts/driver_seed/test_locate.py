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
    {"value": "6707000000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"}}]})
_CONCEPT = "RevenueFromContractWithCustomerExcludingAssessedTax"


def test_value_known_finds_the_printed_quote():
    # value in hand -> find WHERE it is PRINTED. The raw xbrl block rides along as evidence, but the QUOTE
    # must always be text a human wrote. (This test previously asserted a hit with NO text at all, which was
    # only reachable via the fabricated XBRL-metadata quote — it was pinning the bug.)
    r = locate.locate({'xbrls': [_AGG_BLOB], 'texts': ['Total revenue 6,707 for the year'],
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


def test_dispatch_by_presence_of_value():
    vk = locate.locate({'xbrls': [_AGG_BLOB], 'texts': [], 'name': 'Total Revenue',
                        'value': 6707000000, 'fmt': None, 'period': '2024-12-31'})
    vu = locate.locate({'xbrls': [_AGG_BLOB], 'concept': _CONCEPT, 'members': [],
                        'period_start': '2024-01-01', 'period_end': '2024-12-31'})
    assert 'hit' in vk and 'value' in vu   # value present -> value-known; absent -> value-unknown
