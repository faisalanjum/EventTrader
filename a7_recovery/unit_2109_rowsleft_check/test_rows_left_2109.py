"""Can a FINALIZED UNCALLED primary be reported finished? Reproduce, then fix.

rows_left_2104.py unions every finalization's `validity` rows. The transport
refusal closure writes validity [[lane, False], ...] AND uncalled [lanes] for
the same lanes (a7_g1_workflow_gate.py line 476/479), so those lanes appear in
validity while still needing a call. G.lane_states is the original owner of
that question and uses `uncalled`, not `validity`.

Durable, uniquely tagged, read-only against real state.
"""
import collections
import io
import json
import os
import shutil
import subprocess
import sys

A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery'
HERE = os.path.join(A7, 'unit_2109_rowsleft_check')
VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
G2 = os.path.join(A7, 'unit_2103_g23_grading/G2')
G3 = os.path.join(A7, 'unit_2103_g23_grading/G3')
CONNECTOR = os.path.join(A7, 'unit_2103_execution_prep/rows_left_2104.py')
TAG = os.environ.get('A7_TEST_TAG', 'q1')
WORK = os.path.join(HERE, 'runs_%s' % TAG)
sys.path[:0] = [VIEW, os.path.join(A7, 'unit_2020_codex_check'),
                os.path.join(A7, 'unit_2009/owner')]
os.chdir(VIEW)
import a7_g1_build as G                                            # noqa: E402
import a7_g23_build as B                                           # noqa: E402

LAUNCH = json.load(io.open(os.path.join(G2, 'LAUNCH.json')))
B.bind_grading_scorer(
    os.path.join(os.path.dirname(G.__file__), 'scorers/score_exp5_current.py'),
    LAUNCH['owners']['grading_scorer'])
assert not os.path.isdir(WORK), '%s exists; pick a new A7_TEST_TAG' % WORK
os.makedirs(WORK)

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print('  %-64s %s %s' % (name, 'PASS' if ok else 'FAIL', str(detail)[:60]))


def connector(run_dir):
    """The connector as the driver actually calls it."""
    out = subprocess.run([sys.executable, '-B', CONNECTOR, run_dir],
                         capture_output=True, text=True,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return out.stdout.strip(), out.returncode


def owner_left(run_dir, root):
    """The same question asked of the ORIGINAL owner."""
    states = G.lane_states(run_dir)
    return len([r['lane_id'] for r in root['rows']
                if states.get(r['lane_id']) != 'called'])


# ---- the real runs first: the connector must already agree here --------------
for name, path, expect in (('G2', os.path.join(G2, 'run'), 137),
                           ('G3', os.path.join(G3, 'run'), 0)):
    root = G.load_root(path, G._sha_file(os.path.join(path, 'root.json')))
    said, code = connector(path)
    check('%s: connector reports the actual remaining count' % name,
          said == str(expect) and code == 0, '%s (want %d)' % (said, expect))
    check('%s: the original owner agrees on the real run' % name,
          owner_left(path, root) == expect, owner_left(path, root))

# ---- now the shape that breaks it -------------------------------------------
run = os.path.join(WORK, 'refusal_shaped', 'run')
shutil.copytree(LAUNCH['run_dir'], run)
root = G.load_root(run, G._sha_file(os.path.join(run, 'root.json')))
before_conn, _ = connector(run)
before_owner = owner_left(run, root)
check('positive control: both agree before the refusal-shaped closure',
      before_conn == str(before_owner) == '137', '%s / %s' % (before_conn, before_owner))

# publish a real never-called primary through the real publisher, then give it
# the finalization SHAPE the transport-refusal closure writes (validity rows
# for lanes that are simultaneously uncalled). Written here as a fixture, not
# by calling that closure, which would need a fabricated tool refusal.
G._write_new(G.finalization_path(run, 5), G._pretty(collections.OrderedDict([
    ('schema', G.SCHEMA), ('segment', 5), ('attempt', 2),
    ('validity', []), ('problems', {}), ('retry', []),
    ('uncalled', ['G2-001/G1a']),
    ('ledger', {'scheduled': 0, 'valid': 0, 'invalid': 0, 'retry': 0,
                'uncalled': 1})])) + '\n')
identity, problems = G.publish_run(LAUNCH['candidate_dir'], run,
                                   G._sha_file(os.path.join(run, 'root.json')),
                                   ['G2-002/G1a'], attempt=1)
check('positive control: a real never-called primary was published',
      identity is not None and not problems, problems[:1])
seg = identity['segment']
receipt = G.load_receipt(run, seg)
lanes = [r['lane_id'] for r in receipt['rows']]
G._write_new(G.finalization_path(run, seg), G._pretty(collections.OrderedDict([
    ('schema', G.SCHEMA), ('segment', seg), ('attempt', receipt['attempt']),
    ('validity', [[lane, False] for lane in lanes]),      # <- the refusal shape
    ('problems', {lane: ['prelaunch_refusal'] for lane in lanes}),
    ('retry', []), ('uncalled', list(lanes)),
    ('ledger', {'scheduled': 0, 'valid': 0, 'invalid': 0, 'retry': 0,
                'uncalled': len(lanes)})])) + '\n')

after_conn, _ = connector(run)
after_owner = owner_left(run, root)
check('positive control: the lane really is still uncalled per the owner',
      G.lane_states(run).get('G2-002/G1a') == 'uncalled',
      G.lane_states(run).get('G2-002/G1a'))
print('    connector says %s remaining; the owner says %s'
      % (after_conn, after_owner))
check('and the original owner still counts it as remaining',
      after_owner == before_owner, after_owner)
# With the connector FIXED to reuse G.lane_states, it must now agree with the
# owner on exactly this shape. Before the fix this check failed (136 vs 137).
check('FIXED: the connector now agrees with the original owner',
      int(after_conn) == after_owner, '%s vs %s' % (after_conn, after_owner))

# ---- the other lane states, each with its own control -----------------------
states = G.lane_states(run)
check('control: a called primary is reported called',
      states.get('G2-000/G1a') == 'called', states.get('G2-000/G1a'))
check('control: an invalid-BUT-CALLED primary is still called, not remaining',
      states.get('G2-001/G1a') == 'called', states.get('G2-001/G1a'))
check('control: a retry-only lane never becomes a primary again',
      'G2-001/G1a' not in [r['lane_id'] for r in root['rows']
                           if states.get(r['lane_id']) != 'called'])
# taken from the root rather than typed, so it is a lane that really exists
unseen = [r['lane_id'] for r in root['rows'] if r['lane_id'] not in states]
check('positive control: the root really has never-seen primaries',
      bool(unseen), len(unseen))
check('control: an unseen primary is counted as remaining',
      unseen and unseen[0] in [r['lane_id'] for r in root['rows']
                               if states.get(r['lane_id']) != 'called'],
      unseen[:1])

json.dump({'connector_before': before_conn, 'owner_before': before_owner,
           'connector_after': after_conn, 'owner_after': after_owner,
           'reproduced': int(after_conn) < after_owner, 'model_calls': 0},
          io.open(os.path.join(WORK, 'REPRODUCTION.json'), 'w'), indent=1)

print()
passed = sum(1 for _n, ok in RESULTS if ok)
print('%d/%d checks passed' % (passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
