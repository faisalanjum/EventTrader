"""The controlled ladder that names the shared cause exactly.

One variable is added at each rung and the receipt's own verifier is asked
what it still objects to. The verifier is never patched, the receipt is never
rehashed, and the expectation is taken from _expected_for - the same function
_receipt_problems compares against - so nothing here is a second opinion.

  rung        extra file served from the sealing era      remaining fault
  current     -                                           receipt.derived_from
  era         build_kfields_key.py                        receipt.prompts
  era2        + build_kfields_hard_review.py              none

Two independent era-bound fields, both read off the run, not predicted.
"""
import collections
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
A7 = os.path.dirname(HERE)
LOGS = os.path.join(A7, 'unit_1957/logs')
OUT = os.path.join(HERE, 'CAUSE_LADDER_2100.json')
#: (rung, the module run's log tag, the probe's log tag)
RUNGS = (('current', 'grader_core2100cur', None),
         ('era', 'grader_core2100era', 'grader_probe2100era2'),
         ('era2', 'grader_core2100era2', 'grader_probe2100era2f'))
FAULT = re.compile(r"receipt is not the owner's: (receipt\.[a-z_]+)")


def stdout(tag):
    path = os.path.join(LOGS, 'attempt_' + tag, 'stdout.txt')
    return io.open(path, encoding='utf-8', errors='replace').read()


rows = collections.OrderedDict()
for rung, run_tag, probe_tag in RUNGS:
    text = stdout(run_tag)
    summary = [l for l in text.split('\n')
               if re.match(r'^\s+"summary": ', l)]
    faults = sorted(set(FAULT.findall(text)))
    probe = None
    if probe_tag:
        ptext = stdout(probe_tag)
        doc = json.loads(ptext[ptext.index('PROBE ') + 6:])
        probe = collections.OrderedDict(
            (origin, info.get('problems')) for origin, info in doc.items())
    # MEASURED from the served snapshots, not read off a recorded field: the
    # question is which bytes this rung actually served, and only the trees
    # themselves can answer that.
    view = os.path.join(A7, 'grader_20260909/attempts',
                        run_tag.replace('grader_', ''), 'view/harness_g1v3')
    baseline_view = os.path.join(A7, 'grader_20260909/attempts/core2100cur',
                                 'view/harness_g1v3')
    differs = sorted(
        name for name in os.listdir(view)
        if os.path.isfile(os.path.join(view, name))
        and io.open(os.path.join(view, name), 'rb').read()
        != io.open(os.path.join(baseline_view, name), 'rb').read())
    rows[rung] = collections.OrderedDict([
        ('served_from_the_sealing_era', differs),
        ('served_view', view),
        ('module_summary', summary[0].split('"summary": ')[1].strip(' ",')
         if summary else None),
        ('receipt_faults_the_module_hit', faults or ['none']),
        ('probe_problems_by_origin', probe)])

record = collections.OrderedDict([
    ('kind', 'controlled ladder isolating the shared TEST fixture mismatch'),
    ('representative_module', 'test_a7_trace_1471.py'),
    ('verifier_used', 'build_kfields_hard_review._receipt_problems, unpatched'),
    ('expectation_source', 'build_kfields_hard_review._expected_for, unpatched'),
    ('rungs', rows),
    ('conclusion', 'the preserved TEST lineage is sealed against a harness ERA, '
                   'not against one file: derived_from pins the key owner BYTES '
                   'and prompts pins the LIVE render of the hard-review prompt. '
                   'Both changed lawfully since the seal.'),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(record, indent=1) + '\n')
for rung, info in rows.items():
    print('%-8s %-46s %-28s %s' % (
        rung, ','.join(info['served_from_the_sealing_era']) or '-',
        info['module_summary'], ','.join(info['receipt_faults_the_module_hit'])))
print('wrote', OUT)
