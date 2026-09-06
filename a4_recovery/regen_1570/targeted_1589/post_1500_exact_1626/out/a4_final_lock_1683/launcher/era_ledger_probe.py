"""Rederive the era A6 ledger from its own inputs, with provenance (Codex 1712 item 2).
Read-only; nothing is typed and no total is substituted."""
import json, os, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
HV = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
os.chdir(HV); sys.path.insert(0, HV)
import a6_launch_freeze as A6
total, rows = A6.ledger()
print("LEDGER TOTAL %d" % total)
for r in rows:
    print("  %-26s calls %4s  %s" % (r.get("stage"), r.get("calls"),
                                     (r.get("run_dir") or r.get("owner") or "")[-52:]))
print("rows %d  sum %d" % (len(rows), sum(int(r.get("calls") or 0) for r in rows)))
