"""Score saved A7 answers with the verified key and exact grading corrections.

No new scoring rules or AI calls. Existing context, evidence, revision and
counter owners perform their own checks. The report records the actual final
inputs as well as scores, so cause analysis does not need another native run.
"""
import copy
import os
from pathlib import Path

# The existing native context sets the harness dependencies before importing
# the reuse owner. Imported tests supply those dependencies through fixtures.
if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2143_source_authority'))
    from build_candidate_2148 import E

import a7_g2_key_reuse_2159 as REUSE
import a7_grading_revision_2115 as REV
import a7_grading_input_correction_2114 as V
import a7_grading_script_binding_2156 as TRANSPORT
import a7_duplicate_accounting_2116 as DUP

G, B, C, R = REUSE.G, REUSE.B, REUSE.C, REUSE.R


def validate_revision(reuse_ref, revision_ref):
    """Require exactly the reviewed changed tasks; native owners judge evidence."""
    REUSE._pin(reuse_ref)
    REUSE._pin(revision_ref)
    reuse = G._read(reuse_ref['path'])
    selection = REUSE.derive(reuse['selection']['path'], reuse['selection']['sha256'])
    REUSE._pin(reuse['current_preparation'])
    current = G._read(reuse['current_preparation']['path'])
    g3 = current['candidates']['G3']
    REUSE._pin(g3)
    candidate, _ = G.load_frozen(str(Path(g3['path']).parent), g3['sha256'])
    wanted = {'G2': selection['correction_population'], 'G3': candidate['population']}
    wanted = {kind: pop for kind, pop in wanted.items() if pop}
    revision = G._read(revision_ref['path'])
    if set(revision['corrections']) != set(wanted):
        raise ValueError('final scoring does not include every required correction kind')
    for kind, population in wanted.items():
        correction = revision['corrections'][kind]
        if G._plain(correction['population']) != G._plain(population):
            raise ValueError('final scoring changed the approved correction population')
        if correction['input_correction_sha256'] != G._sha_file(V.__file__):
            raise ValueError('final scoring changed the approved grading input version')
    return revision


def _indexed(mapping):
    """Represent existing tuple keys explicitly, without changing their values."""
    return [{'key': list(k), 'value': copy.deepcopy(v)}
            for k, v in sorted((mapping or {}).items())]


def run(E, reuse_ref, revision_ref, approved_ref, duplicate_pin):
    revision = validate_revision(reuse_ref, revision_ref)
    REUSE._pin(approved_ref)
    approved = G._read(approved_ref['path'])
    format_pins = G._read(reuse_ref['path'])['format']

    def score(producer, _inputs, g1):
        import build_a5_exp5_kit as A5
        legs = list(A5.ACTIVE_ARM_IDS) + [G.LEG_UNION]
        sources = {leg: revision['base_sources'] for leg in legs}
        routes, loads, cases = [], [], {}
        route, load, bound = B.route_for, C.load_g23, B._score_leg_bound
        key, key_identity = G.live_key()

        def record_route(*args, **kwargs):
            routes.extend((Path(args[1]).name, sid) for sid in args[0])
            return route(*args, **kwargs)

        def record_load(*args, **kwargs):
            loads.append(args[0])
            return load(*args, **kwargs)

        def record_bound(bundle, leg, *args):
            if leg in cases:
                raise ValueError('a final scoring leg ran twice')
            row = {'answers': copy.deepcopy(bundle['arms'][leg]),
                   'event_meta': copy.deepcopy(bundle['derived']['event_meta']),
                   'resolutions': _indexed(bundle['derived']['resolutions'].get(leg)),
                   'route': {
                       sid: dict(copy.deepcopy({k: v for k, v in data.items()
                                                if k != 'index_map'}),
                                 index_map=_indexed(data['index_map']))
                       for sid, data in bundle['derived']['routes'][leg].items()}}
            cases[leg] = row
            verdicts = B._verdict_maps_from

            def record_verdicts(*vargs, **kwargs):
                meanings, extras = verdicts(*vargs, **kwargs)
                if 'meanings' in row:
                    raise ValueError('a final leg read its combined judgments twice')
                row['meanings'], row['extras'] = _indexed(meanings), _indexed(extras)
                return meanings, extras

            with R._using(B, _verdict_maps_from=record_verdicts):
                result = bound(bundle, leg, *args)
            return result

        with REUSE.FORMAT.scope(format_pins['code_sha256'], format_pins['rule_sha256']), \
                REV.scope(revision_ref['path'], revision_ref['sha256']), \
                DUP.scope(B._scorer(), duplicate_pin, E.launch['owners']['grading_scorer']), \
                R._using(B, route_for=record_route, _score_leg_bound=record_bound), \
                R._using(C, load_g23=record_load):
            decisions, results = B.official_tier_decision(
                producer, sources, str(E.out / 'route'), g1)
        expected_routes = {(leg, sid) for leg in legs for sid in key}
        assert set(routes) == expected_routes and len(routes) == len(expected_routes)
        assert set(cases) == set(legs) == set(results)
        assert all('meanings' in row and 'extras' in row for row in cases.values())
        assert len(loads) == len(set(loads)) == len(revision['corrections'])
        assert all(result['gold_n'] == key_identity['accepted_rows']
                   for result in results.values())
        return dict(scope='Corrected A7 measurement over unchanged saved answers; '
                          'a completed measurement is not necessarily PASS',
                    caller_sha256=G._sha_file(__file__),
                    reuse=reuse_ref, revision=revision_ref, current_input=approved_ref,
                    duplicate_accounting_sha256=duplicate_pin,
                    producer=producer, g1=g1, key_identity=key_identity,
                    key=key, decisions=decisions, results=results, cases=cases,
                    route_count=len(routes), correction_completion_load_count=len(loads),
                    new_model_calls=0)

    with TRANSPORT.scope(approved['script_binding'], approved['g1']['pins']):
        report = REUSE.evaluate(E, reuse_ref['path'], reuse_ref['sha256'], score)
    for ref in (reuse_ref, revision_ref, approved_ref):
        REUSE._pin(ref)
    G._write_new(str(E.out / 'A7_CORRECTED_SCORE.json'), G._pretty(report) + '\n')
    print('SAVED CORRECTED A7 MEASUREMENT', G._plain(report['decisions']), flush=True)
    return report


if __name__ == '__main__':
    def ref(name):
        return {'path': os.environ[name], 'sha256': os.environ[name + '_SHA256']}

    run(E, ref('A7_G2_KEY_REUSE_PLAN'), ref('A7_GRADING_REVISION'),
        ref('A7_CURRENT_G23_INPUT'), os.environ['A7_DUPLICATE_ACCOUNTING_SHA256'])
