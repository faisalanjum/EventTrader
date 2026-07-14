#!/usr/bin/env python3
"""UNPARKED multi-axis test (user 2026-07-13): convert the independently-audited 156-pair TRUE
multi-axis benchmark (/tmp/regression_audit_axes.cHcqXo, SHA-manifested) into my reader schema,
rebuilding candidates with the ported locate at keep=24 (their dev curve: 24 -> 99-100% of present).
Their addresses carry identity axes -> the ported facet scoring engages. NO truth in batches.

    venv/bin/python scripts/driver_seed/relocate_probe/build_multiaxis.py
"""
import os, sys, json, glob, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
import prep, link_lib as L, run_code_tier as RC

BENCH = pathlib.Path('/tmp/regression_audit_axes.cHcqXo')
HERE = os.path.dirname(__file__)


def main():
    truth = [json.loads(l) for l in (BENCH / 'truth_2plus.jsonl').read_text().splitlines() if l]
    RC.load_env_neo4j()
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(os.environ['NEO4J_URI'],
                               auth=(os.environ.get('NEO4J_USERNAME', 'neo4j'), os.environ['NEO4J_PASSWORD']))
    accs = sorted({json.loads((BENCH / 'batches_2plus' / f"batch_{r['id']}.json").read_text())['source_accession']
                   for r in truth})
    with drv.session() as s:
        res = s.run("""MATCH (r:Report)-[:HAS_SECTION]->(x:ExtractedSectionContent)
                       WHERE r.accessionNo IN $a RETURN r.accessionNo AS acc, collect(DISTINCT x.content) AS texts""",
                    a=accs)
        source = {row['acc']: sorted(t for t in row['texts'] if t) for row in res}
    drv.close()
    bdir = f'{HERE}/batches_multiaxis'; os.makedirs(bdir, exist_ok=True)
    for f in glob.glob(f'{bdir}/*.json'):
        os.remove(f)
    tr = open(f'{HERE}/truth_multiaxis.jsonl', 'w')
    ceil = 0
    for r in truth:
        b = json.loads((BENCH / 'batches_2plus' / f"batch_{r['id']}.json").read_text())
        cands = prep.locate(source.get(b['source_accession'], []), b['address'], keep=24)
        json.dump({'id': r['id'], 'ticker': r['ticker'], 'kpi': ' '.join(b['address']['label']),
                   'fmt': 'number', 'source': b.get('form', '10-Q'), 'period_type': b.get('period_type', 'quarterly'),
                   'period_lock': r['lock']['period']['end_date'], 'period_target': r['target']['period']['end_date'],
                   'address': b['address'], 'candidates': cands}, open(f'{bdir}/batch_{r["id"]}.json', 'w'))
        v = int(float(r['target']['value_raw']))
        tr.write(json.dumps({'id': r['id'], 'ticker': r['ticker'], 'kpi': ' '.join(b['address']['label']),
                 'fmt': 'number', 'period_target': r['target']['period']['end_date'], 'value_target': v,
                 'split': r['split'], 'type': f"axes{r['identity']['nonstructural_axis_count']}"}) + '\n')
        if any(L.value_present_rounded(v, 'number', c['text']) for c in cands):
            ceil += 1
    tr.close()
    print(f"multi-axis batches built: {len(truth)}  (dev {sum(r['split']=='development' for r in truth)}"
          f" / holdout {sum(r['split']=='holdout' for r in truth)})")
    print(f"  value present in candidates (ceiling): {ceil}/{len(truth)} = {100*ceil/len(truth):.0f}%")


if __name__ == '__main__':
    main()
