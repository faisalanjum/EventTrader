"""Why do those modules error? Run ONE of them alone and keep the reason.

Diagnosis only: the new policy is not imported by any of these modules, so it
cannot be the cause. This establishes whether the errors are pre-existing
setup conditions of running them outside their own invocation, which is what
they look like, rather than anything this round changed.
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
MODULE = 'test_a7_trace_1471.py'
OUT = os.path.join(HERE, 'ERROR_DIAGNOSIS_2097.json')

proc = subprocess.run(
    [sys.executable, '-m', 'pytest', '-q', '--no-header',
     '-p', 'no:cacheprovider', os.path.join(VIEW, MODULE)],
    cwd=VIEW, capture_output=True, text=True)
text = proc.stdout
# the first setup error's own words, not a summary line
reason = ''
for marker in ('ERROR at setup', 'errors during collection', 'E   '):
    i = text.find(marker)
    if i != -1:
        reason = text[i:i + 700]
        break
result = {
    'module': MODULE,
    'exit_code': proc.returncode,
    'summary': [l for l in text.strip().split('\n') if l.strip()][-1:],
    'first_error_text': reason,
    'policy_imported_by_this_module':
        'a7_partial_grading_2095' in io.open(os.path.join(VIEW, MODULE),
                                             encoding='utf-8').read()
        if os.path.isfile(os.path.join(VIEW, MODULE)) else None,
}
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(result, indent=1) + '\n')
print(json.dumps(result, indent=1)[:1800])
