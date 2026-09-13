"""Prove the one saved real signer reply, without harvesting or calling a model."""
import json
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_1955/lock_owners'))
import signer_proof as SP
sys.path.insert(0, str(A7 / 'unit_1997/owner'))
import a4_source_key as SK

candidate = Path(os.environ['A7_CANDIDATE_DIR'])
sig = str(candidate / 'signer')
collection = A7 / 'unit_2083_signer_collection'
record = json.loads((collection / 'LAUNCH_RECORD_2083.json').read_text())
ledger = json.loads((collection / 'evidence/signer/launch_ledger_2083.json').read_text())
manifest = json.loads((candidate / 'signer/signer.manifest.json').read_text())
assert len(ledger['launches']) == record['authorized_calls'] == 1
row = ledger['launches'][0]
assert row['attempt'] == record['attempt'] == 1
assert record['authority_sha256'] == SP.shaf('/home/faisal/.core827-orchestrator/archive_CODEX_2083.md')
for name, path in (
        ('candidate_result', candidate.parent / 'RESULT.json'),
        ('ordinary', candidate.parent / 'ordinary_bound.json'),
        ('key_identity', candidate / 'key_identity.json'),
        ('manifest', candidate / 'signer/signer.manifest.json'),
        ('prompt', candidate / 'signer/signer_prompt.txt'),
        ('script', candidate / 'signer/final_sign.attempt1.js')):
    assert SP.shaf(str(path)) == record[name + '_sha256'], name
assert SK.K is SP.K and not SK.role_problems(), SK.role_problems()
assert SK.key_transport() == manifest['transport']
with SK._key_role_binding():
    proof, problems = SP.prove(sig, manifest, 1, row['runId'],
                                os.environ['A7_SIGNER_SESSION'], {})
assert not problems, problems
assert proof['outcome'] == 'signed', proof['outcome']
assert proof['_reply']['signed'] is True and proof['_reply']['blocked'] == []
for field, suffix in (('state', 'state.json'), ('transcript', 'transcript.jsonl')):
    saved = collection / 'evidence/signer' / (row['runId'] + '.' + suffix)
    assert saved.read_bytes() == Path(proof[field + '_path']).read_bytes(), field
    assert SP.shaf(str(saved)) == proof[field + '_sha256'], field
raw = collection / 'evidence/signer' / (row['runId'] + '.returned.txt')
assert raw.read_text() == proof['_text']
assert SP.shaf(str(raw)) == proof['raw_sha256'] == row['returned_text_sha256']
assert proof['script_sha256'] == record['script_sha256'] == row['state_script_sha256']
assert proof['prompt_sha256'] == record['prompt_sha256']
assert manifest['budget']['before'] == record['ledger_before'] == 667
assert manifest['shards'] and len(manifest['shards']) == 33
assert not list((candidate / 'signer').glob('*.evidence.json'))
assert not (candidate / 'a4_final_key_lock.json').exists()
print(json.dumps({'proof': {k: v for k, v in proof.items() if k != '_text'},
                  'ledger_after': 668, 'model_calls': 0, 'harvest': False,
                  'lock': False, 'durable_native_copies_identical': True}, indent=1))
