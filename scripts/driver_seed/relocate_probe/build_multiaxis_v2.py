#!/usr/bin/env python3
"""Multi-axis batches v2 (#767): LOCK LADDER = exact-cell (inline-XBRL, filer's printed
row/column/section) -> fallback to the v1 address (kept verbatim). ALL addresses now carry
measurement='gaap' (XBRL-oracle truths are GAAP by construction). Candidates: locate keep=24.

    venv/bin/python scripts/driver_seed/relocate_probe/build_multiaxis_v2.py
"""
import os, sys, json, glob, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, link_lib as L, run_code_tier as RC, lock_cell

HERE = os.path.dirname(__file__)
B = f'{HERE}/benchmark'


def main():
    rows = [json.loads(l) for l in open(f'{B}/multiaxis_pool/truth_2plus_156.jsonl')]
    old_batches = {int(f.split('_')[-1].split('.')[0]): json.load(open(f))
                   for f in glob.glob(f'{B}/batches_multiaxis/batch_*.json')}
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    accs = sorted({r['lock']['accession'] for r in rows} | {r['target']['accession'] for r in rows})
    with drv.session() as s:
        res = s.run("""MATCH (r:Report) WHERE r.accessionNo IN $a
                       OPTIONAL MATCH (r)-[:HAS_SECTION]->(x:ExtractedSectionContent)
                       RETURN r.accessionNo AS acc, r.primaryDocumentUrl AS url,
                              collect(DISTINCT x.content) AS texts""", a=accs)
        meta = {row['acc']: (row['url'], sorted(t for t in row['texts'] if t)) for row in res}
    drv.close()
    bdir = f'{HERE}/batches_multiaxis'
    os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    cells = fallbacks = 0
    for r in rows:
        i = r['id']; ob = old_batches[i]
        lock = r['lock']; ident = r['identity']
        url, _ = meta.get(lock['accession'], (None, []))
        addr = None
        if url:
            path = lock_cell.fetch_inline_html(url, lock['accession'])
            if path:
                sw = lock_cell.exact_cell(path, ident['concept_qname'],
                                          lock['period']['start_date'], lock['period']['end_date'],
                                          [(a['dimension_qname'], a['member_qname']) for a in ident['axes']])
                if sw and (sw.get('row') or sw.get('column')):
                    addr = lock_cell.cell_address(sw, ob['address']['label'], measurement='gaap',
                                                  lock_quote=ob['address'].get('lock_row', ''))
                    cells += 1
        if addr is None:                                  # ladder fallback: v1 address, unchanged
            addr = dict(ob['address']); addr['measurement'] = 'gaap'
            fallbacks += 1
        _, ttexts = meta.get(r['target']['accession'], (None, []))
        cands = prep.locate(ttexts, addr, keep=24) or ob['candidates']
        json.dump({**{k: ob[k] for k in ('id', 'ticker', 'kpi', 'fmt', 'source', 'period_type',
                                         'period_lock', 'period_target')},
                   'address': addr, 'candidates': cands}, open(f'{bdir}/batch_{i}.json', 'w'))
    ceil = 0
    truth = {t['id']: t for t in (json.loads(l) for l in open(f'{B}/truth_multiaxis.jsonl'))}
    for i, t in truth.items():
        b = json.load(open(f'{bdir}/batch_{i}.json'))
        if any(L.value_present_rounded(t['value_target'], 'number', c['text']) for c in b['candidates']):
            ceil += 1
    print(f"exact-cell locks: {cells}/156 | fallback addresses: {fallbacks}")
    print(f"ceiling: {ceil}/156 = {100*ceil/156:.0f}%")


if __name__ == '__main__':
    main()
