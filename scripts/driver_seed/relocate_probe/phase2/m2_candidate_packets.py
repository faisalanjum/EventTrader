"""M2 PRE-HARNESS — one exact evidence packet per CANDIDATE CELL (reviewer order
2026-07-22). These are 19 unique CANDIDATE CELLS — NOT independent truth; the
reviewer audits every packet and only accepted cases become M2 accuracy truth.

Packet contents (his spec, verbatim fields): document hash · stable cell/span ·
full row (NO truncation) · aligned headers + caption context · printed unit/scale
markers AS FOUND (verbatim strings, zero derivation) · period · exact Decimal value
(string-constructed — no float in any packet field). Finder = the SAME certified
literal laws as the qualification (_tableforms/at_boundary/strict classifier);
spans = the certified pinned representation (inline_html._visible_walk + sha).

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_candidate_packets.py
"""
import hashlib
import json
import os
import sys
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'scripts', 'driver_seed'))
sys.path.insert(0, _HERE)

import link_lib as L
from driver.relocation import inline_html as IH
import m1_structure_inventory as INV

EX_CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
BODY_CACHE = os.path.join(_HERE, 'm2_body_cache')
QUAL = os.path.join(_HERE, 'm2_wp1_8k_qualification.json')
WP1 = os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'wp1', 'code_resolved.jsonl')
OUT = os.path.join(_HERE, 'm2_candidate_packets.jsonl')


def _doc_path(name):
    p = os.path.join(EX_CACHE, name)
    return p if os.path.exists(p) else os.path.join(BODY_CACHE, name)


def _packet(doc_name, recs):
    """recs: the WP1 records resolved to ONE cell in doc_name (merged duplicates)."""
    path = _doc_path(doc_name)
    raw = open(path, 'rb').read()
    html = raw.decode('utf-8', 'replace')
    soup = IH._soup(html)
    ctx = {'tables': {}, 'cells': {}}
    fmt = None if recs[0]['fmt'] == 'number' else recs[0]['fmt']
    forms = L._tableforms(float(recs[0]['value']), fmt)  # WP1's certified finder law
    hit = None
    for s in soup.find_all(string=True):
        text = str(s)
        tok = None
        for fo in sorted(forms):
            i = text.find(fo)
            while i >= 0:
                if L.at_boundary(text, i, i + len(fo)):
                    tok = fo
                    break
                i = text.find(fo, i + 1)
            if tok:
                break
        if not tok:
            continue
        el = s.parent
        node, skip = el, False
        while node is not None and getattr(node, 'name', None):
            nm = node.name.lower()
            if nm in INV._SKIP_TAGS or nm == 'ix:hidden' or IH._hidden_cell(node):
                skip = True
                break
            node = node.parent
        if skip:
            continue
        cell = el if el.name in ('td', 'th') else el.find_parent(['td', 'th'])
        if cell is None or cell.find_parent('table') is None:
            continue
        assert hit is None or hit[0] is cell, f'multiple cells in {doc_name}'
        hit = (cell, tok)
    assert hit, f'no cell re-located in {doc_name}'
    cell, printed_token = hit

    verdict = INV._classify_cell(cell, ctx)
    assert verdict == 'complete_strict', (doc_name, verdict)
    rows, grid, zone_end, grid_width = INV._table_ctx(cell, ctx)
    tr = cell.find_parent('tr')
    row_idx = next(i for i, r in enumerate(rows) if r is tr)
    t_start, t_end = next((s, e) for c, s, e in grid[row_idx] if c is cell)
    table = cell.find_parent('table')
    tables_in_doc = [t for t in soup.find_all('table')
                     if t.find_parent('table') is None]
    table_idx = next(i for i, t in enumerate(tables_in_doc) if t is table)

    spans = {}
    doc_text = IH._visible_walk(soup, spans)
    cell_span = spans.get(id(cell))
    row_span = spans.get(id(tr))
    tok_abs = None
    if cell_span:
        seg = doc_text[cell_span[0]:cell_span[1]]
        j = seg.find(printed_token)
        if j >= 0:
            tok_abs = (cell_span[0] + j, cell_span[0] + j + len(printed_token))

    headers = []
    caption_banners = []
    for i in range(zone_end):
        for c, s0, e0 in grid[i]:
            txt = IH._text(c)
            if not txt.strip(' —-') or IH._hidden_cell(c):
                continue
            if e0 <= t_start or s0 >= t_end:
                continue
            if s0 == 0 and e0 >= grid_width:
                caption_banners.append({'row': i, 'text': txt,
                                        'span': spans.get(id(c))})
            elif not (s0 == 0 and t_start > 0):
                headers.append({'row': i, 'grid': [s0, e0], 'text': txt,
                                'span': spans.get(id(c))})

    return {
        'candidate_id': f'{doc_name}#t{table_idx}r{row_idx}c{t_start}-{t_end}',
        'item_ids': [r['item_id'] for r in recs],
        'ticker': recs[0]['ticker'],
        'raw_labels': sorted({r['raw_label'] for r in recs}),
        'document': {'file': doc_name, 'bytes_sha256': hashlib.sha256(raw).hexdigest(),
                     'pinned_text_sha256': IH.sha256_text(doc_text)},
        'cell': {'table_index': table_idx, 'row_index': row_idx,
                 'grid_col_start': t_start, 'grid_col_end': t_end,
                 'text': IH._text(cell), 'span': cell_span,
                 'printed_token': printed_token, 'token_span': tok_abs},
        'row': {'text_full': IH._text(tr), 'span': row_span},
        'aligned_headers_near_to_far': sorted(headers, key=lambda h: -h['row']),
        'caption_context_full_grid_rows': caption_banners,
        'printed_scale_unit_markers_verbatim': {
            'note': 'as-found strings only; nothing derived',
            'in_row': IH._text(tr),
            'in_headers': [h['text'] for h in headers],
            'in_caption': [b['text'] for b in caption_banners]},
        'record': {'value_exact_decimal': str(recs[0]['value']),
                   'fmt': recs[0]['fmt'], 'is_currency': recs[0]['is_currency'],
                   'period_end': recs[0]['period_end'],
                   'wp1_quote': recs[0]['quote'],
                   'wp1_quote_source': recs[0]['quote_source']},
    }


