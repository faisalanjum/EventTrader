"""PHASE-2 M1 SOURCE-STRUCTURE INVENTORY (FinalPlan §8 M1; read-only, no tokens).

Measures, from SOURCE STRUCTURE (DOM), for every on-disk earnings-8-K exhibit:
numeric occurrences in real <table> elements versus paragraphs/lists/other prose, and
— for table occurrences — complete row + header stack versus incomplete/ambiguous.

TWO POPULATIONS, NEVER MIXED (two-corpus doctrine):
  CANONICAL DECISION = the combined-selected events' HTML exhibits from
    m1_canonical_selection_final.jsonl (sha db73a0cd…; selector ACCEPTED audit r2).
  BROAD STRESS = the fetched rows of m1_8k_fetch_manifest.jsonl — structural failure
    modes ONLY, never accuracy evidence.
Files are parsed once (shared cache); aggregation is per population.

DECLARED DEFINITIONS (classification from structure, not text punctuation):
  * numeric token = the transcript census NUM pattern (m1_transcript_census.py) applied
    to visible DOM text — the SAME recognizer across sources for comparability; it
    recognizes tokens, it decides nothing.
  * visibility = the certified hidden law (inline_html._hidden_cell ancestry +
    ix:hidden) PLUS <script>/<style> exclusion (declared addition: exhibits may embed
    code; the certified display-doc walker never met it).
  * table vs prose = <table> DOM ancestry of the text node; prose = everything else.
    DECLARED LIMIT: some filers wrap entire documents in LAYOUT tables — those
    numerics measure as table occurrences (DOM truth) and overwhelmingly classify
    ambiguous; read 'ambiguous' with that in mind.
  * HEADER ZONE (the structural analog of the certified _aligned_columns, whose
    data-row skip keys off ix-tag presence that untagged exhibits lack): a row is
    DATA-LIKE iff its leftmost occupied grid cell carries word text AND any other
    cell carries a numeric token (the label+numbers shape). The header zone = the
    maximal PREFIX of rows before the first data-like row (empty if the first row is
    data-like or none is). Position + shape only — no vocabulary, no punctuation.
    Hand-verified on a real filing: 'Q1 2023 | Q1 2022 | Y/Y' rows land in the zone;
    'Revenue ($M) | $5,353 | …' rows do not.
    DECLARED MISS, conservative: a header row whose corner cell carries its own label
    ('($ in millions) | 2024 | 2023') is shape-identical to a data row and is NOT
    credited → such tables under-count complete. The opposite choice would credit
    genuine data rows and overstate — worse for a zero-wrong-accept decision.
  * token in a header-zone cell → 'header_zone' (labels, counted separately, never
    complete/ambiguous).
  * complete table occurrence (body rows only) = its cell satisfies BOTH:
      (a) row label — some other same-row cell carries word text;
      (b) STRICT header credit — a header-zone row has a non-empty, non-hidden cell
          overlapping the cell's column range (colspan-aware via the certified
          _table_grid; numeric-only header cells like a bare year RETAINED) that
          PROVES THE SPECIFIC COLUMN, meaning BOTH:
            - NOT full-grid-width (`start == 0 and end >= grid_width`): a heading
              spanning every column ('Condensed Consolidated Balance Sheets',
              'FY 2026E') can never prove one specific column — including for a
              target that starts at grid column 0 (audit-round-2 catch: the
              left-anchor guard alone never fires for leftmost targets);
            - NOT left-anchored while the target is not (the certified
              _aligned_columns guard `start == 0 and target_start > 0`,
              inline_html.py:147 — retained as well).
          Audit history: run 1 omitted both; run 2 added only the certified guard;
          run 3 adds the full-grid rule. Pinned RED-first in
          test_m1_structure_inventory.py on real AAP/AMD/AA cells.
    Everything else in a table body = incomplete/ambiguous.
  * TRANSITION REPORTING (audit item 3): each body-cell verdict is computed under
    BOTH rules — old (any overlapping credit) and strict — and reported as
    complete_strict (complete→complete), complete_unproven_column
    (complete→ambiguous: no credit cell proves the specific column — full-grid
    and/or guarded-left-anchored credits only), ambiguous (unchanged), header_zone
    (unchanged).
  * nested tables: a row belongs only to its nearest enclosing table.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m1_structure_inventory.py
"""
import hashlib
import json
import multiprocessing
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from m1_transcript_census import NUM                      # the one shared recognizer
from driver.relocation import inline_html as IH           # certified machinery

CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
SELECTION = os.path.join(_HERE, 'm1_canonical_selection_final.jsonl')
BROAD_MANIFEST = os.path.join(_HERE, 'm1_8k_fetch_manifest.jsonl')
CANON_MANIFEST = os.path.join(_HERE, 'm1_canonical_fetch_manifest.jsonl')
RECORDS = os.path.join(_HERE, 'm1_structure_inventory_records.jsonl')
SUMMARY = os.path.join(_HERE, 'm1_structure_inventory_summary.json')

_SKIP_TAGS = {'script', 'style'}


def _own_rows(table):
    return [tr for tr in table.find_all('tr') if tr.find_parent('table') is table]


def _data_like(placed):
    if not placed:
        return False
    leftmost = min(placed, key=lambda item: item[1])[0]
    if not IH._words(IH._text(leftmost)):
        return False
    return any(cell is not leftmost and NUM.search(IH._text(cell))
               for cell, _s, _e in placed)


def _table_ctx(cell, ctx):
    table = cell.find_parent('table')
    if table is None:
        return None
    tid = id(table)
    if tid not in ctx['tables']:
        rows = _own_rows(table)
        grid = IH._table_grid(rows)
        zone_end = next((i for i, placed in enumerate(grid) if _data_like(placed)), 0)
        grid_width = max((e for placed in grid for _c, _s, e in placed), default=0)
        ctx['tables'][tid] = (rows, grid, zone_end, grid_width)
    return ctx['tables'][tid]


def _classify_cell(cell, ctx):
    key = id(cell)
    if key in ctx['cells']:
        return ctx['cells'][key]
    verdict = 'ambiguous'
    entry = _table_ctx(cell, ctx)
    if entry is not None:
        rows, grid, zone_end, grid_width = entry
        tr = cell.find_parent('tr')
        row_idx = next((i for i, r in enumerate(rows) if r is tr), None)
        if row_idx is not None:
            if row_idx < zone_end:
                verdict = 'header_zone'
            else:
                target = next(((s, e) for c, s, e in grid[row_idx] if c is cell),
                              None)
                if target:
                    t_start, t_end = target
                    row_label = any(
                        c is not cell and IH._words(IH._text(c))
                        for c, _s, _e in grid[row_idx])
                    credit_any = credit_strict = False
                    for i in range(zone_end):
                        for c, s, e in grid[i]:
                            if (e <= t_start or s >= t_end) \
                                    or not IH._text(c).strip(' —-') \
                                    or IH._hidden_cell(c):
                                continue
                            credit_any = True
                            if (s == 0 and e >= grid_width):  # full-grid: proves no column
                                continue
                            if not (s == 0 and t_start > 0):  # inline_html.py:147
                                credit_strict = True
                    if row_label and credit_strict:
                        verdict = 'complete_strict'
                    elif row_label and credit_any:
                        verdict = 'complete_unproven_column'
    ctx['cells'][key] = verdict
    return verdict


def inspect(path):
    rec = {'file': os.path.basename(path)}
    try:
        raw = open(path, 'rb').read()
        rec['bytes'] = len(raw)
        rec['sha256'] = hashlib.sha256(raw).hexdigest()
        soup = IH._soup(raw.decode('utf-8', 'replace'))
        ctx = {'tables': {}, 'cells': {}}
        tok_table = tok_prose = strict = banner_only = ambiguous = header_zone = 0
        for s in soup.find_all(string=True):
            n = len(NUM.findall(s))
            if not n:
                continue
            el = s.parent
            skip = False
            node = el
            while node is not None and getattr(node, 'name', None):
                nm = node.name.lower()
                if nm in _SKIP_TAGS or nm == 'ix:hidden' or IH._hidden_cell(node):
                    skip = True
                    break
                node = node.parent
            if skip:
                continue
            cell = el if el.name in ('td', 'th') else el.find_parent(['td', 'th'])
            if cell is not None and cell.find_parent('table') is not None:
                tok_table += n
                verdict = _classify_cell(cell, ctx)
                if verdict == 'complete_strict':
                    strict += n
                elif verdict == 'complete_unproven_column':
                    banner_only += n
                elif verdict == 'header_zone':
                    header_zone += n
                else:
                    ambiguous += n
            else:
                tok_prose += n
        rec.update({'parse_ok': True, 'tokens_table': tok_table,
                    'tokens_prose': tok_prose, 'table_complete_strict': strict,
                    'table_complete_unproven_column': banner_only,
                    'table_ambiguous': ambiguous, 'table_header_zone': header_zone,
                    'n_tables': len(ctx['tables'])})
    except Exception as e:
        rec.update({'parse_ok': False, 'parse_error': type(e).__name__})
    return rec


