# -*- coding: utf-8 -*-
"""The thin collection / resume entry for the seven-source packet.

Codex SEQ 2129. It saves, proves and accounts through the owners that already
exist - `F.record_state` and `F.finalize` - inside the SAME shared binding the
preparation used, so the served wording and every pointer come from one place.

It decides nothing. There is no verdict, no retry rule, no key edit and no
fallback to an earlier answer here; an incomplete or invalid result is reported
exactly as the owners return it.

REQUIRED INPUTS, and there are only three:

  A7_COLLECT_REPORT         the frozen packet report to collect against
  A7_COLLECT_REPORT_SHA256  that report's expected sha256
  A7_COLLECT_STATES         JSON list of official workflow state paths

Run it the way every other payload in this lane runs, through
`unit_1947/ledger/run_real_1947.sh` with the real map and environment.
"""
import collections
import json
import os
import sys
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path

#: the report fields this entry relies on, checked before anything is recorded
PINS = ('owner_sha256', 'binding_sha256', 'renderer_sha256')


def _pinned_paths(E, X):
    """Where each pinned identity lives. Derived, never typed."""
    U = E.A7 / 'unit_2128_source_corrections'
    return collections.OrderedDict([
        ('owner_sha256', X.__file__),
        ('binding_sha256', str(U / 'a7_round_binding_2128.py')),
        ('renderer_sha256', str(E.A7 / 'unit_2127_source_context'
                                / 'a7_source_context_2127.py'))])


def collect(E, X, B, V2, V3, report_path, expected_sha256, states):
    """Record, prove and account one prepared packet. -> the collection record.

    Every judgement below belongs to `F.record_state` and `F.finalize`; this
    reads the report, checks the identities it depends on, and reports what
    those owners returned.
    """
    F, K, G = E.F, E.K, E.G
    got = G._sha_file(report_path)
    if got != expected_sha256:
        raise ValueError('the packet report is %s, not the expected %s'
                         % (got, expected_sha256))
    report = G._read(report_path)
    live = _pinned_paths(E, X)
    for pin in PINS:
        actual = G._sha_file(live[pin])
        if report[pin] != actual:
            raise ValueError('%s drifted: %s is %s, not the reported %s'
                             % (pin, live[pin], actual, report[pin]))
    run = report['run_dir']
    wanted = collections.OrderedDict(
        (r['source_id'], r['prompt_sha256']) for r in report['input_declarations'])

    b = B.binding(E, X)
    bound = X.bind(b.bound, run)
    # the served findings come from the live current key, through the owner
    _shards, raws, _origins, bad = B.current_key(E, X, b)
    if bad:
        raise ValueError('the current key does not read cleanly: %s' % bad[:2])
    findings = B.round_findings(E, b, raws)

    recorded, receipt_before = [], K._load(os.path.join(run, K.RECEIPT_NAME))
    with B.scope(E, X, b, bound, findings, V2, V3):
        # IDENTITY FIRST, through the receipt's own owner: the published
        # receipt must still be the one this binding expects, and its prompt
        # block must still be the report's. Both survive a resume, which the
        # raw receipt hash does not once a state has been appended.
        problems = F.receipt_problems(run, bound, receipt_before)
        if problems:
            raise ValueError('the published receipt is not this binding\'s: %s'
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

    raw_dir = Path(run) / 'raw'
    return collections.OrderedDict([
        ('scope', 'collection/resume through F.record_state and F.finalize; '
                  'no semantic decision, no retry rule, no key edit'),
        ('report', report_path), ('report_sha256', expected_sha256),
        ('run_dir', run),
        ('pinned_identities', collections.OrderedDict(
            (pin, report[pin]) for pin in PINS)),
        ('events', list(wanted)),
        ('receipt_sha256_before', G._sha_file(
            os.path.join(run, K.RECEIPT_NAME)) if not states else None),
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
            (p.name, G._sha_file(str(p))) for p in sorted(raw_dir.glob('*')))
         if raw_dir.is_dir() else collections.OrderedDict()),
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
    sys.path.insert(0, str(E.A7 / 'unit_2063_source_closeout'))
    sys.path.insert(0, str(E.A7 / 'unit_2127_source_context'))
    sys.path.insert(0, str(E.A7 / 'unit_2128_source_corrections'))
    import a4_source_taskv2 as V2                                 # noqa: E402
    import a7_source_context_2127 as V3                           # noqa: E402
    import a7_round_binding_2128 as B                             # noqa: E402

    def run(_producer, _inputs):
        out = E.A7 / 'unit_2128_source_corrections' / os.environ['A7_TAG']
        out.mkdir(parents=True, exist_ok=True)
        record = collect(E, E.X, B, V2, V3,
                         os.environ['A7_COLLECT_REPORT'],
                         os.environ['A7_COLLECT_REPORT_SHA256'],
                         json.loads(os.environ['A7_COLLECT_STATES']))
        E.G._write_new(str(out / 'COLLECTION_2129.json'),
                       E.G._pretty(record) + '\n')
        print('COLLECTION_2129', json.dumps(collections.OrderedDict([
            ('outcomes', [[l, o] for l, o, _w in record['finalization']['outcomes']]),
            ('phase_complete', record['finalization']['phase_complete']),
            ('ledger', record['finalization']['ledger']),
            ('retry', record['finalization']['retry']),
        ])), flush=True)
        return record

    E.with_prepared_inputs(run)


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                           / 'unit_2020_codex_check'))
    import prepare_g23_partial_2097 as _E                         # noqa: E402
    _candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
    assert _E.G._sha_file(_candidate) == os.environ[
        'A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
    _spec = importlib.util.spec_from_file_location(
        'round_candidate_2129', _candidate,
        loader=SourceFileLoader('round_candidate_2129', _candidate))
    _E.X = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_E.X)
    _main(_E)
