"""The separate launch/outcome record for the ANSWERED segment-1 run.

The earlier pre-worker refusal keeps its own LAUNCH_RECORD_SEG01.json and
LAUNCHED_SEG01.json untouched; this is added beside them, never over them.
Every hash here is measured from the file it names.
"""
import collections
import hashlib
import io
import json
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
REC = os.path.dirname(A7)
RUN = 'wf_9a7866e5-c64'
SEG = os.path.join(HERE, 'native', 'seg01', RUN)
G1 = os.path.join(HERE, 'g1')
EXECUTED = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
            '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a7_grading_2088/g1/'
            'grade_batch.seg01.js')
OUT = os.path.join(HERE, 'LAUNCHED_SEG01_ANSWERED.json')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


launch = json.load(io.open(os.path.join(HERE, 'LAUNCH.json')))
inv = json.load(io.open(os.path.join(HERE, 'NATIVE_INVENTORY_SEG01.json')))
answered = inv['answered_run']
lanes = answered['lanes']
head = subprocess.run(['git', '-C', REC, 'rev-parse', 'HEAD'],
                      capture_output=True, text=True).stdout.strip()

record = collections.OrderedDict([
    ('kind', 'the owner-authorized answered Workflow call for segment 1'),
    ('authority', 'Codex SEQ 2088 authorized the 52 lanes; Codex SEQ 2090 adopted this run'),
    ('authority_sha256', sha('/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md')),
    ('relation_to_the_refusal',
     'wf_61f6147b-947 was refused before any worker existed and spent nothing; '
     'its record and evidence are preserved separately and unchanged'),
    ('publication_head', head),
    ('recorded_utc', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())),
    ('recorded_utc_note',
     'recording time, not the call start; the official state startTime is the truth'),

    ('workflow_run_id', RUN),
    ('task_id', answered['task_id']),
    ('status', answered['status']),
    ('start_time_ms', answered['start_time_ms']),
    ('duration_ms', answered['duration_ms']),
    ('total_tokens', answered['total_tokens']),
    ('total_tool_calls', answered['total_tool_calls']),

    ('script_path_called', answered['script_path']),
    ('executed_script_sha256', sha(EXECUTED)),
    ('executed_script_bytes', os.path.getsize(EXECUTED)),
    ('preserved_script_sha256', sha(os.path.join(G1, 'grade_batch.seg01.js'))),
    ('root_sha256', launch['root_sha256']),
    ('candidate_sha256', launch['candidate_sha256']),
    ('receipt_sha256', sha(os.path.join(G1, 'receipt.seg01.json'))),
    ('invocation_sha256', sha(os.path.join(G1, 'invocation.seg01.json'))),
    ('transport', collections.OrderedDict(sorted(launch['lane'].items()))),
    ('transcript_models_observed', answered['transcript_models']),

    ('counts', collections.OrderedDict([
        ('scheduled', launch['first_segment_lanes']),
        ('launched', answered['lanes_recorded']),
        ('captured_with_text', answered['lanes_with_text']),
        ('uncalled', launch['first_segment_lanes'] - answered['lanes_recorded']),
        ('journal_failed', answered['journal_failed']),
        ('distinct_agents', answered['distinct_agent_ids']),
        ('distinct_requests', answered['distinct_request_ids']),
        ('distinct_responses', answered['distinct_response_ids'])])),
    ('lane_identities', [collections.OrderedDict([
        ('lane_id', l['lane_id']), ('agent_id', l['agent_id']),
        ('request_id', l['request_id']), ('response_id', l['response_id']),
        ('raw_text_sha256', l['raw_text_sha256'])]) for l in lanes]),

    ('experiment_ledger_before', launch['budget']['spent_before']),
    ('experiment_ledger_after',
     launch['budget']['spent_before'] + answered['lanes_with_text']),
    ('ledger_note',
     'the earlier zero-worker refusal remains visible and adds nothing; it was '
     'never a model answer'),
    ('full_initial_g1_requirement', launch['total_primary_lanes']),
    ('evidence_dir', SEG),
    ('evidence_inventory', os.path.join(HERE, 'NATIVE_INVENTORY_SEG01.json')),
    ('evidence_inventory_sha256', sha(os.path.join(HERE, 'NATIVE_INVENTORY_SEG01.json'))),
    ('finalization', 'not yet run at the time this record was written'),
    ('no_grading_score_claimed', True)])

with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('wrote', OUT)
print('record sha256', sha(OUT))
print('ledger %d -> %d over %d captured lanes'
      % (record['experiment_ledger_before'], record['experiment_ledger_after'],
         record['counts']['captured_with_text']))
