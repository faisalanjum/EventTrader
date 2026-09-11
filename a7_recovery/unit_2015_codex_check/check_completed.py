"""Read-only native closeout and preservation proof; never calls a model."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

A7 = Path(__file__).resolve().parents[1]
unit = A7 / 'unit_2015_real_reviews'
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_prepared_run as PR

record = json.loads((unit / 'PREPARED_REVIEW_2015.core_prep2015_real.json').read_text())
run, pkg = record['run'], record['package']
old, old_stage = R.old_readings()
merged, stages = R.merged_readings(run, pkg)
assert len(merged) == len(old) == 66
assert dict(Counter(v[0] for v in old.values())) == {'valid': 62, 'invalid_response': 4}
assert dict(Counter(v[0] for v in merged.values())) == {'valid': 66}
assert all(merged[k] == v for k, v in old.items() if v[0] == 'valid')
owed = [k for k, v in old.items() if v[0] != 'valid']
assert owed == [r['label'] for r in record['invocations']]
receipt = R.K._load(os.path.join(run, R.K.RECEIPT_NAME))
fin = R.K._load(os.path.join(run, R.K.FINALIZATION_NAME))
assert receipt['allowed'] == owed and len(receipt['states']) == 4
assert len(set(receipt['states'])) == 4
assert fin['primary_complete'] is True and fin['problems'] == []
assert fin['retry'] == [] and not (Path(run) / 'retry').exists()
assert fin['ledger'] == {'scheduled': 4, 'valid': 4, 'invalid_response': 0,
                         'transport_no_answer': 0, 'unproved': 0, 'missing': 0}
assert fin['budget']['ledger_before'] == 495 and fin['budget']['ledger_after'] == 499

ledger = json.loads((unit / 'evidence/review/launch_ledger_2015.json').read_text())
assert [row['label'] for row in ledger['launches']] == owed
scripts = {row['label']: row['script_sha256'] for row in record['invocations']}
states = {Path(p).stem: Path(p) for p in receipt['states']}
preserved = []
for row in ledger['launches']:
    label, run_id = row['label'], row['runId']
    source = states[run_id]
    doc = json.loads(source.read_text())
    assert hashlib.sha256(doc['script'].encode()).hexdigest() == scripts[label]
    rows = [r for r in doc['workflowProgress'] if r['type'] == 'workflow_agent']
    assert len(rows) == 1 and rows[0]['label'] == label and rows[0]['state'] == 'done'
    assert rows[0]['model'] == 'claude-sonnet-5'
    transcript = source.parent.parent / 'subagents/workflows' / run_id / ('agent-%s.jsonl' % rows[0]['agentId'])
    for name, raw in [('state.json', source.read_bytes()),
                      ('transcript.jsonl', transcript.read_bytes()),
                      ('returned.txt', doc['result']['text'].encode())]:
        saved = unit / 'evidence/review' / (run_id + '.' + name)
        assert saved.read_bytes() == raw
        preserved.append({'path': str(saved), 'sha256': hashlib.sha256(raw).hexdigest()})
    assert doc['result']['text'] == merged[label][2]

with R.final_scope(run, pkg):
    manifest = R.SK.manifest()
    assert len(manifest['hard_review']['stages']) == 2
    budget = manifest['budget'] if 'budget' in manifest else R.SK.budget()
    assert budget['before'] == 499
a3 = PR._executed(os.path.abspath(R.K.a3_run_dirs()[0]))
assert a3 == {'run_digest': '460c543b82ec3c69be70b2eebec3df1311263ecf885d3a1215ddc8627ad08034', 'run_files': 799}
print(json.dumps({'verified': 'native review completion, not approved key truth',
                  'preserved_valid': 62, 'new_valid': 4, 'combined_valid': 66,
                  'new_calls': 4, 'retry_calls': 0, 'ledger_after': 499,
                  'receipt_sha256': R.INV.sha_file(os.path.join(run, R.K.RECEIPT_NAME)),
                  'finalization_sha256': R.INV.sha_file(os.path.join(run, R.K.FINALIZATION_NAME)),
                  'preserved_copies': preserved, 'a3': a3,
                  'next_key_counts': manifest['counts'], 'next_key_budget': budget,
                  'model_calls_by_this_check': 0}, indent=1))
