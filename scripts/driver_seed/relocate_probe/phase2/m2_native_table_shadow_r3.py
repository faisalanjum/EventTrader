"""M2 NATIVE-TABLE SHADOW — ROUND 3 (audit-only; reviewer order 2026-07-22).

ANSWER-FREE: location receives NO expected value and NO target year — the anchor is
label words only ('&'→'and' approved typography; NO trailing-s fold — rejected as
meaning-changing; no other normalization). Rounds 1-2 stand as known-answer
location evidence only.

ONE SHARED STRUCTURAL HELPER (_row_scope; composes the certified grid — no second
header system): per body row → {exact row label · governing local section (the
NEAREST wordy, number-free row above, within the table only) · aligned column
headers (strict credit incl. full-grid + left-anchor guards) · immediate caption
(the table's own full-grid banner rows ONLY — no nearby prose, no preceding
block)}. NARROW per order: scope is these four structures, nothing else.

MATCH: all anchor words appear in the scope text; the row's OWN meaning words
(parenthesized unit/qualifier segments and bare footnote digits separated
MECHANICALLY first) must add nothing beyond the anchor — unexplained meaning
words abstain that row (his item 4).
ROW-LEVEL uniqueness (his item 4): EXACTLY ONE proven row per filing — it EMITS
EVERY valid period cell (headers verbatim = the period evidence; no meaning
assigned). Multiple rows → disputed abstain (the consolidated-vs-regional case is
REPORTED EXPLICITLY). No cell-level filing-wide requirement.

SCORING (truth used ONLY here): every emitted cell must match the audited
row-family truth (fe961101…) by address+tokens; any emitted cell outside truth or
mismatched → HARD STOP. HONESTY CLAUSE (his item 7): real Driver slice identity is
unavailable until Phase 5 — this round proves TABLE GEOMETRY ONLY; final identity
accuracy waits for real slice-bearing anchors.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_native_table_shadow_r3.py
"""
import hashlib
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from driver.relocation import inline_html as IH
import m1_structure_inventory as INV
from m1_transcript_census import NUM

EX_CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
BODY_CACHE = os.path.join(_HERE, 'm2_body_cache')
TRUTH = os.path.join(_HERE, 'm2_row_family_truth.jsonl')
TRUTH_SHA = '465d72cadbbf4cbef63ee288c7722a82effa9ec77e487aff69ad90f7ac08ce2c'
WP1 = os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'wp1', 'code_resolved.jsonl')
OUT = os.path.join(_HERE, 'm2_native_table_shadow_r3_report.json')
_SEARCHED = {}


def _fold(text):
    return text.lower().replace('&', ' and ')


def _wordset(text):
    return set(re.findall(r'[a-z0-9]+', _fold(text)))


def _docs_of(acc):
    docs = []
    body = os.path.join(BODY_CACHE, acc.replace('/', '_') + '.htm')
    if os.path.exists(body):
        docs.append(body)
    docs += sorted(os.path.join(EX_CACHE, f) for f in os.listdir(EX_CACHE)
                   if f.startswith(acc + '__'))
    for d in docs:
        if d not in _SEARCHED:
            _SEARCHED[d] = hashlib.sha256(open(d, 'rb').read()).hexdigest()
    return docs


def _numeric_data_cols(grid, zone_end):
    """The table's aligned numeric-data column ranges (reviewer ruling 5): grid
    ranges of NON-LEFTMOST body cells carrying a numeric token. The leftmost
    occupied position is the label convention (same anchor the certified
    _data_like uses) \u2014 so numeric NAMES like 'Product 50' stay labels."""
    cols = set()
    for placed in grid[zone_end:]:
        if not placed:
            continue
        leftmost = min(c[1] for c in placed)
        for cell, s, e in placed:
            if s != leftmost and NUM.search(IH._text(cell)):
                cols.add((s, e))
    return cols


def _context_track(grid, num_cols, gw):
    """The TWO-REGISTER single-pass tracker (reviewer model): band rows update
    the column-header band; structural label rows update the section; blank rows
    change nothing; data rows receive both; each register replaces only itself."""
    ctx = {}
    band, section = [], []
    prev = None
    for j, placed in enumerate(grid):
        if not any(IH._text(c).strip() for c, _s, _e in placed):
            continue
        if INV._data_like(placed):
            ctx[j] = (list(band), list(section))
            prev = 'data'
            continue
        over_value = any(
            IH._text(c).strip() and not (s == 0 and e >= gw)
            and any(not (ne <= s or ns >= e) for ns, ne in num_cols)
            for c, s, e in placed)
        kind = 'band' if over_value else 'section'
        if kind == 'band':
            band = band + [j] if prev == 'band' else [j]
        else:
            section = section + [j] if prev == 'section' else [j]
        prev = kind
    return ctx


