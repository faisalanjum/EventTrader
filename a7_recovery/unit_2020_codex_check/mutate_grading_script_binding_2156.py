"""Four in-memory fault controls; the published module is never edited."""
import io
from pathlib import Path
import types
import unittest

import test_grading_script_binding_2156 as TEST

original = TEST.T
source = Path(original.__file__).read_text(encoding='utf-8')
faults = {
    'unapproved_code_or_binding': (
        'if pins.get(name) != G._sha_file(filename):', 'if False:'),
    'changed_evidence': ('if G._sha_file(filename) != expected:', 'if False:'),
    'unrelated_run_rebound': ("if state_path != record['state_path']:", 'if False:'),
    'native_failure_hidden': (
        "return native(state_path, dict(expected, script_path=record['executed_script_path']))",
        "return [], native(state_path, dict(expected, script_path=record['executed_script_path']))[1]"),
}

for name, (old, new) in faults.items():
    assert source.count(old) == 1, name
    mutant = types.ModuleType('fault_' + name)
    mutant.__file__ = original.__file__
    exec(compile(source.replace(old, new), original.__file__, 'exec'), mutant.__dict__)
    TEST.T = mutant
    try:
        result = unittest.TextTestRunner(stream=io.StringIO()).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(TEST.ScriptBinding))
        assert result.failures and not result.errors, (name, result.failures, result.errors)
        print(name, 'CAUGHT', len(result.failures), 'assertion failures', flush=True)
    finally:
        TEST.T = original

result = unittest.TextTestRunner().run(
    unittest.defaultTestLoader.loadTestsFromTestCase(TEST.ScriptBinding))
assert result.wasSuccessful()
print('Restored controls PASS; no runtime source was edited.', flush=True)
