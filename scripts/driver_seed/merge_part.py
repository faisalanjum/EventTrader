#!/usr/bin/env python3
"""Assemble a part's final seed records: code-tier + LLM-tier, with the deterministic value gate
applied to BOTH. Any record whose exact value is not literally present in its quote (at a numeric
boundary, losslessly) is dropped to abstain — this catches source-vs-filing value drift that the
LLM verifier can talk itself past.

    venv/bin/python scripts/driver_seed/merge_part.py --part 1 --llm-output <task_output.json>

writes data/driver_catalog_seed/part<N>/seed_records.jsonl (+ merge_summary.json)
"""
import json, argparse, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
import link_lib as L

OUT = 'data/driver_catalog_seed'


def load_llm_records(path, batches):
    raw = json.loads(open(path).read())
    res = raw['result'] if isinstance(raw, dict) and 'result' in raw else raw
    if isinstance(res, str):
        res = json.loads(res)
    recs = res.get('records', []) if isinstance(res, dict) else []
    out = []
    for r in recs:
        b = batches[r['batch']]
        km = {k['kpi']: k for k in b['kpis']}
        kk = km.get(r['kpi'])
        if not kk:
            continue
        out.append({
            'ticker': b['ticker'], 'kpi': r['kpi'], 'value': kk['value'], 'fmt': kk['fmt'],
            'is_currency': kk.get('is_currency', 1), 'period': b['period'], 'form': b['form'],
            'filing_id': b.get('filing_id'), 'tier': 'T3-llm', 'quote': r['quote'],
            'source': r.get('source_type'), 'source_element_id': r.get('source_element_id'),
            'value_as_written': r.get('value_as_written'),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', type=int, required=True)
    ap.add_argument('--llm-output', nargs='*', default=[],
                    help='one or more task .output json files from batched_llm_bind')
    a = ap.parse_args()
    pdir = f'{OUT}/part{a.part}'

    code = [json.loads(l) for l in open(f'{pdir}/code_resolved.jsonl')]
    llm = []
    if a.llm_output:
        batches = json.load(open(f'{pdir}/llm_batches.json'))
        for p in a.llm_output:
            if os.path.exists(p):
                llm += load_llm_records(p, batches)

    kept, dropped = [], []
    for r in code + llm:
        if r['value'] is None or not r.get('quote'):
            dropped.append({**r, 'drop_reason': 'no_quote'}); continue
        if L.value_ok(r['value'], r['fmt'], r['quote']):
            kept.append(r)
        else:
            dropped.append({**r, 'drop_reason': 'value_not_literally_in_quote'})

    # dedupe: one record per (ticker, kpi, period); prefer the deterministic tier
    order = {'T1-xbrl': 0, 'T2-label': 1, 'T3-llm': 2}
    best = {}
    for r in sorted(kept, key=lambda x: order.get(x['tier'], 9)):
        best.setdefault((r['ticker'], r['kpi'], r['period']), r)
    final = list(best.values())

    with open(f'{pdir}/seed_records.jsonl', 'w') as fh:
        for r in final:
            fh.write(json.dumps(r) + '\n')
    with open(f'{pdir}/gate_dropped.jsonl', 'w') as fh:
        for r in dropped:
            fh.write(json.dumps(r) + '\n')

    summary = {
        'part': a.part,
        'code_in': len(code), 'llm_in': len(llm),
        'gate_dropped': len(dropped),
        'seed_records': len(final),
        'by_tier': dict(collections.Counter(r['tier'] for r in final)),
        'companies': len({r['ticker'] for r in final}),
    }
    json.dump(summary, open(f'{pdir}/merge_summary.json', 'w'), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
