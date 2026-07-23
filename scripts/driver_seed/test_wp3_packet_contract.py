"""WP3 PACKET CONTRACT TEST (RED-first, 2026-07-23 — the reviewer's four ACI failures).

A compliant packet file must satisfy, for EVERY item:
  1. PRINTED VALUE: the value appears in the quote in a source-printed form under the
     existing exact Decimal comma/parenthesis law ('69690.4' matches '69,690.4';
     accounting negatives match parenthesized prints) — full magnitudes the source
     never printed (45600000 for '45.6 million') FAIL;
  2. XBRL EVIDENCE: an XBRL-proven item carries the element's verbatim ix evidence
     (scale / sign / unit_ref present under xbrl.ix);
  3. NO UNSUPPORTED PROSE: an item whose quote states a percentage must itself carry
     that printed evidence (a prose grab without it must have ABSTAINED instead);
  4. CHRONOLOGICAL: packets are ordered by ascending event_time.

    venv/bin/python -m pytest scripts/driver_seed/test_wp3_packet_contract.py -q
      (tag via WP3_TAG env; default = the compliant CE packet)
"""
import json
import os

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                     'data', 'driver_catalog_seed')
_BOTH = ('wp3_ce_compliant', 'wp3_aci_stream')     # BOTH outputs, always
_PATH = os.path.join(_DATA, 'wp3_aci_stream', 'packets.jsonl')


def _packets():
    for tag in _BOTH:
        for l in open(os.path.join(_DATA, tag, 'packets.jsonl')):
            yield json.loads(l)


def _printed_forms(v):
    # the existing exact Decimal comma/parenthesis law (locator._grp grouping)
    import sys as _s
    _s.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '..', '..', 'driver', 'relocation'))
    import locator as L
    s = str(v).lstrip('-')
    ip, dot, frac = s.partition('.')
    g = L._grp(ip) + dot + frac
    return {s, g, '(' + s + ')', '(' + g + ')'}


def test_printed_values_only():
    for p in _packets():
        for i in p['items']:
            q = i.get('quote') or ''
            assert any(f in q for f in _printed_forms(i['value'])), \
                f"{p['source_id']}: value {i['value']} is not the printed value"


def test_xbrl_items_carry_ix_evidence():
    for p in _packets():
        for i in p['items']:
            if i.get('xbrl'):
                ix = i['xbrl'].get('ix') or {}
                assert all(k in ix for k in ('scale', 'sign', 'unit_ref')), \
                    f"{p['source_id']}: XBRL item lacks scale/sign/unit evidence"


def test_no_unsupported_prose():
    for p in _packets():
        for i in p['items']:
            q = i.get('quote') or ''
            if '%' in q and not i.get('xbrl'):
                assert any(str(i.get(k, '')) and str(i[k]) in q
                           for k in ('stated_pct', 'printed_value')), \
                    f"{p['source_id']}: prose item states a % it never captured"


def test_packets_chronological():
    for tag in _BOTH:                                # chronology is PER package
        import datetime as _dt
        ts = [_dt.datetime.fromisoformat(json.loads(l)['event_time'])
              for l in open(os.path.join(_DATA, tag, 'packets.jsonl'))]
        assert ts == sorted(ts), f"{tag} not chronological: {ts}"   # parsed, not text


# ---- WP3 corrective pins (RED-first): no filtering · ordering · completeness ----

def _wp3():
    import wp3_compliant_packet as W
    return W


def test_ce_preserves_all_four_items():
    pks = _wp3().ce_packets()
    vals = sorted(str(i['value']) for p in pks for i in p['items'])
    assert vals == ['361', '390', '726', '778']      # no value filtering, ever


