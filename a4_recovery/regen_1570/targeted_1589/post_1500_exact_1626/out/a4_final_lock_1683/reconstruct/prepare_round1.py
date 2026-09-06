# -*- coding: utf-8 -*-
"""Round-1 correction package and run preparation (Codex SEQ 1731/1732).

A minimal adapter: it calls the frozen owner's OWN functions in the order the existing
recon_round1 seam already establishes - build the package, preflight it, prepare the run
from the bound session store - and asserts nothing of its own. The receipts those calls
read were produced by the earlier stages and are bound read-only at their historical
paths, so no completed prerequisite is recomputed here.
"""
import hashlib, io, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT                        # noqa: E402
import inspect                                                   # noqa: E402


def era_call(fn, *args):
    """Call the owner's own function with as many of these arguments as IT takes.

    The seam is the same across the correction snapshots but the signatures are not:
    an earlier owner carries the door in the function while a later one is handed it.
    Reading the signature keeps the call the owner's, not this adapter's.
    """
    n = len(inspect.signature(fn).parameters)
    return fn(*args[:n])

RUN1 = "/tmp/a4_final_targeted_corr_run_1504"
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

print("owner   :", sha(FT.__file__)[:16], flush=True)
print("door    :", FT.CORR_DOOR, flush=True)
print("review  :", os.path.basename(FT.REVIEW_RECEIPT),
      sha(FT.REVIEW_RECEIPT)[:16] if os.path.isfile(FT.REVIEW_RECEIPT) else "MISSING", flush=True)

doc = era_call(FT.build_correction, FT.CORR_PKG_DIR, FT.CORR_DOOR)
print("build_correction ok; pkg", FT.CORR_PKG_DIR, flush=True)
man = os.path.join(FT.CORR_PKG_DIR, "manifest.json")
if os.path.isfile(man):
    print("package manifest:", sha(man), flush=True)

g = era_call(FT.correction_preflight, FT.CORR_PKG_DIR, FT.CORR_DOOR)
print("preflight ok=%s problems=%s" % (g.get("ok"), g.get("problems")), flush=True)
if not g.get("ok"):
    sys.exit(4)

got = era_call(FT.prepare_correction_run, RUN1, FT.CORR_DOOR)
print("prepare ok=%s problems=%s" % (got.get("ok"), got.get("problems")), flush=True)
if not got.get("ok"):
    sys.exit(5)
r = os.path.join(RUN1, "receipt.json")
if os.path.isfile(r):
    print("run receipt:", sha(r), flush=True)
print("PREPARE_ROUND1_OK", flush=True)
