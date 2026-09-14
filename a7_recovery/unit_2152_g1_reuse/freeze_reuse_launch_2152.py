# -*- coding: utf-8 -*-
"""Freeze the unrun G1 root and publish ONLY the changed lanes. SEQ 2152.

The SEQ 2086 invocation, adapted in one way and no other: the lanes offered to
the size gate come from the shared selection owner instead of "every uncalled
lane". The root is still the EXISTING full candidate's root, carrying all of
its lanes and the same approved runtime input on every row, because a root is
the run's only approval token and a lane that is not in it can never be
published.

W.next_admissible is deliberately NOT used: it selects every uncalled lane and
would therefore reserve the carried ones. Its two steps - the existing
lifecycle check, then the existing size gate - are called here in the same
order on the selected lanes only, so no second rule is introduced.

NO MODEL IS CALLED. The run is left frozen, published and preflighted; nothing
is invoked, and lane_states stays empty.
"""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
UNIT = A7 / 'unit_2152_g1_reuse'
REPORT = A7 / 'unit_2020_codex_check/codex_keygrading2150_a/KEY_GRADING_INPUTS.json'
REPORT_SHA = 'd7571670fc3ae38a4dc732a7e377f23c385a0ee59aad3eb38d52151cd590e9f7'
#: the grading scorer the ORIGINAL root recorded; binding it keeps the owner
#: set this run freezes identical to the one the evidence owner will check.
SCORER_SHA = '6d0a02285162a079a81615db6ae64fddaa43acef64214315339c8d78bfd7f43e'
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R                                    # noqa: E402
import a7_g1_build as G                                            # noqa: E402
import a7_g23_build as B                                           # noqa: E402
import a7_g1_workflow_gate as W                                    # noqa: E402
import a7_g1_complete_v2 as C                                      # noqa: E402
sys.path.insert(0, str(UNIT))
import g1_reuse_inputs_2152 as INPUTS                              # noqa: E402

sha = lambda p: G._sha_file(str(p))
run_dir = str(UNIT / 'g1')
selection = INPUTS.derive(str(REPORT), REPORT_SHA)
cand = selection['candidate_dir']
doc, candidate_sha = G.load_frozen(cand, selection['report']['g1_candidate_sha256'])
assert doc['armed_calls'] == 0 and doc['budget']['under_ceiling'] is True

scorer = str(Path(G.__file__).parent / 'scorers/score_exp5_current.py')
B.bind_grading_scorer(scorer, SCORER_SHA)
assert G.owner_hashes()['grading_scorer'] == SCORER_SHA

expected_input = selection['expected_input']
lanes = [r['lane_id'] for r in doc['launchers']['rows']]
assert len(lanes) == len(set(lanes))
eligible = selection['eligible_lanes']
assert set(eligible) <= set(lanes)
carried_batches = set(selection['carry_batches'])

root, root_sha, bad = G.freeze_root(cand, run_dir, candidate_sha,
                                    {lane: expected_input for lane in lanes})
assert not bad, bad
assert [r['lane_id'] for r in root['rows']] == lanes
assert all(r['expected_input'] == expected_input for r in root['rows'])
assert G.load_root(run_dir, root_sha) == root

# ---- THE HONEST PRELAUNCH NEGATIVE, before anything is published ------------
# The run tree digest is measured HERE only so the evidence owner can reach the
# part under test; the thing being demonstrated is the REFUSAL below, never an
# acceptance. Nothing is scored and no expectation is invented for a result.
digest, files = C.run_digest(run_dir)
ev_root, ev_doc, ev_lanes, ev_problems = C.evidence(cand, run_dir, root_sha,
                                                    digest, files)
uncalled = sorted(lane for lane, rec in (ev_lanes or {}).items()
                  if (rec or {}).get('selected') is None)
pins = dict(selection['report']['original_g1']['pins'],
            root_sha256=root_sha, candidate_sha256=candidate_sha,
            run_tree_sha256=digest, run_file_count=files,
            prompt_tree_sha256=root['prompt_tree_sha256'],
            rules_block_sha256=root['rules_block_sha256'])
state, refuse_problems = B.refuse(cand, run_dir, pins)
g1 = {'candidate_dir': cand, 'run_dir': run_dir, 'pins': pins}
lifecycle_refusal = None
try:
    B._lifecycle(g1)
except ValueError as exc:
    lifecycle_refusal = str(exc)
assert lifecycle_refusal, 'an unrun root must not read as a proved lifecycle'

# ---- the existing two steps, on the selected lanes only ---------------------
problems = G.lifecycle_problems(run_dir, root, eligible, W.PRIMARY_ATTEMPT)
assert not problems, problems
selected, size, bad = W._largest_prefix(cand, root, eligible, W.PRIMARY_ATTEMPT)
assert not bad, bad
assert selected and size <= W.SCRIPT_BYTE_LIMIT
assert selected == eligible[:len(selected)]

publication, bad = G.publish_run(cand, run_dir, root_sha, selected)
assert not bad, bad
segment = publication['segment']
receipt_sha = publication['receipt_sha256']
packet, bad = G.preflight(cand, run_dir, segment, root_sha, receipt_sha)
assert not bad, bad
assert Path(packet['scriptPath']).stat().st_size == size
assert [r['lane_id'] for r in packet['args']] == selected
assert all(r['attempt'] == W.PRIMARY_ATTEMPT for r in packet['args'])
# NOT ONE CARRIED LANE MAY BE IN THE PUBLISHED SEGMENT
assert not {lane.rsplit('/', 1)[0] for lane in selected} & carried_batches
assert G.lane_states(run_dir) == {}          # nothing has been called

report = {
    'kind': 'REAL unrun G1 reuse launch; changed lanes only; no AI call or score',
    'model_calls': 0,
    'selection_owner': str(UNIT / 'g1_reuse_inputs_2152.py'),
    'selection_owner_sha256': sha(UNIT / 'g1_reuse_inputs_2152.py'),
    'caller_sha256': sha(__file__),
    'report': str(REPORT), 'report_sha256': REPORT_SHA,
    'candidate_dir': cand, 'candidate_sha256': candidate_sha,
    'run_dir': run_dir, 'root_sha256': root_sha,
    'owners': root['owners'], 'lane': root['lane'],
    'input_profile_sha256': INPUTS.PROFILE_SHA256,
    'expected_input': expected_input,
    'workflow_gate_sha256': W.owner_sha256(),
    'total_root_lanes': len(lanes),
    'carried_batches': len(selection['carry_batches']),
    'changed_batches': selection['changed_batches'],
    'gold_moved_batches': selection['gold_moved_batches'],
    'eligible_lanes': eligible,
    'prelaunch_uncalled_lanes': len(uncalled),
    'prelaunch_evidence_problems': len(ev_problems or []),
    'prelaunch_refuse_problems': len(refuse_problems or []),
    'prelaunch_refuse_returned_state': state is not None,
    'prelaunch_lifecycle_refusal': lifecycle_refusal,
    'first_segment': segment, 'first_segment_lanes': len(selected),
    'first_segment_lane_ids': selected,
    'first_receipt_sha256': receipt_sha,
    'first_script_path': packet['scriptPath'],
    'first_script_sha256': sha(packet['scriptPath']),
    'first_script_bytes': size,
    'invocation_path': G.invocation_path(run_dir, segment),
    'invocation_sha256': sha(G.invocation_path(run_dir, segment)),
}
G._write_new(str(UNIT / 'REUSE_LAUNCH_2152.json'), G._pretty(report) + '\n')
print(G._pretty(report), flush=True)
