"""In-memory TEST mutations of the narrow admission policy; no file is edited."""
import json
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

A7 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(A7 / 'unit_2009/owner'))
import a4_review_composite as R
import a7_partial_grading_2095 as P

source = Path(P.__file__).read_text()
suite = str(Path(__file__).with_name('test_partial_grading_2095.py'))
mutations = {
    'missing_policy_or_rule_pin': ('if pins.get(name) != G._sha_file(path):', 'if False:'),
    'ignored_evidence_problem': ('if problems != allowed:', 'if False:'),
    'unused_or_missing_attempt_accepted': ("if (lanes.get(lane) or {}).get('attempts') != exhausted:", 'if False:'),
    'third_attempt_permitted': ("if root['max_attempts'] != G.MAX_ATTEMPTS:", 'if False:'),
    'wrong_task_kind_accepted': ("if G.task_kind(doc) != 'G1':", 'if False:'),
    'unapproved_policy_scope': ('if G._sha_file(__file__) != expected_sha256:', 'if False:'),
}
results = {}
for name, (old, new) in mutations.items():
    assert source.count(old) == 1, name
    module = types.ModuleType('TEST_MUTANT_' + name)
    module.__file__ = P.__file__
    exec(compile(source.replace(old, new, 1), P.__file__, 'exec'), module.__dict__)
    with patch.object(P, 'lifecycle', module.lifecycle), patch.object(P, 'scope', module.scope):
        status = int(pytest.main([suite, '-q', '--tb=short', '-p', 'no:cacheprovider']))
    assert status == 1, (name, 'mutation survived or failed outside a test assertion', status)
    results[name] = 'killed'
assert Path(P.__file__).read_text() == source
assert int(pytest.main([suite, '-q', '-p', 'no:cacheprovider'])) == 0
out = A7 / 'unit_2020_codex_check' / os.environ['A7_TAG']
out.mkdir()
(out / 'MUTATIONS.json').write_text(json.dumps({'mutations': results, 'restored_control': 'passed',
                                               'code_bytes_unchanged': True}, indent=2) + '\n')
print('ALL_POLICY_MUTATIONS_KILLED', len(results), flush=True)
