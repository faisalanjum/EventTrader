"""Read-only: what shape did the G2 readings actually take?

complete_g23 crashed in the pinned reconciler on `a.get(field)` with `a` a str.
This changes nothing and judges nothing; it reports, per lane, the Python type
of every per-question relation value, so the offending entries can be named
instead of guessed at.
"""
import collections
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R                                   # noqa: E402,F401
import a7_g1_build as G                                           # noqa: E402
import a7_g23_build as B                                          # noqa: E402
import a7_g1_complete_v2 as C                                     # noqa: E402

launch = G._read(os.environ['A7_GRADING_LAUNCH'])
run_dir, cand = launch['run_dir'], launch['candidate_dir']
root = G.load_root(run_dir, launch['root_sha256'])
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      launch['owners']['grading_scorer'])
digest, files = C.run_digest(run_dir)
_root, doc, per_lane, problems = C.evidence(cand, run_dir, launch['root_sha256'],
                                            digest, files)

shapes = collections.Counter()
offenders = []
for lane_id, rel in sorted((per_lane or {}).items()):
    if not isinstance(rel, dict):
        offenders.append((lane_id, '<relation itself>', type(rel).__name__,
                          repr(rel)[:120]))
        continue
    for qid, val in sorted(rel.items()):
        shapes[type(val).__name__] += 1
        if not isinstance(val, dict):
            offenders.append((lane_id, qid, type(val).__name__, repr(val)[:120]))

print(G._pretty({
    'lanes_read': len(per_lane or {}),
    'value_types': dict(shapes),
    'non_dict_entries': len(offenders),
    'first_offenders': offenders[:10],
    'evidence_problems': problems,
}), flush=True)
