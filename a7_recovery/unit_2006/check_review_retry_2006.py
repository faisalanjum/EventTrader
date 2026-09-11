"""Read-only, exact invalid-only child proof before any retry launch."""
import json
import os
from pathlib import Path
import sys

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT.parent / 'unit_2002/owner'))
import a4_source_closure as CL

prepared = json.loads((UNIT.parent / 'unit_2004/PREPARED_REVIEW.json').read_text())
primary, package = prepared['run'], prepared['package']
child = os.path.join(primary, 'retry')
receipt = CL.K._load(os.path.join(child, CL.K.RECEIPT_NAME))
fin = CL.K._load(os.path.join(primary, CL.K.FINALIZATION_NAME))
got, problems = CL.readings(primary, package)
assert not problems, problems
assert not CL.receipt_problems(child, receipt, package)
assert receipt['attempt'] == 2 and not receipt['states']
assert not os.path.exists(os.path.join(child, CL.K.FINALIZATION_NAME))
invalid = [label for label, value in got.items() if value[0] == 'invalid_response']
assert receipt['allowed'] == fin['retry'] == invalid
by = CL.by_label()
rows = []
script_dir = Path(child) / 'scripts'
# The executable alias is a transport location, not a source or task identity.
launch_dir = Path('/tmp/claude-1000/-home-faisal-EventMarketDB') / CL.K.PARENT_SESSION / 'scratchpad/review_retry_2006'
def prompt(body):
    return json.loads(next(line[len('const PROMPT = '):] for line in body.splitlines()
                           if line.startswith('const PROMPT = ')))
for label in invalid:
    task, blind = by[label]
    script = script_dir / (label.replace('/', '_') + '.attempt2.js')
    body = script.read_text()
    expected = CL.render_launcher(task, blind, 2)
    assert body == expected
    assert prompt(body) == prompt(CL.render_launcher(task, blind, 1))
    alias = launch_dir / script.name
    assert alias.read_bytes() == script.read_bytes(), alias
    rows.append({'label': label, 'attempt': 2, 'scriptPath': str(alias),
                 'durable_logical_script': str(script), 'script_sha256': CL.INV.sha_file(str(script))})
known = {r['script_sha256'] for r in rows}
wfroot = Path('/home/faisal/.claude/projects/-home-faisal-EventMarketDB') / CL.K.PARENT_SESSION / 'workflows'
existing = []
for path in sorted(wfroot.glob('*.json')):
    doc = json.loads(path.read_text())
    if CL.K._sha(doc.get('script') or '') in known:
        existing.append({'path': str(path), 'run_id': doc.get('runId'), 'status': doc.get('status')})
assert not existing, existing
print(json.dumps({'kind': 'approved invalid-only candidate, no new call',
                  'primary': primary, 'child': child, 'package': package,
                  'parent_receipt_sha256': CL.INV.sha_file(os.path.join(primary, CL.K.RECEIPT_NAME)),
                  'parent_finalization_sha256': CL.INV.sha_file(os.path.join(primary, CL.K.FINALIZATION_NAME)),
                  'child_receipt_sha256': CL.INV.sha_file(os.path.join(child, CL.K.RECEIPT_NAME)),
                  'primary_valid_preserved': sum(v[0] == 'valid' for v in got.values()),
                  'scheduled_child': len(rows), 'call_total_before': fin['budget']['ledger_after'],
                  'call_total_after': fin['budget']['ledger_after'] + len(rows),
                  'ceiling': fin['budget']['global_ceiling'],
                  'native_existing_child_identities': existing, 'invocations': rows}, indent=1))
