"""Terminal-s collision census (reviewer order 2026-07-22): across the canonical
corpus, how often do BOTH forms (w and w+'s') appear as label/section/band words
within the SAME table — i.e., where a plural fold could conflate two co-existing
forms? Sizes the fold's danger before any approval; meaning otherwise stays with
Core/reader."""
import collections
import hashlib
import json
import multiprocessing
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)
from driver.relocation import inline_html as IH
import m1_structure_inventory as INV

CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
SELECTION = os.path.join(_HERE, 'm1_canonical_selection_final.jsonl')
OUT = os.path.join(_HERE, 'm2_terminal_s_census.json')
W = re.compile(r'[a-z]{3,}')


def scan(path):
    pairs = collections.Counter()
    tables_hit = 0
    try:
        soup = IH._soup(open(path, 'rb').read().decode('utf-8', 'replace'))
    except Exception:
        return pairs, 0
    for table in soup.find_all('table'):
        if table.find_parent('table') is not None:
            continue
        rows = INV._own_rows(table)
        grid = IH._table_grid(rows)
        words = set()
        for placed in grid:
            if not placed:
                continue
            leftmost = min(c[1] for c in placed)
            if INV._data_like(placed):
                words |= set(W.findall(' '.join(
                    IH._text(c).lower() for c, s, _e in placed if s == leftmost)))
            else:
                words |= set(W.findall(' '.join(
                    IH._text(c).lower() for c, _s, _e in placed)))
        hits = {(w, w + 's') for w in words if w + 's' in words}
        if hits:
            tables_hit += 1
            for h in hits:
                pairs[h] += 1
    return pairs, tables_hit


def main():
    files = []
    for line in open(SELECTION):
        row = json.loads(line)
        if row['selected']:
            for e in row['exhibits'] or []:
                if e['cls'] == 'html':
                    p = os.path.join(CACHE, f"{row['accession_8k']}__{e['num']}"
                                     .replace('/', '_') + '.htm')
                    if os.path.exists(p):
                        files.append(p)
    total_pairs = collections.Counter()
    tables_hit = 0
    with multiprocessing.Pool(6) as pool:
        for pairs, th in pool.imap_unordered(scan, files, chunksize=25):
            total_pairs.update(pairs)
            tables_hit += th
    out = {'files_scanned': len(files), 'tables_with_collisions': tables_hit,
           'distinct_collision_pairs': len(total_pairs),
           'top_40': [[a, b, n] for (a, b), n in total_pairs.most_common(40)]}
    json.dump(out, open(OUT, 'w'), indent=1)
    out['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps({k: v for k, v in out.items() if k != 'top_40'}, indent=1))
    print('top 15:', out['top_40'][:15])
    print('TERMINAL-S-CENSUS-DONE')


if __name__ == '__main__':
    main()
