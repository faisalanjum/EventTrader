"""Freeze the real G1 grading population over the locked key and saved answers.

Only existing key, reuse, materialization, matching and prompt owners run.
No model is called; no historical answer, key or native evidence is changed.
"""
import collections
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
build = Path(os.environ['A7_REAL_CANDIDATE_BUILD'])
result = json.loads((build / 'RESULT.json').read_text())
saved = json.loads((Path(result['packet']) / 'FINDINGS_BY_EVENT.json').read_text())
candidate = Path(result['notes']['candidate'])
os.environ['A7_APPROVED_KEY_DIR'] = str(candidate)
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
import a7_reference_inventory as RI
import build_a5_exp5_kit as A5

F, K, SK = R.F, R.K, R.SK
sha = lambda p: R.INV.sha_file(str(p))
inputs = [saved[k] for k in ('by_event', 'decision_by_event',
                            'settlement_by_event', 'closeout_by_event')]
chain = tuple((r, f) for r, f in saved['chain'])
phase = K._load(saved['phase_input_binding'])
carrier = K._load(phase['input_binding'])
out = A7 / 'unit_2020_codex_check' / os.environ['A7_TAG']
out.mkdir()
checks = []


def check(name, condition, detail=None):
    print('PASS' if condition else 'FAIL', name, str(detail)[:400], flush=True)
    assert condition, (name, detail)
    checks.append(name)


