"""BASELINE regression of the affected grading tests, current TEST view.

This is a BASELINE of the current frozen owners in a correctly provisioned
TEST view. It does NOT exercise the partial scope: nothing here enters
a7_partial_grading_2095.scope, and no module imports it. Codex owns the
policy's own unit, mutation and real G1-to-scoring proof.

Runs inside the boundary. Every module is run separately and its FULL stdout,
stderr and real exit code are printed; nothing is summarised away and no setup
error is converted into a skip.
"""
import io
import json
import os
import subprocess
import sys

VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
#: the owners the policy patches or reads; the affected set is derived, not typed
TOUCHED = ('a7_g23_build', 'a7_g1_build', 'a7_g23_run', 'a7_g1_complete_v2')


def affected():
    out = []
    for name in sorted(os.listdir(VIEW)):
        if name.startswith('test_') and name.endswith('.py'):
            text = io.open(os.path.join(VIEW, name), encoding='utf-8').read()
            if any(('import ' + owner) in text for owner in TOUCHED):
                out.append(name)
    return out


modules = affected()
print('VIEW %s' % VIEW)
print('AFFECTED_MODULES %d' % len(modules))
print('ENVIRONMENT ' + json.dumps({k: os.environ.get(k) for k in (
    'A7_APPROVED_KEY_DIR', 'A7_TRACE_FIXTURE', 'A7_FIXTURE_PROJECTS',
    'A7_RUN_BINDING', 'A7_LANE_INPUT_PROFILES', 'A7_DRIVER_VALIDATORS_SHA',
    'CLAUDE_CODE_MAX_OUTPUT_TOKENS')}, sort_keys=True))

rows, green = [], 0
for name in modules:
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '--no-header', '-ra',
         '-p', 'no:cacheprovider', os.path.join(VIEW, name)],
        cwd=VIEW, capture_output=True, text=True)
    tail = [l for l in proc.stdout.strip().split('\n') if l.strip()][-1:]
    green += proc.returncode == 0
    rows.append({'module': name, 'exit': proc.returncode,
                 'summary': tail[0] if tail else '',
                 'stdout_bytes': len(proc.stdout.encode('utf-8')),
                 'stderr_bytes': len(proc.stderr.encode('utf-8'))})
    print('\n===== MODULE %s exit=%d =====' % (name, proc.returncode))
    print('----- stdout -----')
    print(proc.stdout)
    print('----- stderr -----')
    print(proc.stderr)

print('\nRESULT ' + json.dumps({
    'kind': 'baseline regression of the affected grading modules, current TEST view',
    'exercises_partial_scope': False,
    'module_count': len(modules), 'modules_green': green,
    'per_module': rows}, indent=1))
