"""The selected-review retry uses real native/finalization owners; TEST only."""
import collections
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R
sys.path.insert(0, str(UNIT.parent / 'unit_2001/tests'))
import synthetic_reading as SYN

CL, H, K = R.CL, R.HR, R.K
projects = Path('/home/faisal/.claude/projects')
assert os.path.samefile(projects, UNIT / 'integration_retry/projects')
pristine = UNIT.parent / 'unit_2008/TEST_projects/_pristine'
saved = json.loads((UNIT / 'TEST_codex_join2009_a/TEST_RESULT.json').read_text())
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
run, package = str(out / 'run'), str(out / 'package')
checks = []


def check(name, ok):
    assert ok, name
    checks.append(name)
    print('PASS', name, flush=True)


old, stage = R.old_readings()
expected = H._canonical_of(R._context(old, stage))
for name, changed_old, changed_stage, changes in [
    ('changed historical population', collections.OrderedDict(list(old.items())[1:]), stage, {}),
    ('unexhausted historical retry', old,
     dict(stage, evidence={R.OLD_RUN: stage['evidence'][R.OLD_RUN]}), {}),
    ('unchanged prompt after exhausted retry', old, stage,
     {'_blind_prompt': R.OLD._blind_prompt}),
]:
    check('positive before ' + name, H._canonical_of(R._context(old, stage)) == expected)
    with R._using(H, **changes):
        try:
            R._context(changed_old, changed_stage)
        except ValueError:
            check(name + ' refuses', True)
        else:
            raise AssertionError(name + ' accepted')
    check('positive restored after ' + name,
          H._canonical_of(R._context(old, stage)) == expected)

R.build(package)
prep = R.prepare_run(run, package)
check('only four unsatisfied slots prepare', prep['ok'] and len(prep['invocations']) == 4)
bad_label = prep['invocations'][0]['label']
valid_texts = {inv['label']: Path(saved['review'], 'raw',
               inv['label'].replace('/', '_') + '.attempt1.proved.json').read_text()
               for inv in prep['invocations']}
with R._current_scope():
    for n, inv in enumerate(prep['invocations']):
        text = '{}' if inv['label'] == bad_label else valid_texts[inv['label']]
        path = SYN.write_state(CL, run, package, inv['label'],
                               'wf_TEST_retry2009_primary_%03d' % n,
                               str(pristine), str(projects), text=text)
        assert not CL.record_state(run, path)
primary = R.finalize(run, package)
check('one invalid result remains counted and gets exactly one child',
      primary['primary_complete'] and not primary['problems']
      and primary['ledger']['valid'] == 3 and primary['ledger']['invalid_response'] == 1
      and primary['retry'] == [bad_label])
child = os.path.join(run, 'retry')
receipt = K._load(os.path.join(child, K.RECEIPT_NAME))
check('child excludes every successful primary', receipt['allowed'] == [bad_label])
try:
    with R.final_scope(run, package):
        raise AssertionError('a waiting child reached the key phase')
except ValueError:
    check('waiting child blocks the key phase', True)
before = {p: p.read_bytes() for p in Path(run, 'raw').iterdir() if p.is_file()}
with R._current_scope():
    path = SYN.write_state(CL, child, package, bad_label, 'wf_TEST_retry2009_child_000',
                           str(pristine), str(projects), text=valid_texts[bad_label], attempt=2)
    assert not CL.record_state(child, path)
done = R.finalize(child, package)
check('the native child completes with no third attempt',
      done['primary_complete'] and not done['problems'] and done['ledger']['valid'] == 1
      and not done['retry'] and not os.path.exists(os.path.join(child, 'retry')))
merged, stages = R.merged_readings(run, package)
check('all66 review obligations served and all62 original successes unchanged',
      len(merged) == 66 and all(value[0] == 'valid' for value in merged.values())
      and all(merged[label] == value for label, value in old.items() if value[0] == 'valid'))
check('failed and successful primary raw evidence is unchanged',
      all(path.read_bytes() == data for path, data in before.items()))
with R.final_scope(run, package) as proof:
    doc = R.SK.manifest()
    check('both new attempts are bound and all500 historical/TEST calls count once',
          set(doc['hard_review']['stages']['clarified']['evidence']) == {run, child}
          and doc['budget']['before'] == 382 + 33 + 66 + 14 + 4 + 1)
    check('final key still receives exactly two leads for each of33 sources',
          len(proof['by_source']) == 33
          and all(len(leads) == 2 for leads in proof['by_source'].values()))
R.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind': 'TEST ONLY: copied synthetic answers; zero model calls',
    'checks': checks, 'passed': len(checks), 'run': run, 'package': package}, indent=1))
print('COMPLETE', len(checks), 'checks; zero AI calls')
