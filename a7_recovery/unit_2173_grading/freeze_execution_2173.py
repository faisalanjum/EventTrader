# -*- coding: utf-8 -*-
"""Freeze and preflight the execution layout for the approved 24 lanes.

The 2088/2103 publisher arrangement, reused unchanged: the runtime path the
Workflow will execute and the durable recovery path are ONE directory through
the established map, so the receipt, the invocation and the executed script all
name the same bytes and nothing is copied between binding and call.

Nothing is rendered, batched, graded or called here. Both candidates and their
prompts are read-only inputs and are not modified.
"""
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
A7 = Path(__file__).resolve().parents[1]
UNIT = A7 / 'unit_2173_grading'
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R                                    # noqa: E402,F401
import a7_g1_build as G                                            # noqa: E402
import a7_g23_build as B                                           # noqa: E402
import a7_g1_workflow_gate as W                                    # noqa: E402

EXECUTION = Path(os.environ['A7_EXECUTION_ROOT'])
PROFILE_ROOT = os.environ['A7_PROFILE_ROOT']
assert G._sha_file(PROFILE_ROOT) == os.environ['A7_PROFILE_ROOT_SHA256']
proven = G._read(PROFILE_ROOT)
#: the ONE reviewed grading-lane input every proven grading row was frozen
#: under; it is read from that proven root, never composed here.
shapes = {G._plain(r.get('expected_input')) for r in proven['rows']}
assert len(shapes) == 1, shapes
PROFILE = proven['rows'][0]['expected_input']
SEGMENT = 1
CANDIDATES = {
    'G2': (os.environ['A7_G2_CANDIDATE'], os.environ['A7_G2_CANDIDATE_SHA256']),
    'G3': (os.environ['A7_G3_CANDIDATE'], os.environ['A7_G3_CANDIDATE_SHA256']),
}

