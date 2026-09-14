# -*- coding: utf-8 -*-
"""Boundary payload: preserve the EIGHT completed calls' native bytes.

Codex SEQ 2143 item 4. The copy/proof owner is `preserve_native_2136`, reused
unchanged - it takes the completed run, a pinned native proof and an output
directory, and proves every copy byte-for-byte against its original.

WHAT THIS ADDS, and only this: the copies are ALSO checked against root's own
independently measured identities, so "byte-exact against root" is a comparison
and not a restatement of our own measurement. The counts reported here are the
ones the record actually carries.

THE OWNER'S OWN `scope` STRING STILL SAYS SEVEN. It was written for the seven
round and it is a REPORTED file, so it is not edited here; the stale label is
recorded verbatim beside the true counts rather than quietly repeated.
"""
import collections
import json
import os
import sys
from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2020_codex_check'))
import prepare_g23_partial_2097 as E                                  # noqa: E402

CAND = os.environ['A7_KEY_SUCCESSOR_CANDIDATE']
assert E.G._sha_file(CAND) == os.environ['A7_KEY_SUCCESSOR_CANDIDATE_SHA256']
_s = importlib.util.spec_from_file_location(
    'owner_p2143', CAND, loader=SourceFileLoader('owner_p2143', CAND))
E.X = importlib.util.module_from_spec(_s)
_s.loader.exec_module(E.X)

U = E.A7 / 'unit_2143_source_authority'
OUT = U / os.environ['A7_TAG']
DONE = str(E.A7 / 'unit_2136_source_questions/packet_2136')
PROOF = str(E.A7 / 'unit_2020_codex_check/EIGHT_NATIVE_AND_ROW_AUDIT_2141.json')
PROOF_SHA256 = ('277268c492ee042d0417b1a472361442b2c73124d7f355203bb6ae0ed5e4'
                '5d8d')
KEEP = str(U / 'native_evidence_2143')


def run(_p, _i):
    G = E.G
    sys.path.insert(0, str(E.A7 / 'unit_2136_source_questions'))
    import preserve_native_2136 as PR                                 # noqa: E402
    OUT.mkdir(parents=True)
    rec = PR.preserve(E, E.X, DONE, PROOF, PROOF_SHA256, KEEP)

    proof = G._read(PROOF)
    by_run = {s['run']: s for s in proof['sources']}
    checked = []
    for call in rec['preserved']:
        root = by_run[call['run_id']]
        got = {f['kind']: f['sha256'] for f in call['files']}
        checked.append(collections.OrderedDict([
            ('run_id', call['run_id']), ('agent_id', call['agent_id']),
            ('source_id', root['source_id']),
            ('agent_matches_root', call['agent_id'] == root['agent']),
            ('state_matches_root', got['state'] == root['state_sha256']),
            ('transcript_matches_root',
             got['transcript'] == root['native_sha256'])]))

    out = collections.OrderedDict([
        ('scope', 'durable copies of the EIGHT completed calls native bytes, '
                  'checked against root\'s own identities; no call re-run, no '
                  're-finalization, originals untouched'),
        ('caller_sha256', G._sha_file(__file__)),
        ('preserved_dir', KEEP),
        ('preserved_calls', rec['preserved_calls']),
        ('preserved_files', rec['preserved_files']),
        ('all_copies_match_originals', rec['all_copies_match']),
        ('root_proof', PROOF), ('root_proof_sha256', PROOF_SHA256),
        ('root_sources', len(proof['sources'])),
        ('checked_against_root', checked),
        ('every_copy_matches_root', all(
            c['agent_matches_root'] and c['state_matches_root']
            and c['transcript_matches_root'] for c in checked)),
        ('completed_packet_unchanged', rec['completed_packet_unchanged']),
        ('receipt_sha256', rec['receipt_sha256']),
        ('finalization_sha256', rec['finalization_sha256']),
        ('copy_owner', str(Path(PR.__file__).resolve())),
        ('copy_owner_sha256', G._sha_file(PR.__file__)),
        ('copy_owner_scope_label_is_stale', rec['scope']),
        ('model_calls', rec['model_calls'])])
    assert out['preserved_calls'] == 8, out['preserved_calls']
    assert out['preserved_files'] == 16, out['preserved_files']
    assert out['root_sources'] == 8, out['root_sources']
    assert out['all_copies_match_originals'] and out['every_copy_matches_root']
    assert out['completed_packet_unchanged']
    G._write_new(str(OUT / 'PRESERVED_NATIVE_2143.json'), G._pretty(out) + '\n')
    print('PRESERVED_2143', json.dumps({
        'calls': out['preserved_calls'], 'files': out['preserved_files'],
        'matches_originals': out['all_copies_match_originals'],
        'matches_root': out['every_copy_matches_root'],
        'packet_unchanged': out['completed_packet_unchanged'],
        'sha': G._sha_file(str(OUT / 'PRESERVED_NATIVE_2143.json'))}), flush=True)
    return out


if __name__ == '__main__':
    E.with_prepared_inputs(run)
