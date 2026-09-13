"""Read-only, complete live retry eligibility proof; never publishes a call."""
import json
import os
import runpy
from pathlib import Path

os.environ['A7_GRADING_COMMAND'] = 'status'
ns = runpy.run_path(str(Path(__file__).with_name('run_grading_2086.py')))
G, run, root = ns['G'], ns['run_dir'], ns['root']
expected = os.environ['A7_GRADING_RETRY_LANES'].split(',')
before = {str(p): G._sha_file(str(p)) for p in Path(run).rglob('*') if p.is_file()}
rows = []
for row in root['rows']:
    lane = row['lane_id']
    first = G.lifecycle_problems(run, root, [lane], 1)
    retry = G.lifecycle_problems(run, root, [lane], 2)
    assert first, 'a captured primary cannot run again: ' + lane
    rows.append({'lane': lane, 'first_refusal': first, 'retry_refusal': retry})
eligible = [r['lane'] for r in rows if not r['retry_refusal']]
assert eligible == expected, (eligible, expected)
assert set(G.latest_retry(run)) > set(eligible), 'live consumed-entry reproduction absent'
for lanes, attempt in (([], 2), (expected * 2, 2), (['unknown'], 2), (expected, 3)):
    assert G.lifecycle_problems(run, root, lanes, attempt), (lanes, attempt)
after = {str(p): G._sha_file(str(p)) for p in Path(run).rglob('*') if p.is_file()}
assert before == after, 'read-only eligibility check changed the run'
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()
(out / 'RETRY_PROOF.json').write_text(json.dumps({'eligible': eligible, 'rows': rows,
    'run_unchanged': True, 'negative_controls': 4}, sort_keys=True, indent=2) + '\n')
print('ELIGIBILITY_VERIFIED', len(rows), 'eligible', eligible, flush=True)
