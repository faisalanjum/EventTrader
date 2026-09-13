"""Save the reviewed G2 completion and score real A7 through existing owners.

No AI calls, invented judgments, new scoring rules or production writes.
An already saved, byte-identical completion is reusable after interruption;
each scoring attempt still has its own create-only output directory.
"""
import os
from pathlib import Path

import prepare_g23_partial_2097 as E
import a7_g1_complete_v2 as C
import a7_meaning_format_2105 as F

G, B = E.G, E.B


def checked(path, digest):
    assert G._sha_file(str(path)) == digest, str(path)
    return G._read(str(path))


def score(producer, _inputs):
    review_path = Path(os.environ['A7_G2_REVIEW_REPORT'])
    review = checked(review_path, os.environ['A7_G2_REVIEW_REPORT_SHA256'])
    inputs = checked(review['input_path'], review['input_sha256'])
    launch = checked(inputs['launch_path'], inputs['launch_sha256'])
    approved = checked(review_path.with_name('COMPLETION_CANDIDATE.json'),
                       review['completion_candidate_sha256'])
    g3 = checked(os.environ['A7_G3_PERSISTED_REPORT'],
                 os.environ['A7_G3_PERSISTED_REPORT_SHA256'])
    prep = checked(os.environ['A7_VERIFY_G23_PREPARATION'],
                   os.environ['A7_VERIFY_G23_PREPARATION_SHA256'])
    for row in inputs['files']:
        assert G._sha_file(row['path']) == row['sha256'], row['path']
    g1_before = C.run_digest(E.g1['run_dir'])
    with F.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']):
        assert C.g23_identity(launch['root_sha256'], launch['run_dir']) == review['run_identity']
        completion_path = Path(launch['candidate_dir']) / C.G23_NAME
        completion_sha = review['completion_candidate_sha256']
        if completion_path.exists():
            assert C.load_g23(launch['candidate_dir'], completion_sha,
                              launch['root_sha256'], launch['run_dir']) == approved
        else:
            _path, saved_sha = C.persist_g23(launch['candidate_dir'], approved)
            assert saved_sha == completion_sha
        sources = {'G2': {'run_dir': launch['run_dir'], 'root_sha256': launch['root_sha256'],
                          'completion_sha256': completion_sha},
                   'G3': {'run_dir': g3['run_identity']['run_dir'],
                          'root_sha256': g3['run_identity']['root_sha256'],
                          'completion_sha256': g3['completion_sha256']}}
        by_leg = {leg: sources for leg in prep['findings']}
        routed, loaded = [], []
        route, load = B.route_for, C.load_g23

        def record_routes(*args, **kwargs):
            routed.extend((Path(args[1]).name, sid) for sid in args[0])
            return route(*args, **kwargs)

        def record_load(*args, **kwargs):
            loaded.append(args[0])
            return load(*args, **kwargs)

        with E.R._using(B, route_for=record_routes), E.R._using(C, load_g23=record_load):
            decisions, results = B.official_tier_decision(producer, by_leg, str(E.out / 'route'), E.g1)
        expected_routes = {(leg, sid) for leg in by_leg for sid in G.live_key()[0]}
        assert len(routed) == len(expected_routes) and set(routed) == expected_routes
        assert len(loaded) == len(sources) and len(set(loaded)) == len(sources)
        assert all(r['gold_n'] == prep['full_key_fact_count'] for r in results.values())
        for kind, prior in (('G2', review), ('G3', g3)):
            identity = prior['run_identity']
            assert C.run_digest(sources[kind]['run_dir']) == (identity['run_digest'], identity['run_files'])
        assert C.run_digest(E.g1['run_dir']) == g1_before
    for row in inputs['files']:
        assert G._sha_file(row['path']) == row['sha256'], row['path']
    report = {'scope': 'REAL A7 baseline over unchanged saved producer replies; not a corrected result',
              'caller_sha256': G._sha_file(__file__), 'producer': producer,
              'key_identity': prep['key_identity'], 'g1': E.g1, 'sources': sources,
              'g2_review_sha256': os.environ['A7_G2_REVIEW_REPORT_SHA256'],
              'g3_review_sha256': os.environ['A7_G3_PERSISTED_REPORT_SHA256'],
              'route_count': len(routed), 'completion_load_count': len(loaded),
              'decisions': decisions, 'results': results,
              'original_records_unchanged': True, 'new_model_calls': 0}
    G._write_new(str(E.out / 'A7_BASELINE.json'), G._pretty(report) + '\n')
    print('SAVED REAL A7 BASELINE', G._plain(decisions), flush=True)
    return report


E.with_prepared_inputs(score)
