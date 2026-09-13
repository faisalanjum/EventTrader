"""Bind the same proved grading candidate to its actual execution location.

The old unrun launch is preserved. No key, prompt, model or runtime owner
changes. The existing publisher must pin the actual path BEFORE any call;
a same-byte copy alone is deliberately not accepted by the native auditor.
"""
import os
import sys
import tempfile
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_workflow_gate as W
import audit_worker_access as AUD

previous_path = A7 / 'unit_2086_real_grading/LAUNCH.json'
previous_sha = '3754473566bf0d8effc043ee3489afb27cc6c5f6fad133f13dc371a0f1a9ef45'
assert G._sha_file(str(previous_path)) == previous_sha
old = G._read(str(previous_path))
old_root = G.load_root(old['run_dir'], old['root_sha256'])
assert G.lane_states(old['run_dir']) == {}
assert G._read(G.state_path(old['run_dir'], 1))['states'] == []
old_script = G.script_path(old['run_dir'], 1)
assert AUD._same_published_script(old_script, old_script)
with tempfile.TemporaryDirectory(prefix='TEST_transport_', dir=str(A7 / 'unit_2088_real_grading')) as test:
    twin = Path(test) / 'same_bytes.js'
    twin.write_bytes(Path(old_script).read_bytes())
    assert G._sha_file(str(twin)) == G._sha_file(old_script)
    assert not AUD._same_published_script(str(twin), old_script)

B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      old['owners']['grading_scorer'])
assert G.owner_hashes() == old['owners']
assert W.owner_sha256() == old['workflow_gate_sha256']
cand = old['candidate_dir']
doc, candidate_sha = G.load_frozen(cand, old['candidate_sha256'])
run_dir = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
           '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a7_grading_2088/g1')
durable = A7 / 'unit_2088_real_grading/g1'
assert os.path.samefile(run_dir, str(durable))  # existing boundary, not a byte alias
inputs = {r['lane_id']: r['expected_input'] for r in old_root['rows']}
root, root_sha, bad = G.freeze_root(cand, run_dir, candidate_sha, inputs)
assert not bad, bad
assert root == old_root and root_sha == old['root_sha256']
lanes, size, bad = W.next_admissible(cand, run_dir, root_sha)
assert not bad and len(lanes) == old['first_segment_lanes'], bad
pub, bad = G.publish_run(cand, run_dir, root_sha, lanes)
assert not bad, bad
packet, bad = G.preflight(cand, run_dir, pub['segment'], root_sha, pub['receipt_sha256'])
assert not bad, bad
invocation = G._read(G.invocation_path(run_dir, pub['segment']))
previous_invocation = G._read(old['invocation_path'])
assert invocation['args'] == previous_invocation['args']
assert packet['scriptPath'] == str(Path(run_dir) / 'grade_batch.seg01.js')
assert os.path.samefile(packet['scriptPath'], str(durable / 'grade_batch.seg01.js'))
new_invocation_sha = G._sha_file(G.invocation_path(run_dir, pub['segment']))
script = Path(packet['scriptPath']).read_text(encoding='utf-8')
assert script == Path(old_script).read_text(encoding='utf-8').replace(
    old['invocation_sha256'], new_invocation_sha)
assert len(script.encode('utf-8')) == size == old['first_script_bytes']

report = dict(old, run_dir=run_dir, durable_run_dir=str(durable),
              root_sha256=root_sha, first_segment=pub['segment'],
              first_receipt_sha256=pub['receipt_sha256'],
              first_script_sha256=G._sha_file(packet['scriptPath']),
              invocation_path=G.invocation_path(run_dir, pub['segment']),
              invocation_sha256=new_invocation_sha,
              previous_unrun_launch=str(previous_path), previous_unrun_launch_sha256=previous_sha,
              transport_proof='same root/args/prompts/owners; actual path published; different-file copy refused')
G._write_new(str(durable.parent / 'LAUNCH.json'), G._pretty(report) + '\n')
print(G._pretty(report), flush=True)
