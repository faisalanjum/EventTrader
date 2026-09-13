"""Offline recovery tests only; these authorize no model call or scoring change."""
import copy
import itertools
import json
import sys
from pathlib import Path

import pytest

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F


@pytest.fixture(autouse=True)
def scorer(monkeypatch):
    monkeypatch.setattr(B, 'GRADING_SCORER', None)
    monkeypatch.setattr(B, 'GRADING_SCORER_PROVENANCE', None)
    path = str(Path(G.__file__).parent / 'scorers/score_exp5_current.py')
    B.bind_grading_scorer(path, G._sha_file(path))


def case(value=True):
    return [{'question_id': 'unfamiliar-id',
             'verdicts': {field: value for field in B.meaning_fields()}}], {
                 'question_ids': ['unfamiliar-id']}


@pytest.mark.parametrize('value', [True, False, None])
@pytest.mark.parametrize('fenced', [False, True])
def test_exact_values_recover_without_changing_any_judgment(value, fenced):
    rows, packet = case(value)
    expected = {row['question_id']: copy.deepcopy(row['verdicts']) for row in rows}
    for row in rows:
        row['verdicts'] = {field: json.dumps(v) for field, v in row['verdicts'].items()}
    raw = json.dumps(rows)
    if fenced:
        raw = '```json\n' + raw + '\n```'
    before = copy.deepcopy(packet)
    assert B.read_meaning_reply(raw, packet)[1]
    answer, problems, audit = F.read(raw, packet)
    assert not problems
    assert answer == expected
    assert audit['original_valid'] is False
    assert len(audit['conversions']) == len(B.meaning_fields())
    assert packet == before
    assert B.read_meaning_reply(raw, packet)[1], 'original reply must remain invalid'


@pytest.mark.parametrize('value', [True, False, None])
def test_native_valid_control_is_unchanged_and_needs_no_recovery(value):
    rows, packet = case(value)
    raw = json.dumps(rows)
    expected, original_problems = B.read_meaning_reply(raw, packet)
    assert not original_problems
    answer, problems, audit = F.read(raw, packet)
    assert not problems and answer == expected
    assert audit['original_valid'] is True and audit['conversions'] == []


def test_each_field_handles_mixed_representations_without_rewriting_other_fields():
    for field, value in itertools.product(B.meaning_fields(), [True, False, None]):
        rows, packet = case(False)
        rows[0]['verdicts'][field] = value
        expected = copy.deepcopy(rows[0]['verdicts'])
        rows[0]['verdicts'][field] = json.dumps(value)
        result, bad, audit = F.read(json.dumps(rows), packet)
        assert not bad and result == {'unfamiliar-id': expected}
        assert audit['conversions'] == [{'question_id': 'unfamiliar-id',
                                         'field': field, 'from': json.dumps(value), 'to': value}]


@pytest.mark.parametrize('invalid', [0, 1, -1, 0.0, 1.0, '0', '1', '', 'True',
                                   'False', 'NULL', ' true', 'false ', 'null\n',
                                   'yes', 'no', [], {}, ['true']])
def test_every_wrong_type_or_nonexact_string_stays_invalid_with_positive_control(invalid):
    for field in B.meaning_fields():
        rows, packet = case('true')
        rows[0]['verdicts'][field] = invalid
        result, bad, _ = F.read(json.dumps(rows), packet)
        assert result is None and bad
        rows[0]['verdicts'][field] = True
        result, bad, _ = F.read(json.dumps(rows), packet)
        assert result is not None and not bad


@pytest.mark.parametrize('fault', ['missing_question', 'extra_question', 'repeated_question',
                                  'unknown_id', 'missing_aspect', 'extra_aspect',
                                  'missing_top_field', 'extra_top_field', 'bad_id',
                                  'nonobject', 'not_array', 'not_verdict_object'])
def test_original_schema_and_identity_checks_still_own_the_boundary(fault):
    rows, packet = case('true')
    if fault == 'missing_question':
        packet['question_ids'].append('another-id')
    elif fault == 'extra_question':
        rows.append(dict(rows[0], question_id='extra-id'))
    elif fault == 'repeated_question':
        rows.append(copy.deepcopy(rows[0]))
    elif fault == 'unknown_id':
        rows[0]['question_id'] = 'not-asked'
    elif fault == 'missing_aspect':
        del rows[0]['verdicts'][B.meaning_fields()[0]]
    elif fault == 'extra_aspect':
        rows[0]['verdicts']['not-an-aspect'] = 'true'
    elif fault == 'missing_top_field':
        del rows[0]['question_id']
    elif fault == 'extra_top_field':
        rows[0]['explanation'] = 'not allowed'
    elif fault == 'bad_id':
        rows[0]['question_id'] = []
    elif fault == 'nonobject':
        rows[0] = 'true'
    elif fault == 'not_array':
        rows = rows[0]
    else:
        rows[0]['verdicts'] = 'true'
    raw = json.dumps(rows)
    assert B.read_meaning_reply(raw, packet)[1]
    answer, problems, _ = F.read(raw, packet)
    assert answer is None and problems
    control, packet = case('false')
    assert not F.read(json.dumps(control), packet)[1]


