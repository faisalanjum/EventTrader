"""Read-only positive, failure and removed-binding tests over a saved TEST run."""
import contextlib
import hashlib
import json
import os
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2002/owner")
import a4_source_closure as CL

F, SK = CL.F, CL.SK
base = os.path.dirname(CL.PKG_DIR)
tag = os.environ.get("A7_SAVED_TAG", "codex_final2002_qualified")
review = os.path.join(base, "review_" + tag)
review_pkg = os.path.join(base, "closure_pkg_" + tag)
final = os.path.join(base, "final_" + tag)
final_pkg = os.path.join(base, "final_pkg_" + tag)
initial_scope, initial_reader = SK._scope, SK.read_shard
expected = [t["source_id"] for t in SK.tasks()]
readings, problems = CL.readings(review, review_pkg)
assert not problems and all(v[0] == "valid" for v in readings.values())
cases = []


def check(name, ok, detail=None):
    cases.append({"case": name, "ok": bool(ok), "detail": detail})


def positive():
    with CL.final_scope(review, review_pkg):
        doc = SK.resume_plan(final, package=final_pkg)
        accepted, _raws, bad = SK.accepted_shards(final, package=final_pkg)
        ready = SK.preflight(final_pkg)
    return (doc["served"] == expected and not doc["owed"]
            and not doc["problems"] and not bad
            and list(accepted) == expected and ready["ok"])


check("positive before failures", positive())

# Remove each of the two required connections separately. The real reader
# and resume checks must detect either historical defect, with no fake gate.
with CL.final_scope(review, review_pkg):
    correct = SK._scope
    SK._scope = initial_scope
    try:
        shards, _raws, bad = SK.accepted_shards(final, package=final_pkg)
        check("mutation/removing finalizer scope loses accepted answers",
              list(shards) != expected and bool(bad), len(shards))
    finally:
        SK._scope = correct
with CL.final_scope(review, review_pkg):
    correct = SK.read_shard
    SK.read_shard = initial_reader
    try:
        resumed = SK.resume_plan(final, package=final_pkg)
        check("mutation/removing resume reader loses completed answers",
              resumed["served"] != expected and bool(resumed["owed"]),
              len(resumed["served"]))
    finally:
        SK.read_shard = correct

# A run-level fault alone must block the stage even with every row valid.
original = CL.readings
first = next(iter(readings))
try:
    for state in ("missing", "invalid_response", "unproved", "waiting"):
        altered = dict(readings)
        altered[first] = (state, "TEST boundary result", None)
        CL.readings = lambda *_a, _data=altered, **_k: (_data, [])
        refused = ""
        try:
            with CL.final_scope(review, review_pkg):
                pass
        except ValueError as exc:
            refused = str(exc)
        check("failure/%s reading prevents final publication" % state,
              first in refused and state in refused)
    CL.readings = lambda *_a, **_k: (readings, ["TEST run-level duplicate"])
    try:
        with CL.final_scope(review, review_pkg):
            refused = ""
    except ValueError as exc:
        refused = str(exc)
    check("failure/run-level error blocks despite all valid rows",
          "TEST run-level duplicate" in refused)
finally:
    CL.readings = original

good_gate = CL.signing_checks(review, review_pkg, key_run=final,
                              key_package=final_pkg)
wrong_gate = CL.signing_checks(review, review_pkg, key_run=final,
                               key_package=SK.PKG_DIR)
check("positive/exact final package signs", good_gate["ok"])
check("failure/the initial package cannot approve a final key",
      wrong_gate["ok"] is False, wrong_gate.get("stops"))

# Every borrowed function and model identity restores on normal and exceptional
# exit. Include the new binding names, not just the historical subset.
owners = (SK, F, CL.K, CL.HR)
saved = {(m.__name__, n): v for m in owners for n, v in vars(m).items()
         if callable(v) or n in ("MODEL", "RUNTIME_MODEL_ID", "ROW_MODEL_ID",
                                "EFFORT", "PAYLOAD_KEYS")}
try:
    with CL.final_scope(review, review_pkg, bind_role=True):
        raise RuntimeError("TEST scope exit")
except RuntimeError as exc:
    assert str(exc) == "TEST scope exit"
modules = {m.__name__: m for m in owners}
changed = ["%s.%s" % key for key, value in saved.items()
           if getattr(modules[key[0]], key[1]) is not value]
check("scope restores after an exception", not changed, changed)
check("positive after failures", positive())
print(json.dumps({"test_only": True, "cases": cases,
                  "passed": sum(c["ok"] for c in cases), "total": len(cases),
                  "model_calls": 0}, indent=1))
raise SystemExit(0 if all(c["ok"] for c in cases) else 3)
