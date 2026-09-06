# -*- coding: utf-8 -*-
"""The real A5.prepare publication gate, in the no-call private view (Codex 1758 step 4).

This reconstructs the approved historical prelaunch fixture under the same logical
run identity Codex SEQ 1517 named. It runs the actual gate, not import or plan(),
executes no launcher, freezes nothing, and makes no model call.
"""
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
RUN = S + "/a6_a5run_1515"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_a5_exp5_kit as A5                                # noqa: E402

WANT = {"manifest": "5e33c3e4acbff1c710321008335d6a66622992a8317027c9d231d85912f37c53",
        "bundle": "d2e850d86f643f177868b8b755b0a0d92c0a57f1aec8fabd4455acea2367edff",
        "receipt": "b468a0a19f778f48f415b210afd95dc70eb381d9b50f1c4097384be84dfedf84"}
CHECKS = []


def fsha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %-46s %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:64],
                             "" if ok else "   != %s" % str(want)[:64]), flush=True)


if os.listdir(RUN):
    raise SystemExit("REFUSED: %s already holds a prepared run" % RUN)

got = A5.prepare(RUN)
check("prepare ok", got.get("ok"), True)
check("prepare problems", list(got.get("problems") or []), [])
check("prepared manifest", fsha(RUN + "/plan/a5_exp5_reader.manifest.json"), WANT["manifest"])
check("launcher bundle", fsha(RUN + "/plan/a5_launcher.bundle.json"), WANT["bundle"])
check("initial receipt", fsha(RUN + "/receipt.json"), WANT["receipt"])

rec = json.load(io.open(RUN + "/receipt.json", encoding="utf-8"))
check("the receipt schedules the planned calls", len(rec["allowed"]), 392)
check("no state is recorded yet", len(rec.get("states") or []), 0)
check("no answers directory exists", os.path.exists(RUN + "/answers"), False)
print("run_id:", rec.get("run_id"), flush=True)

out = {"run": RUN, "run_id": rec.get("run_id"),
       "manifest_sha256": fsha(RUN + "/plan/a5_exp5_reader.manifest.json"),
       "bundle_sha256": fsha(RUN + "/plan/a5_launcher.bundle.json"),
       "receipt_sha256": fsha(RUN + "/receipt.json"),
       "allowed": len(rec["allowed"]), "states": len(rec.get("states") or []),
       "files": sum(len(f) for _r, _d, f in os.walk(RUN))}
io.open(RUN + "/A5_PREPARE_RESULT.json", "w", encoding="utf-8").write(json.dumps(out, indent=1))
print(json.dumps(out, indent=1), flush=True)

bad = [n for n, ok in CHECKS if not ok]
print("checks %d  failed %d  %s" % (len(CHECKS), len(bad), bad), flush=True)
print("A5_PREPARE_1758_DONE" if not bad else "A5_PREPARE_1758_MISMATCH", flush=True)
sys.exit(1 if bad else 0)
