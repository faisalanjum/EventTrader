"""M2 NATIVE-TABLE SHADOW HARNESS — audit-only (reviewer GO 2026-07-22).

Shadows the PROPOSED Route-B contract (FinalPlan §5B: accept only a true
source-native row with its complete header stack and an unambiguous cell; original
exhibit HTML; everything else abstains) against the ACCEPTED 19-case truth set.
No production edits; Route C held.

THE SHADOW EXTRACTOR (declared; every law reused, nothing new):
  anchor  = {label tokens via link_lib._toks(raw_label) · year = period_end[:4]}
  docs    = the WHOLE filing (8-K body cache + every cached exhibit of the accession)
  row     = body rows (below the header zone) whose word-bearing cells contain ALL
            anchor label tokens (case-insensitive; the existing token law) —
            EXACTLY ONE such row across the filing or abstain;
  cell    = numeric cells of that row whose STRICT header stack (certified 3-rule
            credit: overlap · non-full-grid · certified left-anchor guard) contains
            the anchor year as a standalone token, AND which classify
            complete_strict — EXACTLY ONE such cell or abstain.
  accept  = (doc, table_index, row_index, grid range, printed token); else abstain.

REVIEWER REQUIREMENTS ENFORCED:
  * verifies the ACCEPTED v2 truth artifact hash before anything runs;
  * per-document byte hashes re-verified against each packet;
  * accuracy denominator = 19 CELLS (the merged AAL Cargo pair counts once);
  * regression ledger kept COMPLETELY SEPARATE: the 20 non-qualified WP1 8-K
    records (11 duplicate-cell + 9 prose-only) where honest behavior is abstain —
    accepts there carry no truth and are LISTED for audit, never auto-judged;
  * HARD STOP on any wrong acceptance against truth (wrong cell or wrong token).

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_native_table_shadow.py
"""
import hashlib
import json
import os
import re
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
from m1_transcript_census import NUM

EX_CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
BODY_CACHE = os.path.join(_HERE, 'm2_body_cache')
V2 = os.path.join(_HERE, 'm2_candidate_packets_v2.jsonl')
V2_SHA = '5aff53ccb3a3a71ef7b1cc747b219cbd6e75b7918de8c4141fbf8cd8e2d9dc9e'
QUAL = os.path.join(_HERE, 'm2_wp1_8k_qualification.json')
WP1 = os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'wp1', 'code_resolved.jsonl')
OUT = os.path.join(_HERE, 'm2_native_table_shadow_report.json')


def _docs_of(acc):
    docs = []
    body = os.path.join(BODY_CACHE, acc.replace('/', '_') + '.htm')
    if os.path.exists(body):
        docs.append(body)
    docs += sorted(os.path.join(EX_CACHE, f) for f in os.listdir(EX_CACHE)
                   if f.startswith(acc + '__'))
    return docs


def _extract(acc, raw_label, year):
    """The declared shadow extractor. Returns (accept_dict|None, reason)."""
    toks = [t.lower() for t in (L._toks(raw_label)
                                or re.findall(r"[A-Za-z0-9&]{2,}", raw_label))]
    if not toks:
        return None, 'abstain_no_label_tokens'
    row_hits = []
    for path in _docs_of(acc):
        soup = IH._soup(open(path, 'rb').read().decode('utf-8', 'replace'))
        tables = [t for t in soup.find_all('table')
                  if t.find_parent('table') is None]
        for ti, table in enumerate(tables):
            rows = INV._own_rows(table)
            grid = IH._table_grid(rows)
            zone_end = next((i for i, p in enumerate(grid)
                             if INV._data_like(p)), 0)
            gw = max((e for p in grid for _c, _s, e in p), default=0)
            for ri in range(zone_end, len(grid)):
                label_text = ' '.join(
                    IH._text(c) for c, _s, _e in grid[ri]
                    if IH._words(IH._text(c))).lower()
                if not label_text or not all(t in label_text for t in toks):
                    continue
                row_hits.append((os.path.basename(path), ti, ri,
                                 rows, grid, zone_end, gw))
    if not row_hits:
        return None, 'abstain_no_labeled_row'
    if len(row_hits) > 1:
        return None, 'abstain_multiple_labeled_rows'
    doc, ti, ri, rows, grid, zone_end, gw = row_hits[0]
    year_pat = re.compile(rf'\b{year}\b')
    cands = []
    for cell, s, e in grid[ri]:
        txt = IH._text(cell)
        if not NUM.search(txt):
            continue
        heads = [IH._text(c) for i in range(zone_end) for c, hs, he in grid[i]
                 if not (he <= s or hs >= e) and IH._text(c).strip(' —-')
                 and not IH._hidden_cell(c)
                 and not (hs == 0 and he >= gw)
                 and not (hs == 0 and s > 0)]
        if not heads or not any(year_pat.search(h) for h in heads):
            continue
        ctx = {'tables': {}, 'cells': {}}
        if INV._classify_cell(cell, ctx) != 'complete_strict':
            continue
        tok = NUM.findall(txt)
        cands.append({'doc': doc, 'table_index': ti, 'row_index': ri,
                      'grid': [s, e], 'cell_text': txt,
                      'printed_tokens': tok, 'headers': heads})
    if not cands:
        return None, 'abstain_no_year_proven_cell'
    if len(cands) > 1:
        return None, 'abstain_multiple_year_cells'
    return cands[0], 'accepted'


