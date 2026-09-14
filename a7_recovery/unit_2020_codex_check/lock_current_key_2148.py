"""Prove/preserve one real signer and invoke the unchanged final-lock owner.

No model call. The original producer remains proved in its original context;
the shared current-key boundary supplies the new key and historical inputs.
The external source-preparation and native pins are required, not inferred.
"""
import json
import os
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2143_source_authority'))
from build_candidate_2148 import E
import a7_current_key_context_2148 as CURRENT


def lock(_producer, _inputs):
    G, K, F, X, R = E.G, E.K, E.F, E.X, E.R
    mode = os.environ.get('A7_FINAL_LOCK_MODE', 'lock')
    if mode not in ('lock', 'verify'):
        raise ValueError('unsupported final-lock mode')
    authority = os.environ['A7_AUTHORITY']
    assert G._sha_file(authority) == os.environ['A7_AUTHORITY_SHA256']
    preparation = os.environ['A7_CURRENT_KEY_PREPARATION']
    pin = os.environ['A7_CURRENT_KEY_PREPARATION_SHA256']
    run_id = os.environ['A7_SIGNER_RUN_ID']
    attempt = int(os.environ['A7_SIGNER_ATTEMPT'])
    owners = A7 / 'unit_1955/lock_owners'
    sys.path.insert(0, str(owners))
    import signer_proof as SP

    with CURRENT.current_key(E, preparation, pin) as (C, bound, prepared):
        candidate = Path(prepared['candidate'])
        sig = str(candidate / 'signer')
        manifest = K._load(str(candidate / 'signer/signer.manifest.json'))
        assert SP.K is K and R.SK.K is K
        assert not R.SK.role_problems()
        assert R.SK.key_transport() == manifest['transport']
        with R.SK._key_role_binding():
            proof, bad = SP.prove(sig, manifest, attempt, run_id,
                                  os.environ['A7_SIGNER_SESSION'], {})
        assert not bad, bad
        for name in ('state', 'transcript', 'raw'):
            assert proof[name + '_sha256'] == os.environ[
                'A7_SIGNER_' + name.upper() + '_SHA256'], name
        G._write_new(str(E.out / 'SIGNER_PROOF.json'), G._pretty({
            k: v for k, v in proof.items() if k != '_text'}) + '\n')
        assert proof['outcome'] == 'signed', proof['outcome']
        assert proof['_reply']['signed'] is True and proof['_reply']['blocked'] == []

        # The existing native proof and spent-identity owners, not copied
        # evidence readers, establish that this separate signer is independent.
        records = [r for r in SP.AUD._jsonl(proof['transcript_path'])
                   if r.get('type') == 'assistant']
        current = ({proof['run_id']}, {proof['agent_id']},
                   {r['message']['id'] for r in records},
                   {r['requestId'] for r in records})
        identity = K._load(str(candidate / 'key_identity.json'))
        prior = sorted(set(identity['runs']) | set(F._prior_runs(
            sig, bound, {'phase': 'signer'})))
        spent = [set() for _ in current]
        for run in prior:
            for target, values in zip(spent, F._spent_identities(run)):
                target.update(values)
        assert all(spent) and all(current)
        assert all(not (old & new) for old, new in zip(spent, current))
        print('Independent signer proved; no prior response identity reused', flush=True)

        # Historical verification can select its own candidate at import.
        # The harvest also selects at import, so explicitly serve THIS one.
        if mode == 'lock':
            os.environ['A7_CANDIDATE_DIR'] = str(candidate)
            previous_argv = sys.argv
            try:
                sys.argv = [str(owners / 'harvest_final_sign.py'), run_id, str(attempt)]
                with R.SK._key_role_binding():
                    try:
                        runpy.run_path(sys.argv[0], run_name='__main__')
                    except SystemExit as exc:
                        assert exc.code == 0, exc.code
            finally:
                sys.argv = previous_argv

        # Fresh after harvest, since the lock owner freezes its actual attempt
        # membership at import. Re-derive the candidate in its ordinary role
        # before native signature validation temporarily binds the signer role.
        L = X._lock_owner(str(candidate))
        L.AUTHORITY = authority
        assert sys.modules['build_final_key_candidate'] is C
        assert not L._candidate_problems(), L._candidate_problems()
        with R.SK._key_role_binding():
            if mode == 'lock':
                try:
                    L.main()
                except SystemExit as exc:
                    assert exc.code == 0, exc.code
            result, receipt = K._load(L.LOCK), K._load(L.RECEIPT)
            assert not L.verify(result)
        assert receipt['lock_sha256'] == G._sha_file(L.LOCK)
        assert receipt['every_bound_value_refuses_when_mutated'] is True
        assert not receipt['verify_problems_on_the_live_bytes']
        assert result['signer']['run_id'] == run_id
        assert result['counts'] == prepared['full_counts']
        accounting = result['call_accounting']
        assert accounting['ledger_before'] == prepared['signer_ledger_before']
        assert accounting['ledger_after'] == accounting['ledger_before'] + accounting['signer_calls']
        report = {
            'scope': 'Real current key signature/lock; no model call or grading score',
            'caller_sha256': G._sha_file(__file__),
            'context_sha256': G._sha_file(CURRENT.__file__),
            'mode': mode, 'preparation': preparation, 'preparation_sha256': pin,
            'candidate': str(candidate), 'ordinary': prepared['ordinary'],
            'ordinary_sha256': prepared['ordinary_sha256'],
            'lock': L.LOCK, 'lock_sha256': G._sha_file(L.LOCK),
            'receipt': L.RECEIPT, 'receipt_sha256': G._sha_file(L.RECEIPT),
            'candidate_identity_sha256': G._sha_file(candidate / 'key_identity.json'),
            'signer_proof_sha256': G._sha_file(str(E.out / 'SIGNER_PROOF.json')),
            'counts': result['counts'], 'call_accounting': accounting,
            'mutations': receipt['mutations'], 'prior_runs': prior,
            'prior_identity_counts': [len(s) for s in spent],
            'identity_collisions': [len(old & new) for old, new in zip(spent, current)],
            'model_calls': 0,
        }
        G._write_new(str(E.out / 'SIGNED_KEY.json'), G._pretty(report) + '\n')
        print('Current signed key locked and all recorded mutations refused', flush=True)
        return report


if __name__ == '__main__':
    E.with_prepared_inputs(lock)
