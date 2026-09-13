"""Connect the approved partial G1 result to the existing real G2/G3 owner.

No model call or invented verdict. Reuse the signed source-key bindings and
saved producer evaluation from the verified preparation. Never edit them.
"""
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
build = Path(os.environ['A7_REAL_CANDIDATE_BUILD'])
result = json.loads((build / 'RESULT.json').read_text())
saved = json.loads((Path(result['packet']) / 'FINDINGS_BY_EVENT.json').read_text())
os.environ['A7_APPROVED_KEY_DIR'] = result['notes']['candidate']
os.environ['A7_ORDINARY_BOUND'] = result['notes']['ordinary']
for rel in ('unit_2009/owner', 'unit_2023_source_correction',
            'unit_2041_decision_connection', 'unit_2053_owner_retry',
            'unit_2061_settlement_connection', 'unit_2065_closeout_connection',
            'unit_2068_input_recovery', 'unit_2076_latest_source_decisions'):
    sys.path.insert(0, str(A7 / rel))
import a4_review_composite as R
import a4_source_correction as C2023
import a4_source_decision as D
import a4_source_recovery as RECOV
import a4_source_settlement as S
import a4_source_closeout as V
import a4_phase_input as N
import a4_v6_successor_chain as X
import a6_launch_freeze as A6
import a7_prepared_run as PR
import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as GR
import a7_partial_grading_2095 as P

F, K, SK = R.F, R.K, R.SK
preparation = os.environ['A7_VERIFY_PREPARATION']
assert G._sha_file(preparation) == os.environ['A7_VERIFY_PREPARATION_SHA256']
prep = K._load(preparation)
launch_path = os.environ['A7_GRADING_LAUNCH']
assert G._sha_file(launch_path) == os.environ['A7_GRADING_LAUNCH_SHA256']
launch = K._load(launch_path)
g1 = {'candidate_dir': launch['candidate_dir'], 'run_dir': launch['run_dir'],
      'pins': json.loads(os.environ['A7_REVIEW_G1_PINS'])}
assert g1['pins'][P.POLICY_PIN] == os.environ['A7_PARTIAL_POLICY_SHA256']
source_inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                                  'settlement_by_event', 'closeout_by_event')]
chain = tuple((r, f) for r, f in saved['chain'])
phase = K._load(saved['phase_input_binding'])
carrier = K._load(phase['input_binding'])
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()


@F._operation
def with_prepared_inputs(action):
    with R.candidate_scope(saved['review_run'], saved['review_package'],
                           saved['run'], carrier['package']):
        evaluation = K._load(str(Path(prep['evaluation']) / A6.REUSE_FREEZE_NAME))
        try:
            producer = PR.reuse(prep['evaluation'], prep['evaluation_sha256'])
        except ValueError:
            fresh = A6.reuse_freeze(evaluation['run_dir'], evaluation['initial_key_manifest'])
            difference = {k: {'frozen': evaluation.get(k), 'live': fresh.get(k)}
                          for k in set(evaluation) | set(fresh) if evaluation.get(k) != fresh.get(k)}
            G._write_new(str(out / 'EVALUATION_DIFFERENCE.json'), G._pretty(difference) + '\n')
            raise
        assert producer == prep['run']
        with N.input_scope(saved['phase_input_binding']):
            corrected = C2023.bind(SK.bound(saved['run'], carrier['package']), saved['corrections'])
            closed = V.bind(S.bind(D.bind(corrected, saved['decision']),
                                   saved['settlement']), phase['run'])
            bound = X.bind(closed, saved['third_round'])
            with RECOV.recovery_scope(saved['recovery'], corrected, source_inputs[0]), \
                    X.successor_scope(bound, saved['third_by_event'], chain[-1][0],
                                      chain[-1][1], source_inputs, chain[:-1]), \
                    P.scope(os.environ['A7_PARTIAL_POLICY_SHA256']):
                assert G._approved_bound() == bound
                assert G.live_key()[1] == prep['key_identity']
                # Prove and materialize the producer in its ORIGINAL unbound
                # preparation context. Then bind the later grading scorer.
                # The existing single-trace path rechecks the original bytes;
                # the G1 lifecycle separately verifies every grading owner.
                _arms, meta, bad = G.materialize(producer)
                assert not bad and meta['answers'] == prep['population']['answers'], bad
                B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                                      launch['owners']['grading_scorer'])
                assert G.owner_hashes() == launch['owners']
                bench = str(Path(G.__file__).resolve().parents[5])
                inputs = B.load_verified_inputs(evaluation['source_manifest'], producer, bench)
                result = action(producer, inputs)
                assert G.run_of(producer) == producer['run_dir']
                return result


