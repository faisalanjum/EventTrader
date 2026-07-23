"""PHASE-4 CHRONOLOGICAL DRY RUN — v2 (reviewer Phase-4 corrective, 2026-07-22).

ONE publication-time replay of 7 of the 10 WP1 companies (the 8-K-qualified subset:
AA AAL ABT ACI ADM AEE AFL). LAW: process every source at its real publication time;
NEVER assume which source type arrives first (5 paired periodics really published
before their 8-K — recorded in pair_timing). Reader OFF; Routes B/C absent; graph
READ-ONLY; zero Core imports; nothing emitted (anchors are Phase-5 Core property).

v2 over v1 (his findings, all reproduced first):
  * COMPLETE 8-K source events (Design law): exhibits (cached original HTML) + stored
    sections + filing text, exact-string deduped like the code-tier builder;
  * deterministic hashes for EVERY source part (exact stored string / file bytes) +
    parent manifest hashes (sha over sorted part shas);
  * REAL access audit: every content read is logged against the replay clock;
  * REAL retry: the two parked WP1 items run the actual code tier at their arrival
    events under the new as_of cutoff; final outcomes recorded;
  * honest labels (component reconciliation coverage; 7-of-10 universe; AAL gap).

    venv/bin/python scripts/driver_seed/relocate_probe/phase4/p4_dry_run.py
"""
import datetime
import hashlib
import json
import math
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROBE = os.path.abspath(os.path.join(_HERE, '..'))
_P2 = os.path.join(_PROBE, 'phase2')
_SEED = os.path.abspath(os.path.join(_PROBE, '..'))
_ROOT = os.path.abspath(os.path.join(_SEED, '..', '..'))
for p in (_ROOT, _SEED, _PROBE, _P2, _HERE):
    sys.path.insert(0, p)

import m4_reader_residual as M4                     # scan(), real caps
import route_a_component_census as CEN              # work() — the Route-A leg
import run_code_tier as RC                          # the code tier + as_of selector
import build_packets as BP                          # corpus_complete routing law
from m1_canonical_selector import _driver
from m1_transcript_census import NUM, spoken_text

TICKERS = ('AA', 'AAL', 'ABT', 'ACI', 'ADM', 'AEE', 'AFL')
SELECTION = os.path.join(_P2, 'm1_canonical_selection_final.jsonl')
EX_CACHE = os.path.join(_PROBE, 'exhibit_html_cache')
INLINE_CACHE = os.path.join(_PROBE, 'inline_html_cache')
WP1_DIR = os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'wp1')
LEDGER_OUT = os.path.join(_HERE, 'p4_event_ledger.jsonl')
REPORT_OUT = os.path.join(_HERE, 'p4_dry_run_report.json')

_META_Q = """MATCH (x:XBRLNode {accessionNo:$acc})<-[:HAS_XBRL]-(r:Report)
RETURN x.id AS url, r.formType AS form, r.created AS created"""
_PARTS_Q = """MATCH (r:Report {accessionNo:$acc})
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(sx:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN collect(DISTINCT e.content) AS ex, collect(DISTINCT sx.content) AS secs,
       collect(DISTINCT f.content) AS fts"""

ACCESS = []          # the real access log: every content read vs the replay clock


class PITOrderError(Exception):
    """A stream (or retry arrival) violated public-time order."""


def _t(iso):
    return datetime.datetime.fromisoformat(iso)


def _sha(data):
    return hashlib.sha256(data if isinstance(data, bytes)
                          else data.encode('utf-8')).hexdigest()


def _touch(event_sid, event_t, accessed_sid, accessed_t):
    ACCESS.append({'event': event_sid, 'event_t': event_t,
                   'accessed': accessed_sid, 'accessed_t': accessed_t})


