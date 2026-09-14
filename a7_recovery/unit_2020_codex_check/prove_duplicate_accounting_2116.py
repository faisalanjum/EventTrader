"""Real full-consumer counter correction proof; no new answers or judgments."""
import os
from pathlib import Path

import prepare_g23_partial_2097 as E
import a7_meaning_format_2105 as F
import a7_duplicate_accounting_2116 as D

G, B = E.G, E.B
HERE = Path(__file__).resolve().parent
BASE = HERE / 'codex_actualscore2111_a/A7_BASELINE.json'
BASE_SHA = '98a7a6ad3a346e5417dcc2120568c5ab1461ba41a160a0f800256102a2a5e19d'


def prove(producer, _inputs):
    assert G._sha_file(str(BASE)) == BASE_SHA
    baseline = G._read(str(BASE))
    assert producer == baseline['producer'] and E.g1 == baseline['g1']
    before = G.owner_hashes()
    code_sha = G._sha_file(D.__file__)
    sources = {leg: baseline['sources'] for leg in baseline['results']}
    routed = []
    original_route = B.route_for

    def route(*args, **kwargs):
        routed.extend((Path(args[1]).name, sid) for sid in args[0])
        return original_route(*args, **kwargs)

    with F.scope(os.environ['A7_FORMAT_CODE_SHA256'], os.environ['A7_FORMAT_RULE_SHA256']), \
            D.scope(B.GRADING_SCORER, code_sha, before['grading_scorer']), \
            E.R._using(B, route_for=route):
        decisions, results = B.official_tier_decision(
            producer, sources, str(E.out / 'route'), E.g1)
    assert G.owner_hashes() == before
    assert G._sha_file(D.__file__) == code_sha
    assert decisions == baseline['decisions']
    expected_routes = {(leg, sid) for leg in sources for sid in G.live_key()[0]}
    assert len(routed) == len(expected_routes) and set(routed) == expected_routes
    trace_path = HERE / 'codex_scoretrace2112_a/SCORER_TRACE.json'
    assert G._sha_file(str(trace_path)) == '0b4a3f624a4024fb071fff1740f04b186027b2c91bcade2aaba4ce6bb05f7ee4'
    trace = G._read(str(trace_path))
    changes = {}
    for leg, result in results.items():
        old = baseline['results'][leg]
        allowed = {'duplicate_violations', 'open_identity_findings'}
        changed = {k: {'before': old[k], 'after': result[k]}
                   for k in old if old[k] != result[k]}
        assert set(result) == set(old) and set(changed) <= allowed, (leg, changed)
        exact_rows = [r for r in result['ambiguous_rows']
                      if r.get('reason') == 'duplicate_produced']
        assert not exact_rows and result['duplicate_violations'] == 0
        groups = trace['records'][leg]['inputs']['safety_findings']['confirmed_duplicate_groups']
        assert result['open_identity_findings'] == old['open_identity_findings'] + len(groups)
        changes[leg] = changed
    assert G._sha_file(str(BASE)) == BASE_SHA
    report = {
        'scope': 'REAL counter-only corrected replay; semantic grading corrections remain open',
        'baseline_sha256': BASE_SHA, 'caller_sha256': G._sha_file(__file__),
        'correction_sha256': code_sha, 'owners': before,
        'producer': producer, 'key_identity': baseline['key_identity'],
        'g1': E.g1, 'sources': baseline['sources'], 'route_count': len(routed),
        'new_model_calls': 0, 'decisions': decisions, 'changes': changes,
        'results': results, 'other_results_unchanged': True,
    }
    G._write_new(str(E.out / 'COUNTER_CORRECTION_PROOF.json'), G._pretty(report) + '\n')
    print('VERIFIED real counter correction', G._plain(changes), flush=True)


E.with_prepared_inputs(prove)
