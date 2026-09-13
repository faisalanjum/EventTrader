"""Real saved key/producer/G1 -> native TEST G2/G3 -> the actual tier scorer.

G2/G3 replies are explicit deterministic TEST fixtures, never model evidence
or an A7 score. Only fixture locations and declared input are bound; every
original validator, parser, completion and scoring owner still runs.
"""
import copy
import json
import os
from functools import partial
from pathlib import Path

import prepare_g23_partial_2097 as E
import a7_g1_complete_v2 as CV
import audit_worker_access as AUD
import g1_fake_state as FAKE
import raw_transport as RT

G, B, GR, R = E.G, E.B, E.GR, E.R
strict_lifecycle = B._lifecycle
native_evidence = CV.evidence
freeze_root = G.freeze_root
reuse = None
if os.environ.get('A7_TEST_REUSE_SOURCES'):
    reuse_path = os.environ['A7_TEST_REUSE_SOURCES']
    assert G._sha_file(reuse_path) == os.environ['A7_TEST_REUSE_SOURCES_SHA256']
    reuse = G._read(reuse_path)
test_root = Path(reuse['test_root']) if reuse else E.out / 'TEST_only'
projects = str(test_root / 'projects')


def fixture_root(candidate, run, digest, lane_inputs=None):
    assert Path(run).resolve().is_relative_to(test_root.resolve())
    assert lane_inputs is None
    doc, _ = G.load_frozen(candidate, digest)
    spec, _ = RT.declared_lane_input()
    inputs = {row['lane_id']: copy.deepcopy(spec) for row in doc['launchers']['rows']}
    return freeze_root(candidate, run, digest, lane_inputs=inputs)


def fixture_evidence(candidate, run, *pins):
    # Select the store for these two TEST runs, never replace their evidence
    # or result. The real G1 path uses its unchanged official project store.
    if Path(run).resolve().is_relative_to(test_root.resolve()):
        with R._using(AUD, PROJECTS_ROOT=projects):
            return native_evidence(candidate, run, *pins)
    return native_evidence(candidate, run, *pins)


