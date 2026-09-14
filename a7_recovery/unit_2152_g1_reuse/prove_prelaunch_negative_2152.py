# -*- coding: utf-8 -*-
"""The prelaunch negative, on its OWN fresh root. Codex SEQ 2152.

A frozen, unpublished root is an ACCOUNTED population, not a score. This proves
that with the existing owners and nothing else: the evidence owner reads the
whole root and reports every lane as uncalled WITHOUT a problem of its own, the
refusal owner returns that state together with one missing-valid diagnostic per
lane, and BOTH the approved lifecycle and the existing partial policy refuse it.

The partial policy refusal is the important half: it admits a missing lane only
when that lane's bounded attempts are all evidenced invalid, so a lane that was
never called cannot be waived into a score by it. No model is called and no
segment is published here.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
UNIT = A7 / 'unit_2152_g1_reuse'
REPORT = A7 / 'unit_2020_codex_check/codex_keygrading2150_a/KEY_GRADING_INPUTS.json'
REPORT_SHA = 'd7571670fc3ae38a4dc732a7e377f23c385a0ee59aad3eb38d52151cd590e9f7'
SCORER_SHA = '6d0a02285162a079a81615db6ae64fddaa43acef64214315339c8d78bfd7f43e'
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R                                    # noqa: E402
import a7_g1_build as G                                            # noqa: E402
import a7_g23_build as B                                           # noqa: E402
import a7_g1_complete_v2 as C                                      # noqa: E402
sys.path.insert(0, str(A7 / 'unit_2020_codex_check'))
import a7_partial_grading_2095 as P                                # noqa: E402
sys.path.insert(0, str(UNIT))
import g1_reuse_inputs_2152 as INPUTS                              # noqa: E402

selection = INPUTS.derive(str(REPORT), REPORT_SHA)
cand = selection['candidate_dir']
doc, candidate_sha = G.load_frozen(cand, selection['report']['g1_candidate_sha256'])
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      SCORER_SHA)
run_dir = str(UNIT / 'g1_negative')
lanes = [r['lane_id'] for r in doc['launchers']['rows']]
root, root_sha, bad = G.freeze_root(cand, run_dir, candidate_sha,
                                    {lane: selection['expected_input'] for lane in lanes})
assert not bad, bad

digest, files = C.run_digest(run_dir)
ev_root, ev_doc, ev_lanes, ev_problems = C.evidence(cand, run_dir, root_sha,
                                                    digest, files)
uncalled = sorted(lane for lane, rec in (ev_lanes or {}).items()
                  if (rec or {}).get('selected') is None)
attempts = sorted({json.dumps((rec or {}).get('attempts'))
                   for rec in (ev_lanes or {}).values()})
pins = dict(selection['report']['original_g1']['pins'],
            root_sha256=root_sha, candidate_sha256=candidate_sha,
            run_tree_sha256=digest, run_file_count=files,
            prompt_tree_sha256=root['prompt_tree_sha256'],
            rules_block_sha256=root['rules_block_sha256'])
state, refuse_problems = B.refuse(cand, run_dir, pins)
g1 = {'candidate_dir': cand, 'run_dir': run_dir, 'pins': pins}


def refusal(call):
    try:
        call()
    except Exception as exc:                       # noqa: BLE001 - by design
        return '%s: %s' % (type(exc).__name__, exc)
    raise AssertionError('an unrun root must not be accepted')


record = {
    'kind': 'Prelaunch negative on a fresh unpublished root; no AI call, no score',
    'model_calls': 0, 'run_dir': run_dir, 'root_sha256': root_sha,
    'candidate_sha256': candidate_sha,
    'root_lanes': len(root['rows']),
    'evidence_problems': ev_problems,
    'evidence_uncalled_lanes': len(uncalled),
    'evidence_attempts_shapes': attempts,
    'refuse_returned_state': state is not None,
    'refuse_problem_count': len(refuse_problems or []),
    'refuse_problems_are_all_missing_valid': all(
        p.endswith('has no selected valid attempt') for p in (refuse_problems or [])),
    'lifecycle_refusal': refusal(lambda: B._lifecycle(g1)),
    'partial_policy_refusal': refusal(lambda: P.lifecycle(g1)),
    'partial_policy_sha256': G._sha_file(P.__file__),
    'segments_published': len(G.segments(run_dir)),
    'lane_states': G.lane_states(run_dir),
}
assert record['segments_published'] == 0 and record['lane_states'] == {}
assert record['evidence_uncalled_lanes'] == len(root['rows'])
assert record['refuse_problems_are_all_missing_valid']
G._write_new(str(UNIT / 'PRELAUNCH_NEGATIVE_2152.json'), G._pretty(record) + '\n')
print(G._pretty(record), flush=True)