def check_order(events):
    """The strict clock: refuse ANY regression in public time (ties allowed)."""
    prev = None
    for e in events:
        if prev is not None and _t(e['t']) < _t(prev['t']):
            raise PITOrderError(
                f"out-of-order event {e['source_id']} at {e['t']} after {prev['t']}")
        prev = e


def chunk_law(chars):
    return 0 if not chars else math.ceil(chars / M4.MAX_CHARS)


def manifest_8k_file(source_id, path):
    """SOURCE-LOCAL manifest row for one 8-K exhibit file (original HTML bytes)."""
    body = open(path, 'rb').read()
    rec = M4.scan(path) or {}
    row = {'source_id': source_id, 'sha256': _sha(body),
           'evidence_source_ids': [source_id]}
    for k in ('visible_chars', 'prose_struct_numeric_blocks',
              'prose_struct_numeric_chars', 'table_rows_numeric',
              'table_row_chars', 'strict_table_row_chars', 'doc_chunks'):
        row[k] = rec.get(k)
    return row


def retry_transition(park, event, origin_t):
    """PIT §7: transition ONLY when the awaited (ticker, form, period) source arrives
    STRICTLY LATER than the park origin."""
    if (event.get('kind') != 'periodic' or event.get('ticker') != park['ticker']
            or event.get('form') != park['form']
            or event.get('period') != park['period_end']):
        return None
    if _t(event['t']) <= _t(origin_t):
        raise PITOrderError(
            f"retry arrival {event['t']} not strictly later than origin {origin_t}")
    return {'item_id': park['item_id'], 'ticker': park['ticker'],
            'raw_label': park.get('raw_label'), 'awaited_form': park['form'],
            'period_end': park['period_end'], 'park_reason': park.get('reason'),
            'origin_t': origin_t, 'arrived_at': event['t'],
            'arrival_source': event['source_id']}


def leakage_sweep(ledger, times):
    """Manifest-evidence locality check (structural); the ACCESS AUDIT below is the
    behavioural proof — it checks what the code actually read."""
    viol = []
    for row in ledger:
        for cited in row.get('evidence_source_ids', []):
            if cited != row['source_id']:
                viol.append({'row_source': row['source_id'], 'cited': cited,
                             'future': _t(times[cited]) > _t(row['t'])
                             if cited in times else None})
    return viol


def access_audit(access):
    """The behavioural no-future-read proof: every logged content access must carry
    accessed_t <= event_t. Returns violations."""
    return [a for a in access
            if a['accessed_t'] and _t(str(a['accessed_t'])) > _t(a['event_t'])]


def real_retry(session, item_id, ev):
    """Run the ACTUAL code tier for one parked item at its arrival event, as_of =
    the arrival's replay clock. The item is the ORIGINAL worklist.jsonl row (exact
    _iid match required — every field verbatim, incl. tag/is_currency); the outcome
    is routed by the REAL build_packets.build(), not a hand-rolled copy."""
    wl = [json.loads(l) for l in
          open(os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'worklist.jsonl'))]
    hits = [r for r in wl if RC._iid(r) == item_id]
    assert len(hits) == 1, f'worklist row for {item_id}: {len(hits)} hits'
    it = hits[0]
    filing = RC.fetch_filing(session, it['ticker'], it['form'], it['period'])
    if filing is None:
        return {'disposition': 'parked_corpus_missing', 'real_retry': True}
    assert str(filing['event_time']) <= ev['t'], 'arrived filing after replay clock'
    _touch(ev['source_id'], ev['t'], filing['source_id'], str(filing['event_time']))
    prs, uncertain, audit = RC.fetch_earnings_8ks(
        session, it['ticker'], filing['source_id'], as_of=ev['t'])
    for p in prs:
        _touch(ev['source_id'], ev['t'], p['source_id'], str(p['event_time']))
    resolved, _resid, abstain = RC.process_cp([it], filing, prs,
                                              sources_incomplete=uncertain > 0)
    _pk, skip, park = BP.build(resolved, abstain, {})
    if resolved:
        disp = 'resolved'
    elif skip:
        assert skip[0]['item_id'] == item_id
        disp = skip[0]['reason']
    else:
        assert park and park[0]['item_id'] == item_id
        disp = 'parked_' + park[0]['reason']
    return {'disposition': disp, 'real_retry': True,
            'as_of': ev['t'], 'filing_searched': filing['source_id'],
            'accepted_8k_events_searched': len(prs),
            'excluded_after_as_of': sum(1 for x in audit
                                        if x['verdict'] == 'excluded_after_as_of'),
            'uncertain_8ks': uncertain}


