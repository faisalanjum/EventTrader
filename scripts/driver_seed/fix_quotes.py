#!/usr/bin/env python3
"""Blunt full-table fix (pure code, 0 LLM tokens).

For every seed record where the KPI's own label is NOT adjacent to the value in the quote
(link_lib.label_adjacent), replace the quote with the FULL table that contains it — so the column
header always travels with the value and the evidence is self-proving. Records that already prove
themselves are left untouched (cheap). Re-validates the value is still literally present.

    venv/bin/python scripts/driver_seed/fix_quotes.py --part 1
rewrites data/driver_catalog_seed/part<N>/seed_records.jsonl in place (+ a .bak).
"""
import json, os, argparse, collections, sys, shutil
sys.path.insert(0, os.path.dirname(__file__))
import link_lib as L
import run_code_tier as RC

OUT = 'data/driver_catalog_seed'
TEXT_SOURCES = {'section', 'exhibit_ex99', 'financial_statement_table', 'section_mdna'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--part', type=int, required=True)
    a = ap.parse_args()
    pdir = f'{OUT}/part{a.part}'
    src = f'{pdir}/seed_records.jsonl.bak' if os.path.exists(f'{pdir}/seed_records.jsonl.bak') else f'{pdir}/seed_records.jsonl'
    recs = [json.loads(l) for l in open(src)]

    # (0) tidy EVERY quote first — collapse zero-width/newline padding so the detector sees true
    # label-to-value distance (old-run quotes carry ​ padding that inflates it).
    for r in recs:
        r['quote'] = L._tidy(r['quote'])

    # which records need the full-table fix?  text-sourced, NOT XBRL-backed (T1 is member-verified),
    # and the label is NOT adjacent to the value in the (now tidy) quote.
    need = [r for r in recs
            if r.get('source') in TEXT_SOURCES
            and r.get('tier') != 'T1-xbrl'
            and not L.label_adjacent(r['kpi'], r['value'], r['fmt'], r['quote'])]
    by_cp = collections.defaultdict(list)
    for r in need:
        by_cp[(r['ticker'], r['form'], r['period'])].append(r)

    load = getattr(RC, 'load_env_neo4j'); load()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))

    fixed = gained_header = still_ungated = 0
    with drv.session() as s:
        for i, ((tk, form, per), items) in enumerate(sorted(by_cp.items())):
            xbrls, texts, _ = RC.fetch_corpus(s, tk, form, per)
            texts = texts + RC.fetch_press_release(s, tk, per)
            for r in items:
                new_q = L.expand_to_table(texts, r['quote'], r['value'], r['fmt'])
                if new_q and new_q != r['quote'] and L.value_ok(r['value'], r['fmt'], new_q):
                    if '##TABLE_START' in new_q:
                        gained_header += 1
                    r['quote'] = new_q
                    r['quote_expanded'] = True
                    fixed += 1
                else:
                    still_ungated += 1
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(by_cp)} company-periods…", flush=True)
    drv.close()

    shutil.copy(f'{pdir}/seed_records.jsonl', f'{pdir}/seed_records.jsonl.bak')
    with open(f'{pdir}/seed_records.jsonl', 'w') as fh:
        for r in recs:
            fh.write(json.dumps(r) + '\n')

    print(json.dumps({
        'total_records': len(recs),
        'flagged_needs_table': len(need),
        'flag_rate_pct': round(100 * len(need) / max(len(recs), 1), 1),
        'expanded': fixed,
        'now_carry_table_header': gained_header,
        'could_not_expand (left as-is)': still_ungated,
    }, indent=2))


if __name__ == '__main__':
    main()
