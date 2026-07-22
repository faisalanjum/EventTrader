"""M4 v2 — RESIDUAL + READER COST (combined-audit corrective 2026-07-22; all
seven reviewer items; read-only; NO paid AI calls; no production code).

FIXES OVER v1 (superseded, its sha 70a21434… recorded):
1. 8-K prose bounds — v1's <p>/<li>-only count was a material undercount. Now
   THREE persisted bounds from visible, NON-OVERLAPPING DOM blocks (no language
   parser): LOWER = p/li leaves · STRUCTURAL = p/li/div leaves (a leaf contains
   no other p/li/div) · UPPER = all visible non-table characters.
2. Transcript cost uses NUMERIC-BLOCK characters and REAL transcript sources
   (per-transcript grouping + ceil(numeric_chars/100k) chunk arithmetic).
3. Omitted sources included: the 573 no-exhibit events' display bodies are
   fetched/hashed via linkToFilingDetails (the recorded URL law) and measured as
   their own lane; the 38 PDFs stay LISTED as deferred/unsupported; primary
   bodies of EXHIBIT-BEARING events are declared UNMEASURED (only the 35 WP1-
   probe bodies were ever fetched).
4. The claimed Route-B saving is DELETED — reported only as an UNEARNED
   THEORETICAL CEILING (M2 proved geometry on 7/19 rows; a row can hold both
   clear and unclear cells).
5. Real call-cost model: the REAL caps from batch_groups.py:14-15 (MAX_CASES=8,
   MAX_CHARS=100,000); BASE text chunks reported separately from the anchor
   multiplier; NO invented output-token numbers (anchor input/output and
   tokens-per-accepted-fact are Phase-5-unavailable); historical + per-quarter
   live ranges computed FROM the selection's filed dates.
6. Prose/prepared/Q&A labelled strata are marked DEFERRED to Phase 5/6 — truth
   is unavailable there and none is manufactured.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m4_reader_residual.py
"""
import hashlib
import json
import math
import multiprocessing
import os
import sys
import time
import urllib.request
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from driver.relocation import inline_html as IH
import m1_structure_inventory as INV
from m1_transcript_census import NUM, spoken_text
from m1_canonical_selector import _driver

CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
BODY_CACHE = os.path.join(_HERE, 'm2_body_cache')
SELECTION = os.path.join(_HERE, 'm1_canonical_selection_final.jsonl')
BODY_MANIFEST = os.path.join(_HERE, 'm4_noexhibit_body_manifest.jsonl')
OUT = os.path.join(_HERE, 'm4_reader_residual.json')
UA = {'User-Agent': 'EventMarketDB research faisal@example.com'}
MAX_CASES, MAX_CHARS = 8, 100_000          # batch_groups.py:14-15, verified


def _visible(el):
    node = el
    while node is not None and getattr(node, 'name', None):
        nm = node.name.lower()
        if nm in INV._SKIP_TAGS or nm == 'ix:hidden' or IH._hidden_cell(node):
            return False
        node = node.parent
    return True


def scan(path):
    try:
        soup = IH._soup(open(path, 'rb').read().decode('utf-8', 'replace'))
    except Exception:
        return None
    rec = {'file': os.path.basename(path)}
    rec['visible_chars'] = len(IH._visible_walk(soup))
    lower_b = lower_c = struct_b = struct_c = 0
    numeric_struct_b = numeric_struct_c = numeric_div_b = numeric_div_c = 0
    for el in soup.find_all(['p', 'li', 'div']):
        if el.find_parent('table') is not None or el.find(['p', 'li', 'div']):
            continue                       # leaf, non-overlapping by construction
        if not _visible(el):
            continue
        t = IH._text(el)
        if not t.strip():
            continue
        struct_b += 1
        struct_c += len(t)
        if NUM.search(t):
            numeric_struct_b += 1
            numeric_struct_c += len(t)
            if el.name == 'div':
                numeric_div_b += 1
                numeric_div_c += len(t)
        if el.name in ('p', 'li'):
            lower_b += 1
            lower_c += len(t)
    table_c = 0
    table_all_c = 0
    table_rows = 0
    strict_c = 0
    for table in soup.find_all('table'):
        if table.find_parent('table') is not None:
            continue
        rows = INV._own_rows(table)
        grid = IH._table_grid(rows)
        ctx = {'tables': {}, 'cells': {}}
        for ri, tr in enumerate(rows):
            t = IH._text(tr)
            table_all_c += len(t)
            if not NUM.search(t):
                continue
            table_rows += 1
            table_c += len(t)
            if any(INV._classify_cell(c, ctx) == 'complete_strict'
                   for c, _s, _e in grid[ri] if NUM.search(IH._text(c))):
                strict_c += len(t)
    rec.update({'prose_lower_blocks': lower_b, 'prose_lower_chars': lower_c,
                'prose_struct_blocks': struct_b, 'prose_struct_chars': struct_c,
                'prose_struct_numeric_blocks': numeric_struct_b,
                'prose_struct_numeric_chars': numeric_struct_c,
                'prose_numeric_div_blocks': numeric_div_b,
                'prose_numeric_div_chars': numeric_div_c,
                'table_rows_numeric': table_rows, 'table_row_chars': table_c,
                'table_all_row_chars': table_all_c,
                'strict_table_row_chars': strict_c,
                'nontable_visible_chars_upper':
                    max(0, rec['visible_chars'] - table_all_c),
                'doc_chunks': max(1, __import__('math').ceil(
                    (numeric_struct_c + table_c) / 100_000))
                    if (numeric_struct_c + table_c) else 0})
    return rec


