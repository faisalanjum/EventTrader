"""Replay the actual completed final-key collection without writing evidence."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

A7 = Path(__file__).resolve().parents[1]
unit = A7 / 'unit_2017_final_source_key'
record = json.loads((unit / 'PREPARED_FINAL_KEY_2017.core_final2017_real.json').read_text())
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_prepared_run as PR

SK, K = R.SK, R.K
pkg, run = record['package'], record['run']
run = Path(run)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
before = {str(p): sha(p) for p in run.rglob('*') if p.is_file()}
receipt = json.loads((run / K.RECEIPT_NAME).read_text())
fin_path = run / K.FINALIZATION_NAME
fin = json.loads(fin_path.read_text())
assert fin['phase_complete'] is True and fin['problems'] == fin['retry'] == []
assert fin['receipt_sha256'] == sha(run / K.RECEIPT_NAME)
assert len(receipt['states']) == len(set(receipt['states'])) == 33
assert fin['ledger'] == {'scheduled': 33, 'valid': 33, 'invalid_response': 0,
                         'transport_no_answer': 0, 'unproved': 0, 'missing': 0}
assert not (run / 'retry').exists() and len(list((run / 'raw').iterdir())) == 66
ledger = json.loads((unit / 'evidence/final_key/launch_ledger_2017.json').read_text())
assert len(ledger['launches']) == 33
assert all(r['attempt'] == 1 and r['state'] == 'preserved' for r in ledger['launches'])
assert {Path(p).stem for p in receipt['states']} == {r['runId'] for r in ledger['launches']}

# Full native proof and all 99 copied raw artifacts, not just the closeout count.
runpy.run_path(str(Path(__file__).with_name('check_returned.py')), run_name='__main__')
with R.final_scope(record['review_run'], record['review_package']):
    expected = SK.expected_receipt(str(run), package=pkg)
    expected['states'] = receipt['states']
    assert receipt == expected
    # The raw directory exists and no child is owed. Replaying the finalizer
    # can therefore only read existing files; reject any attempted new write.
    with R._using(R.RT, write_new=R._existing, save_raw=R._no_raw_write):
        replay = SK.finalize(str(run), package=pkg)
    assert replay == fin
    assert json.dumps(replay, indent=1) == fin_path.read_text()
    resume = SK.resume_plan(str(run), package=pkg)
    assert resume['served'] == resume['never_repeat'] == receipt['allowed']
    assert resume['owed'] == resume['retryable'] == resume['problems'] == []
    assert resume['finalized'] is True
    shards, raws, bad = SK.accepted_shards(str(run), package=pkg)
    assert bad == [] and set(shards) == set(raws) == set(receipt['allowed'])
    inventory = list(SK.inventory())
    all_rows = {pid: value for s in shards.values() for pid, value in s['rows'].items()}
    assert len(all_rows) == len(inventory) == 191
    assert set(all_rows) == {pid for pid, _ in inventory}
    outcomes = Counter(v for s in shards.values() for v in s['outcomes'].values())
    facts = sum(len(v['facts']) for v in all_rows.values())
    issues = [{'source_id': sid, **item} for sid, s in shards.items() for item in s['open_issues']]
    open_sources = [sid for sid, s in shards.items() if s['open_issues']]
    native_returned = {r['label']: (unit / 'evidence/final_key' / (r['runId'] + '.returned.txt')).read_text()
                       for r in ledger['launches']}
    assert raws == native_returned
    for sid, text in raws.items():
        assert (run / 'raw' / (sid + '.attempt1.proved.json')).read_text() == text
    # This is a read-only readiness query; neither materialize nor sign.
    gate = SK.signing_checks(shards, str(run), pkg, raws)
    assert issues and not gate['ok']

assert before == {str(p): sha(p) for p in run.rglob('*') if p.is_file()}
a3 = PR._executed(os.path.abspath(K.a3_run_dirs()[0]))
assert a3 == {'run_digest': '460c543b82ec3c69be70b2eebec3df1311263ecf885d3a1215ddc8627ad08034',
              'run_files': 799}
print(json.dumps({'collection_replayed_exactly': True, 'calls': 33, 'retries': 0,
                  'native_schema_valid': 33, 'rows': len(all_rows), 'facts': facts,
                  'row_outcomes': dict(outcomes), 'open_issue_count': len(issues),
                  'open_sources': open_sources, 'signing_gate': gate,
                  'receipt_sha256': sha(run / K.RECEIPT_NAME),
                  'finalization_sha256': sha(fin_path), 'run_files_unchanged': len(before),
                  'a3': a3, 'model_calls': 0, 'key_truth_approved': False}, indent=1, default=str))
