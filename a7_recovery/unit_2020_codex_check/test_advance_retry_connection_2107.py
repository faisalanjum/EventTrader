"""Exercise the actual operator's read-only retry-selection blocks.

Do not execute its preserve/ingest/publish stages: these saved segments are
already finalized. The extracted setup and selection are exact source slices;
the real existing runner and retry-filter CLI execute, with zero AI calls.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
script = HERE.parent / 'unit_2103_execution_prep/advance_2104.sh'
text = script.read_text()
prefix = text.split('# Codex step 4:', 1)[0]
start = text.index('# the finalizer decides; this only reads it')
end = text.index('echo "== next: $NEXT" >&2', start)
selection = text[start:end]
assert 'record_workflow_2104.py' not in prefix
assert 'run ingest' not in selection and 'run retry ' not in selection
base = dict(os.environ)
tag = base['A7_TAG']
out = HERE / tag
out.mkdir()
results = []
for name, kind, segment, pins_ok in [('G2_recovered', 'G2', 4, True),
                                    ('G3_unchanged', 'G3', 10, True),
                                    ('G2_wrong_pin', 'G2', 4, False)]:
    env = dict(base)
    if not pins_ok:
        env['A7_FORMAT_RULE_SHA256'] = '0' * 64
    shell = prefix + '\nSTAMP=' + tag + '_' + name + '\n'
    shell += 'RSHA=$(sha256sum "$UNIT/run/receipt.$TAG.json" | cut -d" " -f1)\n'
    shell += selection + '\nprintf "%s\\n" "$NEXT"\n'
    ran = subprocess.run(['bash', '-c', shell, 'operator-test', kind, str(segment), 'wf_NOT_CALLED'],
                         cwd=str(HERE.parents[1]), env=env, text=True, capture_output=True)
    (out / (name + '.json')).write_text(json.dumps({
        'exit': ran.returncode, 'stdout': ran.stdout, 'stderr': ran.stderr}, indent=2) + '\n')
    if pins_ok:
        assert ran.returncode == 0 and ran.stdout.strip() == 'prepare', (name, ran.returncode, ran.stdout, ran.stderr)
    else:
        assert ran.returncode != 0 and 'unapproved meaning-format rule' in ran.stderr, (name, ran.stdout, ran.stderr)
    results.append({'name': name, 'exit': ran.returncode, 'stdout': ran.stdout, 'stderr': ran.stderr})
(out / 'OPERATOR_CONNECTION.json').write_text(json.dumps({
    'operator_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
    'retry_filter_sha256': base['A7_RETRY_PLAN_SHA256'],
    'checks': results, 'actual_model_calls': 0,
    'real_preserve_ingest_publish_stages_not_executed': True}, indent=2) + '\n')
print('VERIFIED: actual operator selection calls pinned filter; recovered G2 not repeated; G3 unchanged; wrong pin stops')
