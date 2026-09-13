"""Persist the proved original signer and lock the unchanged real candidate.

Existing owners own every proof and write. This caller supplies the saved
role, historical input scopes, recovery, complete round history and authority.
"""
import importlib.util
import json
import os
import runpy
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
build = Path(os.environ['A7_REAL_CANDIDATE_BUILD'])
result = json.loads((build / 'RESULT.json').read_text())
packet = Path(result['packet'])
saved = json.loads((packet / 'FINDINGS_BY_EVENT.json').read_text())
spec = json.loads((packet / 'PACKET.json').read_text())
candidate = result['notes']['candidate']
os.environ['A7_CANDIDATE_DIR'] = candidate
os.environ['A7_ORDINARY_BOUND'] = result['notes']['ordinary']
mode = os.environ.get('A7_FINAL_LOCK_MODE', 'lock')
assert mode in ('lock', 'verify'), mode
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2053_owner_retry',
            'unit_2061_settlement_connection', 'unit_2065_closeout_connection',
            'unit_2068_input_recovery', 'unit_2076_latest_source_decisions'):
    sys.path.insert(0, str(A7 / rel))
import a4_review_composite as R
import a4_source_correction as C2023
import a4_source_decision as D
import a4_source_recovery as RECOV
import a4_source_settlement as S
import a4_source_closeout as V
import a4_phase_input as N
import a4_v6_successor_chain as X

F, K, SK = R.F, R.K, R.SK
sha = lambda p: R.INV.sha_file(str(p))
inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                            'settlement_by_event', 'closeout_by_event')]
chain = tuple((r, f) for r, f in saved['chain'])
phase = K._load(saved['phase_input_binding'])
carrier = K._load(phase['input_binding'])
owners = A7 / 'unit_1955/lock_owners'
assert sha(os.environ['A7_AUTHORITY']) == '747423cd8982530aea76601801c107fa2673284b406db81e7a55d66a02fa0fcd'


@F._operation
def main():
    assert all(sha(p) == h for p, h in spec['dependencies'].items())
    with R.candidate_scope(saved['review_run'], saved['review_package'],
                           saved['run'], carrier['package']) as C, \
            N.input_scope(saved['phase_input_binding']):
        assert Path(C.__file__).resolve() == A7 / 'unit_2005/owner/build_final_key_candidate.py'
        corrected = C2023.bind(SK.bound(saved['run'], carrier['package']), saved['corrections'])
        closed = V.bind(S.bind(D.bind(corrected, saved['decision']),
                               saved['settlement']), phase['run'])
        bound = X.bind(closed, saved['third_round'])
        with RECOV.recovery_scope(saved['recovery'], corrected, inputs[0]), \
                X.successor_scope(bound, saved['third_by_event'], chain[-1][0],
                                  chain[-1][1], inputs, chain[:-1]):
            sys.path.insert(0, str(owners))
            import signer_proof as SP
            manifest = K._load(str(Path(candidate) / 'signer/signer.manifest.json'))
            proof, bad = SP.prove(str(Path(candidate) / 'signer'), manifest, 1,
                                 'wf_cf398299-777', os.environ['A7_SIGNER_SESSION'], {})
            assert not bad and proof['outcome'] == 'signed', bad
            rows = [r for r in SP.AUD._jsonl(proof['transcript_path']) if r.get('type') == 'assistant']
            current = ({proof['run_id']}, {proof['agent_id']},
                       {r['message']['id'] for r in rows}, {r['requestId'] for r in rows})
            identity = K._load(str(Path(candidate) / 'key_identity.json'))
            prior = sorted(set(identity['runs']) | set(F._prior_runs(
                str(Path(candidate) / 'signer'), bound, {'phase': 'signer'})))
            totals = [set() for _ in current]
            for run in prior:
                for target, values in zip(totals, F._spent_identities(run)):
                    target.update(values)
            assert all(totals) and all(current)
            assert all(not (old & new) for old, new in zip(totals, current))
            print(json.dumps({'prior_key_runs': len(prior),
                              'prior_native_identity_counts': [len(s) for s in totals],
                              'signer_collisions': [len(a & b) for a, b in zip(totals, current)]}), flush=True)
            if mode == 'lock':
                original_argv = sys.argv
                try:
                    sys.argv = [str(owners / 'harvest_final_sign.py'), proof['run_id'], '1']
                    try:
                        runpy.run_path(sys.argv[0], run_name='__main__')
                    except SystemExit as exc:
                        assert exc.code == 0, exc.code
                finally:
                    sys.argv = original_argv
            module_spec = importlib.util.spec_from_file_location('a7_real_lock_2084', owners / 'build_final_key_lock.py')
            L = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(L)
            assert sys.modules['build_final_key_candidate'] is C
            if mode == 'lock':
                try:
                    L.main()
                except SystemExit as exc:
                    assert exc.code == 0, exc.code
            lock, receipt = K._load(L.LOCK), K._load(L.RECEIPT)
            assert not L.verify(lock)
            assert receipt['lock_sha256'] == sha(L.LOCK)
            assert receipt['every_bound_value_refuses_when_mutated'] is True
            assert not receipt['verify_problems_on_the_live_bytes']
            assert lock['signer']['run_id'] == proof['run_id']
            assert lock['call_accounting']['ledger_before'] == 667
            assert lock['call_accounting']['ledger_after'] == 668
            print(json.dumps({'mode': mode, 'model_calls': 0, 'lock': L.LOCK,
                              'lock_sha256': sha(L.LOCK), 'receipt_sha256': sha(L.RECEIPT),
                              'candidate_sha256': sha(Path(candidate) / 'key_identity.json'),
                              'mutations': len(receipt['mutations']), 'counts': lock['counts']}, indent=1), flush=True)


main()
