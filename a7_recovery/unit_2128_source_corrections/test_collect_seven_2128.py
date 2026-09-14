"""The focused proof of the collection entry, on an ISOLATED zero-call probe.

It invokes the REAL entry - `collect_seven_2128.collect` - never a copy of it.
The probe packet is prepared through `F.prepare_v6` under the SAME shared
binding, and no model response is faked: seven uncalled events must come back
missing through the owners, never accepted and never inherited from an earlier
answer. The real seven-source packet is hashed before and after and must not
move.
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
    'round_candidate_2129t', candidate,
    loader=SourceFileLoader('round_candidate_2129t', candidate))
E.X = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E.X)

U = E.A7 / 'unit_2128_source_corrections'
OUT = U / os.environ['A7_TAG']
#: the real packet, which must stay byte-identical and unrun
REAL = U / 'core_pkt2128_d/seven_source_packet'
REAL_REPORT = U / 'core_pkt2128_d/SEVEN_SOURCE_PACKET_2128.json'
#: root's independent rerun of the preparation must have finished first
GATE = E.A7 / 'unit_1947/logs/attempt_codex_pkt2129_verify/exit'


def _tree(root):
    return collections.OrderedDict(
        (str(p.relative_to(root)), E.G._sha_file(str(p)))
        for p in sorted(Path(root).rglob('*')) if p.is_file())


def run(_producer, _inputs):
    F, K, X, G = E.F, E.K, E.X, E.G
    OUT.mkdir(parents=True)
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections'):
        sys.path.insert(0, str(E.A7 / rel))
    import a4_source_taskv2 as V2                                 # noqa: E402
    import a7_source_context_2127 as V3                           # noqa: E402
    import a7_round_binding_2128 as B                             # noqa: E402
    import collect_seven_2128 as C                                # noqa: E402

    # ---- the interface this test requires --------------------------------
    assert callable(getattr(C, 'collect', None)), \
        'the collection entry collect_seven_2128.collect is missing'
    assert C.PINS == ('owner_sha256', 'binding_sha256', 'renderer_sha256')

    real_before = _tree(REAL)
    b = B.binding(E, X)
    _shards, raws, _origins, bad = B.current_key(E, X, b)
    assert not bad, bad[:2]
    findings = B.round_findings(E, b, raws)

    # ---- an isolated, clearly named ZERO-CALL probe packet ---------------
    probe = OUT / 'zero_call_probe_packet'
    probe_bound = X.bind(b.bound, str(probe))
    with B.scope(E, X, b, probe_bound, findings, V2, V3):
        prepared = F.prepare_v6(str(probe), probe_bound)
        assert prepared['ok'], prepared['problems']
        receipt = K._load(str(probe / K.RECEIPT_NAME))
    assert receipt['states'] == []
    pins = C._pinned_paths(E, X)
    probe_report = collections.OrderedDict([
        ('scope', 'ZERO-CALL PROBE packet: prepared, never called. Not a key '
                  'round and never to be collected as one.'),
        ('run_dir', str(probe)),
        ('input_declarations', [collections.OrderedDict(
            [('source_id', sid), ('prompt_sha256', receipt['prompts'][sid])])
            for sid in receipt['allowed']])]
        + [(pin, G._sha_file(pins[pin])) for pin in C.PINS])
    report_path = str(OUT / 'ZERO_CALL_PROBE_REPORT.json')
    G._write_new(report_path, G._pretty(probe_report) + '\n')
    report_sha = G._sha_file(report_path)

    # ---- the REAL entry, with no states at all ---------------------------
    first = C.collect(E, X, B, V2, V3, report_path, report_sha, [])
    outcomes = [o for _l, o, _w in first['finalization']['outcomes']]
    assert outcomes == ['missing'] * 7, outcomes
    assert first['finalization']['ledger']['valid'] == 0
    assert first['finalization']['ledger']['scheduled'] == 7
    assert not first['finalization']['phase_complete']
    assert first['finalization']['retry'] == []
    assert first['finalization']['child'] is None
    assert first['paid_raw_files'] == collections.OrderedDict()
    assert first['accounting']['before_this_round'] == 670

    # ---- idempotent resume ----------------------------------------------
    second = C.collect(E, X, B, V2, V3, report_path, report_sha, [])
    assert second['finalization']['outcomes'] == first['finalization']['outcomes']
    assert second['finalization']['sha256'] == first['finalization']['sha256']
    assert second['receipt_states_after'] == []
    assert second['events'] == first['events']

    # ---- interface refusals, each after a valid control ------------------
    negatives = []

    def refuses(name, action):
        assert C.collect(E, X, B, V2, V3, report_path, report_sha,
                         [])['events'] == first['events']
        try:
            action()
        except ValueError as exc:
            negatives.append(collections.OrderedDict(
                [('case', name), ('reason', str(exc)[:200])]))
        else:
            raise AssertionError('did not refuse ' + name)

    refuses('wrong_report_hash', lambda: C.collect(
        E, X, B, V2, V3, report_path, '0' * 64, []))
    drifted = copy.deepcopy(probe_report)
    drifted['renderer_sha256'] = '0' * 64
    drifted_path = str(OUT / 'DRIFTED_BINDING_REPORT.json')
    G._write_new(drifted_path, G._pretty(drifted) + '\n')
    refuses('drifted_binding_identity', lambda: C.collect(
        E, X, B, V2, V3, drifted_path, G._sha_file(drifted_path), []))

    real_after = _tree(REAL)
    record = collections.OrderedDict([
        ('scope', 'focused proof of the collection entry on an isolated '
                  'zero-call probe; no model call, no faked response'),
        ('root_gate_exit', GATE.read_text().strip()),
        ('entry', 'collect_seven_2128.collect'),
        ('entry_sha256', G._sha_file(str(U / 'collect_seven_2128.py'))),
        ('caller_sha256', G._sha_file(__file__)),
        ('required_inputs', ['A7_COLLECT_REPORT', 'A7_COLLECT_REPORT_SHA256',
                             'A7_COLLECT_STATES']),
        ('probe_run_dir', str(probe)),
        ('probe_report_sha256', report_sha),
        ('probe_events', receipt['allowed']),
        ('probe_largest_script_bytes', prepared['largest_script_bytes']),
        ('first_collection', collections.OrderedDict([
            ('outcomes', first['finalization']['outcomes']),
            ('ledger', first['finalization']['ledger']),
            ('phase_complete', first['finalization']['phase_complete']),
            ('retry', first['finalization']['retry']),
            ('problems', first['finalization']['problems']),
            ('finalization_sha256', first['finalization']['sha256'])])),
        ('resume_is_idempotent', collections.OrderedDict([
            ('outcomes_identical', True), ('finalization_identical', True),
            ('states_still_empty', second['receipt_states_after'] == [])])),
        ('negative_controls', negatives),
        ('real_packet_unchanged', real_before == real_after),
        ('real_packet_files', len(real_after)),
        ('real_packet_states',
         K._load(str(REAL / K.RECEIPT_NAME))['states']),
        ('real_packet_has_no_finalization',
         not (REAL / K.FINALIZATION_NAME).exists()),
        ('real_report_sha256', G._sha_file(str(REAL_REPORT))),
        ('model_calls', 0)])
    assert record['real_packet_unchanged']
    assert record['real_packet_has_no_finalization']
    G._write_new(str(OUT / 'COLLECT_PROOF_2129.json'), G._pretty(record) + '\n')
    print('COLLECT_PROOF_2129', json.dumps(collections.OrderedDict([
        ('probe_outcomes', sorted({o for _l, o, _w in first['finalization']['outcomes']})),
        ('ledger', first['finalization']['ledger']),
        ('resume_identical', True),
        ('negatives', [n['case'] for n in negatives]),
        ('real_packet_unchanged', record['real_packet_unchanged']),
        ('proof_sha256', G._sha_file(str(OUT / 'COLLECT_PROOF_2129.json'))),
    ])), flush=True)
    return record


assert GATE.is_file(), 'root packet verification has not finished: %s' % GATE
assert GATE.read_text().strip() == '0', \
    'root packet verification exited %r' % GATE.read_text().strip()
E.with_prepared_inputs(run)
