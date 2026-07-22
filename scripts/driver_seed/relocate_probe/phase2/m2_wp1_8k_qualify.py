"""M2 PRE-HARNESS — qualify the 40 WP1 8-K records as Route-B accuracy truth
(reviewer order 2026-07-22; harness still paused; Route C held).

Per record: find its exact VALUE in the ORIGINAL display HTML (the 8-K body via
linkToFilingDetails — the recorded URL law — plus every cached exhibit of the same
accession) using LITERAL matching only:
  * printed value forms  = the certified _tableforms(value, fmt) (WP1's own law);
  * token boundaries     = the certified at_boundary;
  * cell resolution      = DOM td/th ancestry (certified _soup walk);
  * complete evidence    = the 3-round-audited strict classifier
    (m1_structure_inventory: row label + column-proving header credit).
KEEP (qualified) only records whose form-tokens land in EXACTLY ONE real-table cell
across all searched docs AND that cell classifies complete_strict.
Prose-only, duplicate cells, incomplete row/header, or no match → regression-only.
IDENTITY GRADING (offline only, never truth-promotion): exact later XBRL twin =
later-filed 10-Q/K tagged Fact of the same company with identical numeric value and
the record's period_end under the exclusive(+1 day) law; numeric coincidence is
REPORTED, never treated as identity.

No fuzzy matching, no semantic parsing, no production edits, no reader tokens.

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m2_wp1_8k_qualify.py
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'scripts', 'driver_seed'))
sys.path.insert(0, _HERE)

import link_lib as L                                     # certified WP1 literal laws
from driver.relocation import inline_html as IH
import m1_structure_inventory as INV
from m1_canonical_selector import _driver

EX_CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')
BODY_CACHE = os.path.join(_HERE, 'm2_body_cache')
BODY_MANIFEST = os.path.join(_HERE, 'm2_body_fetch_manifest.jsonl')
OUT = os.path.join(_HERE, 'm2_wp1_8k_qualification.json')
WP1 = os.path.join(_ROOT, 'data', 'driver_catalog_seed', 'wp1', 'code_resolved.jsonl')
UA = {'User-Agent': 'EventMarketDB research faisal@example.com'}

TWIN_Q = (
    "MATCH (r8:Report {accessionNo:$acc})-[:PRIMARY_FILER]->(c:Company) "
    "MATCH (q:Report)-[:PRIMARY_FILER]->(c) "
    "WHERE q.formType IN ['10-Q','10-K'] AND q.created > r8.created "
    "MATCH (q)-[:HAS_XBRL]->(:XBRLNode)<-[:REPORTS]-(f:Fact {is_numeric:'1'}) "
    "MATCH (f)-[:HAS_PERIOD]->(p:Period) "
    "WHERE p.end_date = $period_end_exclusive "
    "RETURN q.accessionNo AS acc, f.qname AS qname, f.value AS value LIMIT 2000")


def _body_doc(acc, url):
    os.makedirs(BODY_CACHE, exist_ok=True)
    path = os.path.join(BODY_CACHE, acc.replace('/', '_') + '.htm')
    if not os.path.exists(path):
        time.sleep(0.5)
        data = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30).read()
        open(path, 'wb').write(data)
        with open(BODY_MANIFEST, 'a') as mf:
            mf.write(json.dumps({'acc': acc, 'url': url,
                                 'sha256': hashlib.sha256(data).hexdigest(),
                                 'bytes': len(data)}) + '\n')
    return path


def _cell_hits(path, forms):
    """(table_cells_hit, prose_hit_count, {cell_key: verdict}) for literal form
    tokens at boundaries — through the SHIPPED classifier."""
    html = open(path, 'rb').read().decode('utf-8', 'replace')
    soup = IH._soup(html)
    ctx = {'tables': {}, 'cells': {}}
    cells = {}
    prose = 0
    for s in soup.find_all(string=True):
        text = str(s)
        hit = False
        for fo in sorted(forms):
            i = text.find(fo)
            while i >= 0:
                if L.at_boundary(text, i, i + len(fo)):
                    hit = True
                    break
                i = text.find(fo, i + 1)
            if hit:
                break
        if not hit:
            continue
        el = s.parent
        node = el
        skip = False
        while node is not None and getattr(node, 'name', None):
            nm = node.name.lower()
            if nm in INV._SKIP_TAGS or nm == 'ix:hidden' or IH._hidden_cell(node):
                skip = True
                break
            node = node.parent
        if skip:
            continue
        cell = el if el.name in ('td', 'th') else el.find_parent(['td', 'th'])
        if cell is not None and cell.find_parent('table') is not None:
            key = (os.path.basename(path), id(cell))
            cells[key] = (INV._classify_cell(cell, ctx),
                          IH._text(cell)[:40],
                          IH._text(cell.find_parent('tr'))[:90])
        else:
            prose += 1
    return cells, prose


def main():
    recs = [json.loads(l) for l in open(WP1)
            if json.loads(l).get('source_type') == '8k']
    assert len(recs) == 40, len(recs)
    drv = _driver()
    with drv.session() as s:
        meta = {r['acc']: r['url'] for r in s.run(
            "MATCH (r:Report) WHERE r.accessionNo IN $accs "
            "RETURN r.accessionNo AS acc, r.linkToFilingDetails AS url",
            accs=sorted({r['source_id'] for r in recs}))}

    ledger = []
    counts = {}
    with drv.session() as s:
        for r in recs:
            acc = r['source_id']
            fmt = None if r['fmt'] == 'number' else r['fmt']
            forms = L._tableforms(float(r['value']), fmt)
            docs = []
            if meta.get(acc):
                try:
                    docs.append(_body_doc(acc, meta[acc]))
                except Exception as e:
                    ledger_err = type(e).__name__
            docs += [os.path.join(EX_CACHE, f) for f in os.listdir(EX_CACHE)
                     if f.startswith(acc + '__')]
            all_cells = {}
            prose = 0
            for d in docs:
                c, p = _cell_hits(d, forms)
                all_cells.update(c)
                prose += p
            row = {'item_id': r['item_id'], 'ticker': r['ticker'],
                   'raw_label': r['raw_label'], 'value': r['value'],
                   'fmt': r['fmt'], 'acc': acc, 'docs_searched': len(docs),
                   'table_cells_hit': len(all_cells), 'prose_hits': prose}
            if not all_cells and not prose:
                row['bucket'] = 'no_match'
            elif not all_cells:
                row['bucket'] = 'prose_only'
            elif len(all_cells) > 1:
                row['bucket'] = 'duplicate_cells'
            else:
                (key, (verdict, cell_txt, row_txt)), = all_cells.items()
                row.update({'doc': key[0], 'cell_text': cell_txt,
                            'row_text': row_txt, 'cell_verdict': verdict})
                row['bucket'] = ('qualified' if verdict == 'complete_strict'
                                 else 'incomplete_row_header')
            if row['bucket'] == 'qualified':
                # offline twin grading only — exclusive(+1d) period law
                from datetime import date, timedelta
                pe = date.fromisoformat(r['period_end']) + timedelta(days=1)
                twins = [t for t in s.run(TWIN_Q, acc=acc,
                                          period_end_exclusive=pe.isoformat())
                         if IH.parse_raw(t['value']) is not None
                         and IH.parse_raw(t['value']) == Decimal(r['value'])]
                row['twin_exact_value_period'] = len(twins)
                row['twin_sample'] = ([{'acc': twins[0]['acc'],
                                        'qname': twins[0]['qname']}]
                                      if twins else [])
            ledger.append(row)
            counts[row['bucket']] = counts.get(row['bucket'], 0) + 1
    drv.close()

    out = {'records': len(recs), 'buckets': counts, 'ledger': ledger}
    json.dump(out, open(OUT, 'w'), indent=1)
    slim = dict(out)
    slim.pop('ledger')
    slim['qualified_with_twin'] = sum(
        1 for r in ledger if r.get('bucket') == 'qualified'
        and r.get('twin_exact_value_period', 0) > 0)
    slim['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps(slim, indent=1))
    print('WP1-8K-QUALIFY-DONE')


if __name__ == '__main__':
    main()
