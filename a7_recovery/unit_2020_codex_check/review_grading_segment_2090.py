"""Read-only replay of collected G1 evidence through the existing owners.

The caller supplies the independently measured whole-run pin. This neither
launches a model nor changes the candidate, run, replies or finalization.
"""
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g1_complete_v2 as C
import a7_g23_build as B
import a7_g1_workflow_gate as W

launch_path = os.environ['A7_GRADING_LAUNCH']
assert G._sha_file(launch_path) == os.environ['A7_GRADING_LAUNCH_SHA256']
launch = G._read(launch_path)
run, candidate = launch['run_dir'], launch['candidate_dir']
expected = (os.environ['A7_REVIEW_RUN_SHA256'], int(os.environ['A7_REVIEW_RUN_FILES']))
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                     launch['owners']['grading_scorer'])
assert G.owner_hashes() == launch['owners']
assert W.owner_sha256() == launch['workflow_gate_sha256']
assert C.run_digest(run) == expected

audits, expected_collected = [], set()
for n in G.segments(run):
    assert G.segment_state(run, n) == 'finalized', n
    receipt_sha = G._sha_file(G.receipt_path(run, n))
    problems, whole = G.audit_official_state(run, n, launch['root_sha256'], receipt_sha)
    print('NATIVE_AUDIT', n, 'whole', len(whole), 'problems', problems, flush=True)
    assert not problems, (n, problems)
    receipt = G.load_receipt(run, n)
    expected_collected.update(r['lane_id'] for r in receipt['rows'])
    audits.append({'segment': n, 'receipt_sha256': receipt_sha,
                   'whole_answers': len(whole), 'problems': problems})

root, doc, lanes, problems = C.evidence(candidate, run, launch['root_sha256'], *expected)
print('EVIDENCE_PROBLEMS', problems, flush=True)
assert not problems, problems
selected = C.relations_from_run(lanes)
assert set(selected) <= expected_collected
grouped, problems = C.lane_relations(doc, selected)
assert not problems, problems
pairs = []
for leg, events in sorted(grouped.items()):
    for source_id, (first, second) in sorted(events.items()):
        if first is None or second is None:
            pairs.append({'leg': leg, 'source_id': source_id, 'missing_reader': True})
        else:
            _accepted, detail = G.event_credit(first, second)
            pairs.append({'leg': leg, 'source_id': source_id, 'detail': detail})
remaining = sorted(set(lanes) - set(selected))
result = {'scope': 'G1 collection/native/schema replay and paired identity evidence; not an A7 score',
          'launch_sha256': G._sha_file(launch_path), 'root_sha256': launch['root_sha256'],
          'run_sha256': expected[0], 'run_files': expected[1],
          'required_primary': len(root['rows']), 'collected_unique': len(expected_collected),
          'selected_valid': len(selected), 'collected_without_valid_answer': sorted(expected_collected - set(selected)),
          'remaining': remaining, 'native_audits': audits, 'lanes': lanes, 'pairs': pairs}
assert C.run_digest(run) == expected, 'review changed or raced with the frozen run'
out = A7 / 'unit_2020_codex_check' / os.environ['A7_TAG']
out.mkdir()
(out / 'REVIEW.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print('REVIEW_SAVED', str(out / 'REVIEW.json'), 'valid', len(selected),
      'required', len(root['rows']), 'remaining', len(remaining), flush=True)
