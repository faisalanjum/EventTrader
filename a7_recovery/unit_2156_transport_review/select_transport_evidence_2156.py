# -*- coding: utf-8 -*-
"""Preserve and independently verify the PRE-CALL transport evidence. SEQ 2156.

Selects, from the live parent transcript, only the records that prove the
staged script existed and was hashed BEFORE either Workflow call, plus both
calls and their returned run ids. Each selected record is written out as its
own file holding the RAW line bytes, unmodified; nothing is rewritten and no
record content is printed. Every path comes from the 2154 authorization
record, so nothing about this round's identities is typed in here.

No AI call, no job, no ingest, no edit to any existing file.
"""
import hashlib
import io
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True
sha = lambda b: hashlib.sha256(b).hexdigest()
AUTH, IDENT, TRANSCRIPT, OUT = sys.argv[1:5]
auth = json.load(io.open(AUTH, encoding='utf-8'))
ident = json.load(io.open(IDENT, encoding='utf-8'))
staged = auth['staged_script_path']
marker = os.path.basename(os.path.dirname(staged))
auth_name = os.path.basename(AUTH)
invocation = json.load(io.open(os.path.join(
    auth['run_dir'], 'invocation.seg%02d.json' % auth['segment']), encoding='utf-8'))
notice = 'CODEX MAILBOX CHANGED SEQ %d' % (int(auth['authority'].split()[-1]) + 1)

selected = []          # (timestamp, kind, uuid, tool_id, raw, detail)


