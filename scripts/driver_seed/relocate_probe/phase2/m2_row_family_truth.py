"""M2 ROW-FAMILY TRUTH v4 — the TWO-REGISTER CONTEXT TRACKER (reviewer model
2026-07-22; supersedes v3's single-block rule, which AEE disproved: date headers
stay valid while sections change — v3 sha 526f59a0 gave every AEE cell an empty
aligned-header list).

THE MODEL (his words): one single-pass scan, two independent registers —
band rows (non-data rows with non-banner text over the value columns) update the
CURRENT COLUMN-HEADER BAND; structural label rows update the CURRENT SECTION;
blank rows change nothing; a repeated header replaces only the band; a new
section replaces only the section; every data row receives BOTH.

'unmarked_numeric' (never 'level'): exact header/unit text is carried and CORE
decides level vs change; the channel asserts nothing.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_row_family_truth.py
"""
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from driver.relocation import inline_html as IH
from m1_transcript_census import NUM

V2 = os.path.join(_HERE, 'm2_candidate_packets_v2.jsonl')
V2_SHA = '5aff53ccb3a3a71ef7b1cc747b219cbd6e75b7918de8c4141fbf8cd8e2d9dc9e'
OUT = os.path.join(_HERE, 'm2_row_family_truth.jsonl')


def _data_like_cells(cells):
    if not cells:
        return False
    leftmost = min(cells, key=lambda c: c['grid'][0])
    if not IH._words(leftmost['text']):
        return False
    return any(c is not leftmost and NUM.search(c['text']) for c in cells)


def context_track(rows, num_cols, gw):
    """ONE single-pass tracker, TWO independent registers (reviewer model):
    band rows (non-data rows with non-banner text over value columns) update the
    CURRENT COLUMN-HEADER BAND; structural label rows update the CURRENT SECTION;
    blank rows change nothing; a repeated header replaces only the band, a new
    section replaces only the section; every data row receives BOTH."""
    ctx = {}
    band, section = [], []
    prev = None
    for j, r in enumerate(rows):
        cells = r['cells']
        if not any(c['text'].strip() for c in cells):
            continue
        if _data_like_cells(cells):
            ctx[j] = (list(band), list(section))
            prev = 'data'
            continue
        over_value = any(
            c['text'].strip() and not (c['grid'][0] == 0 and c['grid'][1] >= gw)
            and any(not (ne <= c['grid'][0] or ns >= c['grid'][1])
                    for ns, ne in num_cols)
            for c in cells)
        kind = 'band' if over_value else 'section'
        if kind == 'band':
            band = band + [r] if prev == 'band' else [r]
        else:
            section = section + [r] if prev == 'section' else [r]
        prev = kind
    return ctx


def numeric_cols(rows):
    cols = set()
    for r in rows:
        if not _data_like_cells(r['cells']):
            continue
        occupied = [c for c in r['cells']]
        if not occupied:
            continue
        leftmost = min(c['grid'][0] for c in occupied)
        for c in occupied:
            if c['grid'][0] != leftmost and NUM.search(c['text']):
                cols.add(tuple(c['grid']))
    return cols


def main():
    assert hashlib.sha256(open(V2, 'rb').read()).hexdigest() == V2_SHA
    fams = []
    for line in open(V2):
        p = json.loads(line)
        rows = p['table_complete']['rows']
        ri = p['cell']['row_index']
        row = rows[ri]
        gw = max((c['grid'][1] for r in rows for c in r['cells']), default=0)
        ncols = numeric_cols(rows)
        ctx_map = context_track(rows, ncols, gw)
        band, sect = ctx_map.get(ri, ([], []))
        block = band + sect
        block_texts = [r['text'] for r in sect if r['text'].strip()]
        cells = []
        for c in row['cells']:
            if not NUM.search(c['text']):
                continue
            s, e = c['grid']
            heads = [bc['text'] for br in band for bc in br['cells']
                     if not (bc['grid'][1] <= s or bc['grid'][0] >= e)
                     and bc['text'].strip(' —-')
                     and not (bc['grid'][0] == 0 and bc['grid'][1] >= gw)
                     and not (bc['grid'][0] == 0 and s > 0)]
            if not heads and not block_texts:
                continue
            kind = ('percent_marked'
                    if '%' in c['text'] or any('%' in h for h in heads)
                    else 'unmarked_numeric')
            cells.append({'grid': c['grid'], 'cell_text': c['text'],
                          'tokens': NUM.findall(c['text']), 'span': c['span'],
                          'aligned_headers_verbatim': heads,
                          'governing_section_verbatim': block_texts,
                          'column_kind': kind})
        orig = [p['cell']['grid_col_start'], p['cell']['grid_col_end']]
        assert any(c['grid'] == orig for c in cells), p['candidate_id']
        fams.append({'candidate_id': p['candidate_id'], 'ticker': p['ticker'],
                     'raw_labels': p['raw_labels'], 'document': p['document'],
                     'table_index': p['cell']['table_index'], 'row_index': ri,
                     'row_text': p['row']['text_full'],
                     'row_span': p['row']['span'],
                     'original_truth_grid': orig,
                     'header_band': [{'row_index': r['row_index'],
                                      'text': r['text'], 'span': r['span']}
                                     for r in band],
                     'governing_section': [{'row_index': r['row_index'],
                                            'text': r['text'], 'span': r['span']}
                                           for r in sect],
                     'headed_numeric_cells': cells})
    with open(OUT, 'w') as f:
        for fam in fams:
            f.write(json.dumps(fam) + '\n')
    sha = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    adm = [f for f in fams if f['ticker'] == 'ADM']
    checks = {
        'ADM_any_metric_tons_anywhere': any(
            'metric tons' in json.dumps(f).lower() for f in adm),
        'ADM_all_have_in_millions': all(
            'in millions' in json.dumps(f).lower() for f in adm),
        'AEE_cells_with_aligned_headers': sum(
            1 for f in fams if f['ticker'] == 'AEE'
            for c in f['headed_numeric_cells'] if c['aligned_headers_verbatim']),
        'any_cell_empty_both': sum(
            1 for f in fams for c in f['headed_numeric_cells']
            if not c['aligned_headers_verbatim']
            and not c['governing_section_verbatim'])}
    print(json.dumps({'rows': len(fams),
                      'headed_numeric_cells': sum(len(f['headed_numeric_cells'])
                                                  for f in fams),
                      'checks': checks, 'output_sha256': sha}, indent=1))
    print('ROW-FAMILY-TRUTH-V4-DONE')


if __name__ == '__main__':
    main()