def main():
    qual = json.load(open(QUAL))
    # parse_float=Decimal: WP1 stores some values as JSON numbers (81.3); a float
    # round-trip would poison the exact-Decimal packet field (reviewer ban).
    wp1 = {}
    for l in open(WP1):
        r = json.loads(l, parse_float=Decimal)
        if r.get('source_type') == '8k':
            wp1[r['item_id']] = r
    by_cell = {}
    for r in qual['ledger']:
        if r['bucket'] != 'qualified':
            continue
        key = (r['acc'], r['doc'], r['row_text'], r['cell_text'])
        by_cell.setdefault(key, []).append(wp1[r['item_id']])
    assert len(by_cell) == 19, len(by_cell)

    packets = []
    for (acc, doc, _rt, _ct), recs in sorted(by_cell.items()):
        vals = {r['value'] for r in recs}
        assert len(vals) == 1, (doc, vals)
        packets.append(_packet(doc, recs))

    with open(OUT, 'w') as f:
        for p in packets:
            f.write(json.dumps(p) + '\n')
    sha = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    merged = [p for p in packets if len(p['item_ids']) > 1]
    print(json.dumps({'packets': len(packets),
                      'merged_duplicate_records': [p['candidate_id'] for p in merged],
                      'every_packet_has': ['bytes_sha256', 'pinned_text_sha256',
                                           'cell span+grid address', 'full row',
                                           'aligned headers', 'caption rows',
                                           'verbatim markers', 'exact Decimal'],
                      'output': OUT, 'output_sha256': sha}, indent=1))
    print('CANDIDATE-PACKETS-DONE')


if __name__ == '__main__':
    main()
