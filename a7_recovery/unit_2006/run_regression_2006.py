"""Select the original qualified fixture environment; run its unchanged suite."""
import json
import os
from pathlib import Path
import runpy
from check_native_isolation_2006 import B, check as check_native

UNIT = Path(__file__).resolve().parent
GRADER = UNIT.parent / 'grader_20260909'
group = os.environ['A7_REGRESSION_GROUP']
if group == 'ordinary':
    assert check_native(B.read_map(os.environ['A7_RUN_BINDING']))
old = {'ordinary': 'ordinary_final4', 'native': 'native_final5'}[group]
report = json.loads((GRADER / 'attempts' / old / 'logs' / ('attempt_grader_' + old)
                     / ('ALIGNED_grader_' + old + '.json')).read_text())
for name in ('A7_APPROVED_KEY_DIR', 'A7_TRACE_FIXTURE', 'A7_FIXTURE_PROJECTS',
             'A7_DRIVER_VALIDATORS_SHA'):
    value = report['environment'][name]
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
os.environ.setdefault('A7_TESTS', json.dumps(report['union_modules']))
runpy.run_path(str(GRADER / 'regression.py'), run_name='__main__')
