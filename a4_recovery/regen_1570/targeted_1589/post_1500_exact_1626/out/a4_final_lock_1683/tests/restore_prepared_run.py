# -*- coding: utf-8 -*-
"""Restore the completed round-1 PREPARATION without rerunning it (Codex SEQ 1734).

The preparation succeeded; only the recording that followed was wrong. Its receipt is the
retained one with the recorded states removed - the sole difference - so the prepared copy
is rebuilt from that evidence and REQUIRED to be the identity the original preparation
produced. The failed-order receipt and finalization are never overwritten; the restored
run is a fresh view beside them.
"""
import hashlib, io, json, os, shutil, sys

UNIT = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
        "/post_1500_exact_1626/out/a4_final_lock_1683")
OUT, KEPT = UNIT + "/out", UNIT + "/failed_order"
RUN = UNIT + "/runs_rw/a4_final_targeted_corr_run_1504"
PREFIX = "a4_final_targeted_corr_run_1504__"
WAS = "54f7e6f4ac6e91f2a4dd4e41917b0dfb10947a5117a6a40ba00712861be2c1e0"
WANT = "06ae95caf416d2c9fb8f1f4255d047d42259f24df4de2faa2e162a5c277939ca"
WANT_BYTES = 4526
sha = lambda b: hashlib.sha256(b).hexdigest()

src = KEPT + "/receipt_54f7e6f4.json"
raw = io.open(src, "rb").read()
if sha(raw) != WAS:
    sys.exit("REFUSE: the retained receipt is %s, not the one the reviewer read" % sha(raw)[:16])
doc = json.loads(raw.decode("utf-8"))
n = len(doc.get("states") or [])
doc["states"] = []
body = json.dumps(doc, indent=1)
if sha(body.encode()) != WANT or len(body.encode()) != WANT_BYTES:
    sys.exit("REFUSE: removing the %d recorded states gives %s at %d bytes, not the "
             "completed preparation" % (n, sha(body.encode())[:16], len(body.encode())))

shutil.rmtree(RUN, ignore_errors=True)
os.makedirs(RUN)
copied = 0
for f in sorted(os.listdir(OUT)):
    if not f.startswith(PREFIX) or f.endswith("__receipt.json") \
            or f.endswith("__finalization.json"):
        continue
    rel = f[len(PREFIX):].replace("__", "/")
    d = os.path.join(RUN, rel)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(os.path.join(OUT, f), d)
    copied += 1
io.open(RUN + "/receipt.json", "w", encoding="utf-8").write(body)
got = sha(io.open(RUN + "/receipt.json", "rb").read())
if got != WANT:
    sys.exit("REFUSE: the restored receipt is %s" % got[:16])
if os.path.exists(RUN + "/finalization.json"):
    sys.exit("REFUSE: a finalization is present in a prepared run")
print("restored prepared run: receipt %s -> %s, %d bytes, %d other files, %d states removed"
      % (WAS[:16], got[:16], len(body.encode()), copied, n))
print("retained failed-order evidence untouched:",
      sha(io.open(KEPT + "/receipt_54f7e6f4.json", "rb").read())[:16],
      sha(io.open(KEPT + "/finalization_66ce479c.json", "rb").read())[:16])
