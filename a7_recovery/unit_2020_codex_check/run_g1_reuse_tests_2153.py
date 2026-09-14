"""Run the affected suite using the actual recovery boundary's import paths."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_build as B
import pytest

assert G._sha_file(G.__file__) == '5523c5b6b8fdc4701730c21e5022693eab0a7f8384c81efdcddf4539e5cf1439'
assert G._sha_file(B.__file__) == '3ca73c35163fdb3c39623711b78e9f0ea3a0c6ed30fdcec943d57ca1deaac79e'
files = [HERE / name for name in ('test_g1_key_reuse_2152.py',
                                  'test_g1_key_reuse_original_2153.py',
                                  'test_g1_reuse_bindings_2153.py',
                                  'test_partial_grading_2095.py')]
files.append(HERE.parents[0] / 'unit_2152_g1_reuse/test_g1_reuse_inputs_2152.py')
print('Actual runtime owners:', G.__file__, B.__file__, flush=True)
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', '-W',
                             'ignore::ResourceWarning'] + [str(p) for p in files]))
