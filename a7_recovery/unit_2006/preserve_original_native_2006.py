"""Preserve byte-identical A3 native records for the isolated TEST namespace.

The TEST projects root shadows the real projects root. A later bind whose
source is that same shadowed path reads the TEST placeholder, not the real
record. Preserve only the already-listed A3 records outside that shadow.
This copies evidence, never constructs or edits native records.
"""
import importlib.util
import json
from pathlib import Path
import shutil

UNIT = Path(__file__).resolve().parent
REC = UNIT.parents[1]
boundary = REC / 'a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher/boundary.py'
spec = importlib.util.spec_from_file_location('boundary', boundary)
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)
rows = B.read_map(str(UNIT / 'map_candidate_TEST_2006.tsv'))
dest = UNIT / 'preserved_original_native'
dest.mkdir()
count = 0
for row in rows:
    source = Path(row['source'])
    if row['logical'] != row['source'] or not str(source).startswith(B.PROJECTS_MOUNT + '/'):
        continue
    assert row['mode'] == 'ro'
    assert B.source_sha(str(source)) == row['sha']
    target = dest / source.name
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copyfile(source, target)
    assert B.source_sha(str(target)) == row['sha']
    row['source'] = str(target)
    count += 1
assert count
print(json.dumps({'preserved_ro_bindings': count,
                  'map': ''.join('\t'.join(row[k] for k in ('logical', 'source', 'sha', 'mode')) + '\n'
                                 for row in rows)}))