def build_stream(session):
    sel = [json.loads(l) for l in open(SELECTION)]
    rows = [r for r in sel if r['ticker'] in TICKERS and r.get('selected')]
    ex_files = sorted(os.listdir(EX_CACHE))
    events, periodics = [], {}
    for r in rows:
        acc = r['accession_8k']
        events.append({'kind': '8k', 'ticker': r['ticker'], 'source_id': acc,
                       't': r['filed_8k'],
                       'exhibit_files': [f for f in ex_files
                                         if f.startswith(acc + '__')]})
        p = r['pairing']
        periodics.setdefault(p['accession_periodic'],
                             {'ticker': r['ticker'], 'form': p['form_type'],
                              'period': p['period']})
    for acc, meta in periodics.items():
        got = session.run(_META_Q, acc=acc).single()
        events.append({'kind': 'periodic', 'ticker': meta['ticker'],
                       'source_id': acc, 't': got['created'], 'form': meta['form'],
                       'period': meta['period'], 'url': got['url']})
    for t in session.run(
            "MATCH (t:Transcript) WHERE t.symbol IN $tk RETURN t.symbol AS ticker, "
            "t.id AS id, t.conference_datetime AS cd", tk=list(TICKERS)):
        events.append({'kind': 'transcript', 'ticker': t['ticker'],
                       'source_id': t['id'], 't': t['cd']})
    events.sort(key=lambda e: (_t(e['t']), e['kind'], e['source_id']))
    pair_timing = []
    ptimes = {e['source_id']: e['t'] for e in events if e['kind'] == 'periodic'}
    for r in rows:
        pa = r['pairing']['accession_periodic']
        if pa in ptimes:
            dh = (_t(ptimes[pa]) - _t(r['filed_8k'])).total_seconds() / 3600
            pair_timing.append({'ticker': r['ticker'], 'acc_8k': r['accession_8k'],
                                'lane': r['lane'], 'periodic': pa,
                                'delta_hours': round(dh, 1), 'inverted': dh < 0,
                                'stale_live_pairing': dh < 0
                                and r['lane'] == 'live_only'})
    return events, pair_timing


def process_8k(session, ev):
    """COMPLETE source event: cached exhibit HTML (structure lanes) + stored sections
    + filing text (whole-part text lanes), exact-string deduped like the builder."""
    ex_rows = []
    for f in ev['exhibit_files']:
        _touch(ev['source_id'], ev['t'], f, ev['t'])
        ex_rows.append(manifest_8k_file(f, os.path.join(EX_CACHE, f)))
    got = session.run(_PARTS_Q, acc=ev['source_id']).single()
    _touch(ev['source_id'], ev['t'], ev['source_id'], ev['t'])
    seen = {c for c in (got['ex'] or []) if c}
    parts, dropped = [], 0
    for lane, texts in (('8k_section', got['secs']), ('8k_filing_text', got['fts'])):
        for c in texts or []:
            if not c:
                continue
            if c in seen:
                dropped += 1
                continue
            seen.add(c)
            numeric = bool(NUM.search(c))
            parts.append({'lane': lane, 'sha256': _sha(c), 'chars': len(c),
                          'numeric': numeric,
                          'numeric_chars': len(c) if numeric else 0,
                          'chunks': chunk_law(len(c)) if numeric else 0})
    manifest = sorted([e['sha256'] for e in ex_rows] + [p['sha256'] for p in parts])
    return {'t': ev['t'], 'kind': '8k', 'ticker': ev['ticker'],
            'source_id': ev['source_id'],
            'evidence_source_ids': [ev['source_id']],
            'sha256': _sha('\n'.join(manifest)), 'exhibits': ex_rows,
            'parts': parts, 'dedup_dropped': dropped}


