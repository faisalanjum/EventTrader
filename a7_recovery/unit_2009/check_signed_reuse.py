"""One TEST signature, real compact lock, and unchanged382-answer handoff.

Reuses the completed four TEST reviews and33 TEST adjudications. No AI call.
"""
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
saved = json.loads((UNIT / 'TEST_codex_join2009_a/TEST_RESULT.json').read_text())
os.environ.pop('A7_APPROVED_KEY_DIR', None)
os.environ['A7_ORDINARY_BOUND'] = saved['ordinary']
sys.path.insert(0, str(UNIT / 'owner'))
import a4_review_composite as R
CL, K = R.CL, R.K
sys.path.insert(0, str(UNIT.parent / 'unit_2001/tests'))
import synthetic_reading as SYN
owners = UNIT.parent / 'unit_1955/lock_owners'
sys.path.insert(0, str(owners))
import signer_proof as SP

projects = Path('/home/faisal/.claude/projects')
assert os.path.samefile(projects, UNIT / 'integration_a/projects'), 'REFUSE live store'
tag = os.environ['A7_TAG']
out = UNIT / ('TEST_' + tag)
out.mkdir()
checks = []


def check(name, ok):
    print('PASS' if ok else 'FAIL', name, flush=True)
    assert ok, name
    checks.append(name)


def exits_zero(fn):
    try:
        fn()
    except SystemExit as exc:
        assert exc.code == 0, exc.code


with R.candidate_scope(saved['review'], saved['review_package'],
                       saved['key_run'], saved['key_package']) as C:
    candidate = Path(saved['candidate'])
    sig = candidate / 'signer'
    manifest = saved['signer_manifest']
    prompt = (sig / 'signer_prompt.txt').read_text()
    script_path = sig / 'final_sign.attempt1.js'
    script = script_path.read_text()
    run_id = 'wf_TEST_signature_' + tag
    session = projects / '-home-faisal-EventMarketDB' / K.PARENT_SESSION
    bound = CL.SK.bound(saved['key_run'], saved['key_package'])
    sig_scripts = sig / 'scripts'
    sig_scripts.mkdir(exist_ok=True)
    if not (sig_scripts / 'TEST_native_script.js').exists():
        CL.RT.write_new(str(sig_scripts / 'TEST_native_script.js'), script)
    # Native fixture only; the production proof/packet/lock owners are not patched.
    if not (session / 'workflows' / (run_id + '.json')).exists():
        initial = K._load(os.path.join(CL.INITIAL_RUN, K.RECEIPT_NAME))
        template = Path(initial['states'][0]).name
        listdir = os.listdir

        def key_template(path):
            # Only the fixture's template selection is narrowed. A mixed store
            # also has Sonnet review states; they cannot model the key signer.
            return [template] if Path(path) == session / 'workflows' else listdir(path)

        with patch.object(CL.F, 'signer_script', return_value=script), \
                patch.object(CL.F, '_signer_context', return_value=(prompt, script)), \
                patch.object(SYN.os, 'listdir', side_effect=key_template):
            SYN.write_signature_state(CL, str(sig), bound, SP.LABEL, run_id, str(projects),
                row={'model':K.ROW_MODEL_ID, 'agentType':K.AGENT_TYPE},
                result={'model':K.MODEL, 'effort':K.EFFORT, 'agentType':K.AGENT_TYPE},
                state={'scriptPath':str(script_path)})
    proof, bad = SP.prove(str(sig), manifest, 1, run_id, str(session), {})
    check('actual native proof accepts the explicit TEST signature',
          not bad and proof['outcome'] == 'signed' and 'establishes no source truth' in proof['_text'])
    env = {'A7_CANDIDATE_DIR':str(candidate), 'A7_ORDINARY_BOUND':saved['ordinary'],
           'A7_SIGNER_SESSION':str(session),
           'A7_AUTHORITY':'/home/faisal/.core827-orchestrator/archive_CODEX_2011.md'}
    with patch.dict(os.environ, env), patch.object(sys, 'argv',
            [str(owners / 'harvest_final_sign.py'), run_id, '1']):
        exits_zero(lambda: runpy.run_path(str(owners / 'harvest_final_sign.py'), run_name='__main__'))
        check('the saved signature is reused and cannot launch again',
              SP.select_saved_call(str(sig), manifest, 1, str(session)) == ('reuse', run_id, None))
        spec = importlib.util.spec_from_file_location('test_join_lock', owners / 'build_final_key_lock.py')
        L = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(L)
        exits_zero(L.main)
        lock = json.loads(Path(L.LOCK).read_text())
        receipt = json.loads(Path(L.RECEIPT).read_text())
        check('actual compact lock and every existing bound-value mutation validate',
              not L.verify(lock) and receipt['every_bound_value_refuses_when_mutated']
              and not receipt['verify_problems_on_the_live_bytes'])
        check('history plus one TEST signer is exactly533 calls, counted once',
              lock['call_accounting']['signer_calls'] == 1
              and lock['call_accounting']['ledger_after'] == 533)
CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind':'TEST ONLY; real original answers but no factual key approval or model call',
    'model_calls':0, 'passed':len(checks), 'checks':checks, 'candidate':str(candidate),
    'lock_sha256':CL.INV.sha_file(str(candidate / 'a4_final_key_lock.json')),
    'receipt_sha256':CL.INV.sha_file(str(candidate / 'a4_final_key_lock_receipt.json')),
}, indent=1))
print('COMPLETE', len(checks), 'checks; zero AI calls', out)
