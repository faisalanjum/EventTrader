# -*- coding: utf-8 -*-
"""Preserve the seven completed calls' native bytes as durable evidence.

Codex SEQ 2136. The official workflow state and its agent transcript live under
the session's project directory, which is not durable recovery evidence. This
copies them BESIDE this packet and proves every copy byte-for-byte against the
original, using the completed packet's own receipt for the state list and
root's native identity proof for the run/agent identities.

It re-runs nothing and re-finalizes nothing: the completed packet is opened
read-only and its hashes are re-measured, not rewritten.
"""
import collections
import json
import os
import shutil


def preserve(E, X, done_run, native_proof_path, native_proof_sha256, out_dir):
    """Copy and prove. -> the preservation record. No call, no re-finalize."""
    F, K, G = E.F, E.K, E.G
    got = G._sha_file(native_proof_path)
    if got != native_proof_sha256:
        raise ValueError('the native identity proof is %s, not the pinned %s'
                         % (got, native_proof_sha256))
    proof = G._read(native_proof_path)
    receipt = K._load(os.path.join(done_run, K.RECEIPT_NAME))
    before = collections.OrderedDict(
        (n, G._sha_file(os.path.join(done_run, n)))
        for n in sorted(os.listdir(done_run))
        if os.path.isfile(os.path.join(done_run, n)))

    os.makedirs(out_dir, exist_ok=True)
    copied = []
    for state in receipt['states']:
        doc = K._load(state)
        sdir, _sid = F.HR.AUD._official_location(state)
        row = [r for r in doc.get('workflowProgress') or []
               if r.get('type') == 'workflow_agent'][0]
        transcript = os.path.join(sdir or '', 'subagents', 'workflows',
                                  doc['runId'], 'agent-%s.jsonl' % row['agentId'])
        pair = []
        for src, kind in ((state, 'state'), (transcript, 'transcript')):
            dst = os.path.join(out_dir, '%s.%s%s' % (
                doc['runId'], kind, os.path.splitext(src)[1]))
            if os.path.exists(dst):
                raise ValueError('a preserved copy already exists: %s' % dst)
            shutil.copyfile(src, dst)
            osha, dsha = G._sha_file(src), G._sha_file(dst)
            if osha != dsha:
                raise ValueError('the copy of %s does not match its original'
                                 % src)
            pair.append(collections.OrderedDict([
                ('kind', kind), ('original_path', src), ('copy_path', dst),
                ('sha256', osha), ('copy_matches_original', True),
                ('bytes', os.path.getsize(src))]))
        copied.append(collections.OrderedDict([
            ('label', row['label']), ('run_id', doc['runId']),
            ('agent_id', row['agentId']), ('status', doc.get('status')),
            ('files', pair)]))

    after = collections.OrderedDict(
        (n, G._sha_file(os.path.join(done_run, n)))
        for n in sorted(os.listdir(done_run))
        if os.path.isfile(os.path.join(done_run, n)))
    if after != before:
        raise ValueError('the completed packet moved during preservation')
    return collections.OrderedDict([
        ('scope', 'durable copies of the seven completed calls native bytes; '
                  'no call re-run, no re-finalization, originals untouched'),
        ('completed_run', done_run),
        ('receipt_sha256', G._sha_file(os.path.join(done_run, K.RECEIPT_NAME))),
        ('finalization_sha256',
         G._sha_file(os.path.join(done_run, K.FINALIZATION_NAME))),
        ('native_identity_proof', native_proof_path),
        ('native_identity_proof_sha256', native_proof_sha256),
        ('proof_scope', proof.get('scope')),
        ('preserved', copied),
        ('preserved_calls', len(copied)),
        ('preserved_files', sum(len(c['files']) for c in copied)),
        ('all_copies_match', all(f['copy_matches_original']
                                 for c in copied for f in c['files'])),
        ('completed_packet_unchanged', True),
        ('model_calls', 0)])
