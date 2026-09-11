"""TEST-key end-to-end preparation over all original paid answers, no AI.

Exercise the actual G1 question freeze, original source context and public
write-disabled route. Missing real grader judgments must remain unapproved.
"""
import collections
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
import a6_launch_freeze as A6
import a7_prepared_run as PR
import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as R
import a7_reference_inventory as REF
from driver.core import driver_write_cli as CLI

out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
scorer = Path(G.__file__).parent / 'scorers/score_exp5_current.py'
B.bind_grading_scorer(str(scorer), CL.INV.sha_file(str(scorer)))
checks = []


def check(name, ok):
    checks.append({'check': name, 'ok': bool(ok)})
    assert ok, name
    print(name, 'PASS', flush=True)


primary, _retry = CL.K.a3_run_dirs()
original = PR._executed(primary)
with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    frozen = A6.reuse_freeze(primary, os.path.join(CL.SK.PKG_DIR, CL.SK.MANIFEST_NAME))
    rendered = A6.render(frozen)
    pin = hashlib.sha256(rendered.encode()).hexdigest()
    CL.RT.write_new(str(out / A6.REUSE_FREEZE_NAME), rendered)
    run = PR.reuse(str(out), pin)
    # The existing reference owner derives the new key's exact source cards.
    # Do not reuse the previous key's file or add another reference reader.
    REF.INVENTORY_PATH = str(out / 'reference_inventory.json')
    reference = REF.expected_document(run)
    REF.write(reference)
    check('source cards are rebuilt and validated by the existing reference owner',
          len(REF.validate(run=run)) == reference['rows_total'])
    doc, prompts, problems = G.freeze(run)
    check('complete G1 question freeze has no missing identity or accounting', not problems)
    check('only the derived two blind readings per nonempty batch are planned',
          doc['launchers']['count'] == len(doc['batch_rows']) * len(G.GRADER_LANES)
          and doc['armed_calls'] == 0
          and doc['budget']['spent_before'] == frozen['budget']['completed_actual'])
    check('each question occurs in exactly one event batch',
          len(doc['question_bindings']) == len({r['question_id'] for r in doc['question_bindings']})
          == sum(r['items'] for r in doc['batch_rows']))
    rebuilt, rebuilt_prompts, rebuilt_bad = G.freeze(run)
    check('G1 rebuild is byte-identical', not rebuilt_bad and rebuilt == doc and rebuilt_prompts == prompts)
    inputs = B.load_verified_inputs(CL.SK.PLAN_PATH, run, str(Path(G.__file__).parents[5]))
    check('source context retains the original manifest identity',
          inputs['source_manifest_sha256'] == run['source_manifest_sha256']
          and 'a5_manifest_sha256' not in inputs)
    for event in CL.SK.plan()['events']:
        B.verified_event_context(inputs, event['source_id'], run)
    check('all original source contexts revalidate from their actual bytes', len(inputs['rows']) == 36)
    _legs, _totals, meta, arms, _gold, bad = G.inventory(run)
    check('both original arms and their union reach the existing matcher',
          not bad and list(arms) == ['P1', 'P2', G.LEG_UNION])
    groups = B.packet_groups(meta['trace'])
    route_calls = []
    real_run_event = CLI.run_event

    def no_write(*args, **kwargs):
        assert kwargs.get('enable_writes') is False
        route_calls.append(args[0]['source_id'])
        return real_run_event(*args, **kwargs)

    routes = {}
    with patch.object(CLI, 'run_event', side_effect=no_write):
        for leg, by_source in arms.items():
            audit = out / 'route' / leg
            audit.mkdir(parents=True)
            routes[leg] = B.route_for(by_source, str(audit), groups.get(leg))
    check('every event and leg reaches the real public no-write route once',
          len(route_calls) == sum(len(by) for by in arms.values())
          and all(set(routes[leg]) == set(arms[leg]) for leg in arms))
    g23, _prompts, bad = R.freeze(run, inputs=inputs, audit_root=str(out / 'not_armed'))
    check('final meaning/extras grading remains refused until real identity judgments exist',
          g23 is None and [r['reason'] for r in bad] == ['g1_lifecycle_required'])
    check('the source-key role does not alter the Sonnet grader role',
          G.LANE['model'] == 'sonnet' and G.LANE['runtime_model_id'] == 'claude-sonnet-5'
          and G.LANE['effort'] == 'high')
    check('every original answer byte remains unchanged', PR._executed(primary) == original)
    CL.RT.write_new(str(out / 'G1_TEST_candidate.json'), G._pretty(doc))
    CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
        'kind': 'TEST key, original paid answers, actual no-write route; no real grade',
        'passed': len(checks), 'checks': checks, 'model_calls': 0,
        'evaluation_sha256': pin, 'grader_questions': doc['questions'],
        'grader_batches': len(doc['batch_rows']), 'derived_grader_calls': doc['launchers']['count'],
        'route_calls': len(route_calls), 'original': original,
    }, indent=1))
print('TEST pipeline:', len(checks), 'checks passed; no AI or database writes')
