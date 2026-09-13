"""Exactly which receipt field disagrees, and what the two values are.

Runs INSIDE the boundary, so the paths and the loaded modules are the ones the
failing test itself gets. It asks the rule owner for its own expectation rather
than recomputing one: _expected_for is what _receipt_problems compares against,
so anything else would be a second, unreviewed opinion.

Reads only. Writes nothing, calls no model, fixes nothing.
"""
import collections
import json
import os
import sys

VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
sys.path.insert(0, VIEW)
os.chdir(VIEW)

import a7_g1_build as G                                           # noqa: E402
import audit_worker_access as AUD                                 # noqa: E402
import a7_reference_inventory as REF                              # noqa: E402
import build_kfields_hard_review as HR                            # noqa: E402
import build_kfields_key as K                                     # noqa: E402

# THE FIXTURE'S OWN TWO BINDINGS, copied from test_a7_trace_1471.run lines
# 38-39, not invented here: the official-state root and the reference
# inventory the trace fixture carries. _items() is lru_cached, so these must
# be in force before the first call or the cache freezes the unpatched answer.
AUD.PROJECTS_ROOT = os.environ['A7_FIXTURE_PROJECTS']
REF.INVENTORY_PATH = os.path.join(os.environ['A7_TRACE_FIXTURE'],
                                  'reference_inventory.json')
print('PROJECTS_ROOT ' + AUD.PROJECTS_ROOT)
print('INVENTORY_PATH ' + REF.INVENTORY_PATH)

bound = G._approved_bound()
print('BOUND ' + json.dumps({f: getattr(bound, f, None) for f in
                             ('package', 'evidence', 'hr', 'hr_package',
                              'events')}, indent=1))
print('KEY_OWNER_SERVED ' + K._sha(open(
    os.path.join(VIEW, 'build_kfields_key.py'), encoding='utf-8').read()))

report = collections.OrderedDict()
for base, origin in ((bound.hr, 'hard_review_primary'),
                     (os.path.join(bound.hr, 'retry'), 'hard_review_child')):
    path = os.path.join(base, HR.RECEIPT_NAME)
    if not os.path.isfile(path):
        report[origin] = {'receipt': path, 'present': False}
        continue
    receipt = K._load(path)
    ctx = HR._default(bound.evidence)
    want, bad = HR._expected_for(ctx, base, bound.hr_package, receipt)
    fields = collections.OrderedDict()
    if want is not None:
        for field in HR.RECEIPT_IMMUTABLE:
            got, expect = receipt.get(field), want[field]
            fields[field] = collections.OrderedDict([
                ('agrees', got == expect),
                ('saved', got), ('expected', expect)])
    report[origin] = collections.OrderedDict([
        ('receipt', path), ('present', True),
        ('expected_for_refused_with', bad),
        ('problems', HR._receipt_problems(ctx, base, bound.hr_package, receipt)),
        ('fields', fields)])

print('PROBE ' + json.dumps(report, indent=1, default=str))
