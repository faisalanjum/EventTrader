"""Screen-span step (an allowed small adapter, PrepareStep.md P20/T1): the labellers' guide says a header covers a value
when the value sits inside the header's span ON SCREEN (guide 3.5 rule 3). DOM colspans can disagree with the screen
(spacer columns, hidden cells), and every HTML tool inherits the DOM grid. This step renders the original in headless
Chrome, measures every table cell's box, derives screen columns from the pixel edges, and re-grids a route's table
cells by their byte anchors, and joins a word or number the tool printed with a space the source does not have where Chrome shows its two
characters touching on one line (a space the tool adds across inline markup: `CORP ORATION` over an iXBRL tag; the page alone can tell that from
a gap its styles make). It changes no anchor; the joined text records where its spaces were. Rules are geometric only.

    <python with playwright> -m benchmarks.prepare.grader.adapters.screen_grid --key <key package> --route <route dir> --out <route dir> [--catalog CSV]"""
import argparse
import json
import re
import time
from bisect import bisect_right
from pathlib import Path

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.anchor import Visible

_CELL_END = re.compile(rb'(?i)</t[dh]\s*>')
TOL = 2  # pixels: edges closer than this are the same column edge


def gaps_of(vis, units):
    """Every space the tool added inside a word or number, per item: [(item, text start, text end, search-form index before, after)] (grade.tool_spaces)."""
    return [(x, a, b, k, l) for u in units for x in ((u.get('cells') or []) if u.get('kind') == 'table' else [u]) for a, b, k, l in grade.tool_spaces(vis, x)]


def tag_cells(raw, vis=None, gaps=()):
    """A copy with data-g="n" on every <td>/<th> (document order) and the byte span of each cell in the original; and, for each gap, a comment <!--j:n.0-->
    / <!--j:n.1--> right before the character before and after it — a comment is no element: no stylesheet rule and no structural selector sees it, the
    page lays out exactly as before (Codex C2), and the page's own range over the character that follows it is measured."""
    vis = Visible(raw) if vis is None else vis
    spans = sorted((a, b) for table in vis.tables for row in table for a, b in row)  # the scanner's cells: the parser's own, where a plain search for the tags ran a cell with no end tag on to the next cell anywhere (Codex G2-C3)
    edits = []
    for n, (start, end) in enumerate(spans):
        close = _CELL_END.match(raw, end); spans[n] = (start, close.end() if close else end)  # with its own end tag, where it has one
        edits.append((start + 3, b' data-g="%d"' % n))
    for n, (_, _, _, k, l) in enumerate(gaps):
        for side, c in ((0, k), (1, l)): edits.append((vis.s[c], b'<!--j:%d.%d-->' % (n, side)))
    out, pos = [], 0
    for at, piece in sorted(edits, key=lambda e: e[0]): out += [raw[pos:at], piece]; pos = at
    out.append(raw[pos:])
    return b''.join(out), spans


def join(gaps, boxes, vis=None, tol=0.75):
    """Remove from each item's text the added spaces whose two characters Chrome lays out on one line, touching (the right box begins where the left one ends,
    within `tol` pixels); returns how many. Each item keeps `joins`: [[start, end, gap in pixels]] in the text as it was; its struck places, which count the
    text's characters, are read again from the source (`vis`; Codex C3) — or dropped where that cannot be done."""
    by_item, n = {}, 0
    for g, (x, a, b, k, l) in enumerate(gaps):
        left, right = boxes.get('%d.0' % g), boxes.get('%d.1' % g)
        if not left or not right or abs(left['t'] - right['t']) > 1 or abs(left['b'] - right['b']) > 1: continue  # not one line
        gap = right['x'] - left['r']
        if not -tol <= gap <= tol: continue  # the page spaces them (its styles), or lays them apart: no join
        by_item.setdefault(id(x), (x, []))[1].append((a, b, round(gap, 2)))
    for x, runs in by_item.values():
        text = x['text']
        for a, b, _ in sorted(runs, reverse=True): text = text[:a] + text[b:]
        x['text'], x['joins'] = text, [list(r) for r in sorted(runs)]; n += len(runs)
        if 'struck_at' in x:
            at = grade.struck_at(vis, x) if vis is not None else None
            if at: x['struck_at'] = at
            else: x.pop('struck_at')
    return n


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
    parents, stack = [], []  # the cell each cell stands in (a table inside a cell): text after the inner table is the outer cell's again (Codex's worktree)
    for g, (start, end) in enumerate(spans):
        while stack and spans[stack[-1]][1] <= start: stack.pop()
        parents.append(stack[-1] if stack else -1); stack.append(g)
    for table_cells in measured_by_table.values():
        for g, (r, c, cs) in screen_grid(table_cells).items(): by_g[g] = (r, c, cs)
    n = 0
    for u in units:
        if u.get('kind') != 'table': continue
        for cell in u.get('cells') or []:
            a = cell.get('anchor'); a = a[0] if isinstance(a, list) else a
            if not isinstance(a, dict) or 'byte_start' not in a: continue
            g = bisect_right(starts, a['byte_start']) - 1
            while g >= 0 and a['byte_start'] >= spans[g][1]: g = parents[g]
            if g < 0 or not (spans[g][0] <= a['byte_start'] < spans[g][1]) or g not in by_g: continue
            r, c, cs = by_g[g]
            if (cell['r'], cell['c'], cell.get('cs', 1)) != (r, c, cs): cell.update(r=r, c=c, cs=cs); n += 1
            cell['grid'] = 'screen'
    return n


