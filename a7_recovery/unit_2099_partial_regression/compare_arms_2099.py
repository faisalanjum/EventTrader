"""Isolate the new G2/G3 grouping owner by controlled comparison.

Two runs of the SAME 19 affected modules in the SAME provisioned TEST view,
differing in exactly one served file: a7_g23_run.py. Anything that changes
between them is the overlay's doing; anything identical in both is not.

"the tests do not import it" is not this proof - that argument was refused,
correctly. This measures both arms instead.
"""
import collections
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
LOGS = os.path.join(A7, 'unit_1957/logs')
NEW = os.path.join(LOGS, 'attempt_grader_core2099run2/stdout.txt')
OLD = os.path.join(LOGS, 'attempt_grader_core2099ctrl/stdout.txt')
OUT = os.path.join(HERE, 'ARM_COMPARISON_2099.json')
#: the 11 modules the saved native_final5 baseline listed as fixture-dependent
NATIVE_FINAL5 = json.load(io.open(os.path.join(
    A7, 'grader_20260909/attempts/native_final5/logs/'
        'attempt_grader_native_final5/ALIGNED_grader_native_final5.json')))


def per_module(path):
    text = io.open(path, encoding='utf-8', errors='replace').read()
    out = collections.OrderedDict()
    for block in re.split(r'^===== MODULE ', text, flags=re.M)[1:]:
        head = block.split('\n')[0]
        name = head.split(' ')[0]
        code = int(head.split('exit=')[1].split(' ')[0])
        summary = [l for l in block.split('\n')
                   if ' in ' in l and re.match(r'^\d+ (passed|failed)', l)]
        named = [l for l in block.split('\n')
                 if l.startswith('FAILED ') or l.startswith('ERROR ')]
        out[name] = collections.OrderedDict([
            ('exit', code), ('summary', summary[-1] if summary else ''),
            ('named_failures', len(named))])
    return out


new, old = per_module(NEW), per_module(OLD)
assert set(new) == set(old), 'the two arms did not run the same modules'

differs = [m for m in new if new[m]['exit'] != old[m]['exit']
           or new[m]['named_failures'] != old[m]['named_failures']]
green = sorted(m for m in new if new[m]['exit'] == 0)
failing = sorted(m for m in new if new[m]['exit'] != 0)
baseline_11 = list(NATIVE_FINAL5['union_modules'])
baseline_now_failing = sorted(m for m in baseline_11 if m in failing)

record = collections.OrderedDict([
    ('kind', 'controlled comparison isolating the new G2/G3 grouping owner'),
    ('only_difference_between_arms', 'a7_g23_run.py'),
    ('treatment_log', NEW), ('control_log', OLD),
    ('modules', len(new)),
    ('modules_differing_between_arms', differs),
    ('overlay_changes_any_affected_module', bool(differs)),
    ('modules_green_both_arms', green),
    ('modules_failing_both_arms', failing),
    ('saved_native_final5', collections.OrderedDict([
        ('summary', NATIVE_FINAL5['summary']),
        ('union_modules', baseline_11),
        ('of_those_now_failing', baseline_now_failing),
        ('caveat', 'that run served the OLD baseline harness; this run serves '
                   'the CURRENT one. The harness version is NOT isolated here, '
                   'so this difference is reported, not attributed.')])),
    ('per_module', collections.OrderedDict(
        (m, collections.OrderedDict([('new', new[m]), ('old', old[m])]))
        for m in sorted(new))),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
print('modules', len(new), '| green both arms', len(green),
      '| failing both arms', len(failing))
print('modules changed by the overlay:', differs or 'NONE')
print('of the 11 baseline modules, now failing:', len(baseline_now_failing))
print('wrote', OUT)