def run(producer, _inputs):
    path = os.environ['A7_VERIFY_G23_PREPARATION']
    assert G._sha_file(path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
    prep = G._read(path)
    assert prep['producer'] == producer and prep['g1'] == E.g1
    doc = G._read(str(Path(path).parent / GR.CANDIDATE_NAME))
    assert doc['producer_identity'] == producer
    assert doc['g1_identity'] == B.g1_identity(E.g1)
    before = CV.run_digest(E.g1['run_dir'])
    # The old fixture's default has no attachment. Supply the already verified
    # real declaration through its existing explicit parameter; do not change
    # the input checker or silently omit what the new root declares.
    input_path = os.environ['A7_TEST_INPUT_TRANSCRIPT']
    assert G._sha_file(input_path) == os.environ['A7_TEST_INPUT_TRANSCRIPT_SHA256']
    records = [json.loads(line) for line in Path(input_path).read_text().splitlines()]
    spec, _ = RT.declared_lane_input()
    record = records[spec['record_index']]
    assert AUD._expected_input(record, spec['record_index'], spec)
    declared = dict(spec, payload=record[spec['payload_field']])
    sources = reuse['sources'] if reuse else {}
    with R._using(CV, evidence=fixture_evidence):
        for kind, identity in (() if reuse else prep['candidates'].items()):
            original = Path(identity['path']).parent
            candidate, _ = G.load_frozen(str(original), identity['sha256'])
            prompts = {r['batch_id']: (original / r['prompt_path']).read_text()
                       for r in candidate['batch_rows']}
            target = test_root / ('candidate_' + kind)
            test_path, digest = GR.write_kind(str(target), kind, doc, prompts, prep['key_identity'])
            assert digest == identity['sha256']
            with R._using(G, freeze_root=fixture_root), R._using(AUD, PROJECTS_ROOT=projects), \
                    R._using(FAKE, _transcript=partial(FAKE._transcript, declared=declared)):
                sources[kind] = FAKE.complete_test_run(kind, target, test_path,
                                                      test_root / ('run_' + kind), projects)
        by_leg = {leg: sources for leg in prep['findings']}
        _arms, trace_meta, bad = G.materialize(producer)
        assert not bad
        scheduled_sources = {row['source_id'] for row in trace_meta['trace']}
        assert scheduled_sources == set(G.live_key()[0])
        expected_routes = {(leg, sid) for leg in by_leg for sid in scheduled_sources}
        routed = []
        counters = {'g1_validation': 0, 'route_calls': 0, 'completion_loads': 0}
        lifecycle, route, completion = B._lifecycle, B.route_for, CV.load_g23
        def check_g1(*args, **kwargs):
            counters['g1_validation'] += 1
            return lifecycle(*args, **kwargs)
        def route_event(*args, **kwargs):
            counters['route_calls'] += 1
            routed.extend((Path(args[1]).name, sid) for sid in args[0])
            return route(*args, **kwargs)
        def load_completion(*args, **kwargs):
            counters['completion_loads'] += 1
            return completion(*args, **kwargs)
        with R._using(B, _lifecycle=check_g1, route_for=route_event), R._using(CV, load_g23=load_completion):
            decisions, results = B.official_tier_decision(producer, by_leg, str(E.out / 'route'), E.g1)
        G._write_new(str(E.out / 'SCORED_BEFORE_ASSERTIONS.json'), G._pretty({
            'scope': 'TEST-only, assertions not yet passed', 'sources': sources,
            'counters': counters, 'decisions': decisions, 'results': results}) + '\n')
        assert set(routed) == expected_routes and len(routed) == len(expected_routes)
        assert counters == {'g1_validation': 1, 'route_calls': len(expected_routes), 'completion_loads': 2}, counters
        assert all(row['gold_n'] == prep['full_key_fact_count'] == 163 for row in results.values())
        gaps = prep['findings']['P2']['incomplete']
        assert len(gaps) == 1 and gaps[0]['of'] == 5 and gaps[0]['ruled'] == 0
        assert results['P2']['matched'] <= prep['full_key_fact_count'] - gaps[0]['of']
        assert results['P2']['required_grading_unfinished']
        assert results['P2']['open_identity_findings'] >= 1
        assert results['P2']['duplicate_violations'] >= len(prep['findings']['P2']['confirmed_duplicate_groups'])
        assert set(decisions.values()) == {False}, decisions
        # A real negative control: removing ONLY the approved policy restores
        # the old public refusal, with the same native evidence and consumer.
        try:
            with R._using(B, _lifecycle=strict_lifecycle):
                B.official_tier_decision(producer, by_leg, str(E.out / 'strict_route'), E.g1)
        except ValueError as exc:
            assert 'has no selected valid attempt' in str(exc), str(exc)
            strict_refusal = str(exc)
        else:
            raise AssertionError('the original strict entry accepted an incomplete G1 run')
    assert CV.run_digest(E.g1['run_dir']) == before
    report = {'scope': 'TEST G2/G3 verdicts; real saved key, producer and G1; NOT an A7 score',
              'actual_model_calls': 0, 'sources': sources, 'counters': counters,
              'strict_control': strict_refusal, 'decisions': decisions, 'results': results,
              'real_g1_unchanged': True, 'full_gold_per_leg': prep['full_key_fact_count'], 'uncredited_gap': gaps}
    report['route_inventory'] = {'scheduled_sources': sorted(scheduled_sources),
                                 'unique_event_legs': len(expected_routes), 'calls': sorted(routed)}
    G._write_new(str(E.out / 'SCORING_CONNECTION.json'), G._pretty(report) + '\n')
    print(G._plain(report), flush=True)


E.with_prepared_inputs(run)
