"""In-memory fault injection only: no runtime or native evidence file changes."""
import ast
import copy
import io
import json
from pathlib import Path
import unittest

import test_g1_key_reuse_2152 as T
import test_g1_key_reuse_original_2153 as EXTRA

REUSE = T.REUSE
source = Path(REUSE.__file__).read_text()
node = next(n for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == '_merge')
original = REUSE._merge


def run():
    stream = io.StringIO()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)
                               for m in (T, EXTRA))
    result = unittest.TextTestRunner(stream=stream).run(suite)
    return result, stream.getvalue()


control, log = run()
assert control.wasSuccessful(), log
rows = [{'control': True, 'tests': control.testsRun, 'failures': 0, 'errors': 0}]
variants = (
    ('ignore new reservations',
     'if any(lane in carry_lanes for _attempt, lane in claimed):', 'if False:'),
    ('ignore added runtime input',
     "('prompt_sha256', 'expected_input')", "('prompt_sha256',)"),
    ('ignore unproved native diagnostics', 'if problems != missing:', 'if False:'),
    ('hide new carried-task evidence',
     "if rec['attempts'] or rec['selected'] is not None or rec['relation'] is not None:",
     'if False:'),
)
try:
    text = ast.get_source_segment(source, node)
    for name, before, after in variants:
        assert text.count(before) == 1, name
        namespace = dict(REUSE.__dict__)
        exec(compile(text.replace(before, after), '<in-memory G1 reuse fault>', 'exec'), namespace)
        REUSE._merge = namespace['_merge']
        result, log = run()
        assert result.failures and not result.errors, (name, log)
        rows.append({'mutation': name, 'tests': result.testsRun,
                     'failures': len(result.failures), 'errors': len(result.errors),
                     'failed_tests': [test.id() for test, _ in result.failures]})
finally:
    REUSE._merge = original
control, log = run()
assert control.wasSuccessful(), log
print(json.dumps({'scope': 'In-memory only; native evidence proof is separate',
                  'checks': rows, 'restored_control_tests': control.testsRun}, indent=2))