@F._operation
def main():
    primary, _ = K.a3_run_dirs()
    before = PR._executed(primary)
    review_path = os.environ.get('A7_VERIFY_PREPARATION')
    review = None
    if review_path:
        check('the cold check names the exact previously frozen preparation',
              sha(review_path) == os.environ['A7_VERIFY_PREPARATION_SHA256'])
        review = K._load(review_path)
    check('real selected lock and receipt are the independently verified bytes',
          sha(candidate / 'a4_final_key_lock.json') == 'dc9192271da3af0c3a0bb2fc2590c151073076f2893ac21136aee30424022e52'
          and sha(candidate / 'a4_final_key_lock_receipt.json') == 'a52323e2ee08be81714109d7f743036c553ebe28f15b529f21dc9ef5e4fad991')
    with R.candidate_scope(saved['review_run'], saved['review_package'],
                           saved['run'], carrier['package']) as C:
        if review:
            evaluation = Path(review['evaluation'])
            frozen = K._load(str(evaluation / A6.REUSE_FREEZE_NAME))
            text = A6.render(frozen)
            check('the cold check preserves the frozen saved-answer evaluation',
                  K._sha(text) == review['evaluation_sha256'])
        else:
            frozen = A6.reuse_freeze(primary, os.path.join(SK.PKG_DIR, SK.MANIFEST_NAME))
            text = A6.render(frozen)
            evaluation = out / 'evaluation'
            evaluation.mkdir()
            R.RT.write_new(str(evaluation / A6.REUSE_FREEZE_NAME), text)
        run = PR.reuse(str(evaluation), K._sha(text))
        check('the evaluation reuses every original call without scheduling another',
              frozen['reused_calls'] == len(frozen['schedule']) == 382
              and frozen['budget']['planned_producer_primary'] == 0)
        with N.input_scope(saved['phase_input_binding']):
            corrected = C2023.bind(SK.bound(saved['run'], carrier['package']), saved['corrections'])
            closed = V.bind(S.bind(D.bind(corrected, saved['decision']),
                                   saved['settlement']), phase['run'])
            bound = X.bind(closed, saved['third_round'])
            with RECOV.recovery_scope(saved['recovery'], corrected, inputs[0]), \
                    X.successor_scope(bound, saved['third_by_event'], chain[-1][0],
                                      chain[-1][1], inputs, chain[:-1]):
                check('the actual grader bound is exactly the signed source-key bound', G._approved_bound() == bound)
                key, identity = G.live_key()
                arms, meta, problems = G.materialize(run)
                check('the actual grading consumer accepts the complete saved population',
                      not problems and (meta['events'], meta['packets'], meta['answers']) == (36, 191, 382)
                      and len(meta['trace']) == 382, problems)
                check('each saved producer arm is present', set(arms) == set(A5.ACTIVE_ARM_IDS), list(arms))
                reference = RI.INVENTORY_PATH
                reference_sha = sha(reference)
                check('the refreshed reference inventory covers the exact signed key',
                      set(RI.validate(run=run)) == {
                          (sid, index) for sid, facts in key.items()
                          for index, fact in enumerate(facts)
                          if fact.get('du_worthy') is True})
                if review:
                    path = review['g1_candidate']
                    actual, prompts, bad = G.freeze(run)
                    locked, _ = G.load_frozen(str(Path(path).parent), review['g1_candidate_sha256'])
                    check('the real G1 candidate re-derives byte-identically in a fresh process',
                          not bad and G._plain(actual) == G._plain(locked), bad)
                    check('all real grader prompts re-derive byte-identically',
                          all((Path(path).parent / row['prompt_path']).read_text()
                              == prompts[row['batch_id']] for row in locked['batch_rows']))
                    check('the cold reference is the exact frozen inventory',
                          reference_sha == review['reference_inventory_sha256'])
                else:
                    path, bad = G.write(str(out / 'g1_candidate'), run)
                check('existing G1 owner freezes the real population without a refusal', not bad, bad)
                doc = K._load(path)
                rows = doc['batch_rows']
                launchers = doc['launchers']['rows']
                expected_legs = set(arms) | {G.LEG_UNION}
                check('both producer arms AND their union are counted', set(doc['legs']) == expected_legs, doc['legs'])
                check('every unmatched gold question has one unique complete binding',
                      doc['questions'] == sum(v['unmatched_gold'] for v in doc['legs'].values())
                      == len(doc['question_bindings'])
                      == len({q['internal_key'] for q in doc['question_bindings']})
                      == sum(r['items'] for r in rows))
                check('every event batch has exactly both independent grader lanes',
                      len(launchers) == len(rows) * len(G.GRADER_LANES)
                      and len({r['lane_id'] for r in launchers}) == len(launchers)
                      and all({l['lane_id'] for l in launchers if l['batch_id'] == r['batch_id']}
                              == {r['batch_id'] + '/' + lane for lane in G.GRADER_LANES} for r in rows))
                check('all frozen grader prompts match their recorded bytes',
                      all(sha(Path(path).parent / r['prompt_path']) == r['prompt_sha256'] for r in rows))
                check('the budget counts completed work once and both readers for each batch',
                      doc['budget']['spent_before'] == 668
                      and doc['budget']['initial_grader_calls'] == len(launchers)
                      and doc['budget']['after_initial'] == 668 + len(launchers)
                      and doc['budget']['max_grader_calls'] == len(launchers) * G.MAX_ATTEMPTS,
                      doc['budget'])
                check('all original answer bytes remain unchanged', PR._executed(primary) == before)
                report = {'kind': 'REAL unrun grading preparation; no model call or A7 score',
                          'model_calls': 0, 'passed': len(checks), 'checks': checks,
                          'key_candidate': str(candidate), 'key_identity': identity,
                          'evaluation': str(evaluation), 'evaluation_sha256': K._sha(text),
                          'run': run, 'g1_candidate': path, 'g1_candidate_sha256': sha(path),
                          'reference_inventory': str(reference), 'reference_inventory_sha256': reference_sha,
                          'population': {'events': meta['events'], 'packets': meta['packets'],
                                         'answers': meta['answers'], 'legs': doc['legs'],
                                         'questions': doc['questions'], 'batches': len(rows),
                                         'reviewer_calls': len(launchers)},
                          'budget': doc['budget'], 'controls': doc['controls'],
                          'trace_statuses': dict(collections.Counter(t['status'] for t in meta['trace']))}
                R.RT.write_new(str(out / 'PREPARATION.json'), json.dumps(report, indent=1, default=str))
                print(json.dumps({k: report[k] for k in ('passed', 'model_calls', 'population', 'budget', 'trace_statuses')}, indent=1), flush=True)


main()
