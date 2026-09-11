"""Read-only preview of preserved key replies; no admission or finalization."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys

A7 = Path(__file__).resolve().parents[1]
unit = A7 / 'unit_2017_final_source_key'
record = json.loads((unit / 'PREPARED_FINAL_KEY_2017.core_final2017_real.json').read_text())
ledger = json.loads((unit / 'evidence/final_key/launch_ledger_2017.json').read_text())
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R

SK, K = R.SK, R.K
pkg, run = record['package'], record['run']
receipt = json.loads((Path(run) / K.RECEIPT_NAME).read_text())
session = receipt['transport']['parent_session_id']
native = Path('/home/faisal/.claude/projects/-home-faisal-EventMarketDB') / session
selected = [r for r in ledger['launches'] if r['state'] == 'preserved' and r['attempt'] == 1]
assert len({r['runId'] for r in selected}) == len({r['label'] for r in selected}) == len(selected)
states, returned = [], {}
pins = {r['label']: r['script_sha256'] for r in record['invocations']}
for row in selected:
    path = native / 'workflows' / (row['runId'] + '.json')
    raw = path.read_bytes()
    doc = json.loads(raw)
    assert hashlib.sha256(doc['script'].encode()).hexdigest() == pins[row['label']]
    agents = [r for r in doc['workflowProgress'] if r['type'] == 'workflow_agent']
    assert len(agents) == 1
    transcript = native / 'subagents/workflows' / row['runId'] / ('agent-%s.jsonl' % agents[0]['agentId'])
    text = doc['result']['text']
    for suffix, data in [('state.json', raw), ('transcript.jsonl', transcript.read_bytes()),
                         ('returned.txt', text.encode())]:
        assert (unit / 'evidence/final_key' / (row['runId'] + '.' + suffix)).read_bytes() == data
    states.append(str(path))
    returned[row['label']] = text

with R.final_scope(record['review_run'], record['review_package']):
    # States are the only mutable receipt field. This temporary in-memory view
    # lets the real native-proof owner inspect results before Core admits them.
    temporary = SK.expected_receipt(run, package=pkg)
    assert {k: v for k, v in receipt.items() if k != 'states'} == {
        k: v for k, v in temporary.items() if k != 'states'}
    temporary['states'] = states
    proved, problems = SK.run_evidence(run, temporary, package=pkg)
    tasks = {t['source_id']: t for t in SK.tasks()}
    results = []
    for row in selected:
        label = row['label']
        status, why, text = proved[label]
        assert status == 'proved', (label, status, why)
        assert text == returned[label]
        obj, bad = SK.read_shard(text, tasks[label])
        results.append({'source_id': label, 'runId': row['runId'],
                        'native_status': status, 'schema_problems': bad,
                        'open_issues': obj.get('open_issues') if obj is not None else None,
                        'returned_sha256': hashlib.sha256(text.encode()).hexdigest(),
                        'duration_ms': row.get('durationMs')})
    assert problems == [], problems
print(json.dumps({'preview_only': True, 'formal_admission_or_finalization': False,
                  'preserved_primaries': len(selected), 'results': results,
                  'native_outcomes': dict(Counter(v[0] for v in proved.values())),
                  'model_calls': 0, 'key_truth_approved': False}, indent=1))
