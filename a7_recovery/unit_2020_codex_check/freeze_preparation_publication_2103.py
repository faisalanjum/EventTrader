"""Finalize the already staged checkpoint plus the bounded path correction.

Preserve the original checkpoint manifest. Only its two current status/review
documents may change; every other recorded byte must still match. No staging.
"""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REC = HERE.parents[1]
A7 = REC / 'a7_recovery'
BASE = HERE / 'PARTIAL_CHECKPOINT_2101.json'
OUT = HERE / 'PARTIAL_PUBLICATION_2103.json'
sha = lambda data: hashlib.sha256(data).hexdigest()
blob = lambda data: hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest()
assert sha(BASE.read_bytes()) == '8ac1dccc1c90883307277b637f242b991797b088b29474c28521fb8f2ed7620d'
base = json.loads(BASE.read_text())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REC).decode().strip() == base['parent']
assert not OUT.exists(), 'publication manifest is write-once'
changed_docs = {'a7_recovery/A7_PREGRADING_WORK_ORDER.md',
                'a7_recovery/unit_2020_codex_check/PARTIAL_PREPARATION_REVIEW_2101.md'}
selected = {REC / row['path'] for row in base['files']}
for row in base['files']:
    data = (REC / row['path']).read_bytes()
    if row['path'] not in changed_docs:
        assert sha(data) == row['sha256'] and blob(data) == row['git_blob'], row['path']
selected.update((BASE, Path(__file__).resolve()))
selected.update(HERE / name for name in (
    'freeze_g23_transport_2103.py', 'map_g23_transport_2103.tsv',
    'G23_TRANSPORT_REVIEW_2103.md'))
roots = [A7 / name for name in ('unit_2101_launch_crosscheck',
                               'unit_2102_transport_probe', 'unit_2103_g23_grading')]
roots += [A7 / 'unit_1947/logs' / ('attempt_' + tag) for tag in (
    'codex_g23transport2103_a', 'codex_g2preflight2103_a',
    'codex_g3preflight2103_a', 'codex_g2wrongreceipt2103_a',
    'codex_g3wrongreceipt2103_a')]
for root in roots:
    assert root.is_dir(), str(root)
    selected.update(p for p in root.rglob('*') if p.is_file())
before = {}
for line in subprocess.check_output(['git', 'ls-tree', '-r', '--full-tree', base['parent']], cwd=REC).decode().splitlines():
    info, path = line.split('\t', 1)
    before[path] = info.split()[2]
rows = []
for path in sorted(selected):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert not {'__pycache__', '.pytest_cache'} & set(path.parts), str(path)
    assert path.suffix != '.pyc' and path.name not in ('.env', '.credentials'), str(path)
    rel = str(path.relative_to(REC))
    assert rel.startswith('a7_recovery/') and rel != 'a7_recovery/grader_20260909/harness_g1v3/build_inventory_review.py'
    data = path.read_bytes()
    assert len(data) < 100 * 1024 * 1024, rel
    rows.append({'path': rel, 'sha256': sha(data), 'bytes': len(data),
                 'git_blob': blob(data), 'changed_from_parent': before.get(rel) != blob(data)})
report = {'scope': 'verified partial-report preparation and supported execution locations; no A7 score or new model calls',
          'parent': base['parent'], 'base_manifest': str(BASE.relative_to(REC)),
          'base_manifest_sha256': sha(BASE.read_bytes()),
          'updated_documents': sorted(changed_docs), 'actual_new_model_calls': 0,
          'files': rows, 'count': len(rows), 'bytes': sum(r['bytes'] for r in rows),
          'changed_files': sum(r['changed_from_parent'] for r in rows)}
with OUT.open('x') as stream:
    json.dump(report, stream, indent=1)
    stream.write('\n')
print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
print('manifest_sha256', sha(OUT.read_bytes()))
