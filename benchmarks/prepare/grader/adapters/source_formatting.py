"""Source-formatting step (a declared small route step, like the screen step): the original's own strike-through — <s>, <del>,
<strike> and CSS `text-decoration: line-through`, inherited by descendants — is written onto the route's units and cells as `struck`
phrases, found through their byte anchors. It changes no text and no anchor. Why: the key keeps struck evidence struck (key README,
E10); Docling maps only the three tags and EdgarTools reports no strikes, so redlines marked with CSS became active text.

    python3 -m benchmarks.prepare.grader.adapters.source_formatting --key <key package> --route <route dir> --out <route dir> [--catalog CSV]"""
import argparse
import json
from pathlib import Path

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.anchor import Visible, norm


def apply(raw, units):
    """Set `struck` on every unit and cell with byte anchors from the source's struck runs; returns how many items carry struck text.
    Only resolved decoration is certified: a struck run is written when no stylesheet rule touches decorations (`struck_certain`); a
    converter's claim is dropped only where nothing is struck and no sheet rule could add a strike (`plain_certain`); anywhere else the
    converter's own claim stands. When neither can be certified nothing is changed and None is returned. Beside the phrases, `struck_at`: the
    exact places of the struck characters in the item's text (`grade.struck_at`), written only where both readings are certain and the text is the
    source's at its place — a phrase that stands twice in the text is placed by it; a redline printed as one run (`TheExcept`) keeps its two words."""
    vis = Visible(raw)
    if not vis.struck_certain and not vis.plain_certain: return None
    runs = vis.struck_runs(); n = 0
    for u in units:
        for x in (u.get('cells') or []) if u.get('kind') == 'table' else [u]:
            byte = [a for a in grade.spans(x.get('anchor')) if 'byte_start' in a]
            if not byte: continue
            phrases = [norm(vis.at(max(s, a['byte_start']), min(e, a['byte_end_exclusive']))) for a in byte for s, e in runs if s < a['byte_end_exclusive'] and a['byte_start'] < e]
            phrases = [p for p in phrases if p and grade.squash(p) in grade.squash(x.get('text', ''))]  # only text the item carries: an anchor may span text the tool dropped
            if phrases and vis.struck_certain: x['struck'] = phrases; n += 1  # a struck run the scanner resolved in full
            elif not phrases and vis.plain_certain: x.pop('struck', None)  # nothing struck here and no sheet rule could add one: a tool's own claim is dropped
            # otherwise the converter's own claim stands: the source's decoration here was not resolved
            at = grade.struck_at(vis, x)
            if at: x['struck_at'] = at
            else: x.pop('struck_at', None)  # nothing struck, or no exact answer: no claim of places
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--key', required=True); ap.add_argument('--route', required=True); ap.add_argument('--out', required=True); ap.add_argument('--catalog')
    a = ap.parse_args(argv)
    paths = {}
    for t in grade.load_sources(a.key, a.catalog): paths.setdefault(t['file_id'], (t['path'], t['sha256']))  # sources only, never answers
    src, out, facts = Path(a.route), Path(a.out), {}
    for rp in sorted(src.rglob('*.json')):
        d = json.loads(rp.read_text()); fid = d.get('file_id'); dest = out / rp.relative_to(src); dest.parent.mkdir(parents=True, exist_ok=True)
        if d.get('status') != 'OK' or not str(fid).lower().endswith(('.htm', '.html')) or fid not in paths: dest.write_text(json.dumps(d, ensure_ascii=False)); continue
        raw = paths[fid][0].read_bytes()
        if grade.sha256(raw) != paths[fid][1] or d.get('sha256') != paths[fid][1]: facts[fid] = {'error': 'source bytes differ from the key'}; dest.write_text(json.dumps(d, ensure_ascii=False)); continue
        n = apply(raw, d['units']); d['route'] = dict(d['route'], name=d['route']['name'] + '+source-formatting', settings=dict(d['route'].get('settings') or {}, source_formatting=True))
        facts[fid] = {'items_with_struck_text': n} if n is not None else {'uncertain': "struck text cannot be certified from the source; the tool's own claims kept"}; dest.write_text(json.dumps(d, ensure_ascii=False))
    (out / 'source_formatting_facts.json').write_text(json.dumps(facts, indent=1))
    print(f"{len(facts)} files; items with struck text: {sum(f.get('items_with_struck_text', 0) for f in facts.values())}; uncertain files: {sum('uncertain' in f for f in facts.values())}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
