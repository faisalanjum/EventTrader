"""M2 CANDIDATE PACKETS v2 (reviewer corrective 2026-07-22: 17/19 were not
self-contained; captions empty; float re-finding at v1 line 50).

Fixes, exactly his prescription — NO new header parser:
  * NO re-finding at all: each cell is located by its ALREADY-AUDITED stable address
    (table_index / row_index / grid col range) from m2_candidate_packets.jsonl (v1 —
    he verified all 19 underlying cells + hashes/spans). Float use eliminated.
  * printed_token carried forward from the audited v1 and re-verified by plain
    string containment in the address-located cell (no forms, no float).
  * SELF-CONTAINED PROOF: each packet now carries the COMPLETE EXACT TABLE (every
    row verbatim with spans) plus the PRECEDING BLOCK (all pinned text between the
    previous top-level table's end — or document start — and this table's start,
    verbatim with span). Scale lines ('in millions'), section sub-headers ('Gas
    Revenues'), and annual/quarterly context arrive as source text, not as parser
    output. v1's DERIVED aligned-header/caption/marker arrays are REMOVED ENTIRELY
    (final cleanup — they carried known-wrong selections); every row additionally
    carries per-cell {text, grid, span} so column relationships are provable by
    overlap arithmetic on the packet alone.
  * Document integrity: bytes sha256 and pinned-text sha must round-trip v1's.

v1 is PRESERVED as the audit trail; v2 writes m2_candidate_packets_v2.jsonl.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_candidate_packets_v2.py
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
import m1_structure_inventory as INV

EX_CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
BODY_CACHE = os.path.join(_HERE, 'm2_body_cache')
V1 = os.path.join(_HERE, 'm2_candidate_packets.jsonl')
OUT = os.path.join(_HERE, 'm2_candidate_packets_v2.jsonl')


def _doc_path(name):
    p = os.path.join(EX_CACHE, name)
    return p if os.path.exists(p) else os.path.join(BODY_CACHE, name)


def _row_span_bounds(rows, spans):
    starts = [spans[id(r)][0] for r in rows if id(r) in spans]
    ends = [spans[id(r)][1] for r in rows if id(r) in spans]
    return (min(starts), max(ends)) if starts else None


def rebuild(p1):
    path = _doc_path(p1['document']['file'])
    raw = open(path, 'rb').read()
    assert hashlib.sha256(raw).hexdigest() == p1['document']['bytes_sha256'], \
        f"document changed: {p1['document']['file']}"
    soup = IH._soup(raw.decode('utf-8', 'replace'))
    spans = {}
    doc_text = IH._visible_walk(soup, spans)
    assert IH.sha256_text(doc_text) == p1['document']['pinned_text_sha256'], \
        f"pinned text changed: {p1['document']['file']}"

    tables = [t for t in soup.find_all('table') if t.find_parent('table') is None]
    table = tables[p1['cell']['table_index']]
    rows = INV._own_rows(table)
    tr = rows[p1['cell']['row_index']]
    grid = IH._table_grid(rows)
    cs, ce = p1['cell']['grid_col_start'], p1['cell']['grid_col_end']
    cell = next(c for c, s, e in grid[p1['cell']['row_index']]
                if s == cs and e == ce)
    cell_text = IH._text(cell)
    assert p1['cell']['printed_token'] in cell_text, \
        (p1['candidate_id'], cell_text)

    # Per-cell grid coordinates from the certified _table_grid — the column
    # relationship (annual vs quarterly) becomes permanently provable by overlap
    # arithmetic on source-native coordinates; empty spacer cells included.
    table_rows = []
    for i, r in enumerate(rows):
        table_rows.append({
            'row_index': i, 'text': IH._text(r), 'span': spans.get(id(r)),
            'cells': [{'text': IH._text(c), 'grid': [s, e],
                       'span': spans.get(id(c))} for c, s, e in grid[i]]})
    bounds = _row_span_bounds(rows, spans)
    prev_end = 0
    ti = p1['cell']['table_index']
    if ti > 0:
        pb = _row_span_bounds(INV._own_rows(tables[ti - 1]), spans)
        if pb:
            prev_end = pb[1]
    preceding = None
    if bounds:
        preceding = {'span': [prev_end, bounds[0]],
                     'text': doc_text[prev_end:bounds[0]]}

    p2 = dict(p1)
    # Reviewer order (final cleanup): the v1-DERIVED header/caption/marker fields
    # carried known-wrong selections (ADM 'metric tons') — removed ENTIRELY; the
    # self-contained proof is the complete table (per-cell grids) + preceding block.
    for stale in ('aligned_headers_near_to_far', 'caption_context_full_grid_rows',
                  'printed_scale_unit_markers_verbatim'):
        p2.pop(stale, None)
    p2['relocated_by'] = 'stable_address_v1_audited (no value re-finding, no float)'
    p2['table_complete'] = {'span_bounds': bounds, 'rows': table_rows}
    p2['preceding_block'] = preceding
    return p2


def main():
    v1 = [json.loads(l) for l in open(V1)]
    assert len(v1) == 19, len(v1)
    packets = [rebuild(p) for p in v1]
    with open(OUT, 'w') as f:
        for p in packets:
            f.write(json.dumps(p) + '\n')
    sha = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    self_contained = sum(
        1 for p in packets
        if p['table_complete']['rows'] and p['preceding_block'] is not None)
    print(json.dumps({'packets': len(packets),
                      'with_complete_table_and_preceding_block': self_contained,
                      'output': OUT, 'output_sha256': sha}, indent=1))
    print('CANDIDATE-PACKETS-V2-DONE')


if __name__ == '__main__':
    main()
