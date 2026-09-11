"""Complete live source-binding failure inventory, plus existing scope regressions.

All keys are preserved TEST fixtures. Only test outputs are written, no model
calls occur, and no pinned input, runtime state or existing test is changed.
"""
import json
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

UNIT = Path(__file__).resolve().parent
sys.path.insert(0, str(UNIT / 'owner'))
import a4_source_candidate as SC
CL, C = SC.CL, SC.C
out = UNIT / ('TEST_' + os.environ['A7_TAG'])
out.mkdir()
base = Path(CL.PKG_DIR).parent
review, review_pkg, key_run, key_pkg = (str(base / n) for n in (
    'review_codex_final2002_qualified', 'closure_pkg_codex_final2002_qualified',
    'final_codex_final2002_qualified', 'final_pkg_codex_final2002_qualified'))
bound = CL.SK.bound(key_run, key_pkg)
fields = ('package', 'evidence', 'hr', 'events', 'hr_package')
offered = {f: getattr(bound, f) for f in fields}
ordinary = out / 'ordinary_bound.json'
CL.RT.write_new(str(ordinary), json.dumps(offered))
C.ORDINARY = str(ordinary)
checks = []
bindings_owner = C.ordinary_bindings


def check(name, ok):
    checks.append({'check': name, 'ok': bool(ok)})
    assert ok, name


def scope():
    return SC.candidate_scope(review, review_pkg, key_run, key_pkg)


def positive():
    with scope():
        return C.ordinary_bindings(C._ordinary_bound())


runs, bindings = positive()
check('positive full binding inventory', len(bindings) > len(runs))
for field in fields:
    bad = dict(offered, **{field: str(out / ('wrong_' + field))})
    path = out / ('wrong_' + field + '.json')
    CL.RT.write_new(str(path), json.dumps(bad))
    with patch.object(C, 'ORDINARY', str(path)):
        try:
            with scope():
                raise AssertionError('wrong ' + field + ' admitted')
        except ValueError as exc:
            check('wrong ordinary identity refuses: ' + field, 'exact source-only key' in str(exc))
    check('positive restored after identity mutation: ' + field, positive() == (runs, bindings))

with patch.object(C, 'ORDINARY', ''):
    try:
        with scope():
            raise AssertionError('absent ordinary binding admitted')
    except ValueError as exc:
        check('missing ordinary binding refuses', 'requires its ordinary binding' in str(exc))
check('positive restored after absent ordinary binding', positive() == (runs, bindings))

# Derive the entire required file inventory from the actual successful owner.
# Simulate one missing readable artifact at a time, without deleting evidence.
shaf = CL.INV.sha_file
for name, row in bindings.items():
    def missing(path, target=row['path']):
        if path == target:
            raise FileNotFoundError('TEST unavailable artifact: ' + target)
        return shaf(path)
    with patch.object(CL.INV, 'sha_file', side_effect=missing):
        try:
            with scope():
                raise AssertionError('missing ' + name + ' admitted')
        except (FileNotFoundError, ValueError):
            check('missing required artifact refuses: ' + name, True)
    check('positive restored after missing artifact: ' + name, positive() == (runs, bindings))

owners = (CL.SK, CL.F, CL.K, CL.HR, C)
before = {(m.__name__, n): v for m in owners for n, v in vars(m).items()
          if callable(v) or n in ('MODEL', 'RUNTIME_MODEL_ID', 'ROW_MODEL_ID', 'EFFORT')}
try:
    with scope():
        raise RuntimeError('TEST downstream operation failed')
except RuntimeError as exc:
    check('caller failure is propagated', str(exc) == 'TEST downstream operation failed')
modules = {m.__name__: m for m in owners}
check('all borrowed owners and role fields restore after caller failure',
      all(getattr(modules[m], n) is v for (m, n), v in before.items()))
check('source binding owner restores after every case', C.ordinary_bindings is bindings_owner)
check('final positive after complete failure inventory', positive() == (runs, bindings))

# Full existing regression suites for the exact final_scope and package
# boundaries composed by the new adapter, executed unchanged with new C loaded.
regressions = []
for name in ('check_final_scope_2002.py', 'check_packet_2002.py'):
    try:
        runpy.run_path(str(UNIT.parent / 'unit_2002/ledger' / name), run_name='__main__')
    except SystemExit as exc:
        assert exc.code == 0, (name, exc.code)
    regressions.append(name)
check('new binding owner survives complete existing scope/package regressions',
      C.ordinary_bindings is bindings_owner and positive() == (runs, bindings))

CL.RT.write_new(str(out / 'TEST_RESULT.json'), json.dumps({
    'kind': 'TEST ONLY; no model calls or source-truth approval',
    'model_calls': 0, 'checks': checks, 'passed': len(checks),
    'required_binding_inventory': bindings, 'unchanged_regression_suites': regressions,
}, indent=1))
print('TEST SOURCE SCOPE', len(checks), 'checks passed plus existing 12+17 regressions')
