"""Route adapter: edgartools `parse_html` -> the common route format, anchored by the shared linker.
edgartools keeps no source positions, so the linker places every block. Under its own environment the adapter first
dumps the parsed node tree to plain JSON (kept as the raw output); `to_units` works on that dump, so it is testable
without the package. Shape rules only, no document-specific logic.

    <edgartools python> -m benchmarks.prepare.grader.adapters.edgartools_html --key <key package> --split development --out <run dir> [--catalog CSV]"""
# The runtime lives in driver.prepare.convert.edgartools_html (moved 2026-10-07); this module keeps the command line over key packets.
import argparse
import json
import time
from pathlib import Path
from benchmarks.prepare.grader import grade
from driver.prepare.convert import anchor, html_route
from benchmarks.prepare.grader.adapters import cache
from driver.prepare.convert.edgartools_html import BLOCKY, BRANCH, KIND, NAME, SETTINGS, _BR, codes, convert, dump, named, parse, route_for, settings, split_lines, to_units, unsupported, version, whole_headings, with_every_picture


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt the saved node dump again instead of parsing')
    a = ap.parse_args(argv)
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for src in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if src['split'] == a.split: files.setdefault(src['file_id'], (src['path'], src['sha256']))
    from playwright.sync_api import sync_playwright
    facts, browser = {}, None
    with sync_playwright() as pw:  # a browser is launched only for a file the scanner cannot certify
        for fid, (path, sha) in sorted(files.items()):
            (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
            if path.suffix.lower() not in ('.htm', '.html'):
                (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version()))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
            rawjson, metajson = out / 'raw' / (fid + '.edgartools.json'), out / 'raw' / (fid + '.meta.json')
            def kept(raw, vis, rawjson=rawjson, metajson=metajson, sha=sha):  # the tool's parse, saved beside the route for a later --reuse-raw
                if a.reuse_raw and rawjson.exists():  # a saved parse is reused only whole: its record names the source bytes, settings, producing version and output (adapters/cache.py; Codex R13 C1, R15-5)
                    meta = cache.reuse(metajson, sha, settings(vis))  # the browser's reading is part of what was parsed (edgartools_html.settings)
                    if meta.get('status') != 'OK': raise RuntimeError('cache refused: the cached run did not succeed')
                    return json.loads(rawjson.read_text()), meta.get('tool_seconds', 0), meta['version']
                cache.begin(metajson)  # from here the old record vouches for nothing: a crash below leaves no record
                tree, seconds, made_by = parse(raw, vis)
                rawjson.write_text(json.dumps(tree, ensure_ascii=False)); cache.save(metajson, [rawjson], sha256=sha, version=made_by, settings=settings(vis), status='OK', tool_seconds=seconds)
                return tree, seconds, made_by
            parse_elapsed = 0
            def timed_parse(raw, vis):
                nonlocal parse_elapsed
                started = time.perf_counter()
                try: return kept(raw, vis)
                finally: parse_elapsed = time.perf_counter() - started
            t0 = time.perf_counter(); raw = path.read_bytes(); anchor.check_source(raw, sha); vis = anchor.Visible(raw)  # the selected route's composition (html_route.prepare): bytes the hash names, then a file the scanner cannot certify is first read in the browser
            if not vis.certain: browser = browser or pw.chromium.launch()
            vis, failed = html_route.visibility(raw, vis, browser)
            route = convert(raw, fid, sha, timed_parse, vis=vis)
            if route['status'] != 'OK':  # a document parse failure is recorded; operational errors have propagated
                facts[fid] = {'status': 'FAILED', 'error': route['error'], 'seconds': round(time.perf_counter() - t0, 2)}
                (out / 'route' / (fid + '.json')).write_text(json.dumps(route)); continue
            if failed: route['status'], route['error'] = 'PARTIAL', 'page visibility: ' + failed  # as html_route.prepare marks it: the scanner's reading kept, the reason said
            flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
            facts[fid] = {'status': route['status'], **({'error': route['error']} if route['error'] else {}), 'version': route['route']['version'], 'tool_seconds': route['seconds'], 'adapter_seconds': round(time.perf_counter() - t0 - parse_elapsed, 2), 'items': len(flat),
                          'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                          'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered'])}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
            print(fid, facts[fid], flush=True)
        if browser is not None: browser.close()
    (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version(), 'split': a.split, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
