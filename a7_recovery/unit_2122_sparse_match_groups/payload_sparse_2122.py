"""Both suites in one attempt: Codex's UNMODIFIED rules-pin reproduction and
the extended native correction proof. The real combined test exit propagates.
"""
import hashlib, io, json, os, subprocess, sys
VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
SERVED = '/tmp/a7_corr2118'
MODULES = ('test_correction_rules_2118.py', 'test_correction_native_2118.py',
           'test_correction_mutations_2119.py')
print('SERVED ' + json.dumps(
    {n: hashlib.sha256(io.open(os.path.join(SERVED, n), 'rb').read()).hexdigest()
     for n in sorted(os.listdir(SERVED))
     if os.path.isfile(os.path.join(SERVED, n))}, indent=1, sort_keys=True))
print('ENVIRONMENT ' + json.dumps({k: os.environ.get(k) for k in (
    'A7_TAG', 'A7_RUN_BINDING', 'A7_TRACE_FIXTURE', 'A7_FIXTURE_PROJECTS',
    'A7_APPROVED_KEY_DIR', 'A7_DRIVER_VALIDATORS_SHA')}, sort_keys=True))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
env['PYTHONPATH'] = SERVED + os.pathsep + VIEW + os.pathsep + env.get('PYTHONPATH', '')
worst, rows = 0, []
for name in MODULES:
    r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--no-header',
                        # -rA so a PASSING check's own measurement reaches the record too
                        '-rA', '-p', 'no:cacheprovider', '-p', 'conftest',
                        os.path.join(SERVED, name)],
                       cwd=VIEW, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.strip().split('\n') if l.strip()][-1:]
    rows.append({'module': name, 'exit': r.returncode,
                 'summary': tail[0] if tail else ''})
    worst = worst or r.returncode
    print('\n===== MODULE %s exit=%d =====' % (name, r.returncode))
    print(r.stdout)
    print('----- stderr -----')
    print(r.stderr)
print('\nRESULT ' + json.dumps({'modules': rows, 'exit': worst,
                                'used_a_consumer_double': False}, indent=1))
sys.exit(worst)
