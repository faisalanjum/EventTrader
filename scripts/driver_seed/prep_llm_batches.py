#!/usr/bin/env python3
"""Group a part's residual KPIs into per-company-period batches for the LLM tier.
Each batch = one filing read that binds many KPIs.

    venv/bin/python scripts/driver_seed/prep_llm_batches.py --part 1
writes data/driver_catalog_seed/part<N>/llm_batches.json
"""
import json, argparse, collections, os

OUT = 'data/driver_catalog_seed'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--part', type=int, required=True)
    a = ap.parse_args()
    pdir = f'{OUT}/part{a.part}'
    groups = collections.OrderedDict()
    for line in open(f'{pdir}/residual.jsonl'):
        r = json.loads(line)
        key = (r['ticker'], r['form'], r['period'])
        g = groups.setdefault(key, {'ticker': r['ticker'], 'form': r['form'], 'period': r['period'],
                                     'filing_id': r.get('filing_id'), 'kpis': []})
        g['kpis'].append({'kpi': r['kpi'], 'value': r['value'], 'fmt': r['fmt'],
                          'is_currency': r['is_currency'],
                          'candidates': r.get('candidates', [])})   # pre-located by the code tier
    batches = list(groups.values())
    batches.sort(key=lambda b: -len(b['kpis']))   # biggest first (better concurrency fill)
    json.dump(batches, open(f'{pdir}/llm_batches.json', 'w'))
    kt = sum(len(b['kpis']) for b in batches)
    print(f"part {a.part}: {len(batches)} company-period batches, {kt} residual KPIs "
          f"(median {sorted(len(b['kpis']) for b in batches)[len(batches)//2]}/batch, max {len(batches[0]['kpis'])})")


if __name__ == '__main__':
    main()
