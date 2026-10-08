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
from pathlib import Path
from benchmarks.prepare.grader import grade
from driver.prepare.convert.screen_grid import JS, TOL, _CELL_END, apply, endpoints_of, gaps_of, join, measure, screen_grid, step, tag_cells


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
            if d.get('status') not in ('OK', 'PARTIAL') or not str(fid).lower().endswith(('.htm', '.html')) or fid not in paths: dest.write_text(json.dumps(d, ensure_ascii=False)); continue  # another step's facts file is copied through
            facts[fid] = step(paths[fid].read_bytes(), d, browser)
            if 'error' in facts[fid]: d['status'], d['error'] = 'PARTIAL', '; '.join(x for x in (d.get('error'), 'screen step: ' + facts[fid]['error']) if x)  # as html_route.prepare marks it, any earlier reason kept
            dest.write_text(json.dumps(d, ensure_ascii=False)); print(fid, facts[fid], flush=True)
        browser.close()
    (out / 'screen_facts.json').write_text(json.dumps(facts, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
