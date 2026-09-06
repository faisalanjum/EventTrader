# -*- coding: utf-8 -*-
"""Re-prove one bound historical run under its own era owner closure
(Codex SEQ 1696 item 2).

`PROVE_TARGET` selects the run. The era closure is supplied by the BOUNDARY as
read-only per-file binds over the bench, so this payload never edits an owner
and never swaps a module in process: the final owners on disk are untouched and
are automatically back in force the moment the namespace exits, error or not.

Reports each owner's resolved identity so the closure that actually proved the
run is recorded, not assumed.
"""
import hashlib
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
TARGET = os.environ["PROVE_TARGET"]                    # targeted | hard_review

sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_key_targeted as T                          # noqa: E402
import build_kfields_hard_review_targeted as HRT                # noqa: E402
import a6_launch_freeze as A6                                   # noqa: E402


def ident(mod):
    f = getattr(mod, "__file__", None)
    if not f or not os.path.isfile(f):
        return "(no file)"
    return hashlib.sha256(open(f, "rb").read()).hexdigest()[:16]


print("closure in force:")
for name, mod in (("build_kfields_key_targeted", T),
                  ("build_kfields_hard_review_targeted", HRT),
                  ("a6_launch_freeze", A6)):
    print("   %-38s %s" % (name, ident(mod)))

if TARGET == "targeted":
    run, owner, fn = "/tmp/a4_targeted_run_1491", "T.proved_spend", T.proved_spend
elif TARGET == "hard_review":
    run, owner, fn = "/tmp/a4_hard_review_run_1495", "HRT.proved_spend", HRT.proved_spend
else:
    print("unknown PROVE_TARGET %r" % TARGET)
    sys.exit(2)

print("proving %s via %s" % (run, owner))
try:
    rows = fn(run)
except BaseException as exc:                                    # noqa: BLE001
    print("REFUSED: %s: %s" % (type(exc).__name__, str(exc)[:600]))
    sys.exit(1)
print("PROVED %s -> %r" % (TARGET, rows))
sys.exit(0)
