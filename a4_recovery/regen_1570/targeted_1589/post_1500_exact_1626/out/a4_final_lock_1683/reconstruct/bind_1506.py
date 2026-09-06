# ponytail: bind the finalized correction run ONCE (Codex SEQ 1505 item 1): dry-run the whole
# proof against a scratch binding first, then write the real binding + pointer, then the ledger.
import hashlib, io, json, os, sys, time
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final_targeted as FT, raw_transport as RT, a6_launch_freeze as A6
RUN = "/tmp/a4_final_targeted_corr2_run_1506"
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
real = FT.CORR2_BINDING
scratch = S + "/scratch_corr2_binding_dryrun.json"
if os.path.exists(scratch): os.remove(scratch)
FT.CORR2_BINDING = scratch
t = time.time(); FT.write_binding(RUN, FT.CORR2_PKG_DIR, FT.CORR2_DOOR)
rows = FT.proved_spend(RUN, FT.CORR2_DOOR)
print("DRY-RUN proved:", json.dumps(rows), "%.1fs" % (time.time() - t))
sh, rw = FT.bound_shards(FT.CORR2_DOOR); print("dry-run bound shards:", [(k[-6:], len(v["open_issues"])) for k, v in sh.items()])
os.remove(scratch)
FT.CORR2_BINDING = real
assert not os.path.exists(real), "the real binding already exists"
doc = FT.write_binding(RUN, FT.CORR2_PKG_DIR, FT.CORR2_DOOR)
RT.write_new(S + "/final_targeted_corr2_dir.txt", RUN + "\n")
print("BINDING", real, sha(real)); print("POINTER", S + "/final_targeted_corr2_dir.txt", sha(S + "/final_targeted_corr2_dir.txt"))
FT._bound_cached.cache_clear()
rows = FT.proved_spend(RUN, FT.CORR2_DOOR); print("REAL proved:", json.dumps(rows))
t = time.time(); total, led = A6.ledger(); print("LEDGER", total, "%.1fs" % (time.time() - t))
for r in led: print("  ", r["stage"], r["calls"], r.get("run_dir"))
