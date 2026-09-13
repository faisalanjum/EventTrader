"""Freeze the already verified G2/G3 candidates with the existing run owner.

This is preparation only: no segment publication, Workflow or model call.
The old G1 collection and its owners remain unchanged.
"""
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as GR
import a7_g1_workflow_gate as W


def pinned(name):
    path = os.environ[name]
    assert G._sha_file(path) == os.environ[name + '_SHA256'], name
    return path, G._read(path)


old_path, old = pinned('A7_GRADING_LAUNCH')
prep_path, prep = pinned('A7_VERIFY_G23_PREPARATION')
cold_path, cold = pinned('A7_VERIFY_G23_COLD')
connection_path, connection = pinned('A7_VERIFY_PARTIAL_CONNECTION')
assert cold['candidates'] == prep['candidates']
assert cold['producer'] == prep['producer'] and cold['g1'] == prep['g1']
assert connection['real_g1_unchanged'] and connection['actual_model_calls'] == 0
assert connection['full_gold_per_leg'] == prep['full_key_fact_count']
assert connection['scope'].startswith('TEST G2/G3 verdicts;')
profile = old['input_profile']
assert G._sha_file(profile) == old['input_profile_sha256']
expected_input = G._read(profile)['expected_input_for_served_lanes']
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      old['owners']['grading_scorer'])
assert G.owner_hashes() == old['owners']
assert W.owner_sha256() == old['workflow_gate_sha256']
assert set(prep['candidates']) == set(GR.KIND_RULES)
spent = old['budget']['spent_before'] + sum(
    G._read(G.finalization_path(old['run_dir'], n))['ledger']['scheduled']
    for n in G.segments(old['run_dir']))
total = prep['remaining_calls']['total']
assert total == sum(prep['remaining_calls'][k.lower()] for k in prep['candidates'])
budget = {'spent_before': spent, 'initial_calls': total,
          'after_initial': spent + total, 'max_attempts_per_row': G.MAX_ATTEMPTS,
          'after_max': spent + total * G.MAX_ATTEMPTS,
          'ceiling': old['budget']['ceiling']}
assert budget['after_max'] <= budget['ceiling']
out = A7 / 'unit_2100_g23_grading'
for kind, identity in prep['candidates'].items():
    candidate_dir = str(Path(identity['path']).parent)
    candidate, digest = G.load_frozen(candidate_dir, identity['sha256'])
    assert G.task_kind(candidate) == kind and candidate['made_calls'] == 0
    assert candidate['g1_identity'] == B.g1_identity(prep['g1'])
    assert candidate['producer_identity'] == prep['producer']
    assert candidate['key_identity'] == prep['key_identity']
    lanes = [r['lane_id'] for r in candidate['launchers']['rows']]
    assert len(lanes) == len(set(lanes)) == prep['remaining_calls'][kind.lower()]
    run = str(out / kind / 'run')
    root, root_sha, bad = G.freeze_root(candidate_dir, run, digest,
                                      {lane: expected_input for lane in lanes})
    assert not bad, bad
    assert [r['lane_id'] for r in root['rows']] == lanes
    assert all(r['expected_input'] == expected_input for r in root['rows'])
    selected, size, bad = W.next_admissible(candidate_dir, run, root_sha)
    assert not bad and selected and size <= W.SCRIPT_BYTE_LIMIT, bad
    assert selected == lanes[:len(selected)] and G.segments(run) == []
    report = {'kind': kind, 'scope': 'REAL unrun grading; no publication or model call',
              'preparation': prep_path, 'preparation_sha256': G._sha_file(prep_path),
              'cold_proof': cold_path, 'cold_proof_sha256': G._sha_file(cold_path),
              'scoring_connection': connection_path,
              'scoring_connection_sha256': G._sha_file(connection_path),
              'g1_launch': old_path, 'g1_launch_sha256': G._sha_file(old_path),
              'candidate_dir': candidate_dir, 'candidate_sha256': digest,
              'run_dir': run, 'root_sha256': root_sha, 'owners': root['owners'],
              'lane': root['lane'], 'workflow_gate_sha256': W.owner_sha256(),
              'input_profile': profile, 'input_profile_sha256': G._sha_file(profile),
              'map': os.environ['A7_RUN_BINDING'],
              'map_sha256': G._sha_file(os.environ['A7_RUN_BINDING']),
              'grouping_owner_sha256': G._sha_file(GR.__file__),
              'total_primary_lanes': len(lanes), 'budget': budget, 'model_calls': 0,
              'next_prefix_lanes': selected, 'next_prefix_script_bytes': size}
    path = out / kind / 'LAUNCH.json'
    G._write_new(str(path), G._pretty(report) + '\n')
    print(kind, str(path), G._sha_file(str(path)), flush=True)