def main():
    got = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
    assert got == V2_SHA, f'v2 truth artifact hash mismatch: {got}'
    packets = [json.loads(l) for l in open(V2)]
    assert len(packets) == 19
    wp1 = {}
    for l in open(WP1):
        r = json.loads(l, parse_float=Decimal)
        if r.get('source_type') == '8k':
            wp1[r['item_id']] = r
    for p in packets:  # per-document integrity vs the accepted packets
        path = os.path.join(EX_CACHE, p['document']['file'])
        if not os.path.exists(path):
            path = os.path.join(BODY_CACHE, p['document']['file'])
        assert hashlib.sha256(open(path, 'rb').read()).hexdigest() == \
            p['document']['bytes_sha256'], p['document']['file']

    acc_ledger = []
    counts = {'correct': 0, 'wrong': 0, 'safe_abstain': 0}
    for p in packets:
        rec = wp1[p['item_ids'][0]]
        accept, reason = _extract(rec['source_id'], rec['raw_label'],
                                  str(rec['period_end'])[:4])
        row = {'candidate_id': p['candidate_id'], 'ticker': p['ticker'],
               'raw_label': rec['raw_label'], 'reason': reason}
        if accept is None:
            counts['safe_abstain'] += 1
            row['outcome'] = 'safe_abstain'
        else:
            truth_ok = (accept['doc'] == p['document']['file']
                        and accept['table_index'] == p['cell']['table_index']
                        and accept['row_index'] == p['cell']['row_index']
                        and accept['grid'] == [p['cell']['grid_col_start'],
                                               p['cell']['grid_col_end']]
                        and p['cell']['printed_token'] in accept['printed_tokens'])
            row['accept'] = accept
            row['outcome'] = 'correct' if truth_ok else 'WRONG_ACCEPT'
            counts['correct' if truth_ok else 'wrong'] += 1
            if not truth_ok:
                acc_ledger.append(row)
                json.dump({'HARD_STOP': 'wrong acceptance against truth',
                           'case': row, 'counts': counts},
                          open(OUT, 'w'), indent=1, default=str)
                print(json.dumps(row, indent=1, default=str))
                print('WRONG-ACCEPT-HARD-STOP')
                sys.exit(1)
        acc_ledger.append(row)

    reg_ledger = []
    qual = json.load(open(QUAL))
    for r in qual['ledger']:
        if r['bucket'] not in ('duplicate_cells', 'prose_only'):
            continue
        rec = wp1[r['item_id']]
        accept, reason = _extract(rec['source_id'], rec['raw_label'],
                                  str(rec['period_end'])[:4])
        reg_ledger.append({'item_id': r['item_id'], 'ticker': r['ticker'],
                           'raw_label': rec['raw_label'],
                           'qualification_bucket': r['bucket'],
                           'reason': reason,
                           'outcome': ('abstain' if accept is None
                                       else 'ACCEPT_NO_TRUTH_for_audit'),
                           'accept': accept})

    reg_counts = {}
    for r in reg_ledger:
        reg_counts[r['outcome']] = reg_counts.get(r['outcome'], 0) + 1
    out = {'truth_artifact_sha_verified': V2_SHA,
           'ACCURACY_19_truth_cells': counts,
           'REGRESSION_20_records_no_truth_separate': reg_counts,
           'accuracy_ledger': acc_ledger, 'regression_ledger': reg_ledger}
    json.dump(out, open(OUT, 'w'), indent=1, default=str)
    slim = {k: v for k, v in out.items() if not k.endswith('_ledger')}
    slim['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps(slim, indent=1))
    print('NATIVE-TABLE-SHADOW-DONE')


if __name__ == '__main__':
    main()
