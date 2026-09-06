# -*- coding: utf-8 -*-
"""Read the A6 ledger in a FRESH process after a round's binding exists (SEQ 1734/1737).

Read-only. The binding, its pointer and the run were written by the previous stage; this
asks the ledger owner what it counts now that they are on disk BEFORE it is imported, so
a total that differs only because the owner was imported first is told apart from a real
accounting difference.

The rounds are not listed here: the wrapper's own CORRECTION_DOORS names them, and each
door's binding path comes from the wrapper's own phase table. The expected total is an
input (A4_LEDGER) and it is a GATE - a zero return code without that exact count is a
failure, not a pass.
"""
import hashlib, io, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

want = os.environ.get("A4_LEDGER")
if not want:
    sys.exit("REFUSE: A4_LEDGER (the expected total) was not given")

import build_kfields_final_targeted as FT                        # noqa: E402
print("ft owner:", sha(FT.__file__)[:16], flush=True)
for d in FT.CORRECTION_DOORS:
    b = FT._phase(d)["binding"]
    print("%-34s %s" % (d, sha(b)[:16] if os.path.isfile(b) else "ABSENT"), flush=True)

import a6_launch_freeze as A6                                    # noqa: E402
print("a6 owner:", sha(A6.__file__)[:16], flush=True)
total, rows = A6.ledger()
print("LEDGER", total, flush=True)
for r in rows:
    print("   %-32s %s" % (r.get("stage"), r.get("calls")), flush=True)
if total != int(want):
    sys.exit("REFUSE: the ledger counts %s, not the expected %s" % (total, want))
print("LEDGER_OK", total)
