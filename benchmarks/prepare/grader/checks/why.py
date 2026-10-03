"""Show what the grader saw behind failures of a graded run: key value vs the route's carriers at the key's anchors.

    python3 -m benchmarks.prepare.grader.checks.why <run dir> [check[:reason]] [n]      e.g. why RUN section_path:missing 5

Read-only; a review aid for people and for Codex, never part of scoring."""
import json
import sys
from pathlib import Path

from benchmarks.prepare.grader import grade

KEY = Path(json.loads((Path(__file__).resolve().parents[2] / 'golden/PACKAGE.json').read_text())['package_path'])  # the recorded final package


def main(argv):
    run = Path(argv[0]); want = (argv[1].split(':') + [None])[:2] if len(argv) > 1 else (None, None); n = int(argv[2]) if len(argv) > 2 else 3
    T = {t['key_id']: t for t in grade.load_key(KEY, KEY.parent.parent / 'case_catalog.csv')}
    rows = [json.loads(l) for l in (run / 'graded' / 'results.jsonl').read_text().splitlines()]
    fails = [r for r in rows if r['verdict'] == 'fail' and (want[0] is None or r['check'] == want[0]) and (want[1] is None or r['reason'] == want[1])]
    buckets = {}
    for r in fails: buckets.setdefault((r['check'], r['reason']), []).append(r)
    cache = {}
    for (check, reason), rs in sorted(buckets.items(), key=lambda x: -len(x[1])):
        print(f'\n#### {check} / {reason}: {len(rs)} cases')
        for r in rs[:n]:
            t = T[r['key_id']]
            if t['file_id'] not in cache: cache[t['file_id']] = grade.RouteFile(json.loads((run / 'route' / (t['file_id'] + '.json')).read_text()), t['path'].read_bytes())
            rf = cache[t['file_id']]; g = grade.Grader(t, rf)
            field = check if check in t['fields'] or check in t['alternatives'] else None
            print(f"  {r['key_id']} | detail={str(r['detail'])[:80]}")
            if field:
                alt, v = grade.alternatives(t, field)[0]
                cars = g.carriers(grade.anchors_of(t, field, alt), grade.pieces_of(v) if isinstance(v, (list, str)) else [], None)
                print(f"      key   : {json.dumps(v, ensure_ascii=False)[:160]}")
                print(f"      route : {[(('cell', k['cell']['r'], k['cell']['c']) if k['cell'] else k['unit']['kind'], k['text'][:70]) for k in cars][:4]}")
            elif check == 'value':
                hits = rf.cells_at(t['anchor']); print(f"      key   : {t['fields'].get('printed_value')!r} / {t['fields'].get('display_value')!r}\n      route : {[(c['r'], c['c'], c['text']) for c in hits]}")
            elif check in ('printed_text', 'kind'):
                units = rf.units_at(t['anchor'], exclude=('clutter',)); print(f"      key   : {t['fields'].get('kind')} {t['fields'].get('printed_text', '')[:120]!r}\n      route : {[(u['kind'], (u.get('text') or '')[:100]) for u in units][:3]}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