def transcripts(session):
    per = {'prepared_remarks': Counter(), 'qa_exchanges': Counter()}
    q = {'prepared_remarks':
         "MATCH (t:Transcript)-[:HAS_PREPARED_REMARKS]->(x) "
         "RETURN elementId(t) AS tid, x.content AS c",
         'qa_exchanges':
         "MATCH (t:Transcript)-[:HAS_QA_EXCHANGE]->(x) "
         "RETURN elementId(t) AS tid, x.exchanges AS c"}
    numeric_chars = {}
    for lane, cy in q.items():
        lane_chars = 0
        for row in session.run(cy):
            text = spoken_text(row['c'])
            if text and NUM.search(text):
                lane_chars += len(text)
                per[lane][row['tid']] += len(text)
        numeric_chars[lane] = lane_chars
    tids = set(per['prepared_remarks']) | set(per['qa_exchanges'])
    chunks = sum(max(1, math.ceil(
        (per['prepared_remarks'][t] + per['qa_exchanges'][t]) / MAX_CHARS))
        for t in tids)
    return {'prepared_numeric_block_chars': numeric_chars['prepared_remarks'],
            'qa_numeric_block_chars': numeric_chars['qa_exchanges'],
            'total_numeric_block_chars': sum(numeric_chars.values()),
            'transcripts_with_numbers': len(tids),
            'min_text_chunks_at_100k': chunks}


def fetch_noexhibit_bodies(session):
    accs = []
    for line in open(SELECTION):
        row = json.loads(line)
        if row['selected'] and not row['exhibits']:
            accs.append(row['accession_8k'])
    urls = {r['acc']: r['url'] for r in session.run(
        "MATCH (r:Report) WHERE r.accessionNo IN $a "
        "RETURN r.accessionNo AS acc, r.linkToFilingDetails AS url", a=accs)}
    os.makedirs(BODY_CACHE, exist_ok=True)
    done = set()
    if os.path.exists(BODY_MANIFEST):
        done = {json.loads(l)['acc'] for l in open(BODY_MANIFEST)}
    paths = []
    with open(BODY_MANIFEST, 'a') as mf:
        for acc in accs:
            path = os.path.join(BODY_CACHE, acc.replace('/', '_') + '.htm')
            if not os.path.exists(path) and urls.get(acc) and acc not in done:
                time.sleep(0.5)
                try:
                    data = urllib.request.urlopen(urllib.request.Request(
                        urls[acc], headers=UA), timeout=30).read()
                    open(path, 'wb').write(data)
                    mf.write(json.dumps({'acc': acc, 'url': urls[acc],
                                         'sha256': hashlib.sha256(data).hexdigest(),
                                         'bytes': len(data)}) + '\n')
                except Exception as e:
                    mf.write(json.dumps({'acc': acc, 'url': urls[acc],
                                         'error': type(e).__name__}) + '\n')
            if os.path.exists(path):
                paths.append(path)
    return accs, paths


