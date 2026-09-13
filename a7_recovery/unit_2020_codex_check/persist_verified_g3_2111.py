"""Save the independently reviewed real G3 completion through its sole owner."""
import os
import runpy
from pathlib import Path

assert os.environ['A7_GRADING_COMMAND'] == 'preflight'
HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, run, candidate, launch = (ctx[k] for k in ('G', 'run_dir', 'cand', 'launch'))
import a7_g1_complete_v2 as C

review_path = HERE / 'codex_g3completion2106_a/REVIEW.json'
completion_path = review_path.with_name('COMPLETION_CANDIDATE.json')
assert G._sha_file(str(review_path)) == os.environ['A7_G3_REVIEW_SHA256']
review = G._read(str(review_path))
assert G._sha_file(str(completion_path)) == review['completion_candidate_sha256']
approved = G._read(str(completion_path))
identity = review['run_identity']
assert identity['root_sha256'] == launch['root_sha256']
assert identity['run_dir'] == run
run_pin = (identity['run_digest'], identity['run_files'])
root, doc, lanes, problems = C.evidence(candidate, run, launch['root_sha256'], *run_pin)
assert not problems and G.task_kind(doc) == 'G3', problems
assert len(lanes) == len(root['rows']) and all(r['selected'] is not None for r in lanes.values())
assert C.g23_identity(launch['root_sha256'], run) == identity
live, problems = C.complete_g23(doc, C.relations_from_run(lanes), identity)
assert not problems and live == approved, problems
for row in review['native_copies'] + review['manifests']:
    assert G._sha_file(row['path']) == row['sha256']
assert C.run_digest(run) == run_pin
path, digest = C.persist_g23(candidate, live)
assert digest == review['completion_candidate_sha256']
assert C.load_g23(candidate, digest, launch['root_sha256'], run) == live
assert C.run_digest(run) == run_pin
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'PERSISTED_G3.json'), G._pretty({
    'scope': 'verified real G3 completion saved; no G2 judgment or A7 score',
    'review_sha256': os.environ['A7_G3_REVIEW_SHA256'],
    'completion_path': path, 'completion_sha256': digest,
    'run_identity': identity, 'questions': live['questions'],
    'agreed': live['credited_questions'], 'unresolved': live['unresolved_questions'],
    'run_unchanged': True, 'actual_model_calls': 0}) + '\n')
print('SAVED verified G3 completion', digest, 'agreed', live['credited_questions'],
      'unresolved', live['unresolved_questions'], flush=True)
