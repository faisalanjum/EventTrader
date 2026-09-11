"""TEST-only gate composition: a run-level error must remain a signing stop.

Simulates an adjudicated key and proved readings at the two input boundaries;
then invokes the REAL closure and F.signing_gate. No real key or evidence is
changed and no model/signature call occurs. The positive uses the same inputs
without the test run-level error. This is not source-truth qualification.
"""
import collections
import copy
import hashlib
import json
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2000/owner")
import a4_source_closure as CL

with open(CL.__file__, "rb") as source:
    before = hashlib.sha256(source.read()).hexdigest()
shards, raws = CL._initial()
labels = CL.required_readings()
cleared = collections.OrderedDict(
    (sid, dict(copy.deepcopy(shard), open_issues=[]))
    for sid, shard in shards.items())
got = {label: ("valid", "", "TEST-only proved reading") for label in labels}
names = ("_initial", "required_readings", "readings")
saved = {name: getattr(CL, name) for name in names}
error = "TEST-only duplicate workflow: run-level proof error"
results = []
try:
    CL._initial = lambda: (cleared, raws)
    CL.required_readings = lambda: list(labels)
    for problems in ([], [error], []):
        CL.readings = lambda *_a, _problems=problems, **_kw: (got, _problems)
        gate = CL.signing_checks("TEST-no-real-run")
        results.append({"supplied_run_problems": problems,
                        "ok": gate["ok"], "stops": gate["stops"],
                        "reading_problems": gate["reading_problems"]})
finally:
    for name, value in saved.items():
        setattr(CL, name, value)
assert all(getattr(CL, name) is value for name, value in saved.items())
with open(CL.__file__, "rb") as source:
    after = hashlib.sha256(source.read()).hexdigest()
assert before == after, "candidate moved during test"
assert results[0]["ok"] is True and results[2]["ok"] is True, results
print(json.dumps({"test_only": True, "closure_owner_sha256": before,
                  "real_F_signing_gate_used": True, "positive_controls_pass": True,
                  "results": results,
                  "required_error_blocks": results[1]["ok"] is False,
                  "source_truth_or_real_signature": False}, indent=1))
