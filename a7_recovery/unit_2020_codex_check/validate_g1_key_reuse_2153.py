"""Native saved-reading reuse and prelaunch refusal; no model call or score."""
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2143_source_authority'))
from build_candidate_2148 import E
import a7_g1_key_reuse_2152 as REUSE
sys.path.insert(0, str(A7 / 'unit_2152_g1_reuse'))
import g1_reuse_inputs_2152 as SELECT

G, B, C = E.G, E.B, REUSE.C
input_path = os.environ['A7_G1_REUSE_VALIDATION']
assert G._sha_file(input_path) == os.environ['A7_G1_REUSE_VALIDATION_SHA256']
approved = E.K._load(input_path)
selection = SELECT.derive(approved['report'], approved['report_sha256'])
assert G._sha_file(approved['launch_report']) == approved['launch_report_sha256']
launch = E.K._load(approved['launch_report'])


def check(producer, inputs, g1):
    state, problems = B.refuse(g1['candidate_dir'], g1['run_dir'], g1['pins'])
    assert state is not None
    root, doc, lanes = state
    assert doc['producer_identity'] == producer
    assert doc == selection['current_candidate']
    current = set(selection['eligible_lanes'])
    carried = set(lanes) - current
    valid = {lane for lane in carried if lanes[lane]['selected'] is not None}
    invalid = carried - valid
    assert len(valid) == approved['expected_carried_valid']
    assert len(invalid) == approved['expected_carried_exhausted_invalid']
    assert all(lanes[lane]['attempts'] == {n: False for n in range(1, root['max_attempts'] + 1)}
               for lane in invalid)
    assert all(lanes[lane]['attempts'] == {} and lanes[lane]['selected'] is None
               and lanes[lane]['relation'] is None for lane in current)
    assert problems == [r['lane_id'] + ' has no selected valid attempt' for r in root['rows']
                        if r['lane_id'] in current | invalid]
    try:
        B.official_resolutions(g1, producer)
    except ValueError as exc:
        refusal = str(exc)
        first = selection['eligible_lanes'][0]
        assert refusal == first + ' is not an exhausted, fully evidenced invalid reading', refusal
    else:
        raise AssertionError('the actual grading consumer credited unfinished changed tasks')

    published = approved['published_g1']
    packet, bad = G.preflight(published['candidate_dir'], published['run_dir'],
                              launch['first_segment'], published['pins']['root_sha256'],
                              launch['first_receipt_sha256'])
    assert not bad, bad
    assert [r['lane_id'] for r in packet['args']] == selection['eligible_lanes']
    assert G._sha_file(packet['scriptPath']) == launch['first_script_sha256']
    assert Path(packet['scriptPath']).stat().st_size == launch['first_script_bytes']
    _pending, pending_problems = B.refuse(published['candidate_dir'], published['run_dir'],
                                         published['pins'])
    assert 'segment 1 is not finalized' in pending_problems
    assert len(pending_problems) == 1 + len(root['rows'])
    result = {'scope': 'REAL original native proof/current-key consumer reuse; prelaunch only, NO score',
              'input_path': input_path, 'input_sha256': G._sha_file(input_path),
              'producer': producer, 'g1': g1, 'published_g1': published,
              'root_lanes': len(lanes), 'carried_valid': len(valid),
              'carried_invalid': {lane: lanes[lane] for lane in sorted(invalid)},
              'changed_uncalled': sorted(current), 'missing_selections': len(problems),
              'actual_resolution_consumer_refusal': refusal,
              'published_native_problems': pending_problems,
              'published_preflight_bytes': launch['first_script_bytes'],
              'g1_identity': B.g1_identity(g1), 'new_model_calls': 0}
    print('Native carry proved:', len(valid), 'valid;', len(invalid), 'exhausted invalid;',
          len(current), 'changed uncalled. Consumer refuses as required.', flush=True)
    return result


result = REUSE.evaluate(E, approved['report'], approved['negative_g1'], check)
G._write_new(str(E.out / 'G1_REUSE_NATIVE_REVIEW.json'), G._pretty(result) + '\n')
print('Native G1 reuse/preflight review complete; no model call or score.', flush=True)
