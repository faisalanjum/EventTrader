"""Audit EVERY branch row against the ONE declared fault registry.

Codex SEQ 1555 point 4. The previous audit re-derived each patch by parsing the case
bodies, so a patch it could not parse or evaluate was scored WEAK - an unmeasured
credit dressed as a result, 25 of them. There is no second patch table now: the row
names a mutation, `mutations.FAULTS` owns it, and the case control applies the same
entry.

Per row, one measurement and no other outcome:
  STRONG   the named test passes unmodified, and fails by AssertionError under the
           exact declared fault - through its own unchanged assertion
  CONTROL  an ordinary byte/pin control with a stated reason and no mutation
  FALSE    the test still passes under the fault
  ERROR    no such test, no declared fault, the test fails unmodified, an unsupported
           fixture, or a failure by any exception OTHER than AssertionError
"""
import contextlib
import importlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
sys.path.insert(0, R)
sys.path.insert(0, os.path.join(R, "tests"))
import chrono_replay as CR                                     # noqa: E402,F401
import replay_transcript as RT                                 # noqa: E402,F401
import branch_inventory as BI                                  # noqa: E402,F401
import mutations as MU                                         # noqa: E402
import replay_caches                                           # noqa: E402
from _pytest.monkeypatch import MonkeyPatch                     # noqa: E402

tests = {}
for f in sorted(os.listdir(os.path.join(R, "tests"))):
    if f.startswith("test_") and f.endswith(".py"):
        try:
            tests[f] = importlib.import_module(f[:-3])
        except Exception as exc:                               # noqa: BLE001
            print("MODULE ERROR %s: %s" % (f, exc))


def run_test(fn):
    """Run a named test, supplying the simple fixtures it declares.

    A test my runner could not call was previously reported as an error, which is how
    three report-boundary rows went unmeasured. `monkeypatch` and `tmp_path` are the
    only fixtures these controls use.
    """
    import pathlib
    import shutil
    import tempfile
    names = fn.__code__.co_varnames[:fn.__code__.co_argcount]
    mp = MonkeyPatch() if "monkeypatch" in names else None
    tmp = tempfile.mkdtemp(prefix="audit_") if "tmp_path" in names else None
    if set(names) - {"monkeypatch", "tmp_path", "emitted"}:
        return "UNSUPPORTED-FIXTURE"
    args = []
    for n in names:
        if n == "monkeypatch":
            args.append(mp)
        elif n == "tmp_path":
            args.append(pathlib.Path(tmp))
        elif n == "emitted":
            # build the module's own fixture rather than skipping the row: an
            # unmeasurable row is how three report-boundary credits went unchecked
            mod = sys.modules[fn.__module__]
            fixture = getattr(mod, "emitted")
            raw = getattr(fixture, "__wrapped__", None) or \
                getattr(getattr(fixture, "_pytestfixturefunction", None), "func", None)
            if raw is None:
                return "UNSUPPORTED-FIXTURE"
            fmp = MonkeyPatch()
            ftmp = tempfile.mkdtemp(prefix="audit_fx_")
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    args.append(raw(pathlib.Path(ftmp), fmp))
            finally:
                fmp.undo()
                shutil.rmtree(ftmp, ignore_errors=True)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            fn(*args)
        return None
    except Exception as exc:                                   # noqa: BLE001
        return type(exc).__name__
    except BaseException as exc:                               # noqa: BLE001
        # pytest's OWN outcomes are BaseException subclasses: `pytest.raises` that did
        # not raise, or `pytest.fail`, is the test's own assertion failing, not a
        # harness error; interrupts still propagate
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return "AssertionError" if type(exc).__name__ == "Failed" else type(exc).__name__
    finally:
        if mp:
            mp.undo()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


# ZERO STATE DRIFT, measured rather than asserted: the exact contents of every
# discovered replay cache before the first row and after the last. Codex SEQ 1556
# item 4 requires this, and an unmeasured claim of isolation is what the fences were
# built to replace.
def _contents(obj):
    if isinstance(obj, dict):
        return dict(obj)
    if isinstance(obj, set):
        return sorted(obj, key=repr)      # a set has no order; a list of one is a trap
    return list(obj)


# warmed before the first fence for the same reason the case runner warms it: a fence
# that hands back an EMPTY ledger cache makes every row re-parse the frozen prefix
RT.result_ledger()

_before_state = {name: _contents(obj)
                 for _m, name, obj in replay_caches.caches([CR, RT])}

report = json.load(open(os.path.join(R, "reports", "branch_inventory.json")))
totals = {"STRONG": 0, "CONTROL": 0, "FALSE": 0, "ERROR": 0, "rows": 0}
lines = []
for row in report["branches"]:
    totals["rows"] += 1
    branch, mut, test = row["branch"], row["mutation"], row["test"]
    fn = next((getattr(m, test) for m in tests.values() if hasattr(m, test)), None)
    if fn is None:
        totals["ERROR"] += 1
        lines.append("ERROR   %-40s no such test %s" % (branch[:40], test))
        continue
    # every base/fault pair runs inside the same fence the case harness uses: one
    # shared process is only an isolated measurement if each row hands back the caches
    # it was given (Codex SEQ 1556 item 1)
    with replay_caches.preserved(CR, RT):
        base = run_test(fn)
    if base is not None:
        totals["ERROR"] += 1
        lines.append("ERROR   %-40s fails unmodified (%s)" % (branch[:40], base))
        continue
    if row.get("control_only"):
        totals["CONTROL"] += 1
        lines.append("CONTROL %-40s %s" % (branch[:40], row["control_only"][:44]))
        continue
    if mut not in MU.FAULTS:
        totals["ERROR"] += 1
        lines.append("ERROR   %-40s no declared fault for %r" % (branch[:40], mut))
        continue
    with replay_caches.preserved(CR, RT), MU.FAULTS[mut].applied(True):
        under = run_test(fn)
    if under is None:
        totals["FALSE"] += 1
        lines.append("FALSE   %-40s test still passes under %s" % (branch[:40], mut[:26]))
    elif under != "AssertionError":
        totals["ERROR"] += 1
        lines.append("ERROR   %-40s fails by %s, not its assertion" % (branch[:40], under))
    else:
        totals["STRONG"] += 1
        lines.append("STRONG  %-40s <- %s" % (branch[:40], mut[:30]))

for l in lines:
    print(l)
print()
print("rows %(rows)d | STRONG %(STRONG)d | CONTROL %(CONTROL)d | FALSE %(FALSE)d | "
      "ERROR %(ERROR)d" % totals)
_after_state = {name: _contents(obj)
                for _m, name, obj in replay_caches.caches([CR, RT])}
drift = sorted(n for n in _before_state
               if _before_state[n] != _after_state.get(n, object()))
print("STATE DRIFT across the whole audit: %d %s" % (len(drift), drift))
import audit_verdict                                             # noqa: E402
_status = audit_verdict.verdict(totals, drift)
print("ACCEPTABLE" if _status == 0 else "NOT ACCEPTABLE")
# REFUSE, do not report: printing the failure and exiting zero let the ordered runner
# treat a failed audit as a passed step and freeze the package anyway.
raise SystemExit(_status)
