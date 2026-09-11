"""Private native-store copy for the complete saved-answer TEST lifecycle."""
import json
from pathlib import Path
import shutil
import sys

from check_native_isolation_2006 import B

unit = Path(__file__).resolve().parent
tag = sys.argv[1]
assert tag.isalnum()
rows = B.read_map(str(unit / 'map_warm_TEST_2006.tsv'))
root = [r for r in rows if r['logical'] == B.PROJECTS_MOUNT]
assert len(root) == 1
source = Path(root[0]['source'])
before = B.source_sha(str(source))
target = unit / ('lifecycle_projects_' + tag)
shutil.copytree(source, target)
assert B.source_sha(str(target)) == before == B.source_sha(str(source))
root[0].update(source=str(target), sha=before)
assert not B.validate(rows), B.validate(rows)
path = unit / ('map_lifecycle_TEST_2006_' + tag + '.tsv')
with path.open('x') as stream:
    stream.write(''.join('\t'.join(r[k] for k in ('logical', 'source', 'sha', 'mode')) + '\n' for r in rows))
with (unit / ('lifecycle_preparation_' + tag + '.json')).open('x') as stream:
    json.dump(dict(source=str(source), source_sha256=before, private_copy=str(target),
                   map=str(path), map_sha256=B.file_sha(str(path))), stream, indent=1)
print(path)
