"""Read-only native, raw, parser and accounting proof for both review attempts."""
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
baseline = UNIT.parent / 'unit_1947/logs/attempt_codex_primary2006_a/stdout.txt'
assert CL.INV.sha_file(str(baseline)) == '28209076a36c25236aa4d20e08bdf0a6a4839ceb3855cef921e28ada230b2f7e'
before = json.loads(baseline.read_text())
prior = {row['label']: row for row in before['rows']}
effective, problems = CL.readings(run, package)
assert not problems, problems
ctx = CL._ctx()
by = CL.by_label()
rows = []
proofs = []
for attempt, base in ((1, run), (2, os.path.join(run, 'retry'))):
    receipt = CL.K._load(os.path.join(base, CL.K.RECEIPT_NAME))
    fin = CL.K._load(os.path.join(base, CL.K.FINALIZATION_NAME))
    assert not CL.HR._receipt_problems(ctx, base, package, receipt)
    evidence, bad = CL.HR._run_evidence(ctx, base, package, receipt)
    assert not bad, bad
    assert fin['primary_complete'] is True and not fin['problems']
    assert fin['receipt_sha256'] == CL.INV.sha_file(os.path.join(base, CL.K.RECEIPT_NAME))
    assert len(receipt['allowed']) == len(receipt['states']) == len(evidence)
    counts = collections.Counter()
    for label, (status, why, raw) in evidence.items():
        assert status == 'proved', (label, status, why)
        task, blind = by[label]
        _parsed, bad = CL.read_reply(raw, task)
        state = 'invalid_response' if bad else 'valid'
        counts[state] += 1
        raw_sha = CL.K._sha(raw)
        script = os.path.join(base, 'scripts', label.replace('/', '_') + '.attempt%d.js' % attempt)
        assert CL.K._sha(CL.render_launcher(task, blind, attempt)) == CL.INV.sha_file(script)
        if attempt == 1:
            assert raw_sha == prior[label]['raw_sha256']
            assert state == prior[label]['state']
            if state == 'valid':
                assert effective[label] == ('valid', '', raw)
        else:
            assert label in before['retry']
        rows.append({'label': label, 'attempt': attempt, 'state': state,
                     'raw_sha256': raw_sha, 'script_sha256': CL.INV.sha_file(script),
                     'parser_problems': bad})
    assert all(fin['ledger'][name] == counts[name] for name in counts)
    if attempt == 2:
        assert set(receipt['allowed']) == set(before['retry']) and fin['retry'] == []
    proofs.append({'attempt': attempt, 'receipt_sha256': fin['receipt_sha256'],
                   'finalization_sha256': CL.INV.sha_file(os.path.join(base, CL.K.FINALIZATION_NAME)),
                   'raw_tree': CL.F.raw_tree(base), 'counts': dict(counts), 'budget': fin['budget']})
counts = dict(collections.Counter(v[0] for v in effective.values()))
assert len(effective) == len(prior) == 66
assert proofs[-1]['budget']['ledger_after'] == 415 + sum(sum(p['counts'].values()) for p in proofs)
try:
    with CL.final_scope(run, package):
        final_ready = True
except ValueError as exc:
    final_ready = False
    final_refusal = str(exc)
assert final_ready == (counts.get('valid') == len(effective))
print(json.dumps({'kind': 'independent complete review-attempt proof, not truth approval',
                  'model_calls': 0, 'effective': counts, 'problems': problems,
                  'all_52_valid_primary_texts_preserved': True,
                  'final_ready': final_ready,
                  'final_refusal': None if final_ready else final_refusal,
                  'attempts': proofs, 'rows': rows}, indent=1))
