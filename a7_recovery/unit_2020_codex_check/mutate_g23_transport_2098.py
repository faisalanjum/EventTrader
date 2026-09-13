"""In-memory batch-owner mutations, with the unmodified test as control."""
import inspect
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unit_2009/owner'))
import a4_review_composite as R
import a7_g1_build as G
import a7_g23_run as GR

suite = str(Path(__file__).with_name('test_g23_transport_2098.py'))
mutations = {
    'ignored_size_limit': ('_rows_and_prompts', 'if largest > W.SCRIPT_BYTE_LIMIT:', 'if False:'),
    'lost_second_half': ('_rows_and_prompts', 'pending.appendleft(batch[middle:])', 'pass'),
    'repeated_first_half': ('_rows_and_prompts', 'pending.appendleft(batch[middle:])', 'pending.appendleft(batch[:middle])'),
    'exact_boundary_refused': ('_rows_and_prompts', 'if largest > W.SCRIPT_BYTE_LIMIT:', 'if largest >= W.SCRIPT_BYTE_LIMIT:'),
    'stale_batch_counts': ('freeze', '("batches", len(g2_rows))', '("batches", len(g2_batches))'),
    'stale_largest_batch': ('freeze', 'max([r["items"] for r in g2_rows] or [0])', 'max([len(b) for b in g2_batches] or [0])'),
}
before = G._sha_file(GR.__file__)
assert int(pytest.main([suite, '-q', '--tb=short', '-p', 'no:cacheprovider'])) == 0
results = {}
for label, (name, old, new) in mutations.items():
    original = getattr(GR, name)
    source = inspect.getsource(original)
    assert source.count(old) == 1, label
    try:
        exec(compile(source.replace(old, new, 1), GR.__file__, 'exec'), GR.__dict__)
        status = int(pytest.main([suite, '-q', '--tb=short', '-p', 'no:cacheprovider']))
        assert status == 1, (label, 'survived or failed outside an assertion', status)
        results[label] = 'killed'
    finally:
        setattr(GR, name, original)
assert int(pytest.main([suite, '-q', '-p', 'no:cacheprovider'])) == 0
assert G._sha_file(GR.__file__) == before
out = Path(__file__).parent / os.environ['A7_TAG']
out.mkdir()
G._write_new(str(out / 'MUTATIONS.json'), G._pretty({'mutations': results,
    'restored_control': 'passed', 'source_sha256': before, 'source_unchanged': True}) + '\n')
print('ALL_TRANSPORT_MUTATIONS_KILLED', len(results), flush=True)
