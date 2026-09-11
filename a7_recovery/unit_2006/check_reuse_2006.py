"""TEST key + real unchanged A3 answers: separate evaluation, never a new run.

No model is called. Expected population counts come from the original source
manifest and receipt, not from the evaluation code under test.
"""
import hashlib
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
CL = SC.CL
import a7_prepared_run as PR
import a7_g1_build as G
import a6_launch_freeze as A6

checks = []


def check(name, ok):
    checks.append({'check': name, 'ok': bool(ok)})
    assert ok, name


def refused(name, call):
    try:
        call()
    except (ValueError, OSError) as exc:
        check(name, True)
        return str(exc)
    raise AssertionError(name + ': accepted')


primary, _retry = CL.K.a3_run_dirs()
plan = CL.RT.a1_plan_for_run(primary)
receipt = CL.K._load(os.path.join(primary, CL.K.RECEIPT_NAME))
original = PR._executed(primary)
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    key_manifest = os.path.join(CL.SK.PKG_DIR, CL.SK.MANIFEST_NAME)
    frozen = A6.reuse_freeze(primary, key_manifest)
    rendered = A6.render(frozen)
    pin = hashlib.sha256(rendered.encode()).hexdigest()
    CL.RT.write_new(str(out / A6.REUSE_FREEZE_NAME), rendered)
    run = PR.reuse(str(out), pin)
    check('original run and era remain explicit',
          run['run_dir'] == primary and run['contract_suffix'] == plan.get('contract_suffix'))
    check('original manifest is not relabelled as an A5 manifest',
          run['source_manifest_sha256'] == CL.INV.sha_file(CL.SK.PLAN_PATH)
          and 'a5_manifest_sha256' not in run)
    check('all original calls are present, with zero new producer calls',
          run['scheduled_calls'] == len(receipt['allowed'])
          and frozen['budget']['planned_producer_primary'] == 0)
    check('original answers are already in the independently signed baseline',
          frozen['budget']['completed_actual'] == 515
          and frozen['reused_calls'] == len(receipt['allowed']))
    refused('a missing external evaluation pin refuses', lambda: PR.reuse(str(out)))
    refused('a foreign external evaluation pin refuses', lambda: PR.reuse(str(out), '0' * 64))
    refused('the old new-run entry still refuses the old A3 directory', lambda: PR.current(primary, pin))
    check('cold consumer revalidates the explicit evaluation', G.run_of(run) == primary)
    arms, meta, problems = G.materialize(run)
    check('full source denominator includes every no-item event',
          meta['events'] == len(plan['events']) == 36)
    check('every scheduled item and reply is represented',
          meta['packets'] == len(plan['packets']) == 191
          and len(meta['trace']) == len(receipt['allowed']) == 382
          and meta['answers'] == 382)
    check('materialization does not count the original calls twice',
          meta['budget']['completed_actual'] == frozen['budget']['completed_actual'])
    check('the complete materializer reports no accounting or identity problem', not problems)
    check('both arms are present', sorted(arms) == ['P1', 'P2'])
    with patch('a1_reader.read_one', side_effect=AssertionError('warm reparse')):
        check('a warm consumer reuses the proved trace', G.materialize(run) == (arms, meta, problems))
    changed = dict(run, scheduled_calls=run['scheduled_calls'] - 1)
    refused('an altered evaluation identity refuses', lambda: G.run_of(changed))
    check('the restored positive still works', G.run_of(run) == primary)
    check('every original run byte is unchanged', PR._executed(primary) == original)

result = {'kind': 'TEST signed key with actual unchanged A3 evidence; no real approval',
          'model_calls': 0, 'passed': len(checks), 'checks': checks,
          'evaluation_sha256': pin, 'identity': run,
          'required': G._required(plan), 'problems': problems}
CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps(result, indent=1))
print(json.dumps(result, indent=1))
