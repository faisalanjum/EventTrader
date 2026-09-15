"""The exact evidence table behind REVIEW_2174.md. Read-only, derived.

Ten questions: root's three source dispositions and the seven newly collected
G3 extras. Every identity, field comparison and trace reason is measured from
the pinned score, key, candidate, served prompts and my own 2168 trace. The
only judgement is the `core_finding` line on each row.
"""
import collections, glob, hashlib, io, json, os, sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
K = os.path.join(A7, 'unit_2020_codex_check')
G3RUN = os.path.join(A7, 'unit_2173_grading/G3/run')
TRACE = os.path.join(A7, 'unit_2168_review/recall_miss_trace_185.json')
SCORE = (os.path.join(K, 'codex_corrected_score2166_a/A7_CORRECTED_SCORE.json'),
         '656c18bd363ac3941a737d4d3ae55b101f303c209727ed261325a42e9664f08a')
SELECTION = (os.path.join(K, 'CHANGED_GRADING_SELECTION_2171.json'),
             '1107680379634723be19afe255bd19864ebdf06e0b65eaeb199ee871d8998710')
ADDENDUM = (os.path.join(K, 'SOURCE_CAUSE_ADDENDUM_2174.md'),
            '882d87159f7f005899ef3b3093fa38ffbe082b690c9a2f6e2bb911a8723ec0e3')

#: MY finding per question. Everything else on the row is measured.
FINDING = {
    'M8624b63494238990': 'grading limitation: the produced fact equals the approved gold fact in every produced field, so no source-supported defect stands behind the negative',
    'Ma31af1665347b9ec': 'producer defect on name/population (NAME-10: a sales channel goes to the slice); the numeric nulls are the SAME open representation question as Md2061d63bedc8f75, mirrored, not merely lawful caution',
    'Md2061d63bedc8f75': 'rule ambiguity: FINAL_DESIGN fixes what value_text may hold and what a floor means, but never says whether a vague band must stay qualitative',
    'X24756096af610d6d': 'existing key fact represented differently (key g2 restaurant_closure_impairment, same type/state/value/unit); not a key omission',
    'X6eea70137b9a2e63': 'existing key fact represented differently (key g6 net_debt, same type/state/value/unit/baseline); not a key omission',
    'X73357410ba2d97a2': 'existing key fact represented differently (key g6 net_debt) AND a second emission of X6eea70137b9a2e63 differing only in period_start_date',
    'X99d7bc16850a9dde': 'existing key fact represented differently (key g6 aircraft_purchase_option, same type/state/ceiling/unit); not a key omission',
    'Xe10aa94910fc4e7a': 'existing key fact represented differently (key g6) AND a second emission of X99d7bc16850a9dde differing only in driver_name',
    'Xa0f9de09f3c55112': 'existing key fact represented differently (key g0 asset_impairment, same type/state/value/unit); it also empties the key population and adds a prior-year comparison to a table dash',
    'X56415b76439cd6be': 'wrong/unsupported produced record: 85 percent is the share of survey RESPONDENTS, stored as the level of travel_spend, and an outside survey expectation about a future quarter is not the company own measured metric',
}
DISPOSITION = {
    'M8624b63494238990': ('UNION', '0000764478-25-000057', 3, 8),
    'Ma31af1665347b9ec': ('UNION', '0001041061-26-000003', 3, 3),
    'Md2061d63bedc8f75': ('P1', 'AAL_2026-04-23T08.30', 7, 7),
}


def pinned(ref):
    raw = io.open(ref[0], 'rb').read()
    if hashlib.sha256(raw).hexdigest() != ref[1]:
        raise ValueError('%s is not at its pin' % os.path.basename(ref[0]))
    return raw


def num(v):
    return (v or {}).get('value')


def view(fact):
    it = fact['item']
    return collections.OrderedDict([
        ('fact_type', fact['fact_type']), ('driver_name', it.get('driver_name')),
        ('driver_state', it.get('driver_state')),
        ('level_low', num(it.get('level_low'))), ('level_high', num(it.get('level_high'))),
        ('level_shape_hint', it.get('level_shape_hint')), ('level_unit', it.get('level_unit')),
        ('comparison_low', num(it.get('comparison_low'))),
        ('comparison_baseline', it.get('comparison_baseline')),
        ('value_text', it.get('value_text')), ('slice_parts', it.get('slice_parts')),
        ('fiscal_year', it.get('fiscal_year')), ('fiscal_quarter', it.get('fiscal_quarter')),
        ('per_x', fact.get('per_x')), ('part_ref', fact.get('part_ref'))])


