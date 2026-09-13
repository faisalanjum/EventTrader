"""Exact file/hash and run/agent/request/response inventory for G1 segment 1.

Read-only over the live native records. Every preserved copy is re-hashed
against the record it came from, so this proves the copy rather than asserting
it, and nothing in the source tree is written or changed.

Two runs live side by side and are kept apart on purpose: the earlier
pre-worker refusal stays at the seg01 root exactly as it was committed, and the
answered run gets its own subdirectory.
"""
import collections
import hashlib
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SEG = os.path.join(HERE, 'native', 'seg01')
LIVE = ('/home/faisal/.claude/projects/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200')
REFUSED = 'wf_61f6147b-947'
ANSWERED = 'wf_9a7866e5-c64'
RUN_DIR = os.path.join(SEG, ANSWERED)
OUT = os.path.join(HERE, 'NATIVE_INVENTORY_SEG01.json')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def source_of(name, run):
    """Where a preserved file came from, by its own name."""
    if name == run + '.state.json':
        return os.path.join(LIVE, 'workflows', run + '.json')
    if name == run + '.journal.jsonl':
        return os.path.join(LIVE, 'subagents', 'workflows', run, 'journal.jsonl')
    if name.startswith('agent-'):
        return os.path.join(LIVE, 'subagents', 'workflows', run, name)
    if name.endswith('.returned.txt'):
        return None            # the tool result as returned; no live twin to re-hash
    return None


def inventory_files(directory, run):
    rows, differ, unsourced = [], [], []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            continue
        digest = sha(path)
        src = source_of(name, run)
        matches = bool(src) and os.path.isfile(src) and sha(src) == digest
        rows.append(collections.OrderedDict([
            ('name', name), ('sha256', digest),
            ('bytes', os.path.getsize(path)),
            ('source', src), ('matches_source', matches)]))
        if src is None:
            unsourced.append(name)
        elif not matches:
            differ.append(name)
    return rows, differ, unsourced


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
            continue                       # a line that will not parse decides nothing
        message = record.get('message')
        if not isinstance(message, dict):
            continue
        model = message.get('model') or model
        request = record.get('requestId') or request
        response = message.get('id') or response
    return model, request, response


refusal_rows, refusal_differ, refusal_unsourced = inventory_files(SEG, REFUSED)
run_rows, run_differ, run_unsourced = inventory_files(RUN_DIR, ANSWERED)

journal = [json.loads(l) for l
           in io.open(os.path.join(RUN_DIR, ANSWERED + '.journal.jsonl'),
                      encoding='utf-8') if l.strip()]
results = [r for r in journal if r.get('type') == 'result']
started = [r for r in journal if r.get('type') == 'started']
failed = [r for r in journal if r.get('type') == 'failed']

state = json.load(io.open(os.path.join(RUN_DIR, ANSWERED + '.state.json')))
lanes = [p for p in state.get('workflowProgress', [])
         if p.get('type') == 'workflow_agent']

# the run's own returned rows, in the order the serial script produced them
returned = state.get('result') or {}
rows_out = returned.get('results') or []

by_agent = {}
for record in results:
    by_agent[record['agentId']] = record.get('result')

lane_rows, empty_text, missing_transcript = [], [], []
for index, lane in enumerate(lanes):
    agent_id = lane.get('agentId')
    transcript = os.path.join(RUN_DIR, 'agent-%s.jsonl' % agent_id)
    model = request = response = None
    if os.path.isfile(transcript):
        model, request, response = worker_identity(transcript)
    else:
        missing_transcript.append(lane.get('label'))
    text = rows_out[index].get('text') if index < len(rows_out) else None
    if not text:
        empty_text.append(lane.get('label'))
    lane_rows.append(collections.OrderedDict([
        ('lane_id', lane.get('label')),
        ('state', lane.get('state')),
        ('agent_id', agent_id),
        ('transcript_model', model),
        ('request_id', request),
        ('response_id', response),
        ('raw_text_sha256', sha_text(text) if text else None),
        ('raw_text_bytes', len(text.encode('utf-8')) if text else 0),
        ('journal_result_matches_returned_text',
         by_agent.get(agent_id) == text if agent_id in by_agent else False)]))

inventory = collections.OrderedDict([
    ('kind', 'preserved native evidence and identity inventory for G1 segment 1'),
    ('runs', collections.OrderedDict([
        (REFUSED, 'earlier pre-worker refusal, kept at the seg01 root, untouched'),
        (ANSWERED, 'the owner-authorized answered run, in its own subdirectory')])),
    ('refusal_evidence', collections.OrderedDict([
        ('directory', SEG), ('file_count', len(refusal_rows)),
        ('all_copies_match_source', not refusal_differ and not refusal_unsourced),
        ('files', refusal_rows)])),
    ('answered_run', collections.OrderedDict([
        ('run_id', ANSWERED),
        ('task_id', state.get('taskId')),
        ('status', state.get('status')),
        ('start_time_ms', state.get('startTime')),
        ('duration_ms', state.get('durationMs')),
        ('agent_count', state.get('agentCount')),
        ('total_tokens', state.get('totalTokens')),
        ('total_tool_calls', state.get('totalToolCalls')),
        ('script_path', state.get('scriptPath')),
        ('default_model_field', state.get('defaultModel')),
        ('default_model_note',
         'the parent chat model the harness records, not the worker identity'),
        ('journal_lines', len(journal)),
        ('journal_started', len(started)),
        ('journal_results', len(results)),
        ('journal_failed', len(failed)),
        ('lanes_recorded', len(lanes)),
        ('lanes_with_text', len(lanes) - len(empty_text)),
        ('lanes_without_text', empty_text),
        ('lanes_missing_a_transcript', missing_transcript),
        ('distinct_agent_ids', len({l['agent_id'] for l in lane_rows})),
        ('distinct_request_ids', len({l['request_id'] for l in lane_rows
                                      if l['request_id']})),
        ('distinct_response_ids', len({l['response_id'] for l in lane_rows
                                       if l['response_id']})),
        ('transcript_models', sorted({l['transcript_model'] for l in lane_rows
                                      if l['transcript_model']})),
        ('every_journal_result_equals_its_returned_text',
         all(l['journal_result_matches_returned_text'] for l in lane_rows)),
        ('file_count', len(run_rows)),
        ('all_copies_match_source', not run_differ),
        ('copies_that_differ', run_differ),
        ('files_with_no_live_twin', run_unsourced),
        ('lanes', lane_rows),
        ('files', run_rows)]))])

with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(inventory, indent=1) + '\n')
answered = inventory['answered_run']
print('wrote', OUT)
print('refusal files %d (all match source %s)'
      % (len(refusal_rows), inventory['refusal_evidence']['all_copies_match_source']))
print('answered files %d (all match source %s, no live twin: %s)'
      % (len(run_rows), answered['all_copies_match_source'], run_unsourced))
print('lanes %d | with text %d | agents %d | requests %d | responses %d'
      % (answered['lanes_recorded'], answered['lanes_with_text'],
         answered['distinct_agent_ids'], answered['distinct_request_ids'],
         answered['distinct_response_ids']))
print('models', answered['transcript_models'])
print('journal result == returned text for every lane:',
      answered['every_journal_result_equals_its_returned_text'])
