"""Source-formatting step (a declared small route step, like the screen step): the original's own strike-through — <s>, <del>,
<strike> and CSS `text-decoration: line-through`, inherited by descendants — is written onto the route's units and cells as `struck`
phrases, found through their byte anchors. It changes no text and no anchor. Why: the key keeps struck evidence struck (key README,
E10); Docling maps only the three tags and EdgarTools reports no strikes, so redlines marked with CSS became active text.

    python3 -m benchmarks.prepare.grader.adapters.source_formatting --key <key package> --route <route dir> --out <route dir> [--catalog CSV]"""
# The runtime lives in driver.prepare.convert.source_formatting (moved 2026-10-07); this module keeps the command line over key packets.
import argparse
import json
from pathlib import Path
from benchmarks.prepare.grader import grade
from driver.prepare.convert.source_formatting import apply, step


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--route', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    a = ap.parse_args(argv)
    paths = {}
    for t in grade.load_sources(a.key, a.catalog): paths.setdefault(t['file_id'], (t['path'], t['sha256']))  # sources only, never answers
    src, out, facts = Path(a.route), Path(a.out), {}
    for rp in sorted(src.rglob('*.json')):
        d = json.loads(rp.read_text()); fid = d.get('file_id'); dest = out / rp.relative_to(src); dest.parent.mkdir(parents=True, exist_ok=True)
        if d.get('status') not in ('OK', 'PARTIAL') or not str(fid).lower().endswith(('.htm', '.html')) or fid not in paths: dest.write_text(json.dumps(d, ensure_ascii=False)); continue
        raw = paths[fid][0].read_bytes()
        if grade.sha256(raw) != paths[fid][1] or d.get('sha256') != paths[fid][1]: facts[fid] = {'error': 'source bytes differ from the key'}; dest.write_text(json.dumps(d, ensure_ascii=False)); continue
        n = step(raw, d)
        facts[fid] = {'items_with_struck_text': n} if n is not None else {'uncertain': "struck text cannot be certified from the source; the tool's own claims kept"}; dest.write_text(json.dumps(d, ensure_ascii=False))
    (out / 'source_formatting_facts.json').write_text(json.dumps(facts, indent=1))
    print(f"{len(facts)} files; items with struck text: {sum(f.get('items_with_struck_text', 0) for f in facts.values())}; uncertain files: {sum('uncertain' in f for f in facts.values())}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