def test_aci_stream_complete_and_ordered():
    import json, os
    out = os.path.join(os.path.dirname(_PATH), '..', 'wp3_aci_stream')
    pks = [json.loads(l) for l in open(os.path.join(out, 'packets.jsonl'))]
    led = [json.loads(l) for l in open(os.path.join(out, 'no_match_ledger.jsonl'))]
    p4 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'relocate_probe', 'phase4', 'p4_event_ledger.jsonl')
    import datetime as _dtt
    truth = sorted(((e['source_id'], _dtt.datetime.fromisoformat(e['t']))
                    for e in (json.loads(l) for l in open(p4))
                    if e['ticker'] == 'ACI'))
    import datetime as _dt
    _p = _dt.datetime.fromisoformat
    got = sorted([(p['source_id'], _p(p['event_time'])) for p in pks]
                 + [(l['event'], _p(l['t'])) for l in led])
    assert got == truth and len(truth) == 18
    import datetime as _dt2
    ts = [_dt2.datetime.fromisoformat(p['event_time']) for p in pks]
    assert len(ts) >= 2 and ts == sorted(ts)         # PARSED aware datetimes, ascending


def test_cadence_item_by_item_fixed_truth():
    """ANTI-CIRCULAR + NO RULES: a hand-fixed, test-ONLY truth table — one row per
    distinct proven period, covering all 11 items — grades both the cadence AND
    the exact printed header evidence. No classifier, no shared table."""
    import json as _j
    TRUTH = {   # (source_id, period_start, period_end): (cadence, evidence)
        ('0001306830-24-000155', '2023-01-01', '2023-06-30'): ('Quarterly', 'Six Months Ended'),
        ('0001306830-24-000155', '2023-04-01', '2023-06-30'): ('Quarterly', 'Three Months Ended'),
        ('0001306830-24-000155', '2024-01-01', '2024-06-30'): ('Quarterly', 'Six Months Ended'),
        ('0001306830-24-000155', '2024-04-01', '2024-06-30'): ('Quarterly', 'Three Months Ended'),
        ('0001646972-23-000045', '2020-03-01', '2021-02-27'): ('Annual', '52 weeks ended'),
        ('0001646972-23-000045', '2021-02-28', '2022-02-26'): ('Annual', '52 weeks ended'),
        ('0001646972-23-000045', '2022-02-27', '2023-02-25'): ('Annual', '52 weeks ended'),
        ('0001646972-23-000056', '2022-02-27', '2022-06-18'): ('Quarterly', '16 weeks ended'),
        ('0001646972-23-000056', '2023-02-26', '2023-06-17'): ('Quarterly', '16 weeks ended'),
        ('0001646972-24-000165', '2023-02-26', '2023-06-17'): ('Quarterly', '16 weeks ended'),
        ('0001646972-24-000165', '2024-02-25', '2024-06-15'): ('Quarterly', '16 weeks ended'),
    }
    seen = 0
    for tag in _BOTH:
        for l in open(os.path.join(_DATA, tag, 'packets.jsonl')):
            p = _j.loads(l)
            for i in p['items']:
                cad, ev = TRUTH[(p['source_id'], i['xbrl']['period_start'],
                                 i['xbrl']['period_end'])]
                assert i['cadence'] == cad
                pieces = ' '.join(x['text'] for x in
                                  i['xbrl']['source_evidence']['pieces'])
                assert ev in pieces
                seen += 1
    assert seen == 11                        # every item graded, none skipped


def test_amendment_and_unknown_form_law():
    import route_a_source as SRC                     # the law lives in the SHARED adapter
    import pytest as _pt
    assert SRC.normalize_form('10-Q/A') == '10q'
    assert SRC.normalize_form('10-K/A') == '10k'
    assert SRC.normalize_form('10-Q') == '10q'
    assert SRC.normalize_form('8-K/A') == '8k'
    assert SRC.normalize_form('8k') == '8k'   # symmetric with '10q' (self-caught)
    with _pt.raises(ValueError):
        SRC.normalize_form('S-1')                    # unknown form: no source, fail closed
    with _pt.raises(ValueError):
        SRC.normalize_form(None)                     # MISSING form: never a silent 10q