def process_transcript(session, ev):
    """Exact-source part hashes (RAW stored strings, sha-sorted manifest) + the
    numeric census (spoken_text law, separate from hashing)."""
    row = {'source_id': ev['source_id'], 'evidence_source_ids': [ev['source_id']]}
    part_shas = []
    for lane, cy in (('prepared', "MATCH (t:Transcript {id:$id})-"
                      "[:HAS_PREPARED_REMARKS]->(x) RETURN x.content AS c"),
                     ('qa', "MATCH (t:Transcript {id:$id})-"
                      "[:HAS_QA_EXCHANGE]->(x) RETURN x.exchanges AS c")):
        blocks = numeric_blocks = chars = 0
        for rec in session.run(cy, id=ev['source_id']):
            raw = rec['c']
            if raw is None:
                continue
            blocks += 1
            part_shas.append(_sha(raw))
            text = spoken_text(raw)
            if text and NUM.search(text):
                numeric_blocks += 1
                chars += len(text)
        row[f'{lane}_blocks'] = blocks
        row[f'{lane}_numeric_blocks'] = numeric_blocks
        row[f'{lane}_numeric_chars'] = chars
    _touch(ev['source_id'], ev['t'], ev['source_id'], ev['t'])
    row['part_shas'] = sorted(part_shas)
    row['sha256'] = _sha('\n'.join(row['part_shas']))
    total = row['prepared_numeric_chars'] + row['qa_numeric_chars']
    row['doc_chunks'] = max(1, chunk_law(total)) if total else 0
    return row


def process_periodic(session, ev):
    path = os.path.join(INLINE_CACHE, ev['source_id'] + '.htm')
    fetched = False
    if not os.path.exists(path):
        from lock_cell import fetch_inline_html
        path = fetch_inline_html(ev['url'], ev['source_id'])
        fetched = True
        if not path:
            return {'source_id': ev['source_id'], 'sha256': None,
                    'evidence_source_ids': [ev['source_id']],
                    'fetch_failed': True, 'fetched_once': True}
    body = open(path, 'rb').read()
    _touch(ev['source_id'], ev['t'], ev['source_id'], ev['t'])
    _acc, buckets, err = CEN.work(path)
    return {'source_id': ev['source_id'], 'sha256': _sha(body),
            'evidence_source_ids': [ev['source_id']],
            'fetched_once': fetched, 'file_error': err or None,
            'buckets': dict(buckets)}


