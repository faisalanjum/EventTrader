"""Read-only query of the actual post-review signing gate; no model calls.

The earlier source-only helper deliberately assumes no hard reviews. It is
not this phase's signing interface: the published integration uses the final
owner directly inside the composite's role-bound final scope, retaining all
66 completed reviews. Do not turn the earlier helper's output into new calls.
"""
import json
from pathlib import Path
import sys

A7 = Path(__file__).resolve().parents[1]
unit = A7 / 'unit_2017_final_source_key'
record = json.loads((unit / 'PREPARED_FINAL_KEY_2017.core_final2017_real.json').read_text())
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R

with R.final_scope(record['review_run'], record['review_package'], bind_role=True):
    bound = R.SK.bound(record['run'], record['package'])
    gate = R.F.signing_gate(record['run'], bound)
assert gate['ok'] is False
print(json.dumps({'interface': 'R.final_scope(bind_role=True) -> F.signing_gate',
                  'key_truth_approved': False, 'model_calls': 0,
                  'gate': gate}, indent=1, default=str))
