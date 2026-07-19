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
