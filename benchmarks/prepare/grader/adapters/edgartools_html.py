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
from driver.prepare.convert import anchor
from benchmarks.prepare.grader.adapters import cache
from driver.prepare.convert.edgartools_html import BLOCKY, BRANCH, KIND, NAME, _BR, codes, dump, named, route_for, split_lines, to_units, unsupported, whole_headings, with_every_picture


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--split', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    ap.add_argument('--reuse-raw', action='store_true', help='adapt the saved node dump again instead of parsing')
    a = ap.parse_args(argv)
    from edgar.documents import parse_html  # only here: the grader package stays standard-library
    whole_headings()
    import importlib.metadata as md
    version = f"edgartools {md.version('edgartools')}"
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True); (out / 'route').mkdir(exist_ok=True)
    files = {}
    for src in grade.load_sources(a.key, a.catalog):  # sources only: converters never read answers
        if src['split'] == a.split: files.setdefault(src['file_id'], (src['path'], src['sha256']))
    facts, settings = {}, {'parse_html': 'defaults', 'retain_pictures': True, 'retain_native_heading_evidence': True, 'picture_names': 'codes', 'hidden_text': 'left out', 'headings': 'detected blocks read whole', 'inline_facts': 'read whole'}  # what the saved parse keeps: one saved before pictures were kept answers to other settings and is not reused
    for fid, (path, sha) in sorted(files.items()):
        (out / 'route' / fid).parent.mkdir(parents=True, exist_ok=True); (out / 'raw' / fid).parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() not in ('.htm', '.html'):
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version))); facts[fid] = {'status': 'UNSUPPORTED'}; continue
        raw = path.read_bytes(); t0 = time.time(); vis = anchor.Visible(raw); scanned = time.time() - t0; t0 = time.time(); rawjson = out / 'raw' / (fid + '.edgartools.json'); metajson = out / 'raw' / (fid + '.meta.json'); ver = version
        try:
            if a.reuse_raw and rawjson.exists():  # a saved parse is reused only whole: its record names the source bytes, settings, producing version and output (adapters/cache.py; Codex R13 C1, R15-5)
                meta = cache.reuse(metajson, sha, settings)
                if meta.get('status') != 'OK': raise RuntimeError('cache refused: the cached run did not succeed')
                tree, dt, ver = json.loads(rawjson.read_text()), meta.get('tool_seconds', 0), meta['version']
            else:
                cache.begin(metajson)  # from here the old record vouches for nothing: a crash below leaves no record
                tree = dump(parse_html(named(raw, vis, codes(raw, vis))).root); dt = time.time() - t0  # the tool reads the source with the pictures' names as codes and no empty anchor
                rawjson.write_text(json.dumps(tree, ensure_ascii=False)); cache.save(metajson, [rawjson], sha256=sha, version=version, settings=settings, status='OK', tool_seconds=round(dt, 2))
        except Exception as e:  # a tool crash is a result, never a stop
            facts[fid] = {'status': 'FAILED', 'error': repr(e)[:300], 'seconds': round(time.time() - t0, 2)}
            (out / 'route' / (fid + '.json')).write_text(json.dumps(unsupported(fid, sha, version, 'FAILED', repr(e)[:300]))); continue
        t1 = time.time(); route = route_for(tree, raw, fid, sha, round(dt, 2), ver, settings, vis)
        flat = [x for u in route['units'] for x in (u.get('cells') or [u])]
        facts[fid] = {'status': 'OK', 'version': ver, 'tool_seconds': round(dt, 2), 'adapter_seconds': round(time.time() - t1 + scanned, 2), 'items': len(flat),
                      'unanchored': sum(1 for x in flat if not x.get('anchor')), 'uncovered_spans': len(route['uncovered']),
                      'uncovered_chars': sum(len(anchor.squash(s['text'])) for s in route['uncovered'])}
        (out / 'route' / (fid + '.json')).write_text(json.dumps(route, ensure_ascii=False))
        print(fid, facts[fid], flush=True)
    (out / 'facts.json').write_text(json.dumps({'route': NAME, 'version': version, 'split': a.split, 'files': facts}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
