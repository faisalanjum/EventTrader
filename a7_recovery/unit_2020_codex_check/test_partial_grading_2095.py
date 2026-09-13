"""Focused policy tests; native whole-run proof is separate, never mocked here."""
import copy
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_complete_v2 as C
import a7_partial_grading_2095 as P


def fixture():
    root = {'max_attempts': 2, 'rows': [{'lane_id': 'sample/G1a'}, {'lane_id': 'sample/G1b'}]}
    lanes = {
        'sample/G1a': {'attempts': {1: False, 2: False}, 'selected': None, 'relation': None},
        'sample/G1b': {'attempts': {1: True}, 'selected': 1, 'relation': {7: []}},
    }
    doc = {'schema': G.SCHEMA, 'producer_identity': 'independent-fixture'}
    state = (root, doc, lanes)
    problems = ['sample/G1a has no selected valid attempt']
    pins = {P.POLICY_PIN: G._sha_file(P.__file__), P.RULE_PIN: G._sha_file(str(P.RULE_FILE))}
    handle = {'candidate_dir': 'fixture-candidate', 'run_dir': 'fixture-run', 'pins': pins}
    return state, problems, handle


def public_call(state, problems, handle):
    with patch.object(B, 'refuse', return_value=(state, problems)) as check:
        with patch.object(B, '_resolutions_from', return_value='downstream-result') as consumer:
            with P.scope(G._sha_file(P.__file__)):
                result = B.official_resolutions(handle, 'independent-fixture')
            check.assert_called_once_with('fixture-candidate', 'fixture-run', handle['pins'])
            consumer.assert_called_once_with(state, 'independent-fixture')
    return result


def test_exhausted_invalid_admits_only_partial_reporting_without_changing_state():
    state, problems, handle = fixture()
    before = copy.deepcopy(state)
    original_entry = B._lifecycle
    assert public_call(state, problems, handle) == 'downstream-result'
    assert state == before
    assert B._lifecycle is original_entry


def test_complete_valid_control_and_empty_relation_stay_valid():
    state, _, handle = fixture()
    state[2]['sample/G1a'].update(attempts={1: True}, selected=1, relation={7: []})
    assert public_call(state, [], handle) == 'downstream-result'


@pytest.mark.parametrize('attempts', [{}, {1: False}, {2: False}, {1: False, 2: True}, {1: False, 2: False, 3: False}])
def test_unstarted_unused_retry_missing_raw_or_inconsistent_attempts_still_refuse(attempts):
    state, problems, handle = fixture()
    state[2]['sample/G1a']['attempts'] = attempts
    with pytest.raises(ValueError):
        public_call(state, problems, handle)


@pytest.mark.parametrize('problem', ['native reply missing', 'wrong request identity', 'root hash changed',
                                   'candidate hash changed', 'owner hash changed', 'unfinalized segment'])
def test_no_evidence_or_identity_problem_is_waived(problem):
    state, problems, handle = fixture()
    with pytest.raises(ValueError):
        public_call(state, problems + [problem], handle)


@pytest.mark.parametrize('name', [P.POLICY_PIN, P.RULE_PIN])
@pytest.mark.parametrize('value', [None, 'unapproved'])
def test_policy_and_rule_pins_are_required(name, value):
    state, problems, handle = fixture()
    if value is None:
        del handle['pins'][name]
    else:
        handle['pins'][name] = value
    with pytest.raises(ValueError):
        public_call(state, problems, handle)


def test_no_state_no_policy_hash_and_original_strict_entry_still_refuse():
    state, problems, handle = fixture()
    with pytest.raises(ValueError):
        public_call(None, ['missing required external pins'], handle)
    with pytest.raises(ValueError):
        with P.scope('unapproved'):
            raise AssertionError('a wrong policy hash opened the scope')
    with patch.object(B, 'refuse', return_value=(state, problems)):
        with pytest.raises(ValueError, match='no selected valid attempt'):
            B.official_resolutions(handle, 'independent-fixture')


