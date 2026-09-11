"""Complete all grading stages over the saved producer using TEST judgments.

Uses the existing faithful native-state test writer, public capture/finalizers,
no-write route and official scoring entry. No model is called and no TEST
judgment is a claim about the real answers' meaning or readiness of the key.
"""
import collections
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
import a7_g23_build as B
import a7_g23_run as R
import a7_reference_inventory as REF
import audit_worker_access as AUD
import g1_fake_state as FAKE
from driver.core import driver_write_cli as CLI

out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
preparation = UNIT / 'TEST_codex_reuse_pipeline2006_c'
prepped = json.loads((preparation / 'TEST_RESULT.json').read_text())
REF.INVENTORY_PATH = str(preparation / 'reference_inventory.json')
scorer = Path(G.__file__).parent / 'scorers/score_exp5_current.py'
B.bind_grading_scorer(str(scorer), CL.INV.sha_file(str(scorer)))
checks, route_calls = [], []
real_route = CLI.run_event


def check(name, condition):
    checks.append(dict(check=name, ok=bool(condition)))
    assert condition, name
    print(name, 'PASS', flush=True)


def no_write(*args, **kwargs):
    assert kwargs.get('enable_writes') is False
    route_calls.append(args[0]['source_id'])
    return real_route(*args, **kwargs)


with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']), \
        patch.object(CLI, 'run_event', side_effect=no_write):
    producer = PR.reuse(str(preparation), prepped['evaluation_sha256'])
    original = PR._executed(producer['run_dir'])
    inputs = B.load_verified_inputs(CL.SK.PLAN_PATH, producer, str(Path(G.__file__).parents[5]))
    candidate, problems = G.write(str(out / 'G1_candidate'), producer)
    check('the existing G1 owner publishes the saved-answer candidate', not problems)
    g1 = FAKE.complete_test_run('G1', out / 'G1_candidate', candidate,
                                out / 'G1_run', AUD.PROJECTS_ROOT)
    check('complete TEST G1 evidence passes its actual public lifecycle', bool(g1['pins']))
    doc, prompts, problems = R.freeze(producer, inputs=inputs, g1=g1,
                                      audit_root=str(out / 'prepare_route'))
    check('G2 and G3 freeze from that completed G1 and original source inputs', not problems)
    check('both later grading kinds have real derived TEST obligations',
          bool(doc['g2_pairs']) and bool(doc['g3_idxs']))
    identity = doc['key_identity']
    handles = {}
    for kind in ('G2', 'G3'):
        path, _digest = R.write_kind(str(out / (kind + '_candidate')), kind, doc, prompts, identity)
        completed = FAKE.complete_test_run(kind, out / (kind + '_candidate'), path,
                                           out / (kind + '_run'), AUD.PROJECTS_ROOT)
        handles[kind] = {key: completed[key] for key in (
            'candidate_dir', 'run_dir', 'root_sha256', 'completion_sha256')}
        check(kind + ' passes raw capture, native proof, completion and read-back', completed['lanes'] > 0)
    legs = ['P1', 'P2', G.LEG_UNION]
    by_leg = {leg: {kind: handles[kind] for kind, pop in (
                    ('G2', doc['g2_pairs']), ('G3', doc['g3_idxs']))
                   if any(key.split('|', 1)[0] == leg for key in pop)} for leg in legs}
    decisions, scores = B.official_tier_decision(producer, by_leg,
                                                str(out / 'score_route'), g1)
    check('the official scorer consumes all original arms and union',
          list(scores) == legs and all(value is not None for value in scores.values()))
    check('both public routing stages keep all99 event-arm routes, with writes disabled',
          len(route_calls) == 2 * prepped['route_calls'])
    check('original producer bytes and its full denominator are unchanged',
          PR._executed(producer['run_dir']) == original == prepped['original'])
    CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps(dict(
        kind='TEST judgments only; no real AI score', model_calls=0, passed=len(checks),
        checks=checks, producer=producer, g1=g1, completions=handles,
        g2_pairs=doc['g2_pairs'], g3_idxs=doc['g3_idxs'], decisions=decisions,
        scores=scores, route_calls=len(route_calls), original=original), indent=1))
print('Complete saved-answer TEST lifecycle passed; score arithmetic remains independently audited.')
