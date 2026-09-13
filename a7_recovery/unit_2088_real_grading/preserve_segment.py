"""Preserve one G1 segment's native evidence and record its outcome.

Usage: preserve_segment.py <segment> <workflow_run_id>

Copies never overwrite: each run gets its own subdirectory under
native/seg<NN>, every copy is re-hashed against the live record it came from,
and the original native records are only read. Written with exclusive create,
so re-running cannot silently replace an earlier segment's evidence.
"""
import collections
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time

SEGMENT = int(sys.argv[1])
RUN = sys.argv[2]
TAG = 'seg%02d' % SEGMENT
HERE = os.path.dirname(os.path.abspath(__file__))
REC = os.path.dirname(os.path.dirname(HERE))
G1 = os.path.join(HERE, 'g1')
LIVE = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')
SRC_STATE = os.path.join(LIVE, 'workflows', RUN + '.json')
SRC_DIR = os.path.join(LIVE, 'subagents', 'workflows', RUN)
DEST = os.path.join(HERE, 'native', TAG, RUN)
INV_OUT = os.path.join(HERE, 'NATIVE_INVENTORY_%s.json' % TAG.upper())
REC_OUT = os.path.join(HERE, 'OUTCOME_%s.json' % TAG.upper())
EXECUTED = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
            '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a7_grading_2088/g1/'
            'grade_batch.%s.js' % TAG)


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def worker_identity(path):
    """model / request / response as the worker's own transcript records them."""
    model = request = response = None
    for line in io.open(path, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue                      # a line that will not parse decides nothing
        message = record.get('message')
        if not isinstance(message, dict):
            continue
        model = message.get('model') or model
        request = record.get('requestId') or request
        response = message.get('id') or response
    return model, request, response


# ---------------------------------------------------------------- copy, never clobber
os.makedirs(DEST)
copies = [(SRC_STATE, RUN + '.state.json'),
          (os.path.join(SRC_DIR, 'journal.jsonl'), RUN + '.journal.jsonl')]
for name in sorted(os.listdir(SRC_DIR)):
    if name.startswith('agent-'):
        copies.append((os.path.join(SRC_DIR, name), name))
for src, name in copies:
    shutil.copyfile(src, os.path.join(DEST, name))

files, differ = [], []
for src, name in copies:
    path = os.path.join(DEST, name)
    digest = sha(path)
    matches = sha(src) == digest
    files.append(collections.OrderedDict([
        ('name', name), ('sha256', digest), ('bytes', os.path.getsize(path)),
        ('source', src), ('matches_source', matches)]))
    if not matches:
        differ.append(name)

# ---------------------------------------------------------------- what the run recorded
state = json.load(io.open(os.path.join(DEST, RUN + '.state.json')))
journal = [json.loads(l) for l
           in io.open(os.path.join(DEST, RUN + '.journal.jsonl'), encoding='utf-8')
           if l.strip()]
results = {r['agentId']: r.get('result') for r in journal if r.get('type') == 'result'}
failed = [r for r in journal if r.get('type') == 'failed']
lanes_progress = [p for p in state.get('workflowProgress', [])
                  if p.get('type') == 'workflow_agent']
returned = (state.get('result') or {}).get('results') or []

lane_rows, no_text, no_transcript = [], [], []
for index, lane in enumerate(lanes_progress):
    agent_id = lane.get('agentId')
    transcript = os.path.join(DEST, 'agent-%s.jsonl' % agent_id)
    model = request = response = None
    if os.path.isfile(transcript):
        model, request, response = worker_identity(transcript)
    else:
        no_transcript.append(lane.get('label'))
    text = returned[index].get('text') if index < len(returned) else None
    error = returned[index].get('error') if index < len(returned) else None
    if not text:
        no_text.append(lane.get('label'))
    lane_rows.append(collections.OrderedDict([
        ('lane_id', lane.get('label')), ('state', lane.get('state')),
        ('blocked', lane.get('blocked')), ('error', lane.get('error') or error),
        ('agent_id', agent_id), ('transcript_model', model),
        ('request_id', request), ('response_id', response),
        ('raw_text_sha256', sha_text(text) if text else None),
        ('raw_text_bytes', len(text.encode('utf-8')) if text else 0),
        ('journal_result_matches_returned_text',
         results.get(agent_id) == text if agent_id in results else False)]))

inventory = collections.OrderedDict([
    ('kind', 'preserved native evidence and identity inventory for G1 %s' % TAG),
    ('segment', SEGMENT), ('run_id', RUN), ('directory', DEST),
    ('file_count', len(files)),
    ('all_copies_match_source', not differ), ('copies_that_differ', differ),
    ('task_id', state.get('taskId')), ('status', state.get('status')),
    ('start_time_ms', state.get('startTime')), ('duration_ms', state.get('durationMs')),
    ('agent_count', state.get('agentCount')),
    ('total_tokens', state.get('totalTokens')),
    ('total_tool_calls', state.get('totalToolCalls')),
    ('script_path', state.get('scriptPath')),
    ('default_model_field', state.get('defaultModel')),
    ('default_model_note',
     'the parent chat model the harness records, not the worker identity'),
    ('journal_lines', len(journal)), ('journal_results', len(results)),
    ('journal_failed', len(failed)),
    ('lanes_recorded', len(lanes_progress)),
    ('lanes_with_text', len(lanes_progress) - len(no_text)),
    ('lanes_without_text', no_text),
    ('lanes_missing_a_transcript', no_transcript),
    ('distinct_agent_ids', len({r['agent_id'] for r in lane_rows})),
    ('distinct_request_ids', len({r['request_id'] for r in lane_rows if r['request_id']})),
    ('distinct_response_ids', len({r['response_id'] for r in lane_rows if r['response_id']})),
    ('transcript_models', sorted({r['transcript_model'] for r in lane_rows
                                  if r['transcript_model']})),
    ('every_journal_result_equals_its_returned_text',
     all(r['journal_result_matches_returned_text'] for r in lane_rows)),
    ('lanes', lane_rows), ('files', files)])
with io.open(INV_OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(inventory, indent=1) + '\n')

# ---------------------------------------------------------------- the outcome record
launch = json.load(io.open(os.path.join(HERE, 'LAUNCH.json')))
head = subprocess.run(['git', '-C', REC, 'rev-parse', 'HEAD'],
                      capture_output=True, text=True).stdout.strip()
record = collections.OrderedDict([
    ('kind', 'the authorized Workflow call for G1 %s and its outcome' % TAG),
    ('authority_sha256', sha('/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md')),
    ('publication_head', head),
    ('recorded_utc', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())),
    ('recorded_utc_note',
     'recording time, not the call start; the official state startTime is the truth'),
    ('segment', SEGMENT), ('workflow_run_id', RUN), ('task_id', state.get('taskId')),
    ('launch_record', os.path.join(HERE, 'LAUNCH_RECORD_%s.json' % TAG.upper())),
    ('launch_record_sha256',
     sha(os.path.join(HERE, 'LAUNCH_RECORD_%s.json' % TAG.upper()))),
    ('script_path_called', state.get('scriptPath')),
    ('executed_script_sha256', sha(EXECUTED)),
    ('preserved_script_sha256', sha(os.path.join(G1, 'grade_batch.%s.js' % TAG))),
    ('root_sha256', launch['root_sha256']),
    ('candidate_sha256', launch['candidate_sha256']),
    ('receipt_sha256', sha(os.path.join(G1, 'receipt.%s.json' % TAG))),
    ('invocation_sha256', sha(os.path.join(G1, 'invocation.%s.json' % TAG))),
    ('transport', collections.OrderedDict(sorted(launch['lane'].items()))),
    ('transcript_models_observed', inventory['transcript_models']),
    ('counts', collections.OrderedDict([
        ('scheduled', len(json.load(io.open(
            os.path.join(G1, 'invocation.%s.json' % TAG)))['args'])),
        ('launched', inventory['lanes_recorded']),
        ('captured_with_text', inventory['lanes_with_text']),
        ('journal_failed', inventory['journal_failed']),
        ('distinct_agents', inventory['distinct_agent_ids']),
        ('distinct_requests', inventory['distinct_request_ids']),
        ('distinct_responses', inventory['distinct_response_ids'])])),
    ('lane_identities', [collections.OrderedDict([
        ('lane_id', r['lane_id']), ('agent_id', r['agent_id']),
        ('request_id', r['request_id']), ('response_id', r['response_id']),
        ('raw_text_sha256', r['raw_text_sha256'])]) for r in lane_rows]),
    ('completed_calls_note',
     'this record reports THIS run only. A cumulative call total must not be '
     'derived from valid readings: a completed call that the finalizer rejects '
     'is still a spent call. The authoritative running totals are the '
     'finalizers own attempted/valid/invalid columns.'),
    ('full_initial_g1_requirement', launch['total_primary_lanes']),
    ('evidence_dir', DEST), ('evidence_inventory', INV_OUT),
    ('evidence_inventory_sha256', sha(INV_OUT)),
    ('finalization', 'not yet run at the time this record was written'),
    ('no_grading_score_claimed', True)])
with io.open(REC_OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')

print('inventory', INV_OUT, sha(INV_OUT))
print('outcome  ', REC_OUT, sha(REC_OUT))
print('files %d (all match source %s) | lanes %d, with text %d, failed %d'
      % (len(files), not differ, inventory['lanes_recorded'],
         inventory['lanes_with_text'], inventory['journal_failed']))
print('agents %d | requests %d | responses %d | models %s'
      % (inventory['distinct_agent_ids'], inventory['distinct_request_ids'],
         inventory['distinct_response_ids'], inventory['transcript_models']))
print('journal result == returned text for every lane:',
      inventory['every_journal_result_equals_its_returned_text'])
print('this run: %d attempted, %d returned text (validity is the finalizers call)'
      % (record['counts']['launched'], record['counts']['captured_with_text']))
