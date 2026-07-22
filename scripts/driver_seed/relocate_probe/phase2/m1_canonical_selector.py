"""PHASE-2 CANONICAL PER-21 EVENT SELECTOR (read-only) — the canonical M1 source selection.

LAW (FINAL_DESIGN.md §6.2 PER-21 + ReviewRecord 2026-07-22): exactly TWO authorities,
both IMPORTED — never copied, never re-implemented — and BOTH PER-21 ROUTES:
  PAIRING (historical lane) = match_8k_to_periodic
      .claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py:411
  TRUST  = resolve_quarter_info (scripts/earnings/quarter_identity.py), supplying ONLY
      its AUTO_OK safety_action; its labels/projected dates are never join keys.
HISTORICAL-selected = lag-valid exact-accession pairing AND AUTO_OK.
LIVE-selected = AUTO_OK alone (PER-21's live route: before/without a timely target
10-Q/K, quarter_identity alone governs — reviewer correction 2026-07-22; run 1 of this
script wrongly parked 149 live-passing events whose only failure was a missing timely
companion). COMBINED corpus = historical ∪ live (= all AUTO_OK events; historical is a
subset because it also requires AUTO_OK). Everything else PARKS with an enumerated
reason. No third matcher: events the authorities' own queries do not cover (8-K/A,
missing ticker, resolver errors) are COUNTED and parked, never re-matched — verified:
BOTH authorities' queries match formType='8-K' exactly. Multiple 8-Ks may pair to one
periodic filing and remain separate events.

Output: m1_canonical_selection_final.jsonl (one row per (ticker, 8-K 2.02) event,
selected AND parked, each carrying historical_selected/live_selected/lane + full pairing
and trust state; ALL exhibits inventoried per COMBINED-selected event from
Report.exhibits) + EVENT counts printed separately from EXHIBIT counts. Run 1's
historical-lane-only output m1_canonical_selection.jsonl (sha 816b9f9f…) is PRESERVED
untouched as the historical-lane result. Shares the broad HTML cache by identical
acc__exhibit key; results are NEVER mixed with the broad stress manifest.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m1_canonical_selector.py
"""
import hashlib
import importlib.util
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
OUT = os.path.join(_HERE, 'm1_canonical_selection_final.jsonl')


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_ROOT, relpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# qi FIRST: its import inserts the skills scripts dir on sys.path, which gqf's
# own `from fiscal_math import ...` needs.
qi = _load('qi_authority', 'scripts/earnings/quarter_identity.py')
gqf = _load('gqf_authority',
            '.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py')

UNIVERSE_Q = (
    "MATCH (r:Report)-[:PRIMARY_FILER]->(c:Company) "
    "WHERE r.formType STARTS WITH '8-K' AND toString(r.items) CONTAINS '2.02' "
    "RETURN c.ticker AS ticker, r.accessionNo AS acc, r.formType AS form, "
    "r.exhibits AS ex, toString(r.created) AS filed "
    "ORDER BY ticker, filed, acc")


def _driver():
    from dotenv import dotenv_values
    from neo4j import GraphDatabase
    cfg = dotenv_values(os.path.join(_ROOT, '.env'))
    return GraphDatabase.driver(cfg['NEO4J_URI'],
                                auth=(cfg['NEO4J_USERNAME'], cfg['NEO4J_PASSWORD']))


def _exhibits_of(acc, ex_json):
    try:
        ex = json.loads(ex_json) or {}
    except (TypeError, ValueError):
        return []
    out = []
    for num, url in sorted(ex.items()):
        if not url:
            out.append({'num': num, 'url': url, 'ext': None,
                        'cls': 'missing_url', 'cached_broad': False})
            continue
        ext = url.rsplit('.', 1)[-1].lower()
        cls = ('pdf' if ext == 'pdf' else
               'html' if ext in ('htm', 'html') else
               'txt' if ext == 'txt' else 'other')
        cached = os.path.exists(
            os.path.join(CACHE, f'{acc}__{num}'.replace('/', '_') + '.htm'))
        out.append({'num': num, 'url': url, 'ext': ext,
                    'cls': cls, 'cached_broad': cached})
    return out


