"""Verify the completed authority round and build its unrun signer packet.

This is an invocation of the existing owners, not a new key or grading rule.
The saved producer is first proved in its original context by E. The current
key then uses the same round binding as preparation and collection. No model
call, signature, lock or grading is performed here.
"""
import importlib.util
import json
import os
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

sys.dont_write_bytecode = True
UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E

owner = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(owner) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
spec = importlib.util.spec_from_file_location(
    'round_owner_candidate2147', owner,
    loader=SourceFileLoader('round_owner_candidate2147', owner))
E.X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E.X)


def files(root):
    return {str(p.relative_to(root)): E.G._sha_file(str(p))
            for p in sorted(root.rglob('*')) if p.is_file()}


def build(_producer, _inputs):
    for rel in ('unit_2063_source_closeout', 'unit_2127_source_context',
                'unit_2128_source_corrections', 'unit_2136_source_questions',
                'unit_2143_source_authority'):
        sys.path.insert(0, str(E.A7 / rel))
    import a7_source_authority_2143 as V
    import a7_round_binding_2136 as B2136
    import a7_round_binding_2143 as B
    import preserve_native_2136 as PR
    import build_final_key_candidate as C

    F, K, G, X, R = E.F, E.K, E.G, E.X, E.R
    packet = UNIT / 'packet_2143'
    before = files(packet)
    proof_path = UNIT / 'SOURCE_RESULT_REVIEW_2147.json'
    proof_sha = 'dfecc9e55b76e82ec5145912574fdf97fed7d98a715f11ad2bd7ebf7a82060d2'
    assert G._sha_file(str(proof_path)) == proof_sha
    proof = K._load(str(proof_path))
    collection = UNIT / 'core_collect2146_a/COLLECTION_2143.json'
    assert G._sha_file(str(collection)) == proof['hashes']['collection']
    collected = K._load(str(collection))

    preserved = PR.preserve(E, X, str(packet), str(proof_path), proof_sha,
                            str(E.out / 'native_evidence'))
    assert len(preserved['preserved']) == 1
    call = preserved['preserved'][0]
    assert (call['run_id'], call['agent_id']) == (proof['run'], proof['agent'])
    assert {f['kind']: f['sha256'] for f in call['files']} == {
        'state': proof['hashes']['state'], 'transcript': proof['hashes']['native']}
    G._write_new(str(E.out / 'PRESERVED_NATIVE.json'), G._pretty(preserved) + '\n')
    print('Native state and transcript preserved against independent proof', flush=True)

    previous = B.pinned(E, B.REVIEW, B.REVIEW_SHA256)
    bb = B.binding(E, X, B2136, V)
    _shards, old_raws, old_origins, bad = B.current_key(E, X, bb)
    assert not bad, bad
    assert {s: K._sha(r) for s, r in old_raws.items()} == previous['all_current_raw_sha256']
    assert old_origins == previous['all_current_origins']
    findings = B.round_findings(E, bb, old_raws)
    bound = X.bind(bb.bound, str(packet))
    with B.scope(E, X, bb, bound, findings, V):
        stale = F._receipt_still_the_proved_one(str(packet), bound)
        assert not stale, stale
        shards, raws, origins, bad = F.v6_shards(bound)
        assert not bad, bad
        assert set(raws) == set(old_raws) == set(shards) == set(origins)
        unaffected = sorted(set(raws) - set(findings))
        for sid in unaffected:
            assert (raws[sid], origins[sid]) == (old_raws[sid], old_origins[sid])
        assert list(findings) == [proof['source_id']]
        assert K._sha(raws[proof['source_id']]) == proof['hashes']['raw']
        gate = F.signing_gate(bound.events, bound)
        ledger = C.signer_ledger_before(bound)

    record = {
        'scope': 'actual completed current-key gate and candidate preparation; no signature or score',
        'caller_sha256': G._sha_file(__file__),
        'round_owner_sha256': G._sha_file(owner),
        'source_review_sha256': proof_sha,
        'collection_sha256': proof['hashes']['collection'],
        'previous_33_source_review_sha256': B.REVIEW_SHA256,
        'source_raw_sha256': {s: K._sha(r) for s, r in raws.items()},
        'source_origins': origins, 'unaffected_sources': unaffected,
        'replaced_sources': list(findings),
        'signing_gate_ok': gate['ok'], 'signing_gate_stops': gate['stops'],
        'counts': gate.get('counts'), 'signer_ledger_before': ledger,
        'original_producer_verified': _producer,
        'packet_files': before, 'model_calls': 0,
    }
    G._write_new(str(E.out / 'CURRENT_KEY_GATE.json'), G._pretty(record) + '\n')
    assert gate['ok'], gate['stops']
    assert ledger == collected['accounting']['before_this_round'] + collected['finalization']['ledger']['scheduled']
    print('Actual current key is clean; counts=' + json.dumps(gate['counts']), flush=True)

    ordinary = E.out / 'ordinary_bound.json'
    wire = {field: getattr(bound, field) for field in (
        'package', 'evidence', 'hr', 'events', 'hr_package', 'corrections',
        'decision', 'decision_correction', 'decision_correction_v5',
        'decision_correction_v6')}
    wire['recovery'] = E.saved['recovery']
    G._write_new(str(ordinary), G._pretty(wire) + '\n')
    old_ordinary = C.ORDINARY
    # The old input is a genuine negative control: it denotes the previously
    # signed key and must never be silently accepted as this corrected key.
    assert C._ordinary_bound() != bound
    candidate = E.out / 'candidate'
    try:
        with B.scope(E, X, bb, bound, findings, V):
            with R._using(C, ORDINARY=str(ordinary)):
                assert C._ordinary_bound() == bound
                hashes, full_counts, counts, manifest = C.build(str(candidate))
                problems = C.verify(str(candidate))
                assert not problems, problems
    except BaseException as exc:
        G._write_new(str(E.out / 'CANDIDATE_FAILURE.json'), G._pretty({
            'type': type(exc).__name__, 'reason': str(exc),
            'ordinary': str(ordinary), 'packet_unchanged': files(packet) == before,
            'model_calls': 0}) + '\n')
        raise
    assert C.ORDINARY == old_ordinary
    identity = K._load(str(candidate / 'key_identity.json'))
    provenance = K._load(str(candidate / 'provenance.json'))
    assert provenance['origins'] == origins
    assert {sid: row['raw_sha256'] for sid, row in
            provenance['provenance']['events'].items()} == record['source_raw_sha256']
    assert str(packet) in identity['runs']
    assert identity['bindings']['v6_correction_receipt']['sha256'] == proof['hashes']['receipt']
    assert identity['bindings']['v6_correction_finalization']['sha256'] == proof['hashes']['finalization']
    assert all(G._sha_file(v['path']) == v['sha256'] for v in identity['bindings'].values())
    assert manifest['budget']['before'] == ledger
    assert manifest['budget']['after_clean'] == ledger + 1
    assert manifest['budget']['worst'] == ledger + F.MAX_ATTEMPTS
    assert manifest['retry_law']['retryable'] == list(F.RETRYABLE)
    assert manifest['shards'] == [{'shard': s, 'sha256': K._sha(raws[s])} for s in raws]
    assert manifest['script_bytes'] < K.TRANSPORT_LIMIT
    assert files(packet) == before
    record.update({
        'ordinary': str(ordinary), 'ordinary_sha256': G._sha_file(str(ordinary)),
        'old_binding_negative_and_current_positive': True,
        'candidate': str(candidate), 'candidate_hashes': hashes,
        'candidate_files': files(candidate), 'candidate_rederived_exactly': True,
        'manifest': manifest, 'counts': counts, 'full_counts': full_counts,
        'packet_unchanged': True, 'signature': 'UNRUN',
    })
    G._write_new(str(E.out / 'CANDIDATE_PREPARATION.json'), G._pretty(record) + '\n')
    print('Candidate and unrun signer verified; ledger before=' + str(ledger), flush=True)
    return record


if __name__ == '__main__':
    E.with_prepared_inputs(build)
