"""Read-only ETA input: exact existing-renderer groups, not launch authority."""
import os
import runpy
from pathlib import Path

assert os.environ['A7_GRADING_COMMAND'] == 'preflight'
HERE = Path(__file__).resolve().parent
ctx = runpy.run_path(str(HERE / 'run_grading_2086.py'))
G, W, run, candidate, launch = (ctx[k] for k in ('G', 'W', 'run_dir', 'cand', 'launch'))
root = G.load_root(run, launch['root_sha256'])
states = G.lane_states(run)
remaining = [r['lane_id'] for r in root['rows'] if states.get(r['lane_id']) != 'called']
pending, groups = list(remaining), []
while pending:
    lanes, size, problems = W._largest_prefix(candidate, root, pending, W.PRIMARY_ATTEMPT)
    assert not problems and lanes and lanes == pending[:len(lanes)], problems
    groups.append({'lanes': lanes, 'script_bytes': size})
    pending = pending[len(lanes):]
assert [lane for group in groups for lane in group['lanes']] == remaining
out = HERE / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'BATCH_MEASUREMENT.json'), G._pretty({
    'scope': 'read-only primary-size forecast at one state snapshot; no launch authority or score',
    'root_sha256': launch['root_sha256'], 'gate_sha256': W.owner_sha256(),
    'state_snapshot': states, 'remaining_primaries': len(remaining),
    'remaining_workflow_groups_without_retries': len(groups), 'groups': groups,
    'actual_model_calls': 0}) + '\n')
print('MEASURED', len(remaining), 'remaining primaries in', len(groups),
      'exact-rendered groups; retries and ongoing-call time not predicted', flush=True)
