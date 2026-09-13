"""Freeze the fully collected real G3 evidence for review; no AI or score."""
import os
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, run, candidate, launch = (ctx[k] for k in ('G', 'run_dir', 'cand', 'launch'))
import a7_g1_complete_v2 as C

review_path = HERE / 'codex_g3native2106_a/REVIEW.json'
assert G._sha_file(str(review_path)) == 'bf3091293f193424731a9280a5b018efccd0608c37229e2d7b757fc0fccbb4f7'
review = G._read(str(review_path))
assert review['kind'] == 'G3'
assert review['launch_sha256'] == os.environ['A7_GRADING_LAUNCH_SHA256']
root, doc, lanes, bad = C.evidence(candidate, run, launch['root_sha256'],
    os.environ['A7_REVIEW_RUN_SHA256'], int(os.environ['A7_REVIEW_RUN_FILES']))
assert not bad, bad
assert G.task_kind(doc) == 'G3'
assert [r['segment'] for r in review['segments']] == G.segments(run)
assert len(lanes) == len(root['rows']) and all(r['selected'] is not None for r in lanes.values())
called, validity, native_files, manifests = [], [], [], []
native_root = Path(os.environ['A7_GRADING_LAUNCH']).parent / 'native'
for segment in review['segments']:
    n = segment['segment']
    final = G._read(G.finalization_path(run, n))
    assert G._sha_file(G.finalization_path(run, n)) == segment['finalization_sha256']
    assert G._sha_file(G.receipt_path(run, n)) == segment['receipt_sha256']
    assert not final['uncalled']
    called.extend((lane, final['attempt']) for lane, _valid in final['validity'])
    validity.extend(ok for _lane, ok in final['validity'])
    candidates = list((native_root / ('seg%02d' % n)).glob('*/PRESERVED.json'))
    assert len(candidates) == 1
    manifest_path = candidates[0]
    manifest = G._read(str(manifest_path))
    assert manifest['segment'] == n and manifest['kind'] == 'G3'
    assert manifest['file_count'] == len(manifest['files'])
    for row in manifest['files']:
        saved = manifest_path.parent / row['name']
        assert G._sha_file(str(saved)) == row['sha256'] == G._sha_file(row['source'])
        assert saved.stat().st_size == row['bytes'] == Path(row['source']).stat().st_size
        native_files.append({'path': str(saved), 'sha256': row['sha256']})
    manifests.append({'path': str(manifest_path), 'sha256': G._sha_file(str(manifest_path))})
assert len(set(called)) == len(called)
assert {lane for lane, attempt in called if attempt == 1} == set(lanes)
assert all(attempt <= root['max_attempts'] for lane, attempt in called)
for lane, attempt in called:
    if attempt > 1:
        assert lanes[lane]['attempts'][attempt - 1] is False
identity = C.g23_identity(launch['root_sha256'], run)
assert (identity['run_digest'], identity['run_files']) == (
    os.environ['A7_REVIEW_RUN_SHA256'], int(os.environ['A7_REVIEW_RUN_FILES']))
completion, bad = C.complete_g23(doc, C.relations_from_run(lanes), identity)
assert not bad, bad
expected = {q for b in doc['batch_rows'] for q in b['question_ids']}
reached = list(completion['credited']) + [r['question_id'] for r in completion['unresolved']]
assert len(reached) == len(set(reached)) and set(reached) == expected
assert completion['questions'] == doc['questions'] == len(expected)
assert C.run_digest(run) == (identity['run_digest'], identity['run_files'])
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'COMPLETION_CANDIDATE.json'), G._pretty(completion) + '\n')
report = {'scope': 'real G3 whole-evidence/paired-verdict review; NOT an A7 score',
    'root_sha256': launch['root_sha256'], 'run_identity': identity,
    'required_primary_readings': len(lanes), 'actual_calls': len(called),
    'original_valid': sum(validity), 'original_invalid': len(validity) - sum(validity),
    'selected_usable': sum(r['selected'] is not None for r in lanes.values()),
    'uncalled': 0, 'exhausted': 0, 'questions': len(expected),
    'agreed_questions': completion['credited_questions'],
    'unresolved_questions': completion['unresolved_questions'],
    'completion_candidate_sha256': G._sha_file(str(out / 'COMPLETION_CANDIDATE.json')),
    'native_copies': native_files, 'manifests': manifests, 'new_model_calls': 0}
G._write_new(str(out / 'REVIEW.json'), G._pretty(report) + '\n')
print(G._plain({k: v for k, v in report.items() if k not in ('native_copies', 'manifests')}), flush=True)
