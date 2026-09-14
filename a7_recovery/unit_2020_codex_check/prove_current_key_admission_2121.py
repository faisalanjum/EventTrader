"""Test the real current-key correction boundary; never call a model."""
import importlib.util
from importlib.machinery import SourceFileLoader
import copy
import json
import os
import sys
from pathlib import Path

import prepare_g23_partial_2097 as E

candidate = os.environ.get('A7_KEY_SUCCESSOR_CANDIDATE')
if candidate:
    assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
    spec = importlib.util.spec_from_file_location(
        'current_key_candidate_2121', candidate,
        loader=SourceFileLoader('current_key_candidate_2121', candidate))
    E.X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E.X)


def prove(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    bound = G._approved_bound()
    shards, raws, origins, bad = F.v6_shards(bound)
    assert not bad, bad
    provenance = G._read(str(Path(E.result['notes']['candidate']) / 'provenance.json'))
    assert origins == provenance['origins']
    assert all(K._sha(raws[sid]) == provenance['provenance']['events'][sid]['raw_sha256']
               for sid in raws)
    run = E.saved['third_round']
    phase, _phase_raws, bad = F.accepted_shards(run, bound, X.PHASE)
    assert not bad and phase, bad

    def findings(sid):
        return {sid: [{'source_id': sid, 'raw_sha256': K._sha(raws[sid]),
                       'row': F._task_by_label(bound.evidence, sid)['rows'][0]}]}

    def entries(doc):
        return X.successor_entries(bound, doc, run, E.saved['third_by_event'],
                                   E.source_inputs, E.chain)

    # Real positive control before the complete population, not a mock reader.
    control = sorted(phase)[0]
    assert entries(findings(control)) == [(control, findings(control)[control])]
    refused = []
    for sid in shards:
        try:
            assert entries(findings(sid)) == [(sid, findings(sid)[sid])]
        except ValueError as exc:
            refused.append({'source_id': sid, 'origin': origins[sid], 'error': str(exc)})
    report = {'model_calls': 0, 'current_key_sources': len(shards),
              'last_phase_sources': len(phase), 'positive_control': control,
              'refused_current_sources': refused,
              'owner_sha256': G._sha_file(X.__file__),
              'caller_sha256': G._sha_file(__file__)}
    G._write_new(str(E.out / 'CURRENT_KEY_ADMISSION.json'), G._pretty(report) + '\n')
    print(json.dumps(report, sort_keys=True), flush=True)
    assert not refused, 'current key entries must not be limited to the latest correction round'

    negatives = []

    def rejects(name, action):
        # Every rejection follows the real, unchanged positive control.
        assert entries(findings(control))
        try:
            action()
        except ValueError as exc:
            negatives.append({'case': name, 'reason': str(exc)})
        else:
            raise AssertionError('failed to reject ' + name)

    for field, value in [('source_id', 'not-a-current-source'),
                         ('raw_sha256', '0' * 64),
                         ('row', 'not-an-original-target')]:
        changed = copy.deepcopy(findings(control))
        changed[control][0][field] = value
        rejects(field, lambda: entries(changed))
    rejects('empty_findings', lambda: entries({}))
    rejects('empty_event_findings', lambda: entries({control: []}))
    unknown = {'not-a-current-source': findings(control)[control]}
    rejects('unknown_source', lambda: entries(unknown))
    original_key = X._F_V6_SHARDS

    def bad_key():
        with E.R._using(X, _F_V6_SHARDS=lambda _b: (shards, raws, origins, ['unproved history'])):
            X.first_round_key(bound, run, E.saved['third_by_event'], E.source_inputs, E.chain)

    rejects('unproved_key', bad_key)
    assert X._F_V6_SHARDS is original_key

    # Re-derive every completed round using its recorded inputs and exact
    # prompt hashes, not the new correction inputs.
    history = list(E.chain) + [(run, E.saved['third_by_event'])]
    historical = []
    for i, (prior_run, prior_findings) in enumerate(history):
        prior_bound = X.first_bound(bound, prior_run)
        with X.first_round_scope(bound, prior_run, prior_findings,
                                 E.source_inputs, tuple(history[:i])):
            receipt = K._load(os.path.join(prior_run, K.RECEIPT_NAME))
            actual = {sid: K._sha(F.v6_prompt(prior_bound, sid))
                      for sid in F.v6_labels(prior_bound)}
            assert actual == receipt['prompts'], prior_run
            assert F._receipt_still_the_proved_one(prior_run, prior_bound) == [], prior_run
        historical.append({'run': prior_run, 'prompts': len(actual),
                           'receipt_sha256': G._sha_file(os.path.join(prior_run, K.RECEIPT_NAME))})

    # This existing phase only corrects sources admitted in v5. Its two
    # original news entries remain in the complete key, not in this phase.
    v5_receipt = K._load(os.path.join(bound.decision_correction_v5, K.RECEIPT_NAME))
    supported = set(v5_receipt['allowed'])
    assert supported == set(F.v5_labels(bound))
    assert supported <= set(shards)
    all_findings = {sid: findings(sid)[sid] for sid in shards if sid in supported}
    next_bound = X.bind(bound, str(E.out / 'unrun_correction'))
    prompt_rows = []
    with X.successor_scope(next_bound, all_findings, run,
                           E.saved['third_by_event'], E.source_inputs, E.chain):
        assert F.v6_labels(next_bound) == list(all_findings)
        carried, carried_raws, carried_origins, bad = F.v5_shards(next_bound)
        assert not bad and carried == shards and carried_raws == raws and carried_origins == origins
        for sid in all_findings:
            text = F.v6_prompt(next_bound, sid)
            body = json.loads(text.split('[INPUT]\n', 1)[1])
            prior_key = X.PRIOR_KEY if origins[sid] == X.ORIGIN else 'prior_key_shard'
            prior_reply = body.pop(prior_key)
            assert prior_reply == {'origin': origins[sid] + '_reply',
                                   'sha256': K._sha(raws[sid]), 'raw': raws[sid]}
            finding = body.pop('reviewer_finding')
            assert finding['finding'] == all_findings[sid]
            expected = F.payload(next_bound, F._task_by_label(bound.evidence, sid))
            assert body == json.loads(json.dumps(expected)), sid
            prompt_rows.append({'source_id': sid, 'origin': origins[sid],
                                'prior_body_key': prior_key, 'prompt_sha256': K._sha(text)})
        before = F.v6_ledger_before(next_bound)
        prior_runs = F._prior_runs(str(E.out / 'unrun_correction'), next_bound, {'phase': X.PHASE})
        pins = F._phase_history(next_bound, X.PHASE)
    outside_phase = sorted(set(shards) - supported)
    for sid in outside_phase:
        with X.successor_scope(next_bound, findings(sid), run,
                               E.saved['third_by_event'], E.source_inputs, E.chain):
            try:
                F.v6_labels(next_bound)
            except ValueError as exc:
                assert 'v5 phase never corrected' in str(exc)
            else:
                raise AssertionError('the existing phase guard was weakened')
    report.update({'negative_controls': negatives, 'historical_rounds': historical,
                   'prompt_sources': prompt_rows, 'ledger_before': before,
                   'prior_runs': prior_runs, 'history_pin_tags': list(pins),
                   'carried_key_sources': len(carried),
                   'sources_outside_this_phase': outside_phase})
    G._write_new(str(E.out / 'CURRENT_KEY_BOUNDARY_PROOF.json'), G._pretty(report) + '\n')
    print('FULL_BOUNDARY', len(prompt_rows), len(negatives), len(historical), flush=True)

    # Read the completed signature with its existing native proof owner. The
    # source-key ledger must retain this call when a post-score correction is
    # eventually scheduled; a pre-signature count cannot stand in for it.
    sys.path.insert(0, str(E.A7 / 'unit_1955/lock_owners'))
    import signer_proof as SP
    signature_dir = Path(E.result['notes']['candidate']) / 'signer'
    signature_manifest = G._read(str(signature_dir / 'signer.manifest.json'))
    evidence = G._read(str(signature_dir / 'final_sign.attempt1.evidence.json'))
    seen_ids = {}
    with E.SK._key_role_binding():
        proof, problems = SP.prove(str(signature_dir), signature_manifest,
                                   evidence['attempt'], evidence['run_id'],
                                   str(Path(evidence['state_path']).parents[1]), seen_ids)
    assert not problems, problems
    assert not SP.disagreements(evidence, proof)
    assert proof['outcome'] == 'signed'
    diagnostic = {
        'scope': 'Post-signature accounting observation; no new call or approval',
        'source_key_ledger_before_next_round': before,
        'previous_signature_budget_before': signature_manifest['budget']['before'],
        'proved_completed_signature': proof['run_id'],
        'signature_evidence_sha256': G._sha_file(str(signature_dir / 'final_sign.attempt1.evidence.json')),
        'signature_is_in_prior_run_dirs': str(signature_dir) in prior_runs,
        'signature_has_legacy_spent_identity_counts': [len(s) for s in F._spent_identities(str(signature_dir))],
        'native_signature_identity_count': len(seen_ids),
        'history_pin_tags': list(pins),
        'model_calls': 0,
    }
    G._write_new(str(E.out / 'POST_SIGNATURE_ACCOUNTING_PROBE.json'), G._pretty(diagnostic) + '\n')
    print('POST_SIGNATURE_ACCOUNTING_PROBE', json.dumps(diagnostic, sort_keys=True), flush=True)


E.with_prepared_inputs(prove)
