# -*- coding: utf-8 -*-
"""Independent review of the proposed path binding. SEQ 2156. Read-only.

Measures, from the artifacts and from the UNCHANGED owner source, exactly what
the proposed correction would and would not change: which audit check consults
the expected script path, what the existing same-file allowance actually
requires, what the state itself already proves, and what the audit still needs
that lives only in the live session tree.

Nothing is imported, run, edited or ingested. Every line number is FOUND by
searching for the source line, never typed.
"""
import datetime
import hashlib
import io
import json
import os
import sys

sys.dont_write_bytecode = True
sha_b = lambda b: hashlib.sha256(b).hexdigest()
sha_f = lambda p: sha_b(io.open(p, 'rb').read())
AUTH, IDENT, EVIDENCE, OUT = sys.argv[1:5]
auth = json.load(io.open(AUTH, encoding='utf-8'))
ident = json.load(io.open(IDENT, encoding='utf-8'))
ev = json.load(io.open(EVIDENCE, encoding='utf-8'))
run_dir = auth['run_dir']
seg = auth['segment']
receipt = json.load(io.open(os.path.join(run_dir, 'receipt.seg%02d.json' % seg),
                            encoding='utf-8'))
invocation = json.load(io.open(os.path.join(run_dir, 'invocation.seg%02d.json' % seg),
                               encoding='utf-8'))
root = json.load(io.open(os.path.join(run_dir, 'root.json'), encoding='utf-8'))
state_path = ident['state_path']
state = json.load(io.open(state_path, encoding='utf-8'))
staged = auth['staged_script_path']


def find(path, needle):
    """(line number, whether it is unique) for a source line, by search."""
    hits = [n for n, l in enumerate(io.open(path, encoding='utf-8'), 1) if needle in l]
    return {'line': hits[0] if hits else None, 'occurrences': len(hits)}


def owner_file(name, pinned_prefix):
    """The file whose hash IS the one this run's root pinned for that owner."""
    here = os.path.dirname(os.path.abspath(AUTH))
    a7 = os.path.abspath(os.path.join(here, '..'))
    for dirpath, _dirs, files in os.walk(a7):
        if name in files:
            p = os.path.join(dirpath, name)
            if sha_f(p).startswith(pinned_prefix):
                return p
    return None


AUD = owner_file('audit_worker_access.py', root['owners']['audit_worker_access'])
BLD = owner_file('a7_g1_build.py', root['owners']['a7_g1_build'])
ts = {r['kind']: r['timestamp'] for r in ev['records'] if r['order'] <= 9}
order = [(r['timestamp'], r['kind'], r['tool_use_id']) for r in ev['records'][:9]]