def test_real_completion_preserves_every_uncredited_fact_and_other_event_credit():
    state, problems, handle = fixture()
    root, doc, lanes = state
    doc['launchers'] = {'lanes': ['G1a', 'G1b']}
    doc['question_bindings'] = [
        {'batch_id': 'sample', 'leg': 'P2', 'source_id': 'unfamiliar-event'},
        {'batch_id': 'control', 'leg': 'P1', 'source_id': 'another-event'},
    ]
    lanes['sample/G1b']['relation'] = {7: [11], 19: [23]}
    for letter in ['G1a', 'G1b']:
        lane = 'control/' + letter
        root['rows'].append({'lane_id': lane})
        lanes[lane] = {'attempts': {1: True}, 'selected': 1, 'relation': {31: [47]}}
    legs = {
        'P2': {'unfamiliar-event': {'unmatched_gold': [7, 19], 'unmatched_produced': [11, 23]}},
        'P1': {'another-event': {'unmatched_gold': [31], 'unmatched_produced': [47]}},
    }
    handle['pins'].update({key: 'TEST-only external pin' for key in B.PIN_KEYS})
    with patch.object(B, 'refuse', return_value=(state, problems)):
        with patch.object(G, 'inventory', return_value=(legs, {}, {}, {}, {}, [])):
            with P.scope(G._sha_file(P.__file__)):
                resolution = B.official_resolutions(handle, 'independent-fixture')
                missing = B.official_safety_findings('P2', handle, 'independent-fixture')
                clean = B.official_safety_findings('P1', handle, 'independent-fixture')
    assert resolution == {'P1': {('another-event', 31): 47}}
    assert missing['incomplete'] == [{'leg': 'P2', 'sid': 'unfamiliar-event', 'ruled': 0,
                                     'of': 2, 'why': 'a blind lane produced no valid answer'}]
    assert not clean['incomplete']
    completed, errors = C.complete(doc, legs, C.relations_from_run(lanes))
    assert not errors
    assert completed['gold_rows'] == completed['terminal_total'] == 3
    assert completed['terminal_counts']['accepted'] == 1
    assert completed['terminal_counts']['absent'] == 2
    assert completed['accepted_pairs'] == [(31, 47)]


def test_unchanged_final_gate_keeps_unknowns_and_known_failures_separate(monkeypatch):
    # This tests the served scorer, not a real run's launch identity. Keep its
    # module binding local to the test and require no caller shell fixture.
    monkeypatch.setattr(B, 'GRADING_SCORER', None)
    monkeypatch.setattr(B, 'GRADING_SCORER_PROVENANCE', None)
    path = str(Path(G.__file__).parent / 'scorers/score_exp5_current.py')
    scorer = B.bind_grading_scorer(path, G._sha_file(path))
    passing = {'gold_n': 100, 'matched': 100, 'would_park': 0, 'value_shape_acc': 1,
               'PASS': True, 'safety_result': 'PASS', 'required_grading_unfinished': False}
    assert scorer.final_gate(passing, passing, originals=[passing, passing], union_required=True) is True
    incomplete = dict(passing, safety_result='INCONCLUSIVE', required_grading_unfinished=True)
    assert scorer.final_gate(passing, passing, originals=[passing, incomplete], union_required=True) is None
    unsafe = dict(passing, confirmed_wrong_accepted=1)
    assert scorer.final_gate(unsafe, passing, originals=[unsafe, incomplete], union_required=True) is False


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_partial_identity_exception_never_accepts_another_grading_task(kind):
    state, problems, handle = fixture()
    state[1]['task_kind'] = kind
    with pytest.raises(ValueError):
        public_call(state, problems, handle)


def test_existing_identity_carries_both_policy_pins():
    _, _, handle = fixture()
    identity = B.g1_identity(handle)
    assert identity[P.POLICY_PIN] == handle['pins'][P.POLICY_PIN]
    assert identity[P.RULE_PIN] == handle['pins'][P.RULE_PIN]


def test_a_changed_retry_limit_is_not_partial_reporting():
    state, problems, handle = fixture()
    state[0]['max_attempts'] = 3
    state[2]['sample/G1a']['attempts'][3] = False
    with pytest.raises(ValueError, match='retry limit'):
        public_call(state, problems, handle)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q', '-p', 'no:cacheprovider']))
