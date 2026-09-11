"""Independent read-only audit of every primary source-key review.

Recompute runtime/receipt/raw proof and the full parser result. Preserve full
errors, rather than trusting Core's counts or repairing malformed answers.
"""
import collections
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_2002/owner'))
import a4_source_closure as CL

prepared = json.loads((UNIT.parent / 'unit_2004/PREPARED_REVIEW.json').read_text())
run, package = prepared['run'], prepared['package']
got, problems = CL.readings(run, package)
ledger_path = UNIT.parent / 'unit_2004/evidence/review/launch_ledger_2004.json'
ledger = json.loads(ledger_path.read_text())
launches = {r['label']: r for r in ledger['launches']}
assert len(launches) == len(ledger['launches']) == len(got)
by = CL.by_label()
rows = []
for label, (state, why, text) in got.items():
    launch = launches[label]
    raw_path = UNIT.parent / 'unit_2004/evidence/review' / (launch['runId'] + '.returned.txt')
    raw = raw_path.read_text()
    assert CL.K._sha(raw) == launch['returned_text_sha256']
    assert launch['state'] == 'preserved'
    task, blind = by[label]
    parsed, bad = CL.read_reply(raw, task)
    script = os.path.join(run, 'scripts', label.replace('/', '_') + '.attempt1.js')
    assert CL.INV.sha_file(script) == launch['script_sha256']
    assert CL.K._sha(CL.render_launcher(task, blind, 1)) == launch['script_sha256']
    assert (not bad) == (state == 'valid')
    if state == 'valid':
        assert text == raw
    rows.append({'label': label, 'state': state, 'runtime_id': launch['runId'],
                 'raw_sha256': launch['returned_text_sha256'],
                 'script_sha256': launch['script_sha256'], 'parser_problems': bad})
fin_path = os.path.join(run, CL.K.FINALIZATION_NAME)
fin = CL.K._load(fin_path)
counts = dict(collections.Counter(r['state'] for r in rows))
invalid = [r['label'] for r in rows if r['state'] == 'invalid_response']
assert not problems and not fin['problems']
assert fin['primary_complete'] is True and fin['retry'] == invalid
assert fin['receipt_sha256'] == CL.INV.sha_file(os.path.join(run, CL.K.RECEIPT_NAME))
assert fin['ledger']['scheduled'] == len(rows)
assert all(fin['ledger'][name] == value for name, value in counts.items())
print(json.dumps({'kind': 'independent complete primary-review proof; no calls or writes',
                  'model_calls': 0, 'counts': counts, 'run_problems': problems,
                  'receipt_sha256': fin['receipt_sha256'],
                  'finalization_sha256': CL.INV.sha_file(fin_path),
                  'launch_ledger_sha256': CL.INV.sha_file(str(ledger_path)),
                  'retry': invalid, 'rows': rows}, indent=1))
