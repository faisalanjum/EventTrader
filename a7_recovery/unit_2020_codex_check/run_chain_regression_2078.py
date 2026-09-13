"""Run the unchanged complete 22-test suite against the rehomed owner.

Only the legacy import name is bound to the real new module. No test, proof
owner, operation lifetime or cache behavior is changed.
"""
import hashlib
from pathlib import Path
import runpy
import sys

A7 = Path(__file__).resolve().parents[1]
owner = A7 / 'unit_2076_latest_source_decisions/a4_v6_successor_chain.py'
suite = A7 / 'unit_2072_two_event_closeout/test_v6_successor_2072.py'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(owner) == 'beed43091c4a5088f248122c3cf627ef82fd72cdbad7d9390863d1cb4ad558a7'
assert sha(suite) == '352edec87f71f7940b09724f9de210294f4201604d6179e5809d541d6e12b2bd'
sys.path.insert(0, str(owner.parent))
import a4_v6_successor_chain as X
assert Path(X.__file__).resolve() == owner
assert 'a4_v6_successor' not in sys.modules
sys.modules['a4_v6_successor'] = X
sys.argv = [str(suite)]
print('REAL_REHOMED_OWNER', str(owner), sha(owner), flush=True)
try:
    runpy.run_path(str(suite), run_name='__main__')
finally:
    assert sha(owner) == 'beed43091c4a5088f248122c3cf627ef82fd72cdbad7d9390863d1cb4ad558a7'
    assert sha(suite) == '352edec87f71f7940b09724f9de210294f4201604d6179e5809d541d6e12b2bd'
    print('OWNER_AND_UNMODIFIED_SUITE_STILL_PINNED', flush=True)
