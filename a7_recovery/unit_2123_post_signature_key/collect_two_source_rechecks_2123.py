"""Collect the TWO source-only decisions into the frozen recheck packet.

Codex SEQ 2123. The calls themselves are made by the Workflow route outside
this boundary; this binds ONLY the owners that already exist - `record_state`
for the official states, `finalize` for the paid raw bytes, the native proof,
the retry law and the gate - under the SAME successor scope, with the prior
signature supplied. It starts no call, renders no new prompt and decides
nothing: every judgement below is F's own.

  A7_RECHECK_STATES  JSON list of the official state paths to record.
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
BINDINGS_SHA256 = 'a97d16ba0895f6170e3f4ac5358152d7e4c987057b9c2bdf09c153513b964bb0'
PACKET = E.A7 / 'unit_2123_post_signature_key/core_recheck2123_h'
RUN = PACKET / 'recheck_packet'
#: the packet Codex froze, named by him in SEQ 2123
FROZEN = {
    'packet': '532c0a741bc5a6f2acc287dd295c296f024ca6e4f805e5ba7abedb54c1ca286a',
    '0000898173-26-000006': (
        'c9008c82550214e4907176b3f1b9174fb714506ddaf152f3eba2361eb588d632',
        '84ee6efb1e440fbec3af994cf12353b9b4cd8931928d19e57169d2fe2c1299c8'),
    '0001104659-26-017090': (
        'c718049bc6480b5430766fb07121c605712e5edd52a9cffed7871d07bcccb191',
        '686b3931700d80712ed278f1e54a9bf0e48ff20ca08e24d72e2a9f6197f2e8ad'),
}
OUT = E.A7 / 'unit_2123_post_signature_key' / os.environ['A7_TAG']


def _two_findings(F, K, bound, raws, origins, request):
    """The SAME two findings the packet was frozen with, re-derived."""
    order = [t['source_id'] for t in F.event_tasks(bound.evidence)]
    two = collections.OrderedDict()
    for event in sorted(request['source_events'],
                        key=lambda e: order.index(e['source_id'])):
        sid = event['source_id']
        task = F._task_by_label(bound.evidence, sid)
        assert list(task['rows']) == list(event['original_task_ids']), sid
        assert origins[sid] == event['prior_key_origin'], sid
        assert K._sha(raws[sid]) == event['prior_source_raw_sha256'], sid
        two[sid] = [collections.OrderedDict(
            [('source_id', sid), ('raw_sha256', K._sha(raws[sid])),
             ('row', row)]) for row in event['original_task_ids']]
    return two


def collect(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    bound = G._approved_bound()
    shards, raws, origins, bad = F.v6_shards(bound)
    assert not bad, bad
    assert G._sha_file(BINDINGS) == BINDINGS_SHA256
    request = G._read(BINDINGS)
    run_id = E.saved['third_round']
    candidate_dir = E.result['notes']['candidate']
    two = _two_findings(F, K, bound, raws, origins, request)
    assert set(two) == set(FROZEN) - {'packet'}

    # -- 1. THE FROZEN PACKET IS STILL THE FROZEN PACKET --------------------
    before = collections.OrderedDict([
        ('packet_sha256', G._sha_file(str(PACKET / 'RECHECK_PACKET_2123.json'))),
        ('receipt_sha256', G._sha_file(str(RUN / K.RECEIPT_NAME))),
        ('receipt_states', K._load(str(RUN / K.RECEIPT_NAME))['states']),
        ('scripts', collections.OrderedDict(
            (sid, G._sha_file(str(RUN / 'scripts' / ('%s.attempt1.js' % sid))))
            for sid in two))])
    assert before['packet_sha256'] == FROZEN['packet']
    for sid in two:
        assert before['scripts'][sid] == FROZEN[sid][1], sid

    next_bound = X.bind(bound, str(RUN))
    with X.successor_scope(next_bound, two, run_id, E.saved['third_by_event'],
                           E.source_inputs, E.chain, signature=candidate_dir):
        assert F.v6_labels(next_bound) == list(two)
        for sid in two:
            assert K._sha(F.v6_prompt(next_bound, sid)) == FROZEN[sid][0], sid
        # -- 2. RECORD every official state, BEFORE anything parses it ------
        recorded = []
        for state in json.loads(os.environ['A7_RECHECK_STATES']):
            problems = F.record_state(str(RUN), state)
            recorded.append(collections.OrderedDict([
                ('state', state), ('problems', problems),
                ('state_sha256', G._sha_file(state))]))
        receipt = K._load(str(RUN / K.RECEIPT_NAME))
        # -- 3. FINALIZE through the existing owner: paid bytes first -------
        closed = F.finalize(str(RUN), next_bound)
        budget = F.v6_budget(next_bound)
        shards_after = F.v6_shards(next_bound)

    raw_dir = RUN / 'raw'
    kept = collections.OrderedDict(
        (p.name, G._sha_file(str(p))) for p in sorted(raw_dir.glob('*'))) \
        if raw_dir.is_dir() else collections.OrderedDict()
    outcomes = collections.OrderedDict((l, [o, w]) for l, o, w in
                                       closed['outcomes'])
    accepted, _accepted_raws, key_bad = shards_after[0], shards_after[1], shards_after[3]
    changed = collections.OrderedDict()
    for sid in two:
        was, now = K._sha(raws[sid]), K._sha(shards_after[1][sid])
        changed[sid] = collections.OrderedDict([
            ('origin_before', origins[sid]),
            ('origin_after', shards_after[2][sid]),
            ('raw_before', was), ('raw_after', now), ('changed', was != now)])

    report = collections.OrderedDict([
        ('scope', 'the two source-only rechecks, collected through the '
                  'existing owners; no signer, no key publication'),
        ('caller_sha256', G._sha_file(__file__)),
        ('owner_sha256', G._sha_file(X.__file__)),
        ('frozen_before_the_calls', before),
        ('recorded_states', recorded),
        ('receipt_states_after_recording', receipt['states']),
        ('receipt_sha256_after_recording',
         G._sha_file(str(RUN / K.RECEIPT_NAME))),
        ('paid_raw_files', kept),
        ('finalization', collections.OrderedDict([
            ('phase_complete', closed['phase_complete']),
            ('problems', closed['problems']),
            ('outcomes', outcomes), ('ledger', closed['ledger']),
            ('retry', closed['retry']), ('child', closed.get('child')),
            ('harvested_raw', closed['harvested_raw']),
            ('sha256', G._sha_file(str(RUN / K.FINALIZATION_NAME)))])),
        ('call_accounting', collections.OrderedDict([
            ('before_this_collection', budget['before']),
            ('scheduled_here', closed['ledger']['scheduled']),
            ('valid', closed['ledger']['valid']),
            ('invalid_response', closed['ledger']['invalid_response']),
            ('transport_no_answer', closed['ledger']['transport_no_answer']),
            ('unproved', closed['ledger']['unproved']),
            ('missing', closed['ledger']['missing']),
            ('retry_offered', closed['retry']),
            ('retryable_outcomes', list(F.RETRYABLE))])),
        ('key_after', collections.OrderedDict([
            ('sources', len(accepted)), ('problems', key_bad),
            ('the_two', changed),
            ('other_sources_unchanged', all(
                K._sha(shards_after[1][s]) == K._sha(raws[s])
                for s in shards_after[1] if s not in two)),
            ('other_origins_unchanged', all(
                shards_after[2][s] == origins[s]
                for s in shards_after[2] if s not in two))])),
        ('model_calls_started_here', 0)])
    G._write_new(str(OUT / 'COLLECTION_2123.json'), G._pretty(report) + '\n')
    print('COLLECTION_2123', json.dumps(collections.OrderedDict([
        ('outcomes', [[l, o] for l, o, _w in closed['outcomes']]),
        ('phase_complete', closed['phase_complete']),
        ('ledger', closed['ledger']), ('retry', closed['retry']),
        ('key_sources', len(accepted)), ('key_problems', key_bad[:1]),
        ('report_sha256', G._sha_file(str(OUT / 'COLLECTION_2123.json'))),
    ]), sort_keys=False), flush=True)
    return report


E.with_prepared_inputs(collect)
