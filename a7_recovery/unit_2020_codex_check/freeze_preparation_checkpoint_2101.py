"""Freeze this reviewed preparation's explicit publication scope; never stage.

Every path is from this task's known code, run or test-output roots. Unrelated
work, including the pre-existing dirty grader copy, is never selected.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
REC = HERE.parents[1]
A7 = REC / 'a7_recovery'
PARENT = '01ddc8e35d11bab58c6ad24fa053f6257188615b'
OUT = HERE / 'PARTIAL_CHECKPOINT_2101.json'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REC).decode().strip()


assert git('rev-parse', 'HEAD') == PARENT
assert not git('diff', '--cached', '--name-only'), 'index is not empty'
assert not OUT.exists(), 'checkpoint is write-once'
selected = {A7 / 'A7_PREGRADING_WORK_ORDER.md', Path(__file__).resolve()}
for name in (
    'a7_partial_grading_2095.py', 'test_partial_grading_2095.py',
    'mutate_partial_grading_2095.py', 'prepare_g23_partial_2097.py',
    'test_g23_transport_2098.py', 'mutate_g23_transport_2098.py',
    'map_g23_transport_2098.tsv', 'review_g23_transport_2098.py',
    'compare_g23_preparation_2099.py', 'test_partial_scoring_native_2099.py',
    'PARTIAL_TEST_SOURCES_2099.json', 'freeze_g23_launch_2100.py',
    'G23_LAUNCH_REVIEW_2100.md', 'PARTIAL_PREPARATION_REVIEW_2101.md',
):
    selected.add(HERE / name)
roots = [A7 / n for n in (
    'unit_2097_partial_review', 'unit_2098_partial_regression',
    'unit_2099_partial_regression', 'unit_2100_partial_regression',
    'unit_2098_g23_transport', 'unit_2100_g23_grading')]
roots += [p for p in HERE.iterdir() if p.is_dir() and
          re.fullmatch(r'codex_(?:g23.*209[789].*|partial2098_mutations|partialscore2099_[abc])', p.name)]
for directory in (A7 / 'unit_1947/logs', A7 / 'unit_1957/logs'):
    roots += [p for p in directory.iterdir() if p.is_dir()
              and re.search(r'209[789]|2100', p.name)]
roots += [A7 / 'grader_20260909/attempts' / n for n in (
    'core2099base', 'core2099ctrl', 'core2100cur', 'core2100era',
    'core2100era2', 'core2100nat', 'core2100ord')]
selected.update((A7 / 'unit_1957').glob('map_codex_grader_core2099*.tsv'))
selected.update((A7 / 'unit_1957').glob('map_codex_grader_core2100*.tsv'))
for root in roots:
    assert root.is_dir(), str(root)
    selected.update(p for p in root.rglob('*') if p.is_file())
before = {}
for line in git('ls-tree', '-r', '--full-tree', PARENT).splitlines():
    info, path = line.split('\t', 1)
    before[path] = info.split()[2]
rows = []
for path in sorted(selected):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert not {'__pycache__', '.pytest_cache'} & set(path.parts), str(path)
    assert path.suffix != '.pyc' and path.name not in ('.env', '.credentials'), str(path)
    rel = str(path.relative_to(REC))
    assert rel != 'a7_recovery/grader_20260909/harness_g1v3/build_inventory_review.py'
    data = path.read_bytes()
    assert len(data) < 100 * 1024 * 1024, 'oversized Git blob: ' + rel
    blob = hashlib.sha1(('blob %d\0' % len(data)).encode() + data).hexdigest()
    rows.append({'path': rel, 'sha256': hashlib.sha256(data).hexdigest(),
                 'bytes': len(data), 'git_blob': blob,
                 'changed_from_parent': before.get(rel) != blob})
report = {'scope': 'verified partial-report and G2/G3 preparation plus complete TEST evidence; no A7 score',
          'parent': PARENT, 'actual_new_model_calls': 0,
          'files': rows, 'count': len(rows),
          'changed_files': sum(r['changed_from_parent'] for r in rows),
          'bytes': sum(r['bytes'] for r in rows)}
with OUT.open('x') as stream:
    json.dump(report, stream, indent=1)
    stream.write('\n')
print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
print('manifest_sha256', hashlib.sha256(OUT.read_bytes()).hexdigest())