JS = """() => { const tables = Array.from(document.querySelectorAll('table')); const out = [];
  for (const el of document.querySelectorAll('[data-g]')) { const r = el.getBoundingClientRect(); const t = el.closest('table');
    out.push({g: +el.dataset.g, table: tables.indexOf(t), row: el.parentElement ? el.parentElement.rowIndex : -1, x: r.left, w: r.width}); }
  const boxes = {}; const w = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
  for (let c = w.nextNode(); c; c = w.nextNode()) { const m = /^j:(\\d+\\.[01])$/.exec(c.data); if (!m) continue; let t = c.nextSibling; while (t && t.nodeType === Node.COMMENT_NODE) t = t.nextSibling;  // one character can end one gap and begin the next: its two marks stand side by side
    if (!t || t.nodeType !== Node.TEXT_NODE || !t.data.length) continue; const r = document.createRange(); r.setStart(t, 0); r.setEnd(t, 1); const rs = r.getClientRects();
    if (rs.length === 1) boxes[m[1]] = {x: rs[0].left, r: rs[0].right, t: rs[0].top, b: rs[0].bottom}; }
  return {cells: out, boxes}; }"""


def measure(marked_html, browser):
    """Boxes of every tagged cell as Chrome lays the document out (the document's own styles, a wide window)."""
    page = browser.new_page(viewport={'width': 1400, 'height': 1000})
    try:
        page.set_content(marked_html.decode('utf-8', 'replace'), wait_until='load'); got = page.evaluate(JS)
    finally:
        page.close()
    by_table = {}
    for c in got['cells']: by_table.setdefault(c['table'], []).append(c)
    return by_table, got['boxes']


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--route', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright
    paths = {}
    for t in grade.load_sources(a.key, a.catalog): paths.setdefault(t['file_id'], t['path'])  # sources only
    src, out = Path(a.route), Path(a.out); facts = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for rp in sorted(src.rglob('*.json')):
            d = json.loads(rp.read_text()); fid = d.get('file_id'); dest = out / rp.relative_to(src); dest.parent.mkdir(parents=True, exist_ok=True)
            if d.get('status') != 'OK' or not str(fid).lower().endswith(('.htm', '.html')) or fid not in paths: dest.write_text(json.dumps(d, ensure_ascii=False)); continue  # another step's facts file is copied through
            t0 = time.time(); raw = paths[fid].read_bytes(); vis = Visible(raw); gaps = gaps_of(vis, d['units']); marked, spans = tag_cells(raw, vis, gaps)
            try: measured, boxes = measure(marked, browser)
            except Exception as e: facts[fid] = {'error': repr(e)[:200]}; dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True); continue
            n = apply(d['units'], spans, measured); j = join(gaps, boxes, vis); d['route'] = dict(d['route'], name=d['route']['name'] + '+screen', settings=dict(d['route'].get('settings') or {}, screen_grid=True, joins='touching on one line'))
            facts[fid] = {'cells_regridded': n, 'cells_measured': sum(len(v) for v in measured.values()), 'spaces_the_tool_added': len(gaps), 'joined': j, 'seconds': round(time.time() - t0, 1)}
            dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True)
        browser.close()
    (out / 'screen_facts.json').write_text(json.dumps(facts, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