def test_build_source_integration_no_bypass():
    """Through build_source() itself (his attack surface): the override is
    normalized; unknown/missing forms return None, never crash, never default."""
    import route_a_source as SRC
    CE = '0001306830-24-000155'
    s = SRC.build_source(CE, source_type='10-Q/A')
    assert s and s['source_type'] == '10q'           # override normalized
    assert SRC.build_source(CE, source_type='S-1') is None    # unknown -> None
    assert SRC.build_source(CE, source_type='') is None       # empty -> None
    s2 = SRC.build_source(CE)
    assert s2 and s2['source_type'] == '10q'         # graph form, normalized


def test_unknown_form_never_touches_the_fetcher():
    """His ordering attack, pinned: an unknown/missing form returns None BEFORE
    any cache/fetch access — the fetcher is called ZERO times. A positive control
    proves the counter wiring would catch a violation."""
    import route_a_source as SRC
    import lock_cell
    calls = []
    real = lock_cell.fetch_inline_html
    lock_cell.fetch_inline_html = lambda url, acc: (calls.append(acc), None)[1]
    try:
        class _Sess:
            def __init__(self, metas): self._m = metas
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def run(self, q, **kw):
                return list(self._m) if 'HAS_XBRL' in q else [{'dummy': 1}]
        class _Drv:
            def __init__(self, metas): self._m = metas
            def session(self): return _Sess(self._m)
            def close(self): pass
        meta_unknown = [{'url': 'u', 'form': 'S-1', 'cik': '1'}]
        meta_missing = [{'url': 'u', 'form': None, 'cik': '1'}]
        meta_valid = [{'url': 'u', 'form': '10-Q', 'cik': '1'}]
        assert SRC.build_source('NO-CACHE-1', driver=_Drv(meta_unknown)) is None
        assert SRC.build_source('NO-CACHE-2', driver=_Drv(meta_missing)) is None
        assert calls == []                   # ZERO fetch attempts on bad forms
        assert SRC.build_source('NO-CACHE-3', driver=_Drv(meta_valid)) is None
        assert calls == ['NO-CACHE-3']       # positive control: counter DOES fire
    finally:
        lock_cell.fetch_inline_html = real


def test_no_match_rows_carry_phase4_source_hash():
    import json as _j
    p4 = {r['source_id']: r['sha256'] for r in
          (_j.loads(l) for l in open(os.path.join(
              os.path.dirname(os.path.abspath(__file__)), 'relocate_probe',
              'phase4', 'p4_event_ledger.jsonl')))}
    led = [_j.loads(l) for l in open(os.path.join(
        _DATA, 'wp3_aci_stream', 'no_match_ledger.jsonl'))]
    assert led and all(l['p4_source_sha'] == p4[l['event']] for l in led)


def test_all_ledger_outcomes_abstain():
    import json as _j
    led = [_j.loads(l) for l in open(os.path.join(
        _DATA, 'wp3_aci_stream', 'no_match_ledger.jsonl'))]
    assert len(led) == 15 and all(l['result'] == 'no_proven_match' for l in led)


def test_packet_fields_survive_serialization():
    import json, os
    out = os.path.join(os.path.dirname(_PATH), '..', 'wp3_aci_stream')
    pks = [json.loads(l) for l in open(os.path.join(out, 'packets.jsonl'))]
    need = ('raw_label', 'value', 'quote', 'period_evidence', 'tier', 'xbrl',
            'period_end', 'cadence')                 # contract top-level fields
    for p in pks:
        for i in p['items']:
            assert all(k in i for k in need), sorted(set(need) - set(i))
            assert isinstance(i['value'], str)       # exact Decimal JSON string ("390")
            assert i['tier'] == 'T1-xbrl'            # FISCAL provenance label only
            ix = i['xbrl']['ix']
            assert all(k in ix for k in ('scale', 'sign', 'unit_ref'))
    ce = [json.loads(l) for l in
          open(os.path.join(_DATA, 'wp3_ce_compliant', 'packets.jsonl'))]
    for p in ce:
        for i in p['items']:
            assert all(k in i for k in need) and i['tier'] == 'T1-xbrl'