def recursive_diff(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(path + '/' + k + ' :only in the second')
            elif k not in b:
                out.append(path + '/' + k + ' :only in the first')
            else:
                out += recursive_diff(a[k], b[k], path + '/' + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append('%s :length %d vs %d' % (path, len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out += recursive_diff(x, y, '%s[%d]' % (path, i))
    elif a != b:
        out.append('%s : %r vs %r' % (path, a, b))
    return out


def served_g3():
    """Each collected G3 question's own served event, from the run's scripts."""
    out = {}
    for path in sorted(glob.glob(os.path.join(G3RUN, 'grade_batch.*.js'))):
        text = io.open(path, encoding='utf-8').read()
        at = text.index('const BOUND =')
        bound, _ = json.JSONDecoder().raw_decode(text[at + len('const BOUND ='):].lstrip())
        for prompt in bound['prompts']:
            body = prompt[prompt.index('[EVENT]\n') + len('[EVENT]\n'):]
            for event in json.JSONDecoder().raw_decode(body)[0]['events']:
                out.setdefault(event['questions'][0]['question_id'], event)
    return out


def main(out_path):
    score = json.loads(pinned(SCORE))
    selection = json.loads(pinned(SELECTION))
    pinned(ADDENDUM)
    key, cases = score['key'], score['cases']
    trace = json.load(io.open(TRACE, encoding='utf-8'))
    trace_rows = trace if isinstance(trace, list) else trace['rows']
    by_gold = {(r['leg'], r['sid'], r['gold_idx']): r for r in trace_rows
               if r.get('gold_idx') is not None}
    events = served_g3()
    rows = collections.OrderedDict()

    for qid, (leg, sid, gi, pi) in sorted(DISPOSITION.items()):
        gold = key[sid][gi]
        produced = cases[leg]['answers'][sid]['facts'][pi]
        rows[qid] = collections.OrderedDict([
            ('part', 'root source disposition'), ('leg', leg), ('source_id', sid),
            ('gold_idx', gi), ('produced_idx', pi),
            ('gold', view(gold)), ('produced', view(produced)),
            ('recursive_difference', recursive_diff(gold, produced)),
            ('gold_ambiguity_note', gold.get('ambiguity_note')),
            ('core_finding', FINDING[qid])])

    idx = {}
    for group, produced_idxs in selection['populations']['G3'].items():
        leg, sid = group.split('|', 1)
        for i in produced_idxs:
            idx['X' + hashlib.sha256(
                ('G3|%s|%s|%d' % (leg, sid, i)).encode()).hexdigest()[:16]] = (leg, sid, i)
    if sorted(idx) != selection['question_ids']['G3']:
        raise ValueError('the regenerated G3 ids are not the selection')

    for qid in sorted(idx):
        leg, sid, pi = idx[qid]
        produced = cases[leg]['answers'][sid]['facts'][pi]
        event = events[qid]
        cards = {c['quote']: c['reference_name']
                 for c in (event.get('reference_cards') or [])}
        # Which approved key fact, if any, states the same claim: same fact
        # type, state and level numbers. The NAME is deliberately excluded -
        # that is the very field these records differ on.
        same = [i for i, g in enumerate(key[sid])
                if g['fact_type'] == produced['fact_type']
                and g['item'].get('driver_state') == produced['item'].get('driver_state')
                and num(g['item'].get('level_low')) == num(produced['item'].get('level_low'))
                and num(g['item'].get('level_high')) == num(produced['item'].get('level_high'))]
        row = collections.OrderedDict([
            ('part', 'newly collected G3 extra'), ('leg', leg), ('source_id', sid),
            ('produced_idx', pi), ('produced', view(produced)),
            ('approved_key_facts_stating_the_same_claim', same),
            ('its_card_was_served', [key[sid][i]['item'].get('quote') in cards for i in same]),
            ('card_reference_name', [cards.get(key[sid][i]['item'].get('quote')) for i in same]),
            ('served_reference_cards', len(cards)),
            ('served_other_records', len(event.get('other_records') or [])),
            ('core_finding', FINDING[qid])])
        for i in same:
            hit = by_gold.get((leg, sid, i))
            if hit:
                row.setdefault('matching_gold_is_a_recall_miss', {})[str(i)] = hit['reasons']
        rows[qid] = row

    doc = collections.OrderedDict([
        ('schema', 'a7-final-source-cause-check/2174'),
        ('scope', 'independent cause review; it overwrites no verdict, label, '
                  'key or score, and establishes no replacement grade'),
        ('counts', collections.OrderedDict([
            ('questions', len(rows)),
            ('root_dispositions', len(DISPOSITION)),
            ('newly_collected_g3', len(idx)),
            ('g3_establishing_a_fact_absent_from_the_key', 0),
        ])),
        ('questions', rows)])
    json.dump(doc, io.open(out_path, 'w', encoding='utf-8'), indent=1)
    print('questions', len(rows))
    for qid, row in rows.items():
        if row['part'].startswith('newly'):
            print(' ', qid, 'same-claim key facts', row['approved_key_facts_stating_the_same_claim'],
                  '| card served', row['its_card_was_served'],
                  '| gold is a recall miss', list(row.get('matching_gold_is_a_recall_miss', {})))


if __name__ == '__main__':
    main(sys.argv[1])
