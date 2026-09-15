"""Derive the two clauses' exact affected/unaffected question population.

Read-only. Every identity comes from the candidate and from the prompt bytes
the graders were actually served; the only judgment is the per-source-claim
disposition table, which is attached to the CLAIM so it propagates by
measurement rather than by a question list.

    python3 -B derive_affected_population_2169.py <out.json>
"""
import collections
import glob
import hashlib
import io
import json
import os
import sys

A = ('/home/faisal/EventMarketDB-driver-recovery/a7_recovery/'
     'unit_2020_codex_check/')
ORIGINAL = A + 'codex_currentg232157_c'
CORRECTIVE = ('/home/faisal/EventMarketDB-driver-recovery/a7_recovery/'
              'unit_2161_execution')
sha = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()
cand = json.load(io.open(A + 'codex_currentg232157_c/a7_g23_candidate.json'))
score = json.load(io.open(A + 'codex_corrected_score2166_a/A7_CORRECTED_SCORE.json'))
KEY, CASES = score['key'], score['cases']


def build():
    rows = []
    for group, pairs in cand['g2_pairs'].items():
        leg, sid = group.split('|', 1)
        for gold_idx, produced_idx in pairs:
            rows.append({
                'kind': 'G2', 'leg': leg, 'source_id': sid,
                'gold_idx': gold_idx, 'produced_idx': produced_idx,
                'question_id': 'M' + sha('G2|%s|%s|%d|%d' % (
                    leg, sid, gold_idx, produced_idx))[:16],
                'gold': KEY[sid][gold_idx],
                'produced': CASES[leg]['answers'][sid]['facts'][produced_idx]})
    for group, idxs in cand['g3_idxs'].items():
        leg, sid = group.split('|', 1)
        pool = [row[1] for row in cand['g2_pairs'].get(group, [])]
        for produced_idx in idxs:
            rows.append({
                'kind': 'G3', 'leg': leg, 'source_id': sid,
                'gold_idx': None, 'produced_idx': produced_idx,
                'question_id': 'X' + sha('G3|%s|%s|%d' % (
                    leg, sid, produced_idx))[:16],
                'gold': None,
                'produced': CASES[leg]['answers'][sid]['facts'][produced_idx],
                'comparators': sorted(i for i in pool if i != produced_idx)})
    return rows


A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
ORIGINAL = os.path.join(A7, 'unit_2020_codex_check/codex_currentg232157_c')
CORRECTIVE = os.path.join(A7, 'unit_2161_execution')


def _events(prompt):
    body = prompt[prompt.index('[EVENT]\n') + len('[EVENT]\n'):]
    return json.JSONDecoder().raw_decode(body)[0]['events']


#: the two frozen clauses the new contract replaces. A rendering that does not
#: carry a clause cannot have its answer changed by that clause's correction.
CLAUSE = {
    'A': '   empty only for the whole company. A period is not a population.',
    'B': ('   streak do not create one. Keep the primary comparison; where prior '
          'year and\n   sequential are both stated, prior year is the baseline. '
          'Own-target')}


def _index(slots, event, source, prompt):
    served = {name: prompt.count(text) for name, text in CLAUSE.items()}
    for question in event['questions']:
        slots.setdefault(question['question_id'], []).append(
            {'question': question, 'event': event, 'source': source,
             'clauses': served})


def load():
    slots = {}
    for kind in ('G2', 'G3'):
        for path in sorted(glob.glob(os.path.join(ORIGINAL, kind, 'prompts/*.txt'))):
            prompt = io.open(path, encoding='utf-8').read()
            for event in _events(prompt):
                _index(slots, event, 'original:' + os.path.basename(path), prompt)
        for path in sorted(glob.glob(os.path.join(
                CORRECTIVE, kind, 'run/grade_batch.*.js'))):
            text = io.open(path, encoding='utf-8').read()
            at = text.index('const BOUND =')
            bound, _ = json.JSONDecoder().raw_decode(
                text[at + len('const BOUND ='):].lstrip())
            for prompt in bound['prompts']:
                for event in _events(prompt):
                    _index(slots, event, 'corrective:' + os.path.basename(path),
                           prompt)
    return slots


def records(slot):
    """(role, served produced record) for one rendering of one question."""
    out = [('asked', slot['question']['produced_record'])]
    for other in (slot['event'].get('other_records') or []):
        out.append(('comparator:' + other['other'], other['produced_record']))
    return out