@pytest.mark.parametrize('fault', ['duplicate_key', 'nan', 'infinity', 'prose', 'two_blocks', 'truncated'])
def test_transport_refusals_are_never_repaired(fault):
    rows, packet = case('true')
    raw = json.dumps(rows)
    if fault == 'duplicate_key':
        raw = raw.replace('"question_id":', '"question_id":"shadow-id", "question_id":', 1)
    elif fault in ('nan', 'infinity'):
        raw = raw.replace('"true"', 'NaN' if fault == 'nan' else 'Infinity', 1)
    elif fault == 'prose':
        raw = 'I refuse. ' + raw
    elif fault == 'two_blocks':
        raw = '```json\n' + raw + '\n```\n```json\n[]\n```'
    else:
        raw = raw[:-2]
    assert B.read_meaning_reply(raw, packet)[1]
    answer, problems, _ = F.read(raw, packet)
    assert answer is None and problems


def test_reconciliation_keeps_false_null_and_disagreement_distinct():
    for left, right in itertools.product([True, False, None], repeat=2):
        a, packet = case(json.dumps(left))
        b, _ = case(json.dumps(right))
        first, bad, _ = F.read(json.dumps(a), packet)
        assert not bad
        second, bad, _ = F.read(json.dumps(b), packet)
        assert not bad
        agreed, unresolved = B.reconcile_meaning(first, second)
        if left is not None and left is right:
            assert not unresolved
            assert agreed == {'unfamiliar-id': {f: left for f in B.meaning_fields()}}
        else:
            assert unresolved and not agreed


@pytest.fixture
def run_fixture(monkeypatch):
    """Unit boundary doubles, not native-evidence proof."""
    rows, packet = case('false')
    root = {'candidate_dir': 'fixture-candidate', 'candidate_sha256': 'candidate-pin',
            'rows': [{'lane_id': 'batch/G1a', 'batch_id': 'batch'}]}
    doc = {'task_kind': 'G2'}
    lanes = {'batch/G1a': {'batch_id': 'batch', 'attempts': {1: False},
                         'selected': None, 'relation': None}}
    final = {'attempt': 1, 'validity': [['batch/G1a', False]], 'uncalled': []}
    monkeypatch.setattr(C, 'evidence', lambda *args: (root, doc, copy.deepcopy(lanes), []))
    monkeypatch.setattr(C, 'g23_identity', lambda *args: {
        'root_sha256': 'root-pin', 'run_dir': 'fixture-run', 'run_digest': 'run-pin', 'run_files': 10})
    monkeypatch.setattr(G, 'load_root', lambda *args: root)
    monkeypatch.setattr(G, 'load_frozen', lambda *args: (doc, 'candidate-pin'))
    monkeypatch.setattr(G, 'segments', lambda *args: [1])
    monkeypatch.setattr(G, 'segment_state', lambda *args: 'finalized')
    monkeypatch.setattr(G, '_read', lambda *args: final)
    monkeypatch.setattr(G, 'whole_answers', lambda *args: ({'batch/G1a': json.dumps(rows)}, []))
    monkeypatch.setattr(G, 'binding_and_parser', lambda *args: (lambda *a: packet, B.read_meaning_reply))
    return root, doc, lanes, final


def approved_scope():
    return F.scope(G._sha_file(F.__file__), G._sha_file(str(F.RULE_FILE)))


def test_versioned_completion_gets_recovered_relation_and_original_invalid_record(run_fixture):
    original_evidence, original_identity = C.evidence, C.g23_identity
    with approved_scope():
        root, doc, lanes, bad = C.evidence('fixture-candidate', 'fixture-run', 'root-pin', 'run-pin', 10)
        assert not bad
        assert lanes['batch/G1a']['relation'] == {'unfamiliar-id': {f: False for f in B.meaning_fields()}}
        assert lanes['batch/G1a']['selected'] == 1
        assert lanes['batch/G1a']['attempts'] == {1: False}, 'original invalid flag must survive'
        ident = C.g23_identity('root-pin', 'fixture-run')
        audit = ident['meaning_format_recovery']
        assert audit['code_sha256'] == G._sha_file(F.__file__)
        assert audit['rule_sha256'] == G._sha_file(str(F.RULE_FILE))
        assert audit['attempts'][0]['original_valid'] is False
        assert audit['attempts'][0]['recovered'] is True
    assert C.evidence is original_evidence and C.g23_identity is original_identity
    assert original_evidence()[2]['batch/G1a']['selected'] is None


