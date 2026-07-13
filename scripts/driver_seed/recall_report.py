#!/usr/bin/env python3
"""Recall report: separate REAL misses from CORRECT abstentions.

For every KPI value in a part, ask the oracle question: does this exact value appear ANYWHERE in
the company-period's corpus (filing text, press release, or XBRL facts) at a numeric boundary?
  * not present  -> no verbatim quote can exist -> abstaining is CORRECT, not a miss
  * present      -> a quote exists -> if we didn't bind it, that is a genuine recall gap
This gives the true recall ceiling and shows where the remaining headroom actually is.

    venv/bin/python scripts/driver_seed/recall_report.py --part 1
"""
import os, re, json, argparse, collections, sys
sys.path.insert(0, os.path.dirname(__file__))
import link_lib as L
import run_code_tier as RC

OUT = 'data/driver_catalog_seed'


def findable(texts, xbrls, val, fmt):
    """is the exact value present anywhere in this company-period's corpus?"""
    forms = {f for f in L.value_forms(val, fmt or 'number') if len(f) >= 2}
    for div in (1e6, 1e9):
        xx = abs(float(val)) / div
        if xx >= 1:
            for d in (1, 2):
                forms.add(f"{xx:,.{d}f}")
    for blob in texts:
        for f in forms:
            if L.bounded_hit(blob, f) and L.exact_form(f, val, fmt):
                return 'text'
    sval = str(int(round(float(val))))
    for b in xbrls:
        if f'"{sval}"' in b or f'"{sval}.0"' in b:
            return 'xbrl'
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--part', type=int, required=True)
    a = ap.parse_args()
    pdir = f'{OUT}/part{a.part}'

    work = [json.loads(l) for l in open(f'{OUT}/worklist.jsonl')]
    tickers = sorted({w['ticker'] for w in work})
    chunk = (len(tickers) + 3) // 4
    part_tk = set(tickers[(a.part-1)*chunk: a.part*chunk])
    work = [w for w in work if w['ticker'] in part_tk]
    cps = collections.defaultdict(list)
    for w in work:
        cps[(w['ticker'], w['form'], w['period'])].append(w)

    bound = set()
    for fn in ('code_resolved.jsonl', 'seed_records.jsonl'):
        p = f'{pdir}/{fn}'
        if os.path.exists(p):
            for l in open(p):
                r = json.loads(l)
                bound.add((r['ticker'], r['kpi'], r['period']))

    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    stats = collections.Counter()
    by_fmt = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    with drv.session() as s:
        for i, ((tk, form, per), items) in enumerate(sorted(cps.items())):
            xbrls, texts, _ = RC.fetch_corpus(s, tk, form, per)
            texts = texts + RC.fetch_press_release(s, tk, per)
            for it in items:
                v, fmt = it['value'], it['fmt']
                if v is None:
                    continue
                key = (it['ticker'], it['kpi'], it['period'])
                where = findable(texts, xbrls, v, fmt)
                is_bound = key in bound
                if where and is_bound:
                    cat = 'bound'
                elif where and not is_bound:
                    cat = 'MISS (value is in the filing)'
                elif not where and is_bound:
                    cat = 'bound_via_xbrl_only'
                else:
                    cat = 'correct_abstain (value not in filing)'
                stats[cat] += 1
                by_fmt[fmt or 'number'][cat] += 1
                if cat.startswith('MISS') and len(examples['miss']) < 15:
                    examples['miss'].append(f"{tk} {it['kpi'][:40]} = {v} ({fmt}) in {where}")
                if cat.startswith('correct') and len(examples['abstain']) < 15:
                    examples['abstain'].append(f"{tk} {it['kpi'][:40]} = {v} ({fmt})")
            if (i+1) % 100 == 0:
                print(f"  {i+1}/{len(cps)} company-periods…", flush=True)
    drv.close()

    tot = sum(stats.values())
    ceiling = tot - stats['correct_abstain (value not in filing)']
    print("\n===== RECALL REPORT: part %d (%d KPI values) =====" % (a.part, tot))
    for k, n in stats.most_common():
        print(f"  {k:38} {n:6}  ({100*n/tot:5.1f}%)")
    got = stats['bound'] + stats['bound_via_xbrl_only']
    print(f"\n  quote CAN exist for            {ceiling:6}  ({100*ceiling/tot:.1f}% of all values)  <- the ceiling")
    print(f"  we bound                       {got:6}  ({100*got/max(ceiling,1):.1f}% of the ceiling)  <- TRUE RECALL")
    print("\n  by format (bound / miss / correct-abstain):")
    for fmt, c in by_fmt.items():
        b = c['bound'] + c['bound_via_xbrl_only']
        print(f"    {fmt:8} bound={b:5}  miss={c['MISS (value is in the filing)']:5}  correct_abstain={c['correct_abstain (value not in filing)']:5}")
    print("\n  sample MISSES (a quote exists, we failed to bind):")
    for e in examples['miss'][:10]:
        print("    -", e)
    print("\n  sample CORRECT abstentions (value appears nowhere in the filing):")
    for e in examples['abstain'][:10]:
        print("    -", e)
    json.dump({'stats': dict(stats), 'ceiling': ceiling, 'bound': got, 'total': tot},
              open(f'{pdir}/recall_report.json', 'w'), indent=2)


if __name__ == '__main__':
    main()
