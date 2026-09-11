"""Prove completed closeouts through the original finalizer, without writes."""
from contextlib import ExitStack
import hashlib
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
run, package = base / 'review_2004', base / 'closure_2004'


def exact_existing(path, text):
    path = Path(path)
    if not path.is_file() or path.read_bytes() != text.encode('utf-8'):
        raise ValueError('completed closeout differs or is missing: %s' % path)


def no_raw_write(*args, **kwargs):
    raise ValueError('completed raw evidence is missing; read-only proof cannot recover it')


def snapshot(paths):
    return {str(p): (hashlib.sha256(p.read_bytes()).hexdigest(),
                     str(p.stat().st_mtime_ns)) for p in paths}


paths = [p for root in (run, package) for p in root.rglob('*') if p.is_file()]
attempts = (run, run / 'retry')
for attempt in attempts:
    receipt = json.loads((attempt / old.RECEIPT_NAME).read_text())
    paths.extend(Path(p) for p in receipt['states'])
before = snapshot(paths)
results = []
with ExitStack() as stack:
    for owner in (CL, CL.SK, CL.F):
        stack.enter_context(patch.object(owner, 'HR', old))
    stack.enter_context(patch.object(CL.F, '_HERE', str(old_path.parent)))
    stack.enter_context(patch.object(CL.RT, 'write_new', exact_existing))
    stack.enter_context(patch.object(CL.RT, 'save_raw', no_raw_write))
    ctx = CL._ctx()
    assert not old._package_problems(ctx, str(package))
    for attempt in attempts:
        assert (attempt / 'raw').is_dir()
        stored = json.loads((attempt / old.FINALIZATION_NAME).read_text())
        if stored['retry']:
            assert (attempt / 'retry' / old.RECEIPT_NAME).is_file()
        got = old._finalize(ctx, str(attempt), str(package))
        assert got == stored and got['primary_complete'] and not got['problems']
        results.append({'attempt': str(attempt), 'ledger': got['ledger']})
assert snapshot(paths) == before, 'original bytes or nanosecond mtimes changed'
print(json.dumps({'ok': True, 'read_only_files': len(before),
                  'attempts': results}, indent=1))
