"""Screen-span step (an allowed small adapter, PrepareStep.md P20/T1): the labellers' guide says a header covers a value
when the value sits inside the header's span ON SCREEN (guide 3.5 rule 3). DOM colspans can disagree with the screen
(spacer columns, hidden cells), and every HTML tool inherits the DOM grid. This step renders the original in headless
Chrome, measures every table cell's box, derives screen columns from the pixel edges, and re-grids a route's table
cells by their byte anchors, and joins a word or number the tool printed with a space the source does not have where Chrome shows its two
characters touching on one baseline (a space the tool adds across inline markup: `CORP ORATION` over an iXBRL tag; the page alone can tell that from
a gap its styles make). It changes no anchor; the joined text records where its spaces were. Rules are geometric only.

    <python with playwright> -m benchmarks.prepare.grader.adapters.screen_grid --key <key package> --route <route dir> --out <route dir> [--catalog CSV]"""
# The runtime lives in driver.prepare.convert.screen_grid (moved 2026-10-07); this module keeps the command line over key packets.
import argparse
import json
import time
from pathlib import Path
from benchmarks.prepare.grader import grade
from driver.prepare.convert.anchor import Visible
from driver.prepare.convert.screen_grid import JS, TOL, _CELL_END, apply, endpoints_of, gaps_of, join, measure, screen_grid, tag_cells


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
            t0 = time.time(); raw = paths[fid].read_bytes(); vis = Visible(raw); gaps = gaps_of(vis, d['units']); endpoints = endpoints_of(vis, d['units']) if not vis.certain else []; marked, spans = tag_cells(raw, vis, gaps + endpoints)
            try: measured, boxes = measure(marked, browser)
            except Exception as e: facts[fid] = {'error': repr(e)[:200]}; dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True); continue
            if endpoints:  # source-bound endpoints, measured in the existing render; no answer key chooses them
                d['screen_endpoints'] = {side: {str(g[0][side]): boxes[str(len(gaps) + n) + '.' + str(ix)] for n, g in enumerate(endpoints) if str(len(gaps) + n) + '.' + str(ix) in boxes} for ix, side in enumerate(('start', 'end'))}
            n = apply(d['units'], spans, measured); j = join(gaps, boxes, vis); d['route'] = dict(d['route'], name=d['route']['name'] + '+screen', settings=dict(d['route'].get('settings') or {}, screen_grid=True, joins='touching on one baseline'))
            facts[fid] = {'cells_regridded': n, 'cells_measured': sum(len(v) for v in measured.values()), 'spaces_the_tool_added': len(gaps), 'joined': j, 'seconds': round(time.time() - t0, 1)}
            dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True)
        browser.close()
    (out / 'screen_facts.json').write_text(json.dumps(facts, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