def cards(slot):
    card = slot['question'].get('reference_card')
    return [card] if card else list(slot['event'].get('reference_cards') or [])



#: one disposition per SOURCE CLAIM that the changed clause reaches, with the
#: reason read off that claim's own served quote.
SCOPE = {
    'During fiscal 2025, the Company repurchased': (
        'unaffected',
        'the source names the consolidated Company as the actor and its own '
        'common stock as the object, so whole-company scope and no-applicable-'
        'part are both establishable; empty stays lawful under either text'),
    'Other Income Tax impacts recorded as Special': (
        'unaffected',
        'a consolidated income-tax special item; no business part is stated and '
        'the company-level reading is establishable, so both texts accept empty'),
    'Tax (Benefit) - Tax audit in the quarter': (
        'unaffected',
        'a consolidated income-tax item; no business part is stated and the '
        'company-level reading is establishable, so both texts accept empty'),
    '(in thousands, except per share amounts) (unaudited) Three months ended Year ended': (
        'unaffected',
        'a consolidated non-GAAP reconciliation table of a single-brand company; '
        'no part is stated and whole-company is establishable'),
    'Announced planned deployment of Starlink': (
        'unaffected',
        'the source states the deployment is across the fleet, so whole-company '
        'scope is explicit and empty is lawful under either text'),
    'with an option to purchase up to an additional 30 of the same aircraft': (
        'affected',
        'an aircraft purchase option is neither a consolidated whole-company '
        'claim nor a business population the source names, so the served text '
        'makes empty assert something the quote does not establish while the '
        'corrected text makes empty affirmatively lawful'),
    'a $320 million revenue impact from winter storms': (
        'unaffected',
        'the stated figure is a consolidated revenue impact; no business part is '
        'stated and whole-company is establishable'),
    '($ in millions, except per share amounts)': (
        'open',
        'the served quote is the consolidated table, but the corrective rules '
        'direct the grader to the surrounding source where the impairment is '
        'attributed to Health; whether a part is therefore source-stated is '
        'unsettled and Codex already holds this row open'),
    'We recorded a $15.9 million loss on early debt extinguishment': (
        'unaffected',
        'a corporate financing charge; no business part is stated and '
        'whole-company is establishable'),
    'in millions, except per share amounts Earnings Before Income Tax': (
        'open',
        'the reconciliation footnote says primarily, not exclusively, Bahama '
        'Breeze, so whether an applicable part is source-stated - which the '
        'corrected text still requires in the field - is unsettled'),
    'On October 6, 2022, we entered into a Fourth Amended and Restated Loan Agreement': (
        'unaffected',
        'a corporate credit agreement; no business part is stated and '
        'whole-company is establishable'),
    'The decrease in gross margin was driven by a 138 basis point non-cash LIFO charge.': (
        'unaffected',
        'a consolidated gross-margin charge; no business part is stated and '
        'whole-company is establishable'),
}

BASELINE = {
    '1Q26 vs 4Q25': (
        'affected',
        'the table states a prior-year column and a sequential column, and its '
        'ONLY stated change is the 1Q26 vs 4Q25 column, so the headline '
        'comparison is sequential; the served text forces prior year whenever '
        'both appear and the corrected text keeps the headline'),
    'year over year quarter over quarter': (
        'affected',
        'the quote states year over year AND quarter over quarter, and the only '
        'quantified comparison is versus the fourth quarter, so the headline is '
        'sequential; served forces prior year, corrected keeps the headline'),
    'increase sequentially up into March': (
        'unaffected',
        'the 7% carries no stated basis, so either the sequential move is the '
        'only stated comparison - both texts pick it - or the 7% is the '
        'year-over-year headline, which both texts also pick; the required '
        'answer is the same on either reading'),
    'sequential improvement from the fourth quarter': (
        'unaffected',
        'the claim states one temporal comparison, the sequential one, so the '
        "served tiebreak's both-stated precondition does not fire and the "
        'corrected headline is that same comparison'),
    'improving sequentially each month': (
        'unaffected',
        'every served produced record on this claim carries no comparison '
        'baseline at all; both texts only choose among STATED comparisons and '
        'neither speaks to an absent baseline. A correctly supported prior-year '
        'headline is not changed by the sequential mention'),
}


