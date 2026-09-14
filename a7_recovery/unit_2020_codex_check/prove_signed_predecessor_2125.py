"""Cold-read the completed post-signature round before its next correction.

No AI call, no receipt/result rewrite. The actual completed round is the
positive control; its chronological signature context must survive resume.
"""
import collections
import copy
import importlib.util
import os
from importlib.machinery import SourceFileLoader

import prepare_g23_partial_2097 as E

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
spec = importlib.util.spec_from_file_location(
    'signed_predecessor_candidate_2125', candidate,
    loader=SourceFileLoader('signed_predecessor_candidate_2125', candidate))
E.X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E.X)

RUN = str(E.A7 / 'unit_2123_post_signature_key/core_recheck2123_h/recheck_packet')


def prove(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G

    def cold(action):
        # The real outer-operation boundary clears native proof caches.
        with E.R._using(F, _OP_DEPTH=[0]):
            return F._operation(action)()

    bound = G._approved_bound()
    request_path = str(E.A7 / 'unit_2020_codex_check/SOURCE_KEY_RECHECK_BINDINGS_2120.json')
    assert G._sha_file(request_path) == 'a97d16ba0895f6170e3f4ac5358152d7e4c987057b9c2bdf09c153513b964bb0'
    request = G._read(request_path)
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    findings = collections.OrderedDict()
    for event in sorted(request['source_events'], key=lambda e: order.index(e['source_id'])):
        findings[event['source_id']] = [collections.OrderedDict([
            ('source_id', event['source_id']),
            ('raw_sha256', event['prior_source_raw_sha256']), ('row', row)])
            for row in event['original_task_ids']]
    signed_key = E.result['notes']['candidate']
    signer = cold(lambda: X.signature_accounting(signed_key))
    prior = tuple(E.chain) + ((E.saved['third_round'], E.saved['third_by_event']),)
    own_bound = X.bind(bound, RUN)
    def original_context():
        with X.successor_scope(own_bound, findings, E.saved['third_round'],
                               E.saved['third_by_event'], E.source_inputs,
                               E.chain, signature=signed_key):
            actual = F.v6_shards(own_bound)
            assert not actual[3] and len(actual[0]) == 33, actual[3]
            assert F._receipt_still_the_proved_one(RUN, own_bound) == []
            return actual, F.v6_ledger_before(own_bound)

    actual, before = cold(original_context)
    assert before == 668
    # A cold read starts a NEW operation: the preceding intact control must
    # not donate accepted-shard cache entries to a different history scope.
    # Use the real operation owner; no transcript or result is changed.
    try:
        cold(lambda: X.first_round_key(
            bound, RUN, findings, E.source_inputs, prior))
    except ValueError as exc:
        omitted = str(exc)
    else:
        raise AssertionError('missing signature context silently admitted')
    observation = {'positive_sources': len(actual[0]),
                   'omitted_signature_refusal': omitted,
                   'owner_sha256': G._sha_file(X.__file__),
                   'caller_sha256': G._sha_file(__file__), 'model_calls': 0}
    G._write_new(str(E.out / 'SIGNED_PREDECESSOR_OBSERVATION.json'), G._pretty(observation) + '\n')
    print('SIGNED_PREDECESSOR_OBSERVATION', omitted, flush=True)

    signatures = {RUN: signed_key}
    recovered = cold(lambda: X.first_round_key(
        bound, RUN, findings, E.source_inputs, prior, signatures=signatures))
    assert recovered == actual
    accepted, accepted_raws = cold(lambda: X.first_round_accepted(
        bound, RUN, findings, E.source_inputs, prior, signatures=signatures))
    assert set(accepted) == set(findings)
    assert all(accepted_raws[sid] == actual[1][sid] for sid in findings)
    new_findings = collections.OrderedDict(
        (sid, [collections.OrderedDict([
            ('source_id', sid), ('raw_sha256', K._sha(actual[1][sid])),
            ('row', row)]) for row in F._task_by_label(bound.evidence, sid)['rows']])
        for sid in findings)
    next_bound = X.bind(bound, str(E.out / 'unrun_next'))
    with X.successor_scope(next_bound, new_findings, RUN, findings,
                           E.source_inputs, prior, signatures=signatures):
        assert F.v5_shards(next_bound) == actual
        assert F.v6_ledger_before(next_bound) == 670
        labels = F.v6_labels(next_bound)
        assert labels == list(new_findings)
        prompts = {sid: K._sha(F.v6_prompt(next_bound, sid)) for sid in labels}
        history = F._phase_history(next_bound, X.PHASE)
        prior_runs = F._prior_runs(next_bound.decision_correction_v6,
                                  next_bound, {'phase': X.PHASE})
        assert RUN in prior_runs
        assert str(E.A7 / 'unit_2081_final_key_candidate/codex_cand2082_a/candidate/signer') in prior_runs
        assert 'signature' in history
        assert F._spent_identities(signer.directory) == signer.identities
        assert all(len(ids) == 1 for ids in signer.identities)
        assert F._spent_identities(RUN) != signer.identities
    with X.first_round_scope(bound, RUN, findings, E.source_inputs, prior,
                             signatures=signatures):
        assert F._receipt_still_the_proved_one(RUN, own_bound) == []
        observed = {sid: K._sha(F.v6_prompt(own_bound, sid)) for sid in findings}
        assert observed == K._load(os.path.join(RUN, K.RECEIPT_NAME))['prompts']
    negatives = []

    def next_count(plan, *, latest_signature=None):
        with X.successor_scope(next_bound, new_findings, RUN, findings,
                               E.source_inputs, prior, signatures=plan,
                               signature=latest_signature):
            # Both admission and accounting must use the same history.
            assert F.v5_shards(next_bound) == actual
            return F.v6_ledger_before(next_bound)

    def refuses(name, action):
        # Real intact control, followed by a fresh negative operation: no
        # accepted result cache may hide a missing or misplaced signature.
        assert cold(lambda: next_count(signatures)) == 670
        try:
            cold(action)
        except ValueError as exc:
            negatives.append({'case': name, 'reason': str(exc)})
        else:
            raise AssertionError('did not refuse ' + name)

    refuses('omitted_signature', lambda: next_count({}))
    refuses('outside_history', lambda: next_count({'unrecorded-round': signed_key}))
    refuses('wrong_earlier_boundary', lambda: next_count({prior[-1][0]: signed_key}))
    refuses('wrong_later_boundary', lambda: next_count(
        {str(E.out / 'unrun_next'): signed_key}))
    refuses('same_signature_twice', lambda: next_count(
        {RUN: signed_key, str(E.out / 'unrun_next'): signed_key}))
    refuses('conflicting_shorthand', lambda: next_count(
        {str(E.out / 'unrun_next'): signed_key}, latest_signature='not-the-same-candidate'))

    wrong_findings = copy.deepcopy(new_findings)
    changed_source = next(iter(wrong_findings))
    wrong_findings[changed_source][0]['raw_sha256'] = '0' * 64
    refuses('stale_current_raw', lambda: X.successor_entries(
        next_bound, wrong_findings, RUN, findings, E.source_inputs, prior,
        signatures=signatures))
    # All historical phases keep their exact current/old prompt identities.
    historical = []
    for n, (run, row_findings) in enumerate(prior + ((RUN, findings),)):
        phase_bound = X.first_bound(bound, run)
        plan = signatures if run == RUN else {}
        with X.first_round_scope(bound, run, row_findings, E.source_inputs,
                                 prior[:n], signatures=plan):
            receipt = K._load(os.path.join(run, K.RECEIPT_NAME))
            current = {sid: K._sha(F.v6_prompt(phase_bound, sid))
                       for sid in F.v6_labels(phase_bound)}
            assert current == receipt['prompts']
            assert F._receipt_still_the_proved_one(run, phase_bound) == []
        historical.append({'run': run, 'prompts': current})
    observation.update({'cold_sources': len(recovered[0]), 'next_before': 670,
                        'next_prompt_hashes': prompts, 'history_keys': list(history),
                        'prior_runs': prior_runs, 'original_prompt_hashes': observed,
                        'negative_controls': negatives, 'historical_rounds': historical})
    G._write_new(str(E.out / 'SIGNED_PREDECESSOR_PROOF.json'), G._pretty(observation) + '\n')
    print('SIGNED_PREDECESSOR_PROVED', len(recovered[0]), len(prompts), 670, flush=True)


E.with_prepared_inputs(prove)
