"""Ordered correction composition; native lifecycle proof is separate."""
import copy
import json
import sys
import types
from pathlib import Path

import pytest
import test_grading_revision_2115 as ENV
import a7_grading_revision_chain_2169 as CHAIN

G, B, REV = ENV.G, ENV.B, ENV.REV
case = ENV.case


def chained(revisions):
    return CHAIN.scope(revisions, G._sha_file(CHAIN.__file__))


def plans(case, tmp_path):
    refs = []
    for index, kind in enumerate(('G2', 'G3')):
        plan = copy.deepcopy(case['plan'])
        plan['corrections'] = {kind: plan['corrections'][kind]}
        path = tmp_path / ('round%d.json' % index)
        path.write_text(json.dumps(plan), encoding='utf-8')
        refs.append({'path': str(path), 'sha256': G._sha_file(str(path))})
    return refs


def test_two_required_corrections_preserve_both_results(case, tmp_path):
    baseline = case['run']()
    refs = plans(case, tmp_path)
    # Each existing correction works by itself: this is not invalid evidence.
    with REV.scope(refs[0]['path'], refs[0]['sha256']):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False
    with REV.scope(refs[1]['path'], refs[1]['sha256']):
        assert case['run']()[1][('source-A', 11)] == 'key_miss'
    with chained(refs):
        meaning, extras = case['run']()
    assert meaning == {('source-A', 2): {'driver_state': False},
                       ('source-A', 5): {'driver_state': False}}
    assert extras == {('source-A', 11): 'key_miss', ('source-A', 12): 'duplicate'}
    assert B._verdict_maps_from is case['original']
    assert case['run']() == baseline


@pytest.fixture
def same_question(case, tmp_path, monkeypatch):
    refs = plans(case, tmp_path)
    source = {'run_dir': 'second-G2', 'root_sha256': 'second-root',
              'completion_sha256': 'second-completion'}
    plan = json.loads(Path(refs[0]['path']).read_text())
    correction = plan['corrections']['G2']
    correction['source'] = source
    correction['reason'] = 'a separately proved later task correction'
    correction['input_correction_sha256'] = 'c' * 64
    answers = {('source-A', 2): {'growth_basis': True}}
    original = B._verdict_maps_from

    def native(leg, sources, producer, required, g1, memo):
        if sources == {'G2': source}:
            assert required == {'G2': correction['population']}
            assert producer == plan['producer_identity']
            assert B.g1_identity(g1) == plan['g1_identity']
            memo[('G2', source['run_dir'], source['root_sha256'],
                  source['completion_sha256'])] = ({
                      'input_correction_sha256': 'c' * 64}, {})
            return (copy.deepcopy(answers) if leg == 'P1' else {}), {}
        return original(leg, sources, producer, required, g1, memo)

    monkeypatch.setattr(B, '_verdict_maps_from', native)
    path = tmp_path / 'later.json'
    path.write_text(json.dumps(plan))
    refs[1] = {'path': str(path), 'sha256': G._sha_file(str(path))}
    return refs, answers, native


def test_latest_partial_answer_does_not_inherit_an_older_aspect(case, same_question):
    refs, answers, native = same_question
    baseline = case['run']()
    with chained(refs):
        current = case['run']()
        assert current[0][('source-A', 2)] == {'growth_basis': True}
        assert current[0][('source-A', 5)] == baseline[0][('source-A', 5)]
        assert current[1] == baseline[1]
    with chained(list(reversed(refs))):
        assert case['run']()[0][('source-A', 2)] == {'driver_state': False}
    assert B._verdict_maps_from is native and case['run']() == baseline


def test_latest_unresolved_answer_removes_prior_credit(case, same_question):
    refs, answers, native = same_question
    with chained(refs):
        assert case['run']()[0][('source-A', 2)]
    answers.clear()
    with chained(refs):
        result = case['run']()
        assert ('source-A', 2) not in result[0]
        assert result[0][('source-A', 5)] == {'driver_state': False}
    assert B._verdict_maps_from is native


