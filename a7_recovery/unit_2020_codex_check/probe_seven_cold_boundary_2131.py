"""Read-only proof of the completed seven-source round as a predecessor.

No calls, candidate creation, key edits or new lifecycle. Exercise the actual
current scope first, then the existing cold predecessor reader. The report
records a refusal honestly; a completed diagnostic is not a passing boundary.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import prepare_g23_partial_2097 as E

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
spec = importlib.util.spec_from_file_location('cold_seven_owner_2131', candidate)
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)
E.X = X


def probe(_producer, _inputs):
    F = E.F
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections'):
        sys.path.insert(0, str(E.A7 / rel))
    import a4_source_taskv2 as V2
    import a7_source_context_2127 as V3
    import a7_round_binding_2128 as B
    b = B.binding(E, X)
    _key, raws, _origins, bad = B.current_key(E, X, b)
    assert not bad, bad[:3]
    findings = B.round_findings(E, b, raws)
    run = str(E.A7 / 'unit_2128_source_corrections/core_pkt2128_d/seven_source_packet')
    bound = X.bind(b.bound, run)

    def cold(action):
        with E.R._using(F, _OP_DEPTH=[0]):
            return F._operation(action)()

    with B.scope(E, X, b, bound, findings, V2, V3):
        present = cold(lambda: F.v6_shards(bound))
    assert not present[3] and len(present[0]) == 33, present[3][:3]
    expected_raws = {sid: E.K._sha(raw) for sid, raw in present[1].items()}
    report = {
        'scope': __doc__, 'caller_sha256': E.G._sha_file(__file__),
        'owner_sha256': E.G._sha_file(candidate), 'run': run,
        'positive_sources': len(present[0]), 'raw_hashes': expected_raws,
        'receipt_sha256': E.G._sha_file(os.path.join(run, E.K.RECEIPT_NAME)),
        'finalization_sha256': E.G._sha_file(os.path.join(run, E.K.FINALIZATION_NAME)),
        'model_calls': 0,
    }
    try:
        got = cold(lambda: X.first_round_key(
            b.bound, run, findings, E.source_inputs,
            b.prior + ((b.predecessor, b.predecessor_findings),),
            signatures=b.signatures))
        report['cold_problems'] = got[3]
        report['cold_sources'] = len(got[0])
        report['cold_matches_current_raws'] = {
            sid: E.K._sha(raw) for sid, raw in got[1].items()} == expected_raws
        report['cold_boundary_verified'] = not got[3] and report['cold_matches_current_raws']
    except (ValueError, AssertionError, SystemExit) as exc:
        report['cold_exception'] = type(exc).__name__
        report['cold_problems'] = [str(exc)]
        report['cold_boundary_verified'] = False
    out = E.A7 / 'unit_2020_codex_check' / os.environ['A7_TAG']
    # E.with_prepared_inputs already owns this output directory. The report
    # writer below still refuses to overwrite an existing result.
    E.G._write_new(str(out / 'COLD_SEVEN_BOUNDARY.json'), E.G._pretty(report) + '\n')
    print('COLD_SEVEN_BOUNDARY', json.dumps(report), flush=True)


E.with_prepared_inputs(probe)
