"""Cold verification of the saved REAL key candidate; no model call or lock.

The existing candidate owner re-derives its artifacts. A missing recovery
reference is then exercised at its real input reader, with valid controls.
Source/native inputs and the saved candidate remain unchanged throughout.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

A7 = Path(__file__).resolve().parents[1]
build = Path(os.environ['A7_REAL_CANDIDATE_BUILD'])
result = json.loads((build / 'RESULT.json').read_text())
packet = Path(result['packet'])
saved = json.loads((packet / 'FINDINGS_BY_EVENT.json').read_text())
spec = json.loads((packet / 'PACKET.json').read_text())
ordinary = result['notes']['ordinary']
candidate = result['notes']['candidate']
os.environ['A7_ORDINARY_BOUND'] = ordinary
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
checks = []


def check(name, condition, detail=None):
    print('PASS' if condition else 'FAIL', name, str(detail)[:400], flush=True)
    assert condition, (name, detail)
    checks.append(name)


@F._operation
def main():
    before = {str(p): sha(p) for p in Path(candidate).rglob('*') if p.is_file()}
    check('all frozen runtime dependencies match',
          all(sha(p) == h for p, h in spec['dependencies'].items()))
    check('ordinary data retains the saved recovery reference',
          K._load(ordinary)['recovery'] == saved['recovery'])
    with R.candidate_scope(saved['review_run'], saved['review_package'],
                           saved['run'], carrier['package']) as C, \
            N.input_scope(saved['phase_input_binding']):
        corrected = C2023.bind(SK.bound(saved['run'], carrier['package']),
                               saved['corrections'])
        closed = V.bind(S.bind(D.bind(corrected, saved['decision']),
                               saved['settlement']), phase['run'])
        bound = X.bind(closed, saved['third_round'])
        with RECOV.recovery_scope(saved['recovery'], corrected, inputs[0]), \
                X.successor_scope(bound, saved['third_by_event'], chain[-1][0],
                                  chain[-1][1], inputs, chain[:-1]):
            check('cold ordinary bound is the actual final bound', C._ordinary_bound() == bound)
            check('cold existing verifier reproduces every candidate byte', not C.verify(candidate))
            gate = F.signing_gate(bound.events, bound)
            check('actual key remains complete and clean', gate['ok'], gate['stops'])
            identity = K._load(os.path.join(candidate, 'key_identity.json'))
            provenance = K._load(os.path.join(candidate, 'provenance.json'))
            check('every actual source origin and raw hash is exact',
                  provenance['origins'] == gate['origins']
                  and set(provenance['provenance']['events']) == set(gate['raws'])
                  and all(provenance['provenance']['events'][sid]['raw_sha256'] == K._sha(raw)
                          for sid, raw in gate['raws'].items()))
            check('every bound history artifact matches live bytes',
                  all(sha(v['path']) == v['sha256'] for v in identity['bindings'].values()))
            recovered = RECOV.binding(saved['recovery'])[0]['recovery_run']
            expected_recovery = {
                'recovery_binding': saved['recovery'],
                'recovery_record': os.path.join(recovered, RECOV.RECORD_NAME),
                'recovery_receipt': os.path.join(recovered, K.RECEIPT_NAME),
                'recovery_finalization': os.path.join(recovered, K.FINALIZATION_NAME),
            }
            check('all recovered-stage evidence is explicitly bound',
                  recovered in identity['runs'] and all(
                      identity['bindings'][name]['path'] == path
                      for name, path in expected_recovery.items()))
            manifest_path = os.path.join(candidate, 'signer/signer.manifest.json')
            manifest = K._load(manifest_path)
            check('signer has the exact complete ordered raw population',
                  manifest['shards'] == [dict(shard=sid, sha256=K._sha(raw))
                                         for sid, raw in gate['raws'].items()])
            check('signer counts all actual completed calls once',
                  manifest['budget']['before'] == C.signer_ledger_before(bound)
                  == spec['ledger_after_proposed'])
            fields = C.BIR.approved_lane_input_fields()
            check('signer declares the actual current approved input',
                  bool(fields) and all(manifest.get(k) == v for k, v in fields.items()), fields)
            check('signer manifest record names the actual manifest',
                  result['notes']['signer']['manifest_sha256'] == sha(manifest_path))
            # Drop only the recovery declaration at the real metadata reader.
            # Source/native inputs are immutable, so operation caching remains valid.
            original_load = K._load

            def without_recovery(path, *args, **kwargs):
                value = original_load(path, *args, **kwargs)
                if os.path.abspath(path) == os.path.abspath(ordinary):
                    return {k: v for k, v in value.items() if k != 'recovery'}
                return value

            with patch.object(K, '_load', without_recovery):
                differences = C.verify(candidate)
            check('dropping recovery at the real reader cannot reproduce the saved candidate',
                  'key_identity.json' in differences and 'provenance.json' in differences,
                  differences)
            check('restoring the real reader reproduces every byte again', not C.verify(candidate))
    check('all saved candidate bytes are unchanged',
          {str(p): sha(p) for p in Path(candidate).rglob('*') if p.is_file()} == before)
    print(json.dumps({'build': str(build), 'passed': len(checks), 'checks': checks,
                      'candidate_sha256': sha(Path(candidate) / 'key_identity.json'),
                      'model_calls': 0, 'signature': False, 'lock': False}, indent=1))


main()
