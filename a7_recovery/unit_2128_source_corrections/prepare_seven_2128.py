"""Assemble and prove the seven-source correction packet. No model call.

Everything runs through the existing owners: `X.first_round_key` for the
current key, `F.prepare_v6` for the packet, `F.v6_budget` for the accounting,
and the shared binding for every pointer. Nothing here copies owner logic or
opens a phase, and the packet is left armed and unrun.
"""
import collections
import copy
import json
import os
import sys
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E                              # noqa: E402

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
_spec = importlib.util.spec_from_file_location(
    'round_candidate_2128', candidate,
    loader=SourceFileLoader('round_candidate_2128', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

U = E.A7 / 'unit_2128_source_corrections'
OUT = U / os.environ['A7_TAG']
#: root's clean predecessor proof must have finished before any native check
GATE = E.A7 / 'unit_1947/logs/attempt_codex_predecessor2128_final/exit'


def _body(text):
    return json.loads(text.split('[INPUT]\n', 1)[1])


def prepare(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections'):
        sys.path.insert(0, str(E.A7 / rel))
    import a4_source_taskv2 as V2                                 # noqa: E402
    import a7_source_context_2127 as V3                           # noqa: E402
    import a7_round_binding_2128 as B                             # noqa: E402

    def cold(action):
        """A real outer-operation boundary; clears the native proof caches."""
        with E.R._using(F, _OP_DEPTH=[0]):
            return F._operation(action)()

    b = B.binding(E, X)
    assert len(b.affected) == 7, b.affected
    # ---- the current key, through the existing owner --------------------
    shards, raws, origins, bad = cold(lambda: B.current_key(E, X, b))
    assert not bad, bad[:2]
    assert len(shards) == 33, len(shards)
    findings = B.round_findings(E, b, raws)
    assert list(findings) == b.affected
    untouched = [s for s in shards if s not in b.affected]
    assert len(untouched) == 26, len(untouched)
    before_raws = {s: K._sha(raws[s]) for s in untouched}
    before_origins = {s: origins[s] for s in untouched}

    packet = OUT / 'seven_source_packet'
    next_bound = X.bind(b.bound, str(packet))
    rows, receipt, historical = [], None, []
    # the prompts WITHOUT the wording install, for the exact-delta comparison
    with X.successor_scope(next_bound, findings, b.predecessor,
                           b.predecessor_findings, E.source_inputs, b.prior,
                           signatures=b.signatures):
        plain = {sid: F.v6_prompt(next_bound, sid) for sid in b.affected}
    with B.scope(E, X, b, next_bound, findings, V2, V3):
        labels = F.v6_labels(next_bound)
        assert labels == b.affected, labels
        carried, carried_raws, carried_origins, cbad = F.v5_shards(next_bound)
        assert not cbad and len(carried) == 33
        assert {s: K._sha(carried_raws[s]) for s in untouched} == before_raws
        assert {s: carried_origins[s] for s in untouched} == before_origins
        budget = F.v6_budget(next_bound)
        assert budget['before'] == 670, budget['before']
        result = F.prepare_v6(str(packet), next_bound)
        assert result['ok'], result['problems']
        receipt = K._load(str(packet / K.RECEIPT_NAME))
        for sid in labels:
            text = F.v6_prompt(next_bound, sid)
            script = F.render_v6_launcher(next_bound, sid, 1)
            head, tail = plain[sid].split(V3.SPAN_OLD, 1)
            task = F._task_by_label(b.bound.evidence, sid)
            body = copy.deepcopy(_body(text))
            prior_key = (X.PRIOR_KEY if origins[sid] == X.ORIGIN
                         else 'prior_key_shard')
            reply = body.pop(prior_key)
            finding = body.pop('reviewer_finding')
            expected = F.payload(next_bound, task)
            rows.append(collections.OrderedDict([
                ('source_id', sid), ('event_index', task['event_index']),
                ('origin', origins[sid]), ('prior_body_key', prior_key),
                ('original_rows', list(task['rows'])),
                ('rows_served', len(finding['finding'])),
                ('served_body_keys', list(_body(text))),
                ('finding_fields', sorted({k for r in finding['finding']
                                           for k in r})),
                ('prior_reply_is_the_current_source_key',
                 reply == {'origin': origins[sid] + '_reply',
                           'sha256': K._sha(raws[sid]), 'raw': raws[sid]}),
                ('source_view_matches_the_payload_owner',
                 body == json.loads(json.dumps(expected))),
                ('exactly_the_approved_prefix_delta',
                 text == head + V3.SPAN_NEW + tail),
                ('clarification_occurrences',
                 text.count(V3.CLARIFICATION_BLOCK)),
                ('prompt_sha256', K._sha(text)),
                ('prompt_bytes', len(text.encode('utf-8'))),
                ('script_sha256', K._sha(script)),
                ('script_bytes', len(script.encode('utf-8')))]))
        # ---- 4 rounds / 12 prompts, WITH the install held -------------
        for n, (run, row_findings) in enumerate(
                b.prior + ((b.predecessor, b.predecessor_findings),)):
            phase_bound = X.first_bound(b.bound, run)
            plan = b.signatures if run == b.predecessor else {}
            with X.first_round_scope(b.bound, run, row_findings,
                                     E.source_inputs, b.prior[:n],
                                     signatures=plan):
                recorded = K._load(os.path.join(run, K.RECEIPT_NAME))
                got = {s: K._sha(F.v6_prompt(phase_bound, s))
                       for s in F.v6_labels(phase_bound)}
                assert F._receipt_still_the_proved_one(run, phase_bound) == []
            historical.append(collections.OrderedDict([
                ('run', run), ('prompts', len(got)),
                ('byte_exact', got == recorded['prompts'])]))
        # An UNRUN packet has no accepted answer for the events it asks, so
        # the merged key must refuse rather than read as though it had one.
        # Recorded as a property of the armed packet, not asserted clean.
        after = F.v6_shards(next_bound)
        unrun_refusal = after[3]
        assert unrun_refusal, 'the unrun packet read as an answered round'

    assert [r['prompt_sha256'] for r in rows] == [receipt['prompts'][s]
                                                  for s in b.affected]
    assert all(h['byte_exact'] for h in historical)
    assert sum(h['prompts'] for h in historical) == 12

    # ---- collection/resume reads the SAME binding -------------------------
    fresh = B.binding(E, X)
    resume_findings = None
    rb = X.bind(fresh.bound, str(packet))
    with B.scope(E, X, fresh, rb, findings, V2, V3):
        resume_findings = F.v6_labels(rb)
        cold_problems = F.receipt_problems(str(packet), rb, receipt)
        resume_prompts = {s: K._sha(F.v6_prompt(rb, s)) for s in resume_findings}
    assert resume_findings == b.affected
    assert cold_problems == []
    assert resume_prompts == {r['source_id']: r['prompt_sha256'] for r in rows}

    # ---- negatives, each after a real intact positive control -------------
    negatives = []

    def control():
        with B.scope(E, X, b, next_bound, findings, V2, V3):
            assert F.v5_shards(next_bound)[0] == shards
            return F.v6_ledger_before(next_bound)

    def refuses(name, action):
        assert cold(control) == 670
        try:
            cold(action)
        except (ValueError, AssertionError) as exc:
            negatives.append(collections.OrderedDict(
                [('case', name), ('reason', str(exc)[:200])]))
        else:
            raise AssertionError('did not refuse ' + name)

    def counted(plan):
        with X.successor_scope(next_bound, findings, b.predecessor,
                               b.predecessor_findings, E.source_inputs,
                               b.prior, signatures=plan):
            assert F.v5_shards(next_bound)[0] == shards
            return F.v6_ledger_before(next_bound)

    refuses('omitted_signature', lambda: counted({}))
    refuses('misplaced_signature',
            lambda: counted({b.prior[-1][0]: b.signatures[b.predecessor]}))
    refuses('signature_outside_this_history',
            lambda: counted({'not-a-recorded-round': b.signatures[b.predecessor]}))
    stale = copy.deepcopy(findings)
    stale[b.affected[0]][0]['raw_sha256'] = '0' * 64
    refuses('stale_current_raw', lambda: X.successor_entries(
        next_bound, stale, b.predecessor, b.predecessor_findings,
        E.source_inputs, b.prior, signatures=b.signatures))
    changed = tuple(b.prior[:-1])
    refuses('changed_history', lambda: X.successor_entries(
        next_bound, findings, b.predecessor, b.predecessor_findings,
        E.source_inputs, changed, signatures=b.signatures))

    pre = K._load(os.path.join(b.predecessor, K.RECEIPT_NAME))
    report = collections.OrderedDict([
        ('scope', 'PRE-CALL packet for the seven affected source events; armed '
                  'and unrun. No model call, no key change, no publication.'),
        ('model_calls', 0),
        ('caller_sha256', G._sha_file(__file__)),
        ('binding_sha256', G._sha_file(str(U / 'a7_round_binding_2128.py'))),
        ('owner_sha256', G._sha_file(X.__file__)),
        ('renderer_sha256', G._sha_file(str(E.A7 / 'unit_2127_source_context'
                                            / 'a7_source_context_2127.py'))),
        ('root_gate_exit', GATE.read_text().strip()),
        ('binding', B.pointers(E, b)),
        ('run_dir', str(packet)),
        ('receipt_sha256', G._sha_file(str(packet / K.RECEIPT_NAME))),
        ('allowed', receipt['allowed']), ('states', receipt['states']),
        ('tasks', sum(len(r['original_rows']) for r in rows)),
        ('role_and_runtime', receipt['transport']),
        ('role_and_runtime_matches_the_predecessor',
         receipt['transport'] == pre['transport']),
        ('input_declarations', rows),
        ('invocations', result['invocations']),
        ('largest_script_bytes', result['largest_script_bytes']),
        ('transport_limit', K.TRANSPORT_LIMIT),
        ('call_accounting', collections.OrderedDict([
            ('before', budget['before']),
            ('planned_corrections', budget['planned_corrections']),
            ('planned_signer', budget['planned_signer']),
            ('after_planned', budget['after_planned']),
            ('max_attempts_per_call', budget['max_attempts_per_call']),
            ('retryable_outcomes', list(F.RETRYABLE)),
            ('worst_case_after', budget['worst_case_after']),
            ('global_ceiling', budget['global_ceiling'])])),
        ('key', collections.OrderedDict([
            ('sources', len(shards)),
            ('asked_again', list(b.affected)),
            ('untouched', len(untouched)),
            ('untouched_raws_unchanged', True),
            ('untouched_origins_unchanged', True)])),
        ('historical_rounds', historical),
        ('unrun_packet_refuses_as_a_merged_key', unrun_refusal[:2]),
        ('resume_uses_the_same_binding', collections.OrderedDict([
            ('labels', resume_findings), ('receipt_problems', cold_problems),
            ('prompt_hashes_identical', True)])),
        ('negative_controls', negatives)])
    G._write_new(str(OUT / 'SEVEN_SOURCE_PACKET_2128.json'),
                 G._pretty(report) + '\n')
    print('SEVEN_SOURCE_PACKET_2128', json.dumps(collections.OrderedDict([
        ('events', len(rows)), ('tasks', report['tasks']),
        ('before', budget['before']), ('after_planned', budget['after_planned']),
        ('largest_script', result['largest_script_bytes']),
        ('historical', [h['prompts'] for h in historical]),
        ('negatives', [n['case'] for n in negatives]),
        ('packet_sha256', G._sha_file(str(OUT / 'SEVEN_SOURCE_PACKET_2128.json'))),
    ])), flush=True)
    return report


assert GATE.is_file(), 'root predecessor proof has not finished: %s' % GATE
assert GATE.read_text().strip() == '0', \
    'root predecessor proof exited %r' % GATE.read_text().strip()
E.with_prepared_inputs(prepare)