report, scheduled = {}, {}
for kind in sorted(CANDIDATES):
    cand_file, expect = CANDIDATES[kind]
    candidate = str(Path(cand_file).parent)
    run = str(EXECUTION / kind / 'run')
    durable = UNIT / kind / 'run'
    # THE RUNTIME PATH AND THE DURABLE PATH ARE ONE DIRECTORY, not a copy.
    assert os.path.samefile(run, str(durable)), (run, str(durable))

    doc, digest = G.load_frozen(candidate, expect)
    assert digest == expect and G.task_kind(doc) == kind
    assert doc['made_calls'] == 0
    B.bind_grading_scorer(
        str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
        proven['owners']['grading_scorer'])

    rows = doc['launchers']['rows']
    inputs = {r['lane_id']: PROFILE for r in rows}
    root, root_sha, bad = G.freeze_root(candidate, run, digest, inputs)
    assert not bad, bad
    assert G._plain(root['lane']) == G._plain(proven['lane'])
    assert root['owners'] == G.owner_hashes()
    assert root['max_attempts'] == proven['max_attempts']
    assert all(G._plain(r['expected_input']) == G._plain(PROFILE)
               for r in root['rows'])

    lanes, size, bad = W.next_admissible(candidate, run, root_sha)
    assert not bad and lanes, bad
    pub, bad = G.publish_run(candidate, run, root_sha, lanes)
    assert not bad and pub['segment'] == SEGMENT, bad
    packet, bad = G.preflight(candidate, run, SEGMENT, root_sha,
                              pub['receipt_sha256'])
    assert not bad, bad

    script_path = packet['scriptPath']
    assert script_path == G.script_path(run, SEGMENT)
    assert os.path.samefile(script_path, str(durable / Path(script_path).name))
    script = Path(script_path).read_bytes()
    assert len(script) == size <= W.SCRIPT_BYTE_LIMIT, (len(script), size)
    invocation_path = G.invocation_path(run, SEGMENT)
    invocation = G._read(invocation_path)
    assert [r['lane_id'] for r in invocation['args']] == lanes
    assert invocation['scriptPath'] == script_path
    assert G.lane_states(run) == {}
    assert G._read(G.state_path(run, SEGMENT))['states'] == []

    scheduled[kind] = [r['lane_id'] for r in root['rows']]
    report[kind] = {
        'candidate_dir': candidate, 'candidate_sha256': digest,
        'runtime_run_dir': run, 'durable_run_dir': str(durable),
        'runtime_and_durable_are_one_directory': True,
        'root_sha256': root_sha, 'root_path': G.root_path(run),
        'rows': len(root['rows']), 'batches': len(rows) // len(G.GRADER_LANES),
        'questions': doc['questions'],
        'lane': root['lane'], 'owners': root['owners'],
        'max_attempts': root['max_attempts'],
        'max_output_tokens': root['max_output_tokens'],
        'expected_input': PROFILE,
        'expected_input_source': PROFILE_ROOT,
        'first_segment': SEGMENT,
        'first_segment_lanes': lanes,
        'receipt_path': G.receipt_path(run, SEGMENT),
        'receipt_sha256': pub['receipt_sha256'],
        'script_path': script_path,
        'script_sha256': G._sha_file(script_path),
        'script_bytes': len(script),
        'script_byte_limit': W.SCRIPT_BYTE_LIMIT,
        'invocation_path': invocation_path,
        'invocation_sha256': G._sha_file(invocation_path),
        'args_sha256': G._sha(G._plain(packet['args'])),
        'args_rows': len(packet['args']),
        'primary_lanes': len(root['rows']),
        'invalid_only_retry_lanes': len(root['rows']) * (root['max_attempts'] - 1),
        'lane_states': G.lane_states(run),
        'made_calls': doc['made_calls'],
    }
    G._write_new(str(durable.parent / 'LAUNCH_2173.json'),
                 G._pretty(report[kind]) + '\n')
    G._write_new(str(durable.parent / ('args_seg%02d.json' % SEGMENT)),
                 G._plain(packet['args']))
    # The operator reads ONE per-kind view of these same frozen facts. Nothing
    # here is new truth: every field is copied from the root, the candidate or
    # the publication that has just been checked above.
    G._write_new(str(durable.parent / 'LAUNCH_OPERATOR_2173.json'), G._pretty({
        'scope': 'operator-compatible view of the frozen 2173 run; adds no new truth',
        'kind': kind,
        'run_dir': run,
        'durable_run_dir': str(durable),
        'candidate_dir': candidate,
        'candidate_sha256': digest,
        'root_sha256': root_sha,
        'owners': root['owners'],
        'workflow_gate_sha256': W.owner_sha256(),
        'max_output_tokens': root['max_output_tokens'],
        'first_segment': SEGMENT,
        'first_receipt_sha256': pub['receipt_sha256'],
        'first_script_sha256': G._sha_file(script_path),
        'source_report': str(UNIT / 'EXECUTION_LAYOUT_2173.json'),
    }) + '\n')

# ---- THE WHOLE SCHEDULED INVENTORY, across both kinds -----------------------
every = [(k, lane) for k in sorted(scheduled) for lane in scheduled[k]]
assert len(every) == len(set(every))
assert not set(scheduled['G2']) & set(scheduled['G3'])
primary = sum(report[k]['primary_lanes'] for k in report)
whole = {
    'scope': 'frozen + preflighted execution layout for the verified lanes; '
             'NO model call, NOT an authorization to call',
    'model_calls': 0,
    'map': os.environ['A7_RUN_BINDING'],
    'map_sha256': G._sha_file(os.environ['A7_RUN_BINDING']),
    'execution_root': str(EXECUTION),
    'primary_lanes_total': primary,
    'invalid_only_retry_total': sum(report[k]['invalid_only_retry_lanes']
                                    for k in report),
    'lanes_are_disjoint': True,
    'kinds': report,
}
G._write_new(str(UNIT / 'EXECUTION_LAYOUT_2173.json'), G._pretty(whole) + '\n')
print('FROZEN:', json.dumps({
    'primary_lanes_total': primary,
    'per_kind': {k: {'rows': report[k]['rows'],
                     'first_segment_lanes': len(report[k]['first_segment_lanes']),
                     'script_bytes': report[k]['script_bytes']} for k in report},
}), flush=True)
