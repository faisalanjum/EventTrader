"""Observe the existing A7 scorer to bind its totals to exact input records.

One deterministic replay, no AI, no changed scorer or judgments. The original
baseline remains immutable. This is diagnosis evidence, not another scorer.
"""
import ast
import collections
import copy
import os
import runpy
import sys
from pathlib import Path

import prepare_g23_partial_2097 as E

G, B = E.G, E.B
HERE = Path(__file__).resolve().parent
baseline_path = Path(os.environ['A7_BASELINE_PATH'])
assert G._sha_file(str(baseline_path)) == os.environ['A7_BASELINE_SHA256']
baseline = G._read(str(baseline_path))
caller = HERE / 'score_actual_grading_2111.py'
assert G._sha_file(str(caller)) == baseline['caller_sha256']
records, active, counter_lines = {}, {}, {}


def indexed(mapping):
    return [{'key': list(k), 'value': v} for k, v in sorted((mapping or {}).items())]


def context(frame):
    values = frame.f_locals
    names = ('sid', 'gi', 'pi', 'orig_i', 'ai', 'f', 'slot', 'problem',
             'established', 'written', 'accepted_unmatched', 'tally')
    return {'line': frame.f_lineno,
            'locals': copy.deepcopy({k: values[k] for k in names if k in values})}


def score_trace(frame, event, value):
    state = active[id(frame)]
    loc = frame.f_locals
    for name in ('confirmed_wrong_accepted', 'verdicts_missing'):
        now = loc.get(name, 0)
        before = state['last'].get(name, 0)
        if now != before:
            assert now > before and name in state['pending'], name
            state['row'][name].append(dict(state['pending'][name], delta=now - before))
        state['last'][name] = now
        if event == 'line' and frame.f_lineno in counter_lines[name]:
            state['pending'][name] = context(frame)
    if event == 'return':
        keys = ('tot_gold', 'matched', 'lane_wrong', 'park', 'items_n',
                'code_ok', 'code_all', 'state_ok', 'state_all',
                'other_ok', 'other_all', 'confirmed_wrong_accepted',
                'verdicts_missing', 'ambiguities_unresolved', 'grader_problems')
        state['row']['counters'] = {k: loc[k] for k in keys}
        state['row']['result'] = copy.deepcopy(value)
        del active[id(frame)]
    return score_trace


def observe(frame, event, _value):
    if event != 'call':
        return None
    parent = frame.f_back
    if frame.f_code.co_name == '_e' and parent is not None and id(parent) in active:
        active[id(parent)]['row']['errors'].append(
            dict(context(parent), code=frame.f_locals['code']))
        return None
    scorer = B.GRADING_SCORER
    if scorer is None or frame.f_code is not scorer.score_arm.__code__:
        return None
    while parent is not None and parent.f_code is not B._score_leg_bound.__code__:
        parent = parent.f_back
    if parent is None:
        return None  # Population preparation is not the final per-leg score.
    leg = parent.f_locals['leg']
    assert leg not in records, 'a final leg was scored twice'
    if not counter_lines:
        assert G._sha_file(scorer.__file__) == E.launch['owners']['grading_scorer']
        tree = ast.parse(Path(scorer.__file__).read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'score_arm')
        for name in ('confirmed_wrong_accepted', 'verdicts_missing'):
            counter_lines[name] = {n.lineno for n in ast.walk(fn)
                                   if isinstance(n, ast.AugAssign)
                                   and isinstance(n.target, ast.Name)
                                   and n.target.id == name}
            assert counter_lines[name], name
    loc = frame.f_locals
    inputs = copy.deepcopy({k: loc[k] for k in
                            ('gold_by_event', 'arm_by_event', 'event_meta',
                             'responses', 'responses_required', 'safety_findings')})
    for name in ('grader_verdicts', 'ambiguity_resolutions', 'extras_verdicts'):
        inputs[name] = copy.deepcopy(indexed(loc[name]))
    inputs['route'] = {
        sid: dict(copy.deepcopy({k: v for k, v in row.items() if k != 'index_map'}),
                  index_map=copy.deepcopy(indexed(row['index_map'])))
        for sid, row in loc['route'].items()}
    row = {'inputs': inputs, 'errors': [], 'confirmed_wrong_accepted': [], 'verdicts_missing': []}
    records[leg] = row
    active[id(frame)] = {'row': row, 'last': {}, 'pending': {}}
    return score_trace


previous = sys.gettrace()
completed = False
try:
    sys.settrace(observe)
    runpy.run_path(str(caller), run_name='__main__')
    completed = True
finally:
    sys.settrace(previous)
    G._write_new(str(E.out / 'SCORER_TRACE.json'), G._pretty({
        'scope': 'observed real scorer inputs, error emissions and counter increments',
        'replay_completed': completed, 'baseline_sha256': os.environ['A7_BASELINE_SHA256'],
        'observer_sha256': G._sha_file(__file__), 'records': records,
        'new_model_calls': 0}) + '\n')

assert not active
assert set(records) == set(baseline['results'])
for leg, row in records.items():
    expected = baseline['results'][leg]
    assert row['result'] == expected, leg
    assert dict(collections.Counter(r['code'] for r in row['errors'])) == expected['error_table'], leg
    for name in ('confirmed_wrong_accepted', 'verdicts_missing'):
        assert sum(r['delta'] for r in row[name]) == expected[name], (leg, name)
assert G._sha_file(str(E.out / 'A7_BASELINE.json')) == os.environ['A7_BASELINE_SHA256']
G._write_new(str(E.out / 'TRACE_CHECK.json'), G._pretty({
    'scope': 'all final scorer totals reproduce the immutable baseline exactly',
    'baseline_sha256': os.environ['A7_BASELINE_SHA256'],
    'trace_sha256': G._sha_file(str(E.out / 'SCORER_TRACE.json')),
    'legs': {leg: {'error_emissions': len(r['errors']),
                   'wrong_accepts': sum(x['delta'] for x in r['confirmed_wrong_accepted']),
                   'missing_judgments': sum(x['delta'] for x in r['verdicts_missing'])}
             for leg, r in records.items()}, 'new_model_calls': 0}) + '\n')
print('VERIFIED observer covers every final error emission and counted wrong/unknown judgment', flush=True)