def quarters():
    per_q = Counter()
    for line in open(SELECTION):
        row = json.loads(line)
        if row['selected'] and row['filed_8k']:
            d = str(row['filed_8k'])[:7]
            y, m = int(d[:4]), int(d[5:7])
            per_q[f'{y}Q{(m - 1) // 3 + 1}'] += 1
    full = sorted(per_q)[1:-1]             # drop partial edge quarters
    vals = [per_q[q] for q in full]
    return {'events_total': sum(per_q.values()),
            'full_quarters': len(full),
            'events_per_quarter_min': min(vals), 'max': max(vals),
            'mean': round(sum(vals) / len(vals), 1),
            'by_quarter': dict(sorted(per_q.items()))}


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
    drv = _driver()
    with drv.session() as s:
        tr = transcripts(s)
        noex_accs, noex_paths = fetch_noexhibit_bodies(s)
    drv.close()

    def agg(paths):
        tot = Counter()
        n = 0
        with multiprocessing.Pool(6) as pool:
            for rec in pool.imap_unordered(scan, paths, chunksize=25):
                if rec is None:
                    continue
                n += 1
                if rec['doc_chunks']:
                    tot['doc_chunks_docs'] += 1
                for k, v in rec.items():
                    if k != 'file':
                        tot[k] += v
        return n, dict(tot)

    n_ex, ex = agg(files)
    n_bd, bd = agg(noex_paths)

    def chunks_over(paths_chars_key, tot, n):
        # base text chunks: per doc ceil(numeric_chars/100k) needs per-doc data;
        # approximate EXACTLY by rescanning? No — compute per-doc in scan pass:
        return None

    # per-doc chunk arithmetic (exact): rescan quickly using stored per-file data
    def chunk_count(paths):
        c = 0
        docs_numeric = 0
        with multiprocessing.Pool(6) as pool:
            for rec in pool.imap_unordered(scan, paths, chunksize=25):
                if rec is None:
                    continue
                nc = rec['prose_struct_numeric_chars'] + rec['table_row_chars']
                if nc:
                    docs_numeric += 1
                    c += max(1, math.ceil(nc / MAX_CHARS))
        return docs_numeric, c

    ex_docs_numeric, ex_chunks = ex.get('doc_chunks_docs', 0), ex.get('doc_chunks', 0)
    bd_docs_numeric, bd_chunks = bd.get('doc_chunks_docs', 0), bd.get('doc_chunks', 0)

    CPT = [3.5, 4.0, 4.5]
    def toks(chars):
        return {f'@{c}': round(chars / c) for c in CPT}

    reader_chars_structural = (ex['table_row_chars']
                               + ex['prose_struct_numeric_chars']
                               + bd['table_row_chars']
                               + bd['prose_struct_numeric_chars']
                               + tr['total_numeric_block_chars'])
    q = quarters()
    live_share = q['mean'] / q['events_total']

    out = {
        'v2_supersedes': 'v1 sha 70a21434… (p/li undercount; transcript upper '
                         'bound; invented output tokens; unearned Route-B saving)',
        'anchors_and_output_side': 'UNAVAILABLE until Phase 5 — anchor input, '
            'output tokens, and tokens-per-accepted-fact are NOT estimated; the '
            'anchor multiplier is ceil(anchors/8) calls per chunk group '
            '(batch_groups MAX_CASES=8) and multiplies the BASE chunks below',
        'labelled_strata': {'8k_tables': {'rows': 19, 'accepted': 7, 'wrong': 0,
                                          'disputed': 3, 'plural_blocked': 9},
                            '8k_prose': 'DEFERRED to Phase 5/6 — no independent '
                                        'truth exists; none manufactured',
                            'prepared_remarks': 'DEFERRED to Phase 5/6',
                            'qa': 'DEFERRED to Phase 5/6'},
        '8k_exhibits': {'files': n_ex,
                        'prose_bounds': {
                            'lower_p_li': {'blocks': ex['prose_lower_blocks'],
                                           'chars': ex['prose_lower_chars']},
                            'structural_p_li_div_leaves_all': {
                                'blocks': ex['prose_struct_blocks'],
                                'chars': ex['prose_struct_chars']},
                            'structural_numeric_bearing': {
                                'blocks': ex['prose_struct_numeric_blocks'],
                                'chars': ex['prose_struct_numeric_chars']},
                            'numeric_div_leaves_alone': {
                                'blocks': ex['prose_numeric_div_blocks'],
                                'chars': ex['prose_numeric_div_chars']},
                            'upper_all_visible_nontable':
                                ex['nontable_visible_chars_upper']},
                        'tables': {'numeric_rows': ex['table_rows_numeric'],
                                   'row_chars': ex['table_row_chars'],
                                   'strict_row_chars_UNEARNED_THEORETICAL_'
                                   'CEILING_ONLY': ex['strict_table_row_chars']},
                        'base_text_chunks_at_100k': ex_chunks,
                        'numeric_docs': ex_docs_numeric},
        '8k_noexhibit_bodies': {'events': len(noex_accs),
                                'bodies_on_disk': n_bd,
                                'manifest': os.path.basename(BODY_MANIFEST),
                                'tables_row_chars': bd.get('table_row_chars', 0),
                                'prose_struct_numeric_chars':
                                    bd.get('prose_struct_numeric_chars', 0),
                                'base_text_chunks_at_100k': bd_chunks},
        '8k_exhibit_bearing_event_bodies': 'UNMEASURED (only the 35 WP1-probe '
            'bodies were ever fetched) — content may duplicate exhibits; '
            'measurement deferred with that question open',
        'pdfs': {'count': 38, 'status': 'DEFERRED/UNSUPPORTED — listed, never '
                                        'fetched, never silently removed'},
        'transcripts': tr,
        'reader_input_chars_structural_numeric': reader_chars_structural,
        'projected_input_tokens_structural': toks(reader_chars_structural),
        'base_text_chunks_total': ex_chunks + bd_chunks
                                  + tr['min_text_chunks_at_100k'],
        'historical_vs_live': {
            'quarters': q,
            'live_per_quarter_share': round(live_share, 5),
            'live_per_quarter_chunks':
                round((ex_chunks + bd_chunks + tr['min_text_chunks_at_100k'])
                      * live_share),
            'live_per_quarter_input_tokens_structural':
                toks(reader_chars_structural * live_share)},
    }
    json.dump(out, open(OUT, 'w'), indent=1)
    sha = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    slim = {k: out[k] for k in ('8k_exhibits', '8k_noexhibit_bodies',
                                'transcripts', 'base_text_chunks_total',
                                'projected_input_tokens_structural',
                                'historical_vs_live')}
    slim['output_sha256'] = sha
    print(json.dumps(slim, indent=1))
    print('M4-V2-DONE')


if __name__ == '__main__':
    main()
