"""PHASE-2 BROAD EX-99 STRESS CORPUS fetch (read-only) — ⛔ NOT CANONICAL M1.

RULING (2026-07-22): this broad 10,274-row inventory serves ONLY as a structural
stress corpus (unusual HTML shapes, fetch failures). It is NEVER labelled accuracy
evidence and NEVER mixed with the separate PER-21 canonical manifest, which alone
drives coverage/recall/reader-cost decisions.

Broad population = FinalPlan §15's pinned inventory (formType STARTS WITH '8-K', items
contain '2.02', exhibit_number in EX-99.1/EX-99/99.1; 10,274 rows measured). Fetches
each exhibit's ORIGINAL HTML once (polite >=0.5s spacing), caches by
accession__exhibit, records byte sha256 per file in a manifest. PDFs and failures are
recorded, never retried silently.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m1_8k_fetch.py
"""
import hashlib
import json
import os
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
MANIFEST = os.path.join(_HERE, 'm1_8k_fetch_manifest.jsonl')
UA = {'User-Agent': 'EventMarketDB research faisal@example.com'}


def rows():
    from dotenv import dotenv_values
    from neo4j import GraphDatabase
    cfg = dotenv_values(os.path.join(_HERE, '..', '..', '..', '..', '.env'))
    drv = GraphDatabase.driver(cfg['NEO4J_URI'],
                               auth=(cfg['NEO4J_USERNAME'], cfg['NEO4J_PASSWORD']))
    with drv.session() as s:
        out = [dict(r) for r in s.run(
            "MATCH (r:Report)-[:HAS_EXHIBIT]->(e:ExhibitContent) "
            "WHERE r.formType STARTS WITH '8-K' "
            "AND toString(r.items) CONTAINS '2.02' "
            "AND e.exhibit_number IN ['EX-99.1','EX-99','99.1'] "
            "RETURN DISTINCT r.accessionNo AS acc, r.exhibits AS ex, "
            "e.exhibit_number AS num")]
    drv.close()
    return out


def main():
    done = set()
    if os.path.exists(MANIFEST):
        for line in open(MANIFEST):
            done.add(json.loads(line)['key'])
    todo = []
    for r in rows():
        try:
            url = (json.loads(r['ex']) or {}).get(r['num'])
        except (TypeError, ValueError):
            url = None
        key = f"{r['acc']}__{r['num']}"
        if url and key not in done:
            todo.append((key, r['acc'], r['num'], url))
    print(f'to fetch: {len(todo)} (already manifested: {len(done)})', flush=True)
    last = 0.0
    with open(MANIFEST, 'a') as mf:
        for i, (key, acc, num, url) in enumerate(todo):
            ext = url.rsplit('.', 1)[-1].lower()
            rec = {'key': key, 'acc': acc, 'exhibit': num, 'url': url, 'ext': ext}
            if ext == 'pdf':
                rec['status'] = 'pdf_skipped'
            else:
                path = os.path.join(CACHE, key.replace('/', '_') + '.htm')
                if not os.path.exists(path):
                    wait = 0.5 - (time.time() - last)
                    if wait > 0:
                        time.sleep(wait)
                    last = time.time()
                    try:
                        req = urllib.request.Request(url, headers=UA)
                        data = urllib.request.urlopen(req, timeout=30).read()
                        open(path, 'wb').write(data)
                        rec['status'] = 'fetched'
                    except Exception as e:
                        rec['status'] = f'fetch_error:{type(e).__name__}'
                else:
                    rec['status'] = 'cached'
                if os.path.exists(path):
                    rec['sha256'] = hashlib.sha256(
                        open(path, 'rb').read()).hexdigest()
                    rec['bytes'] = os.path.getsize(path)
            mf.write(json.dumps(rec) + '\n')
            mf.flush()
            if (i + 1) % 200 == 0:
                print(f'{i+1}/{len(todo)}', flush=True)
    print('BROAD-STRESS-FETCH-DONE', flush=True)


if __name__ == '__main__':
    main()
