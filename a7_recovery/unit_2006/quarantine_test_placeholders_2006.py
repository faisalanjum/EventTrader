"""Preserve only empty TEST placeholders created by the failed self-bind.

The actual original native records are untouched. No reviewed TEST artifact
is removed; the original workflow names were absent from the TEST namespace
before unit2006. Keep the empty placeholders recoverably outside mountpoints.
"""
import json
from pathlib import Path

UNIT = Path(__file__).resolve().parent
rows = [line.split('\t') for line in (UNIT / 'map_native_TEST_2006.tsv').read_text().splitlines()
        if line and not line.startswith('#')]
native_root = '/home/faisal/.claude/projects'
test_root = next(Path(row[1]) for row in rows if row[0] == native_root)
assert test_root == UNIT.parent / 'unit_2002/TEST_projects'
targets = []
for logical, source, sha, mode in rows:
    if Path(source).parent != UNIT / 'preserved_original_native' or not Path(source).is_dir():
        continue
    target = test_root / Path(logical).relative_to(native_root)
    if target.is_dir():
        continue
    assert target.is_file() and not target.is_symlink() and target.stat().st_size == 0, target
    targets.append(target)
dest = UNIT / 'rejected_empty_TEST_mountpoints'
dest.mkdir()
for target in targets:
    target.rename(dest / target.name)
print(json.dumps({'empty_TEST_placeholders_preserved': len(targets), 'original_native_changes': 0}))
