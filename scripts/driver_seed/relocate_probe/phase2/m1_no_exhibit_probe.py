"""M1 — the 573 no-exhibit canonical events: filing-text availability probe
(read-only; persisted per M1 audit round 1 item 5 — the original run wrote its result
to session tmp and the Record wrongly cited it as a repo path).

For every combined-selected event whose Report.exhibits JSON is empty, report:
  - extracted 8-K body text presence: Report-[:HAS_SECTION]->ExtractedSectionContent
    (count + total chars) — the basis for "filing text EXISTS; never call fact-absent";
  - the two URL fields and their SHAPES (audit item 6): primaryDocumentUrl (measured:
    points at the EXTRACTED *_htm.xml rendition, which Phase 1 proved drops inline
    element ids) versus linkToFilingDetails (the display filing route future body
    parsing must use).

    venv/bin/python scripts/driver_seed/relocate_probe/phase2/m1_no_exhibit_probe.py
"""
import collections
import hashlib
import json
import os

from m1_canonical_selector import _driver  # same .env plumbing; no third matcher

_HERE = os.path.dirname(os.path.abspath(__file__))
SELECTION = os.path.join(_HERE, 'm1_canonical_selection_final.jsonl')
OUT = os.path.join(_HERE, 'm1_no_exhibit_573_probe.json')

QUERY = (
    "MATCH (r:Report) WHERE r.accessionNo IN $accs "
    "OPTIONAL MATCH (r)-[:HAS_SECTION]->(sec:ExtractedSectionContent) "
    "WITH r, count(sec) AS n_sec, sum(size(coalesce(sec.content,''))) AS sec_chars "
    "RETURN r.accessionNo AS acc, n_sec, sec_chars, r.exhibits AS ex, "
    "r.primaryDocumentUrl AS primary_url, r.linkToFilingDetails AS filing_details")


def _url_shape(url):
    if not url:
        return 'absent'
    tail = url.rsplit('/', 1)[-1].lower()
    if tail.endswith('_htm.xml'):
        return 'extracted_htm_xml'
    for ext in ('.htm', '.html', '.xml', '.txt', '.pdf'):
        if tail.endswith(ext):
            return ext.lstrip('.')
    return 'other'


def main():
    accs = []
    for line in open(SELECTION):
        row = json.loads(line)
        if row['selected'] and not row['exhibits']:
            accs.append(row['accession_8k'])
    drv = _driver()
    with drv.session() as s:
        rows = [dict(r) for r in s.run(QUERY, accs=accs)]
    drv.close()

    counts = collections.Counter()
    p_shapes = collections.Counter()
    d_shapes = collections.Counter()
    sec_chars = 0
    for r in rows:
        assert not r['ex'] or json.loads(r['ex']) == {}, r['acc']
        counts['with_section_text' if r['n_sec'] else 'NO_section_text'] += 1
        sec_chars += r['sec_chars'] or 0
        p_shapes[_url_shape(r['primary_url'])] += 1
        d_shapes[_url_shape(r['filing_details'])] += 1

    result = {'no_exhibit_selected_events': len(accs), 'graph_rows': len(rows),
              'section_text': dict(counts), 'section_chars_total': sec_chars,
              'primaryDocumentUrl_shapes': dict(p_shapes),
              'linkToFilingDetails_shapes': dict(d_shapes),
              'query': QUERY,
              'sample_urls': [{'acc': r['acc'], 'primary_url': r['primary_url'],
                               'filing_details': r['filing_details']}
                              for r in sorted(rows, key=lambda x: x['acc'])[:3]],
              'rows': sorted(rows, key=lambda x: x['acc'])}
    json.dump(result, open(OUT, 'w'), indent=1, default=str)
    slim = {k: v for k, v in result.items() if k not in ('rows', 'query')}
    slim['output_sha256'] = hashlib.sha256(open(OUT, 'rb').read()).hexdigest()
    print(json.dumps(slim, indent=1))
    print('NO-EXHIBIT-PROBE-DONE')


if __name__ == '__main__':
    main()
