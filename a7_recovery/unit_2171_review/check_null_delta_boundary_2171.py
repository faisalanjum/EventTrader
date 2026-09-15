"""Independently check the carried null-change task selection and its boundary.

Three things are proved here and none of them is taken from root's file:

  * the CLASS: which carried G2 tasks the corrected null/read-time sentence can
    reach at all, re-derived from the saved records' own shapes;
  * the BOUNDARY: that no other carried task can be reached, because the
    sentence's precondition is a derivable change and derivation needs a
    comparison operand those records do not have;
  * the SPLIT: for each distinct record, whether the source states a numeric
    delta OF THAT CLAIM, which is what makes the old and corrected texts differ.

FINAL_DESIGN line 239 owns the rule twice over: `Leave change_value=null when
it could merely be derived from a closed shape (derive at read)` and `it is
stored ONLY when the source states a non-derivable delta AND its arithmetic
sign is determinable`. So a STATED but DERIVABLE delta belongs in neither text's
change_value - which is exactly why a stated delta beside two closed operands
is the case whose task moved.

    python3 -B check_null_delta_boundary_2171.py <out.json>
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
K = os.path.join(A7, 'unit_2020_codex_check')
REVIEW_2169 = os.path.join(A7, 'unit_2169_review',
                           'derive_affected_population_2169.py')
REVIEW_2169_SHA256 = ('2d1902a370163f2198e5112005a0570c'
                      '489292660f0cc107814a9687e7ecc9a1')
ROOT_REVIEW = os.path.join(K, 'CARRIED_NULL_DELTA_REVIEW_2170.json')
ROOT_REVIEW_SHA256 = ('bb8d13ad1f63b2540755045910b918ec'
                      '4662c5f870f915becaf7bb5f51131240')
SELECTION = os.path.join(K, 'G2_REUSE_SELECTION_2159.json')
SELECTION_SHA256 = ('9603626914cdddd79461ad8150d4a054'
                    'dbde5776cb6af4f58057b21dd48228c2')

#: The already accepted two-clause population, so the overlap is measured and
#: not assumed.
ACCEPTED_FIFTEEN = (
    'M02d957fa99800507', 'M24065e66c77fea00', 'M43e87509e5cc819b',
    'Mabd80961830fa09a', 'Mc17055ff4a7a52dd', 'Mc6c32dee91400e91',
    'Mde7d5e39712de0c7', 'Mf91a92c59065852f', 'X24756096af610d6d',
    'X56415b76439cd6be', 'X6eea70137b9a2e63', 'X73357410ba2d97a2',
    'X99d7bc16850a9dde', 'Xa0f9de09f3c55112', 'Xe10aa94910fc4e7a')

#: MY reading of each distinct record in the class, keyed by the exact record
#: (source id + sha256 of the saved fact). True means the source states a
#: numeric delta OF THIS CLAIM, so the old text could demand the field the
#: corrected text forbids; False means it states none, so null was already
#: lawful under both. The evidence is the exact fragment the reading rests on.
DELTA_STATED = {
    '0000006201-26-000031|39151b09': (True, 'Passenger revenue per ASM (cents) 18.57 17.41 6.6 %'),  # 00 passenger_revenue_per_available_seat_mile
    '0000006201-26-000032|35bcf47a': (True, 'an increase of 5.2% from 14.54 cents'),  # 01 operating_cost_per_available_seat_mile
    '0000092380-26-000044|ee045a35': (True, 'Freight 44 41 7.3'),  # 02 revenue
    '0000764478-25-000057|3eef3b9d': (False, 'four stated LEVELS, 31.8 / 31.4 / 32.1 / 31.2, and no delta for this claim'),  # 03 revenue
    '0000764478-25-000057|284498e0': (False, 'four stated LEVELS and no delta for this claim'),  # 04 revenue
    '0000898173-26-000006|4ddcfaa0': (True, 'increased 10% to $2.97 ... versus $2.71'),  # 05 earnings_per_share
    '0000940944-25-000038|908bb8e8': (True, 'LongHorn Steakhouse 19.3% 18.4% 90 BP'),  # 06 segment_profit_margin
    '0000940944-26-000009|f6c63934': (True, 'Earnings from continuing operations $ 2.68 $ 2.74 (2.2)%'),  # 07 continuing_operations_earnings_per_share
    '0001041061-26-000084|a9f552ee': (True, 'a 6% increase from the quarterly dividend of $0.71 per share'),  # 08 dividend_per_share
    '0001058090-26-000007|f1bfe281': (False, 'a decrease from 24.8% - a direction, with no numeric delta'),  # 09 restaurant_level_operating_margin
    '0001104659-25-105631|6d11a17a': (True, 'increased 16.1% to $83.5 million ... compared to $71.9 million'),  # 10 sales
    '0001104659-26-027061|79953c4c': (False, 'decreased to 38.1% compared to 38.2% - two levels, no stated delta'),  # 11 gross_margin
    '0001104659-26-032757|3178c772': (False, 'approximately 85% ... approximately 86% - two approximate levels, no stated delta'),  # 12 sales_mix
    '0000006201-26-000031|9bfd4ed2': (True, 'Regional (4) 32,500 30,700 5.9 %'),  # 13 full_time_equivalent_employees
    '0000006201-26-000032|3bf2a370': (True, 'an increase of 5.2% from 14.54 cents'),  # 14 operating_cost_per_available_seat_mile
    '0000764478-25-000057|caaee9e8': (False, 'the impairment row states 171 and a dash; the table % change rows belong to revenue and comparable sales, not to this claim'),  # 15 goodwill_and_intangible_asset_impairment
    '0000764478-25-000057|69cfb96d': (False, 'four stated LEVELS and no delta for this claim'),  # 16 revenue_mix
    '0000764478-25-000057|bb85b384': (False, 'four stated LEVELS and no delta for this claim'),  # 17 revenue_mix
    '0000898173-26-000006|63487d31': (True, 'increased 10% to $2.97 ... versus $2.71'),  # 18 earnings_per_share
    '0000940944-26-000009|6b9131d7': (True, 'Fine Dining $ 402.0 $ 385.3 4.3 %'),  # 19 sales
    '0001104659-26-027061|abd93613': (False, 'decreased to 38.1% compared to 38.2% - two levels, no stated delta'),  # 20 gross_margin
    '0001104659-26-032757|774ec72e': (False, 'approximately 85% ... approximately 86% - two approximate levels, no stated delta'),  # 21 sales_mix
}


def _sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _pinned(path, expected):
    raw = io.open(path, 'rb').read()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('%s is not at its pin' % os.path.basename(path))
    return raw


def _closed(value):
    return isinstance(value, dict) and value.get('value') is not None


def shape(fact, prefix):
    """The saved record's own shape, in the vocabulary FINAL_DESIGN uses."""
    low, high = fact['item'].get(prefix + '_low'), fact['item'].get(prefix + '_high')
    if not _closed(low) and not _closed(high):
        return 'none'
    if _closed(low) and _closed(high):
        return 'point' if str(low['value']) == str(high['value']) else 'range'
    return 'floor' if _closed(low) else 'ceiling'


