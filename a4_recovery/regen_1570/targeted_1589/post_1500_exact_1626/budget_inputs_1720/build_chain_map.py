# -*- coding: utf-8 -*-
"""The replay map for the recorded key-ledger chain (Codex SEQ 1715 item 1).

Two rule-based differences from the projection map, no hand editing:
  * the historical run views are dropped - these generators build their own /tmp
    artifacts, and a read-only view of one would refuse their writes;
  * the bench is a PRIVATE WRITABLE COPY, because the recorded generators write
    their own era owner bytes into the harness. The preserved read-only tree is
    never the write target.
"""
import io, os, re, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
UNIT = P + "/out/a4_final_lock_1683"
K = P + "/budget_inputs_1720"
sys.path.insert(0, UNIT + "/launcher")
import boundary                                          # noqa: E402
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
out = []
for ln in io.open(UNIT + "/launcher/recon_map.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if re.match(r"^/tmp/a[467]_", lg):
        continue
    if lg == S + "/bench_1306":
        src, mode = K + "/bench/bench_1306", "rw"
        sha = boundary.source_sha(src)
    out.append("\t".join([lg, src, sha, mode]))
io.open(UNIT + "/launcher/budget_chain_map.tsv", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("chain map rows: %d" % len(out))
for l in out:
    c = l.split("\t")
    if c[3] == "rw":
        print("   WRITABLE %s <- %s" % (c[0].replace(S, "S"), c[1].replace(P + "/", "")))