def utc(p):
    return datetime.datetime.utcfromtimestamp(os.path.getmtime(p)).strftime(
        '%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def gap(a, b):
    f = '%Y-%m-%dT%H:%M:%S.%fZ'
    return round((datetime.datetime.strptime(b, f)
                  - datetime.datetime.strptime(a, f)).total_seconds(), 3)


launches = [r for r in ev['records'] if r['kind'] == 'WORKFLOW']
notice = min(r['timestamp'] for r in ev['records'] if r['kind'] == 'INTERRUPT_NOTICE')
hashed_at = [r['timestamp'] for r in ev['records'] if r['kind'] == 'RESULT'
             and r['detail'].get('reports_staged_script_sha256')][0]

review = {
    'kind': 'independent read-only review of the proposed one-state path binding',
    'model_calls': 0, 'jobs_run': 0, 'files_edited': 0, 'ingest_run': False,
    'audit_owner_file': AUD, 'audit_owner_sha256': sha_f(AUD),
    'audit_owner_is_the_hash_this_run_pinned':
        sha_f(AUD).startswith(root['owners']['audit_worker_access']),
    'g1_owner_file': BLD, 'g1_owner_sha256': sha_f(BLD),
    # A same-named copy sits beside the pinned audit owner and is NOT the
    # pinned G1 owner; line numbers read there would be wrong.
    'g1_owner_copy_beside_the_audit_owner': os.path.join(
        os.path.dirname(AUD), os.path.basename(BLD)),
    'g1_owner_copy_beside_the_audit_owner_sha256': sha_f(os.path.join(
        os.path.dirname(AUD), os.path.basename(BLD))),
    'that_copy_is_the_pinned_owner': sha_f(os.path.join(
        os.path.dirname(AUD), os.path.basename(BLD))) == sha_f(BLD),

    # ---- WHAT THE EXPECTED PATH IS USED FOR, measured in the owner source ----
    'expected_path_is_consulted_at': find(AUD, 'expect["script_path"]'),
    'expected_path_is_never_opened_or_hashed': find(AUD, 'open(expect')['line'] is None,
    'the_same_file_allowance': find(AUD, 'def _same_published_script'),
    'the_same_file_allowance_requires_samefile': find(AUD, 'os.path.samefile')['line'],
    'official_location_rule': find(AUD, 'def _official_location'),
    'child_transcript_dir_rule': find(AUD, '"subagents", "workflows", rid'),
    'expect_is_built_inside_the_owner_at': find(BLD, '("script_path", receipt["script_path"])'),
    'owner_entry_takes_no_expect': find(BLD, 'def audit_official_state'),

    # ---- WHAT THE COMPLETED STATE ALREADY PROVES, on its own --------------
    'state_path': state_path,
    # the canonical shape the audit demands: <projects>/<project>/<session>/
    # workflows/<runId>.json. Reported as the parts, not as my own verdict.
    'state_path_parts_under_projects_root': os.path.realpath(state_path).split(os.sep)[-4:],
    'state_file_is_named_for_its_run': os.path.basename(state_path) ==
        ident['accepted_run_id'] + '.json',
    'state_status': state.get('status'),
    'state_args_equal_the_frozen_invocation':
        json.dumps(state.get('args'), sort_keys=True)
        == json.dumps(invocation['args'], sort_keys=True),
    'state_persisted_script_sha256': sha_b(state['script'].encode('utf-8')),
    'receipt_script_sha256': receipt['script_sha256'],
    'state_persisted_script_is_the_published_one':
        sha_b(state['script'].encode('utf-8')) == receipt['script_sha256'],
    'receipt_script_path': receipt['script_path'],
    'state_script_path': state.get('scriptPath'),
    'the_only_disagreement_is_the_path_string':
        receipt['script_path'] != state.get('scriptPath'),

    # ---- THE PRE-CALL CHAIN, with its gaps stated -------------------------
    'pre_call_order': order,
    'staged_file_mtime_utc': utc(staged),
    'staged_file_sha256_now': sha_f(staged),
    'staged_file_is_still_the_frozen_bytes':
        sha_f(staged) == auth['frozen_script_sha256'],
    'seconds_from_hashing_to_first_launch': gap(hashed_at, launches[0]['timestamp']),
    'seconds_from_hashing_to_full_launch': gap(hashed_at, launches[1]['timestamp']),
    'seconds_from_full_launch_to_interrupt_notice':
        gap(launches[1]['timestamp'], notice),
    'full_launch_preceded_the_interrupt': gap(launches[1]['timestamp'], notice) > 0,
    'launch_record_write_time_is_later_than_the_launch':
        gap(launches[1]['timestamp'], ident['launched_utc'].replace('Z', '.000Z')) > 0,

    # ---- WHAT IS NOT PROVED ----------------------------------------------
    'not_proved': [
        'the staged file INODE at call time - only its bytes are evidenced; '
        'mtime is not evidence and nothing captured stat before the call',
        'the file content at the moment of the call from the transcript alone: '
        'the Workflow call carried only scriptPath and args, never the script',
        'that the live state and child transcripts will outlive the session '
        'tree they sit in; the audit refuses a state anywhere else',
    ],
}
io.open(os.path.join(OUT, 'INDEPENDENT_REVIEW_2156.json'), 'w',
        encoding='utf-8').write(json.dumps(review, indent=1, sort_keys=True) + '\n')
print(json.dumps(review, indent=1, sort_keys=True))
