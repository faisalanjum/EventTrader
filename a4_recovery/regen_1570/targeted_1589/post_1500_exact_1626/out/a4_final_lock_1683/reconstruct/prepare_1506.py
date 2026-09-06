# ponytail: Codex SEQ 1506 item 1 - the owner preflight, then ONE fresh run from the frozen package; zero calls.
import hashlib, json, os, sys, time
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
sys.path.insert(0, S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, a6_launch_freeze as A6
RUN = "/tmp/a4_final_targeted_corr2_run_1506"; D = FT.CORR2_DOOR
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
man = os.path.join(FT.CORR2_PKG_DIR, FT.CORR_MANIFEST_NAME); pre = os.path.join(FT.CORR2_PKG_DIR, FT.CORR_PREFIX_NAME)
print("manifest", sha(man), "prefix", sha(pre), "owner", sha(FT._OWNER), flush=True)
t = time.time(); g = FT.correction_preflight(FT.CORR2_PKG_DIR, D); print("preflight ok", g["ok"], g["problems"], "%.0fs" % (time.time() - t), flush=True)
if not g["ok"]:
    print("REFUSED: preflight"); sys.exit(2)
doc = g["manifest"]; print("budget", json.dumps(doc["budget"]), flush=True); print("capacity", json.dumps(doc["capacity"]), flush=True)
t = time.time(); led = A6.ledger()[0]; print("ledger", led, "%.0fs" % (time.time() - t), flush=True)
assert led == doc["budget"]["before"], (led, doc["budget"]["before"])
assert not os.path.exists(RUN), RUN
t = time.time(); got = FT.prepare_correction_run(RUN, D); print("prepare ok", got["ok"], got["problems"], "%.0fs" % (time.time() - t), flush=True)
if not got["ok"]:
    print("REFUSED: prepare"); sys.exit(3)
by = {r["source_id"]: r for r in doc["tasks"]}
for i in got["invocations"]:
    assert i["script_sha256"] == by[i["label"]]["script_sha256"] == sha(i["scriptPath"]), i["label"]
    print("invocation", i["label"], i["attempt"], i["scriptPath"], i["script_sha256"], flush=True)
rec = json.load(open(os.path.join(RUN, "receipt.json")))
print("receipt", sha(os.path.join(RUN, "receipt.json")), "door", rec["door"], "allowed", rec["allowed"], "manifest", rec["manifest_sha256"], flush=True)
print("PREPARE_DONE", flush=True)
