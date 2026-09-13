"""Versioned A7 partial-report admission, separate from frozen collection.

The original run remains validated by its original owners. Only the later
reporting entry is replaced in an explicit scope; no saved run or parser is
changed. The reporting code and rule travel in the existing G1 identity pins.
"""
from contextlib import contextmanager
from pathlib import Path

import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B

POLICY_PIN = 'partial_grading_policy_sha256'
RULE_PIN = 'partial_grading_rule_sha256'
RULE_FILE = Path(__file__).resolve().parents[2] / '.claude/plans/Drivers/FinalDesign/FableExperimentPlan.md'


def lifecycle(g1):
    """Allow only exhausted, evidenced invalids past the old all-valid gate.

    No caller can supply a state or a ruling: the frozen checker reads all
    native evidence itself. Its only waived messages are the exact missing-
    valid messages for lanes whose complete bounded attempts were invalid.
    The original completion/scorer still owns all credit and incomplete flags.
    """
    pins = (g1 or {}).get('pins') or {}
    for name, path in ((POLICY_PIN, __file__), (RULE_PIN, str(RULE_FILE))):
        if pins.get(name) != G._sha_file(path):
            raise ValueError('missing or changed partial grading pin: ' + name)
    state, problems = B.refuse(g1['candidate_dir'], g1['run_dir'], pins)
    if state is None:
        raise ValueError('partial grading evidence refused: %s' % problems)
    root, doc, lanes = state
    if G.task_kind(doc) != 'G1':
        raise ValueError('partial identity admission requires a G1 run')
    missing = [r['lane_id'] for r in root['rows']
               if (lanes.get(r['lane_id']) or {}).get('selected') is None]
    allowed = [lane + ' has no selected valid attempt' for lane in missing]
    if problems != allowed:
        raise ValueError('partial grading evidence refused: %s' % problems)
    if root['max_attempts'] != G.MAX_ATTEMPTS:
        raise ValueError('partial grading cannot change the frozen retry limit')
    exhausted = {n: False for n in range(1, root['max_attempts'] + 1)}
    for lane in missing:
        if (lanes.get(lane) or {}).get('attempts') != exhausted:
            raise ValueError('%s is not an exhausted, fully evidenced invalid reading' % lane)
    return state


@contextmanager
def scope(expected_sha256):
    if G._sha_file(__file__) != expected_sha256:
        raise ValueError('partial grading policy does not match its approved hash')
    with R._using(B, _lifecycle=lifecycle):
        yield
