"""Source-rule regression, not a test of a model's eventual judgment."""
import copy
import hashlib

import pytest

import test_grading_input_correction_2114 as ENV

import a7_grading_contract_2168 as SUBJECT
source = ENV.source


def body(prompt):
    return prompt.split('[EVENT]\n', 1)[1]


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_action_empty_population_has_its_own_declared_meaning(source, kind):
    rules = SUBJECT.meaning_rules() if kind == 'G2' else SUBJECT.extras_rules()
    flat = ' '.join(rules.split())
    # FINAL_DESIGN 5.2: omitted slice = whole-company for the three non-action
    # lanes; for actions it means no-applicable-part. No company examples.
    assert 'For an action, empty means no applicable part' in flat
    assert '   empty only for the whole company.' not in rules


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_primary_baseline_uses_headline_before_prior_year_tiebreak(source, kind):
    rules = SUBJECT.meaning_rules() if kind == 'G2' else SUBJECT.extras_rules()
    flat = ' '.join(rules.split())
    # FINAL_DESIGN 7.1 / DU-15: headline first, prior-year only as tiebreak.
    assert "Keep the source's headline comparison" in flat
    assert 'use prior year before sequential only to break a tie' in flat


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_single_and_batch_change_rules_only_not_the_evidence(source, kind):
    raw, run, inputs, fact = source
    before = copy.deepcopy(fact)
    args = ('P1', raw['source_id'], [(0, 0)], [fact], [fact], run)
    if kind == 'G2':
        previous = ENV.SUBJECT.meaning_packet(*args, inputs=inputs)
        current = SUBJECT.meaning_packet(*args, inputs=inputs)
    else:
        args = ('P1', raw['source_id'], [0], [fact], [(0, fact)], run)
        kw = dict(inputs=inputs, matched_pairs={'P1|' + raw['source_id']: []})
        previous = ENV.SUBJECT.extras_packet(*args, **kw)
        current = SUBJECT.extras_packet(*args, **kw)
    assert fact == before
    assert body(current['prompt']) == body(previous['prompt'])
    assert current['question_ids'] == previous['question_ids']
    assert current['event_context'] == previous['event_context']
    assert current['prompt_sha256'] == hashlib.sha256(current['prompt'].encode()).hexdigest()
    earlier = ENV.SUBJECT.batch_packet(kind, [previous])
    batch = SUBJECT.batch_packet(kind, [current])
    assert body(batch['prompt']) == body(earlier['prompt'])
    assert batch['question_ids'] == earlier['question_ids']
    assert batch['source_ids'] == earlier['source_ids']
    assert current['prompt'] != previous['prompt']
    assert current['input_correction_sha256'] != previous['input_correction_sha256']
    assert batch['input_correction_sha256'] == current['input_correction_sha256']


@pytest.mark.parametrize('kind', ['G2', 'G3'])
@pytest.mark.parametrize('changed', ['version', 'digest', 'rules', 'historical'])
def test_wrong_packet_binding_refuses_with_a_valid_control(source, kind, changed):
    raw, run, inputs, fact = source
    if kind == 'G2':
        args = ('P2', raw['source_id'], [(0, 0)], [fact], [fact], run)
        kw = dict(inputs=inputs)
        build, old_build = SUBJECT.meaning_packet, ENV.SUBJECT.meaning_packet
    else:
        args = ('P2', raw['source_id'], [0], [fact], [(0, fact)], run)
        kw = dict(inputs=inputs, matched_pairs={'P2|' + raw['source_id']: []})
        build, old_build = SUBJECT.extras_packet, ENV.SUBJECT.extras_packet
    packet = build(*args, **kw)
    before = copy.deepcopy(packet)
    assert SUBJECT.batch_packet(kind, [packet])['question_ids'] == packet['question_ids']
    bad = copy.deepcopy(packet)
    if changed == 'version':
        bad['input_correction_sha256'] = '0' * 64
    elif changed == 'digest':
        bad['prompt_sha256'] = '0' * 64
    elif changed == 'rules':
        bad['prompt'] = 'Other instructions\n' + bad['prompt']
        bad['prompt_sha256'] = ENV.G._sha(bad['prompt'])
    else:
        bad = old_build(*args, **kw)
    with pytest.raises(ValueError, match='rules and version'):
        SUBJECT.batch_packet(kind, [bad])
    assert packet == before
    assert SUBJECT.batch_packet(kind, [packet])['question_ids'] == packet['question_ids']


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_existing_duplicate_question_guard_is_not_bypassed(source, kind):
    raw, run, inputs, fact = source
    if kind == 'G2':
        packet = SUBJECT.meaning_packet('P1', raw['source_id'], [(0, 0)],
                                         [fact], [fact], run, inputs=inputs)
    else:
        packet = SUBJECT.extras_packet('P1', raw['source_id'], [0], [fact],
                                        [(0, fact)], run, inputs=inputs,
                                        matched_pairs={'P1|' + raw['source_id']: []})
    assert SUBJECT.batch_packet(kind, [packet])['question_ids'] == packet['question_ids']
    with pytest.raises(ValueError, match='repeats a question'):
        SUBJECT.batch_packet(kind, [packet, packet])


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_changed_historical_owner_refuses_without_changing_it(source, monkeypatch, kind):
    before = ENV.G._sha_file(ENV.SUBJECT.__file__)
    assert len(SUBJECT._rules(kind)) == 2
    monkeypatch.setattr(SUBJECT, 'BASE_SHA256', '0' * 64)
    with pytest.raises(ValueError, match='frozen base'):
        SUBJECT._rules(kind)
    assert ENV.G._sha_file(ENV.SUBJECT.__file__) == before


@pytest.mark.parametrize('kind', ['G2', 'G3'])
@pytest.mark.parametrize('index', [0, 1])
def test_each_actual_rule_removal_is_detected(source, monkeypatch, kind, index):
    check = (test_action_empty_population_has_its_own_declared_meaning,
             test_primary_baseline_uses_headline_before_prior_year_tiebreak)[index]
    check(source, kind)
    original = SUBJECT.CORRECTIONS
    monkeypatch.setattr(SUBJECT, 'CORRECTIONS', original[:index] + original[index + 1:])
    with pytest.raises(AssertionError):
        check(source, kind)


def test_unknown_grading_kind_refuses_with_valid_control(source):
    assert SUBJECT.meaning_rules() and SUBJECT.extras_rules()
    with pytest.raises(ValueError, match='G2 or G3'):
        SUBJECT.batch_packet('not-a-kind', [])
