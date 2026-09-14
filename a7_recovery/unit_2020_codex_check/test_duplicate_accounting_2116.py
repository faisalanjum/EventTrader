"""Actual scorer regressions; saved routes and synthetic route rows, no AI.

The complete saved replay is checked against its immutable baseline first.
Synthetic controls exercise accounting, not production-route certification.
"""
import copy
import hashlib
import importlib.util
import json
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest
from driver.core.prepared_fact_v2 import NUMERIC_SLOTS

A7 = Path(__file__).resolve().parents[1]
for rel in ('grader_20260909/harness_g1v3', 'unit_2008/harness_g1v3',
            'unit_2006/harness_g1v3', 'unit_2009/owner'):
    sys.path.insert(0, str(A7 / rel))

OWNER = A7 / 'unit_2008/harness_g1v3/scorers/score_exp5_current.py'
OWNER_SHA = '6d0a02285162a079a81615db6ae64fddaa43acef64214315339c8d78bfd7f43e'
TRACE = Path(__file__).parent / 'codex_scoretrace2112_a/SCORER_TRACE.json'
TRACE_SHA = '0b4a3f624a4024fb071fff1740f04b186027b2c91bcade2aaba4ce6bb05f7ee4'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def scorer():
    assert sha(OWNER) == OWNER_SHA
    spec = importlib.util.spec_from_file_location('duplicate_accounting_subject', OWNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def correction(scorer):
    import a7_duplicate_accounting_2116 as fix
    return fix.scope(scorer, sha(Path(fix.__file__)), OWNER_SHA)


def replay(leg):
    assert sha(TRACE) == TRACE_SHA
    row = json.loads(TRACE.read_text())['records'][leg]
    args = row['inputs']
    # The observer's exact JSON encoder stores Decimal as strings. Restore
    # only the declared numeric-object fields, never identifiers or quotes.
    facts = [f for rows in args['gold_by_event'].values() for f in rows]
    facts += [f for answer in args['arm_by_event'].values() for f in answer['facts']]
    for fact in facts:
        for field in NUMERIC_SLOTS:
            slot = fact['item'].get(field)
            if slot is not None:
                for name in ('value', 'scale_multiplier'):
                    if isinstance(slot[name], str):
                        slot[name] = Decimal(slot[name])
    for field in ('grader_verdicts', 'ambiguity_resolutions', 'extras_verdicts'):
        args[field] = {tuple(r['key']): r['value'] for r in args[field]}
    for route in args['route'].values():
        route['index_map'] = {tuple(r['key']): r['value'] for r in route['index_map']}
    return args, row['result']


@pytest.mark.parametrize('leg,open_groups', [('P1', 1), ('P2', 3), ('UNION', 55)])
def test_entire_saved_population_keeps_all_non_accounting_results(scorer, leg, open_groups):
    args, baseline = replay(leg)
    assert scorer.score_arm(**args) == baseline
    assert not [r for r in baseline['ambiguous_rows'] if r['reason'] == 'duplicate_produced']
    before = copy.deepcopy(args)
    with correction(scorer):
        result = scorer.score_arm(**args)
    assert result['duplicate_violations'] == 0
    assert result['open_identity_findings'] == open_groups
    assert {k: v for k, v in result.items() if k not in (
        'duplicate_violations', 'open_identity_findings')} == {
        k: v for k, v in baseline.items() if k not in (
            'duplicate_violations', 'open_identity_findings')}
    assert scorer.final_gate(result) is False  # Wrong accepts still veto.
    assert args == before
    assert scorer.score_arm(**args) == baseline


def control(scorer, extra=None, group=False, wrong=False):
    args, _ = replay('P1')
    sid, rows = next(iter(args['gold_by_event'].items()))
    gold = copy.deepcopy(next(f for f in rows if f.get('du_worthy') is True))
    produced = [{k: copy.deepcopy(v) for k, v in gold.items()
                 if k not in ('du_worthy', 'gold_extra', 'ambiguity_note')}]
    if extra:
        produced.append(copy.deepcopy(produced[0]))
        if extra == 'semantic':
            produced[1]['item']['driver_name'] += '_alternate'
    verdicts = {name: True for name in scorer.MEANING_FIELDS}
    if wrong:
        verdicts['driver_state'] = False
    return dict(
        gold_by_event={sid: [gold]},
        arm_by_event={sid: {'facts': produced, 'abstentions': []}},
        event_meta={sid: args['event_meta'][sid]},
        grader_verdicts={(sid, 0): verdicts}, ambiguity_resolutions={},
        extras_verdicts={(sid, 1): 'duplicate'} if extra == 'semantic' else {},
        safety_findings={'confirmed_duplicate_groups': [
            {'source_id': sid, 'kind': 'one_gold_many_produced',
             'gold_idxs': [0], 'produced_idxs': [0, 1], 'contested': False}]
            if group else []},
        route={sid: {'result': {'items': [
            {'index': i, 'decision': 'written', 'codes': []} for i in range(len(produced))]},
            'index_map': {('fact', i): i for i in range(len(produced))},
            'rejected_conflicting_names': [], 'rejected_fact_idxs': []}})


def test_semantic_extra_is_reported_but_does_not_fail_emission_bar(scorer):
    base = control(scorer)
    assert scorer.score_arm(**base)['PASS'] is True
    args = control(scorer, extra='semantic')
    with correction(scorer):
        result = scorer.score_arm(**args)
    assert result['extras']['duplicate'] == 1
    assert result['duplicate_violations'] == 0
    assert result['safety_result'] == 'PASS'
    assert result['matched'] == 1 and result['recall'] == 1
    assert result['PASS'] is True


def test_exact_duplicate_still_fails_and_never_gets_double_credit(scorer):
    with correction(scorer):
        assert scorer.score_arm(**control(scorer))['PASS'] is True
        result = scorer.score_arm(**control(scorer, extra='exact'))
    assert result['duplicate_violations'] == 1
    assert result['matched'] == 1 and result['recall'] == 1
    assert result['safety_result'] == 'FAIL'
    assert scorer.final_gate(result) is False


def test_g1_attempt_group_remains_open_without_claiming_an_emission(scorer):
    with correction(scorer):
        result = scorer.score_arm(**control(scorer, extra='semantic', group=True))
    assert result['duplicate_violations'] == 0
    assert result['open_identity_findings'] == 1
    assert result['safety_result'] == 'INCONCLUSIVE'
    assert scorer.final_gate(result) is None


def test_real_wrong_accept_still_fails_beside_unresolved_identity(scorer):
    with correction(scorer):
        result = scorer.score_arm(**control(scorer, extra='semantic', group=True, wrong=True))
    assert result['confirmed_wrong_accepted'] == 1
    assert result['open_identity_findings'] == 1
    assert scorer.final_gate(result) is False


@pytest.mark.parametrize('decision', ['written', 'parked', 'skipped', 'rejected'])
@pytest.mark.parametrize('count', [2, 3, 5])
def test_exact_duplicate_counts_every_repetition_even_when_not_written(scorer, decision, count):
    args = control(scorer)
    sid = next(iter(args['arm_by_event']))
    fact = args['arm_by_event'][sid]['facts'][0]
    args['arm_by_event'][sid]['facts'] = [copy.deepcopy(fact) for _ in range(count)]
    entry = args['route'][sid]
    entry['result']['items'] = [{'index': i, 'decision': decision, 'codes': []}
                                for i in range(count)]
    entry['index_map'] = {('fact', i): i for i in range(count)}
    with correction(scorer):
        result = scorer.score_arm(**args)
    assert result['duplicate_violations'] == count - 1
    assert result['matched'] == 1
    assert scorer.final_gate(result) is False


def test_pin_refusals_and_owner_restoration(scorer, monkeypatch):
    import a7_duplicate_accounting_2116 as fix
    code_sha = sha(Path(fix.__file__))
    original = scorer.score_arm
    assert scorer.score_arm(**control(scorer))['PASS'] is True
    for code, owner in [('0' * 64, OWNER_SHA), (code_sha, '0' * 64)]:
        with pytest.raises(ValueError, match='unapproved'):
            with fix.scope(scorer, code, owner):
                pytest.fail('an unapproved identity entered scoring')
        assert scorer.score_arm is original
    with pytest.raises(ValueError, match='route must cover exactly'):
        with correction(scorer):
            args = control(scorer)
            args['route'] = {}
            scorer.score_arm(**args)
    assert scorer.score_arm is original
    with pytest.raises(ValueError, match='unapproved'):
        with correction(scorer):
            saved = fix.G._sha_file
            monkeypatch.setattr(fix.G, '_sha_file', lambda p: '0' * 64
                                if str(p) == str(OWNER) else saved(p))
            scorer.score_arm(**control(scorer))
    assert scorer.score_arm is original


@pytest.mark.parametrize('mutation', ['lose_exact_violation', 'lose_open_group', 'penalize_semantic'])
def test_meaningful_counter_mutations_with_real_positive_controls(scorer, mutation):
    import a7_duplicate_accounting_2116 as fix
    # These controls call the actual scorer, not a test verdict stub.
    test_exact_duplicate_still_fails_and_never_gets_double_credit(scorer)
    test_g1_attempt_group_remains_open_without_claiming_an_emission(scorer)
    test_semantic_extra_is_reported_but_does_not_fail_emission_bar(scorer)
    source = Path(fix.__file__).read_text()
    if mutation == 'lose_exact_violation':
        old, new = 'sum(len(row["produced_idxs"]) - 1', 'sum(0'
    elif mutation == 'lose_open_group':
        # Replace only the NEW string, not the frozen-source match guard.
        old = "'    open_identity = (len(_find.get(\"confirmed_duplicate_groups\") or [])\\n'"
        new = "'    open_identity = (0\\n'"
    else:
        old, new = 'duplicate_violations = sum(', 'duplicate_violations = extras_tally.get("duplicate", 0) + sum('
    assert source.count(old) == 1
    mutant = types.ModuleType('mutant_duplicate_accounting')
    mutant.__file__ = fix.__file__
    exec(compile(source.replace(old, new, 1), '<test-only-mutant>', 'exec'), vars(mutant))
    with mutant.scope(scorer, sha(Path(fix.__file__)), OWNER_SHA):
        exact = scorer.score_arm(**control(scorer, extra='exact'))
        opened = scorer.score_arm(**control(scorer, extra='semantic', group=True))
        semantic = scorer.score_arm(**control(scorer, extra='semantic'))
    assert not (exact['duplicate_violations'] == 1
                and opened['open_identity_findings'] == 1
                and semantic['duplicate_violations'] == 0)