def canon(o):
    return sha(json.dumps(o, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def items(obj):
    msg = obj.get('message') or {}
    c = msg.get('content')
    return c if isinstance(c, list) else []


# ---- pass 1: the tool CALLS, found by what they name, not by a known id -----
with io.open(TRANSCRIPT, 'rb') as fh:
    for raw in fh:
        if marker.encode() not in raw and auth_name.encode() not in raw:
            continue
        obj = json.loads(raw.decode('utf-8'))
        for it in items(obj):
            if not isinstance(it, dict) or it.get('type') != 'tool_use':
                continue
            inp = it.get('input') or {}
            name, detail = it.get('name'), None
            if name == 'Workflow' and inp.get('scriptPath') == staged:
                a = inp.get('args')
                dec = json.loads(a) if isinstance(a, str) else a
                detail = {
                    'input_keys': sorted(inp.keys()),
                    'scriptPath': inp.get('scriptPath'),
                    'scriptPath_is_the_staged_copy': inp.get('scriptPath') == staged,
                    'args_field_type': type(a).__name__,
                    'args_rows_decoded': len(dec) if isinstance(dec, list) else None,
                    'args_canonical_sha256': canon(dec),
                    'args_equal_frozen_invocation': dec == invocation['args'],
                    'frozen_invocation_args_sha256': canon(invocation['args']),
                }
            elif name == 'Bash' and marker in (inp.get('command') or ''):
                cmd = inp.get('command') or ''
                detail = {
                    'command_bytes': len(cmd.encode('utf-8')),
                    'command_sha256': sha(cmd.encode('utf-8')),
                    'writes_the_authorization_record': auth_name in cmd,
                    'copies_the_frozen_script': auth['frozen_script_path'] in cmd,
                }
            if detail is not None:
                selected.append([obj.get('timestamp'), name.upper(), obj.get('uuid'),
                                 it.get('id'), raw, detail])

ids = {r[3] for r in selected}

# ---- pass 2: the RESULTS of exactly those calls, and the interrupt notice ---
with io.open(TRANSCRIPT, 'rb') as fh:
    for raw in fh:
        hit = next((i for i in ids if i.encode() in raw), None)
        if hit is None and notice.encode() not in raw:
            continue
        obj = json.loads(raw.decode('utf-8'))
        if notice.encode() in raw and hit is None:
            selected.append([obj.get('timestamp'), 'INTERRUPT_NOTICE', obj.get('uuid'),
                             None, raw, {'names_the_interrupt': notice}])
            continue
        for it in items(obj):
            if not isinstance(it, dict) or it.get('type') != 'tool_result':
                continue
            if it.get('tool_use_id') not in ids:
                continue
            text = json.dumps(it.get('content'))
            selected.append([obj.get('timestamp'), 'RESULT', obj.get('uuid'),
                             it.get('tool_use_id'), raw, {
                                 'reports_frozen_script_sha256':
                                     auth['frozen_script_sha256'] in text,
                                 'reports_staged_script_sha256':
                                     auth['staged_script_sha256'] in text,
                                 'reports_authorization_sha256':
                                     ident['authorization_sha256'] in text,
                                 'names_accepted_run_id':
                                     ident['accepted_run_id'] in text,
                                 'names_refused_run_id':
                                     ident['refused_first_invocation']['run_id'] in text,
                             }])

selected.sort(key=lambda r: (r[0] or '', r[1]))

# ---- preserve: raw line bytes, one file per record, nothing rewritten -------
recdir = os.path.join(OUT, 'preserved/transcript_records')
manifest = []
for n, (ts, kind, uid, tid, raw, detail) in enumerate(selected, 1):
    name = '%02d_%s_%s.jsonl' % (n, kind.lower(), (uid or 'no-uuid'))
    with io.open(os.path.join(recdir, name), 'wb') as fh:
        fh.write(raw)
    manifest.append({'order': n, 'kind': kind, 'timestamp': ts, 'uuid': uid,
                     'tool_use_id': tid, 'raw_line_bytes': len(raw),
                     'raw_line_sha256': sha(raw), 'preserved_as': name,
                     'detail': detail})

# ---- preserve: the failed state and the staged inputs, byte-identical -------
copies = []
refused = ident['refused_first_invocation']
failed_state = os.path.join(os.path.dirname(ident['state_path']),
                            refused['run_id'] + '.json')
for src in (failed_state, staged,
            os.path.join(os.path.dirname(staged), 'args.json')):
    dst = os.path.join(OUT, 'preserved', os.path.basename(src))
    shutil.copy2(src, dst)
    a, b = sha(io.open(src, 'rb').read()), sha(io.open(dst, 'rb').read())
    assert a == b, src
    copies.append({'source': src, 'preserved_as': os.path.basename(dst),
                   'bytes': os.path.getsize(dst), 'sha256': a})

order = [r['kind'] for r in manifest]
launches = [r for r in manifest if r['kind'] == 'WORKFLOW']
record = {
    'kind': 'PRE-CALL transport evidence, preserved and independently verified',
    'model_calls': 0, 'edits_to_existing_files': 0,
    'transcript': TRANSCRIPT, 'transcript_bytes': os.path.getsize(TRANSCRIPT),
    'selection_rule': ('records naming the staged directory %r or %s, plus the results '
                       'of exactly those tool ids, plus the interrupt notice' %
                       (marker, auth_name)),
    'authorization_record': AUTH, 'authorization_sha256': ident['authorization_sha256'],
    'staged_script_path': staged,
    'frozen_script_path': auth['frozen_script_path'],
    'failed_run_id': refused['run_id'],
    'failed_run_agent_transcript_dir': refused['transcript_dir'],
    'failed_run_agent_transcript_dir_exists': os.path.isdir(refused['transcript_dir']),
    'completed_run_agent_transcript_dir_exists': os.path.isdir(ident['transcript_dir']),
    'record_order': order,
    'launch_count': len(launches),
    'every_launch_used_the_staged_copy': all(
        r['detail']['scriptPath_is_the_staged_copy'] for r in launches),
    'args_field_types': sorted({r['detail']['args_field_type'] for r in launches}),
    'args_rows_per_launch': [r['detail']['args_rows_decoded'] for r in launches],
    'full_launch_args_equal_frozen_invocation': [
        r['detail']['args_equal_frozen_invocation'] for r in launches],
    'records': manifest,
    'copies': copies,
}
io.open(os.path.join(OUT, 'TRANSPORT_EVIDENCE_2156.json'), 'w', encoding='utf-8').write(
    json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps({k: v for k, v in record.items() if k not in ('records', 'copies')},
                 indent=1, sort_keys=True))
print('records preserved:', len(manifest), 'copies:', len(copies))