def _agg(keys, by_file, label):
    out = {'population': label, 'files_expected': len(keys), 'files_on_disk': 0,
           'parse_ok': 0, 'parse_errors': {}, 'bytes': 0, 'tokens_table': 0,
           'tokens_prose': 0, 'table_complete_strict': 0,
           'table_complete_unproven_column': 0, 'table_ambiguous': 0,
           'table_header_zone': 0, 'n_tables': 0, 'files_missing': 0}
    for key in keys:
        rec = by_file.get(key.replace('/', '_') + '.htm')
        if rec is None:
            out['files_missing'] += 1
            continue
        out['files_on_disk'] += 1
        out['bytes'] += rec.get('bytes', 0)
        if rec.get('parse_ok'):
            out['parse_ok'] += 1
            for field in ('tokens_table', 'tokens_prose', 'table_complete_strict',
                          'table_complete_unproven_column', 'table_ambiguous',
                          'table_header_zone', 'n_tables'):
                out[field] += rec[field]
        else:
            err = rec.get('parse_error', '?')
            out['parse_errors'][err] = out['parse_errors'].get(err, 0) + 1
    out['transition_old_to_new'] = {
        'complete->complete': out['table_complete_strict'],
        'complete->ambiguous (unproven column credit)': out['table_complete_unproven_column'],
        'ambiguous->ambiguous': out['table_ambiguous'],
        'header_zone->header_zone': out['table_header_zone']}
    return out


def main():
    t0 = time.time()
    canon_keys = []
    for line in open(SELECTION):
        row = json.loads(line)
        if row['selected']:
            for e in row['exhibits'] or []:
                if e['cls'] == 'html':
                    canon_keys.append(f"{row['accession_8k']}__{e['num']}")
    broad_keys = [r['key'] for r in map(json.loads, open(BROAD_MANIFEST))
                  if r['status'] == 'fetched']
    canon_fetch = {r['key']: r['status'] for r in map(json.loads, open(CANON_MANIFEST))} \
        if os.path.exists(CANON_MANIFEST) else {}

    union = sorted({k.replace('/', '_') + '.htm' for k in canon_keys + broad_keys})
    paths = [os.path.join(CACHE, f) for f in union]
    paths = [p for p in paths if os.path.exists(p)]
    print(f'canonical html {len(canon_keys)} · broad fetched {len(broad_keys)} '
          f'· union files on disk {len(paths)}', flush=True)

    records = []
    with multiprocessing.Pool(6) as pool:
        for i, rec in enumerate(pool.imap_unordered(inspect, paths, chunksize=25)):
            records.append(rec)
            if (i + 1) % 1000 == 0:
                print(f'{i + 1}/{len(paths)}', flush=True)
    records.sort(key=lambda r: r['file'])
    with open(RECORDS, 'w') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')
    by_file = {r['file']: r for r in records}

    summary = {
        'CANONICAL_DECISION': _agg(canon_keys, by_file, 'canonical (decision-grade)'),
        'BROAD_STRESS': _agg(broad_keys, by_file,
                             'broad stress (structural only — NEVER accuracy evidence)'),
        'canonical_fetch_statuses': {
            s: sum(1 for v in canon_fetch.values() if v == s)
            for s in sorted(set(canon_fetch.values()))},
        'records': RECORDS,
        'records_sha256': hashlib.sha256(open(RECORDS, 'rb').read()).hexdigest(),
        'secs': round(time.time() - t0),
    }
    json.dump(summary, open(SUMMARY, 'w'), indent=1)
    print(json.dumps(summary, indent=1), flush=True)
    print('STRUCTURE-INVENTORY-DONE', flush=True)


if __name__ == '__main__':
    main()
