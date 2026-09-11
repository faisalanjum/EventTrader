"""All evaluation blocks, CLI selection, and source-descriptor boundaries.

The positive is the complete saved-answer TEST path. Mutants get fresh TEST
directories and external hashes; not one original artifact is altered.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

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

source = UNIT / 'TEST_codex_reuse_pipeline2006_c'
frozen = json.loads((source / A6.REUSE_FREEZE_NAME).read_text())
pin = CL.INV.sha_file(str(source / A6.REUSE_FREEZE_NAME))
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
scorer = Path(G.__file__).parent / 'scorers/score_exp5_current.py'
B.bind_grading_scorer(str(scorer), CL.INV.sha_file(str(scorer)))
results = []


def refusal(name, action):
    try:
        action()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        results.append({'case': name, 'refused': True, 'reason': str(exc)})
    else:
        results.append({'case': name, 'refused': False})


with SC.candidate_scope(saved['review_run'], saved['review_package'],
                        saved['key_run'], saved['key_package']):
    run = PR.reuse(str(source), pin)
    assert PR.cli_run(['--run', str(source), '--expect-freeze', pin]) == run
    assert PR.cli_run(['--run=' + str(source), '--expect-freeze=' + pin]) == run
    assert G.run_of(run) == run['run_dir']
    for field in frozen:
        mutant = copy.deepcopy(frozen)
        del mutant[field]
        dest = out / ('missing_' + field)
        dest.mkdir()
        rendered = A6.render(mutant)
        CL.RT.write_new(str(dest / A6.REUSE_FREEZE_NAME), rendered)
        refusal('missing evaluation block/' + field,
                lambda: PR.reuse(str(dest), hashlib.sha256(rendered.encode()).hexdigest()))
    for field, value in [('contract_suffix', 'TEST foreign instructions'),
                         ('reused_calls', frozen['reused_calls'] - 1),
                         ('armed_grader_calls', 1), ('database_writes', 1),
                         ('activated', True)]:
        mutant = copy.deepcopy(frozen)
        mutant[field] = value
        dest = out / ('changed_' + field)
        dest.mkdir()
        rendered = A6.render(mutant)
        CL.RT.write_new(str(dest / A6.REUSE_FREEZE_NAME), rendered)
        refusal('changed evaluation value/' + field,
                lambda: PR.reuse(str(dest), hashlib.sha256(rendered.encode()).hexdigest()))
    refusal('CLI cannot choose a different freeze',
            lambda: PR.cli_run(['--run', str(source), '--expect-freeze', '0' * 64]))
    refusal('CLI cannot omit the freeze', lambda: PR.cli_run(['--run', str(source)]))
    inputs = B.load_verified_inputs(CL.SK.PLAN_PATH, run, str(Path(G.__file__).parents[5]))
    sid = next(iter(inputs['rows']))
    context = B.verified_event_context(inputs, sid, run)
    for field in inputs:
        changed = copy.deepcopy(inputs)
        if field == 'rows':
            changed[field].pop(sid)
        else:
            changed[field] = str(out / 'not_the_producer_input')
        refusal('changed context descriptor/' + field,
                lambda: B.verified_event_context(changed, sid, run))
    assert B.verified_event_context(inputs, sid, run) == context
    assert PR.reuse(str(source), pin) == run
    assert PR._executed(run['run_dir']) == run['executed']
CL.RT.write_new(str(out / 'RESULTS.json'), json.dumps(results, indent=1))
print(json.dumps({'negative_cases': len(results),
                  'refused': sum(r['refused'] for r in results),
                  'unexpected_accepts': [r for r in results if not r['refused']],
                  'positive_controls': 'both CLI forms, original input before/after, original run digest'}, indent=1))
assert all(r['refused'] for r in results), 'a mutated binding was accepted'
