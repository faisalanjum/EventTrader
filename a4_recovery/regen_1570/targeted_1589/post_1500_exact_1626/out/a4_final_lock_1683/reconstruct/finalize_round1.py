# -*- coding: utf-8 -*-
"""Record the saved answers into the round-1 correction run and finalize it (SEQ 1732).

The step the existing seam skipped: it went from preparing the run straight to binding,
so the run was never finalized and the binding had nothing to bind. This calls the frozen
owner's OWN finalize on the prepared run and reports what it produced; it invents no
total and asserts no acceptance of its own.
"""
import hashlib, io, json, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT                        # noqa: E402

#: which correction round this stage serves; the door and the run directory are the
#: owner's own constants for it, never named here
ROUND = os.environ.get("A4_ROUND", "1")
DOOR = getattr(FT, "CORR_DOOR" if ROUND == "1" else "CORR%s_DOOR" % ROUND)
RUN = {"1": "/tmp/a4_final_targeted_corr_run_1504",
       "2": "/tmp/a4_final_targeted_corr2_run_1506",
       "3": "/tmp/a4_final_targeted_corr3_run_1509"}[ROUND]
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
print("owner   :", sha(FT.__file__)[:16], flush=True)
print("run     :", RUN, "receipt", sha(RUN + "/receipt.json")[:16], flush=True)
for d in ("raw", "answers", "scripts", "states"):
    p = os.path.join(RUN, d)
    print("  %-8s %s" % (d, len(os.listdir(p)) if os.path.isdir(p) else "-"), flush=True)

out = FT.finalize(RUN)
print("finalize keys:", sorted(out)[:12], flush=True)
for k in ("ledger", "attempt", "retry", "outcomes"):
    if k in out:
        print("  %-9s %s" % (k, json.dumps(out[k])[:200]), flush=True)
f = os.path.join(RUN, "finalization.json")
if os.path.isfile(f):
    print("finalization:", sha(f), os.path.getsize(f), "bytes", flush=True)
print("FINALIZE_ROUND1_OK", flush=True)
