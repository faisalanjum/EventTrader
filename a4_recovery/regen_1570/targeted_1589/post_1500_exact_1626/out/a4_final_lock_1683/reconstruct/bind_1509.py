# ponytail: Codex SEQ 1510 item 1 - re-prove the exact hashes he named, dry-run the binding proof against a scratch
# binding, then bind run 1509 ONCE + pointer, then the ledger. Refuses on any mismatch before writing.
import hashlib, io, json, os, subprocess, sys, time
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, build_kfields_final as F, raw_transport as RT, a6_launch_freeze as A6
RUN = "/tmp/a4_final_targeted_corr3_run_1509"; PY = "/home/faisal/EventMarketDB/venv/bin/python3"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
HIS = {"receipt": "268f55910d888ced32895f4ed3337146090dc66137f408f11d80e8b136cde1dd",
       "finalization": "603be212f3320a21c74ebedd44a16bb8495b8c2a2e17c128d3cb3c050ffa2fc9",
       "raw_tree": "6438b015564c8f504511e0619caebb8a1d8f85a7e12dd8b0c8ee22d04b442ef1"}
assert sha(RUN + "/receipt.json") == HIS["receipt"], "RECEIPT MISMATCH"
assert sha(RUN + "/finalization.json") == HIS["finalization"], "FINALIZATION MISMATCH"
assert F.raw_tree(RUN)["sha256"] == HIS["raw_tree"], "RAW TREE MISMATCH"
fin = json.load(open(RUN + "/finalization.json"))
assert (fin["budget"]["ledger_before"], fin["budget"]["ledger_after"]) == (5217, 5219) and fin["ledger"]["scheduled"] == 2 and fin["retry"] == []
ev = lambda sub: subprocess.run([PY, "-B", S + "/evidence_1509.py", sub], capture_output=True, text=True, cwd="/home/faisal/EventMarketDB").stdout.strip()
assert ev("completed") == "2" and ev("agents") == "2" and ev("tools") == "0" and ev("reads") == "0" and ev("mid") == "4", "STATE/TRANSCRIPT EVIDENCE MISMATCH"
modelset = json.loads(ev("modelset")); assert dict((k, v) for k, v in modelset) == {"agentType:lean-probe": 2, "effort:high": 2, "meta:sonnet": 2, "result:sonnet": 2, "state_default:claude-fable-5": 2, "transcript:claude-sonnet-5": 4}, modelset
print("HIS HASHES HOLD: receipt, finalization, raw tree; 2 completed states, 2 agents, 0 tools, 0 Read, sonnet/high/lean-probe x2, claude-sonnet-5 x4, budget 5217 -> 5219", flush=True)
real = FT.CORR3_BINDING; scratch = S + "/scratch_corr3_binding_dryrun.json"
if os.path.exists(scratch): os.remove(scratch)
FT.CORR3_BINDING = scratch
t = time.time(); FT.write_binding(RUN, FT.CORR3_PKG_DIR, FT.CORR3_DOOR)
rows = FT.proved_spend(RUN, FT.CORR3_DOOR); print("DRY-RUN proved:", json.dumps(rows), "%.1fs" % (time.time() - t), flush=True)
sh, rw = FT.bound_shards(FT.CORR3_DOOR); print("dry-run bound shards:", [(k[-6:], len(v["open_issues"])) for k, v in sh.items()], flush=True)
os.remove(scratch); FT.CORR3_BINDING = real
assert not os.path.exists(real), "the real binding already exists"
FT.write_binding(RUN, FT.CORR3_PKG_DIR, FT.CORR3_DOOR)
RT.write_new(S + "/final_targeted_corr3_dir.txt", RUN + "\n")
print("BINDING", real, sha(real)); print("POINTER", S + "/final_targeted_corr3_dir.txt", sha(S + "/final_targeted_corr3_dir.txt"), flush=True)
FT._bound_cached.cache_clear()
rows = FT.proved_spend(RUN, FT.CORR3_DOOR); print("REAL proved:", json.dumps(rows), flush=True)
t = time.time(); total, led = A6.ledger(); print("LEDGER", total, "%.1fs" % (time.time() - t))
for r in led: print("  ", r["stage"], r["calls"], r.get("run_dir"))
print("BIND_DONE")
