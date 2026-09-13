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
MAP = os.path.join(A7, 'unit_2020_codex_check/map_g23_transport_2098.tsv')
HARNESS_LOGICAL = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
                   '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
                   '.claude/plans/Drivers/experiments/harness_g1v3')
#: 'current' reproduces Core 2099; 'era' additionally serves the key owner the
#: preserved lineage's receipt was sealed under. One variable, nothing else.
ARM = sys.argv[1] if len(sys.argv) > 1 else 'current'
assert ARM in ('current', 'era', 'era2'), ARM
DEST = os.path.join(HERE, 'harness_%s' % ARM)
OUT = os.path.join(HERE, 'PRIVATE_HARNESS_2100_%s.json' % ARM)
ERA_VIEW = os.path.join(
    A7, 'grader_20260909/attempts/native_final5/view/harness_g1v3')
#: 'era' isolates the key owner alone. 'era2' adds the module that RENDERS the
#: hard-review prompt live, which is the second era-bound field the receipt
#: pins. This is a diagnostic arm, not a proposal to serve old code.
ERA_FILES = {'era': ('build_kfields_key.py',),
             'era2': ('build_kfields_key.py', 'build_kfields_hard_review.py')}
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

# THE ONE VARIABLE. The era arm serves the key owner whose bytes the preserved
# lineage's receipt pins, at the only path its verifier reads - the harness dir
# itself, because _derived_from hashes os.path.join(_HERE, "build_kfields_key.py").
# OWNER_EQUIVALENCE_2100.json proves the two versions differ in one function
# whose changed comparison reads a constant bound once to the value it read
# before, so this serves the era's BYTES, never older behaviour.
era_swap = []
for name0 in ERA_FILES.get(ARM, ()):
    target, source = os.path.join(DEST, name0), os.path.join(ERA_VIEW, name0)
    swap = collections.OrderedDict([
        ('name', name0), ('replaced_sha256', sha(target)),
        ('with_sha256', sha(source)), ('source', source)])
    assert swap['replaced_sha256'] != swap['with_sha256'], '%s: no change' % name0
    shutil.copyfile(source, target)
    assert sha(target) == swap['with_sha256']
    era_swap.append(swap)
era_swap = era_swap or None

# THE FOUR HISTORICAL ARTIFACTS ARE prepare.py's TO SUPPLY, NOT MINE.
# With historical=True it asserts each is ABSENT from the snapshot and copies
# it from the frozen legacy tree. The current harness already carries all four,
# byte-identical to that legacy source, so a complete tree makes that assertion
# fail. Removing them here hands the job back to the routine that owns it; the
# provisioner then asserts the finished snapshot equals the complete tree, so
# the served bytes are unchanged either way.
HISTORICAL_NAMES = ('exp5_prompt_producer.v2.md', 'frozen_proof_r15.txt',
                    'step1_inventory.json', 'launch_exp5_readers.workflow.js')
LEGACY = os.path.join(A7, 'unit_1771/tree/.claude/plans/Drivers/experiments'
                          '/harness_g1v3')
complete_tree_sha = B.source_sha(DEST)
handed_back = []
for name0 in HISTORICAL_NAMES:
    here, legacy = os.path.join(DEST, name0), os.path.join(LEGACY, name0)
    assert sha(here) == sha(legacy), (
        '%s is not the legacy bytes; removing it would change what is served'
        % name0)
    handed_back.append(collections.OrderedDict([
        ('name', name0), ('sha256', sha(here))]))
    os.remove(here)


report = collections.OrderedDict([
    ('kind', 'private CURRENT harness incl. the one G2/G3 transport overlay'),
    ('arm', ARM),
    ('key_owner_served', sha(os.path.join(DEST, 'build_kfields_key.py'))),
    ('historical_artifacts_handed_back_to_prepare', handed_back),
    ('complete_tree_sha256_before_handback', complete_tree_sha),
    ('era_owner_swap', era_swap),
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
