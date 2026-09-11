"""Isolate the already-qualified ordinary/native fixtures for these four edits.

No new test runner or expected result. Reuse the original regression payload,
its exact two module populations and all frozen read-only inputs. Copy only
writable fixtures, not old test-output trees. Original evidence stays untouched.
"""
import json
from pathlib import Path
import shutil
import sys

UNIT = Path(__file__).resolve().parent
REC = UNIT.parents[1]
GRADER = UNIT.parent / 'grader_20260909'
BND = REC / 'a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher'
sys.path.insert(0, str(BND))
import boundary as B
from check_native_isolation_2006 import native_targets, check as check_native

group = sys.argv[1]
tag = sys.argv[2]
assert tag.isalnum()
old = {'ordinary': 'ordinary_final4', 'native': 'native_final5'}[group]
source_root = GRADER / 'attempts' / old
target = UNIT / ('regression_' + group + '_' + tag)
target.mkdir()
template = UNIT.parent / 'unit_1957' / ('map_codex_grader_' + old + '.tsv')
rows = B.read_map(str(template))
# September 10's owner-approved evidence-reuse docs supersede the old whole-
# directory pin. Use the exact already-reviewed live binding, never accept an
# arbitrary directory rehash; record this sole input delta in the preparation.
authority = '/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign'
current = B.read_map(str(UNIT / 'map_native_TEST_2006.tsv'))
replacement = [r for r in current if r['source'] == authority]
assert len(replacement) == 1 and replacement[0]['mode'] == 'ro'
prior_authority = []
for index, row in enumerate(rows):
    if row['source'] == authority:
        prior_authority.append(dict(row))
        assert row['logical'] == replacement[0]['logical']
        rows[index] = dict(replacement[0])
assert len(prior_authority) == 1
assert not B.validate(rows), B.validate(rows)
copied = {}
for row in rows:
    if row['mode'] != 'rw':
        continue
    source = Path(row['source'])
    if source not in copied:
        dest = target / source.relative_to(source_root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if row['logical'] in ('/tmp/a7_logs_1781', '/tmp/a7_g23_route_audit'):
            dest.mkdir()
            if group == 'native' and row['logical'] == '/tmp/a7_logs_1781':
                # Use the store BEFORE a regression added its synthetic jobs.
                # Copying the completed suite's store repeats TEST run ids.
                fixture = next(r for r in rows if r['logical'] ==
                               '/tmp/a7_logs_1781/attempt_grader_path7')
                pristine = Path(fixture['source']).parent / 'life_native5'
                shutil.copytree(pristine, dest / 'life_native5')
        elif source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
        copied[source] = dest
    row['source'] = str(copied[source])
if group == 'ordinary':
    # This historical test writes/restores both the native state and its child
    # records. Bind private copies, never the live session or frozen archive.
    for logical, preserved in native_targets():
        dest = target / 'native_mutation_fixture' / preserved.parent.name / preserved.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if preserved.is_dir():
            shutil.copytree(preserved, dest)
        else:
            shutil.copy2(preserved, dest)
        rows.append(dict(logical=str(logical), source=str(dest),
                         sha=B.source_sha(str(dest)), mode='rw'))
    assert check_native(rows)
harness = next(r for r in rows if r['logical'].endswith('/experiments/harness_g1v3')
               and '/bench_1306/' in r['logical'])
changed = sorted((UNIT / 'harness_g1v3').glob('*.py'))
assert len(changed) == 4
changed = [UNIT / 'harness_warm' / p.name if p.name == 'a7_prepared_run.py' else p
           for p in changed]
for path in changed:
    baseline = Path(harness['source']) / path.name
    assert baseline.read_bytes() == (UNIT.parent / 'unit_1997/harness_g1v3' / path.name).read_bytes()
    rows.append(dict(logical=harness['logical'] + '/' + path.name,
                     source=str(path), sha=B.file_sha(str(path)), mode='ro'))
assert not B.validate(rows), B.validate(rows)
map_path = UNIT / ('map_regression_' + group + '_2006_' + tag + '.tsv')
with map_path.open('x') as stream:
    for row in rows:
        stream.write('\t'.join(row[k] for k in ('logical', 'source', 'sha', 'mode')) + '\n')
with (target / 'PREPARATION.json').open('x') as stream:
    json.dump({'template': str(template), 'template_sha256': B.file_sha(str(template)),
               'map': str(map_path), 'map_sha256': B.file_sha(str(map_path)),
               'prior_authority': prior_authority, 'current_authority': replacement,
               'old': old, 'group': group, 'changed': {p.name: B.file_sha(str(p)) for p in changed}}, stream, indent=1)
print(str(map_path))
