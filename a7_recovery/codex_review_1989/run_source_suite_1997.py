"""Reuse the existing source-key suite on the successor owner.

Only fixture configuration changes: the preparation tests start undeclared,
and their TEST role now supplies both model fields. No test assertion or proof
implementation is replaced here. Runtime fixtures stay in the boundary tmpfs.
"""
import importlib.util
import os
import sys
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1997/owner")
import a4_source_key as S

path = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1995/owner/test_a4_source_key.py"
spec = importlib.util.spec_from_file_location("source_suite", path)
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)
assert suite.SK is S
suite.OWNER = os.path.dirname(S.__file__)
real_declare = suite.declare


def declare(kind, alias, runtime=None, **over):
    over.setdefault("workflow_row_model", runtime or "TEST-independent-runtime")
    return real_declare(kind, alias, runtime, **over)


suite.declare = declare
original = S.KEY_ROLE_FILE
S.KEY_ROLE_FILE = "/tmp/TEST_source_key_role_absent_codex1997.json"
assert not os.path.exists(S.KEY_ROLE_FILE)
try:
    result = suite.main()
finally:
    S.KEY_ROLE_FILE = original
raise SystemExit(result)
