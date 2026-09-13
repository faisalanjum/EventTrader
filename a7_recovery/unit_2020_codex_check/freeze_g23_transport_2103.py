"""Publish the unchanged G2/G3 requests at the supported execution paths.

The recovery-path refusal is preserved in unit_2102_transport_probe. This
uses the already proved 2088 publisher/bind-mount arrangement, not a new
runner or an alias for an old receipt. Old unrun roots stay untouched.
"""
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_workflow_gate as W

PREVIOUS = {
    'G2': '7e47f8017c011d1fc4eeb093aa632d621a353d0c96f5973eb9948e83156ab764',
    'G3': 'c1cb93906e25aa6cf557345578aabe8c0522aeb1f3fc1271bedc529f840930bd',
}
EXECUTION = Path('/tmp/claude-1000/-home-faisal-EventMarketDB/'
                 '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a7_grading_2103')
report = {}
for kind, expected_sha in PREVIOUS.items():
    previous_path = A7 / 'unit_2100_g23_grading' / kind / 'LAUNCH.json'
    assert G._sha_file(str(previous_path)) == expected_sha
    old = G._read(str(previous_path))
    old_run = old['run_dir']
    root = G.load_root(old_run, old['root_sha256'])
    assert G.segments(old_run) == [1] and G.lane_states(old_run) == {}
    assert G._read(G.state_path(old_run, 1))['states'] == []
    B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                          old['owners']['grading_scorer'])
    assert G.owner_hashes() == root['owners'] == old['owners']
    assert W.owner_sha256() == old['workflow_gate_sha256']
    candidate = old['candidate_dir']
    doc, digest = G.load_frozen(candidate, old['candidate_sha256'])
    assert G.task_kind(doc) == kind
    run = str(EXECUTION / kind / 'run')
    durable = A7 / 'unit_2103_g23_grading' / kind / 'run'
    assert os.path.samefile(run, str(durable))
    inputs = {r['lane_id']: r['expected_input'] for r in root['rows']}
    new_root, root_sha, bad = G.freeze_root(candidate, run, digest, inputs)
    assert not bad and new_root == root and root_sha == old['root_sha256'], bad
    lanes, size, bad = W.next_admissible(candidate, run, root_sha)
    assert not bad and lanes == old['next_prefix_lanes'], bad
    pub, bad = G.publish_run(candidate, run, root_sha, lanes)
    assert not bad and pub['segment'] == 1, bad
    packet, bad = G.preflight(candidate, run, 1, root_sha, pub['receipt_sha256'])
    assert not bad, bad
    invocation_path = G.invocation_path(run, 1)
    invocation = G._read(invocation_path)
    old_invocation_path = G.invocation_path(old_run, 1)
    old_invocation = G._read(old_invocation_path)
    assert invocation['args'] == old_invocation['args']
    assert packet['scriptPath'] == str(Path(run) / 'grade_batch.seg01.js')
    assert os.path.samefile(packet['scriptPath'], str(durable / 'grade_batch.seg01.js'))
    invocation_sha = G._sha_file(invocation_path)
    script = Path(packet['scriptPath']).read_bytes()
    old_script = Path(G.script_path(old_run, 1)).read_bytes()
    assert script == old_script.replace(G._sha_file(old_invocation_path).encode(),
                                         invocation_sha.encode())
    assert len(script) == size == old['next_prefix_script_bytes']
    new = dict(old, run_dir=run, durable_run_dir=str(durable),
               scope='REAL unrun grading; supported path published; no model call',
               map=os.environ['A7_RUN_BINDING'],
               map_sha256=G._sha_file(os.environ['A7_RUN_BINDING']),
               first_segment=1, first_receipt_sha256=pub['receipt_sha256'],
               first_script_sha256=G._sha_file(packet['scriptPath']),
               invocation_path=invocation_path, invocation_sha256=invocation_sha,
               previous_unrun_launch=str(previous_path),
               previous_unrun_launch_sha256=expected_sha)
    G._write_new(str(durable.parent / 'LAUNCH.json'), G._pretty(new) + '\n')
    G._write_new(str(durable.parent / 'g1_args_seg01.json'), G._plain(packet['args']))
    assert G.lane_states(run) == {} and G._read(G.state_path(run, 1))['states'] == []
    report[kind] = new
print(G._pretty(report), flush=True)
