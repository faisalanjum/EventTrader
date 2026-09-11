"""Private copies for the complete clarified-review TEST lifecycle."""
from pathlib import Path
import shutil
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_2006'))
from check_native_isolation_2006 import B

tag = sys.argv[1]
assert tag.isalnum()
rows = B.read_map(str(UNIT.parent / 'unit_2010_native_fixture/map_native_2010.tsv'))
target = UNIT / ('integration_' + tag)
target.mkdir()
for row in rows:
    if row['mode'] != 'rw':
        continue
    source = Path(row['source'])
    copy = target / ('projects' if row['logical'] == B.PROJECTS_MOUNT else 'key_root')
    before = B.source_sha(str(source))
    shutil.copytree(source, copy)
    assert B.source_sha(str(copy)) == before == B.source_sha(str(source))
    row.update(source=str(copy), sha=before)
assert not B.validate(rows), B.validate(rows)
out = UNIT / ('map_integration_' + tag + '.tsv')
with out.open('x') as stream:
    stream.write(''.join('\t'.join(row[key] for key in ('logical', 'source', 'sha', 'mode'))
                        + '\n' for row in rows))
print(out)