@pytest.mark.parametrize('error', ['missing native evidence', 'identity drift', 'unfinished segment',
                                  'refusal', 'wrong run hash', 'wrong frozen owner'])
def test_original_evidence_refusals_cannot_be_normalized_away(run_fixture, monkeypatch, error):
    root, doc, lanes, final = run_fixture
    monkeypatch.setattr(C, 'evidence', lambda *args: (root, doc, lanes, [error]))
    def forbidden(*args):
        raise AssertionError('format recovery ran after original evidence was refused')
    monkeypatch.setattr(G, 'whole_answers', forbidden)
    with approved_scope():
        result = C.evidence('fixture-candidate', 'fixture-run', 'root-pin', 'run-pin', 10)
    assert result == (root, doc, lanes, [error])


@pytest.mark.parametrize('which', ['code', 'rule'])
def test_an_unapproved_format_version_never_opens_the_scope(which):
    pins = [G._sha_file(F.__file__), G._sha_file(str(F.RULE_FILE))]
    pins[0 if which == 'code' else 1] = 'not-approved'
    with pytest.raises(ValueError):
        with F.scope(*pins):
            pass


@pytest.mark.parametrize('kind', ['G1', 'G3'])
def test_other_grading_kinds_are_unchanged(run_fixture, kind):
    root, doc, lanes, final = run_fixture
    doc['task_kind'] = kind
    original_evidence, original_identity = C.evidence, C.g23_identity
    with approved_scope():
        assert C.evidence('c', 'r', 'h', 'd', 10) == original_evidence('c', 'r', 'h', 'd', 10)
        assert C.g23_identity('h', 'r') == original_identity('h', 'r')


@pytest.mark.parametrize('second, selected, expected', [('true', 2, True), ('True', 1, False)])
def test_existing_latest_usable_attempt_rule_is_preserved(run_fixture, monkeypatch, second, selected, expected):
    root, doc, lanes, final = run_fixture
    lanes['batch/G1a']['attempts'] = {1: False, 2: False}
    monkeypatch.setattr(G, 'segments', lambda *args: [1, 2])
    monkeypatch.setattr(G, '_read', lambda path: dict(final, attempt=2 if 'seg02' in path else 1))
    def answers(run, segment):
        rows, _ = case('false' if segment == 1 else second)
        return {'batch/G1a': json.dumps(rows)}, []
    monkeypatch.setattr(G, 'whole_answers', answers)
    with approved_scope():
        result = C.evidence('c', 'r', 'h', 'd', 10)[2]['batch/G1a']
    assert result['selected'] == selected
    assert result['relation'] == {'unfamiliar-id': {f: expected for f in B.meaning_fields()}}
    assert result['attempts'] == {1: False, 2: False}


def test_explicit_zero_call_closure_is_not_a_missing_model_answer(run_fixture, monkeypatch):
    root, doc, lanes, final = run_fixture
    final['uncalled'] = ['batch/G1a']
    lanes['batch/G1a']['attempts'] = {}
    def no_answer(*args):
        raise AssertionError('an uncalled reservation has no model answer to recover')
    monkeypatch.setattr(G, 'whole_answers', no_answer)
    with approved_scope():
        assert C.evidence('c', 'r', 'h', 'd', 10)[2] == lanes
        assert C.g23_identity('h', 'r')['meaning_format_recovery']['attempts'] == []


@pytest.mark.parametrize('fault', ['whole_error', 'unfinalized', 'unbound_reply',
                                  'unknown_lane', 'duplicate_attempt', 'validity_drift'])
def test_recovery_reread_refuses_each_own_evidence_failure(run_fixture, monkeypatch, fault):
    root, doc, lanes, final = run_fixture
    with approved_scope():
        assert not C.evidence('c', 'r', 'h', 'd', 10)[3]
    if fault == 'whole_error':
        monkeypatch.setattr(G, 'whole_answers', lambda *args: (None, ['whole bytes moved']))
    elif fault == 'unfinalized':
        monkeypatch.setattr(G, 'segment_state', lambda *args: 'published')
    elif fault == 'unbound_reply':
        monkeypatch.setattr(G, 'whole_answers', lambda *args: ({'unbound/lane': '[]'}, []))
    elif fault == 'unknown_lane':
        root['rows'] = []
    elif fault == 'duplicate_attempt':
        monkeypatch.setattr(G, 'segments', lambda *args: [1, 2])
    else:
        final['validity'] = [['batch/G1a', True]]
    with pytest.raises(ValueError), approved_scope():
        C.evidence('c', 'r', 'h', 'd', 10)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q', '-p', 'no:cacheprovider']))
