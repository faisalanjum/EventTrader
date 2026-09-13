"""Verify the applied zero-call closure against its independent before/after manifest."""
import os
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, W, run, candidate, launch = (ctx[k] for k in ('G', 'W', 'run_dir', 'cand', 'launch'))
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F

path = HERE / 'ACTUAL_UNUSED_RETRY_CLOSURE_2110.json'
assert G._sha_file(str(path)) == os.environ['A7_CLOSURE_MANIFEST_SHA256']
proof = G._read(str(path))
assert proof['existing_files_changed'] == 0 and proof['actual_model_calls'] == 0
old = {row['path']: row for row in proof['before']}
new = {row['path']: row for row in proof['after']}
assert all(new[p] == row for p, row in old.items())
assert set(new) - set(old) == {'accounting.seg05.json', 'finalization.seg05.json', 'unused_retry.seg05.json'}
for rel, row in new.items():
    assert G._sha_file(str(Path(run) / rel)) == row['sha256']
expected_digest = G._sha(''.join(sorted('%s  ./%s\n' % (r['sha256'], r['path']) for r in proof['after'])))
assert C.run_digest(run) == (expected_digest, len(new))
with F.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']):
    root, doc, lanes, problems = C.evidence(candidate, run, launch['root_sha256'], expected_digest, len(new))
    assert not problems, problems
    relations = C.relations_from_run(lanes)
    assert set(relations) == {'G2-000/G1a', 'G2-000/G1b', 'G2-001/G1a'}
    assert lanes['G2-000/G1b']['selected'] == 2
    assert lanes['G2-001/G1a']['selected'] == 1
    identity = C.g23_identity(launch['root_sha256'], run)
    audit = identity['meaning_format_recovery']['attempts']
    assert len(audit) == 4 and sum(x['original_valid'] for x in audit) == 1
    assert sum(x['recovered'] for x in audit) == 3
    completion, problems = C.complete_g23(doc, relations, identity)
    assert not problems and completion['questions'] == 306, problems
    assert completion['credited_questions'] + completion['unresolved_questions'] == 306
state = G.lane_states(run)
remaining = [r['lane_id'] for r in root['rows'] if state.get(r['lane_id']) != 'called']
assert len(remaining) == 137
next_lanes, size, problems = W.next_admissible(candidate, run, launch['root_sha256'])
assert not problems and next_lanes and next_lanes == remaining[:len(next_lanes)], problems
assert not any(G.segment_state(run, n) != 'finalized' for n in G.segments(run))
assert C.run_digest(run) == (expected_digest, len(new))
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'REVIEW.json'), G._pretty({
    'scope': 'applied zero-call closure and read-only real resume; NOT an A7 score',
    'manifest_sha256': os.environ['A7_CLOSURE_MANIFEST_SHA256'],
    'run_identity': identity, 'original_files_unchanged': len(old), 'new_files': len(new)-len(old),
    'actual_calls': len(audit), 'original_valid': sum(x['original_valid'] for x in audit),
    'recovered': sum(x['recovered'] for x in audit), 'remaining_primaries': len(remaining),
    'next_original_owner_lanes': next_lanes, 'next_script_bytes': size,
    'next_segment_not_published': True, 'actual_model_calls_by_this_check': 0}) + '\n')
print('VERIFIED:46 original files unchanged,3 zero-call artifacts,4 saved readings reused,137 primaries remain; next owner prefix admitted')
