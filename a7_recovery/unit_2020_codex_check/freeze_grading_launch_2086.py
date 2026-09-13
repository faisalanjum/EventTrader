"""Freeze the verified REAL G1 launch through the existing lifecycle owners.

No agent is called. The original answers, key and candidate are read only.
The current, previously observed runtime attachment is explicitly bound; an
unexpected actual input remains a refusal at the existing native auditor.
"""
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
PREP = A7 / 'unit_2020_codex_check/codex_gprep2086_a/PREPARATION.json'
EXPECTED_PREP = 'a889236369af76bdbadb3ffc9056395524b5473d45647e00e2c45e919e91ab6c'
COLD = A7 / 'unit_2020_codex_check/codex_gprepcold2086_a/PREPARATION.json'
EXPECTED_COLD = '2c2b98e91ffd81ea52a6596271bc71dae003036332d34dc7e28390375081058e'
PROFILE = A7 / 'unit_2068_input_recovery/input_profile_2068.json'
EXPECTED_PROFILE = '78b58fe7fd5ba60b9199ada86fe27d90101ceb57cd7617db158e2ea724e2da18'
SCORER_SHA = '6d0a02285162a079a81615db6ae64fddaa43acef64214315339c8d78bfd7f43e'
OUT = A7 / 'unit_2086_real_grading'
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_workflow_gate as W

sha = lambda p: G._sha_file(str(p))
assert sha(PREP) == EXPECTED_PREP and sha(COLD) == EXPECTED_COLD
assert sha(PROFILE) == EXPECTED_PROFILE
prep = G._read(str(PREP))
cold = G._read(str(COLD))
assert cold['g1_candidate_sha256'] == prep['g1_candidate_sha256']
assert cold['run'] == prep['run'] and cold['population'] == prep['population']
cand = str(Path(prep['g1_candidate']).parent)
doc, candidate_sha = G.load_frozen(cand, prep['g1_candidate_sha256'])
assert doc['producer_identity'] == prep['run']
assert doc['armed_calls'] == 0 and doc['budget']['under_ceiling'] is True

scorer = str(Path(G.__file__).parent / 'scorers/score_exp5_current.py')
B.bind_grading_scorer(scorer, SCORER_SHA)
assert G.owner_hashes()['grading_scorer'] == SCORER_SHA
expected_input = G._read(str(PROFILE))['expected_input_for_served_lanes']
lanes = [r['lane_id'] for r in doc['launchers']['rows']]
assert len(lanes) == len(set(lanes)) == prep['population']['reviewer_calls']
run_dir = str(OUT / 'g1')
root, root_sha, bad = G.freeze_root(cand, run_dir, candidate_sha,
                                  {lane: expected_input for lane in lanes})
assert not bad, bad
assert [r['lane_id'] for r in root['rows']] == lanes
assert all(r['expected_input'] == expected_input for r in root['rows'])
assert G.load_root(run_dir, root_sha) == root
selected, size, bad = W.next_admissible(cand, run_dir, root_sha)
assert not bad and selected and size <= W.SCRIPT_BYTE_LIMIT, bad
assert selected == lanes[:len(selected)]
publication, bad = G.publish_run(cand, run_dir, root_sha, selected)
assert not bad, bad
segment = publication['segment']
receipt_sha = publication['receipt_sha256']
packet, bad = G.preflight(cand, run_dir, segment, root_sha, receipt_sha)
assert not bad, bad
assert Path(packet['scriptPath']).stat().st_size == size
assert [r['lane_id'] for r in packet['args']] == selected
assert all(r['attempt'] == 1 for r in packet['args'])
assert G.lane_states(run_dir) == {}  # nothing has been called
report = {'kind': 'REAL unrun G1 launch; no AI call or score', 'model_calls': 0,
          'preparation': str(PREP), 'preparation_sha256': EXPECTED_PREP,
          'cold_proof': str(COLD), 'cold_proof_sha256': EXPECTED_COLD,
          'candidate_dir': cand, 'candidate_sha256': candidate_sha,
          'run_dir': run_dir, 'root_sha256': root_sha,
          'owners': root['owners'], 'lane': root['lane'],
          'input_profile': str(PROFILE), 'input_profile_sha256': EXPECTED_PROFILE,
          'workflow_gate_sha256': W.owner_sha256(),
          'total_primary_lanes': len(lanes), 'budget': doc['budget'],
          'first_segment': segment, 'first_segment_lanes': len(selected),
          'first_receipt_sha256': receipt_sha,
          'first_script_sha256': sha(packet['scriptPath']),
          'first_script_bytes': size,
          'invocation_path': G.invocation_path(run_dir, segment),
          'invocation_sha256': sha(G.invocation_path(run_dir, segment))}
G._write_new(str(OUT / 'LAUNCH.json'), G._pretty(report) + '\n')
print(G._pretty(report), flush=True)
