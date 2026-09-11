"""Combine reviewed file identities into an exact, non-staging publication list."""
import collections
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
REC = UNIT.parents[1]
sys.path.insert(0, str(UNIT.parent / 'unit_2006'))
from check_native_isolation_2006 import B

env = dict(os.environ)
for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
    env.pop(key, None)
git = lambda *args: subprocess.check_output(['git', '-C', str(REC), *args], env=env)
assert git('rev-parse', 'HEAD').decode().strip() == 'f985d272569ea09c1e0f96d95bff7ce00792515d'
assert not git('diff', '--cached', '--name-only'), 'an existing index change is not ours'
tracked = set(git('ls-files', '-z').decode().split('\0'))
dirty = set(git('diff', '--name-only', '-z').decode().split('\0')) - {''}
inputs = [UNIT.parent / 'unit_2013_publication_inventory/PUBLICATION_INVENTORY.json',
          UNIT / 'REVIEW_SNAPSHOT.json']
pins = ['41b24c3012d877a43fc460d8718cad1dfe5dd845c806e18f217e4aaa0c899aab',
        'aabbe8b770becca09f82ed9a056b0f75b88ddfc38b05a0120f80ea9bace41d9f']
entries = {}


def add(path, expected=None, reason='publication record'):
    p = Path(path)
    assert p.is_relative_to(REC) and p.is_file(), p
    rel = str(p.relative_to(REC))
    assert not p.is_symlink() or rel in tracked, 'refuse a new unreviewed symlink: ' + rel
    assert rel not in dirty, 'refuse unrelated tracked change: ' + rel
    sha = B.file_sha(str(p))
    assert expected is None or sha == expected, 'reviewed bytes changed: ' + rel
    if rel in entries:
        assert entries[rel]['sha256'] == sha
    entries[rel] = {'path': rel, 'sha256': sha, 'bytes': p.stat().st_size,
                    'already_tracked': rel in tracked, 'reason': reason}
    if p.is_symlink():
        entries[rel]['existing_symlink_target'] = os.readlink(p)


for p, pin in zip(inputs, pins):
    assert B.file_sha(str(p)) == pin
    for row in json.loads(p.read_text())['entries']:
        add(REC / row['path'], row['sha256'], row.get('reason', 'frozen reviewed file'))
    add(p, pin)
add(Path(__file__))
add(UNIT / 'FINAL_REVIEW.md')
add(UNIT.parent / 'unit_2014_closeout_review/battery_closeout_2014.py',
    '80b3b344692fbe2028c565b6f186e68e9ee49415dff2162e01f319a4fb7c53e4',
    'independent final closeout checker')
for name in ('exit', 'stdout.txt', 'stderr.txt', 'owner.tsv'):
    add(UNIT.parent / 'unit_1947/logs/attempt_core_closeout2014_c' / name,
        reason='independent final closeout raw evidence')

# These are the actual current replay/launch inputs, not every old private map.
# A directory pin is whole: no selected regular file inside it may be omitted.
missing = []
external = []
empty = set()
for name in ('map_approved_reuse_b.tsv', 'map_integration_retry.tsv'):
    for row in B.read_map(str(UNIT / name)):
        p = Path(row['source'])
        if not p.is_relative_to(REC):
            external.append({k: row[k] for k in ('logical', 'source', 'sha', 'mode')})
            continue
        assert p.exists(), p
        if row['mode'] == 'ro':
            assert B.source_sha(str(p)) == row['sha'], p
        paths = [p] if p.is_file() else [Path(d) / n for d, _, fs in os.walk(p) for n in fs]
        regular = [q for q in paths if q.is_file() and not q.is_symlink()]
        if not regular and p.is_dir():
            empty.add(str(p.relative_to(REC)))
        missing.extend(str(q.relative_to(REC)) for q in regular
                       if str(q.relative_to(REC)) not in entries)
assert not missing, ('required map input files absent', sorted(set(missing))[:20])
new = [e for e in entries.values() if not e['already_tracked']]
assert all(e['bytes'] <= 100 * 1024 * 1024 for e in new)
assert not any('/unit_2008/owner/a4_review_composite.py' in e['path'] for e in new)
doc = {
    'kind': 'Publication candidate only; no staging or complete A7 claim',
    'branch': git('rev-parse', '--abbrev-ref', 'HEAD').decode().strip(),
    'base': git('rev-parse', 'HEAD').decode().strip(),
    'inputs': dict(zip((str(p.relative_to(REC)) for p in inputs), pins)),
    'entries': [entries[p] for p in sorted(entries)],
    'new_files': len(new), 'new_bytes': sum(e['bytes'] for e in new),
    'external_bindings': external, 'empty_source_directories': sorted(empty),
    'limits': [
        'Historical verification reports may reference superseded disposable TEST clones not included here.',
        'Current exact native TEST replay inputs and the saved real answers are included.',
        'Requires the pinned main-tree authorities and existing subscription/runtime environment.',
        'Prior unit2008 record-composite results are diagnostics only; unit2009 is the approved replacement.',
        'Independent closeout is resolved by FINAL_REVIEW.md; exact staged-tree review is required before commit.',
    ],
}
with (HERE / 'VERIFIED_PUBLICATION.json').open('x') as stream:
    json.dump(doc, stream, indent=1)
with (HERE / 'verified_paths.nul').open('xb') as stream:
    stream.write(b''.join(e['path'].encode() + b'\0' for e in sorted(new, key=lambda e:e['path'])))
print(json.dumps({'files_referenced': len(entries), 'new_files': len(new),
                  'new_bytes': doc['new_bytes'], 'external_bindings': external,
                  'empty_source_directories': sorted(empty),
                  'candidate_sha256': B.file_sha(str(HERE / 'VERIFIED_PUBLICATION.json'))}, indent=1))
