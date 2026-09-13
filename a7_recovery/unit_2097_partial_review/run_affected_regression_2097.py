"""Run the grading tests directly affected by the new partial-report policy.

The unit's own aligned harness compares a CHANGED owner tree against its
predecessor. Nothing frozen changed in this round - the policy is a new,
separate module that patches B._lifecycle only inside an explicit scope - so
there is no before/after owner tree to align and that harness does not apply.
The affected set is therefore DERIVED from live imports: every served test
module that imports an owner the policy actually touches.

TEST-only: reads the served harness, writes nothing outside this unit, calls
no model, and changes no frozen owner or real run.
"""
import collections
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
#: the owners the policy reaches: it patches B._lifecycle, and that gate is
#: read by B.refuse, the two public B entries and a7_g23_run.populations.
TOUCHED = ('a7_g23_build', 'a7_g1_build', 'a7_g23_run', 'a7_g1_complete_v2')
OUT = os.path.join(HERE, 'AFFECTED_REGRESSION_2097.json')


def affected_modules():
    """Every served test module importing an owner the policy touches."""
    found = []
    for name in sorted(os.listdir(VIEW)):
        if not (name.startswith('test_') and name.endswith('.py')):
            continue
        text = io.open(os.path.join(VIEW, name), encoding='utf-8').read()
        if any(('import ' + owner) in text for owner in TOUCHED):
            found.append(name)
    return found


modules = affected_modules()
assert modules, 'no affected module found; the derivation is wrong, not the code'

def demanded_env(text):
    """The env var a module's own fixture assertion names, if it has one."""
    for line in text.split('\n'):
        if 'assert' in line and 'A7_' in line:
            for tok in line.replace('"', ' ').replace("'", ' ').split():
                if tok.startswith('A7_'):
                    return tok
    return None

per, green, needs_fixture = [], 0, []
for m in modules:
    path = os.path.join(VIEW, m)
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '--no-header',
         '-p', 'no:cacheprovider', path],
        cwd=VIEW, capture_output=True, text=True)
    tail = [l for l in proc.stdout.strip().split('\n') if l.strip()][-1:]
    summary = tail[0] if tail else ''
    env = demanded_env(io.open(path, encoding='utf-8').read())
    ok = proc.returncode == 0
    green += ok
    if not ok and env:
        needs_fixture.append({'module': m, 'demands': env})
    per.append(collections.OrderedDict([
        ('module', m), ('exit', proc.returncode), ('summary', summary),
        ('fixture_env_its_own_assertion_names', env)]))

result = collections.OrderedDict([
    ('kind', 'grading tests directly affected by the new partial-report policy'),
    ('derivation', 'served test modules importing any of ' + ', '.join(TOUCHED)),
    ('why_not_the_aligned_harness',
     'grader_20260909/regression.py compares a CHANGED owner tree with its '
     'predecessor; no frozen owner changed this round, so it has no second '
     'side to align and does not apply here'),
    ('policy_imported_by_any_affected_module',
     any('a7_partial_grading_2095' in io.open(os.path.join(VIEW, m), encoding='utf-8').read()
         for m in modules)),
    ('module_count', len(modules)),
    ('modules_green', green),
    ('modules_needing_an_unserved_TEST_fixture', needs_fixture),
    ('per_module', per),
    ('model_calls', 0)])
with io.open(OUT, 'x', encoding='utf-8') as fh:
    fh.write(json.dumps(result, indent=1) + '\n')
print('modules %d | green %d | needing an unserved fixture %d'
      % (len(modules), green, len(needs_fixture)))
for r in per:
    print('  %-42s exit %d  %s' % (r['module'], r['exit'], r['summary'][:44]))
print('wrote', OUT)