def _row_scope(rows, grid, zone_end, gw, ri, num_cols, ctx_map):
    """THE shared helper: the structural identity scopes of one body row —
    everything from the ACTIVE BLOCK only."""
    leftmost = min((c[1] for c in grid[ri]), default=0)
    label_cells = [IH._text(c) for c, s, e in grid[ri]
                   if IH._words(IH._text(c))
                   and (s == leftmost
                        or not any(not (ne <= s or ns >= e)
                                   for ns, ne in num_cols))]
    band, sect = ctx_map.get(ri, ([], []))
    section = [' '.join(IH._text(c) for c, _s, _e in grid[j]
                        if IH._text(c).strip()) for j in sect]
    col_headers = []
    for cell, s, e in grid[ri]:
        if not NUM.search(IH._text(cell)):
            continue
        col_headers += [IH._text(c) for j in band for c, hs, he in grid[j]
                        if not (he <= s or hs >= e)
                        and IH._text(c).strip(' —-')
                        and not IH._hidden_cell(c)
                        and not (hs == 0 and he >= gw)
                        and not (hs == 0 and s > 0)]
    caption = [IH._text(c) for j in band + sect for c, hs, he in grid[j]
               if hs == 0 and he >= gw and IH._text(c).strip()]
    return {'row_label': ' '.join(label_cells), 'section': ' '.join(section),
            'col_headers': ' '.join(col_headers), 'caption': ' '.join(caption)}


def _emit_family(rows, grid, zone_end, gw, ri, doc, ti, spans, ctx_map):
    band, sect = ctx_map.get(ri, ([], []))
    block_texts = [IH._text(rows[j]) for j in sect if IH._text(rows[j]).strip()]
    cells = []
    for cell, s, e in grid[ri]:
        txt = IH._text(cell)
        if not NUM.search(txt):
            continue
        heads = [IH._text(c) for j in band for c, hs, he in grid[j]
                 if not (he <= s or hs >= e) and IH._text(c).strip(' \u2014-')
                 and not IH._hidden_cell(c)
                 and not (hs == 0 and he >= gw)
                 and not (hs == 0 and s > 0)]
        if not heads and not block_texts:
            continue
        cells.append({'grid': [s, e], 'cell_text': txt,
                      'tokens': NUM.findall(txt),
                      'span': (list(spans[id(cell)])
                               if id(cell) in spans else None),
                      'aligned_headers_verbatim': heads,
                      'governing_section_verbatim': block_texts,
                      'column_kind': ('percent_marked' if '%' in txt
                                      or any('%' in h for h in heads)
                                      else 'unmarked_numeric')})
    return {'doc': doc, 'table_index': ti, 'row_index': ri, 'cells': cells}


def _extract(acc, raw_label):
    anchor = _wordset(raw_label)
    if not anchor:
        return None, 'abstain_no_label_words', []
    hits = []
    doc_spans = {}
    for path in _docs_of(acc):
        html = open(path, 'rb').read().decode('utf-8', 'replace')
        soup = IH._soup(html)
        spans = {}
        IH._visible_walk(soup, spans)
        doc_spans[os.path.basename(path)] = spans
        tables = [t for t in soup.find_all('table')
                  if t.find_parent('table') is None]
        for ti, table in enumerate(tables):
            rows = INV._own_rows(table)
            grid = IH._table_grid(rows)
            zone_end = next((i for i, p in enumerate(grid)
                             if INV._data_like(p)), 0)
            gw = max((e for p in grid for _c, _s, e in p), default=0)
            num_cols = _numeric_data_cols(grid, zone_end)
            ctx_map = _context_track(grid, num_cols, gw)
            for ri in range(zone_end, len(grid)):
                if not any(NUM.search(IH._text(c)) for c, _s, _e in grid[ri]):
                    continue
                scope = _row_scope(rows, grid, zone_end, gw, ri, num_cols, ctx_map)
                scope_words = _wordset(' '.join(scope.values()))
                if not anchor <= scope_words:
                    continue
                label_mech = re.sub(r'\([^)]*\)', ' ', scope['row_label'])
                row_meaning = {w for w in _wordset(label_mech)
                               if not w.isdigit()}
                if row_meaning and not row_meaning <= anchor:
                    continue        # unexplained meaning words → this row abstains
                hits.append((os.path.basename(path), ti, ri,
                             rows, grid, zone_end, gw, scope, ctx_map))
    if not hits:
        return None, 'abstain_no_row', []
    if len(hits) > 1:
        return None, 'abstain_disputed_rows', [
            {'doc': h[0], 'table_index': h[1], 'row_index': h[2],
             'row_label': h[7]['row_label'], 'section': h[7]['section'][:60],
             'caption': h[7]['caption'][:80]} for h in hits]
    doc, ti, ri, rows, grid, zone_end, gw, _scope, _ctx = hits[0]
    return (_emit_family(rows, grid, zone_end, gw, ri, doc, ti, doc_spans[doc],
                         hits[0][8]), 'accepted_row', [])


