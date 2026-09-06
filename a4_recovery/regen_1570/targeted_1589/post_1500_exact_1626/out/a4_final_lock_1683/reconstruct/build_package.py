# -*- coding: utf-8 -*-
"""Build ONE correction round's package through the owner's own builder (SEQ 1737).

The saved preflight/prepare script for a later round expects its package to exist; round 1
built its own through the owner and the later rounds need the same call. The round is an
input and the package directory is the owner's constant for it.
"""
import hashlib, inspect, io, os, sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT                        # noqa: E402

ROUND = os.environ.get("A4_ROUND", "1")
DOOR = getattr(FT, "CORR_DOOR" if ROUND == "1" else "CORR%s_DOOR" % ROUND)
PKG = getattr(FT, "CORR_PKG_DIR" if ROUND == "1" else "CORR%s_PKG_DIR" % ROUND)
sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def era_call(fn, *args):
    """As many arguments as the owner's own function takes."""
    return fn(*args[:len(inspect.signature(fn).parameters)])


print("round %s door %s" % (ROUND, DOOR), flush=True)
print("owner  %s" % sha(FT.__file__)[:16], flush=True)
if os.path.isdir(PKG) and os.listdir(PKG):
    print("package already present at", PKG, flush=True)
else:
    era_call(FT.build_correction, PKG, DOOR)
    print("build_correction ok", flush=True)
for f in sorted(os.listdir(PKG)):
    print("   %-44s %s" % (f, sha(os.path.join(PKG, f))), flush=True)
print("BUILD_PACKAGE_OK", flush=True)
