"""Read the completed eight-source packet through its real current owners.

No model, signer, candidate or source edit. Preserve the packet and compare
all carried sources against the independently frozen pre-round raw hashes.
Report the actual signing gate, including failures, without promoting it.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare_g23_partial_2097 as E

candidate = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
if E.G._sha_file(candidate) != os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']:
    raise ValueError('round-input owner differs from its frozen identity')
spec = importlib.util.spec_from_file_location('round_owner_review_2141', candidate)
E.X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E.X)
UNIT = E.A7 / 'unit_2136_source_questions'


def tree(root):
    return {str(p.relative_to(root)): E.G._sha_file(str(p))
            for p in sorted(root.rglob('*')) if p.is_file()}


def review(_producer, _inputs):
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections', 'unit_2136_source_questions'):
        sys.path.insert(0, str(E.A7 / rel))
    import a7_source_context_2127 as V3
    import a7_round_binding_2128 as B2128
    import a7_round_binding_2136 as B
    import collect_questions_2136 as C

    F, K, G, X = E.F, E.K, E.G, E.X
    packet = UNIT / 'packet_2136'
    before = tree(packet)
    report = UNIT / 'QUESTION_PACKET_2136.json'
    report_sha = '8f8739445058e4874643648c68795bd7a7b79b77f770cf3b7accc03d8114420d'
    old_result = UNIT / 'core_collect2140_a/COLLECTION_2138.json'
    old_sha = 'd61ef95466997a6a4f2dce0d9c672f9379eb4b7d9887215bada04e3260df93c8'
    expected_path = E.A7 / 'unit_2020_codex_check/codex_rootflow2134_b/COLD_HISTORY.json'
    expected_sha = '05f7372bc0807aeb45f3fdcd229424ea4063bf05c5ff2fa13050e007084729ff'
    assert G._sha_file(str(old_result)) == old_sha
    assert G._sha_file(str(expected_path)) == expected_sha
    previous = K._load(str(old_result))
    expected_before = K._load(str(expected_path))['raw_hashes']
    states = K._load(str(packet / K.RECEIPT_NAME))['states']
    assert states == previous['receipt_states_after']

    collected = C.collect(E, X, B, B2128, V3, str(report), report_sha, states)
    assert collected['finalization'] == previous['finalization']
    assert collected['paid_raw_files'] == previous['paid_raw_files']
    assert collected['receipt_states_before'] == states
    assert collected['receipt_states_after'] == states
    # K.record_state rejects duplicate appends. These eight states already
    # belong to the immutable completed receipt; finalization must still agree.
    assert len(collected['recorded_states']) == len(states)
    assert all(r['problems'] == ['that state is already recorded']
               for r in collected['recorded_states'])
    print('Repeated actual collection agrees in every finalization field', flush=True)

    bb = B.binding(E, X, B2128, V3)
    _old_shards, old_raws, old_origins, bad = B.current_key(E, X, bb)
    assert not bad, bad
    assert {s: K._sha(r) for s, r in old_raws.items()} == expected_before
    findings = B.round_findings(E, bb, old_raws)
    bound = X.bind(bb.bound, str(packet))
    with B.scope(E, X, bb, bound, findings, V3):
        shards, raws, origins, bad = F.v6_shards(bound)
        assert not bad, bad
        assert set(raws) == set(old_raws) == set(shards) == set(origins)
        untouched = sorted(set(raws) - set(findings))
        for sid in untouched:
            assert raws[sid] == old_raws[sid]
            assert origins[sid] == old_origins[sid]
        for sid in findings:
            assert raws[sid] == K._read(str(packet / 'raw' / (sid + '.attempt1.proved.json')))
        print('All current source raws and unaffected origins agree', flush=True)
        gate = F.signing_gate(bound.events, bound)

    assert tree(packet) == before, 'verification changed completed packet bytes'
    record = {
        'scope': 'actual completed source collection, current materialization and signing-gate diagnostic; no source-meaning approval',
        'caller_sha256': G._sha_file(__file__),
        'round_owner_sha256': G._sha_file(candidate),
        'collection_sha256': old_sha,
        'external_pre_round_sha256': expected_sha,
        'repeated_finalization_identical': True,
        'duplicate_record_outcomes': collected['recorded_states'],
        'all_current_raw_sha256': {s: K._sha(r) for s, r in raws.items()},
        'all_current_origins': origins,
        'unaffected_sources': untouched,
        'replaced_sources': list(findings),
        'original_rows_in_this_round': sum(len(F._task_by_label(bound.evidence, s)['rows']) for s in findings),
        'open_issues_by_source': {s: sh['open_issues'] for s, sh in shards.items() if sh['open_issues']},
        'signing_gate_ok': gate['ok'],
        'signing_gate_stops': gate['stops'],
        'counts': gate.get('counts'),
        'packet_unchanged': True,
        'packet_files': before,
        'model_calls': 0,
    }
    G._write_new(str(E.out / 'EIGHT_SOURCE_REVIEW_2141.json'), G._pretty(record) + '\n')
    print('EIGHT_SOURCE_REVIEW_2141', json.dumps({
        'sources': len(raws), 'unaffected': len(untouched),
        'gate_ok': gate['ok'], 'stops': gate['stops'],
        'packet_unchanged': True}), flush=True)
    return record


E.with_prepared_inputs(review)
