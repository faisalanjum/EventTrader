"""Read-only cross-check of the prepared REAL G2/G3 launch.

Three questions, and nothing else - this is not another code, prompt, source
or historical audit:

  1. Would the actual invocation use the EXACT published scriptPath and args?
  2. Is the frozen model/effort/agentType/input declaration the same one the
     G1 launch froze?
  3. Do the counters add up?

Every value is measured from the artifacts at read time. Writes one JSON
record beside this file and touches nothing else.
"""
import collections
import glob
import hashlib
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
LAUNCH_DIR = os.path.join(A7, 'unit_2100_g23_grading')
#: the only A7 collection that has actually made calls, and its published run
G1 = os.path.join(A7, 'unit_2088_real_grading')
PROFILE_KEY = 'expected_input_for_served_lanes'


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def where(path):
    """Which tree a path lives in - the distinction the audit turns on."""
    if '/EventMarketDB-driver-recovery/' in path:
        return 'recovery'
    return 'scratchpad' if '/scratchpad/' in path else 'other'


# ---- what the ONLY proven A7 launch actually executed ---------------------------
executed = collections.Counter()
for state_file in sorted(glob.glob(os.path.join(G1, 'g1/state.*.json'))):
    for official in json.load(io.open(state_file))['states']:
        # the PLATFORM's own record, not our invocation file
        executed[where(json.load(io.open(official))['scriptPath'])] += 1
g1_launch = json.load(io.open(os.path.join(G1, 'LAUNCH.json')))

kinds = collections.OrderedDict()
for kind in sorted(os.listdir(LAUNCH_DIR)):
    run = os.path.join(LAUNCH_DIR, kind, 'run')
    launch = json.load(io.open(os.path.join(LAUNCH_DIR, kind, 'LAUNCH.json')))
    root = json.load(io.open(os.path.join(run, 'root.json')))
    receipt = json.load(io.open(os.path.join(run, 'receipt.seg01.json')))
    invocation = json.load(io.open(os.path.join(run, 'invocation.seg01.json')))
    state = json.load(io.open(os.path.join(run, 'state.seg01.json')))
    operator_args = json.load(io.open(
        os.path.join(LAUNCH_DIR, kind, 'g1_args_seg01.json')))
    profile = json.load(io.open(launch['input_profile']))[PROFILE_KEY]
    by_lane = {r['lane_id']: r for r in root['rows']}

    kinds[kind] = collections.OrderedDict([
        # 1. the invocation
        ('script_path', receipt['script_path']),
        ('script_path_tree', where(receipt['script_path'])),
        ('script_sha256_matches_receipt',
         sha(os.path.join(run, 'grade_batch.seg01.js')) == receipt['script_sha256']),
        ('script_bytes', os.path.getsize(os.path.join(run, 'grade_batch.seg01.js'))),
        ('invocation_scriptPath_is_the_published_one',
         invocation['scriptPath'] == receipt['script_path']),
        ('operator_args_equal_invocation_args', operator_args == invocation['args']),
        ('every_arg_matches_its_root_row', all(
            by_lane.get(a['lane_id'], {}).get('prompt_sha256') == a['prompt_sha256']
            and by_lane.get(a['lane_id'], {}).get('batch_id') == a['batch_id']
            for a in invocation['args'])),
        ('lanes', [a['lane_id'] for a in invocation['args']]),
        ('receipt_binds', collections.OrderedDict(
            (name, sha(os.path.join(run, name)) == receipt[key])
            for name, key in (('root.json', 'root_sha256'),
                              ('invocation.seg01.json', 'invocation_sha256'),
                              ('reservation.seg01.json', 'reservation_sha256')))),
        # 2. the frozen declaration
        ('lane_declaration_equals_the_g1_launch', launch['lane'] == g1_launch['lane']),
        ('owners_equal_the_g1_launch', launch['owners'] == g1_launch['owners']),
        ('every_root_row_carries_the_profile_input',
         all(r.get('expected_input') == profile for r in root['rows'])),
        # 3. the counters
        ('primary_lanes', launch['total_primary_lanes']),
        ('root_rows', len(root['rows'])),
        ('budget', launch['budget']),
        ('calls_made_so_far', len(state['states'])),
        ('run_dir_tree', where(launch['run_dir'])),
    ])

budget = kinds['G2']['budget']
totals = collections.OrderedDict([
    ('primaries_sum', sum(k['primary_lanes'] for k in kinds.values())),
    ('budget_initial_calls', budget['initial_calls']),
    ('primaries_sum_equals_initial_calls',
     sum(k['primary_lanes'] for k in kinds.values()) == budget['initial_calls']),
    ('after_initial_adds_up',
     budget['spent_before'] + budget['initial_calls'] == budget['after_initial']),
    ('after_max_adds_up',
     budget['spent_before'] + budget['initial_calls'] * budget['max_attempts_per_row']
     == budget['after_max']),
    ('after_max_within_ceiling', budget['after_max'] <= budget['ceiling']),
    ('both_kinds_share_one_budget', kinds['G2']['budget'] == kinds['G3']['budget']),
])

record = collections.OrderedDict([
    ('kind', 'read-only cross-check of the prepared REAL G2/G3 launch'),
    ('per_kind', kinds),
    ('counters', totals),
    ('the_only_proven_a7_launch', collections.OrderedDict([
        ('published_run_dir_tree', where(g1_launch['run_dir'])),
        ('official_workflow_states_by_tree', dict(executed)),
        ('note', 'these are the PLATFORM\'s own state files for the 862 real '
                 'calls, not our own invocation records')])),
    ('the_audit_rule_that_removes_the_fallback', collections.OrderedDict([
        ('owner', 'audit_worker_access._same_published_script, line 188'),
        ('used_at', 'audit_worker_access line 1298'),
        ('rule', 'os.path.samefile: two different files with identical bytes '
                 'are still two files and are refused')])),
    ('model_calls', 0)])
OUT = os.path.join(HERE, 'G23_LAUNCH_CROSSCHECK_2101.json')
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')

for kind, info in kinds.items():
    print('%s  lanes=%s  script=%s tree=%s  args_match=%s  decl_same=%s  calls=%d'
          % (kind, info['lanes'], info['script_bytes'], info['script_path_tree'],
             info['operator_args_equal_invocation_args'],
             info['lane_declaration_equals_the_g1_launch'],
             info['calls_made_so_far']))
print('counters all consistent:', all(v for v in totals.values() if isinstance(v, bool)))
print('G1 executed from:', dict(executed), '| G1 run_dir tree:',
      where(g1_launch['run_dir']))
print('wrote', OUT)
