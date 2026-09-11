"""Independent read-only verification of the four real requests; no calls."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

A7 = Path(__file__).resolve().parents[1]
unit = A7 / 'unit_2015_real_reviews'
record = json.loads(Path(os.environ['A7_PREP_RECORD']).read_text())
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R

runpy.run_path(str(unit / 'verify_prepared_2015.py'), run_name='__main__')
import boundary as B
import a7_prepared_run as PR

mapping = B.read_map(os.environ['A7_PREP_MAP'])
assert B.validate(mapping) == []
old, stage = R.old_readings()
assert dict(Counter(v[0] for v in old.values())) == {'valid': 62, 'invalid_response': 4}
owed = [k for k, v in old.items() if v[0] != 'valid']
assert owed == ['sokc-013/b2', 'sokc-020/b1', 'sokc-026/b1', 'sokc-029/b2']
ctx = R._context(old, stage)
pkg, run = record['package'], record['run']
preflight = R.HR._preflight(ctx, pkg)
assert preflight['ok'] and preflight['problems'] == []
receipt = R.K._load(os.path.join(run, R.K.RECEIPT_NAME))
assert receipt == R.HR._expected_receipt(ctx, run, pkg, 1, owed)
with R.old_scope():
    old_ctx = R.CL._ctx()
    old_by = R.OLD._by_label_of(old_ctx)
    original_prompts = {lab: R.OLD._blind_prompt(old_ctx, old_by[lab][0]) for lab in owed}
    old_prefix = R.OLD._prompt_prefix(old_ctx['suffix'], 'group')

by_label = R.HR._by_label_of(ctx)
new_prefix = R.HR._prompt_prefix(ctx['suffix'], 'group')
sizes = []
for inv in record['invocations']:
    label = inv['label']
    task, blind = by_label[label]
    prompt = R.HR._blind_prompt(ctx, task)
    original = original_prompts[label]
    assert original.startswith(old_prefix)
    assert prompt == new_prefix + original[len(old_prefix):]
    assert hashlib.sha256(prompt.encode()).hexdigest() == receipt['prompts'][label]
    expected = R.HR._render_launcher(ctx, task, blind, 1).encode()
    durable = Path(inv['scriptPath']).read_bytes()
    launch = Path(os.environ['A7_LAUNCH_DIR']) / Path(inv['scriptPath']).name
    assert durable == expected == launch.read_bytes()
    assert hashlib.sha256(durable).hexdigest() == inv['script_sha256']
    assert len(durable) < R.K.TRANSPORT_LIMIT
    sizes.append(len(durable))

assert len(sizes) == 4 and max(sizes) == record['capacity']['largest_script_bytes']
assert ctx['before'] == 495
assert [record['budget'][k] for k in ('primaries', 'after_primaries', 'worst_case_after')] == [4, 499, 503]
a3 = PR._executed(os.path.abspath(R.K.a3_run_dirs()[0]))
assert a3 == {'run_digest': '460c543b82ec3c69be70b2eebec3df1311263ecf885d3a1215ddc8627ad08034', 'run_files': 799}
assert not (Path(run) / 'raw').exists()
assert not (Path(run) / R.K.FINALIZATION_NAME).exists()
print(json.dumps({'independent_packet_verified': True,
                  'all_binding_rows': len(mapping), 'owed': owed,
                  'only_prompt_prefix_changed': len(sizes),
                  'script_bytes': sizes, 'a3': a3, 'model_calls': 0}, indent=1))
