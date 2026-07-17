#!/usr/bin/env python3
"""EXACT-CELL lock (#767 step 2/3) — the TOP rung of the LOCK ladder, never a replacement.

LADDER (each rung falls through to the next; nothing removed):
  1. exact-cell (this file): inline-XBRL anchors the known fact to its printed CELL ->
     row / column / section in the FILER'S OWN WORDS. Only possible for 10-K/10-Q (they
     carry ix: tags). Needs the filing HTML from SEC EDGAR (cached).
  2. text-scan lock (link_lib.scan_text strict) — works on any source.
  3. skip (no lock, pair not built).

Extractor = the head-to-head-verified one (benchmark/multiaxis_pool/final/lock_row_extract.py,
SHA 38690c7b): plain HTML rules (colspan/rowspan), zero company rules; non-unique fact -> None.
"""
import os, re, sys, time, json, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, f'{HERE}/benchmark/multiaxis_pool/final')
CACHE = f'{HERE}/inline_html_cache'
UA = {'User-Agent': 'EventMarketDB research faisal@example.com'}
_last_fetch = [0.0]


def fetch_inline_html(url, accession):
    """EDGAR inline-XBRL doc, cached by accession; polite >=0.5s spacing; None on failure.
    Graph URLs point at the raw XBRL instance (_htm.xml) — the extractor needs the INLINE HTML."""
    url = url.replace('_htm.xml', '.htm')
    os.makedirs(CACHE, exist_ok=True)
    path = f"{CACHE}/{accession.replace('/', '_')}.htm"
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        return path
    wait = 0.5 - (time.time() - _last_fetch[0])
    if wait > 0:
        time.sleep(wait)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        _last_fetch[0] = time.time()
        if len(data) < 10000:
            return None
        open(path, 'wb').write(data)
        return path
    except Exception:
        _last_fetch[0] = time.time()
        return None


def _resolve_concept(html_path, concept):
    """bare local name -> the doc's own full qname, ONLY if unique in the doc; else as-given."""
    if ':' in concept:
        return concept
    local = concept.lower()
    names = set(re.findall(r'ix:nonfraction[^>]*?name="([^"]+)"', open(html_path, errors='replace').read(), re.I))
    hits = {n for n in names if n.split(':')[-1].lower() == local}
    return next(iter(hits)) if len(hits) == 1 else concept


def exact_cell(html_path, concept_qname, start, end, pairs):
    """{'section','row','column','nearby_anchor'} for the UNIQUE matching fact, else None.
    pairs = [(dimension_qname, member_qname), ...]. Safe-abstains (None) on any ambiguity."""
    try:
        import lock_row_extract as X
        out = X.extract(html_path, _resolve_concept(html_path, concept_qname), start, end,
                        [tuple(p) for p in pairs])
        sw = dict(out['source_words'])
        sw['row_cells'] = out.get('evidence', {}).get('row_cells', [])   # verbatim row WITH numbers
        return sw
    except (SystemExit, Exception):
        return None                     # non-unique / hidden / parse failure -> next rung


def cell_address(sw, label_tokens, measurement='', lock_quote=''):
    """address from exact-cell source words. HYBRID (user design 2026-07-14, A/B: +4 fixed −1 on the
    23 hardest): cell labels carry IDENTITY (caption=section, siblings=row+column words) while
    lock_row keeps the VERBATIM BLOB with its number — the reader's consistency rule #4 needs it."""
    row, col, sec = sw.get('row', ''), sw.get('column', ''), sw.get('section', '')
    sib = sorted({w.lower() for w in re.findall(r"[A-Za-z][A-Za-z&'-]{2,}", f'{row} {col}')})
    return {'label': label_tokens, 'caption': (sec or sw.get('nearby_anchor', ''))[:120],
            'siblings': sib[:40], 'unit': 'currency',
            'lock_row': lock_quote or f"{sec} | {row} | {col}".strip(' |'), 'measurement': measurement}


if __name__ == '__main__':
    rows = [json.loads(l) for l in open(f'{HERE}/benchmark/multiaxis_pool/truth_pool.jsonl')]
    r = rows[0]['lock']
    url = r['primary_document_url'].replace('_htm.xml', '.htm')
    p = fetch_inline_html(url, r['accession'])
    assert p, 'fetch failed'
    sw = exact_cell(p, r['concept_qname'], r['period_start'], r['period_end'],
                    [(f['axis_qname'], f['member_qname']) for f in r['facets']])
    print('source_words:', json.dumps(sw))
    assert sw and sw.get('row'), 'exact-cell lock failed on the known-good EQR case'
    print('lock_cell self-check OK:', cell_address(sw, ['operating', 'lease', 'income'], 'gaap')['lock_row'])
