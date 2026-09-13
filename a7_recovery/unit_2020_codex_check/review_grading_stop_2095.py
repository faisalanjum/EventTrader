"""Replay the saved collection and prove the real public scoring-entry stop.

This proof calls unchanged owners. It launches no model and changes no saved
answer, run, key, prompt or grading rule.
"""
import json
import os
import runpy
from pathlib import Path

review = runpy.run_path(str(Path(__file__).with_name('review_grading_segment_2090.py')))
B, C = review['B'], review['C']
pins = json.loads(os.environ['A7_REVIEW_G1_PINS'])
candidate, run = review['candidate'], review['run']
expected_missing = json.loads(os.environ['A7_REVIEW_MISSING_LANES'])
state, problems = B.refuse(candidate, run, pins)
assert state is not None, problems
assert problems == [lane + ' has no selected valid attempt' for lane in expected_missing], problems
assert review['result']['remaining'] == expected_missing
assert not review['result']['native_audits'][0]['problems']

handle = {'candidate_dir': candidate, 'run_dir': run, 'pins': pins}
try:
    B.official_resolutions(handle, review['doc']['producer_identity'])
except ValueError as exc:
    public_error = str(exc)
    assert public_error == ('the approved G1 lifecycle does not hold: %s' % problems[:2]), public_error
else:
    raise AssertionError('public resolutions accepted a run with missing valid readings')

assert C.run_digest(run) == review['expected'], 'proof changed or raced with the saved run'
result = {
    'scope': 'Unchanged public G1 gate; no semantic score or rule change',
    'pins': pins,
    'positive_control': 'All native and complete evidence checks passed before the valid-reading gate',
    'required_primary': review['result']['required_primary'],
    'collected_unique': review['result']['collected_unique'],
    'selected_valid': review['result']['selected_valid'],
    'missing_valid_lanes': expected_missing,
    'collected_without_valid_answer': review['result']['collected_without_valid_answer'],
    'refuse_problems': problems,
    'public_entry': 'a7_g23_build.official_resolutions',
    'public_error': public_error,
    'inputs_unchanged': True,
}
(review['out'] / 'STOP_PROOF.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print('PUBLIC_GATE_STOP_PROVED', len(problems), 'missing valid readings', flush=True)
