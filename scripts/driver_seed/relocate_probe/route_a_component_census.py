"""ROUTE-A COMPONENT CENSUS (durable; Phase-1 corrective item 11).

A COMPONENT census — NOT full Route-A certification: it exercises prepare + id join +
identity fallback + semantic-unit tuple map + context-pointer match + period law +
hidden/typed + exact-Decimal reconciliation per fact. It does NOT call LOC.locate
(no anchors, no identity proof, no emission shape) — the end-to-end runs live in
route_a_e2e_150.py and the pytest suites.

    venv/bin/python scripts/driver_seed/relocate_probe/route_a_component_census.py
"""
import datetime
import glob
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', '..', '..', 'driver', 'relocation'))
CACHE = os.path.join(_HERE, 'inline_html_cache')
OUT = os.path.join(_HERE, 'route_a_component_census_result.json')
_drv = None


def _init():
    global _drv
    from dotenv import dotenv_values
    from neo4j import GraphDatabase
    cfg = dotenv_values(os.path.join(_HERE, '..', '..', '..', '.env'))
    _drv = GraphDatabase.driver(cfg['NEO4J_URI'],
                                auth=(cfg['NEO4J_USERNAME'], cfg['NEO4J_PASSWORD']))


def _plus_one(d):
    try:
        return (datetime.date.fromisoformat(d)
                + datetime.timedelta(days=1)).isoformat()
    except (ValueError, TypeError):
        return None


def work(path):
    import inline_html as IH
    import locator as LOC
    acc = os.path.basename(path)[:-4]
    t = Counter()
    try:
        prepared = IH.prepare(open(path, encoding='utf-8',
                                   errors='replace').read())
    except Exception as e:
        return acc, {'file_error': 1}, str(e)[:80]
    q = ("MATCH (x:XBRLNode {accessionNo:$a})<-[:REPORTS]-(f:Fact)"
         "-[:HAS_PERIOD]->(p:Period) WHERE f.is_numeric='1' AND f.is_nil='0' "
         "MATCH (f)-[:HAS_UNIT]->(u:Unit) "
         "RETURN f.fact_id AS fid, f.qname AS qn, f.context_id AS cid, "
         "f.value AS v, f.unit_ref AS ur, u.name AS un, u.is_divide AS dv, "
         "p.period_type AS pt, p.start_date AS ps, p.end_date AS pe")
    with _drv.session() as s:
        rows = list(s.run(q, a=acc))
    for r in rows:
        t['facts'] += 1
        sem = LOC.ROUTE_A_SEM_UNIT.get(
            (r['un'], LOC.ROUTE_A_BOOLS.get(r['dv'])))
        t[f'unit_{sem or "abstain"}'] += 1
        fid = r['fid'] if isinstance(r['fid'], str) else ''
        ev = None
        if not fid.strip() or fid == 'null':
            el, why = IH.identity_fallback(prepared, r['qn'], r['cid'] or '',
                                           r['ur'] or '')
            t[f'fallback_{why}'] += 1
            if el is None:
                continue
            ev, why2 = IH.evidence_for_element(prepared, el)
            if ev is None:
                t[f'evidence_{why2}'] += 1
                continue
        elif fid != fid.strip():
            t['padded_id_rejected'] += 1
            continue
        else:
            cnt = prepared['ids'].get(fid, 0)
            if cnt != 1:
                t['missing' if cnt == 0 else 'duplicate'] += 1
                continue
            ev, why = IH.element_evidence(prepared, fid)
            if ev is None:
                t[f'evidence_{why}'] += 1
                continue
        if ev['hidden']:
            t['hidden'] += 1
            continue
        if r['cid'] and ev['context_ref'] != r['cid']:
            t['ctx_pointer_mismatch'] += 1
            continue
        ds, de = ev['period']
        ok_p = (_plus_one(de) == r['ps'] if r['pt'] == 'instant'
                else (ds == r['ps'] and _plus_one(de) == r['pe']))
        t['period_ok' if ok_p else 'period_mismatch'] += 1
        if not ok_p:
            continue
        ok = IH.reconcile(ev['displayed'], ev['fmt'], ev['scale'], ev['sign'],
                          r['v'])
        t['reconcile_ok' if ok else 'reconcile_fail'] += 1
        if ok and ev['in_table'] and (ev['row_label'] or ev['columns']):
            t['has_row_or_header'] += 1
    return acc, dict(t), ''


def main():
    t0 = time.time()
    paths = sorted(p for p in glob.glob(CACHE + '/*.htm')
                   if os.path.getsize(p) > 10000)
    tot = Counter()
    errs = []
    with Pool(6, initializer=_init) as p:
        for i, (acc, t, e) in enumerate(p.imap_unordered(work, paths,
                                                         chunksize=4)):
            tot.update(t)
            if e:
                errs.append((acc, e))
            if (i + 1) % 250 == 0:
                print(f'{i+1}/{len(paths)} {time.time()-t0:.0f}s', flush=True)
    out = {'label': 'ROUTE-A COMPONENT CENSUS (not full certification)',
           'files': len(paths), 'buckets': dict(tot),
           'file_errors': errs[:5], 'secs': round(time.time() - t0)}
    json.dump(out, open(OUT, 'w'), indent=1)
    print('CENSUS-DONE', json.dumps(out)[:800], flush=True)


if __name__ == '__main__':
    main()
