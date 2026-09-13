"""Why the existing TEST preparation refuses, and the smallest fix that clears it.

The preparer asserts its template validates before it builds anything. It does
not. This records the exact refusal, identifies the cause from git rather than
from bytes, and proves by positive control that ONE re-pinned row is the whole
remedy - all in memory, editing nobody's file.
"""
import collections
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
REC = os.path.dirname(A7)
MAIN = '/home/faisal/EventMarketDB'
TEMPLATE = os.path.join(A7, 'unit_1957/map_1957_test.tsv')
OUT = os.path.join(HERE, 'TEMPLATE_REFUSAL_2098.json')
sys.path.insert(0, os.path.join(
    REC, 'a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626',
    'out/a4_final_lock_1683/launcher'))
import boundary as B                                              # noqa: E402

rows = B.read_map(TEMPLATE)
refusal = [str(p) for p in B.validate(rows)]

# WHICH rows, named by their own logical path rather than by position
# ONLY the rows validate itself refuses. An unpinned row records '-' and an
# rw row is not pinned at all; comparing those to a measured sha invents drift
# the checker never claimed, which my first pass did.
drifted, unpinned_skipped = [], 0
for row in rows:
    if row['mode'] != 'ro' or row['sha'] in ('-', '', None):
        unpinned_skipped += 1
        continue
    measured = B.source_sha(row['source'])
    if measured != row['sha']:
        drifted.append(collections.OrderedDict([
            ('logical', row['logical']), ('source', row['source']),
            ('template_pin', row['sha']), ('measured_now', measured)]))

# THE CAUSE, from git: is any TRACKED governing file modified, or is this only
# new untracked material dropped into a directory the template pins wholesale?
def git(*args, cwd):
    return subprocess.run(['git', '-C', cwd] + list(args),
                          capture_output=True, text=True).stdout

cause = {}
for d in drifted:
    src = d['source']
    repo = MAIN if src.startswith(MAIN + os.sep) else REC
    status = git('status', '--porcelain', '--', os.path.relpath(src, repo), cwd=repo)
    lines = [l for l in status.split('\n') if l.strip()]
    cause[d['logical']] = collections.OrderedDict([
        ('repo', repo),
        ('tracked_modified', [l for l in lines if l[:2].strip() in ('M', 'MM', 'AM')]),
        ('untracked_additions', [l[3:] for l in lines if l.startswith('??')])])

# POSITIVE CONTROL: re-pin ONLY the drifted rows to their measured value and
# validate again. If that clears it, one re-pin is the entire remedy.
patched = [dict(r) for r in rows]
for r in patched:
    if any(r['logical'] == d['logical'] for d in drifted):
        r['sha'] = B.source_sha(r['source'])
assert len(drifted) == len(refusal), (
    'the rows I call drifted must be exactly the ones validate refuses: '
    '%d vs %d' % (len(drifted), len(refusal)))
after = [str(p) for p in B.validate(patched)]

record = collections.OrderedDict([
    ('kind', 'exact refusal of the existing TEST preparation, and its smallest fix'),
    ('template', TEMPLATE),
    ('template_rows', len(rows)),
    ('rows_not_pinned_so_not_checked', unpinned_skipped),
    ('refusal_before', refusal),
    ('drifted_rows', drifted),
    ('cause_from_git', cause),
    ('positive_control_repin_only_those_rows', collections.OrderedDict([
        ('problems_after', after),
        ('clears_the_refusal', not after)])),
    ('smallest_rule_owner_fix',
     'no tracked governing document changed; the template pins the whole main '
     'FinalDesign DIRECTORY, so untracked additions to it break TEST '
     'preparation. Re-pin that single row in unit_1957/map_1957_test.tsv to '
     'its measured tree sha, or narrow it to the files the tests actually '
     'read. Not mine to edit.'),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('refusal:', refusal)
print('drifted rows:', len(drifted))
for d in drifted:
    print('  ', d['logical'])
    print('     pin', d['template_pin'][:16], '-> now', d['measured_now'][:16])
    c = cause[d['logical']]
    print('     tracked modified:', len(c['tracked_modified']),
          '| untracked additions:', len(c['untracked_additions']))
    for u in c['untracked_additions']:
        print('        ??', u)
print('positive control clears it:',
      record['positive_control_repin_only_those_rows']['clears_the_refusal'])
print('wrote', OUT)
