"""Read-only feasibility check: actual old native verifier, no saved verdicts."""
from contextlib import ExitStack
import collections
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'unit_2002/owner'))
import a4_source_closure as CL

old_path = ROOT / 'unit_1997/harness_g1v3/build_kfields_hard_review.py'
spec = importlib.util.spec_from_file_location('a7_preserved_hard_review', old_path)
old = importlib.util.module_from_spec(spec)
prior_path = list(sys.path)
spec.loader.exec_module(old)
sys.path[:] = prior_path
base = Path(CL.PKG_DIR).parent
run, package = str(base / 'review_2004'), str(base / 'closure_2004')
new_sha = CL.INV.sha_file(CL.HR.__file__)
with ExitStack() as stack:
    for owner in (CL, CL.SK, CL.F):
        stack.enter_context(patch.object(owner, 'HR', old))
    stack.enter_context(patch.object(CL.F, '_HERE', str(old_path.parent)))
    context = CL._ctx()
    package_bad = old._package_problems(context, package)
    readings, problems = CL.readings(run, package)
    print(json.dumps({'old_owner_sha256': CL.INV.sha_file(old.__file__),
                      'successor_sha256': new_sha, 'package_problems': package_bad,
                      'readings_problems': problems,
                      'counts': dict(collections.Counter(v[0] for v in readings.values()))}, indent=1))
    assert not package_bad and not problems
    assert dict(collections.Counter(v[0] for v in readings.values())) == {'valid':62,'invalid_response':4}
assert CL.INV.sha_file(CL.HR.__file__) == new_sha
