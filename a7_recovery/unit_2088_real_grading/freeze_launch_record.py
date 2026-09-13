"""Freeze the pre-call launch record for one G1 segment.

Usage: freeze_launch_record.py <segment>

Every hash is measured from the file it names. Written with exclusive create,
so it can never overwrite an earlier segment's record.
"""
import collections
import hashlib
import io
import json
import os
import subprocess
import sys
import time

SEGMENT = int(sys.argv[1])
TAG = 'seg%02d' % SEGMENT
HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.dirname(os.path.dirname(HERE))
G1 = os.path.join(HERE, 'g1')
EXECUTED = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
            '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a7_grading_2088/g1/'
            'grade_batch.%s.js' % TAG)
OUT = os.path.join(HERE, 'LAUNCH_RECORD_%s.json' % TAG.upper())


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


launch = json.load(io.open(os.path.join(HERE, 'LAUNCH.json')))
invocation = json.load(io.open(os.path.join(G1, 'invocation.%s.json' % TAG)))
lanes = [r['lane_id'] for r in invocation['args']]
# the attempt is the published rows' own, never a constant typed here
attempts = sorted({r['attempt'] for r in invocation['args']})
assert len(attempts) == 1, 'one published segment carries one attempt: %s' % attempts
attempt = attempts[0]
# and the authority is whichever message is currently in the mailbox
INBOUND = '/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md'
authority = 'Codex SEQ ' + next(
    l.split(':', 1)[1].strip() for l in io.open(INBOUND, encoding='utf-8')
    if l.startswith('SEQ:'))
head = subprocess.run(['git', '-C', REC, 'rev-parse', 'HEAD'],
                      capture_output=True, text=True).stdout.strip()
stat = os.stat(EXECUTED)

# THE property that matters: no reading the finalizer already ACCEPTED may be
# asked again. Membership in a prior invocation is not it - a lawful retry is a
# prior invocation's lane by definition, which is why the earlier version of
# this record refused the authorized attempt 2. The accepted set comes from the
# finalizers' own validity tables, so this record never decides validity itself.
accepted = set()
for name in sorted(os.listdir(G1)):
    if name.startswith('finalization.'):
        doc = json.load(io.open(os.path.join(G1, name)))
        accepted |= {lane for lane, ok in doc['validity'] if ok}

record = collections.OrderedDict([
    ('kind', 'pre-call launch record for G1 segment %d' % SEGMENT),
    ('authority', authority),
    ('authority_sha256', sha(INBOUND)),
    ('publication_head', head),
    ('frozen_utc', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())),
    ('segment', SEGMENT),
    ('attempt', attempt),
    ('map', os.path.join(os.path.dirname(HERE),
                         'unit_2020_codex_check/map_real_grading_2088.tsv')),
    ('map_sha256', sha(os.path.join(os.path.dirname(HERE),
                                    'unit_2020_codex_check/map_real_grading_2088.tsv'))),
    ('caller_sha256', sha(os.path.join(os.path.dirname(HERE),
                                       'unit_2020_codex_check/run_grading_2086.py'))),
    ('launch_sha256', sha(os.path.join(HERE, 'LAUNCH.json'))),
    ('root_sha256', launch['root_sha256']),
    ('candidate_sha256', launch['candidate_sha256']),
    ('receipt_sha256', sha(os.path.join(G1, 'receipt.%s.json' % TAG))),
    ('invocation_sha256', sha(os.path.join(G1, 'invocation.%s.json' % TAG))),
    ('preserved_script', os.path.join(G1, 'grade_batch.%s.js' % TAG)),
    ('preserved_script_sha256', sha(os.path.join(G1, 'grade_batch.%s.js' % TAG))),
    ('published_args_file', os.path.join(HERE, 'g1_args_%s.json' % TAG)),
    ('published_args_sha256', sha(os.path.join(HERE, 'g1_args_%s.json' % TAG))),
    ('executed_script_path', EXECUTED),
    ('executed_script_sha256', sha(EXECUTED)),
    ('executed_script_bytes', stat.st_size),
    ('executed_script_is_regular_file',
     os.path.isfile(EXECUTED) and not os.path.islink(EXECUTED)),
    ('executed_script_hardlinks', stat.st_nlink),
    ('transport', collections.OrderedDict(sorted(launch['lane'].items()))),
    ('segment_lanes', len(lanes)),
    ('lane_ids', lanes),
    ('readings_already_accepted', len(accepted)),
    ('repeats_an_accepted_reading', sorted(set(lanes) & accepted)),
    ('total_primary_lanes', launch['total_primary_lanes']),
    ('launched', 0)])
assert not record['repeats_an_accepted_reading'], \
    'this segment would repeat a reading the finalizer already accepted'
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('wrote', OUT)
print('record sha256', sha(OUT))
print('segment %d: %d lanes %s .. %s | script %s %d B regular=%s links=%d'
      % (SEGMENT, len(lanes), lanes[0], lanes[-1],
         record['executed_script_sha256'][:16], record['executed_script_bytes'],
         record['executed_script_is_regular_file'], record['executed_script_hardlinks']))
print('%s | attempt %d | accepted readings so far %d | repeats: %s'
      % (record['authority'], attempt, record['readings_already_accepted'],
         record['repeats_an_accepted_reading'] or 'none'))