def prepare(producer, inputs):
    doc, prompts, bad = GR.freeze(producer, inputs=inputs, g1=g1,
                                 audit_root=str(out / 'route'))
    assert not bad, bad
    assert doc['producer_identity'] == producer
    assert doc['g1_identity'] == B.g1_identity(g1)
    assert doc['materialization']['answers'] == prep['population']['answers']
    assert not doc['g3']['unroutable']
    previous_path = os.environ.get('A7_VERIFY_G23_PREPARATION')
    previous = None
    if previous_path:
        assert G._sha_file(previous_path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
        previous = K._load(previous_path)
        frozen_path = Path(previous_path).parent / GR.CANDIDATE_NAME
        frozen = K._load(str(frozen_path))
        difference = {k: {'frozen': frozen.get(k), 'live': doc.get(k)}
                      for k in set(frozen) | set(doc)
                      if G._plain(frozen.get(k)) != G._plain(doc.get(k))}
        if difference:
            G._write_new(str(out / 'COLD_DIFFERENCE.json'), G._pretty(difference) + '\n')
        assert not difference, 'cold G2/G3 derivation changed'
    candidates = {}
    for kind in GR.KIND_RULES:
        if previous:
            path, digest = (previous['candidates'][kind][k] for k in ('path', 'sha256'))
        else:
            path, digest = GR.write_kind(str(out / kind), kind, doc, prompts,
                                        prep['key_identity'])
        candidate, _ = G.load_frozen(str(Path(path).parent), digest)
        assert candidate['g1_identity'] == B.g1_identity(g1)
        assert candidate['questions'] == doc[kind.lower()]['questions']
        rows = [r for r in doc['batching']['rows'] if r['batch_id'].startswith(kind + '-')]
        assert G._plain(candidate) == G._plain(GR.kind_candidate(kind, doc, rows, prep['key_identity']))
        for row in rows:
            assert (Path(path).parent / row['prompt_path']).read_text() == prompts[row['batch_id']]
        candidates[kind] = {'path': path, 'sha256': digest}
    findings = {leg: B.official_safety_findings(leg, g1, producer)
                for leg in sorted(set(doc['materialization']['legs']) | {G.LEG_UNION})}
    # Every reported missing event stays in the same signed key.
    key, _ = G.live_key()
    for finding in findings.values():
        for gap in finding['incomplete']:
            assert gap['sid'] in key and gap['ruled'] == 0
    if not previous:
        G._write_new(str(out / GR.CANDIDATE_NAME), G._pretty(doc) + '\n')
    report = {'scope': 'REAL partial G1 to G2/G3 preparation, zero model calls; NOT an A7 score',
              'producer': producer, 'g1': g1, 'findings': findings,
              'candidates': candidates, 'remaining_calls': doc['remaining_calls'],
              'g2': doc['g2'], 'g3': doc['g3'], 'key_identity': prep['key_identity'],
              'cold_verified_from': previous_path,
              'full_key_fact_count': sum(len(G.accepted_positions(v)) for v in key.values())}
    G._write_new(str(out / 'PREPARATION.json'), G._pretty(report) + '\n')
    print(G._plain(report), flush=True)
    return report


if __name__ == '__main__':
    with_prepared_inputs(prepare)
