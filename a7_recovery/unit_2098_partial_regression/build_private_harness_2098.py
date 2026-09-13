"""Build the private, verified CURRENT harness this regression must be served.

It is exactly what map_real_grading_2088.tsv serves the real grading runs: the
unit_2008 tree, then the individual file rows that override it. Every override
is re-hashed against the map before it is used, and the base tree is re-hashed
against the map's own pinned tree sha, so this copy is the served bytes rather
than a convenient nearby tree.

TEST-only. Reads the frozen sources, writes only inside this unit.
"""
import collections
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
REC = os.path.dirname(A7)
MAP = os.path.join(A7, 'unit_2020_codex_check/map_real_grading_2088.tsv')
HARNESS_LOGICAL = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
                   '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
                   '.claude/plans/Drivers/experiments/harness_g1v3')
DEST = os.path.join(HERE, 'harness_g1v3')
OUT = os.path.join(HERE, 'PRIVATE_HARNESS_2098.json')
sys.path.insert(0, os.path.join(
    REC, 'a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626',
    'out/a4_final_lock_1683/launcher'))
import boundary as B                                              # noqa: E402


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


rows = [l.rstrip('\n').split('\t') for l in io.open(MAP, encoding='utf-8')]
rows = [r for r in rows if len(r) >= 4]
base = [r for r in rows if r[0] == HARNESS_LOGICAL]
assert len(base) == 1, 'the map serves %d harness trees' % len(base)
base_source, base_sha = base[0][1], base[0][2]
measured = B.source_sha(base_source)
assert measured == base_sha, 'the served harness tree moved: %s' % measured

assert not os.path.exists(DEST), 'the private harness already exists'
shutil.copytree(base_source, DEST)
assert B.source_sha(DEST) == base_sha, 'the copy is not the served tree'

# the file rows that override that tree, applied in map order, each re-hashed
overrides = []
for logical, source, want, _mode in rows:
    if not logical.startswith(HARNESS_LOGICAL + '/'):
        continue
    if logical.count('/') != HARNESS_LOGICAL.count('/') + 1:
        continue                       # a nested directory row, not a file override
    if os.path.isdir(source):
        continue
    got = sha(source)
    assert got == want, '%s is %s, the map pins %s' % (source, got, want)
    target = os.path.join(DEST, os.path.basename(logical))
    shutil.copyfile(source, target)
    assert sha(target) == want
    overrides.append(collections.OrderedDict([
        ('name', os.path.basename(logical)), ('source', source), ('sha256', want)]))

# THE DIRTY FILE QUESTION, ANSWERED FROM GIT RATHER THAN FROM ITS BYTES.
# unit_2008's copy is committed and clean; the grader_20260909 copy is the
# tracked-modified one. They currently hold the same bytes, so identity has to
# come from provenance, not from a hash comparison.
name = 'build_inventory_review.py'
grader = os.path.join(A7, 'grader_20260909/harness_g1v3', name)
mine = os.path.join(DEST, name)
status = subprocess.run(
    ['git', '-C', REC, 'status', '--porcelain', '--',
     os.path.relpath(os.path.join(base_source, name), REC)],
    capture_output=True, text=True).stdout.strip()
committed = subprocess.run(
    ['git', '-C', REC, 'show', 'HEAD:' + os.path.relpath(
        os.path.join(base_source, name), REC)],
    capture_output=True, text=True).stdout

report = collections.OrderedDict([
    ('kind', 'private verified CURRENT harness for the affected regression'),
    ('base_source', base_source),
    ('base_tree_sha256', base_sha),
    ('base_tree_matches_the_live_map', measured == base_sha),
    ('override_count', len(overrides)),
    ('overrides', overrides),
    ('private_harness', DEST),
    ('private_tree_sha256', B.source_sha(DEST)),
    ('dirty_file_check', collections.OrderedDict([
        ('name', name),
        ('served_copy_git_status', status or 'clean'),
        ('served_copy_matches_its_own_commit',
         hashlib.sha256(committed.encode()).hexdigest() == sha(mine)),
        ('grader_working_copy_sha256', sha(grader) if os.path.isfile(grader) else None),
        ('served_copy_sha256', sha(mine)),
        ('note', 'the two copies hold the same bytes; the served one is '
                 'committed and clean, the grader one is the tracked-modified '
                 'file. Provenance, not bytes, is what distinguishes them.')])),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(report, indent=1) + '\n')
print('private harness', DEST)
print('base tree', base_sha[:16], 'matches live map', measured == base_sha)
print('overrides applied', len(overrides), [o['name'] for o in overrides])
print('private tree sha', report['private_tree_sha256'][:16])
print('served build_inventory_review.py status:',
      report['dirty_file_check']['served_copy_git_status'],
      '| matches its own commit:',
      report['dirty_file_check']['served_copy_matches_its_own_commit'])
print('wrote', OUT)
