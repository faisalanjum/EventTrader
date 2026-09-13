"""Bind one segment's authorization to its exact request, BEFORE the call.

Evidence, not a rule engine: the publication receipt already owns validity.
This only records, from the preflight output rather than by hand, what was
about to be called and under whose authority - so a later reader can tell which
Codex message and which commit a call belongs to.

    python3 -B launch_note_2104.py <kind> <segment> <preflight stdout path>
"""
import collections
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
REC = os.path.dirname(A7)
MAILBOX = '/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md'
KIND, SEGMENT, PREFLIGHT = sys.argv[1], int(sys.argv[2]), sys.argv[3]
RUN = os.path.join(A7, 'unit_2103_g23_grading', KIND, 'run')
TAG = 'seg%02d' % SEGMENT
OUT = os.path.join(A7, 'unit_2103_g23_grading', KIND,
                   'LAUNCH_NOTE_%s.json' % TAG.upper())


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# The packet the operator itself returned - never a reconstruction. Taken as
# the last JSON object the payload printed, because preflight and retry emit
# the same fields in a different key order and a literal prefix match would
# only work for one of them.
result = None
for line in io.open(PREFLIGHT, encoding='utf-8'):
    line = line.strip()
    if line.startswith('{') and line.endswith('}'):
        try:
            candidate = json.loads(line)
        except ValueError:
            continue
        if 'packet' in candidate:
            result = candidate
assert result is not None, 'no packet line in %s' % PREFLIGHT
packet = result['packet']
invocation = json.load(io.open(os.path.join(RUN, 'invocation.%s.json' % TAG)))
receipt = json.load(io.open(os.path.join(RUN, 'receipt.%s.json' % TAG)))

assert packet['segment'] == SEGMENT, packet['segment']
assert packet['scriptPath'] == invocation['scriptPath'], 'preflight names another script'
assert packet['args'] == invocation['args'], 'preflight args are not the published args'
assert packet['receipt_sha256'] == sha(os.path.join(RUN, 'receipt.%s.json' % TAG))
root_sha = result.get('root_sha256') or sha(os.path.join(RUN, 'root.json'))
assert root_sha == sha(os.path.join(RUN, 'root.json'))
assert sha(packet['scriptPath']) == receipt['script_sha256'], \
    'the file at the execution path is not the published script'

# Codex: detect any already-started identity before calling. A segment that
# already recorded worker state has been run; calling it again would repeat a
# completed row. A note that already names a workflow is the same signal.
state = json.load(io.open(os.path.join(RUN, 'state.%s.json' % TAG)))
assert state['states'] == [], (
    'segment %d already recorded %d worker state(s); it has been run'
    % (SEGMENT, len(state['states'])))
if os.path.exists(OUT):
    existing = json.load(io.open(OUT))
    assert existing.get('workflow_id') is None, (
        'segment %d already names workflow %s'
        % (SEGMENT, existing['workflow_id']))

note = collections.OrderedDict([
    ('kind', KIND), ('segment', SEGMENT),
    ('authority', collections.OrderedDict([
        ('codex_message_seq', int(subprocess.run(
            ['sed', '-n', 's/^SEQ:[[:space:]]*//p', MAILBOX],
            capture_output=True, text=True).stdout.split('\n')[0])),
        ('codex_message_sha256', sha(MAILBOX)),
        ('recovery_commit', subprocess.run(
            ['git', '-C', REC, 'rev-parse', 'HEAD'],
            capture_output=True, text=True).stdout.strip()),
        ('owner_workflow_optin',
         'Run the workflow for all remaining G2 and G3 A7 grading calls and '
         "the permitted invalid-only retries, following Codex's instructions"),
    ])),
    ('root_sha256', root_sha),
    ('receipt_sha256', packet['receipt_sha256']),
    ('script_path', packet['scriptPath']),
    ('script_sha256', sha(packet['scriptPath'])),
    ('invocation_sha256', sha(os.path.join(RUN, 'invocation.%s.json' % TAG))),
    ('ordered_lanes', [a['lane_id'] for a in packet['args']]),
    ('attempts', sorted({a['attempt'] for a in packet['args']})),
    ('called_at_utc', None),
    ('workflow_id', None),
])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(note, indent=1) + '\n')
print(json.dumps(note, indent=1))
print('wrote', OUT)
