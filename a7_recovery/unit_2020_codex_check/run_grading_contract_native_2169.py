"""Run the existing lifecycle with the new contract in its pinned served view."""
import hashlib
import json
import os
import subprocess
import sys

VIEW = ('/tmp/claude-1000/-home-faisal-EventMarketDB/'
        '5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/'
        '.claude/plans/Drivers/experiments/harness_g1v3')
SERVED = '/tmp/a7_corr2118'
TEST = os.path.join(SERVED, os.environ.get('A7_NATIVE_TEST', 'test_grading_contract_native_2169.py'))
OWNERS = ('a7_grading_contract_2168.py', 'a7_grading_input_correction_2114.py',
          'a7_grading_revision_2115.py', 'a7_correction_candidate_2118.py',
          'test_correction_native_2118.py', os.path.basename(TEST))
print('CONTRACT_NATIVE_2169 ' + json.dumps({
    name: hashlib.sha256(open(os.path.join(SERVED, name), 'rb').read()).hexdigest()
    for name in OWNERS}, sort_keys=True), flush=True)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
           PYTHONPATH=SERVED + os.pathsep + VIEW)
out = os.environ['A7_CONTRACT_NATIVE_OUT']
# The fixture's recorded state paths are identities: keep its proven logical
# projects root. The existing TEST state builder derives new workflow IDs from
# each unique run directory under this attempt; it does not replace old runs.
result = subprocess.run([
    sys.executable, '-B', '-m', 'pytest', '-q', '-x', '--no-header', '-ra',
    '-p', 'no:cacheprovider', '-p', 'conftest',
    '--basetemp=' + os.path.join(out, 'pytest'), TEST],
    cwd=VIEW, env=env)
print('TEST_REPLIES_ONLY; model calls=0; raw pytest exit=' + str(result.returncode), flush=True)
sys.exit(result.returncode)
