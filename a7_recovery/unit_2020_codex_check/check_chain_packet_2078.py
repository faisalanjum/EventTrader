"""Cold read of the saved THIRD-round packet; no calls or state writes.

This independent check consumes the saved packet, not the preparer's in-memory
objects. It proves the two requests, original replies, history and accounting
at the real receipt/resume boundary. It does not approve source meaning.
"""
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
packet = Path(os.environ['A7_SUCCESSOR_PACKET'])
spec = K._load(str(packet / 'PACKET.json'))
saved = K._load(str(packet / 'FINDINGS_BY_EVENT.json'))
inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                            'settlement_by_event', 'closeout_by_event')]
findings = saved['third_by_event']
chain = tuple((r, f) for r, f in saved['chain'])
first, first_findings = chain[-1]
chain_prior = chain[:-1]
run = saved['third_round']
assert len(chain) == 2 and saved['predecessor'] == first
assert saved['predecessor_by_event'] == first_findings
checks = []
sha = lambda path: R.INV.sha_file(str(path))


def check(name, okay, detail=None):
    print('PASS' if okay else 'FAIL', name, str(detail)[:300], flush=True)
    assert okay, (name, detail)
    checks.append(name)


@F._operation
def main():
    check('packet and saved bindings name the same first round and phase',
          spec['phase'] == X.PHASE and spec['round'] == 3
          and spec['predecessor'] == first and spec['model_calls'] == 0
          and spec['chain'] == [r for r, f in chain])
    check('the exact reviewed source leads are saved, not reconstructed answers',
          sha(spec['findings_path']) == spec['findings_sha256']
          and K._load(spec['findings_path'])['findings'] == findings)
    check('every declared runtime module still matches its frozen bytes',
          all(sha(p) == h for p, h in spec['dependencies'].items()))
    check('the current successor owner and boundary map match this packet',
          sha(X.__file__) == spec['chain_owner_sha256']
          and sha(spec['boundary_map']) == spec['boundary_map_sha256'])
    with R.final_scope(saved['review_run'], saved['review_package'], bind_role=True), \
            N.input_scope(saved['phase_input_binding']):
        phase = K._load(saved['phase_input_binding'])
        carrier = K._load(phase['input_binding'])
        corrected = C.bind(SK.bound(saved['run'], carrier['package']),
                           saved['corrections'])
        closed = V.bind(S.bind(D.bind(corrected, saved['decision']),
                               saved['settlement']), phase['run'])
        with RECOV.recovery_scope(saved['recovery'], corrected, inputs[0]):
            with X.first_round_scope(closed, first, first_findings, inputs, chain_prior):
                fb = X.first_bound(closed, first)
                old, old_raw, old_origins, old_bad = F.v6_shards(fb)
                accounted = CAND.signer_ledger_before(fb)
                first_receipt = K._load(os.path.join(first, K.RECEIPT_NAME))
                first_final = K._load(os.path.join(first, K.FINALIZATION_NAME))
                check('the two predecessor replies and their earlier history still reconstruct',
                      not old_bad and len(first_receipt['allowed']) == 2
                      and first_final['ledger']['valid'] == 2
                      and not F._receipt_still_the_proved_one(first, fb))
            bound = X.bind(closed, run)
            before_prior = F._prior_runs
            baseline_prior = {phase_name: F._prior_runs(
                run, bound, {'phase': phase_name}) for phase_name in F.PHASES}
            with X.successor_scope(bound, findings, first, first_findings, inputs, chain_prior):
                receipt = K._load(os.path.join(run, K.RECEIPT_NAME))
                check('the real uncalled receipt resumes from saved inputs',
                      not F.receipt_problems(run, bound, receipt)
                      and not F._receipt_still_the_proved_one(run, bound))
                check('the two requests are uncalled, with nothing finalized',
                      not receipt['states']
                      and not os.path.exists(os.path.join(run, K.FINALIZATION_NAME))
                      and receipt['allowed'] == list(findings)
                      and len(receipt['allowed']) == 2)
                check('the receipt pins the exact first-round history',
                      receipt['v1_evidence']['v6'] == F._run_evidence_pins(first)
                      and receipt['v1_evidence']['v6_round1']
                      == F._run_evidence_pins(chain[0][0]))
                check('all previous calls are counted once before these two',
                      F.v6_ledger_before(bound) == accounted == spec['ledger_before']
                      and CAND.signer_ledger_before(bound) == accounted,
                      accounted)
                scripts = F.v6_scripts(bound)
                measured = {e['source_id']: e for e in spec['events']}
                check('the independently derived request set equals the saved set',
                      list(scripts) == list(measured) == receipt['allowed'])
                for sid, script in scripts.items():
                    event = measured[sid]
                    prompt = F.v6_prompt(bound, sid)
                    body = json.loads(prompt.split('[INPUT]\n', 1)[1])
                    check('cold prompt, script, source and prior reply: ' + sid,
                          K._sha(prompt) == event['prompt_sha256']
                          == receipt['prompts'][sid]
                          and K._sha(script) == event['script_sha256']
                          == sha(event['script_path'])
                          and script == Path(event['script_path']).read_text()
                          and len(script.encode()) == event['script_bytes']
                          and len(script.encode()) < K.TRANSPORT_LIMIT
                          and C.declared_keys(prompt) == list(body)
                          and 'v5_shard' not in body
                          and body['v6_shard']['raw'] == old_raw[sid]
                          and body['v6_shard']['sha256'] == K._sha(old_raw[sid])
                          == event['prior_raw_sha256']
                          and body['reviewer_finding']['finding'] == findings[sid])
                base, base_raw, origins, bad = F.v5_shards(bound)
                check('the complete 33-source merge base is byte-identical',
                      not bad and len(base) == 33 and base == old
                      and base_raw == old_raw and origins == old_origins)
                key, sidecar, problems = F.materialize(bound.evidence, base)
                counts = F.counts(key, sidecar)
                check('all 191 rows remain accounted for, with the one recorded open issue',
                      not problems and counts['rows_accounted'] == 191
                      and counts['open_issues'] == 1, counts)
                pending, pending_bad = F.run_evidence(run, bound, receipt)
                missing = set(receipt['allowed']) - set(pending)
                check('the real proof owner credits no answer; both remain missing',
                      not pending_bad and not pending and missing == set(scripts),
                      {'proved': len(pending), 'missing': sorted(missing)})
                first_ids = F._spent_identities(first)
                check('the immediate predecessor has two real run and agent identities',
                      len(first_ids[0]) == len(first_ids[1]) == 2,
                      [len(v) for v in first_ids])
                for phase_name, baseline in baseline_prior.items():
                    got = F._prior_runs(run, bound, {'phase': phase_name})
                    expected = list(baseline)
                    if phase_name in (X.PHASE, 'signer'):
                        for prior_run in (p for r, f in chain for p in (r, os.path.join(r, 'retry'))):
                            if os.path.isdir(prior_run) and prior_run not in expected:
                                expected.append(prior_run)
                    check('all older identity protection stays intact: ' + phase_name,
                          got == expected, {'before': len(baseline), 'after': len(got)})
                for phase_name in (X.PHASE, 'signer'):
                    prior = F._prior_runs(run, bound, dict(receipt, phase=phase_name))
                    spent = [set() for _ in first_ids]
                    for prior_run in prior:
                        for union, values in zip(spent, F._spent_identities(prior_run)):
                            union.update(values)
                    check('prior identity protection includes the first round: ' + phase_name,
                          first in prior and all(a <= b for a, b in zip(first_ids, spent)),
                          {'first_round_in_prior_runs': first in prior,
                           'omitted_id_counts': [len(a - b) for a, b in zip(first_ids, spent)]})
            check('the outer recovery identity owner is restored on exit',
                  F._prior_runs is before_prior)
    print(json.dumps({'packet': str(packet), 'packet_sha256': sha(packet / 'PACKET.json'),
                      'owner_sha256': sha(X.__file__), 'passed': len(checks),
                      'checks': checks, 'model_calls': 0,
                      'limitation': 'Source decisions, real signature and grading are not established.'}, indent=1))


main()
