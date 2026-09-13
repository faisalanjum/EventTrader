"""Measure the completed G2 collection under the SERVED owners. Read only.

Runs as a boundary payload, exactly like the pinned retry filter: the same
read-only preflight bootstrap loads the same operator, so every owner used here
is the one the transport map actually serves, not a host copy. The recovery
split is NOT recomputed - it is the completion owner's own identity under the
pinned format scope. Nothing is written; the whole manifest goes to stdout and
the boundary runner preserves it as that attempt's evidence.
"""
if __name__ == '__main__':
    import os
    import runpy
    from pathlib import Path
    if os.environ.get('A7_GRADING_COMMAND') != 'preflight':
        raise ValueError('this manifest only permits the read-only preflight bootstrap')
    import sys
    A7 = Path(__file__).resolve().parents[1]
    # the pinned format owner is published beside the operator; it verifies its
    # own code and rule hashes inside scope(), so importing it proves nothing
    # on its own and cannot substitute a different file silently
    sys.path.insert(0, str(A7 / 'unit_2020_codex_check'))
    ctx = runpy.run_path(str(A7 / 'unit_2020_codex_check/run_grading_2086.py'))

import collections
import hashlib
import io
import os
import sys
from pathlib import Path

import a7_g1_build as G
import a7_g1_complete_v2 as C
import a7_g23_build as B
import a4_review_composite as R
import raw_transport as RT
import a7_meaning_format_2105 as F

A7 = Path(__file__).resolve().parents[1]
KIND = os.environ['A7_MANIFEST_KIND']
UNIT = A7 / 'unit_2103_g23_grading' / KIND
RUN = str(UNIT / 'run')
CODE = os.environ['A7_FORMAT_CODE_SHA256']
RULE = os.environ['A7_FORMAT_RULE_SHA256']


def sha(path):
    with io.open(str(path), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


owners = collections.OrderedDict(
    (name, {'path': module.__file__, 'sha256': sha(module.__file__)})
    for name, module in [('a7_g1_build', G), ('a7_g1_complete_v2', C),
                         ('a7_g23_build', B), ('a4_review_composite', R),
                         ('raw_transport', RT), ('a7_meaning_format_2105', F)])

launch = G._read(str(UNIT / 'LAUNCH.json'))
root = G.load_root(RUN, launch['root_sha256'])
digest, count = C.run_digest(RUN)

segments, calls = [], []
for n in G.segments(RUN):
    tag = 'seg%02d' % n
    note = UNIT / ('LAUNCH_NOTE_%s.json' % tag.upper())
    workflow = G._read(str(note))['workflow_id'] if note.exists() else None
    preserved = UNIT / 'native' / tag / (workflow or '') / 'PRESERVED.json'
    final = G._read(G.finalization_path(RUN, n))
    invocation = Path(RUN) / ('invocation.%s.json' % tag)
    segments.append(collections.OrderedDict([
        ('segment', n), ('workflow_id', workflow),
        ('state', G.segment_state(RUN, n)), ('attempt', final['attempt']),
        ('request_sha256', sha(invocation) if invocation.exists() else None),
        ('receipt_sha256', sha(Path(RUN) / ('receipt.%s.json' % tag))),
        ('finalization_sha256', sha(G.finalization_path(RUN, n))),
        ('native_manifest_sha256', sha(preserved) if preserved.exists() else None),
        ('ledger', final['ledger']), ('uncalled', final['uncalled']),
    ]))
    if invocation.exists():
        for row in G._read(str(invocation))['args']:
            calls.append(collections.OrderedDict(
                [('segment', n)] + [(k, row[k]) for k in sorted(row)]))

# the completion owner's own recovery audit, under the pinned format scope
with F.scope(CODE, RULE):
    identity = C.g23_identity(launch['root_sha256'], RUN)
audit = identity['meaning_format_recovery']['attempts']
states = G.lane_states(RUN)
answers = collections.Counter()
for record in audit:
    answers['original_valid' if record['original_valid'] else
            ('recovered' if record['recovered'] else 'exhausted_unusable')] += 1

report = collections.OrderedDict([
    ('kind', KIND),
    ('launch_sha256', sha(UNIT / 'LAUNCH.json')),
    ('root_sha256', launch['root_sha256']),
    ('candidate_sha256', root['candidate_sha256']),
    ('run_whole_tree_digest', digest), ('run_file_count', count),
    ('root_rows', len(root['rows'])),
    ('lane_states', dict(collections.Counter(states.values()))),
    ('uncalled_rows', [r['lane_id'] for r in root['rows']
                       if states.get(r['lane_id']) != 'called']),
    ('answers', dict(answers)), ('attempts_recorded', len(audit)),
    ('attempt_numbers', dict(collections.Counter(c['attempt'] for c in calls))),
    ('actual_calls', len(calls)), ('segments', segments), ('calls', calls),
    ('recovery_audit', audit),
    ('format_code_sha256', CODE), ('format_rule_sha256', RULE),
    ('owner_modules', owners),
])
sys.stdout.write(G._pretty(report) + '\n')