@pytest.mark.parametrize('bad', ['empty', 'not_list', 'extra_field', 'duplicate',
                                'wrong_pin', 'wrong_code', 'wrong_owner'])
def test_bad_chain_refuses_with_a_valid_control(case, tmp_path, monkeypatch, bad):
    refs = plans(case, tmp_path)
    with chained(refs):
        assert case['run']()[1][('source-A', 11)] == 'key_miss'
    code_pin = G._sha_file(CHAIN.__file__)
    if bad == 'empty':
        refs = []
    elif bad == 'not_list':
        refs = {'rounds': refs}
    elif bad == 'extra_field':
        refs[0]['unapproved'] = True
    elif bad == 'duplicate':
        refs.append(refs[0])
    elif bad == 'wrong_pin':
        refs[0]['sha256'] = '0' * 64
    elif bad == 'wrong_code':
        code_pin = '0' * 64
    else:
        monkeypatch.setattr(CHAIN, 'REVISION_SHA256', '0' * 64)
    with pytest.raises(ValueError):
        with CHAIN.scope(refs, code_pin):
            case['run']()
    assert B._verdict_maps_from is case['original']


@pytest.mark.parametrize('when', ['before_read', 'after_read'])
def test_an_in_scope_plan_edit_refuses_and_restores(case, tmp_path, when):
    refs = plans(case, tmp_path)
    with chained(refs):
        assert case['run']()[1][('source-A', 11)] == 'key_miss'
    with pytest.raises(ValueError):
        with chained(refs):
            if when == 'after_read':
                case['run']()
            path = Path(refs[0]['path'])
            path.write_text(path.read_text() + '\n')
            if when == 'before_read':
                case['run']()
    assert B._verdict_maps_from is case['original']


def test_native_refusal_still_propagates(case, tmp_path, monkeypatch):
    refs = plans(case, tmp_path)
    with chained(refs):
        assert case['run']()[1][('source-A', 11)] == 'key_miss'
    original = B._verdict_maps_from

    def refusal(leg, sources, *args):
        if sources.get('G3', {}).get('run_dir') == 'corrected-G3':
            raise ValueError('native completion refused')
        return original(leg, sources, *args)

    monkeypatch.setattr(B, '_verdict_maps_from', refusal)
    with pytest.raises(ValueError, match='native completion refused'):
        with chained(refs):
            case['run']()
    assert B._verdict_maps_from is refusal


def test_internal_dispatch_cannot_read_an_unapproved_subset(case):
    plan = case['plan']
    consumer = CHAIN._consumer_for(plan, case['original'], case['original'])
    args = (plan['producer_identity'], plan['required_population'],
            {'pins': plan['g1_identity']}, {})
    assert consumer('P1', plan['base_sources'], *args) == case['run']()
    with pytest.raises(ValueError, match='outside its approved plan'):
        consumer('P1', {'G2': {'run_dir': 'unknown'}}, *args)


@pytest.mark.parametrize('before,after', [
    ('return prior(leg, sources, producer, required, g1, memo)',
     'return native(leg, sources, producer, required, g1, memo)'),
    ('return native(leg, sources, producer, required, g1, memo)',
     'return prior(leg, sources, producer, required, g1, memo)'),
    ("scopes.enter_context(REV.scope(ref['path'], ref['sha256']))", 'None'),
])
def test_each_composition_mutation_is_detected(case, tmp_path, monkeypatch, before, after):
    test_two_required_corrections_preserve_both_results(case, tmp_path)
    source = Path(CHAIN.__file__).read_text()
    assert source.count(before) == 1
    mutant = types.ModuleType('mutated_chain')
    mutant.__file__ = CHAIN.__file__
    exec(compile(source.replace(before, after), mutant.__file__, 'exec'), mutant.__dict__)
    monkeypatch.setattr(sys.modules[__name__], 'CHAIN', mutant)
    with pytest.raises((AssertionError, ValueError)):
        test_two_required_corrections_preserve_both_results(case, tmp_path)
