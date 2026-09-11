"""TEST ONLY: source-only candidate -> native proof -> canonical compact lock.

No model is called. The runtime store must be the explicit TEST bind mount;
the fixture labels its answer as synthetic and proves no factual key accuracy.
"""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_source_candidate as SC
CL, C = SC.CL, SC.C
sys.path.insert(0, str(UNIT.parent / 'unit_2001/tests'))
import synthetic_reading as SYN

projects = Path('/home/faisal/.claude/projects')
test_projects = UNIT.parent / 'unit_2002/TEST_projects'
assert os.path.samefile(projects, test_projects), 'REFUSE any real runtime store write'
tag = os.environ['A7_TAG']
out = UNIT / ('TEST_' + tag)
out.mkdir()
base = Path(CL.PKG_DIR).parent
review, review_package, key_run, key_package = (str(base / n) for n in (
    'review_codex_final2002_qualified', 'closure_pkg_codex_final2002_qualified',
    'final_codex_final2002_qualified', 'final_pkg_codex_final2002_qualified'))
bound = CL.SK.bound(key_run, key_package)
ordinary = out / 'ordinary_bound.json'
CL.RT.write_new(str(ordinary), json.dumps({f: getattr(bound, f) for f in
                ('package', 'evidence', 'hr', 'events', 'hr_package')}))
C.ORDINARY = str(ordinary)
candidate = out / 'candidate'
owners = UNIT.parent / 'unit_1955/lock_owners'
sys.path.insert(0, str(owners))
import signer_proof as SP
assert Path(SP.__file__).resolve() == owners / 'signer_proof.py'
checks = []


def check(name, value):
    checks.append({'check': name, 'ok': bool(value)})
    assert value, name


def exits_zero(fn):
    try:
        fn()
    except SystemExit as exc:
        assert exc.code == 0, ('nonzero owner exit', exc.code)


with SC.candidate_scope(review, review_package, key_run, key_package):
    _hashes, _full, _counts, manifest = C.build(str(candidate))
    sig = candidate / 'signer'
    prompt = (sig / 'signer_prompt.txt').read_text()
    script_path = sig / 'final_sign.attempt1.js'
    script = script_path.read_text()
    (sig / 'scripts').mkdir()
    CL.RT.write_new(str(sig / 'scripts/TEST_native_script.js'), script)
    run_id = 'wf_TEST_signed_' + tag
    session = projects / '-home-faisal-EventMarketDB' / CL.K.PARENT_SESSION
    assert not (session / 'workflows' / (run_id + '.json')).exists()
    # Adapt only fixture generation to the canonical packet. Its real proof,
    # parser, candidate and lock owners below remain completely unmodified.
    with patch.object(CL.F, 'signer_script', return_value=script), \
            patch.object(CL.F, '_signer_context', return_value=(prompt, script)):
        native = SYN.write_signature_state(
            CL, str(sig), bound, SP.LABEL, run_id, str(projects),
            row={'model': CL.K.ROW_MODEL_ID, 'agentType': CL.K.AGENT_TYPE},
            result={'model': CL.K.MODEL, 'effort': CL.K.EFFORT,
                    'agentType': CL.K.AGENT_TYPE},
            state={'scriptPath': str(script_path)})
    proof, bad = SP.prove(str(sig), manifest, 1, run_id, str(session), {})
    check('canonical packet passes actual native proof', not bad)
    check('test signature cannot assert source truth',
          proof['outcome'] == 'signed' and 'establishes no source truth' in proof['_text'])

    # Mutate native identities, not the expected proof. Each negative case is
    # paired with a fresh proof of the restored original TEST bytes.
    original = Path(native).read_bytes()
    for field, value in (('runId', run_id + '_other'), ('script', script + '\n'),
                         ('status', 'failed'), ('totalToolCalls', 1)):
        mutated = json.loads(original)
        mutated[field] = value
        try:
            CL.RT._atomic_json(native, mutated)
            check('native mutation refuses: ' + field,
                  bool(SP.prove(str(sig), manifest, 1, run_id, str(session), {})[1]))
        finally:
            # TEST output restoration, never a source or live runtime record.
            Path(native).write_bytes(original)
        check('native positive restored: ' + field,
              not SP.prove(str(sig), manifest, 1, run_id, str(session), {})[1])

    env = {'A7_CANDIDATE_DIR': str(candidate), 'A7_ORDINARY_BOUND': str(ordinary),
           'A7_SIGNER_SESSION': str(session),
           'A7_AUTHORITY': '/home/faisal/.core827-orchestrator/archive_CODEX_2005.md'}
    with patch.dict(os.environ, env), patch.object(sys, 'argv',
            [str(owners / 'harvest_final_sign.py'), run_id, '1']):
        exits_zero(lambda: runpy.run_path(str(owners / 'harvest_final_sign.py'), run_name='__main__'))
        check('saved signature is reused, never relaunched',
              SP.select_saved_call(str(sig), manifest, 1, str(session)) == ('reuse', run_id, None))
        saved = {p.name: p.read_bytes() for p in sig.glob('final_sign.attempt1.*json')}
        exits_zero(lambda: runpy.run_path(str(owners / 'harvest_final_sign.py'), run_name='__main__'))
        check('harvest resume preserves every saved byte',
              saved == {p.name: p.read_bytes() for p in sig.glob('final_sign.attempt1.*json')})
        spec = importlib.util.spec_from_file_location('test_canonical_lock_2005', owners / 'build_final_key_lock.py')
        L = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(L)
        check('lock uses exact new candidate and old shared proof',
              sys.modules['build_final_key_candidate'] is C and L.SP is SP)
        exits_zero(L.main)
        lock = json.loads(Path(L.LOCK).read_text())
        receipt = json.loads(Path(L.RECEIPT).read_text())
        check('actual compact lock and receipt validate',
              not L.verify(lock) and receipt['every_bound_value_refuses_when_mutated']
              and not receipt['verify_problems_on_the_live_bytes'])
        check('all existing bound-value mutations refuse',
              bool(receipt['mutations']) and set(receipt['mutations'].values()) == {'refused'})
        check('one signer call is counted exactly once',
              lock['call_accounting']['signer_calls'] == 1
              and lock['call_accounting']['ledger_after'] == manifest['budget']['before'] + 1)

CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind': 'SYNTHETIC ONLY: no source truth, real approval or model call',
    'model_calls': 0, 'checks': checks, 'passed': len(checks),
    'ordinary': str(ordinary), 'candidate': str(candidate),
    'review_run': review, 'review_package': review_package,
    'key_run': key_run, 'key_package': key_package,
    'lock_sha256': CL.INV.sha_file(str(candidate / 'a4_final_key_lock.json')),
    'receipt_sha256': CL.INV.sha_file(str(candidate / 'a4_final_key_lock_receipt.json')),
}, indent=1))
print('TEST SIGNED CANDIDATE', len(checks), 'checks passed; zero model calls; output', out)
