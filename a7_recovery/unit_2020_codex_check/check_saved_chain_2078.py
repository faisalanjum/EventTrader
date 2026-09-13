"""Read-only independent checks of the two real predecessors and next inputs.

No model, receipt, raw, signature or key writes. Each mutation is a separate
operation; evidence is immutable inside the operation-scoped native cache.
This does not substitute for a completed TEST third-round consumer proof.
"""
import collections
import contextlib
import copy
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2053_owner_retry',
            'unit_2061_settlement_connection', 'unit_2065_closeout_connection',
            'unit_2068_input_recovery', 'unit_2069_targeted_source',
            'unit_2076_latest_source_decisions', 'unit_2005/owner'):
    sys.path.insert(0, str(A7 / rel))
import a4_review_composite as R
import a4_source_correction as C
import a4_source_decision as D
import a4_source_recovery as RECOV
import a4_source_settlement as S
import a4_source_closeout as V
import a4_phase_input as N
import a4_v6_successor_chain as X
import build_final_key_candidate as CAND

F, K, SK = R.F, R.K, R.SK
packet = A7 / 'unit_2072_two_event_closeout/packet_codex_succpkt2073_b'
saved = K._load(str(packet / 'FINDINGS_BY_EVENT.json'))
spec = K._load(str(packet / 'PACKET.json'))
findings = K._load(str(A7 / 'unit_2020_codex_check/SOURCE_FINDINGS_2076_v2.json'))['findings']
inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                            'settlement_by_event', 'closeout_by_event')]
run1, run2 = saved['first_round'], saved['successor']
find1, find2 = saved['first_round_by_event'], saved['successor_by_event']
prior = ((run1, find1),)
new_run = str(A7 / 'unit_2020_codex_check/NONEXISTENT_READ_ONLY_2078')
assert not os.path.exists(new_run)
owner_sha = R.INV.sha_file(X.__file__)
assert owner_sha == 'beed43091c4a5088f248122c3cf627ef82fd72cdbad7d9390863d1cb4ad558a7'
assert all(R.INV.sha_file(p) == h for p, h in spec['dependencies'].items())


@contextlib.contextmanager
def lane():
    with R.final_scope(saved['review_run'], saved['review_package'], bind_role=True), \
            N.input_scope(saved['phase_input_binding']):
        phase = K._load(saved['phase_input_binding'])
        carrier = K._load(phase['input_binding'])
        corrected = C.bind(SK.bound(saved['run'], carrier['package']), saved['corrections'])
        closed = V.bind(S.bind(D.bind(corrected, saved['decision']), saved['settlement']), phase['run'])
        with RECOV.recovery_scope(saved['recovery'], corrected, inputs[0]):
            yield X.bind(closed, new_run)


@F._operation
def positive():
    with lane() as bound:
        before_owner = F._prior_runs
        before_identity = F._prior_runs(new_run, bound, {'phase': X.PHASE})
        with X.successor_scope(bound, findings, run2, find2, inputs, prior):
            scripts = F.v6_scripts(bound)
            assert list(scripts) == list(findings) and len(scripts) == 2
            assert F.v6_ledger_before(bound) == CAND.signer_ledger_before(bound) == 665
            expected_raw = {sid: entries[0]['raw_sha256'] for sid, entries in findings.items()}
            for sid, script in scripts.items():
                body = json.loads(F.v6_prompt(bound, sid).split('[INPUT]\n', 1)[1])
                assert body[X.PRIOR_KEY]['sha256'] == expected_raw[sid]
                assert K._sha(body[X.PRIOR_KEY]['raw']) == expected_raw[sid]
                assert body['reviewer_finding']['finding'] == findings[sid]
                assert C.declared_keys(F.v6_prompt(bound, sid)) == list(body)
                assert len(script.encode()) < K.TRANSPORT_LIMIT
            merged, raws, origins, bad = F.v5_shards(bound)
            assert not bad and len(merged) == 33
            assert collections.Counter(origins.values())[X.ORIGIN] == 6
            for run, ff, chain in ((run1, find1, ()), (run2, find2, prior)):
                fb = X.first_bound(bound, run)
                with X.first_round_scope(bound, run, ff, inputs, chain):
                    assert not F._receipt_still_the_proved_one(run, fb)
            protected = {}
            for phase in (X.PHASE, 'signer'):
                dirs = F._prior_runs(new_run, bound, {'phase': phase})
                assert set(before_identity) <= set(dirs)
                for run in (run1, run2):
                    assert run in dirs and all(F._spent_identities(run))
                protected[phase] = dirs
            hist = F._phase_history(bound, X.PHASE)
            assert hist['v6'] == F._run_evidence_pins(run2)
            assert hist['v6_round1'] == F._run_evidence_pins(run1)
        assert F._prior_runs is before_owner
        assert F._prior_runs(new_run, bound, {'phase': X.PHASE}) == before_identity
    assert R.INV.sha_file(X.__file__) == owner_sha
    print(json.dumps({'positive': True, 'scripts': {k: K._sha(v) for k, v in scripts.items()},
                      'ledger_before': 665, 'sources': len(merged),
                      'prior_dirs': protected, 'owner_sha256': owner_sha}), flush=True)


@F._operation
def rejected(name, ff, chain):
    with lane() as bound:
        restored = F._prior_runs
        try:
            with X.successor_scope(bound, ff, run2, find2, inputs, chain):
                F.v6_scripts(bound)
        except (ValueError, OSError, KeyError) as exc:
            assert F._prior_runs is restored
            print(json.dumps({'mutation': name, 'refused': True,
                              'reason': str(exc)[:500]}), flush=True)
        else:
            raise AssertionError('mutation accepted: ' + name)


positive()
for field, value in (('raw_sha256', '0' * 64), ('source_id', 'wrong-source'),
                     ('row', 'wrong-row')):
    bad = copy.deepcopy(findings)
    bad[next(iter(bad))][0][field] = value
    rejected(field, bad, prior)
    positive()
rejected('missing saved predecessor chain', findings, ())
positive()
rejected('duplicate prior round', findings, prior + prior)
positive()
print('COMPLETE: 6 real positive controls; 5 separate-operation refusals; model/state writes 0', flush=True)
