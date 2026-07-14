#!/usr/bin/env python3
"""Adapter (S2 Part D SUBMIT): harvest records -> ONE candidate-fact packet per SOURCE EVENT.

Reads a harvest tag's code_resolved.jsonl + abstain.jsonl (from run_code_tier.py) and:
  * groups gate-clean records by source_id -> one Block-0 envelope per source event, N raw items;
  * resolves the envelope (canonical source_id, source_type, event_time, fye_month, ticker);
  * routes every abstain to SKIP (terminal) or PARK (retry) per the frozen outcome map.
Emits ONLY raw FETCH signals -- NO decomposition (name/slice/measurement/unit/fiscal-quarter are
shared-core, added downstream). `build()` is pure (no Neo4j) so it is unit-tested directly.

    venv/bin/python scripts/driver_seed/build_packets.py --tag smoke
"""
import os, re, sys, json, argparse, collections
sys.path.insert(0, os.path.dirname(__file__))

OUT = 'data/driver_catalog_seed'
FORMMAP = {'10-K': '10k', '10-Q': '10q', '8-K': '8k'}
# frozen FETCH raw-item fields carried into each packet item (Part D FETCH list). Decomposition
# outputs (proposed_name/slice/measurement/time_type/fiscal_quarter/series_unit) are DELIBERATELY
# absent. concept/member are NOT top-level -- they live raw inside `xbrl` (no duplication).
ITEM_FIELDS = ('raw_label', 'value', 'fmt', 'is_currency', 'period_end', 'cadence',
               'quote', 'period_evidence', 'tier', 'quote_source', 'xbrl')


def canonicalize_source_id(s):
    return (s or '').replace(':', '_')


def unit_hints(fmt, is_currency):
    """Deterministic fmt/is_currency -> raw unit HINTS the shared resolver canonicalizes (D.2).
    Pure code, no semantic call; the decomposer refines (e.g. per-X -> price_like) and owns series_unit."""
    if fmt == '%':
        raw, kind = 'percent', 'ratio'
    elif is_currency:
        raw, kind = 'usd', 'money'
    else:
        raw, kind = 'count', 'count'
    return {'level_unit_raw': raw, 'level_unit_kind_hint': kind,
            'level_money_mode_hint': 'aggregate', 'level_shape_hint': 'point'}


def corpus_complete(searched, form):
    """The expected source set for a company-period was present AND searched: the named filing
    AND the earnings 8-K EX-99.1. Anything less = corpus-incomplete -> PARK, never a SKIP."""
    return FORMMAP.get(form) in (searched or []) and '8k' in (searched or [])


def build(records, abstains, fye_map):
    """Pure. Returns (packets, skip_ledger, park_ledger).
    packets: one per source event (source_id). skip/park: routed abstains with a machine reason."""
    packets = collections.OrderedDict()
    for r in records:
        sid = canonicalize_source_id(r['source_id'])
        pk = packets.get(sid)
        if pk is None:
            pk = packets[sid] = {'source_id': sid, 'source_type': r['source_type'],
                                 'ticker': r['ticker'], 'fye_month': fye_map.get(r['ticker']),
                                 'event_time': r.get('event_time'), 'items': []}
        item = {k: r[k] for k in ITEM_FIELDS if k in r}
        item.update(unit_hints(r.get('fmt'), r.get('is_currency')))
        pk['items'].append(item)

    skip, park = [], []
    for a in abstains:
        status, reason = a.get('status'), a.get('reason')
        led = {'ticker': a.get('ticker'), 'raw_label': a.get('raw_label') or a.get('kpi'),
               'period_end': a.get('period_end') or a.get('period'), 'form': a.get('form'), 'reason': reason}
        if status == 'skip':                             # derived / plug -> terminal, counted
            skip.append(led)
        elif reason == 'corpus_missing':                 # named filing not in graph yet
            park.append({**led, 'reason': 'corpus_missing'})
        elif status == 'value_absent':
            if corpus_complete(a.get('sources_searched'), a.get('form')):
                skip.append({**led, 'reason': 'value_absent_complete'})
            else:                                        # didn't search everything -> retry, don't skip
                park.append({**led, 'reason': 'corpus_incomplete'})
        else:
            park.append({**led, 'reason': reason or 'unknown'})
    return list(packets.values()), skip, park


def fetch_fye(session, tickers):
    rows = session.run("""MATCH (c:Company) WHERE c.ticker IN $t
                          RETURN c.ticker AS tk, c.fiscal_year_end_month AS m""", t=list(tickers)).data()
    return {r['tk']: r['m'] for r in rows}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--tag', required=True); a = ap.parse_args()
    pdir = f'{OUT}/{a.tag}'
    records = [json.loads(l) for l in open(f'{pdir}/code_resolved.jsonl')]
    abstains = [json.loads(l) for l in open(f'{pdir}/abstain.jsonl')] if os.path.exists(f'{pdir}/abstain.jsonl') else []
    tickers = {r['ticker'] for r in records} | {a.get('ticker') for a in abstains}
    tickers.discard(None)

    import run_code_tier as RC
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    with drv.session() as s:
        fye = fetch_fye(s, tickers)
    drv.close()

    packets, skip, park = build(records, abstains, fye)
    with open(f'{pdir}/packets.jsonl', 'w') as f:
        for p in packets: f.write(json.dumps(p) + '\n')
    with open(f'{pdir}/skip_ledger.jsonl', 'w') as f:
        for x in skip: f.write(json.dumps(x) + '\n')
    with open(f'{pdir}/park_ledger.jsonl', 'w') as f:
        for x in park: f.write(json.dumps(x) + '\n')
    items = sum(len(p['items']) for p in packets)
    by_src = collections.Counter(p['source_type'] for p in packets)
    print(json.dumps({'tag': a.tag, 'packets': len(packets), 'items': items, 'by_source': dict(by_src),
                      'skip': len(skip), 'park': len(park),
                      'fye_missing': sum(1 for p in packets if p['fye_month'] is None)}, indent=2))


if __name__ == '__main__':
    main()
