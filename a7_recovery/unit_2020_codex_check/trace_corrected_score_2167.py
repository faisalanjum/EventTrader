"""Read-only cause inventory for the saved native score; no grading decisions.

Reuses the real matcher, scorer and route-accounting owners. Decimal strings
are restored only in numeric slots of inputs already validated by the native
run: G._pretty encodes Decimal that way. Original model bytes never change.
"""
import copy
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

import test_grading_input_correction_2114 as ENV
import a7_duplicate_accounting_2116 as DUP
from driver.core.prepared_fact_v2 import NUMERIC_SLOTS

G, B = ENV.G, ENV.OLD
U = Path(__file__).resolve().parent
REPORT = U / 'codex_corrected_score2166_a/A7_CORRECTED_SCORE.json'
CANDIDATE = U / 'codex_currentg232157_c/a7_g23_candidate.json'
SCORER = U.parent / 'unit_2008/harness_g1v3/scorers/score_exp5_current.py'
PINS = {
    str(REPORT): '656c18bd363ac3941a737d4d3ae55b101f303c209727ed261325a42e9664f08a',
    str(CANDIDATE): '020f4550c47e0f4bbfb63aebe67854d5eb3efade92c674ae72fceb40f1d3050a',
    str(SCORER): '6d0a02285162a079a81615db6ae64fddaa43acef64214315339c8d78bfd7f43e',
    DUP.__file__: '375cc4830da12ba1728371e7a76a4d6932c6fb7fada545ce16c918eef4879ce4',
}


def verify():
    for path, digest in PINS.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path


def indexed(rows):
    result = {tuple(row['key']): row['value'] for row in rows}
    assert len(result) == len(rows)
    return result


def restore_numeric_slots(facts):
    result = copy.deepcopy(facts)
    for fact in result:
        for name in NUMERIC_SLOTS:
            slot = fact['item'].get(name)
            if slot is not None:
                for field in ('value', 'scale_multiplier'):
                    if isinstance(slot[field], str):
                        slot[field] = Decimal(slot[field])
                        assert slot[field].is_finite()
    return result


def run():
    verify()
    report = json.loads(REPORT.read_text())
    candidate = json.loads(CANDIDATE.read_text())
    B.bind_grading_scorer(str(SCORER), PINS[str(SCORER)])
    S = B._scorer()
    gold = {sid: restore_numeric_slots(rows) for sid, rows in report['key'].items()}
    rows, counters, measured = [], [], {}
    for leg, case in report['cases'].items():
        answers = copy.deepcopy(case['answers'])
        for answer in answers.values():
            answer['facts'] = restore_numeric_slots(answer['facts'])
        resolution = indexed(case['resolutions'])
        meanings, extras = indexed(case['meanings']), indexed(case['extras'])
        route = copy.deepcopy(case['route'])
        for event in route.values():
            event['index_map'] = indexed(event['index_map'])
        pairs = B.matched_pairs(gold, answers, resolution)
        wanted = {sid: candidate['g2_pairs'].get(leg + '|' + sid, []) for sid in gold}
        assert {sid: [list(p) for p in ps] for sid, ps in pairs.items()} == wanted
        assert set(meanings) == {(sid, gi) for sid, ps in pairs.items() for gi, pi in ps}

        def trace(frame, event, _arg):
            if event == 'call' and frame.f_code.co_name == '_e':
                parent = frame.f_back
                if parent.f_code.co_name == 'score_arm':
                    local, code = parent.f_locals, frame.f_locals['code']
                    row = {'leg': leg, 'sid': local['sid'], 'code': code}
                    if code.startswith(('mismatch:', 'verdict:', 'wrong_lane:')):
                        row['gold_idx'] = local.get('gi')
                        if code != 'wrong_lane:missing_gold_twin':
                            row['produced_idx'] = local.get('pi')
                    counters.append(row)
            return trace

        previous = sys.gettrace()
        try:
            sys.settrace(trace)
            with DUP.scope(S, PINS[DUP.__file__], PINS[str(SCORER)]):
                result = S.score_arm(gold, answers, case['event_meta'], meanings,
                                     resolution, route=route, extras_verdicts=extras)
        finally:
            sys.settrace(previous)
        # External response statistics and G1 group findings were not replayed.
        # Every counter this read-only replay actually consumes must match.
        compared = ('gold_n', 'matched', 'recall', 'wrong_lane', 'value_shape_acc',
                    'state_acc', 'other_meaning_acc', 'would_park', 'error_table',
                    'extras', 'ambiguous_rows', 'confirmed_wrong_accepted',
                    'verdicts_missing', 'ambiguities_unresolved',
                    'name_spelling_differences', 'duplicate_violations')
        for field in compared:
            assert result[field] == report['results'][leg][field], (leg, field)
        measured[leg] = {field: result[field] for field in compared}
        for sid, facts in gold.items():
            du = [g for g in facts if g.get('du_worthy') is True]
            produced = answers[sid]['facts']
            outcomes = S._rows_for_event(route, sid, produced,
                                         len(answers[sid].get('abstentions') or []))
            by_gold = dict(pairs[sid])
            for gi, fact in enumerate(du):
                base = {'leg': leg, 'sid': sid, 'gold_idx': gi}
                if gi not in by_gold:
                    rows.append(dict(base, kind='recall_miss',
                                     ruling_present=(sid, gi) in resolution,
                                     ruling=resolution.get((sid, gi))))
                    continue
                pi = by_gold[gi]
                verdict = meanings[(sid, gi)]
                false = [k for k, v in verdict.items() if v is False]
                unknown = [k for k in S.MEANING_FIELDS
                           if not isinstance(verdict.get(k), bool)]
                row = dict(base, produced_idx=pi,
                           question_id=B.meaning_question_id(leg, sid, gi, pi),
                           outcome=outcomes[('fact', pi)])
                if false:
                    rows.append(dict(row, kind='meaning_false', aspects=false,
                                     wrong_accept_flag=row['outcome']['decision'] == 'written'))
                if unknown:
                    rows.append(dict(row, kind='meaning_incomplete', aspects=unknown))
            for (source, pi), verdict in extras.items():
                if source == sid:
                    rows.append(dict(leg=leg, sid=sid, produced_idx=pi,
                                     question_id=B.extras_question_id(leg, sid, pi),
                                     kind='extra', bucket=verdict,
                                     outcome=outcomes[('fact', pi)]))
        own = [row for row in rows if row['leg'] == leg]
        wrong = sum(row.get('wrong_accept_flag', False) for row in own)
        wrong += sum(row['kind'] == 'extra' and row['bucket'] == 'unsupported'
                     and row['outcome']['decision'] == 'written' for row in own)
        assert wrong == result['confirmed_wrong_accepted']
        assert sum(row['kind'] == 'recall_miss' for row in own) == result['gold_n'] - result['matched']
        assert sum(row['kind'] == 'meaning_incomplete' for row in own) == result['verdicts_missing']
    verify()
    return dict(scope='Read-only native-owner counter replay and exact cause inventory; '
                      'not independent semantic adjudication or a replacement score',
                inputs=PINS, code_sha256=G._sha_file(__file__),
                excluded_from_replay=['original response reliability', 'G1 group safety findings',
                                      'final tier decision'],
                measured=measured, rows=rows, counter_events=counters)


if __name__ == '__main__':
    print(G._pretty(run()))
