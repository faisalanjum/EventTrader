"""Operate the frozen real G1 run through the existing, reviewed operator.

No workflow/model is launched here. Core supplies a separately authorized
Workflow call and its actual run id. The old operator remains the sole owner
of preparation, native ingestion, retry handling and status sequencing.
"""
import importlib.util
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g1_workflow_gate as W

launch_path = Path(os.environ['A7_GRADING_LAUNCH'])
assert G._sha_file(str(launch_path)) == os.environ['A7_GRADING_LAUNCH_SHA256']
launch = G._read(str(launch_path))
run_dir, cand = launch['run_dir'], launch['candidate_dir']
root = G.load_root(run_dir, launch['root_sha256'])
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      launch['owners']['grading_scorer'])
assert G.owner_hashes() == root['owners'] == launch['owners']
assert W.owner_sha256() == launch['workflow_gate_sha256']
assert G.live_output_limit() == root['max_output_tokens']

operator = A7 / 'unit_1792/view/scratchpad/g1_run_1525.py'
assert G._sha_file(str(operator)) == 'e2aba199fbe7328ee4f14f6061cfc7599123360833142414bf1e8a79c2f2715d'
spec = importlib.util.spec_from_file_location('historical_g1_operator', str(operator))
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
assert old.G is G and old.W is W
command = os.environ.get('A7_GRADING_COMMAND', 'status')
with R._using(old, RUN=run_dir, CAND=cand, S=str(launch_path.parent)):
    assert old.root_sha() == launch['root_sha256']
    if command == 'status':
        old.status()
    elif command == 'preflight':
        n = int(os.environ['A7_GRADING_SEGMENT'])
        receipt_sha = os.environ['A7_GRADING_RECEIPT_SHA256']
        packet, bad = G.preflight(cand, run_dir, n, launch['root_sha256'], receipt_sha)
        assert not bad, bad
        print(G._plain({'segment': n, 'root_sha256': launch['root_sha256'],
                        'receipt_sha256': receipt_sha, 'packet': packet}), flush=True)
    elif command == 'prepare':
        old.prepare()
    elif command == 'ingest':
        old.ingest(int(os.environ['A7_GRADING_SEGMENT']),
                   os.environ['A7_GRADING_RECEIPT_SHA256'],
                   os.environ['A7_GRADING_WORKFLOW_RUN'].removeprefix('wf_'))
    elif command == 'retry':
        # The existing finalizer determines eligibility; the external exact
        # lane list is a reviewer check, never an authorization to repeat a success.
        old.retry(os.environ['A7_GRADING_RETRY_LANES'].split(','))
    else:
        raise ValueError('unknown grading operation: ' + command)
