"""Actual source-question connection proof, on a never-launched probe only.

The expected 33 raw hashes are independently frozen outside this binding.
No synthetic model result, source/key edit, model call or new scoring rule.
"""
import collections
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(candidate) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
spec = importlib.util.spec_from_file_location('round_owner_check_2138', candidate)
E.X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E.X)
U = E.A7 / 'unit_2136_source_questions'
OUT = U / os.environ['A7_TAG']


def tree(root):
    return {str(p.relative_to(root)): E.G._sha_file(str(p))
            for p in sorted(root.rglob('*')) if p.is_file()}


def run(_producer, _inputs):
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections', 'unit_2136_source_questions'):
        sys.path.insert(0, str(E.A7 / rel))
    import a7_source_context_2127 as V3
    import a7_round_binding_2128 as B2128
    import a7_round_binding_2136 as B
    import prepare_questions_2136 as P
    import collect_questions_2136 as C

    F, K, G, X = E.F, E.K, E.G, E.X
    OUT.mkdir(parents=True)
    actual = U / 'packet_2136'
    actual_before = tree(actual)
    assert K._load(str(actual / K.RECEIPT_NAME))['states'] == []
    assert not (actual / K.FINALIZATION_NAME).exists()
    expected_path = E.A7 / 'unit_2020_codex_check/codex_rootflow2134_b/COLD_HISTORY.json'
    expected_sha = '05f7372bc0807aeb45f3fdcd229424ea4063bf05c5ff2fa13050e007084729ff'
    assert G._sha_file(str(expected_path)) == expected_sha
    expected = K._load(str(expected_path))['raw_hashes']

    bb = B.binding(E, X, B2128, V3)
    _shards, raws, origins, bad = B.current_key(E, X, bb)
    assert not bad, bad
    assert {s: K._sha(r) for s, r in raws.items()} == expected
    findings = B.round_findings(E, bb, raws)
    untouched = sorted(set(raws) - set(findings))
    probe = OUT / 'UNLAUNCHED_ZERO_ANSWER_PROBE'
    bound = X.bind(bb.bound, str(probe))
    with B.scope(E, X, bb, bound, findings, V3):
        _shards, carried, carried_origins, bad = F.v5_shards(bound)
        assert not bad, bad
        assert carried == raws and carried_origins == origins
    report = P.prepare(E, X, B, B2128, V3, str(probe))
    report_path = str(OUT / 'PROBE_REPORT.json')
    G._write_new(report_path, G._pretty(report) + '\n')
    report_sha = G._sha_file(report_path)
    assert report['events'] == list(findings)
    assert sum(report['rows_served'].values()) == 52
    assert sum(report['findings_served'].values()) == 13
    assert report['accounting']['before_this_round'] == 677
    assert report['receipt_states'] == [] and not report['capacity_problems']
    pristine_receipt_sha = G._sha_file(str(probe / K.RECEIPT_NAME))

    def collect():
        return C.collect(E, X, B, B2128, V3, report_path, report_sha, [])

    first = collect()
    assert first['finalization']['ledger'] == {
        'scheduled': len(findings), 'valid': 0, 'invalid_response': 0,
        'transport_no_answer': 0, 'unproved': 0, 'missing': len(findings)}
    assert all(o == 'missing' and w == 'no official state'
               for _sid, o, w in first['finalization']['outcomes'])
    assert not first['finalization']['phase_complete']
    assert not first['finalization']['problems']
    assert first['finalization']['retry'] == []
    assert first['finalization']['child'] is None
    assert not first['paid_raw_files']
    second = collect()
    assert second['finalization'] == first['finalization']
    assert second['receipt_states_after'] == []
    assert G._sha_file(str(probe / K.RECEIPT_NAME)) == pristine_receipt_sha

    # Every reported dependency pin must refuse drift before recording a state.
    refusals = []
    for pin in C.PINS:
        changed = copy.deepcopy(report)
        changed[pin] = '0' * 64
        path = str(OUT / ('DRIFTED_' + pin + '.json'))
        G._write_new(path, G._pretty(changed) + '\n')
        try:
            C.collect(E, X, B, B2128, V3, path, G._sha_file(path), [])
        except ValueError as exc:
            assert pin + ' drifted:' in str(exc), str(exc)
            refusals.append({'pin': pin, 'reason': str(exc)})
        else:
            raise AssertionError('accepted changed dependency ' + pin)
    assert collect()['finalization'] == first['finalization']
    assert tree(actual) == actual_before
    record = {
        'scope': 'actual preparation/collection/resume on an isolated unlaunched probe; not source-truth or A7 approval',
        'caller_sha256': G._sha_file(__file__),
        'collector_sha256': G._sha_file(C.__file__),
        'binding_sha256': G._sha_file(B.__file__),
        'owner_sha256': G._sha_file(candidate),
        'external_expected_sha256': expected_sha,
        'current_raw_hashes': expected,
        'all_current_sources': len(raws),
        'unchanged_sources': untouched,
        'entire_key_and_origins_carried': True,
        'probe_report': report_path, 'probe_report_sha256': report_sha,
        'probe_run': str(probe),
        'full_rows': sum(report['rows_served'].values()),
        'question_rows': sum(report['findings_served'].values()),
        'before_this_round': report['accounting']['before_this_round'],
        'first_collection': first,
        'empty_resume_identical': True,
        'dependency_pin_refusals': refusals,
        'actual_packet_unchanged': True,
        'actual_packet_files': actual_before,
        'model_calls': 0}
    G._write_new(str(OUT / 'CONNECTION_2138.json'), G._pretty(record) + '\n')
    print('CONNECTION_2138', json.dumps({
        'sources': len(raws), 'unchanged': len(untouched),
        'ledger': first['finalization']['ledger'],
        'pin_refusals': len(refusals), 'resume_identical': True,
        'actual_packet_unchanged': True}), flush=True)
    return record


E.with_prepared_inputs(run)
