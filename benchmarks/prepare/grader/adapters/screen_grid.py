"""Screen-span step (an allowed small adapter, PrepareStep.md P20/T1): the labellers' guide says a header covers a value
when the value sits inside the header's span ON SCREEN (guide 3.5 rule 3). DOM colspans can disagree with the screen
(spacer columns, hidden cells), and every HTML tool inherits the DOM grid. This step renders the original in headless
Chrome, measures every table cell's box, derives screen columns from the pixel edges, and re-grids a route's table
cells by their byte anchors. It changes no text and no anchor. Rules are geometric only.

    <python with playwright> -m benchmarks.prepare.grader.adapters.screen_grid --key <key package> --route <route dir> --out <route dir> [--catalog CSV]"""
import argparse
import json
import re
import time
from bisect import bisect_right
from pathlib import Path

from benchmarks.prepare.grader import grade

_CELL = re.compile(rb'(?i)<t([dh])\b')
TOL = 2  # pixels: edges closer than this are the same column edge


def tag_cells(raw):
    """A copy with data-g="n" on every <td>/<th> (document order) and the byte span of each cell in the original."""
    out, spans, pos = [], [], 0
    for n, m in enumerate(_CELL.finditer(raw)):
        close = re.compile(rb'(?i)</t' + m.group(1) + rb'\s*>').search(raw, m.end())
        nxt = _CELL.search(raw, m.end())
        end = close.end() if close and (nxt is None or close.start() < nxt.start()) else (nxt.start() if nxt else len(raw))
        spans.append((m.start(), end)); out.append(raw[pos:m.end()]); out.append(b' data-g="%d"' % n); pos = m.end()
    out.append(raw[pos:])
    return b''.join(out), spans


def screen_grid(cells):
    """{g: (row, column, span)} from measured boxes of one table: columns are the distinct left edges of visible cells."""
    shown = [c for c in cells if c['w'] > 0]
    edges = []
    for x in sorted(c['x'] for c in shown):
        if not edges or x - edges[-1] > TOL: edges.append(x)
    grid = {}
    for c in shown:
        col = max(i for i, e in enumerate(edges) if e <= c['x'] + TOL)
        span = sum(1 for e in edges[col + 1:] if e < c['x'] + c['w'] - TOL) + 1
        grid[c['g']] = (c['row'], col, span)
    return grid


def apply(units, spans, measured_by_table):
    """Re-grid the route's table cells whose byte anchors fall in a measured cell; returns how many changed."""
    starts = [s for s, _ in spans]; by_g = {}
    for table_cells in measured_by_table.values():
        for g, (r, c, cs) in screen_grid(table_cells).items(): by_g[g] = (r, c, cs)
    n = 0
    for u in units:
        if u.get('kind') != 'table': continue
        for cell in u.get('cells') or []:
            a = cell.get('anchor'); a = a[0] if isinstance(a, list) else a
            if not isinstance(a, dict) or 'byte_start' not in a: continue
            g = bisect_right(starts, a['byte_start']) - 1
            if g < 0 or not (spans[g][0] <= a['byte_start'] < spans[g][1]) or g not in by_g: continue
            r, c, cs = by_g[g]
            if (cell['r'], cell['c'], cell.get('cs', 1)) != (r, c, cs): cell.update(r=r, c=c, cs=cs); n += 1
            cell['grid'] = 'screen'
    return n


JS = """() => { const tables = Array.from(document.querySelectorAll('table')); const out = [];
  for (const el of document.querySelectorAll('[data-g]')) { const r = el.getBoundingClientRect(); const t = el.closest('table');
    out.push({g: +el.dataset.g, table: tables.indexOf(t), row: el.parentElement ? el.parentElement.rowIndex : -1, x: r.left, w: r.width}); }
  return out; }"""


def measure(marked_html, browser):
    """Boxes of every tagged cell as Chrome lays the document out (the document's own styles, a wide window)."""
    page = browser.new_page(viewport={'width': 1400, 'height': 1000})
    try:
        page.set_content(marked_html.decode('utf-8', 'replace'), wait_until='load'); rows = page.evaluate(JS)
    finally:
        page.close()
    by_table = {}
    for c in rows: by_table.setdefault(c['table'], []).append(c)
    return by_table


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--route', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright
    paths = {}
    for t in grade.load_key(a.key, a.catalog): paths.setdefault(t['file_id'], t['path'])
    src, out = Path(a.route), Path(a.out); facts = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for rp in sorted(src.rglob('*.json')):
            d = json.loads(rp.read_text()); fid = d['file_id']; dest = out / rp.relative_to(src); dest.parent.mkdir(parents=True, exist_ok=True)
            if d.get('status') != 'OK' or not fid.lower().endswith(('.htm', '.html')): dest.write_text(json.dumps(d, ensure_ascii=False)); continue
            t0 = time.time(); marked, spans = tag_cells(paths[fid].read_bytes())
            try: measured = measure(marked, browser)
            except Exception as e: facts[fid] = {'error': repr(e)[:200]}; dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True); continue
            n = apply(d['units'], spans, measured); d['route'] = dict(d['route'], name=d['route']['name'] + '+screen', settings=dict(d['route'].get('settings') or {}, screen_grid=True))
            facts[fid] = {'cells_regridded': n, 'cells_measured': sum(len(v) for v in measured.values()), 'seconds': round(time.time() - t0, 1)}
            dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True)
        browser.close()
    (out / 'screen_facts.json').write_text(json.dumps(facts, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
