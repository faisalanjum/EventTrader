"""PHASE-2 CANONICAL EXHIBIT FETCH (M1 step 1; selector ACCEPTED audit round 2,
2026-07-22) — fetch + hash the missing canonical HTML exhibits ONLY.

Drives from m1_canonical_selection_final.jsonl (sha db73a0cd…): combined-selected
events' exhibits with cls='html' not present in the shared cache. Reuses
exhibit_html_cache/ by the identical acc__exhibit key; appends to a SEPARATE
canonical manifest — NEVER mixed with the broad stress manifest. The 38 PDFs are
deferred by order and never fetched. Polite >=0.5s spacing; disk re-checked at run
time (a file cached since the selector ran records as already_cached).

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m1_canonical_fetch.py
"""
import hashlib
import json
import os
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
SELECTION = os.path.join(_HERE, 'm1_canonical_selection_final.jsonl')
MANIFEST = os.path.join(_HERE, 'm1_canonical_fetch_manifest.jsonl')
UA = {'User-Agent': 'EventMarketDB research faisal@example.com'}


def main():
    done = set()
    if os.path.exists(MANIFEST):
        for line in open(MANIFEST):
            done.add(json.loads(line)['key'])
    todo = []
    for line in open(SELECTION):
        row = json.loads(line)
        if not row['selected']:
            continue
        for e in row['exhibits'] or []:
            if e['cls'] == 'html' and not e['cached_broad']:
                key = f"{row['accession_8k']}__{e['num']}"
                if key not in done:
                    todo.append((key, e['url']))
    print(f'to fetch: {len(todo)} (already manifested: {len(done)})', flush=True)
    last = 0.0
    with open(MANIFEST, 'a') as mf:
        for i, (key, url) in enumerate(todo):
            rec = {'key': key, 'url': url}
            path = os.path.join(CACHE, key.replace('/', '_') + '.htm')
            if os.path.exists(path):
                rec['status'] = 'already_cached'
            else:
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
            if os.path.exists(path):
                rec['sha256'] = hashlib.sha256(open(path, 'rb').read()).hexdigest()
                rec['bytes'] = os.path.getsize(path)
            mf.write(json.dumps(rec) + '\n')
            mf.flush()
            if (i + 1) % 200 == 0:
                print(f'{i + 1}/{len(todo)}', flush=True)
    print('CANONICAL-FETCH-DONE', flush=True)


if __name__ == '__main__':
    main()