def main():
    assert hashlib.sha256(open(TRUTH, 'rb').read()).hexdigest() == TRUTH_SHA
    truth = {t['candidate_id']: t for t in map(json.loads, open(TRUTH))}
    wp1 = {json.loads(l)['item_id']: json.loads(l) for l in open(WP1)
           if json.loads(l).get('source_type') == '8k'}
    id2item = {}
    for cid, t in truth.items():
        ledger_src = json.load(open(os.path.join(_HERE, 'm2_wp1_8k_qualification.json')))
        break
    qual = json.load(open(os.path.join(_HERE, 'm2_wp1_8k_qualification.json')))

    packets = [json.loads(l) for l in
               open(os.path.join(_HERE, 'm2_candidate_packets_v2.jsonl'))]
    ledger = []
    counts = {'row_correct_full_family': 0, 'row_correct_family_diff': 0,
              'wrong': 0, 'abstain_no_row': 0, 'abstain_disputed_rows': 0}
    cvr = []
    for p in packets:
        rec = wp1[p['item_ids'][0]]
        fam, reason, disputes = _extract(rec['source_id'], rec['raw_label'])
        t = truth[p['candidate_id']]
        row = {'candidate_id': p['candidate_id'], 'ticker': p['ticker'],
               'raw_label': rec['raw_label'], 'reason': reason}
        if fam is None:
            counts[reason] = counts.get(reason, 0) + 1
            row['outcome'] = reason
            if reason == 'abstain_disputed_rows':
                row['disputed_rows'] = disputes
                if len({d['doc'] + str(d['table_index']) for d in disputes}) > 1:
                    cvr.append({'case': rec['raw_label'], 'ticker': p['ticker'],
                                'tables': disputes})
        else:
            right_row = (fam['doc'] == t['document']['file']
                         and fam['table_index'] == t['table_index']
                         and fam['row_index'] == t['row_index'])
            if not right_row:
                row.update({'outcome': 'WRONG_ROW', 'emitted': fam})
                ledger.append(row)
                json.dump({'HARD_STOP': 'wrong row emitted', 'case': row},
                          open(OUT, 'w'), indent=1, default=str)
                print('WRONG-ROW-HARD-STOP')
                sys.exit(1)
            t_cells = {tuple(c['grid']): c for c in t['headed_numeric_cells']}
            e_cells = {tuple(c['grid']): c for c in fam['cells']}
            wrong_cells = [g for g, c in e_cells.items()
                           if g not in t_cells
                           or c['tokens'] != t_cells[g]['tokens']
                           or sorted(c['aligned_headers_verbatim'])
                           != sorted(t_cells[g]['aligned_headers_verbatim'])
                           or c['governing_section_verbatim']
                           != t_cells[g]['governing_section_verbatim']
                           or c['span'] != t_cells[g]['span']]
            if wrong_cells:
                row.update({'outcome': 'WRONG_CELLS', 'wrong': wrong_cells,
                            'emitted': fam})
                ledger.append(row)
                json.dump({'HARD_STOP': 'emitted cell outside/mismatching truth',
                           'case': row}, open(OUT, 'w'), indent=1, default=str)
                print('WRONG-CELL-HARD-STOP')
                sys.exit(1)
            full = set(e_cells) == set(t_cells)
            row['outcome'] = ('row_correct_full_family' if full
                              else 'row_correct_family_diff')
            row['emitted_cells'] = len(e_cells)
            row['truth_cells'] = len(t_cells)
            counts[row['outcome']] += 1
        ledger.append(row)

    out = {'round': 3, 'claim_scope': 'TABLE GEOMETRY ONLY — real Driver slice '
           'identity unavailable until Phase 5; final identity accuracy waits',
           'anchor_inputs': 'PLACEHOLDER label words from WP1 records — Core '
           'authoritative anchor builder VERIFIED UNAVAILABLE (Track A never run); '
           'real slice-bearing anchors arrive Phase 5. NO value, NO year; &=and '
           'only; trailing-s HELD.',
           'truth_sha_verified': TRUTH_SHA,
           'ACCURACY_19_rows_headed_numeric_cells': counts,
           'consolidated_vs_regional_explicit': cvr,
           'searched_documents_pinned': {os.path.basename(k): v for k, v
                                         in sorted(_SEARCHED.items())},
           'ledger': ledger}
    json.dump(out, open(OUT, 'w'), indent=1, default=str)
    slim = {k: v for k, v in out.items()
            if k not in ('ledger', 'searched_documents_pinned')}
    slim['documents_pinned'] = len(_SEARCHED)
    slim['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps(slim, indent=1, default=str))
    print('NATIVE-TABLE-SHADOW-R3-DONE')


if __name__ == '__main__':
    main()
