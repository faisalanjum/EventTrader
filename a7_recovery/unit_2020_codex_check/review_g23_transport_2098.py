"""Exercise the real size gate without publishing or calling any model."""
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import a7_g23_run as GR
import a7_g1_workflow_gate as W

launch_path = os.environ['A7_GRADING_LAUNCH']
assert G._sha_file(launch_path) == os.environ['A7_GRADING_LAUNCH_SHA256']
launch = G._read(launch_path)
B.bind_grading_scorer(str(Path(G.__file__).parent / 'scorers/score_exp5_current.py'),
                      launch['owners']['grading_scorer'])
assert G.owner_hashes() == launch['owners']
path = os.environ['A7_VERIFY_G23_PREPARATION']
assert G._sha_file(path) == os.environ['A7_VERIFY_G23_PREPARATION_SHA256']
preparation = G._read(path)
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()
result = {'scope': 'TEST of exact candidate transport size; zero model calls or publications',
          'preparation': path, 'limit': W.SCRIPT_BYTE_LIMIT, 'kinds': {}}
for kind, candidate in preparation['candidates'].items():
    directory = str(Path(candidate['path']).parent)
    run = str(out / ('TEST_' + kind))
    root, digest, problems = G.freeze_root(directory, run, candidate['sha256'])
    assert not problems, problems
    lanes, size, problems = W.next_admissible(directory, run, digest)
    measured = []
    for row in root['rows']:
        amount, errors = W._script_bytes(directory, root, [row['lane_id']], 1)
        assert not errors, errors
        measured.append({'lane': row['lane_id'], 'script_bytes': amount})
    result['kinds'][kind] = {'root_sha256': digest, 'next': lanes, 'script_bytes': size,
                             'problems': problems, 'measured': measured,
                             'oversized': [r for r in measured if r['script_bytes'] > W.SCRIPT_BYTE_LIMIT]}
G._write_new(str(out / 'TRANSPORT.json'), G._pretty(result) + '\n')
print(G._plain({k: {name: v for name, v in row.items() if name not in ('measured', 'oversized')}
                | {'oversized_lanes': len(row['oversized'])} for k, row in result['kinds'].items()}), flush=True)
assert all(not row['problems'] and not row['oversized'] for row in result['kinds'].values()), \
    'the candidate cannot execute through the unchanged transport gate'
