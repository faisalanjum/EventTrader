"""Read-only evidence for the two collected source rechecks.

What actually changed in the key, what the existing gate says about it, and the
runtime identities the two completed calls really carried. Reads only; it
records nothing, finalizes nothing and starts no call.
"""
import collections
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
    'current_key_candidate_2123', candidate,
    loader=SourceFileLoader('current_key_candidate_2123', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

BINDINGS = str(E.A7 / 'unit_2020_codex_check'
               / 'SOURCE_KEY_RECHECK_BINDINGS_2120.json')
RUN = E.A7 / 'unit_2123_post_signature_key/core_recheck2123_h/recheck_packet'
OUT = E.A7 / 'unit_2123_post_signature_key' / os.environ['A7_TAG']


def _facts(F, text, task, bound):
    """The shard's own parse, through F's own reader."""
    obj, bad = F.read_shard(text, task, F.event_leads(bound, task))
    return obj, bad


def _row_view(shard, task):
    """One compact line per located row, in the task's own order.

    `read_shard` keys its settled rows and outcomes by the located row id, so
    the order comes from the task rather than from the reply.
    """
    out = []
    for n, packet in enumerate(task['rows']):
        settled = (shard['rows'] or {}).get(packet) or {}
        facts = settled.get('facts') or []
        out.append(collections.OrderedDict([
            ('row_index', n + 1), ('row', packet),
            ('final_outcome', (shard['outcomes'] or {}).get(packet)),
            ('facts', [collections.OrderedDict([
                ('fact_type', f.get('fact_type')),
                ('driver_name', (f.get('item') or {}).get('driver_name')),
                ('driver_state', (f.get('item') or {}).get('driver_state'))])
                for f in facts]),
            ('abstentions', len(settled.get('abstentions') or []))]))
    return out


def _settled_diff(G, before, after, task):
    """EVERY field of every settled fact, before against after.

    The coarse row view answers "did the outcome move"; this answers "did any
    measured value move", which is the only thing that can change the key.
    """
    out = []
    for n, packet in enumerate(task['rows']):
        was = (before['rows'] or {}).get(packet) or {}
        now = (after['rows'] or {}).get(packet) or {}
        if G._plain(was) == G._plain(now):
            continue
        wf, nf = was.get('facts') or [], now.get('facts') or []
        row = collections.OrderedDict([('row_index', n + 1), ('row', packet),
                                       ('facts_before', len(wf)),
                                       ('facts_after', len(nf))])
        fields = []
        for i in range(max(len(wf), len(nf))):
            a = (wf[i].get('item') if i < len(wf) else {}) or {}
            b = (nf[i].get('item') if i < len(nf) else {}) or {}
            for key in sorted(set(a) | set(b)):
                if G._plain(a.get(key)) != G._plain(b.get(key)):
                    fields.append(collections.OrderedDict([
                        ('fact_index', i), ('field', key),
                        ('before', G._plain(a.get(key))),
                        ('after', G._plain(b.get(key)))]))
        row['item_fields_that_moved'] = fields
        for key in ('abstentions', 'continuity_hints'):
            if G._plain(was.get(key)) != G._plain(now.get(key)):
                row[key] = [G._plain(was.get(key)), G._plain(now.get(key))]
        out.append(row)
    return out


def _list_diff(G, was, now, key_of):
    """Field-by-field over two aligned lists of objects. -> moved fields."""
    out = []
    for i in range(max(len(was), len(now))):
        a = was[i] if i < len(was) else {}
        b = now[i] if i < len(now) else {}
        for field in sorted(set(a) | set(b)):
            if G._plain(a.get(field)) != G._plain(b.get(field)):
                out.append(collections.OrderedDict([
                    ('at', key_of(a) or key_of(b)), ('field', field),
                    ('before', G._plain(a.get(field))),
                    ('after', G._plain(b.get(field)))]))
    return out


def evidence(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    bound = G._approved_bound()
    request = G._read(BINDINGS)
    two = [e['source_id'] for e in request['source_events']]
    run_id = E.saved['third_round']
    candidate_dir = E.result['notes']['candidate']
    findings = collections.OrderedDict()
    for event in request['source_events']:
        sid = event['source_id']
        findings[sid] = [collections.OrderedDict(
            [('source_id', sid),
             ('raw_sha256', event['prior_source_raw_sha256']), ('row', row)])
            for row in event['original_task_ids']]
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    findings = collections.OrderedDict(
        sorted(findings.items(), key=lambda kv: order.index(kv[0])))

    next_bound = X.bind(bound, str(RUN))
    with X.successor_scope(next_bound, findings, run_id,
                           E.saved['third_by_event'], E.source_inputs,
                           E.chain, signature=candidate_dir):
        was, was_raws, was_origins, wbad = F.v5_shards(next_bound)
        now, now_raws, now_origins, nbad = F.v6_shards(next_bound)
        assert not wbad and not nbad, (wbad[:1], nbad[:1])
        gate = F.signing_gate(bound.evidence, next_bound)
        budget = F.v6_budget(next_bound)
        decisions = collections.OrderedDict()
        for sid in two:
            task = F._task_by_label(bound.evidence, sid)
            before, bbad = _facts(F, was_raws[sid], task, next_bound)
            after, abad = _facts(F, now_raws[sid], task, next_bound)
            assert before is not None and after is not None, (bbad[:1], abad[:1])
            was_rows, now_rows = _row_view(before, task), _row_view(after, task)
            decisions[sid] = collections.OrderedDict([
                ('event_index', task['event_index']),
                ('rows_asked', list(task['rows'])),
                ('origin', [was_origins[sid], now_origins[sid]]),
                ('raw_sha256', [K._sha(was_raws[sid]), K._sha(now_raws[sid])]),
                ('raw_changed', was_raws[sid] != now_raws[sid]),
                ('parse_problems', [bbad[:1], abad[:1]]),
                ('open_issues', [len(before['open_issues']),
                                 len(after['open_issues'])]),
                ('rows_before', was_rows), ('rows_after', now_rows),
                ('rows_that_moved', [r['row'] for r, q in zip(was_rows, now_rows)
                                     if r != q]),
                # the WHOLE parsed shard, not a summary of it: every settled
                # fact with its levels, units, slices and baselines, every
                # outcome, the review rows with their gold fields and hard
                # classes, the groups and the lead reconciliation.
                ('parsed_blocks_that_differ',
                 [k for k in before if G._plain(before[k]) != G._plain(after[k])]),
                ('settled_fields_that_moved',
                 _settled_diff(G, before, after, task)),
                ('review_fields_that_moved',
                 _list_diff(G, before['review'], after['review'],
                            lambda r: (r.get('row_index'),
                                       r.get('fact_index')))),
                ('lead_fields_that_moved',
                 _list_diff(G, before['lead_reconciliation'],
                            after['lead_reconciliation'],
                            lambda r: r.get('lead_id'))),
                ('same_decision', was_rows == now_rows)])

    # the runtime identities the completed calls really carried, from the
    # transcript owner the signature proof already uses
    sys.path.insert(0, str(E.A7 / 'unit_1955/lock_owners'))
    import signer_proof as SP                                     # noqa: E402
    receipt = K._load(str(RUN / K.RECEIPT_NAME))
    runtime = []
    for state in receipt['states']:
        doc = K._load(state)
        session_dir, session_id = F.HR.AUD._official_location(state)
        row = [r for r in doc.get('workflowProgress') or []
               if r.get('type') == 'workflow_agent'][0]
        got = K.direct_result(doc)
        tp = os.path.join(session_dir or '', 'subagents', 'workflows',
                          doc['runId'], 'agent-%s.jsonl' % row['agentId'])
        runtime.append(collections.OrderedDict([
            ('label', row.get('label')), ('run_id', doc['runId']),
            ('agent_id', row['agentId']), ('parent_session_id', session_id),
            ('session_is_the_frozen_one', session_id == K.PARENT_SESSION),
            ('status', doc.get('status')),
            ('declared', [got.get('model'), got.get('effort'),
                          got.get('agentType')]),
            ('observed_runtime_model_ids', sorted(SP._model_ids(tp))),
            ('tool_calls', doc.get('totalToolCalls')),
            ('state_sha256', G._sha_file(state)),
            ('transcript_sha256', G._sha_file(tp)),
            ('prompt_sha256_recorded', receipt['prompts'][row['label']]),
            ('script_bytes_persisted', len(doc.get('script') or ''))]))

    report = collections.OrderedDict([
        ('scope', 'read-only evidence for the two collected rechecks; '
                  'no call, no record, no finalization'),
        ('caller_sha256', G._sha_file(__file__)),
        ('runtime_identities', runtime),
        ('decisions', decisions),
        ('key', collections.OrderedDict([
            ('sources_before', len(was)), ('sources_after', len(now)),
            ('changed', [s for s in now_raws if now_raws[s] != was_raws[s]]),
            ('origins_changed', [s for s in now_origins
                                 if now_origins[s] != was_origins[s]])])),
        ('gate', collections.OrderedDict([
            ('ok', gate['ok']), ('stops', gate.get('stops') or []),
            ('counts', gate.get('counts'))])),
        ('ledger_after_this_collection', budget['before']),
        ('model_calls_started_here', 0)])
    G._write_new(str(OUT / 'RECHECK_EVIDENCE_2123.json'),
                 G._pretty(report) + '\n')
    print('RECHECK_EVIDENCE_2123', json.dumps(collections.OrderedDict([
        ('gate_ok', gate['ok']), ('gate_stops', (gate.get('stops') or [])[:2]),
        ('changed', report['key']['changed']),
        ('same_decision', {s: d['same_decision']
                           for s, d in decisions.items()}),
        ('ledger', budget['before']),
        ('report_sha256', G._sha_file(str(OUT / 'RECHECK_EVIDENCE_2123.json'))),
    ])), flush=True)
    return report


E.with_prepared_inputs(evidence)
