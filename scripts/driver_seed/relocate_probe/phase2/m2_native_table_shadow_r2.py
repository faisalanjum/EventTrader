"""M2 NATIVE-TABLE SHADOW — ROUND 2 (audit-only; reviewer ruling 2026-07-22).

Round 1 is recorded as LOCATION-ONLY. Round 2 validates COMPLETE FACTS under his
ruling: multiple preliminary rows are ALLOWED; 'disputed' means multiple candidates
remain only AFTER the full-identity checks. The year-only refinement was REJECTED
(verified: link_lib.STOP drops 'Revenue' — 'Cargo Revenue' → ['Cargo']; Round 2
uses ALL label words, no stop-filtering).

FULL-IDENTITY CHECKS PER CANDIDATE CELL (all literal; certified machinery only —
no second header system, no vocabulary, no fuzzy matching):
  1. FULL LABEL: every word of the anchor's raw_label (plain word split, lowercased)
     appears in the row's word-bearing cells;
  2. STRUCTURE: strict header credit + complete_strict (the 3-rule classifier);
  3. PERIOD YEAR: the anchor year stands alone (\\bYYYY\\b) in the cell's strict
     header stack; the header FORM is recorded (bare_year vs embedded) — cadence
     meaning is NOT assigned;
  4. SIGN: a parenthesized/minus printed token is negative; must match the anchor
     value's sign;
  5. VALUE FORM: the printed token belongs to the anchor value's certified printed
     forms (link_lib._tableforms + at_boundary — the same law that qualified the
     truth cells).
ACCEPT = EXACTLY ONE (row, cell) filing-wide survives ALL checks; else abstain with
the surviving-candidate count. Every accept EMITS its verbatim evidence bundle
(printed token as exact unscaled Decimal, header texts, year-header form) and
EXPLICITLY declares scale/unit/cadence resolution NOT ATTEMPTED — proving those
literally requires interpreting duration/scale words (a vocabulary), which per the
ruling is a cut-trigger, so it is surfaced, never faked.
HARD STOP on any wrong acceptance against the accepted truth artifact (sha-verified
pre-run). Every searched document is pinned (path → sha256) in the report. The 20
no-truth regression records are recorded NEUTRALLY (behavior only, no win/loss).

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_native_table_shadow_r2.py
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
OUT = os.path.join(_HERE, 'm2_native_table_shadow_r2_report.json')

_BARE_YEAR = re.compile(r'^\s*(19|20)\d\d\s*$')
_SEARCHED = {}


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


def _words(label):
    return [w for w in re.findall(r'[a-z0-9&]+', label.lower())]


def _sign_of_cell(text, token):
    i = text.find(token)
    before = text[:i]
    after = text[i + len(token):]
    return -1 if (before.rstrip().endswith('(') and after.lstrip().startswith(')')
                  ) or before.rstrip().endswith('-') else 1


def _extract(acc, raw_label, year, value, fmt):
    words = _words(raw_label)
    if not words:
        return None, 'abstain_no_label_words', 0
    forms = L._tableforms(float(value), None if fmt == 'number' else fmt)
    year_pat = re.compile(rf'\b{year}\b')
    anchor_sign = -1 if Decimal(str(value)) < 0 else 1
    cands = []
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
                if not label_text or not all(w in label_text for w in words):
                    continue
                for cell, s, e in grid[ri]:
                    txt = IH._text(cell)
                    if not NUM.search(txt):
                        continue
                    tok = next((fo for fo in sorted(forms)
                                if (i := txt.find(fo)) >= 0
                                and L.at_boundary(txt, i, i + len(fo))), None)
                    if tok is None:
                        continue
                    if _sign_of_cell(txt, tok) != anchor_sign:
                        continue
                    heads = [IH._text(c) for i in range(zone_end)
                             for c, hs, he in grid[i]
                             if not (he <= s or hs >= e)
                             and IH._text(c).strip(' —-')
                             and not IH._hidden_cell(c)
                             and not (hs == 0 and he >= gw)
                             and not (hs == 0 and s > 0)]
                    if not heads or not any(year_pat.search(h) for h in heads):
                        continue
                    ctx = {'tables': {}, 'cells': {}}
                    if INV._classify_cell(cell, ctx) != 'complete_strict':
                        continue
                    year_heads = [h for h in heads if year_pat.search(h)]
                    cands.append({
                        'doc': os.path.basename(path), 'table_index': ti,
                        'row_index': ri, 'grid': [s, e], 'cell_text': txt,
                        'printed_token': tok,
                        'value_printed_exact': str(IH.parse_raw(tok)),
                        'sign': anchor_sign,
                        'headers_verbatim': heads,
                        'year_header_form': ('bare_year' if any(
                            _BARE_YEAR.match(h) for h in year_heads)
                            else 'embedded'),
                        'scale_unit_cadence_resolution': 'not_attempted_literal'})
    if not cands:
        return None, 'abstain_no_full_identity_candidate', 0
    if len(cands) > 1:
        return None, 'abstain_disputed_after_full_checks', len(cands)
    return cands[0], 'accepted', 1


def main():
    got = hashlib.sha256(open(V2, 'rb').read()).hexdigest()
    assert got == V2_SHA, f'truth artifact hash mismatch: {got}'
    packets = [json.loads(l) for l in open(V2)]
    assert len(packets) == 19
    wp1 = {}
    for l in open(WP1):
        r = json.loads(l, parse_float=Decimal)
        if r.get('source_type') == '8k':
            wp1[r['item_id']] = r

    acc_ledger = []
    counts = {'correct_complete': 0, 'wrong': 0, 'safe_abstain': 0}
    for p in packets:
        rec = wp1[p['item_ids'][0]]
        accept, reason, n_cand = _extract(
            rec['source_id'], rec['raw_label'], str(rec['period_end'])[:4],
            rec['value'], rec['fmt'])
        row = {'candidate_id': p['candidate_id'], 'ticker': p['ticker'],
               'raw_label': rec['raw_label'], 'reason': reason,
               'surviving_candidates': n_cand}
        if accept is None:
            counts['safe_abstain'] += 1
            row['outcome'] = 'safe_abstain'
        else:
            truth_ok = (accept['doc'] == p['document']['file']
                        and accept['table_index'] == p['cell']['table_index']
                        and accept['row_index'] == p['cell']['row_index']
                        and accept['grid'] == [p['cell']['grid_col_start'],
                                               p['cell']['grid_col_end']]
                        and accept['printed_token'] == p['cell']['printed_token'])
            row['accept'] = accept
            row['outcome'] = ('correct_complete_fact_bundle' if truth_ok
                              else 'WRONG_ACCEPT')
            counts['correct_complete' if truth_ok else 'wrong'] += 1
            if not truth_ok:
                acc_ledger.append(row)
                json.dump({'HARD_STOP': 'wrong acceptance against truth',
                           'case': row}, open(OUT, 'w'), indent=1, default=str)
                print('WRONG-ACCEPT-HARD-STOP')
                sys.exit(1)
        acc_ledger.append(row)

    reg_ledger = []
    qual = json.load(open(QUAL))
    for r in qual['ledger']:
        if r['bucket'] not in ('duplicate_cells', 'prose_only'):
            continue
        rec = wp1[r['item_id']]
        accept, reason, n_cand = _extract(
            rec['source_id'], rec['raw_label'], str(rec['period_end'])[:4],
            rec['value'], rec['fmt'])
        reg_ledger.append({
            'item_id': r['item_id'], 'ticker': r['ticker'],
            'raw_label': rec['raw_label'],
            'qualification_bucket': r['bucket'], 'reason': reason,
            'surviving_candidates': n_cand,
            'behavior': 'abstain' if accept is None else 'accept',
            'note': 'NEUTRAL: no truth exists for this record — behavior '
                    'recorded only, neither win nor loss',
            'accept': accept})

    reg_counts = {}
    for r in reg_ledger:
        reg_counts[r['behavior']] = reg_counts.get(r['behavior'], 0) + 1
    out = {'round': 2,
           'round1_status': 'location-only (recorded per ruling)',
           'truth_artifact_sha_verified': V2_SHA,
           'ACCURACY_19_truth_cells': counts,
           'REGRESSION_20_no_truth_NEUTRAL': reg_counts,
           'searched_documents_pinned': {os.path.basename(k): v
                                         for k, v in sorted(_SEARCHED.items())},
           'accuracy_ledger': acc_ledger, 'regression_ledger': reg_ledger}
    json.dump(out, open(OUT, 'w'), indent=1, default=str)
    slim = {k: v for k, v in out.items()
            if not k.endswith('_ledger') and k != 'searched_documents_pinned'}
    slim['documents_pinned'] = len(_SEARCHED)
    slim['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps(slim, indent=1))
    print('NATIVE-TABLE-SHADOW-R2-DONE')


if __name__ == '__main__':
    main()
