"""Read-only diagnosis of the completed script-copy run; no admission or score.

Reproduce the original refusal, then vary ONLY the expected script location
using its independently pinned pre-call record. All native answer checks and
the existing response parser stay unchanged. This cannot finalize a run.
"""
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import audit_worker_access as AUD

launch_path = os.environ['A7_GRADING_LAUNCH']
assert G._sha_file(launch_path) == os.environ['A7_GRADING_LAUNCH_SHA256']
launch = G._read(launch_path)
run, cand, n = launch['run_dir'], launch['candidate_dir'], launch['first_segment']
root, receipt, bad = G.approved(run, n, launch['root_sha256'], launch['first_receipt_sha256'])
assert not bad, bad
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      launch['owners']['grading_scorer'])
_packet, bad = G.preflight(cand, run, n, launch['root_sha256'], launch['first_receipt_sha256'])
assert not bad, bad
assert G._sha_file(AUD.__file__) == '53e6cba4cf4d243c1a6f7a95ff11776bfc45336cab3707ce8b0a219942d1c562'
precall_path = str(A7 / 'unit_2154_g1_collection/AUTHORIZATION_2154.json')
assert G._sha_file(precall_path) == 'db48422dc0fc7a7516ffb8eb0d0790dbc044d4bdec442dd0f97ef8b85485291d'
precall = G._read(precall_path)
state_path = (AUD.PROJECTS_ROOT + '/-home-faisal-EventMarketDB/'
              '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows/wf_d965de9c-9ba.json')
assert G._sha_file(state_path) == '1cb144fb86d34b6ad23487f15b759b66fecc6edf170c5fefb2b0279756bfb304'
state = G._read(state_path)
invocation = G._read(receipt['invocation_path'])
assert precall['frozen_script_path'] == receipt['script_path'] == invocation['scriptPath']
assert precall['staged_script_path'] != receipt['script_path']
assert G._sha(state['script']) == receipt['script_sha256']
assert precall['frozen_script_sha256'] == precall['staged_script_sha256'] == receipt['script_sha256']
reservation = G._read(G.reservation_path(run, n))
rows, bad = G._rows_for(cand, root, reservation['lanes'], reservation['attempt'])
assert not bad, bad
expected_inputs = {r['lane_id']: r['expected_input'] for r in root['rows']}
captures = []
for result in state['result']['results']:
    returned = {f: result.get(f) for f in G.RESULT_BINDING}
    returned.update(text=result.get('text'), error=result.get('error'))
    captures.append(dict(lane_id=result.get('lane_id'), text=result.get('text'),
                         error=result.get('error'), returned=returned))
expect = dict(script_path=receipt['script_path'], script_sha256=receipt['script_sha256'],
              args=invocation['args'], rows=[dict(lane_id=r['lane_id'], ordinal=r['ordinal'],
              prompt=r['prompt'], prompt_sha256=r['prompt_sha256'],
              expected_input=expected_inputs[r['lane_id']]) for r in rows],
              runtime_model_id=root['lane']['runtime_model_id'],
              agentType=root['lane']['agentType'], effort=root['lane']['effort'], captures=captures)
original_bad, original_whole = AUD.g1_state_audit(state_path, expect)
assert original_bad == ["the state ran %r, this segment published %r" % (
    precall['staged_script_path'], receipt['script_path'])], original_bad
assert original_whole == {}
corrected_expect = dict(expect, script_path=precall['staged_script_path'])
bad, whole = AUD.g1_state_audit(state_path, corrected_expect)
doc, _sha = G.load_frozen(cand, root['candidate_sha256'])
binding, parser = G.binding_and_parser(G.task_kind(doc))
valid, invalid = [], {}
if not bad:
    assert set(whole) == {r['lane_id'] for r in rows}
    for row in rows:
        _reply, why = parser(whole[row['lane_id']], binding(doc, row['batch_id']))
        if why:
            invalid[row['lane_id']] = why
        else:
            valid.append(row['lane_id'])
report = dict(scope='READ-ONLY counterfactual location diagnosis, NOT admission/finalization/score',
              state_path=state_path, state_sha256=G._sha_file(state_path),
              original_refusal=original_bad, location_only_native_problems=bad,
              whole_answer_count=len(whole), response_contract_valid=valid,
              response_contract_invalid=invalid, run_unchanged=True)
assert G._read(G.state_path(run, n))['states'] == []
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir(exist_ok=False)
G._write_new(str(out / 'G1_TRANSPORT_PROBE.json'), G._pretty(report) + '\n')
print(G._pretty(report), flush=True)
