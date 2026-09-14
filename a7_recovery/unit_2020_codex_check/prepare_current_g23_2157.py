"""Prove completed G1 reuse, then derive the real current meaning/extra inputs.

Uses the existing native reader, reconciliation, routing and packet owners.
No verdict transfer, new scoring rule, or model call happens here.
"""
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2143_source_authority'))
from build_candidate_2148 import E
import a7_g1_key_reuse_2152 as REUSE
import a7_grading_script_binding_2156 as TRANSPORT

G, B, GR = E.G, E.B, E.GR
input_path = os.environ['A7_CURRENT_G23_INPUT']
assert G._sha_file(input_path) == os.environ['A7_CURRENT_G23_INPUT_SHA256']
approved = G._read(input_path)
assert G._sha_file(approved['report']) == approved['report_sha256']
key_report = G._read(approved['report'])


def prepare(producer, inputs, g1):
    root, candidate, lanes = B._lifecycle(g1)
    missing = [r['lane_id'] for r in root['rows'] if lanes[r['lane_id']]['selected'] is None]
    assert len(lanes) == approved['expected_total_lanes']
    assert len(lanes) - len(missing) == approved['expected_valid_lanes']
    assert missing == approved['expected_exhausted_invalid_lanes']
    assert all(lanes[lane]['attempts'] == {n: False for n in range(1, root['max_attempts'] + 1)}
               for lane in missing)
    assert candidate['producer_identity'] == producer
    resolutions = B.official_resolutions(g1, producer)
    g1_review = dict(scope='ACTUAL full G1 lifecycle and resolution consumer; not a final score',
                     producer=producer, g1=g1, root_lanes=len(lanes),
                     valid_lanes=len(lanes)-len(missing),
                     exhausted_invalid={lane: lanes[lane] for lane in missing},
                     resolutions={leg: [[list(key), value] for key, value in sorted(rows.items())]
                                  for leg, rows in resolutions.items()},
                     key_identity=G.live_key()[1])
    assert g1_review['key_identity'] == key_report['key_identity']
    G._write_new(str(E.out / 'CURRENT_G1_VERIFIED.json'), G._pretty(g1_review) + '\n')
    print('Current full G1 consumer:', len(lanes)-len(missing), 'valid;',
          len(missing), 'exhausted invalid. Deriving actual G2/G3 inputs.', flush=True)
    doc, prompts, bad = GR.freeze(producer, inputs=inputs, g1=g1,
                                 audit_root=str(E.out / 'route'))
    assert not bad, bad
    assert doc['producer_identity'] == producer
    assert doc['g1_identity'] == B.g1_identity(g1)
    assert doc['key_identity'] == key_report['key_identity']
    assert not doc['g3']['unroutable']
    G._write_new(str(E.out / GR.CANDIDATE_NAME), G._pretty(doc) + '\n')
    candidates = {}
    for kind in GR.KIND_RULES:
        path, digest = GR.write_kind(str(E.out / kind), kind, doc, prompts, doc['key_identity'])
        frozen, _ = G.load_frozen(str(Path(path).parent), digest)
        rows = [r for r in doc['batching']['rows'] if r['batch_id'].startswith(kind + '-')]
        assert G._plain(frozen) == G._plain(GR.kind_candidate(kind, doc, rows, doc['key_identity']))
        for row in rows:
            assert (Path(path).parent / row['prompt_path']).read_text() == prompts[row['batch_id']]
        candidates[kind] = dict(path=path, sha256=digest)
    report = dict(scope='ACTUAL current-key BASE G2/G3 population; corrected renderer/reuse selection still required; NOT launch approval',
                  input_path=input_path, input_sha256=G._sha_file(input_path),
                  producer=producer, g1=g1, key_identity=doc['key_identity'],
                  candidates=candidates, g2=doc['g2'], g3=doc['g3'],
                  full_candidate=str(E.out / GR.CANDIDATE_NAME),
                  full_candidate_sha256=G._sha_file(str(E.out / GR.CANDIDATE_NAME)),
                  full_primary_population_before_reuse=doc['remaining_calls'],
                  new_model_calls=0)
    G._write_new(str(E.out / 'CURRENT_G23_PREPARATION.json'), G._pretty(report) + '\n')
    print('Current G2/G3 populations:', G._plain(doc['g2']), G._plain(doc['g3']), flush=True)
    return report


with TRANSPORT.scope(approved['script_binding'], approved['g1']['pins']):
    REUSE.evaluate(E, approved['report'], approved['g1'], prepare)
assert G._sha_file(input_path) == os.environ['A7_CURRENT_G23_INPUT_SHA256']
print('Completed G1 proof/current G2/G3 preparation; no model call.', flush=True)
