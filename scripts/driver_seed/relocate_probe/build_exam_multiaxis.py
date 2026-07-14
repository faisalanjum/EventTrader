#!/usr/bin/env python3
"""Mini-exam multi-axis strata from the 1,523-pool: --mode fresh (40 holdout pairs NOT used by the
banked gptholdout-100) or --mode drift (the renamed-label cases). Exact-cell HYBRID addresses
(cell identity + verbatim row blob), measurement='gaap', locate keep=24."""
import os, sys, json, glob, random, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, link_lib as L, run_code_tier as RC, lock_cell

HERE = os.path.dirname(__file__)
B = f'{HERE}/benchmark/multiaxis_pool'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', required=True, choices=('fresh', 'drift'))
    ap.add_argument('--n', type=int, default=40); a = ap.parse_args()
    pool = {r['id']: r for r in map(json.loads, open(f'{B}/truth_pool.jsonl'))}
    if a.mode == 'fresh':
        used = {r['pool_id'] for r in map(json.loads, open(f'{B}/final/holdout_blind_truth.jsonl'))}
        cand = [r for r in pool.values() if r['split'] == 'holdout' and r['id'] not in used]
        random.seed(42); rows = random.sample(cand, min(a.n, len(cand)))
    else:
        ids = [d['pool_id'] for d in json.load(open(f'{B}/drift_candidates.json'))]
        rows = [pool[i] for i in ids]
    dset = f'exam_ma{a.mode}'
    bdir = f'{HERE}/batches_{dset}'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    accs = sorted({r['target']['accession'] for r in rows})
    with drv.session() as s:
        res = s.run("""MATCH (r:Report)-[:HAS_SECTION]->(x:ExtractedSectionContent)
                       WHERE r.accessionNo IN $a RETURN r.accessionNo AS acc, collect(DISTINCT x.content) AS t""", a=accs)
        texts = {row['acc']: sorted(x for x in row['t'] if x) for row in res}
    drv.close()
    tr = open(f'{HERE}/truth_{dset}.jsonl', 'w')
    made = ceil = cells = 0
    for k, r in enumerate(rows):
        d = r['lock']
        path = lock_cell.fetch_inline_html(d['primary_document_url'], d['accession'])
        sw = lock_cell.exact_cell(path, d['concept_qname'], d['period_start'], d['period_end'],
                                  [(x['axis_qname'], x['member_qname']) for x in d['facets']]) if path else None
        if not sw or not sw.get('row'):
            continue                                             # exam strata: exact-cell locks only
        label = [w for w in (d['concept_label'] + ' ' + ' '.join(f['member_label'] for f in d['facets'])).split() if len(w) > 1]
        blob = ' '.join(sw.get('row_cells', [])) or None
        addr = lock_cell.cell_address(sw, label, measurement='gaap', lock_quote=blob)
        cells += 1
        cands = prep.locate(texts.get(r['target']['accession'], []), addr, keep=24)
        if not cands:
            continue
        json.dump({'id': made, 'ticker': r['ticker'], 'kpi': ' '.join(label), 'fmt': 'number',
                   'source': '10-Q', 'period_type': 'quarterly', 'period_lock': d['period_end'],
                   'period_target': r['target']['period_end'], 'address': addr, 'candidates': cands},
                  open(f'{bdir}/batch_{made}.json', 'w'))
        v = float(r['target']['value_raw'])                      # keep decimals: int() turned EPS -0.2 into 0
        tr.write(json.dumps({'id': made, 'ticker': r['ticker'], 'kpi': ' '.join(label), 'fmt': 'number',
                 'period_target': r['target']['period_end'], 'value_target': v, 'pool_id': r['id']}) + '\n')
        if any(L.value_present_rounded(v, 'number', c['text']) for c in cands):
            ceil += 1
        made += 1
    tr.close()
    print(f"[{dset}] exact-cell locks {cells}/{len(rows)} | built {made} | ceiling {ceil}/{made} = {100*ceil/max(made,1):.0f}%")


if __name__ == '__main__':
    main()
