# -*- coding: utf-8 -*-
"""Round-1 correction reconstruction (validation) INSIDE the private namespace.
Proves: session bind resolves, prepare_correction_run reads the bound session
store (zero calls), and the round-1 binding regenerates to its historical hash."""
import os, sys, subprocess, hashlib, json
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
REC = os.environ["RECON_DIR"]          # durable unit/reconstruct (scripts), visible via /home
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def run(script):
    r = subprocess.run([sys.executable, "-B", os.path.join(REC, script)], capture_output=True, text=True,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    print("=== %s rc=%s ===" % (script, r.returncode))
    print((r.stdout or "")[-1500:]);  print((r.stderr or "")[-1500:] if r.returncode else "", flush=True)
    return r.returncode
RUN1 = "/tmp/a4_final_targeted_corr_run_1504"
# 1) review receipt (round 1)
if run("review_receipt_1502.py"): print("STOP at review_receipt_1502"); sys.exit(2)
print("review_receipt_1502 done; EVIDENCE has receipt:", os.path.isfile(os.path.join(FT.K.EVIDENCE, "a4_final_review_receipt_1502.json")), flush=True)
# 1b) the round-1 budget receipt, through its authoritative generator
if run("budget_receipt_1501.py"): print("STOP at budget_receipt_1501"); sys.exit(7)

# 2) build round-1 package via the frozen owner FT (generic)
try:
    doc = FT.build_correction(FT.CORR_PKG_DIR, FT.CORR_DOOR)
    print("build_correction ok; pkg", FT.CORR_PKG_DIR, flush=True)
except SystemExit as e: print("build_correction SystemExit:", e); sys.exit(3)
except Exception as e:
    import traceback
    print("build_correction FAIL:", repr(e)[:300])
    print("  missing path:", getattr(e, "filename", None))
    print(traceback.format_exc()[-1200:])
    sys.exit(3)
# 3) preflight
g = FT.correction_preflight(FT.CORR_PKG_DIR, FT.CORR_DOOR)
print("preflight ok=%s problems=%s" % (g.get("ok"), g.get("problems")), flush=True)
if not g.get("ok"): sys.exit(4)
# 4) prepare the run from the bound session store (zero calls)
got = FT.prepare_correction_run(RUN1, FT.CORR_DOOR)
print("prepare ok=%s problems=%s" % (got.get("ok"), got.get("problems")), flush=True)
if not got.get("ok"): sys.exit(5)
# 5) bind round 1
if run("bind_1504.py"): print("STOP at bind_1504"); sys.exit(6)
binding = FT.CORR_BINDING
print("CORR_BINDING sha:", sha(binding)[:16], "(want b1f516f6)", flush=True)
print("ROUND1_OK" if sha(binding).startswith("b1f516f6") else "ROUND1_HASH_MISMATCH", flush=True)
