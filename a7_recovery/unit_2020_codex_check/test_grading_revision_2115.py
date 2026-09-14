"""Revision-boundary tests. Test doubles are not native lifecycle proof."""
import copy
import json
import sys
import types
from pathlib import Path

import pytest

A7 = Path(__file__).resolve().parents[1]
for relative in ('grader_20260909/harness_g1v3', 'unit_2008/harness_g1v3',
                 'unit_2006/harness_g1v3', 'unit_2009/owner'):
    sys.path.insert(0, str(A7 / relative))

import a7_g1_build as G
import a7_g23_build as B
import a7_grading_revision_2115 as REV


@pytest.fixture
def case(monkeypatch, tmp_path):
    producer = {'run_dir': 'unfamiliar-producer', 'identity': 'producer-pin'}
    g1 = {'pins': {'root_sha256': 'g1-pin'}}
    population = {'G2': {'P1|source-A': [[2, 7], [5, 9]],
                         'P2|source-B': [[3, 4]]},
                  'G3': {'P1|source-A': [11, 12], 'P2|source-B': [8]}}

    def handle(name):
        return {'run_dir': name, 'root_sha256': name + '-root',
                'completion_sha256': name + '-completion'}

    base = {kind: handle('base-' + kind) for kind in population}
    correction = {kind: handle('corrected-' + kind) for kind in population}
    changed = {'G2': {'P1|source-A': [[2, 7]]},
               'G3': {'P1|source-A': [11]}}
    docs = {correction[k]['run_dir']: dict(
        {'task_kind': k, 'producer_identity': producer,
         'g1_identity': g1['pins'], 'population': changed[k],
         'input_correction_sha256': 'b' * 64},
        # a G3 correction candidate now also names the matched-pair inventory
        # its comparison records came from, and the consumer checks it against
        # the required G2 population (Core SEQ 2121)
        **({'matched_population': population['G2']} if k == 'G3' else {}))
        for k in population}
    answers = {
        'base-G2': {('source-A', 2): {'driver_state': True},
                    ('source-A', 5): {'driver_state': False}},
        'base-G3': {('source-A', 11): 'unsupported',
                    ('source-A', 12): 'duplicate'},
        'corrected-G2': {('source-A', 2): {'driver_state': False}},
        'corrected-G3': {('source-A', 11): 'key_miss'},
        'P2-base-G2': {('source-B', 3): {'driver_state': True}},
        'P2-base-G3': {('source-B', 8): 'duplicate'}}
    calls = []

    def original(leg, sources, got_producer, required, got_g1, memo):
        assert got_producer == producer and got_g1 == g1
        found = [{}, {}]
        for kind, src in sources.items():
            name = src['run_dir']
            assert src == (base[kind] if name.startswith('base-') else correction[kind])
            want = population[kind] if name.startswith('base-') else docs[name]['population']
            assert required[kind] == want
            calls.append((leg, kind, name))
            if name.startswith('corrected-'):
                memo[(kind, name, src['root_sha256'], src['completion_sha256'])] = (
                    copy.deepcopy(docs[name]), {'fixture': 'verified-completion'})
            value = answers.get(leg + '-' + name, answers[name] if leg == 'P1' else {})
            found[kind == 'G3'].update(copy.deepcopy(value))
        return tuple(found)

    monkeypatch.setattr(B, '_verdict_maps_from', original)
    plan = {'schema': 'a7-grading-revision/v1',
            'code_sha256': G._sha_file(REV.__file__),
            'producer_identity': producer, 'g1_identity': g1['pins'],
            'required_population': population, 'base_sources': base,
            'corrections': {k: {
                'source': correction[k], 'population': changed[k],
                'input_correction_sha256': 'b' * 64,
                'reason': 'independently verified changed grading input'}
                for k in population}}
    path = tmp_path / 'revision.json'

    def save():
        path.write_text(json.dumps(plan), encoding='utf-8')
        return str(path), G._sha_file(str(path))

    def run(leg='P1', sources=None, required=None):
        return B.official_verdict_maps(leg, base if sources is None else sources,
                                      producer, population if required is None else required, g1)

    return {'plan': plan, 'save': save, 'run': run, 'docs': docs,
            'answers': answers, 'calls': calls, 'original': original,
            'base': base, 'population': population}


def test_only_exact_approved_questions_are_replaced_through_existing_verifier(case):
    baseline = case['run']()
    assert baseline[0][('source-A', 2)]['driver_state'] is True
    before = copy.deepcopy(case['answers'])
    with REV.scope(*case['save']()):
        result = case['run']()
    assert result == ({('source-A', 2): {'driver_state': False},
                       ('source-A', 5): {'driver_state': False}},
                      {('source-A', 11): 'key_miss', ('source-A', 12): 'duplicate'})
    assert case['answers'] == before
    assert B._verdict_maps_from is case['original']
    assert case['run']() == baseline
    assert ('P1', 'G2', 'corrected-G2') in case['calls']
    assert ('P1', 'G3', 'corrected-G3') in case['calls']


def test_unresolved_replacement_removes_old_credit_and_preserves_other_questions(case):
    assert case['run']()[0][('source-A', 2)]
    case['answers']['corrected-G2'].clear()
    case['answers']['corrected-G3'].clear()
    with REV.scope(*case['save']()):
        meaning, extras = case['run']()
    assert ('source-A', 2) not in meaning
    assert ('source-A', 11) not in extras
    assert meaning == {('source-A', 5): {'driver_state': False}}
    assert extras == {('source-A', 12): 'duplicate'}


