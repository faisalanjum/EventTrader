# -*- coding: utf-8 -*-
"""Restore and prove the accepted A6 freeze (Codex SEQ 1765 items 2 and 3).

Runs the real A6 owner over the PRESERVED A5 prelaunch fixture, which is mounted
read-only, and writes the freeze into two fresh A6-only directories to show the
render is deterministic. No run is prepared, reset or modified; no JSON is edited
by hand; no model, producer or grader is executed.
"""
import collections
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
RUN = S + "/a6_a5run_1515"
OUT_A, OUT_B = "/tmp/a6_freeze_1765_a", "/tmp/a6_freeze_1765_b"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import a6_launch_freeze as A6                                 # noqa: E402
import build_a5_exp5_kit as A5                                # noqa: E402

WANT = {
    "owner": "2c666040853f611a90f368b9f2dddb1adc8879cb0abfa9fe3923c1eace07118c",
    "freeze": "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d",
    "manifest": "5e33c3e4acbff1c710321008335d6a66622992a8317027c9d231d85912f37c53",
    "bundle": "d2e850d86f643f177868b8b755b0a0d92c0a57f1aec8fabd4455acea2367edff",
    "receipt": "b468a0a19f778f48f415b210afd95dc70eb381d9b50f1c4097384be84dfedf84",
    "lock": "63018354e6b26a8061a114934df15fe035b44fe031dcf00768b440983d43b8a0",
    "lock_receipt": "7f1f7bef4d02b9c5501d9ec6d8d5b9eab5e8aab225092878b7280964bd5d44e3",
    "inventory": "1440d75131c0c7418a66821778a88d5c1ff8fd9bdf7f4cca4d561b596c1b3066",
}
CHECKS = []


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %-56s %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:58],
                             "" if ok else "  != %s" % str(want)[:58]), flush=True)


def as_int(v):
    """ledger() reports (total, provenance rows); budget reports the total directly."""
    if isinstance(v, int):
        return v
    if isinstance(v, tuple) and v and isinstance(v[0], int):
        return v[0]
    if isinstance(v, dict):
        for key in ("completed_actual", "ledger_after", "completed", "total"):
            if isinstance(v.get(key), int):
                return v[key]
    return v


check("the A6 owner in the view is the recovered one",
      fsha(H + "/a6_launch_freeze.py"), WANT["owner"])
check("the prelaunch fixture is the preserved one",
      fsha(RUN + "/receipt.json"), WANT["receipt"])
check("its manifest is the accepted one",
      fsha(RUN + "/plan/a5_exp5_reader.manifest.json"), WANT["manifest"])

doc = A6.freeze(RUN)
check("A6.problems on the accepted freeze", list(A6.problems(doc) or []), [])

# the render is written into two FRESH A6-only directories, never over a run
pa, ha = A6.write(RUN, OUT_A)
pb, hb = A6.write(RUN, OUT_B)
check("the freeze renders identically twice", ha, hb)
check("the accepted freeze identity", ha, WANT["freeze"])
check("the persisted file equals the reported identity", fsha(pa), ha)

bare = as_int(A6.ledger())
fresh = as_int(A6.ledger(RUN))
check("the bare ledger is the signed lock's closed baseline", bare, 5220)
check("the fresh run's ledger is the same closed baseline", fresh, 5220)

c = doc["counts"]
check("events", c["events"], 36)
check("packets", c["packets"], 196)
check("arms", [a["arm"] if isinstance(a, dict) else a for a in c["arms"]], ["P1", "P2"])
check("unique ordered producer calls", c["unique_ordered_calls"], 392)
check("invocations", c["invocations"], 36)

b = doc["budget"]
check("budget completed_actual", as_int(b["completed_actual"]), 5220)
check("budget planned primary", b["planned_producer_primary"], 392)
check("budget producer_primary_after", b["producer_primary_after"], 5612)
check("budget stays under the ceiling", b["under_ceiling"], True)

ba = doc["bound_artifacts"]
check("bound bundle", ba["bundle_sha256"], WANT["bundle"])
check("bound receipt", ba["receipt_sha256"], WANT["receipt"])
check("bound corrected inventory", ba["inventory_sha256"], WANT["inventory"])
check("bound A4 lock", doc["a4_lock"]["sha256"], WANT["lock"])
check("bound A4 lock receipt", doc["a4_lock"]["receipt_sha256"], WANT["lock_receipt"])
check("the lock is signed", doc["a4_lock"]["signed"], True)
check("scorer and matcher are bound",
      bool(ba["scorer_sha256"]) and bool(ba["matcher_sha256"]), True)
check("no forbidden arm is present", sorted(set(doc["absent_arms"].values())), [False])

z = doc["zeros"]
check("nothing has run: states, raw, made_calls, db writes",
      [z["states"], z["raw_replies"], z["made_calls"], z["database_writes"]], [0, 0, 0, 0])
check("not activated", z["activated"], False)

t = doc["transport"]
check("runtime is the subscription Sonnet-5 high",
      [t["runtime_model_id"], t["effort"]], ["claude-sonnet-5", "high"])

g = doc["grader"]
check("the grader inventory is honestly unarmed before A7",
      any(v in (0, None, "undetermined") for v in g.values()) if isinstance(g, dict) else None,
      True)

out = {"freeze_path": pa, "freeze_sha256": ha, "second_build": hb,
       "problems": list(A6.problems(doc) or []),
       "ledger_bare": bare, "ledger_fresh_run": fresh,
       "counts": dict(c), "budget": dict(b),
       "bound_artifacts": {k: ba[k] for k in
                           ("manifest_sha256", "bundle_sha256", "receipt_sha256",
                            "inventory_sha256", "scorer_sha256", "matcher_sha256")},
       "a4_lock": dict(doc["a4_lock"]), "zeros": dict(z), "grader": dict(g)}
io.open(OUT_A + "/A6_FREEZE_RESULT.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=1, default=str) + "\n")
print(json.dumps(out, indent=1, default=str)[:1800], flush=True)

bad = [n for n, ok in CHECKS if not ok]
print("checks %d  failed %d  %s" % (len(CHECKS), len(bad), bad), flush=True)
print("A6_FREEZE_1765_DONE" if not bad else "A6_FREEZE_1765_MISMATCH", flush=True)
sys.exit(1 if bad else 0)
