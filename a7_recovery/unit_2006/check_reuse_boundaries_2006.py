"""Exercise every new freeze refusal with independently proved positive inputs.

Dependency-return mutations are unit tests of this new boundary, not fresh
native evidence. The full unmocked native path is proved by the lifecycle.
No original file is changed and no model or database write is invoked.
"""
import copy
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT.parent / 'unit_2005/TEST_codex_signed2005_a/TEST_RESULT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = saved['candidate']
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT.parent / 'unit_2005/owner'))
import a4_source_candidate as SC
import a6_launch_freeze as A6
import a7_prepared_run as PR
import a7_g1_build as G
import a7_g23_build as B

CL = SC.CL
scorer = Path(G.__file__).parent / 'scorers/score_exp5_current.py'
B.bind_grading_scorer(str(scorer), CL.INV.sha_file(str(scorer)))
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
results = []
with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    primary = CL.K.a3_run_dirs()[0]
    key_path = os.path.join(CL.SK.PKG_DIR, CL.SK.MANIFEST_NAME)
    expected = A6.reuse_freeze(primary, key_path)
    initial = CL.K._load(key_path)
    real_load = CL.K._load
    # These dependencies have just been proved through their real owners.
    # Hold them fixed only to reach the new consumer's exact failure branches.
    positive_inputs = [(A6.A5, 'a4_lock', A6.A5.a4_lock()),
                       (CL.K, 'a3_evidence', CL.K.a3_evidence()),
                       (A6, '_validated_attempts', A6._validated_attempts(primary)),
                       (A6, 'ledger', A6.ledger())]

    def invoke(change=(), run=primary):
        with ExitStack() as stack:
            for owner, name, value in positive_inputs:
                stack.enter_context(patch.object(owner, name, return_value=value))
            for owner, name, value in change:
                stack.enter_context(patch.object(owner, name, return_value=value))
            return A6.reuse_freeze(run, key_path)

    def refuses(name, action, message):
        assert invoke() == expected, 'positive control before ' + name
        try:
            action()
        except (ValueError, RuntimeError) as exc:
            assert message in str(exc), (name, str(exc))
            results.append(dict(case=name, refused=str(exc)))
        else:
            raise AssertionError('wrong acceptance: ' + name)
        assert invoke() == expected, 'positive control after ' + name

    def changed_initial(field, value):
        changed = copy.deepcopy(initial)
        target = changed
        for part in field[:-1]:
            target = target[part]
        target[field[-1]] = value
        with patch.object(CL.K, '_load', side_effect=lambda p: changed if p == key_path else real_load(p)):
            return invoke()

    refuses('foreign original run', lambda: invoke(run=str(out)),
            'not the independently bound A3 run')
    bad_lock = copy.deepcopy(positive_inputs[0][2])
    bad_lock['key']['bindings']['initial_source_package'] = '0' * 64
    refuses('foreign signed initial package',
            lambda: invoke([(A6.A5, 'a4_lock', bad_lock)]),
            'not bound by the signed key')
    refuses('different original plan', lambda: changed_initial(
        ['bound', os.path.basename(expected['source_manifest'])], '0' * 64),
        'not made from this original plan')
    refuses('different inventory', lambda: changed_initial(['bound', 'inventory'], '0' * 64),
            'different inventories')
    refuses('unproved original native evidence',
            lambda: invoke([(CL.K, 'a3_evidence', {'problems': ['TEST unproved']})]),
            'original A3 evidence does not hold')
    refuses('missing original finalization', lambda: invoke([(PR, '_finalizations', {})]),
            'preserved, finalized original evidence')
    refuses('empty original evidence digest', lambda: invoke([(PR, '_executed', {})]),
            'preserved, finalized original evidence')
    refuses('raw rows not bound to native answers', lambda: invoke([
        (CL.RT, 'a1_raw_binding_problems', ['TEST wrong raw binding'])]),
        'original raw binding does not hold')
    for value in (initial['budget']['before'] - 1, True, float(initial['budget']['before'])):
        refuses('wrong baseline value/type ' + repr(value),
                lambda value=value: changed_initial(['budget', 'before'], value),
                'not the source-key baseline')
    refuses('disagreement with original accounting owner', lambda: invoke([
        (CL.K, 'ledger_before', initial['budget']['before'] + 1)]),
        'not the source-key baseline')
    refuses('signed baseline lost original calls', lambda: invoke([
        (A6, 'ledger', (initial['budget']['before'] - 1, []))]),
        'signed key baseline lost its original calls')

    frozen_root = UNIT / 'TEST_codex_reuse_pipeline2006_c'
    pin = CL.INV.sha_file(str(frozen_root / A6.REUSE_FREEZE_NAME))
    def foreign_owner():
        with patch.object(G, '__file__', str(out / 'a7_g1_build.py')):
            return PR.reuse(str(frozen_root), pin)

    refuses('foreign G1 callable owner', foreign_owner, "this harness's G1 owner")
    assert PR.reuse(str(frozen_root), pin)['run_dir'] == primary

CL.RT.write_new(str(out / 'RESULTS.json'), json.dumps({
    'kind': 'consumer refusal branch tests; dependency mutations, not native proof',
    'model_calls': 0, 'passed': len(results), 'results': results,
    'positive_controls': 'real proved freeze before and after each refusal'}, indent=1))
print(json.dumps({'boundary_refusals': len(results), 'positive_controls': 'all passed',
                  'model_calls': 0}, indent=1))
