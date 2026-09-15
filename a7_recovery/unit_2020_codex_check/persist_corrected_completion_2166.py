"""Re-derive a reviewed completion, then save it through its existing owner.

One native checkpoint action; no model calls or new grading rules. Candidate,
launch, owners, selected attempts and every judgment must match before writing.
"""
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F

review_path = os.environ['A7_COMPLETION_REVIEW']
review_pin = os.environ['A7_COMPLETION_REVIEW_SHA256']
launch_path = os.environ['A7_GRADING_LAUNCH']
assert G._sha_file(review_path) == review_pin
assert G._sha_file(launch_path) == os.environ['A7_GRADING_LAUNCH_SHA256']
review, launch = G._read(review_path), G._read(launch_path)
run, candidate, root_pin = (launch[k] for k in
                            ('run_dir', 'candidate_dir', 'root_sha256'))
assert (review['run_dir'], review['candidate_dir'], review['root_sha256']) == (
    run, candidate, root_pin)
assert not review['evidence_problems'] and not review['completion_problems']
root = G.load_root(run, root_pin)
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      launch['owners']['grading_scorer'])
assert G.owner_hashes() == root['owners'] == launch['owners']

with F.scope(os.environ['A7_FORMAT_CODE_SHA256'],
             os.environ['A7_FORMAT_RULE_SHA256']):
    identity = C.g23_identity(root_pin, run)
    assert identity == review['run_identity']
    _, doc, lanes, problems = C.evidence(
        candidate, run, root_pin, identity['run_digest'], identity['run_files'])
    assert not problems, problems
    assert G.task_kind(doc) == review['kind']
    assert len(lanes) == len(root['rows']) == review['lanes_read']
    assert all(row['selected'] is not None for row in lanes.values())
    relations = C.relations_from_run(lanes)
    assert len(relations) == review['lanes_with_selected_relation']
    live, problems = C.complete_g23(doc, relations, identity)
    assert not problems and live == review['completion'], problems
    assert G._sha_file(review_path) == review_pin
    assert C.g23_identity(root_pin, run) == identity
    path, digest = C.persist_g23(candidate, live)
    assert C.load_g23(candidate, digest, root_pin, run) == live

out = Path(__file__).resolve().parent / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'PERSISTED_COMPLETION.json'), G._pretty({
    'review_path': review_path, 'review_sha256': review_pin,
    'completion_path': path, 'completion_sha256': digest,
    'run_identity': identity, 'questions': live['questions'],
    'agreed': live['credited_questions'], 'unresolved': live['unresolved_questions'],
    'lanes_selected': {lane: row['selected'] for lane, row in lanes.items()},
    'caller_sha256': G._sha_file(__file__), 'new_model_calls': 0}) + '\n')
print('VERIFIED AND PERSISTED', review['kind'], digest,
      live['credited_questions'], live['unresolved_questions'], flush=True)
