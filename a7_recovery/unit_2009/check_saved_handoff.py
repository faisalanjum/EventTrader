"""Completed TEST lock -> pinned approval -> actual382-answer grading handoff."""
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT / 'TEST_codex_join2009_a/TEST_RESULT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = saved['candidate']
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R
CL, K = R.CL, R.K
import a6_launch_freeze as A6
import a7_prepared_run as PR
import a7_g1_build as G

out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
checks = []


def check(name, ok):
    print('PASS' if ok else 'FAIL', name, flush=True)
    assert ok, name
    checks.append(name)


with R.candidate_scope(saved['review'], saved['review_package'],
                       saved['key_run'], saved['key_package']):
    primary, _ = K.a3_run_dirs()
    original = PR._executed(primary)
    frozen = A6.reuse_freeze(primary, os.path.join(CL.SK.PKG_DIR, CL.SK.MANIFEST_NAME))
    text = A6.render(frozen)
    pin = K._sha(text)
    CL.RT.write_new(str(out / A6.REUSE_FREEZE_NAME), text)
    run = PR.reuse(str(out), pin)
    arms, meta, problems = G.materialize(run)
    check('the new signed TEST key enters the actual saved-answer grading path', not problems)
    check('full36 events,191 packets,382 original answers with zero new producer calls',
          (meta['events'], meta['packets'], meta['answers']) == (36,191,382)
          and len(meta['trace']) == 382 and frozen['budget']['planned_producer_primary'] == 0)
    check('the signed533 baseline includes rather than re-adds the382 saved calls',
          frozen['budget']['completed_actual'] == meta['budget']['completed_actual'] == 533)
    check('all original answer bytes unchanged', PR._executed(primary) == original)
CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind':'TEST ONLY: no real approval or model calls', 'model_calls':0,
    'passed':len(checks), 'checks':checks, 'evaluation_sha256':pin, 'identity':run,
}, indent=1))
print('COMPLETE', len(checks), 'checks; zero AI calls', out)
