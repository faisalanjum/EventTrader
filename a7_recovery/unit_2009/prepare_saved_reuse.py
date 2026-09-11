"""Use the reviewed grading owners and preserved original native evidence."""
from pathlib import Path
import json
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_2006'))
from check_native_isolation_2006 import B

rows = B.read_map(str(UNIT / 'map_integration_a.tsv'))
qualified = B.read_map(str(UNIT.parent / 'unit_2006/map_warm_TEST_2006.tsv'))
native = UNIT.parent / 'unit_2006/preserved_original_native'
owners = {str(UNIT.parent / ('unit_2006/' + name)) for name in (
    'harness_g1v3/a6_launch_freeze.py', 'harness_warm/a7_prepared_run.py',
    'harness_g1v3/a7_g1_build.py', 'harness_g1v3/a7_g23_build.py')}
selected = [r for r in qualified if Path(r['source']).is_relative_to(native)
            or r['source'] in owners]
assert len([r for r in selected if r['source'] in owners]) == 4
assert all(r['mode'] == 'ro' for r in selected)
logical = {r['logical'] for r in selected}
rows = [r for r in rows if r['logical'] not in logical] + selected
assert not B.validate(rows), B.validate(rows)
approved = len(sys.argv) == 2 and sys.argv[1] == 'approved'
if approved:
    saved = json.loads((UNIT / 'TEST_codex_join2009_a/TEST_RESULT.json').read_text())
    for name in ('a4_final_key_lock.json', 'a4_final_key_lock_receipt.json'):
        source = Path(saved['candidate']) / name
        rows.append(dict(logical='/tmp/a7_approved_key/' + name,
                         source=str(source), sha=B.file_sha(str(source)), mode='ro'))
    rows.append(dict(logical='/tmp/a7_approved_key/ordinary_bound.json',
                     source=saved['ordinary'], sha=B.file_sha(saved['ordinary']), mode='ro'))
    assert not B.validate(rows), B.validate(rows)
path = UNIT / ('map_approved_reuse_b.tsv' if approved else 'map_signed_reuse_a.tsv')
with path.open('x') as stream:
    stream.write(''.join('\t'.join(r[k] for k in ('logical','source','sha','mode'))
                        + '\n' for r in rows))
print(path, 'rows', len(rows), 'selected', len(selected))
