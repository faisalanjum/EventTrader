"""Prompt-contract completeness checks for observed A7 grading defects.

These assert what instructions are served, not a model's semantic accuracy.
The expected clauses come from FINAL_DESIGN 7.1 and the existing field owner.
No example answer, company name or desired judgment enters a prompt.
"""
import json

import pytest

from test_grading_input_correction_2114 import source, SUBJECT, OLD


def assembled_rules(source, kind):
    raw, run, inputs, fact = source
    if kind == 'G2':
        packet = SUBJECT.meaning_packet('P1', raw['source_id'], [(0, 0)],
                                        [fact], [fact], run, inputs=inputs)
    else:
        packet = SUBJECT.extras_packet(
            'P1', raw['source_id'], [0], [fact], [(0, fact)], run,
            inputs=inputs,
            # a G3 packet now names the matched-pair inventory its
            # comparison records come from (Core SEQ 2121)
            matched_pairs={'P1|' + raw['source_id']: []})
    batch = SUBJECT.batch_packet(kind, [packet])
    rules, body = batch['prompt'].split('[EVENT]\n', 1)
    event = json.loads(body)['events'][0]
    assert event['questions'] == packet['questions']
    assert event['event_context'] == packet['event_context']
    assert fact['item']['quote'] in body
    return ' '.join(rules.split())


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_closed_operand_change_precedence_is_served(source, kind):
    rules = assembled_rules(source, kind)
    assert 'A change the source states differs from one merely' in OLD.meaning_contract()
    # Retain the authority's "merely": do not invent a blanket prohibition
    # on every source-stated change whenever two closed numbers coexist.
    assert ('Leave change_value null when it could merely be derived from a '
            'closed shape; derive at read time.') in rules


@pytest.mark.parametrize('kind', ['G2', 'G3'])
def test_percent_guidance_and_its_own_revision_use_distinct_slots(source, kind):
    rules = assembled_rules(source, kind)
    assert "against the company's own prior guide" in rules
    assert ('Percent-only guidance stores its growth basis in level_unit; only '
            "the guide's own revision size belongs in change_value.") in rules


def test_extras_gets_the_same_existing_field_contract_once(source):
    rules = assembled_rules(source, 'G3')
    contract = '[CONTRACT] - the conventions this judgment enforces'
    assert contract in OLD.meaning_contract()
    assert rules.count(contract) == 1
    assert 'STATED AND OMITTED' in rules and 'THE NUMBERS' in rules
    assert 'POPULATION AND MEASUREMENT' in rules
    assert 'SURPRISE PROOF AND FAVORABILITY' in rules


@pytest.mark.parametrize('clause,check_name', [
    ('Leave change_value null when it could merely be derived\n'
     '   from a closed shape; derive at read time.',
     'test_closed_operand_change_precedence_is_served'),
    ('Percent-only guidance stores its growth\n'
     "   basis in level_unit; only the guide's own revision size belongs in\n"
     '   change_value.',
     'test_percent_guidance_and_its_own_revision_use_distinct_slots'),
])
def test_a_missing_numeric_rule_is_detected_on_both_paths(source, monkeypatch,
                                                         clause, check_name):
    check = globals()[check_name]
    for kind in ('G2', 'G3'):
        check(source, kind)
    original = SUBJECT.meaning_contract
    assert original().count(clause) == 1
    monkeypatch.setattr(SUBJECT, 'meaning_contract',
                        lambda: original().replace(clause, '', 1))
    for kind in ('G2', 'G3'):
        with pytest.raises(AssertionError):
            check(source, kind)


def test_an_extras_contract_omission_is_detected(source, monkeypatch):
    test_extras_gets_the_same_existing_field_contract_once(source)
    original = SUBJECT.extras_rules
    contract = SUBJECT.meaning_contract()
    assert original().count(contract) == 1
    monkeypatch.setattr(SUBJECT, 'extras_rules',
                        lambda: original().replace(contract, '', 1))
    with pytest.raises(AssertionError):
        test_extras_gets_the_same_existing_field_contract_once(source)
