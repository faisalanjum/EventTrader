# -*- coding: utf-8 -*-
"""Focused checks on the corrected-G3 caller's OWN logic.

No model call, no native job, no original evidence. The unchanged owners are
not re-audited here: where a refusal belongs to an existing owner, the test
calls that owner directly so the caller is never credited with its work.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

A7 = Path(__file__).resolve().parents[1]
for relative in ('grader_20260909/harness_g1v3', 'unit_2008/harness_g1v3',
                 'unit_2006/harness_g1v3', 'unit_2020_codex_check',
                 'unit_2118_correction_native'):
    sys.path.insert(0, str(A7 / relative))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import a7_g1_build as G                       # noqa: E402
import a7_g23_build as B                      # noqa: E402
import a7_grading_input_correction_2114 as V  # noqa: E402
import a7_correction_candidate_2118 as PREP   # noqa: E402
import g3_checks_2159 as CHECK                # noqa: E402

LEG, SID = 'P1', 'fixture-source'
GROUP = '%s|%s' % (LEG, SID)
G3_POP = {GROUP: [0, 2]}
G2_POP = {GROUP: [[0, 0], [1, 1], [2, 2]]}
CONTEXT = {'event_date': '2026-01-01', 'menu': ['geography:north']}
CARDS = [{'quote': 'the source sentence', 'values': [Decimal('4.5')]}]


def display(leg, source_id, idx):
    assert (leg, source_id) == (LEG, SID)
    return {'row': idx, 'item': {'level_low': Decimal('%d.5' % idx)}}


def context_of(leg, source_id):
    return CONTEXT


def cards_of(leg, source_id):
    return CARDS


def render(blocks):
    """Through the SAME serializer the renderer uses, so the test exercises the
    JSON round trip the real prompts go through."""
    return 'RULES\n' + '\n' + G._pretty({'events': blocks}) + '\n'


def block(idx, comparators, cards=None, context=None, record=None):
    return {
        'event': 'E1',
        'event_context': CONTEXT if context is None else context,
        'reference_cards': CARDS if cards is None else cards,
        'other_records': [{'other': 'O%d' % (n + 1),
                           'produced_record': display(LEG, SID, i)}
                          for n, i in enumerate(comparators)],
        'questions': [{'question_id': B.extras_question_id(LEG, SID, idx),
                       'produced_record': display(LEG, SID, idx)
                       if record is None else record}],
    }


def package(blocks_by_batch):
    candidate = {'batch_rows': [{'batch_id': bid, 'question_ids': [
        q['questions'][0]['question_id'] for q in blocks]}
        for bid, blocks in sorted(blocks_by_batch.items())]}
    prompts = {bid: render(blocks) for bid, blocks in blocks_by_batch.items()}
    return candidate, prompts


def run(blocks_by_batch, g3=None, g2=None, ctx=context_of, cards=cards_of):
    candidate, prompts = package(blocks_by_batch)
    # an EMPTY inventory is a real case, so it must not fall back
    return CHECK.audit(candidate, prompts,
                       G3_POP if g3 is None else g3,
                       G2_POP if g2 is None else g2,
                       display, B.extras_question_id, ctx, cards)


def test_a_complete_package_places_every_question_once_with_its_matched_pool():
    rows, problems, empty = run({'G3-000': [block(0, [1, 2]), block(2, [0, 1])]})
    assert problems == [] and empty == []
    assert [r['asked_produced_idx'] for r in rows] == [0, 2]
    assert [r['comparator_idxs'] for r in rows] == [[1, 2], [0, 1]]
    assert [r['question_id'] for r in rows] == [
        B.extras_question_id(LEG, SID, 0), B.extras_question_id(LEG, SID, 2)]


def test_a_decimal_survives_the_render_and_is_not_a_difference():
    """The whole package above went through the renderer's own serializer, so
    this passing IS the Decimal equivalence proof, through audit."""
    _rows, problems, _e = run({'G3-000': [block(0, [1, 2]), block(2, [0, 1])]})
    assert problems == []


def test_a_changed_number_in_a_comparison_record_is_caught_through_audit():
    blocks = {'G3-000': [block(0, [1, 2]), block(2, [0, 1])]}
    moved = dict(display(LEG, SID, 1))
    moved['item'] = {'level_low': Decimal('1.6')}     # 1.5 -> 1.6
    blocks['G3-000'][0]['other_records'][0]['produced_record'] = moved
    _rows, problems, _e = run(blocks)
    assert len(problems) == 1 and "'item'" in problems[0]


def test_a_changed_number_in_the_asked_record_is_caught_through_audit():
    blocks = {'G3-000': [block(0, [1, 2], record={'row': 0, 'item': {
        'level_low': Decimal('0.6')}}), block(2, [0, 1])]}
    _rows, problems, _e = run(blocks)
    assert len(problems) == 1 and 'asked record' in problems[0]


def test_a_foreign_event_context_is_caught():
    _r, problems, _e = run({'G3-000': [block(0, [1, 2], context={'event_date': '2020-01-01'}),
                                       block(2, [0, 1])]})
    assert len(problems) == 1 and 'event context' in problems[0]


def test_foreign_reference_cards_are_caught():
    _r, problems, _e = run({'G3-000': [block(0, [1, 2], cards=[{'quote': 'other'}]),
                                       block(2, [0, 1])]})
    assert len(problems) == 1 and 'reference cards' in problems[0]


def test_absent_context_or_cards_are_caught_as_identity_not_presence():
    _r, problems, _e = run({'G3-000': [block(0, [1, 2], cards=[]),
                                       block(2, [0, 1], context={})]})
    assert len(problems) == 2
    assert any('reference cards' in p for p in problems)
    assert any('event context' in p for p in problems)


def test_an_event_with_no_matched_pair_is_reported_empty_not_refused():
    rows, problems, empty = run({'G3-000': [block(0, []), block(2, [])]},
                                g2={GROUP: []})
    assert problems == [] and empty == [GROUP]
    assert all(r['comparators_shown'] == 0 for r in rows)


def test_a_group_absent_from_the_comparator_inventory_is_still_covered():
    rows, problems, empty = run({'G3-000': [block(0, []), block(2, [])]}, g2={})
    assert problems == [] and empty == [GROUP] and len(rows) == 2


def test_showing_an_unmatched_record_is_a_problem():
    _rows, problems, _e = run({'G3-000': [block(0, [1, 2, 3]), block(2, [0, 1])]})
    assert len(problems) == 1 and 'comparison records' in problems[0]


def test_showing_the_asked_row_as_its_own_comparator_is_a_problem():
    _rows, problems, _e = run({'G3-000': [block(0, [0, 1, 2]), block(2, [0, 1])]})
    assert len(problems) == 1 and 'comparison records' in problems[0]


def test_a_skipped_question_is_a_problem():
    _rows, problems, _e = run({'G3-000': [block(0, [1, 2])]})
    assert any('never asked' in p for p in problems)


def test_a_repeated_question_is_a_problem():
    _rows, problems, _e = run({'G3-000': [block(0, [1, 2])],
                               'G3-001': [block(0, [1, 2]), block(2, [0, 1])]})
    assert any('more than once' in p for p in problems)


def test_a_missing_comparator_inventory_refuses_in_the_existing_preparer():
    with pytest.raises(ValueError) as bad:
        PREP.prepare('/tmp/unused-2159', 'G3', G3_POP, G3_POP, {}, {},
                     'producer', {'identity': 'x'}, {}, 'identity',
                     matched_pairs=None)
    assert 'matched-pair inventory' in str(bad.value)


def test_a_wrong_comparator_inventory_refuses_in_the_existing_owner():
    facts = [{'a': 0}, {'a': 1}, {'a': 2}]
    assert V.eligible_comparators(G2_POP, LEG, SID, facts) == [0, 1, 2]
    with pytest.raises(ValueError):
        V.eligible_comparators({GROUP: [[0, 9]]}, LEG, SID, facts)
    with pytest.raises(ValueError):
        V.eligible_comparators({GROUP: [[0, 1], [2, 1]]}, LEG, SID, facts)
    with pytest.raises(ValueError):
        V.eligible_comparators({}, LEG, SID, facts)


def test_the_inventory_view_makes_every_asked_group_explicit():
    assert V.matched_inventory({}, G3_POP) == {GROUP: []}
    assert V.matched_inventory(G2_POP, G3_POP) == {GROUP: [[0, 0], [1, 1], [2, 2]]}


def test_the_canonical_comparison_is_the_existing_owner():
    assert CHECK.canon is G._plain


def test_a_tuple_keyed_report_serializes_explicitly():
    report = {'resolutions': {(SID, 3): 'kept', (SID, 1): 'dropped'}, 'n': 2}
    plain = CHECK.plain_report(report)
    assert json.loads(json.dumps(plain)) == json.loads(json.dumps(plain))
    assert plain['resolutions'] == [[[SID, 1], 'dropped'], [[SID, 3], 'kept']]
    with pytest.raises(TypeError):
        CHECK.plain_report({'bad': {1, 2}})
