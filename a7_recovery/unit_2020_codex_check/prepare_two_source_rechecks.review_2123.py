"""Prepare the TWO source-key rechecks through the existing owners.

Codex SEQ 2122. One durable pre-call packet for exactly the two original
events the frozen bindings name, built by F's OWN `prepare_v6` under the
successor scope, with the completed signature accounted for through its own
published-lock owner. It calls no model, signs nothing, publishes no key and
finalizes no run: the packet is armed and left unrun.

Everything the packet is made of is proved here, and every negative control
runs only after the real positive control it is the negative of.
"""
import collections
import copy
import importlib.util
import json
import os
import shutil
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

# the existing real harness, where the tree already keeps it
sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E                              # noqa: E402

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
_spec = importlib.util.spec_from_file_location(
    'current_key_candidate_2123', candidate,
    loader=SourceFileLoader('current_key_candidate_2123', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

BINDINGS = str(E.A7 / 'unit_2020_codex_check'
               / 'SOURCE_KEY_RECHECK_BINDINGS_2120.json')
BINDINGS_SHA256 = 'a97d16ba0895f6170e3f4ac5358152d7e4c987057b9c2bdf09c153513b964bb0'
OUT = E.out / 'packet_proof'


def _script_prompt(path):
    """The exact prompt a rendered launcher carries, read the way it is written."""
    marker = 'const PROMPT = '
    for line in Path(path).read_text().split('\n'):
        if line.startswith(marker):
            return json.loads(line[len(marker):])
    raise ValueError('no rendered prompt in %s' % path)


def _served_body(prompt_text):
    """The ONE JSON object a prompt serves, as its reader parses it."""
    return json.loads(prompt_text[prompt_text.rindex('\n{'):])


def _checked(checks, name, seam):
    """Record one check of the test inventory, derived from a touched seam."""
    def note(detail):
        checks.append(collections.OrderedDict(
            [('check', name), ('seam', seam), ('result', detail)]))
        return detail
    return note


def prepare(_producer, _inputs):
    F, K, X, G, R = E.F, E.K, E.X, E.G, E.R
    checks = []
    OUT.mkdir(parents=True)
    bound = G._approved_bound()
    shards, raws, origins, bad = F.v6_shards(bound)
    assert not bad, bad
    run = E.saved['third_round']
    candidate_dir = E.result['notes']['candidate']
    assert G._sha_file(BINDINGS) == BINDINGS_SHA256
    request = G._read(BINDINGS)

    # -- 1. THE COMPLETED SIGNATURE, through its own owner ------------------
    signature = X.signature_accounting(candidate_dir)
    lock = signature.lock
    _checked(checks, 'the completed signature verifies and proves',
             'signature_accounting')(collections.OrderedDict([
                 ('directory', signature.directory),
                 ('calls', lock['call_accounting']['signer_calls']),
                 ('ledger_before', lock['call_accounting']['ledger_before']),
                 ('ledger_after', lock['call_accounting']['ledger_after']),
                 ('pinned_artifacts', len(lock['artifacts'])),
                 ('run_ids', sorted(signature.identities[0])),
                 ('agent_ids', sorted(signature.identities[1])),
                 ('response_message_ids', len(signature.identities[2])),
                 ('response_request_ids', len(signature.identities[3]))]))
    assert signature.identities[0] == {lock['signer']['run_id']}
    assert signature.identities[1] == {lock['signer']['agent_id']}
    assert signature.identities[2] and signature.identities[3]

    # -- 2. THE TWO EVENTS, from the frozen bindings only -------------------
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    two, targets = collections.OrderedDict(), collections.OrderedDict()
    for event in sorted(request['source_events'],
                        key=lambda e: order.index(e['source_id'])):
        sid = event['source_id']
        task = F._task_by_label(bound.evidence, sid)
        assert list(task['rows']) == list(event['original_task_ids']), sid
        assert task['event_index'] == event['event_index'], sid
        assert origins[sid] == event['prior_key_origin'], sid
        assert K._sha(raws[sid]) == event['prior_source_raw_sha256'], sid
        # The finding is a POINTER to the original targets and nothing else:
        # no verdict, no grade, no review prose can enter the served body.
        two[sid] = [collections.OrderedDict(
            [('source_id', sid), ('raw_sha256', K._sha(raws[sid])),
             ('row', row)]) for row in event['original_task_ids']]
        targets[sid] = [dict(t) for t in event['targets']]
    assert list(two) == [s for s in order if s in two]
    _checked(checks, 'both events bind their six ORIGINAL targets',
             'successor_entries')(collections.OrderedDict(
                 (sid, len(rows)) for sid, rows in two.items()))

    # -- 3. THE PACKET, through F's own preparation owner -------------------
    packet_dir = OUT / 'recheck_packet'
    next_bound = X.bind(bound, str(packet_dir))
    rows, receipt, served = [], None, collections.OrderedDict()
    with X.successor_scope(next_bound, two, run, E.saved['third_by_event'],
                           E.source_inputs, E.chain,
                           signature=candidate_dir):
        assert F.v6_labels(next_bound) == list(two)
        carried, carried_raws, carried_origins, cbad = F.v5_shards(next_bound)
        assert not cbad, cbad
        assert carried == shards and carried_raws == raws
        assert carried_origins == origins
        budget = F.v6_budget(next_bound)
        result = F.prepare_v6(str(packet_dir), next_bound)
        assert result['ok'], result['problems']
        receipt = K._load(str(packet_dir / K.RECEIPT_NAME))
        pins = F._phase_history(next_bound, X.PHASE)
        priors = F._prior_runs(str(packet_dir), next_bound,
                               {'phase': X.PHASE})
        seeded = F._spent_identities(signature.directory)
        for sid in two:
            text = F.v6_prompt(next_bound, sid)
            script = F.render_v6_launcher(next_bound, sid, 1)
            served[sid] = _served_body(text)
            body = copy.deepcopy(served[sid])
            # EVERY key of the served body is accounted for: the payload
            # owner's own source view, this event's independently
            # source-derived prior key, and the pointer above. Nothing else
            # can be in there, which is the blindness rule made mechanical.
            prior_key = (X.PRIOR_KEY if origins[sid] == X.ORIGIN
                         else 'prior_key_shard')
            prior_reply = body.pop(prior_key)
            assert prior_reply == {'origin': origins[sid] + '_reply',
                                   'sha256': K._sha(raws[sid]),
                                   'raw': raws[sid]}, sid
            finding = body.pop('reviewer_finding')
            assert finding == {'source_id': sid, 'finding': two[sid]}, sid
            task = F._task_by_label(bound.evidence, sid)
            expected = F.payload(next_bound, task)
            assert body == json.loads(json.dumps(expected)), sid
            rows.append(collections.OrderedDict([
                ('source_id', sid), ('event_index', task['event_index']),
                ('origin', origins[sid]), ('prior_body_key', prior_key),
                ('prior_source_raw_sha256', K._sha(raws[sid])),
                ('original_task_ids', list(task['rows'])),
                ('source_view_keys', list(body)),
                ('prompt_sha256', K._sha(text)),
                ('prompt_bytes', len(text.encode('utf-8'))),
                ('script_sha256', K._sha(script)),
                ('script_bytes', len(script.encode('utf-8'))),
                ('script_path', str(packet_dir / 'scripts'
                                    / ('%s.attempt1.js' % sid)))]))
    assert [r['prompt_sha256'] for r in rows] == [receipt['prompts'][s]
                                                  for s in two]
    _checked(checks, 'the packet is prepared by F.prepare_v6 for two events',
             'prepare_v6')(collections.OrderedDict([
                 ('run_dir', str(packet_dir)), ('allowed', receipt['allowed']),
                 ('largest_script_bytes', result['largest_script_bytes']),
                 ('transport_limit', K.TRANSPORT_LIMIT),
                 ('invocations', len(result['invocations']))]))

    # -- 3b. BLINDNESS, measured against the ORIGINAL served body -----------
    # The only lawful reference for what this owner may see is what it was
    # served the first time. Every source-derived block is compared to those
    # exact bytes, and the two keys that are NOT source-derived are compared
    # by their field sets, so nothing output-informed can enter unnoticed.
    blindness = []
    for event in request['source_events']:
        sid = event['source_id']
        assert G._sha_file(event['original_script_path']) == \
            event['original_script_sha256'], sid
        was = _served_body(_script_prompt(event['original_script_path']))
        now = served[sid]
        old_shard = [k for k in was if k.endswith('_shard')]
        new_shard = [k for k in now if k.endswith('_shard')]
        assert len(old_shard) == len(new_shard) == 1, sid
        old_key, new_key = old_shard[0], new_shard[0]
        assert list(now) == [new_key if k == old_key else k for k in was], sid
        identical = [k for k in was
                     if k not in (old_key, 'reviewer_finding')
                     and json.dumps(was[k]) == json.dumps(now[k])]
        was_fields = sorted({k for r in was['reviewer_finding']['finding']
                             for k in r})
        now_fields = sorted({k for r in now['reviewer_finding']['finding']
                             for k in r})
        assert identical == [k for k in was
                             if k not in (old_key, 'reviewer_finding')], sid
        assert now_fields == sorted(two[sid][0]), sid
        assert set(now_fields) < set(was_fields), sid
        blindness.append(collections.OrderedDict([
            ('source_id', sid),
            ('served_body_keys', list(now)),
            ('source_blocks_identical_to_the_original', identical),
            ('prior_key_body', collections.OrderedDict([
                ('was', old_key), ('now', new_key),
                ('raw_sha256', now[new_key]['sha256']),
                ('is_the_signed_source_derived_key',
                 now[new_key]['sha256'] == event['prior_source_raw_sha256'])])),
            ('finding_fields_withheld',
             [k for k in was_fields if k not in now_fields]),
            ('finding_fields_served', now_fields)]))
    _checked(checks, 'the served body carries no evaluated or output-informed '
                     'content', 'successor_prompt')(blindness)

    # -- 4. THE THREE ACCUMULATING SEAMS ------------------------------------
    _checked(checks, 'the ledger carries every completed call incl. the '
                     'signature', 'v6_ledger_before')(collections.OrderedDict([
                         ('phase_chain_before_signature',
                          lock['call_accounting']['ledger_before']),
                         ('ledger_before_next_round', budget['before']),
                         ('lock_ledger_after', lock['call_accounting']
                          ['ledger_after'])]))
    assert budget['before'] == lock['call_accounting']['ledger_after']
    assert budget['before'] == (lock['call_accounting']['ledger_before']
                                + lock['call_accounting']['signer_calls'])
    _checked(checks, 'the signature is pinned into this run\'s history',
             '_phase_history')(collections.OrderedDict([
                 ('history_pin_tags', list(pins)),
                 ('signature_pin_matches_lock_artifacts',
                  pins['signature'] == lock['artifacts']),
                 ('receipt_carries_the_same_pins',
                  receipt['v1_evidence'] == json.loads(json.dumps(pins)))]))
    assert pins['signature'] == lock['artifacts']
    assert receipt['v1_evidence'] == json.loads(json.dumps(pins))
    _checked(checks, 'the signature is reachable as a spent-identity source',
             '_prior_runs')(collections.OrderedDict([
                 ('prior_run_dirs', len(priors)),
                 ('signature_is_in_prior_run_dirs',
                  signature.directory in priors)]))
    assert signature.directory in priors
    _checked(checks, 'the signature\'s identities are no longer empty',
             '_spent_identities')(collections.OrderedDict([
                 ('counts_under_the_scope', [len(s) for s in seeded]),
                 ('counts_without_the_scope',
                  [len(s) for s in F._spent_identities(signature.directory)])]))
    assert [len(s) for s in seeded] == [len(s) for s in signature.identities]
    assert [len(s) for s in F._spent_identities(signature.directory)] == \
        [0, 0, 0, 0]

    # -- 5. THE UNSIGNED CONTROL: nothing changes without a signature -------
    control_dir = OUT / 'unsigned_control'
    control_bound = X.bind(bound, str(control_dir))
    with X.successor_scope(control_bound, two, run, E.saved['third_by_event'],
                           E.source_inputs, E.chain):
        unsigned = collections.OrderedDict([
            ('ledger_before', F.v6_ledger_before(control_bound)),
            ('history_pin_tags', list(F._phase_history(control_bound,
                                                       X.PHASE))),
            ('prior_run_dirs', len(F._prior_runs(str(control_dir),
                                                 control_bound,
                                                 {'phase': X.PHASE})))])
    assert unsigned['ledger_before'] == \
        lock['call_accounting']['ledger_before']
    assert 'signature' not in unsigned['history_pin_tags']
    assert unsigned['prior_run_dirs'] == len(priors) - 1
    _checked(checks, 'without a signature the seams are unchanged',
             'successor_scope')(unsigned)

    # -- 6. COLD RECONSTRUCTION OF EVERY COMPLETED ROUND --------------------
    history = list(E.chain) + [(run, E.saved['third_by_event'])]
    historical = []
    for i, (prior_run, prior_findings) in enumerate(history):
        prior_bound = X.first_bound(bound, prior_run)
        with X.first_round_scope(bound, prior_run, prior_findings,
                                 E.source_inputs, tuple(history[:i])):
            recorded = K._load(os.path.join(prior_run, K.RECEIPT_NAME))
            actual = {sid: K._sha(F.v6_prompt(prior_bound, sid))
                      for sid in F.v6_labels(prior_bound)}
            assert actual == recorded['prompts'], prior_run
            assert F._receipt_still_the_proved_one(prior_run,
                                                   prior_bound) == [], prior_run
        historical.append(collections.OrderedDict([
            ('run', prior_run), ('prompts', len(actual)),
            ('receipt_sha256', G._sha_file(os.path.join(prior_run,
                                                        K.RECEIPT_NAME))),
            ('finalization_sha256', G._sha_file(
                os.path.join(prior_run, K.FINALIZATION_NAME)))]))
    _checked(checks, 'every completed round still reconstructs cold',
             'first_round_scope')(historical)

    # -- 7. RESUME: the packet re-derives its own expectation ---------------
    twin_dir = OUT / 'resume_twin'
    twin_bound = X.bind(bound, str(twin_dir))
    with X.successor_scope(twin_bound, two, run, E.saved['third_by_event'],
                           E.source_inputs, E.chain, signature=candidate_dir):
        twin = F.prepare_v6(str(twin_dir), twin_bound)
        assert twin['ok'], twin['problems']
        twin_receipt = K._load(str(twin_dir / K.RECEIPT_NAME))
        # cold: the published receipt is still the one this owner expects
        cold = F.receipt_problems(str(packet_dir), next_bound, receipt)
    same = {k: v for k, v in receipt.items() if k != 'run_id'} == \
        {k: v for k, v in twin_receipt.items() if k != 'run_id'}
    scripts_same = all(
        (packet_dir / 'scripts' / ('%s.attempt1.js' % s)).read_text()
        == (twin_dir / 'scripts' / ('%s.attempt1.js' % s)).read_text()
        for s in two)
    assert same and scripts_same and cold == []
    _checked(checks, 'a second preparation is byte-identical and resumes',
             'receipt_problems')(collections.OrderedDict([
                 ('receipt_identical_but_run_id', same),
                 ('scripts_identical', scripts_same),
                 ('cold_receipt_problems', cold)]))

    # -- 8. RECORD AND FINALIZATION, reached on the TWIN --------------------
    # NEVER on the packet itself: `record_state` rewrites the receipt and
    # `finalize` publishes a finalization whose ledger counts `allowed` as
    # scheduled. Either on the real packet would write down calls that were
    # never made. The twin is the same packet, so reaching those owners
    # through it says exactly what reaching them through the packet would.
    fake_state = OUT / 'not_an_official_state.json'
    fake_state.write_text(json.dumps({'runId': 'not-an-official-run'}))
    with X.successor_scope(twin_bound, two, run, E.saved['third_by_event'],
                           E.source_inputs, E.chain, signature=candidate_dir):
        assert F.record_state(str(twin_dir), str(fake_state)) == []
        recorded = K._load(str(twin_dir / K.RECEIPT_NAME))
        closed = F.finalize(str(twin_dir), twin_bound)
    assert recorded['states'] == [str(fake_state)]
    assert not closed['phase_complete'] and not closed['retry']
    # With no call made, the finalization owner credits NOTHING and offers no
    # retry: both events are missing their official state.
    assert [o for _l, o, _w in closed['outcomes']] == ['missing'] * len(two)
    assert closed['ledger']['valid'] == 0
    assert not (packet_dir / K.FINALIZATION_NAME).exists()
    assert K._load(str(packet_dir / K.RECEIPT_NAME))['states'] == []
    _checked(checks, 'record and finalization reach the packet, on the twin',
             'record_state/finalize')(collections.OrderedDict([
                 ('twin', str(twin_dir)),
                 ('recorded_states', len(recorded['states'])),
                 ('phase_complete', closed['phase_complete']),
                 ('scheduled_on_the_twin', closed['ledger']['scheduled']),
                 ('outcomes', [[l, o] for l, o, _w in closed['outcomes']]),
                 ('retry_offered', closed['retry']),
                 ('packet_receipt_untouched',
                  K._load(str(packet_dir / K.RECEIPT_NAME))['states'] == []),
                 ('packet_has_no_finalization',
                  not (packet_dir / K.FINALIZATION_NAME).exists())]))

    # -- 9. NEGATIVE CONTROLS, each after its own positive control ----------
    negatives = []

    def rejects(name, control, action):
        assert control(), 'the positive control for %s did not pass' % name
        try:
            action()
        except (ValueError, AssertionError) as exc:
            negatives.append(collections.OrderedDict(
                [('case', name), ('reason', str(exc)[:200])]))
        else:
            raise AssertionError('failed to reject ' + name)

    def signature_reads():
        return X.signature_accounting(candidate_dir).lock == lock

    missing = OUT / 'signature_with_no_lock'
    missing.mkdir()
    rejects('missing_prior_signature', signature_reads,
            lambda: X.signature_accounting(str(missing)))

    intact = OUT / 'signature_copy_intact'
    shutil.copytree(candidate_dir, str(intact))
    tampered = OUT / 'signature_copy_tampered'
    shutil.copytree(candidate_dir, str(tampered))
    lock_name = os.path.basename(signature.lock_path)
    moved = G._read(str(tampered / lock_name))
    moved['signer']['run_id'] = moved['signer']['run_id'] + '-moved'
    (tampered / lock_name).write_text(json.dumps(moved, indent=1))
    rejects('tampered_prior_signature',
            lambda: X.signature_accounting(str(intact)).lock == lock,
            lambda: X.signature_accounting(str(tampered)))

    def tamper_the_intact_copy():
        """Move a byte at a path THAT HAS ALREADY BEEN READ CLEANLY.

        The positive control above verified this exact directory a moment
        ago. A reader that remembered that answer would keep counting the
        signature after the bytes moved, which is the one thing the admission
        rule exists to refuse, so the second read must see the live bytes.
        """
        edited = G._read(str(intact / lock_name))
        edited['call_accounting']['ledger_after'] += 1
        (intact / lock_name).write_text(json.dumps(edited, indent=1))
        X.signature_accounting(str(intact))

    rejects('same_path_tampered_after_a_clean_read',
            lambda: X.signature_accounting(str(intact)).lock == lock,
            tamper_the_intact_copy)

    def entries(doc):
        return X.successor_entries(bound, doc, run, E.saved['third_by_event'],
                                   E.source_inputs, E.chain)

    def two_events_admit():
        return entries(two) == [(sid, two[sid]) for sid in two]

    for field, value in (('source_id', 'not-a-current-source'),
                         ('raw_sha256', '0' * 64),
                         ('row', 'not-an-original-target')):
        changed = copy.deepcopy(two)
        changed[list(two)[0]][0][field] = value
        rejects(field, two_events_admit, lambda c=changed: entries(c))

    def short_chain():
        """The same round with the LAST completed round dropped from history.

        The signature was budgeted after every call this phase had made. A
        successor that walks a shorter chain counts fewer, so adopting the
        signature's total there would silently swallow the calls it dropped.
        """
        with X.successor_scope(next_bound, two, E.chain[-1][0], E.chain[-1][1],
                               E.source_inputs, E.chain[:-1],
                               signature=candidate_dir):
            F.v6_ledger_before(next_bound)

    rejects('signature_budgeted_against_another_history',
            lambda: budget['before'] == lock['call_accounting']['ledger_after'],
            short_chain)
    _checked(checks, 'a missing, tampered, or mis-bound input refuses',
             'signature_accounting/successor_entries/v6_ledger_before'
             )(negatives)

    # -- 10. A REUSED NATIVE IDENTITY, at F's own consumer ------------------
    label = list(two)[0]

    def synthetic(run_id):
        path = OUT / ('%s.json' % run_id)
        path.write_text(json.dumps(collections.OrderedDict([
            ('runId', run_id), ('status', 'completed'), ('script', ''),
            ('workflowProgress', [collections.OrderedDict(
                [('type', 'workflow_agent'), ('label', label),
                 ('agentId', 'not-a-spent-agent'), ('state', 'pending')])])])))
        seen = dict(receipt)
        seen['states'] = [str(path)]
        with X.successor_scope(next_bound, two, run, E.saved['third_by_event'],
                               E.source_inputs, E.chain,
                               signature=candidate_dir):
            _out, problems = F.run_evidence(str(packet_dir), next_bound, seen)
        return problems

    spent_run = sorted(signature.identities[0])[0]
    reused = synthetic(spent_run)
    fresh = synthetic('wf-not-a-spent-run-000')
    marker = 'run id %r was already spent' % spent_run
    assert any(marker in p for p in reused), reused[:2]
    assert not any('was already spent' in p for p in fresh), fresh[:2]
    _checked(checks, 'reusing the signature\'s run identity is refused',
             '_spent_identities')(collections.OrderedDict([
                 ('reused_identity', spent_run),
                 ('reused_problems', len(reused)),
                 ('fresh_problems', len(fresh)),
                 ('only_difference_is_the_reuse',
                  [p for p in reused if p not in fresh])]))

    # -- 11. THE DURABLE PACKET --------------------------------------------
    packet = collections.OrderedDict([
        ('scope', 'PRE-CALL packet for two source-key rechecks; armed and '
                  'unrun. No model call, no signature, no key change.'),
        ('model_calls', 0),
        ('caller_sha256', G._sha_file(__file__)),
        ('owner_sha256', G._sha_file(X.__file__)),
        ('bindings', collections.OrderedDict([
            ('path', BINDINGS), ('sha256', BINDINGS_SHA256),
            ('targets_per_event', collections.OrderedDict(
                (sid, len(t)) for sid, t in targets.items()))])),
        ('run_dir', str(packet_dir)),
        ('receipt_sha256', G._sha_file(str(packet_dir / K.RECEIPT_NAME))),
        ('phase', receipt['phase']), ('attempt', receipt['attempt']),
        ('allowed', receipt['allowed']),
        ('role_and_runtime', receipt['transport']),
        ('input_declarations', rows),
        ('invocations', result['invocations']),
        ('current_key', collections.OrderedDict([
            ('sources', len(shards)),
            ('phase_supported_sources', len(F.v5_labels(bound))),
            ('key_identity_sha256', request['approved_key_identity_sha256']),
            ('provenance_sha256',
             request['prior_source_key_provenance_sha256'])])),
        ('old_signature', collections.OrderedDict([
            ('directory', signature.directory),
            ('lock_path', signature.lock_path),
            ('lock_sha256', G._sha_file(signature.lock_path)),
            ('run_id', lock['signer']['run_id']),
            ('agent_id', lock['signer']['agent_id']),
            ('raw_sha256', lock['signer']['raw_sha256']),
            ('artifacts', lock['artifacts'])])),
        ('call_accounting', collections.OrderedDict([
            ('before', budget['before']),
            ('planned_corrections', budget['planned_corrections']),
            ('planned_signer', budget['planned_signer']),
            ('after_planned', budget['after_planned']),
            ('max_attempts_per_call', budget['max_attempts_per_call']),
            ('retryable_outcomes', list(F.RETRYABLE)),
            ('retry_law_owner', 'build_kfields_final.RETRYABLE'),
            ('worst_case_after', budget['worst_case_after']),
            ('global_ceiling', budget['global_ceiling'])])),
        ('history_pin_tags', list(pins)),
        ('prior_identity_sources', priors),
        ('historical_rounds', historical),
        ('sources_not_touched', [s for s in shards if s not in two])])
    G._write_new(str(OUT / 'RECHECK_PACKET_2123.json'), G._pretty(packet) + '\n')
    inventory = collections.OrderedDict([
        ('scope', 'the checks the touched seams require, and nothing else'),
        ('touched_seams', ['signature_accounting', 'v6_ledger_before',
                           '_phase_history', '_prior_runs',
                           '_spent_identities']),
        ('checks', checks), ('model_calls', 0)])
    G._write_new(str(OUT / 'TEST_INVENTORY_2123.json'),
                 G._pretty(inventory) + '\n')
    print('RECHECK_PACKET_2123', json.dumps(collections.OrderedDict([
        ('events', list(two)), ('ledger_before', budget['before']),
        ('history_pin_tags', list(pins)), ('checks', len(checks)),
        ('negatives', len(negatives)), ('model_calls', 0),
        ('packet_sha256', G._sha_file(str(OUT / 'RECHECK_PACKET_2123.json'))),
        ('inventory_sha256', G._sha_file(str(OUT / 'TEST_INVENTORY_2123.json'))),
    ])), flush=True)
    return packet


E.with_prepared_inputs(prepare)
