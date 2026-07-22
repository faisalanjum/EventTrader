"""Adapter proof: REAL graph facts + REAL cached filing, end-to-end through locate().

    venv/bin/python -m pytest scripts/driver_seed/test_route_a_source.py -q
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', '..', 'driver', 'relocation'))
import locator as LOC
import route_a_source as SRC


def test_adapter_builds_real_ce_source_and_locate_binds():
    s = SRC.build_source('0001306830-24-000155')
    if s is None:
        raise AssertionError('cached CE filing or its graph facts unavailable')
    assert s['inline_html'] and s['xbrls'] and s['texts'] == []
    anchor = {"source_id": "SYN-PRIOR", "company": "C1", "driver": "revenue",
              "slice": "segment:acetyl_chain", "measurement": "",
              "series_unit": "m_usd", "time_type": "duration",
              "fact_type": "metric", "wording": ("North America",),
              "concept_clue": "RevenueFromContractWithCustomerExcludingAssessedTax"}
    r = LOC.locate(anchor, s)
    assert r['status'] is None and r['items'], r['status']
    vals = {str(i['value']) for i in r['items']}
    assert '390' in vals, vals
    it = [i for i in r['items'] if str(i['value']) == '390'][0]
    assert 'North America' in it['quote']
    assert it['xbrl']['period_end'] == '2024-06-30'
    assert 'unit_meaning' not in it and 'source_sha256' not in it


def test_adapter_fetches_on_miss_and_fails_closed_on_unknown():
    s = SRC.build_source('0000071691-24-000160')     # one of the 4 uncached gate
    if s is not None:                                # filings: fetch-on-miss law
        assert s['inline_html'] and s['raw_sha256']
    assert SRC.build_source('0000000000-00-000000') is None


def test_metadata_fail_closed_on_duplicates_or_missing():
    class _Sess:
        def __init__(self, metas):
            self._m = metas
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def run(self, q, **kw):
            return list(self._m) if 'HAS_XBRL' in q else []
    class _Drv:
        def __init__(self, metas):
            self._m = metas
        def session(self):
            return _Sess(self._m)
        def close(self):
            pass
    assert SRC.build_source('X', driver=_Drv([])) is None, "zero metas -> None"
    two = [{'url': 'u', 'form': '10-Q', 'cik': '1'},
           {'url': 'u2', 'form': '10-Q', 'cik': '2'}]
    assert SRC.build_source('X', driver=_Drv(two)) is None, \
        "duplicate Report/Company results must ABSTAIN, never silently pick one"


def _mk_packets(acc, ticker, anchor_overrides, concept):
    import build_packets as BP
    s = SRC.build_source(acc)
    anchor = {"source_id": "P", "company": "C", "driver": "d", "slice": "",
              "measurement": "", "series_unit": "m_usd", "time_type": "duration",
              "fact_type": "metric", "wording": ("x",), "concept_clue": concept}
    anchor.update(anchor_overrides)
    r = LOC.locate(anchor, s)
    recs = []
    for it in r['items']:
        rec = dict(it)
        rec.update({'source_id': s['source_id'], 'source_type': s['source_type'],
                    'ticker': ticker, 'fmt': 'number', 'is_currency': True})
        recs.append(rec)
    packets, _, _ = BP.build(recs, [], {ticker: 12})
    return packets


def test_production_jsonl_write_read_exact_decimals(tmp_path):
    import build_packets  # noqa: F401  (the layer under test)
    sys.path.insert(0, _HERE)
    ce = _mk_packets('0001306830-24-000155', 'CE',
                     {'wording': ('North America',),
                      'slice': 'segment:acetyl_chain'},
                     'RevenueFromContractWithCustomerExcludingAssessedTax')
    dal = _mk_packets('0000027904-23-000006', 'DAL',
                      {'series_unit': 'usd', 'wording': ('per share',)},
                      'EarningsPerShareBasic')
    packets = ce + dal
    assert packets and all(p['items'] for p in packets)
    path = str(tmp_path / 'packets.jsonl')
    import json
    import build_packets as BP
    BP.write_jsonl(packets, path)                     # THE one shared writer
    back = [json.loads(l) for l in open(path, encoding='utf-8')]
    flat = {(p['ticker'], str(i['value'])): i
            for p in back for i in p['items'] for p2 in [p]}
    from decimal import Decimal
    ce_i = flat[('CE', '390')]
    dal_i = flat[('DAL', '-0.57')]
    assert Decimal(ce_i['value']) == Decimal('390')
    assert Decimal(dal_i['value']) == Decimal('-0.57'), "sign survives exactly"
    for it, scale, unit in ((ce_i, 6, 'usd'), (dal_i, 0, 'usdPerShare')):
        assert it['xbrl']['ix']['scale'] == scale
        assert it['xbrl']['ix']['unit_ref'] == unit
        assert 'sign' in it['xbrl']['ix'] and 'format' in it['xbrl']['ix']
        assert it['quote'] and it['period_evidence'] == it['quote']
        assert it['xbrl']['axis_members'] is not None
        assert it['xbrl']['period_start'] and it['xbrl']['period_end']
    assert [tuple(x) for x in
            ce_i['xbrl']['axis_members']] == [
        ('srt:StatementGeographicalAxis', 'srt:NorthAmericaMember'),
        ('us-gaap:StatementBusinessSegmentsAxis', 'ce:AcetylChainMember')], \
        "exact dimensions survive serialization"
    import inline_html as IH2
    html = open(os.path.join(_HERE, 'relocate_probe', 'inline_html_cache',
                             '0001306830-24-000155.htm'),
                encoding='utf-8', errors='replace').read()
    prep = IH2.prepare(html)
    se = ce_i['xbrl']['source_evidence']
    assert se['representation_sha256'] == prep['text_sha']
    qa, qb = se['quote_span']
    assert prep['text'][qa:qb] == ce_i['quote'], \
        "the quote span reproduces the representation AFTER write/read"
    assert se['pieces'] and all(
        prep['text'][p2['span'][0]:p2['span'][1]] == p2['text']
        for p2 in se['pieces']), "every nested piece survives serialization"
