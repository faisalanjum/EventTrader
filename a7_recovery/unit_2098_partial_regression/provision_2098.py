"""Provision the CURRENT TEST view through the EXISTING preparer.

The only difference from a normal preparer call is the harness it copies:
prepare.HARNESS is pointed at this unit's private, verified CURRENT harness
(unit_2008 plus the map_real_grading_2088 overlays) instead of the
grader_20260909 working copy, whose build_inventory_review.py is the
tracked-modified file. No preparation framework is added and prepare.py is
not edited; only that one module attribute is bound for this call.

The preparer writes its own uniquely tagged artifacts in its own locations
(grader_20260909/attempts/<name> and unit_1957/map_codex_grader_<name>.tsv).
That is the existing runner's own output, not new machinery of mine.
"""
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
A7 = HERE.parent
NAME = os.environ.get('A7_PROVISION_NAME', 'core2098base')
PAYLOAD = HERE / 'payload_affected_regression_2098.py'
PRIVATE = HERE / 'harness_g1v3'
OUT = HERE / 'PROVISION_2098.json'

sys.path.insert(0, str(A7 / 'grader_20260909'))
import prepare as P                                              # noqa: E402

assert PRIVATE.is_dir(), 'build the private harness first'
report = json.load(io.open(HERE / 'PRIVATE_HARNESS_2098.json'))
assert report['base_tree_matches_the_live_map'], 'the private harness is stale'

original = P.HARNESS
P.HARNESS = PRIVATE                       # the one bound attribute, for this call
try:
    result = P.prepare(NAME, PAYLOAD, native=True, key_fixture=True)
finally:
    P.HARNESS = original

record = {
    'kind': 'CURRENT TEST view provisioned through the existing preparer',
    'preparer': str(A7 / 'grader_20260909/prepare.py'),
    'harness_bound_to': str(PRIVATE),
    'harness_not_used': str(original),
    'why': 'the grader_20260909 copy is the tracked-modified build_inventory_review.py',
    'private_tree_sha256': report['private_tree_sha256'],
    'result': result,
    'model_calls': 0,
}
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print(json.dumps(record, indent=1))
