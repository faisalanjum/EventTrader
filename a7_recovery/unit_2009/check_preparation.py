"""Actual old evidence -> four clarified requests; no model or native writes."""
import collections
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R

CL, HR, K = R.CL, R.HR, R.K
checks = []


def check(name, value):
    assert value, name
    checks.append(name)


original_owners = (CL.HR, CL.SK.HR, CL.F.HR, CL.F._HERE, CL._ctx,
                   CL.RT.write_new, CL.RT.save_raw)
old, stage = R.old_readings()
check('historical native proof retains62 valid and4 invalid',
      collections.Counter(v[0] for v in old.values()) == {'valid':62, 'invalid_response':4})
best = {}
spent = 0
for base in (R.OLD_RUN, os.path.join(R.OLD_RUN, 'retry')):
    doc = json.loads(Path(base, K.FINALIZATION_NAME).read_text())
    spent += len(json.loads(Path(base, K.RECEIPT_NAME).read_text())['allowed'])
    for label, state, reason in doc['outcomes']:
        if best.get(label) != 'valid':
            best[label] = state
expected = [label for label, state in best.items() if state != 'valid']
check('independent old closeout calculation', spent == 80 and expected ==
      ['sokc-013/b2', 'sokc-020/b1', 'sokc-026/b1', 'sokc-029/b2'])
ctx = R._context(old, stage)
check('only the four independently derived missing slots', HR._canonical_of(ctx) == expected)
check('495 earlier calls counted once', ctx['before'] == 382 + 33 + spent)
old_manifest = K._load(os.path.join(R.OLD_PKG, CL.MANIFEST_NAME))
manifest = HR._manifest(ctx)
by_old = {row['task_id']: row for row in old_manifest['tasks']}
for row in manifest['tasks']:
    prior = by_old[row['task_id']]
    check('same source/members/payload: ' + row['task_id'], all(
        row[key] == prior[key] for key in ('source_id', 'members', 'payload_sha256')))
    check('changed instruction only for the unsatisfied slot: ' + row['task_id'],
          row['prompt_sha256'] != prior['prompt_sha256'])
check('unchanged item instructions', manifest['prefix_item_sha256'] == old_manifest['prefix_item_sha256'])
check('four primary calls with only the existing single retry',
      [manifest['budget'][key] for key in ('primaries', 'after_primaries', 'worst_case_after')]
      == [4, 499, 503])
for label, (task, blind) in HR._by_label_of(ctx).items():
    prompt = HR._blind_prompt(ctx, task)
    check('no previous answer in request: ' + label,
          all(value[2] not in prompt for value in old.values() if value[0] == 'valid'))
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
package, run = str(out / 'package'), str(out / 'run')
R.build(package)
prep = R.prepare_run(run, package)
check('actual package and prepare path passes', prep['ok'] and not prep['problems'])
check('actual receipt schedules exactly four',
      K._load(os.path.join(run, K.RECEIPT_NAME))['allowed'] == expected)
check('four emitted callable scripts', len(prep['invocations']) == 4)
try:
    with R.final_scope(run, package):
        raise AssertionError('unfinalized new reviews entered final-key gate')
except ValueError as exc:
    check('unfinalized new reviews refuse before key preparation',
          'not finalized' in str(exc))
check('all temporary owners restored, also after refusal', original_owners ==
      (CL.HR, CL.SK.HR, CL.F.HR, CL.F._HERE, CL._ctx, CL.RT.write_new, CL.RT.save_raw))
result = {'model_calls':0, 'passed':len(checks), 'checks':checks,
          'package':package, 'run':run, 'manifest_sha256':CL.INV.sha_file(
              os.path.join(package, CL.MANIFEST_NAME))}
CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps(result, indent=1))
print(json.dumps(result, indent=1))