def main():
    t0 = time.time()
    drv = _driver()
    with drv.session() as s:
        uni = [dict(r) for r in s.run(UNIVERSE_Q)]

    rows_out = []
    in_scope = []
    for r in uni:
        if not r['ticker']:
            rows_out.append({'ticker': None, 'accession_8k': r['acc'],
                             'filed_8k': r['filed'], 'form_type_8k': r['form'],
                             'pairing': None, 'pairing_state': 'not_run',
                             'trust': None, 'historical_selected': False,
                             'live_selected': False, 'lane': None,
                             'selected': False, 'park_reason': 'no_ticker',
                             'exhibits': None})
        elif r['form'] != '8-K':
            # BOTH authorities' queries match formType = '8-K' exactly (verified in
            # source); amendments etc. are outside their scope — parked, never
            # re-matched, and neither lane can select them.
            rows_out.append({'ticker': r['ticker'], 'accession_8k': r['acc'],
                             'filed_8k': r['filed'], 'form_type_8k': r['form'],
                             'pairing': None, 'pairing_state': 'not_run',
                             'trust': None, 'historical_selected': False,
                             'live_selected': False, 'lane': None,
                             'selected': False,
                             'park_reason': 'authority_scope_formtype',
                             'exhibits': None})
        else:
            in_scope.append(r)

    by_ticker = {}
    for r in in_scope:
        by_ticker.setdefault(r['ticker'], []).append(r)
    tickers = sorted(by_ticker)
    print(f'universe {len(uni)} events · in-scope {len(in_scope)} '
          f'· tickers {len(tickers)}', flush=True)

    with drv.session() as s:
        for i, t in enumerate(tickers):
            matched = {m['accession_8k']: m
                       for m in gqf.match_8k_to_periodic(s, t, require_daily_stock=False)}
            for r in by_ticker[t]:
                m = matched.get(r['acc'])
                pairing = None
                if m is not None:
                    pairing = {'accession_periodic': m['accession_10q'],
                               'form_type': m['form_type'],
                               'period': str(m['period_10q']) if m['period_10q'] else None,
                               'lag_hours': m['lag_hours'],
                               'lag_valid': m['lag_valid']}
                pairing_ok = bool(m and m['accession_10q'] and m['lag_valid'])

                trust = None
                trust_ok = False
                try:
                    ti = qi.resolve_quarter_info(t, r['acc'])
                    trust = {'safety_action': ti['safety_action'],
                             'source': ti['quarter_identity_source'],
                             'quarter_label': ti['quarter_label']}
                    trust_ok = ti['safety_action'] == 'AUTO_OK'
                except Exception as e:  # fail-closed: resolver error parks the event
                    trust = {'error': type(e).__name__}

                hist_sel = pairing_ok and trust_ok
                live_sel = trust_ok  # PER-21 live route: AUTO_OK alone
                selected = hist_sel or live_sel
                lane = ('both' if hist_sel else 'live_only') if selected else None
                if selected:
                    reason = None
                elif trust is not None and 'error' in trust:
                    reason = 'trust_resolver_error'
                else:
                    reason = 'trust_not_auto_ok'
                if m is None:
                    p_state = 'matcher_missing'
                elif not m['accession_10q']:
                    p_state = 'no_companion'
                elif not m['lag_valid']:
                    p_state = 'lag_invalid'
                else:
                    p_state = 'paired_lag_valid'

                rows_out.append({'ticker': t, 'accession_8k': r['acc'],
                                 'filed_8k': r['filed'], 'form_type_8k': r['form'],
                                 'pairing': pairing, 'pairing_state': p_state,
                                 'trust': trust,
                                 'historical_selected': hist_sel,
                                 'live_selected': live_sel, 'lane': lane,
                                 'selected': selected, 'park_reason': reason,
                                 'exhibits': _exhibits_of(r['acc'], r['ex'])
                                 if selected else None})
            if (i + 1) % 25 == 0:
                print(f'tickers {i + 1}/{len(tickers)}', flush=True)
    drv.close()

    rows_out.sort(key=lambda x: (x['ticker'] or '', x['filed_8k'] or '',
                                 x['accession_8k']))
    with open(OUT, 'w') as f:
        for row in rows_out:
            f.write(json.dumps(row) + '\n')

    ev = {}
    p_st = {}
    for row in rows_out:
        ev[row['park_reason'] or 'selected'] = ev.get(row['park_reason'] or 'selected', 0) + 1
        p_st[row['pairing_state']] = p_st.get(row['pairing_state'], 0) + 1
    sel = [row for row in rows_out if row['selected']]
    lanes = {'historical_selected': sum(1 for r in rows_out if r['historical_selected']),
             'live_selected': sum(1 for r in rows_out if r['live_selected']),
             'both': sum(1 for r in sel if r['lane'] == 'both'),
             'live_only': sum(1 for r in sel if r['lane'] == 'live_only'),
             'combined_unique': len(sel)}
    acc_tickers = {}
    for row in rows_out:
        acc_tickers.setdefault(row['accession_8k'], set()).add(row['ticker'])
    multi = sum(1 for v in acc_tickers.values() if len(v) > 1)

    ex_counts = {'events_selected': len(sel), 'events_no_exhibits': 0,
                 'exhibits_total': 0, 'html': 0, 'pdf': 0, 'txt': 0,
                 'other': 0, 'missing_url': 0, 'html_cached_broad': 0,
                 'html_needs_fetch': 0}
    for row in sel:
        if not row['exhibits']:
            ex_counts['events_no_exhibits'] += 1
            continue
        for e in row['exhibits']:
            ex_counts['exhibits_total'] += 1
            ex_counts[e['cls']] += 1
            if e['cls'] == 'html':
                ex_counts['html_cached_broad' if e['cached_broad']
                          else 'html_needs_fetch'] += 1

    sha = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps({
        'EVENTS': {'universe_ticker_event_rows': len(rows_out),
                   'distinct_accessions': len(acc_tickers),
                   'multi_ticker_accessions': multi, 'lanes': lanes,
                   'pairing_states': p_st, 'outcomes': ev},
        'EXHIBITS_combined_selected_events_only': ex_counts,
        'output': OUT, 'output_sha256': sha,
        'secs': round(time.time() - t0)}, indent=1), flush=True)
    print('CANONICAL-SELECTOR-DONE', flush=True)


if __name__ == '__main__':
    main()