def main():
    park = [json.loads(l) for l in open(os.path.join(WP1_DIR, 'park_ledger.jsonl'))]
    drv = _driver()
    CEN._drv = drv
    with drv.session() as session:
        events, pair_timing = build_stream(session)
        check_order(events)
        try:
            check_order(list(reversed(events)))
            attack = 'NOT REFUSED — WRONG RESULT'
        except PITOrderError as e:
            attack = f'REFUSED ({e})'

        sel = [json.loads(l) for l in open(SELECTION)]
        origin = {}
        for p in park:
            cands = [r['filed_8k'] for r in sel
                     if r['ticker'] == p['ticker'] and r.get('selected')
                     and r['pairing'].get('period') == p['period_end']
                     and r['pairing'].get('form_type') == p['form']]
            origin[p['item_id']] = min(cands) if cands else None

        times, ledger, transitions = {}, [], []
        counts = Counter()
        for ev in events:
            counts[ev['kind']] += 1
            times[ev['source_id']] = ev['t']
            if ev['kind'] == '8k':
                r = process_8k(session, ev)
                for e in r['exhibits']:
                    times[e['source_id']] = ev['t']
                ledger.append(r)
            elif ev['kind'] == 'transcript':
                r = process_transcript(session, ev)
                ledger.append({'t': ev['t'], 'kind': 'transcript',
                               'ticker': ev['ticker'], **r})
            else:
                r = process_periodic(session, ev)
                ledger.append({'t': ev['t'], 'kind': 'periodic',
                               'ticker': ev['ticker'], 'form': ev['form'],
                               'period': ev['period'], **r})
                for p in park:
                    if p['item_id'] not in {x['item_id'] for x in transitions} \
                            and origin.get(p['item_id']):
                        tr = retry_transition(p, ev, origin[p['item_id']])
                        if tr:
                            tr.update(real_retry(session, p['item_id'], ev))
                            transitions.append(tr)

        viol = leakage_sweep(
            ledger + [dict(e, t=r['t']) for r in ledger
                      for e in r.get('exhibits', [])], times)
        aviol = access_audit(ACCESS)

    agg8, aggL = Counter(), {'8k_section': Counter(), '8k_filing_text': Counter()}
    for r in ledger:
        if r['kind'] == '8k':
            for e in r['exhibits']:
                for k in ('prose_struct_numeric_blocks', 'prose_struct_numeric_chars',
                          'table_rows_numeric', 'table_row_chars',
                          'strict_table_row_chars', 'doc_chunks'):
                    agg8[k] += e.get(k) or 0
                agg8['files'] += 1
            agg8['dedup_dropped'] += r['dedup_dropped']
            for p in r['parts']:
                c = aggL[p['lane']]
                c['parts'] += 1
                c['chars'] += p['chars']
                c['numeric_parts'] += 1 if p['numeric'] else 0
                c['numeric_chars'] += p['numeric_chars']
                c['chunks'] += p['chunks']
    aggT = Counter()
    for r in ledger:
        if r['kind'] == 'transcript':
            for k in ('prepared_blocks', 'prepared_numeric_blocks',
                      'prepared_numeric_chars', 'qa_blocks', 'qa_numeric_blocks',
                      'qa_numeric_chars', 'doc_chunks'):
                aggT[k] += r.get(k) or 0
    aggP, fetched, ferr = Counter(), 0, []
    for r in ledger:
        if r['kind'] == 'periodic':
            fetched += 1 if r.get('fetched_once') else 0
            if r.get('fetch_failed') or r.get('file_error'):
                ferr.append(r['source_id'])
            for k, v in (r.get('buckets') or {}).items():
                aggP[k] += v

    gaps = [{'source_id': r['source_id'], 'ticker': r['ticker'],
             'prepared_blocks': r['prepared_blocks'], 'qa_blocks': r['qa_blocks']}
            for r in ledger if r['kind'] == 'transcript'
            and r['prepared_blocks'] == 0]
    final_park = []
    for p in park:
        tr = next((t for t in transitions if t['item_id'] == p['item_id']), None)
        final_park.append({'item_id': p['item_id'], 'ticker': p['ticker'],
                           **({'disposition': tr['disposition'], 'real_retry': True,
                               'as_of': tr['as_of']} if tr else
                              {'disposition':
                               'still_parked_awaited_source_not_in_replay_window',
                               'real_retry': False})})

    packed = 0                     # pack the SAME measured text by complete source
    for r in ledger:               # (per-part 533 is an upper bound; exact final
        if r['kind'] == '8k':      # packing = Phase 6's certified block builder)
            ev_chars = sum((e.get('prose_struct_numeric_chars') or 0)
                           + (e.get('table_row_chars') or 0) for e in r['exhibits'])
            ev_chars += sum(p_['numeric_chars'] for p_ in r['parts'])
            packed += chunk_law(ev_chars) if ev_chars else 0
    packed += aggT['doc_chunks']
    total_chunks = (agg8['doc_chunks'] + aggL['8k_section']['chunks']
                    + aggL['8k_filing_text']['chunks'] + aggT['doc_chunks'])
    acc_path = os.path.join(_HERE, 'p4_access_ledger.jsonl')
    with open(acc_path, 'w') as f:
        for a in ACCESS:
            f.write(json.dumps(a) + '\n')
    acc_sha = _sha(open(acc_path, 'rb').read())
    report = {
        'label': ('PHASE-4 CHRONOLOGICAL DRY RUN v2 (reader OFF, read-only, '
                  'no Core; publication-time law — no assumed source-type order)'),
        'universe': {'tickers': list(TICKERS),
                     'note': ('7 of the 10 WP1 companies — the 8-K-qualified '
                              'subset (m2_wp1_8k_qualification); A, AAPL, ACN '
                              'have no qualified 8-K records'),
                     'events': dict(counts), 'total_events': sum(counts.values()),
                     'span': [ledger[0]['t'], ledger[-1]['t']] if ledger else None},
        'pair_timing': pair_timing,
        'transcript_gaps': gaps,
        'pit': {'order_check_real_stream': 'PASS',
                'order_attack_reversed_stream': attack,
                'leakage_sweep': {'rows_swept': len(ledger) + agg8['files'],
                                  'violations': viol},
                'source_access_audit': {
                    'note': ('SOURCE-level access granularity (one row per '
                             'source read per event), persisted for independent '
                             'reproduction'),
                    'rows': len(ACCESS), 'ledger': 'p4_access_ledger.jsonl',
                    'ledger_sha256': acc_sha, 'violations': aviol}},
        'route_a_leg': {'filings': counts['periodic'], 'fetched_once': fetched,
                        'fetch_or_file_errors': ferr,
                        'component_reconciliation_coverage':
                            round(aggP.get('reconcile_ok', 0)
                                  / max(1, aggP.get('facts', 1)), 4),
                        'note': ('component reconciliation coverage — NOT '
                                 'precision/recall; nothing was emitted'),
                        'buckets': dict(aggP)},
        'actual_reader_residual': {
            'note': ('reader-off volume at the real caps (MAX_CASES='
                     f'{M4.MAX_CASES}, MAX_CHARS={M4.MAX_CHARS}); COMPLETE 8-K '
                     'source events: exhibits + stored sections + filing text, '
                     'exact-string deduped like the code-tier builder'),
            '8k_exhibits': dict(agg8),
            '8k_sections': dict(aggL['8k_section']),
            '8k_filing_text': dict(aggL['8k_filing_text']),
            'transcripts': dict(aggT),
            'chunks_per_part_upper_bound': total_chunks,
            'chunks_packed_by_source': packed,
            'packing_note': ('per-part rounding makes the upper bound; packing '
                             'the same measured text by complete source gives '
                             'the lower figure; 12 filing-text records nest '
                             'already-represented exhibit content (substring, '
                             'not exact-string) — exact final packing deferred '
                             'to Phase 6\'s certified source-block builder')},
        'retry': {'parked_items': len(park), 'transitions': transitions,
                  'final_dispositions': final_park}}
    with open(LEDGER_OUT, 'w') as f:
        for r in ledger:
            f.write(json.dumps(r) + '\n')
    json.dump(report, open(REPORT_OUT, 'w'), indent=1)
    print(json.dumps({'events': dict(counts), 'attack': attack[:30],
                      'leak_violations': len(viol), 'access_violations': len(aviol),
                      'inverted_pairs': sum(1 for x in pair_timing if x['inverted']),
                      'retry': [(t['item_id'], t['disposition'])
                                for t in transitions],
                      'chunks_upper_bound': total_chunks, 'chunks_packed': packed}, indent=1))
    drv.close()


if __name__ == '__main__':
    main()
