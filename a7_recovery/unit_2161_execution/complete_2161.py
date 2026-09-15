"""The NATIVE whole-run G2/G3 completion for one finished root.

No model is called and nothing is persisted into the candidate here. This runs
the existing, pinned owners over the finished run - the same chain the historical
completion used - and writes the candidate for review:

    C.evidence(...)        -> the per-lane readings across EVERY finalized segment
    C.g23_identity(...)    -> the run's structured identity, re-measured from the tree
    C.complete_g23(...)    -> the per-QUESTION whole-run judgment

persist_g23 is deliberately NOT called: writing the completion into the candidate
is a once-only immutable act and belongs after review, not before it.
"""
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R                                   # noqa: E402,F401
import a7_g1_build as G                                           # noqa: E402
import a7_g23_build as B                                          # noqa: E402
import a7_g1_complete_v2 as C                                     # noqa: E402
# The meaning-format owner lives beside its own caller, not in the harness,
# so its directory has to be on the path the way that caller gets it.
sys.path.insert(0, str(A7 / 'unit_2020_codex_check'))
import a7_meaning_format_2105 as F                                # noqa: E402

launch_path = Path(os.environ['A7_GRADING_LAUNCH'])
assert G._sha_file(str(launch_path)) == os.environ['A7_GRADING_LAUNCH_SHA256']
launch = G._read(str(launch_path))
run_dir, cand = launch['run_dir'], launch['candidate_dir']
root = G.load_root(run_dir, launch['root_sha256'])
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      launch['owners']['grading_scorer'])
assert G.owner_hashes() == root['owners'] == launch['owners']

digest, files = C.run_digest(run_dir)
_root, doc, per_lane, problems = C.evidence(cand, run_dir, launch['root_sha256'],
                                            digest, files)
# `evidence` returns lane RECORDS (batch_id, attempts, selected, relation).
# complete_g23 consumes the RELATION per lane, so the existing owner that
# extracts them is what stands between the two - not a reshape of my own.
relations = C.relations_from_run(per_lane)
with F.scope(os.environ['A7_FORMAT_CODE_SHA256'],
             os.environ['A7_FORMAT_RULE_SHA256']):
    identity = C.g23_identity(launch['root_sha256'], run_dir)
    result, completion_problems = C.complete_g23(doc, relations, identity)

record = {
    'kind': os.environ['A7_COMPLETION_KIND'],
    'model_calls': 0,
    'persisted': False,
    'run_dir': run_dir,
    'candidate_dir': cand,
    'root_sha256': launch['root_sha256'],
    'run_identity': identity,
    'evidence_problems': problems,
    'completion_problems': completion_problems,
    'lanes_read': len(per_lane or {}),
    'lanes_with_selected_relation': len(relations),
    'completion': result,
}
out = Path(os.environ['A7_COMPLETION_OUT'])
G._write_new(str(out), G._pretty(record) + '\n')
print(G._pretty({k: v for k, v in record.items() if k != 'completion'}), flush=True)
print('COMPLETION_CANDIDATE %s %s' % (out, G._sha_file(str(out))), flush=True)
