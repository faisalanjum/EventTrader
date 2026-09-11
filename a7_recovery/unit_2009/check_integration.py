"""Private TEST reviews -> final adjudication -> materializer -> candidate.

All newly emitted replies are explicit synthetic fixtures, not factual review
or real approval. The preserved original reviews remain exact native bytes.
"""
import collections
import hashlib
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R
sys.path.insert(0, str(UNIT.parent / 'unit_2001/tests'))
import synthetic_reading as SYN
CL, SK, K, HR = R.CL, R.SK, R.K, R.HR
tag = os.environ['A7_TAG']
projects = Path('/home/faisal/.claude/projects')
private = UNIT / ('integration_' + os.environ['A7_TEST_FIXTURE']) / 'projects'
assert os.path.samefile(projects, private), 'REFUSE real native-store write'
pristine = UNIT.parent / 'unit_2008/TEST_projects/_pristine'
out = UNIT / ('TEST_' + tag)
out.mkdir()
review, package, key_run, key_package = (str(out / n) for n in
                                        ('review', 'review_package', 'key_run', 'key_package'))
checks = []


def check(name, ok):
    print('PASS' if ok else 'FAIL', name, flush=True)
    checks.append(name)
    assert ok, name


old, old_stage = R.old_readings()
R.build(package)
prep = R.prepare_run(review, package)
check('the public preparation schedules only four clarified reviews',
      prep['ok'] and len(prep['invocations']) == 4)
with R._current_scope():
    for n, inv in enumerate(prep['invocations']):
        path = SYN.write_state(CL, review, package, inv['label'],
                               'wf_TEST_join_' + tag + '_review_%03d' % n,
                               str(pristine), str(projects))
        assert not CL.record_state(review, path)
fin = R.finalize(review, package)
check('actual native closeout proves four TEST replies',
      fin['primary_complete'] and fin['ledger']['valid'] == 4
      and not fin['retry'] and not fin['problems'])
merged, stages = R.merged_readings(review, package)
check('full66 review obligations served, all old62 byte-identical',
      len(merged) == 66 and all(v[0] == 'valid' for v in merged.values())
      and all(merged[label] == value for label, value in old.items() if value[0] == 'valid'))
with R.final_scope(review, package) as proof:
    doc = SK.build(key_package)
    problems = SK.package_problems(key_package)
    prep = SK.prepare_run(key_run, package=key_package)
    check('actual final-key package and callable preparation',
          not problems and prep['ok'] and len(prep['invocations']) == 33)
    check('both real review stages bound and every call counted once',
          doc['hard_review']['stages'] == stages and doc['budget']['before'] == 499)
    check('two independent review leads per source, no omitted or foreign lead',
          len(proof['by_source']) == 33
          and all(len(leads) == 2 for leads in proof['by_source'].values())
          and all(SK.payload(task)['leads'] == proof['by_source'][task['source_id']]
                  for task in SK.tasks()))
    for n, inv in enumerate(prep['invocations']):
        path = SYN.write_final_state(
            CL, key_run, key_package, inv['label'],
            'wf_TEST_join_' + tag + '_final_%03d' % n, str(projects), proof['by_source'],
            script_path=inv['scriptPath'], resolve_open_issues=True)
        assert not SK.record_state(key_run, path)
    final = SK.finalize(key_run, package=key_package)
    check('actual finalizer retains all33 TEST adjudications',
          final['ledger']['valid'] == 33 and not final['retry'] and not final['problems'])
with R.final_scope(review, package):
    resumed = SK.resume_plan(key_run, package=key_package)
    shards, raws, bad = SK.accepted_shards(key_run, package=key_package)
    key, sidecar, materialize_bad = SK.materialize(shards)
    counts = SK.counts(key, sidecar)
    check('real resume preserves every success and owes no repeated call',
          not resumed['owed'] and not resumed['problems'] and not bad
          and len(resumed['served']) == len(resumed['never_repeat']) == len(shards) == 33)
    check('materializer accounts for all191 rows',
          not materialize_bad and counts['rows_accounted'] == 191)
with R.final_scope(review, package, bind_role=True):
    bound = SK.bound(key_run, key_package)
    gate = R.F.signing_gate(key_run, bound)
    check('existing signing gate accepts the complete TEST key', gate['ok'])
ordinary = out / 'ordinary_bound.json'
R.RT.write_new(str(ordinary), json.dumps({f: getattr(bound, f) for f in
                        ('package', 'evidence', 'hr', 'events', 'hr_package')}))
os.environ['A7_ORDINARY_BOUND'] = str(ordinary)
candidate = out / 'candidate'
with R.candidate_scope(review, package, key_run, key_package) as C:
    hashes, full_counts, candidate_counts, signer_manifest = C.build(str(candidate))
    check('existing artifact builder and full verifier accept', not C.verify(str(candidate)))
    identity = json.loads((candidate / 'key_identity.json').read_text())
    actual_runs = [CL.INITIAL_RUN, R.OLD_RUN, os.path.join(R.OLD_RUN, 'retry'), review, key_run]
    check('every actual stage is bound once, no invented history',
          len(identity['runs']) == len(set(identity['runs'])) == len(actual_runs)
          and set(identity['runs']) == set(actual_runs))
    check('every receipt and finalization present with exact bytes', all(
        any(row['path'] == str(Path(run, filename)) and row['sha256'] ==
            hashlib.sha256(Path(run, filename).read_bytes()).hexdigest()
            for row in identity['bindings'].values())
        for run in actual_runs for filename in (K.RECEIPT_NAME, K.FINALIZATION_NAME)))
    check('candidate retains original source-key binding for saved-answer grading',
          identity['bindings']['initial_source_package']['path'] ==
          os.path.join(SK.PKG_DIR, SK.MANIFEST_NAME))
    check('signer budget counts all532 TEST/history calls once',
          signer_manifest['budget']['before'] == 382 + 33 + 66 + 14 + 4 + 33)
R.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind':'TEST ONLY; no model calls or factual key approval', 'model_calls':0,
    'checks':checks, 'passed':len(checks), 'review':review, 'review_package':package,
    'key_run':key_run, 'key_package':key_package, 'ordinary':str(ordinary),
    'candidate':str(candidate), 'signer_manifest':signer_manifest,
}, indent=1))
print('COMPLETE', len(checks), 'checks; zero AI calls; TEST output', out)
