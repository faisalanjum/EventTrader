# -*- coding: utf-8 -*-
"""The thin collection / resume entry for the source-question packet.

Codex SEQ 2136. It saves, proves and accounts through the owners that already
exist - `F.record_state` and `F.finalize` - inside the SAME shared binding the
preparation used. It decides nothing: no verdict, no retry rule, no key edit
and no fallback to an earlier answer. An incomplete or invalid result is
reported exactly as the owners return it.

Execute through unit_1947/ledger/run_real_1947.sh with the frozen map and
environment. A7_COLLECT_REPORT, A7_COLLECT_REPORT_SHA256 and the JSON list
A7_COLLECT_STATES identify the packet and official states. This entry never
launches a model or approves a retry.
"""
import collections
import importlib.util
import json
import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

#: the report fields this entry relies on, checked before anything is recorded
PINS = ('owner_sha256', 'binding_sha256', 'renderer_sha256')


def _pinned_paths(E, X, B):
    """Where each pinned identity lives. Derived, never typed."""
    return collections.OrderedDict([
        ('owner_sha256', X.__file__),
        ('binding_sha256', B.__file__),
        ('renderer_sha256', str(E.A7 / B.RENDERER))])


def collect(E, X, B, B2128, V3, report_path, expected_sha256, states):
    """Record, prove and account one prepared packet. -> the collection record."""
    F, K, G = E.F, E.K, E.G
    got = G._sha_file(report_path)
    if got != expected_sha256:
        raise ValueError('the packet report is %s, not the expected %s'
                         % (got, expected_sha256))
    report = G._read(report_path)
    live = _pinned_paths(E, X, B)
    for pin in PINS:
        actual = G._sha_file(live[pin])
        if report[pin] != actual:
            raise ValueError('%s drifted: %s is %s, not the reported %s'
                             % (pin, live[pin], actual, report[pin]))
    run = report['run_dir']
    wanted = collections.OrderedDict(
        (r['source_id'], r['prompt_sha256']) for r in report['input_declarations'])

    bb = B.binding(E, X, B2128, V3)
    _shards, raws, _origins, bad = B.current_key(E, X, bb)
    if bad:
        raise ValueError('the current key does not read cleanly: %s' % bad[:2])
    findings = B.round_findings(E, bb, raws)
    bound = X.bind(bb.bound, run)

    recorded, receipt_before = [], K._load(os.path.join(run, K.RECEIPT_NAME))
    with B.scope(E, X, bb, bound, findings, V3):
        problems = F.receipt_problems(run, bound, receipt_before)
        if problems:
            raise ValueError("the published receipt is not this binding's: %s"
                             % problems[:2])
        if receipt_before['prompts'] != dict(wanted):
            raise ValueError('the receipt prompts are not the reported ones')
        for state in states:
            recorded.append(collections.OrderedDict([
                ('state', state),
                ('problems', F.record_state(run, state)),
                ('state_sha256', G._sha_file(state)
                 if os.path.isfile(state) else None)]))
        receipt_after = K._load(os.path.join(run, K.RECEIPT_NAME))
        closed = F.finalize(run, bound)
        budget = F.v6_budget(bound)

    raw_dir = os.path.join(run, 'raw')
    return collections.OrderedDict([
        ('scope', 'collection/resume through F.record_state and F.finalize; '
                  'no semantic decision, no retry rule, no key edit'),
        ('report', report_path), ('report_sha256', expected_sha256),
        ('run_dir', run),
        ('pinned_identities', collections.OrderedDict(
            (pin, report[pin]) for pin in PINS)),
        ('events', list(wanted)),
        ('receipt_states_before', list(receipt_before['states'])),
        ('receipt_states_after', list(receipt_after['states'])),
        ('recorded_states', recorded),
        ('finalization', collections.OrderedDict([
            ('phase_complete', closed['phase_complete']),
            ('problems', closed['problems']),
            ('outcomes', [[l, o, w] for l, o, w in closed['outcomes']]),
            ('ledger', closed['ledger']), ('retry', closed['retry']),
            ('child', closed.get('child')),
            ('harvested_raw', closed['harvested_raw']),
            ('sha256', G._sha_file(os.path.join(run, K.FINALIZATION_NAME)))])),
        ('paid_raw_files', collections.OrderedDict(
            (n, G._sha_file(os.path.join(raw_dir, n)))
            for n in sorted(os.listdir(raw_dir)))
         if os.path.isdir(raw_dir) else collections.OrderedDict()),
        ('accounting', collections.OrderedDict([
            ('before_this_round', budget['before']),
            ('scheduled', closed['ledger']['scheduled']),
            ('valid', closed['ledger']['valid']),
            ('invalid_response', closed['ledger']['invalid_response']),
            ('transport_no_answer', closed['ledger']['transport_no_answer']),
            ('unproved', closed['ledger']['unproved']),
            ('missing', closed['ledger']['missing']),
            ('retry_offered', closed['retry']),
            ('retryable_outcomes', list(F.RETRYABLE))])),
        ('model_calls_started_here', 0)])


def _main(E):
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections', 'unit_2136_source_questions'):
        sys.path.insert(0, str(E.A7 / rel))
    import a7_source_context_2127 as V3
    import a7_round_binding_2128 as B2128
    import a7_round_binding_2136 as B

    def run(_producer, _inputs):
        out = E.A7 / 'unit_2136_source_questions' / os.environ['A7_TAG']
        out.mkdir(parents=True)
        record = collect(E, E.X, B, B2128, V3,
                         os.environ['A7_COLLECT_REPORT'],
                         os.environ['A7_COLLECT_REPORT_SHA256'],
                         json.loads(os.environ['A7_COLLECT_STATES']))
        E.G._write_new(str(out / 'COLLECTION_2138.json'),
                       E.G._pretty(record) + '\n')
        print('COLLECTION_2138', json.dumps({
            'phase_complete': record['finalization']['phase_complete'],
            'ledger': record['finalization']['ledger'],
            'retry': record['finalization']['retry']}), flush=True)
        return record

    E.with_prepared_inputs(run)


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                           / 'unit_2020_codex_check'))
    import prepare_g23_partial_2097 as E
    candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
    if E.G._sha_file(candidate) != os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']:
        raise ValueError('the round-input owner is not the pinned candidate')
    spec = importlib.util.spec_from_file_location(
        'round_owner_2138', candidate,
        loader=SourceFileLoader('round_owner_2138', candidate))
    E.X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E.X)
    _main(E)
