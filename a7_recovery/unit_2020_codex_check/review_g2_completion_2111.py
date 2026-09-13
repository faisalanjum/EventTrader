"""One-shot review of the closed real G2 run; no model call or scoring.

The input pins and selected replies come from Codex's independent native/raw
review. Existing owners alone validate evidence, select attempts and combine
judgments. This saves a review candidate, not the official completion.
"""
import os
import runpy
from pathlib import Path

assert os.environ['A7_GRADING_COMMAND'] == 'preflight'
HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, run, candidate, launch = (ctx[k] for k in ('G', 'run_dir', 'cand', 'launch'))
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F

input_path = os.environ['A7_G2_REVIEW_INPUT']
assert G._sha_file(input_path) == os.environ['A7_G2_REVIEW_INPUT_SHA256']
review = G._read(input_path)
assert review['launch_sha256'] == os.environ['A7_GRADING_LAUNCH_SHA256']
assert review['root_sha256'] == launch['root_sha256']
for row in review['files']:
    assert G._sha_file(row['path']) == row['sha256'], row['path']
    assert Path(row['path']).stat().st_size == row['bytes'], row['path']
run_pin = (review['run_sha256'], review['run_files'])
with F.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']):
    root, doc, lanes, bad = C.evidence(candidate, run, launch['root_sha256'], *run_pin)
    assert not bad and G.task_kind(doc) == 'G2', bad
    assert set(lanes) == {r['lane_id'] for r in root['rows']}
    assert C.relations_from_run(lanes) == review['selected_relations']
    assert {k: v['selected'] for k, v in lanes.items()} == review['selected_attempts']
    identity = C.g23_identity(launch['root_sha256'], run)
    assert (identity['run_digest'], identity['run_files']) == run_pin
    assert identity['meaning_format_recovery']['attempts'] == review['recovery_audit']
    completion, bad = C.complete_g23(doc, C.relations_from_run(lanes), identity)
    assert not bad, bad
    expected = {q for b in doc['batch_rows'] for q in b['question_ids']}
    reached = list(completion['credited']) + [r['question_id'] for r in completion['unresolved']]
    assert len(reached) == len(set(reached)) and set(reached) == expected
    assert completion['questions'] == doc['questions'] == len(expected)
    assert C.run_digest(run) == run_pin

out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'COMPLETION_CANDIDATE.json'), G._pretty(completion) + '\n')
report = {'scope': 'real G2 whole-run review candidate; NOT an A7 score',
          'input_path': input_path, 'input_sha256': os.environ['A7_G2_REVIEW_INPUT_SHA256'],
          'run_identity': identity, 'lanes': lanes,
          'completion_candidate_sha256': G._sha_file(str(out / 'COMPLETION_CANDIDATE.json')),
          'new_model_calls': 0}
G._write_new(str(out / 'REVIEW.json'), G._pretty(report) + '\n')
print('REVIEWED real G2 completion candidate', report['completion_candidate_sha256'],
      'questions', completion['questions'], 'agreed', completion['credited_questions'],
      'unresolved', completion['unresolved_questions'], flush=True)
