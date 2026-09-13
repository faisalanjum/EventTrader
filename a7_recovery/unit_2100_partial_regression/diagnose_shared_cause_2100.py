"""Why 12 of the 19 affected modules never reach grading.

Pure reading. No run, no fix, no model call. Three questions, in order:

  1. Which failure cause does each failing module actually carry? A count of
     modules is not a count of problems; the families have to be named.
  2. For the dominant cause, what EXACTLY is the saved receipt.derived_from
     versus the value the live rule owner expects, field by field?
  3. Which owner produces that expectation, and does my view serve the same
     one the two passing baselines served?

The answer must come from the served bytes and the saved evidence, never from
a summary of them, so every sha here is measured at read time.
"""
import collections
import hashlib
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
G = os.path.join(A7, 'grader_20260909')
LOG = os.path.join(A7, 'unit_1957/logs/attempt_grader_core2099run2/stdout.txt')
COMPARE = os.path.join(A7, 'unit_2099_partial_regression/ARM_COMPARISON_2099.json')
NATIVE5 = os.path.join(G, 'attempts/native_final5/logs/attempt_grader_native_final5'
                          '/ALIGNED_grader_native_final5.json')
#: the receipt the preserved lineage carries, as my run served it
RECEIPT = os.path.join(G, 'attempts/core2099base/logs/life_native5/hr_run/receipt.json')
#: the binding that names that lineage, and the one the REAL grading run uses
TEST_BOUND = os.path.join(A7, 'unit_1957/logs/ordinary_bound_1957.json')
REAL_BOUND = os.path.join(A7, 'unit_2081_final_key_candidate/codex_cand2082_a'
                              '/ordinary_bound.json')
#: the file whose bytes the expectation is computed from
OWNER = 'build_kfields_key.py'
VIEWS = collections.OrderedDict([
    ('native_final5 (passing baseline)', os.path.join(G, 'attempts/native_final5/view/harness_g1v3')),
    ('ordinary_final4 (passing baseline)', os.path.join(G, 'attempts/ordinary_final4/view/harness_g1v3')),
    ('core2099base (my run)', os.path.join(G, 'attempts/core2099base/view/harness_g1v3')),
    ('unit_2008 (current harness)', os.path.join(A7, 'unit_2008/harness_g1v3')),
])
OUT = os.path.join(HERE, 'SHARED_CAUSE_2100.json')


def sha(path):
    with io.open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def blocks(path):
    """{module: its whole stdout block}, split on the payload's own marker."""
    text = io.open(path, encoding='utf-8', errors='replace').read()
    out = collections.OrderedDict()
    for chunk in re.split(r'^===== MODULE ', text, flags=re.M)[1:]:
        head = chunk.split('\n')[0]
        out[head.split(' ')[0]] = (int(head.split('exit=')[1].split(' ')[0]), chunk)
    return out


def cause_lines(chunk):
    """The distinct `E   <Exception>: ...` first lines this module reported.

    Read off the output, not matched against a list of causes I expect - a
    cause I did not anticipate has to show up here rather than be dropped.
    """
    seen = collections.OrderedDict()
    for line in chunk.split('\n'):
        hit = re.match(r'^E +([A-Za-z_.]*(?:Error|Exception)): (.*)$', line.strip())
        if hit:
            seen.setdefault(hit.group(1) + ': ' + hit.group(2)[:140], 0)
            seen[hit.group(1) + ': ' + hit.group(2)[:140]] += 1
    return seen


ran = blocks(LOG)
compare = json.load(io.open(COMPARE))
native_family = set(json.load(io.open(NATIVE5))['union_modules'])
failing = sorted(compare['modules_failing_both_arms'])

per_module = collections.OrderedDict()
for module in failing:
    code, chunk = ran[module]
    per_module[module] = collections.OrderedDict([
        ('exit', code),
        ('baseline_family', 'native_final5' if module in native_family
         else 'ordinary_final4'),
        ('distinct_causes', cause_lines(chunk))])

# ---- question 2: the saved versus the expected derived_from -------------------
saved = json.load(io.open(RECEIPT))['derived_from']
served_owner = sha(os.path.join(VIEWS['core2099base (my run)'], OWNER))
# _derived_from computes owner_sha256 from the file next to the LOADED module,
# so the expected value is simply whatever this view serves.
field_check = collections.OrderedDict([
    ('owner_sha256', collections.OrderedDict([
        ('saved_in_receipt', saved['owner_sha256']),
        ('expected_under_my_view', served_owner),
        ('agrees', saved['owner_sha256'] == served_owner)]))])
for field in [f for f in saved if f != 'owner_sha256']:
    # the other four are read from the evidence run directory, which the
    # preserved lineage carries verbatim; they are recorded for completeness
    field_check[field] = collections.OrderedDict([
        ('saved_in_receipt', saved[field]),
        ('recomputed_here', None),
        ('note', 'read from the evidence run dir, not from served code')])

record = collections.OrderedDict([
    ('kind', 'why the affected modules never reach grading'),
    ('modules_failing', len(failing)),
    ('per_module', per_module),
    ('rule_owner', collections.OrderedDict([
        ('expectation_built_by',
         'build_kfields_hard_review._derived_from, line 575'),
        ('the_binding_line',
         'line 578: INV.sha_file(os.path.join(_HERE, "build_kfields_key.py"))'),
        ('_HERE_is', 'the directory of the LOADED build_kfields_hard_review.py'),
        ('checked_by',
         'build_kfields_hard_review._receipt_problems line 906-908, over '
         'RECEIPT_IMMUTABLE which includes derived_from'),
        ('surfaced_by',
         'build_kfields_final.hard_reading_problems line 149, called first by '
         'signing_gate line 2139, raised by a7_g1_build.gold_by_event line 364'),
    ])),
    ('derived_from', field_check),
    ('owner_served_by_each_view', collections.OrderedDict(
        (name, sha(os.path.join(path, OWNER)) if os.path.isfile(os.path.join(path, OWNER))
         else 'ABSENT') for name, path in VIEWS.items())),
    ('bindings', collections.OrderedDict([
        ('test_fixture', json.load(io.open(TEST_BOUND))),
        ('real_grading_run', json.load(io.open(REAL_BOUND)))])),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')

for module, info in per_module.items():
    print('%-42s %-16s %s' % (module, info['baseline_family'],
                              list(info['distinct_causes'])[:1]))
print()
print('saved  owner_sha256:', saved['owner_sha256'])
print('served owner_sha256:', served_owner)
print('agree:', saved['owner_sha256'] == served_owner)
print('wrote', OUT)
