"""Real saved-answer binding and a complete TEST source lock, with no AI calls."""
import collections
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sys

R = Path('/home/faisal/EventMarketDB-driver-recovery')
S = Path('/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad')
H = S / 'bench_1306/.claude/plans/Drivers/experiments/harness_g1v3'
sys.path[:0] = [str(H), str(R)]
import audit_worker_access as AUD
import build_inventory_review as BIR
import g1_fake_state as FAKE
import raw_transport as RT

ATT = Path(os.environ['A7_ATTEMPT_DIR'])
package = ATT / 'package'
os.environ['A7_REVIEW_OUT'] = str(package)
assert not package.exists()
BIR.build()
manifest_text = (package / 'package.manifest.json').read_text()
manifest = json.loads(manifest_text)
native = FAKE.declared_input_record()
assert native, 'the independently approved native fixture must exist'
assert BIR._package_pin_problems(manifest) == []

saved = R / 'a7_recovery/unit_1947/logs/real_source_review'
sid = '0000006201-26-000031'
raw_name = sid + '.attempt1.complete.raw.json'
raw = saved / 'replies' / raw_name
raw_sha = hashlib.sha256(raw.read_bytes()).hexdigest()
assert raw_sha == '625140d6eb637e029b885f356f3cb68a12ffb8c7ce1e8fded272e36b2471030b'
parent = '5ae9b86b-f0f6-4449-beee-9cac7cfa7200'
state = Path('/home/faisal/.claude/projects/-home-faisal-EventMarketDB') / parent / 'workflows/wf_b5890dc2-781.json'
attempt = dict(task='event', ordinal=[e['source_id'] for e in manifest['events']].index(sid),
               attempt=1, source_id=sid, state_path=str(state),
               agent_id='a9dce3dc893074b40', raw_name=raw_name)
seen = {key: set() for key in ('run', 'agent', 'transcript', 'raw', 'response')}
problems = BIR._attempt_evidence(attempt, 'saved real answer', BIR.prompt_text(sid),
                                str(saved / 'replies'), parent, seen,
                                manifest.get('expected_input'))
assert not problems, problems
receipt = dict(parent_session_id=parent, transport=BIR.REVIEW_TRANSPORT,
               max_output_tokens=manifest['reviewers'][BIR.BLM.OUTPUT_TOKENS_VAR],
               subscription_proof=str(saved / 'subscription.json'),
               base_commit=manifest['base_commit'], base_tree=manifest['base_tree'],
               package_manifest_sha256=BIR._sha_text(manifest_text), attempts=[attempt])
receipt_path = ATT / 'REAL_PARTIAL_RECEIPT.json'
with receipt_path.open('x') as stream:
    json.dump(receipt, stream, indent=2)
receipt_problems = BIR._receipt_problems(receipt, manifest, manifest_text,
                                        str(saved / 'replies'), False)
missing = [p for p in receipt_problems if p.endswith('has no attempt')]
assert len(missing) == len(manifest['events']) - 1 == 35, receipt_problems
assert len(receipt_problems) == len(missing) + 1, receipt_problems
artifacts, materialize_problems, _ = BIR.materialize(str(saved / 'replies'), str(receipt_path))
assert not artifacts and materialize_problems
lock, lock_problems = BIR.derive_lock(str(saved / 'replies'), str(receipt_path), str(ATT / 'absent_lock'))
assert lock is None and lock_problems
retry, why = BIR._retry_lawful(str(raw), 'event')
assert not retry, 'a valid completed answer must not be relaunched'
real = dict(label='Partial compatibility receipt derived now; not the original call receipt',
            raw_sha256=raw_sha, approved_input_binding_problems=problems,
            completed_answers=1, missing_answers=len(missing), retry_allowed=retry,
            retry_reason=why, open_issues=len(RT.parse_reply(raw.read_text())['open_issues']),
            receipt_problems=receipt_problems, materialize_problems=materialize_problems,
            lock_problems=lock_problems, package_sha256=BIR._sha_text(manifest_text))
with (ATT / 'REAL_SOURCE_PROOF.json').open('x') as stream:
    json.dump(real, stream, indent=2)
print('Saved real answer: exact attempt accepted; 35 missing; materialize/lock refused; no retry.', flush=True)

# Reuse the complete existing source fixture. Only its runtime transcript
# fixture gains the fixed native record; no candidate chooses that record.
original = FAKE._transcript
os.environ['A7_TEST_REPLIES'] = str(R / 'a7_recovery/unit_1893/logs/attempt_reh3/TEST_replies')
def native_transcript(tdir, agent_id, session_id, prompt, answer, declared=None):
    return original(tdir, agent_id, session_id, prompt, answer, native)
FAKE._transcript = native_transcript
try:
    try:
        runpy.run_path(str(R / 'a7_recovery/unit_1925/ledger/group_source_v1.py'), run_name='__main__')
    except SystemExit as exc:
        assert exc.code == 0, 'complete TEST source fixture failed: %s' % exc.code
finally:
    FAKE._transcript = original

# Remove the handoff on a separate packet and receipt, then restore the
# original. The complete saved TEST run is never edited or rebuilt.
mutated = ATT / 'package_missing_handoff'
shutil.copytree(package, mutated)
bad_manifest = copy.deepcopy(manifest)
bad_manifest.pop('expected_input', None)
bad_manifest.pop('expected_input_source', None)
bad_text = json.dumps(bad_manifest, indent=1)
(mutated / 'package.manifest.json').write_text(bad_text)
complete_receipt = json.loads((ATT / 'receipt.json').read_text())
bad_receipt = copy.deepcopy(complete_receipt)
bad_receipt['package_manifest_sha256'] = BIR._sha_text(bad_text)
bad_receipt_path = ATT / 'receipt_missing_handoff.json'
with bad_receipt_path.open('x') as stream:
    json.dump(bad_receipt, stream, indent=2)
os.environ['A7_REVIEW_OUT'] = str(mutated)
_, missing_problems, _ = BIR.materialize(str(ATT / 'replies'), str(bad_receipt_path))
assert sum('nothing else may appear between them' in p for p in missing_problems) == len(manifest['events']), missing_problems
os.environ['A7_REVIEW_OUT'] = str(package)
restored, restored_problems = BIR.derive_lock(str(ATT / 'replies'), str(ATT / 'receipt.json'), str(ATT / 'locked'))
assert restored and not restored_problems, restored_problems
with (ATT / 'SOURCE_HANDOFF_MUTATION.json').open('x') as stream:
    json.dump(dict(removed_handoff_problems=missing_problems,
                   restored_lock_sha256=BIR._sha_text(restored)), stream, indent=2)
assert hashlib.sha256(raw.read_bytes()).hexdigest() == raw_sha
print('Complete TEST source: native lock proved; removed handoff refused; original restored.', flush=True)