def _assert_unambiguous(table, quotes):
    """A needle only RECOGNISES a claim; the rule decides. So every needle must
    name exactly one served quote, or a disposition could reach a claim it was
    never read against."""
    for needle in table:
        hit = [quote for quote in quotes if needle in quote]
        if len(hit) != 1:
            raise ValueError('needle %r names %d served quotes, not 1'
                             % (needle[:60], len(hit)))


def _judge(table, quote):
    for needle, verdict in table.items():
        if needle in quote:
            return needle, verdict
    raise ValueError('no disposition for the served claim: %r' % quote[:120])


def collect():
    slots = load()
    facts = {row['question_id']: row for row in build()}
    served_quotes = {fact['item'].get('quote') or ''
                     for renderings in slots.values() for slot in renderings
                     for _role, fact in records(slot)}
    _assert_unambiguous(SCOPE, served_quotes)
    _assert_unambiguous(BASELINE, served_quotes)
    scope, baseline = {}, {}
    for qid, renderings in sorted(slots.items()):
        row = facts[qid]
        for slot in renderings:
            served = slot['clauses']
            for role, fact in records(slot):
                item, quote = fact['item'], fact['item'].get('quote') or ''
                where = 'asked' if role == 'asked' else 'comparator'
                if (served['A'] and fact.get('fact_type') == 'action_event'
                        and item.get('slice_parts') == []):
                    claim, (verdict, reason) = _judge(SCOPE, quote)
                    entry = scope.setdefault(qid, {
                        'kind': row['kind'], 'leg': row['leg'],
                        'source_id': row['source_id'], 'gold_idx': row['gold_idx'],
                        'produced_idx': row['produced_idx'], 'claims': {}})
                    got = entry['claims'].setdefault(claim, {
                        'verdict': verdict, 'reason': reason, 'roles': [],
                        'served_by': []})
                    if where not in got['roles']:
                        got['roles'].append(where)
                    surface = slot['source'].split(':')[0]
                    if surface not in got['served_by']:
                        got['served_by'].append(surface)
                if served['B']:
                    try:
                        claim, (verdict, reason) = _judge(BASELINE, quote)
                    except ValueError:
                        continue
                    entry = baseline.setdefault(qid, {
                        'kind': row['kind'], 'leg': row['leg'],
                        'source_id': row['source_id'], 'gold_idx': row['gold_idx'],
                        'produced_idx': row['produced_idx'], 'claims': {}})
                    got = entry['claims'].setdefault(claim, {
                        'verdict': verdict, 'reason': reason, 'roles': [],
                        'served_by': [],
                        'served_baseline': item.get('comparison_baseline')})
                    if where not in got['roles']:
                        got['roles'].append(where)
                    surface = slot['source'].split(':')[0]
                    if surface not in got['served_by']:
                        got['served_by'].append(surface)
    return scope, baseline


def question_verdict(entry):
    """A claim reached ONLY as a G3 comparator cannot be shown to move the
    asked record's own bucket, so it lands open rather than affected."""
    order = {'affected': 0, 'open': 1, 'unaffected': 2}
    best = min(order[c['verdict']] for c in entry['claims'].values())
    if best == 0 and all(c['roles'] == ['comparator']
                         for c in entry['claims'].values()
                         if c['verdict'] == 'affected'):
        return 'open'
    return ['affected', 'open', 'unaffected'][best]


def main(out):
    scope, baseline = collect()
    for table in (scope, baseline):
        for entry in table.values():
            entry['question_verdict'] = question_verdict(entry)
    summary = {name: collections.Counter(
        (e['kind'], e['question_verdict']) for e in table.values())
        for name, table in (('scope_action_empty', scope),
                            ('baseline_headline', baseline))}
    rows = build()
    population = collections.Counter(row['kind'] for row in rows)
    json.dump({
        'schema': 'a7-two-clause-affected-population/2169',
        'population': {'g2_questions': population['G2'],
                       'g3_questions': population['G3'],
                       'total': len(rows)},
        'summary': {k: {'%s|%s' % kk: vv for kk, vv in sorted(v.items())}
                    for k, v in summary.items()},
        'scope_action_empty': scope,
        'baseline_headline': baseline},
        io.open(out, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    for name, counter in summary.items():
        print(name, dict(counter), 'questions', len(
            scope if name == 'scope_action_empty' else baseline))


if __name__ == '__main__':
    main(sys.argv[1])
