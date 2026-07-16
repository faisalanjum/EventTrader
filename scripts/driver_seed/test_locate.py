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


def test_value_known_finds_the_xbrl_quote():
    # value in hand -> find WHERE it's written (returns a 'hit' with the quote + raw xbrl block).
    r = locate.locate({'xbrls': [_AGG_BLOB], 'texts': [], 'name': 'Total Revenue',
                       'value': 6707000000, 'fmt': None, 'period': '2024-12-31'})
    assert r['hit'] is not None and r['hit']['tier'] == 'T1-xbrl', r
    assert r['hit']['xbrl']['concept'] == _CONCEPT


def test_value_unknown_resolves_the_value():
    # fingerprint only (no number) -> find the value (returns a 'value').
    r = locate.locate({'xbrls': [_AGG_BLOB], 'concept': _CONCEPT, 'members': [],
                       'period_start': '2024-01-01', 'period_end': '2024-12-31'})
    assert r['value'] == 6707000000, r


def test_dispatch_by_presence_of_value():
    vk = locate.locate({'xbrls': [_AGG_BLOB], 'texts': [], 'name': 'Total Revenue',
                        'value': 6707000000, 'fmt': None, 'period': '2024-12-31'})
    vu = locate.locate({'xbrls': [_AGG_BLOB], 'concept': _CONCEPT, 'members': [],
                        'period_start': '2024-01-01', 'period_end': '2024-12-31'})
    assert 'hit' in vk and 'value' in vu   # value present -> value-known; absent -> value-unknown