def test_partial_replacement_does_not_inherit_old_aspects_or_change_another_leg(case):
    expected_other_leg = case['run']('P2')
    case['answers']['corrected-G2'][('source-A', 2)] = {'growth_basis': True}
    with REV.scope(*case['save']()):
        assert case['run']()[0][('source-A', 2)] == {'growth_basis': True}
        assert case['run']('P2') == expected_other_leg


@pytest.mark.parametrize('field,value', [
    ('schema', 'old-schema'), ('code_sha256', '0' * 64),
    ('producer_identity', {'run_dir': 'other'}), ('g1_identity', {}),
    ('required_population', {}), ('base_sources', {}),
    ('corrections', {'G9': {}}), ('corrections', []),
])
def test_changed_plan_identity_refuses_with_a_valid_control(case, field, value):
    with REV.scope(*case['save']()):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False
    case['plan'][field] = value
    with pytest.raises(ValueError):
        with REV.scope(*case['save']()):
            case['run']()
    assert B._verdict_maps_from is case['original']


@pytest.mark.parametrize('population', [
    {}, {'P1|source-A': []}, {'P1|another-source': [[2, 7]]},
    {'P1|source-A': [[2, 9]]}, {'P1|source-A': [[2, 7], [2, 7]]},
    {'P1|source-A': [[True, 7]]}, {'P1|source-A': ['2,7']},
])
def test_wrong_or_duplicated_question_refuses_with_a_valid_control(case, population):
    with REV.scope(*case['save']()):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False
    case['plan']['corrections']['G2']['population'] = population
    case['docs']['corrected-G2']['population'] = population
    with pytest.raises(ValueError):
        with REV.scope(*case['save']()):
            case['run']()


@pytest.mark.parametrize('value', [None, '', 123, True, 'not-a-hash', 'z' * 64])
def test_input_version_must_be_an_actual_sha256_shape(case, value):
    with REV.scope(*case['save']()):
        assert case['run']()[1][('source-A', 11)] == 'key_miss'
    case['plan']['corrections']['G2']['input_correction_sha256'] = value
    case['docs']['corrected-G2']['input_correction_sha256'] = value
    with pytest.raises(ValueError):
        with REV.scope(*case['save']()):
            case['run']()


def test_changed_input_version_is_not_relabelled(case):
    with REV.scope(*case['save']()):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False
    case['docs']['corrected-G2']['input_correction_sha256'] = 'c' * 64
    with pytest.raises(ValueError, match='input version'):
        with REV.scope(*case['save']()):
            case['run']()


def test_wrong_plan_pin_or_in_scope_edit_refuses_and_restores(case):
    path, pin = case['save']()
    with pytest.raises(ValueError, match='unapproved grading revision plan'):
        with REV.scope(path, '0' * 64):
            case['run']()
    with REV.scope(path, pin):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False
    with pytest.raises(ValueError, match='unapproved grading revision plan'):
        with REV.scope(path, pin):
            case['plan']['corrections'] = {}
            case['save']()
            case['run']()
    assert B._verdict_maps_from is case['original']


def test_existing_verifier_refusal_propagates_without_fallback(case, monkeypatch):
    original = case['original']
    with REV.scope(*case['save']()):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False

    def refused(leg, sources, *args):
        if any(s['run_dir'].startswith('corrected-') for s in sources.values()):
            raise ValueError('native completion does not rederive')
        return original(leg, sources, *args)

    monkeypatch.setattr(B, '_verdict_maps_from', refused)
    with pytest.raises(ValueError, match='does not rederive'):
        with REV.scope(*case['save']()):
            case['run']()
    assert B._verdict_maps_from is refused


def test_an_unrequested_judgment_refuses_instead_of_replacing_another_fact(case):
    with REV.scope(*case['save']()):
        assert case['run']()[0][('source-A', 2)]['driver_state'] is False
    case['answers']['corrected-G2'][('source-A', 5)] = {'driver_state': True}
    with pytest.raises(ValueError, match='unrequested judgment'):
        with REV.scope(*case['save']()):
            case['run']()


def test_no_correction_is_exactly_the_original_verified_result(case):
    baseline = case['run']()
    case['plan']['corrections'] = {}
    with REV.scope(*case['save']()):
        assert case['run']() == baseline


@pytest.mark.parametrize('old,new,check_name', [
    ('result[index].pop(key, None)', 'None',
     'test_unresolved_replacement_removes_old_credit_and_preserves_other_questions'),
    ('if G._plain(actual) != G._plain(expected):', 'if False:',
     'test_changed_input_version_is_not_relabelled'),
    ('if set(changed[index]) - targets or changed[1 - index]:', 'if False:',
     'test_an_unrequested_judgment_refuses_instead_of_replacing_another_fact'),
    ('list(copy.deepcopy(original(leg, sources, producer, required, g1, memo)))',
     '[{}, {}]', 'test_only_exact_approved_questions_are_replaced_through_existing_verifier'),
])
def test_revision_mutations_are_killed_with_real_positive_controls(case, monkeypatch,
                                                                  old, new, check_name):
    check = globals()[check_name]
    # The controls and mutants must start with the same fixture bytes/state.
    frozen = {name: copy.deepcopy(case[name]) for name in ('plan', 'docs', 'answers')}
    check(case)
    for name, value in frozen.items():
        case[name].clear()
        case[name].update(value)
    text = Path(REV.__file__).read_text()
    assert text.count(old) == 1
    mutant = types.ModuleType('mutated_grading_revision')
    mutant.__file__ = REV.__file__
    exec(compile(text.replace(old, new), mutant.__file__, 'exec'), mutant.__dict__)
    monkeypatch.setattr(sys.modules[__name__], 'REV', mutant)
    with pytest.raises((AssertionError, pytest.fail.Exception)):
        check(case)