def record_key(source_id, fact):
    return '%s|%s' % (source_id, _sha(json.dumps(fact, sort_keys=True))[:8])


def main(out):
    source = io.open(REVIEW_2169, encoding='utf-8').read()
    if _sha(source) != REVIEW_2169_SHA256:
        raise ValueError('the published 2169 derivation is not at its pin')
    ns = {'__name__': 'review_2169', '__file__': REVIEW_2169}
    exec(compile(source, REVIEW_2169, 'exec'), ns)
    questions = {row['question_id']: row for row in ns['build']()
                 if row['kind'] == 'G2'}
    selection = json.loads(_pinned(SELECTION, SELECTION_SHA256))
    root = json.loads(_pinned(ROOT_REVIEW, ROOT_REVIEW_SHA256))
    carried = {row['question_id'] for row in selection['rows']
               if row['decision'] == 'carry'}
    corrected = {row['question_id'] for row in selection['rows']
                 if row['decision'] == 'correct'}

    # THE CLASS, re-derived from the saved records rather than read off root's
    # file: a closed point level AND a closed point comparison AND no change.
    census = collections.Counter()
    in_class, outside = set(), set()
    for qid in carried:
        fact = questions[qid]['produced']
        row = (shape(fact, 'level'), shape(fact, 'comparison'),
               fact['item'].get('change_value') is not None)
        census[row] += 1
        (in_class if row == ('point', 'point', False) else outside).add(qid)

    # THE BOUNDARY. FINAL_DESIGN line 239 derives a change at read as
    # level_low - comparison_low, so the sentence cannot reach a record that
    # stores no comparison operand at all. This asserts that, rather than
    # asserting the count.
    reachable_outside = sorted(
        qid for qid in outside
        if shape(questions[qid]['produced'], 'comparison') != 'none')
    stored_derivable = sorted(
        qid for qid in carried
        if shape(questions[qid]['produced'], 'level') == 'point'
        and shape(questions[qid]['produced'], 'comparison') == 'point'
        and questions[qid]['produced']['item'].get('change_value') is not None)

    # THE SPLIT, from my own reading of each distinct record.
    root_groups = {}
    for group in root['groups']:
        key = record_key(group['sid'], group['fact'])
        if key in root_groups:
            raise ValueError('two root groups share one record: %s' % key)
        root_groups[key] = group
    if set(root_groups) != set(DELTA_STATED):
        raise ValueError('my reading and the reviewed records do not coincide')

    rows, disagreements = collections.OrderedDict(), []
    for key, group in sorted(root_groups.items()):
        stated, evidence = DELTA_STATED[key]
        mine = 'changed_task' if stated else 'unchanged_task'
        theirs = group['decision']
        if mine != theirs:
            disagreements.append(key)
        for identity in group['identities']:
            qid = identity['q']
            row = questions[qid]
            if (row['leg'], row['gold_idx'], row['produced_idx']) != (
                    identity['leg'], identity['g'], identity['i']):
                raise ValueError('a reviewed identity does not bind: %s' % qid)
            if json.dumps(row['produced'], sort_keys=True) != json.dumps(
                    group['fact'], sort_keys=True):
                raise ValueError('a reviewed fact is not the saved record: %s' % qid)
            rows[qid] = collections.OrderedDict([
                ('leg', row['leg']), ('source_id', row['source_id']),
                ('gold_idx', row['gold_idx']), ('produced_idx', row['produced_idx']),
                ('record', key), ('driver_name', row['produced']['item'].get('driver_name')),
                ('source_states_a_delta_of_this_claim', stated),
                ('evidence', evidence), ('core_decision', mine),
                ('root_decision', theirs), ('agrees', mine == theirs)])
    if set(rows) != in_class:
        raise ValueError('the reviewed identities are not exactly the class')

    # Adjacent sentences of the SAME corrected renderer, so a neighbouring
    # omission side cannot hide behind this one.
    guidance_with_change = sorted(
        qid for qid in carried
        if questions[qid]['produced']['fact_type'] == 'guidance'
        and questions[qid]['produced']['item'].get('change_value') is not None)
    missing_state = sorted(qid for qid in carried
                           if not questions[qid]['produced']['item'].get('driver_state'))
    unit_without_value = sorted(
        qid for qid in carried
        if questions[qid]['produced']['item'].get('change_unit')
        and questions[qid]['produced']['item'].get('change_value') is None)

    changed = {qid for qid, row in rows.items()
               if row['core_decision'] == 'changed_task'}

    # The prior aspect verdicts of the class, so it is visible whether this
    # selection reopens questions that currently score well or badly. A
    # selection that only reopened negatives would be score shopping.
    score = json.loads(_pinned(
        os.path.join(K, 'codex_corrected_score2166_a/A7_CORRECTED_SCORE.json'),
        '656c18bd363ac3941a737d4d3ae55b101f303c209727ed261325a42e9664f08a'))
    verdicts = {}
    for leg, case in score['cases'].items():
        for meaning in case['meanings']:
            verdicts[(leg, meaning['key'][0], meaning['key'][1])] = meaning['value']
    mix = collections.Counter()
    for qid, row in rows.items():
        aspects = verdicts[(row['leg'], row['source_id'], row['gold_idx'])]
        label = ('has_a_false_aspect' if any(v is False for v in aspects.values())
                 else ('all_true' if all(v is True for v in aspects.values())
                       else 'has_a_null_aspect'))
        mix[(row['core_decision'], label)] += 1
        rows[qid]['prior_aspects'] = label
    accepted = set(ACCEPTED_FIFTEEN)
    json.dump(collections.OrderedDict([
        ('schema', 'a7-carried-null-delta-boundary/2171'),
        ('counts', collections.OrderedDict([
            ('carried_g2_questions', len(carried)),
            ('in_class', len(in_class)),
            ('distinct_records_in_class', len(root_groups)),
            ('core_changed_questions', len(changed)),
            ('core_unchanged_questions', len(rows) - len(changed)),
            ('root_changed_questions', len(root['additional_question_ids'])),
            ('disagreements_with_root', len(disagreements)),
            ('outside_the_class', len(outside)),
            ('outside_with_any_comparison_operand', len(reachable_outside)),
            ('carried_storing_a_derivable_change', len(stored_derivable)),
            ('carried_guidance_storing_a_change', len(guidance_with_change)),
            ('carried_missing_driver_state', len(missing_state)),
            ('carried_change_unit_without_value', len(unit_without_value)),
            ('change_unit_without_value_inside_the_class',
             len(set(unit_without_value) & in_class)),
            ('overlap_with_the_accepted_fifteen', len(changed & accepted)),
            ('class_overlap_with_the_accepted_fifteen', len(in_class & accepted)),
            ('combined_distinct_questions', len(changed | accepted)),
            ('changed_inside_the_corrected_eighty_two', len(changed & corrected)),
        ])),
        ('prior_verdict_mix_of_the_class',
         {'%s|%s' % k: v for k, v in sorted(mix.items())}),
        ('shape_census_of_the_carried_population',
         {'level=%s,comparison=%s,change_stored=%s' % k: v
          for k, v in sorted(census.items(), key=lambda x: (-x[1], str(x[0])))}),
        ('core_additional_question_ids', sorted(changed)),
        ('class_overlap_identities', sorted(in_class & accepted)),
        ('disagreements_with_root', disagreements),
        ('change_unit_without_value_identities', unit_without_value),
        ('questions', rows),
    ]), io.open(out, 'w', encoding='utf-8'), indent=1)
    print('carried', len(carried), 'in class', len(in_class),
          'changed', len(changed), 'disagreements', len(disagreements))
    print('outside the class', len(outside),
          'of which any comparison operand', len(reachable_outside))
    print('overlap with the accepted fifteen', len(changed & accepted),
          '| combined', len(changed | accepted))


if __name__ == '__main__':
    main(sys.argv[1])
