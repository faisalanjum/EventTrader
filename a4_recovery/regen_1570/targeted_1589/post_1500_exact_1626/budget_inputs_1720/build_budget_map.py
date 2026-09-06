# -*- coding: utf-8 -*-
"""The replay map for the recorded G1-root / G2-G3 chain (Codex SEQ 1720).

Same two rules as the key-ledger map, with one addition the recorded writers
force: the two historical runs these generators READ - the producer run and the
G1 run3 whose 26 finalizations carry the prior-call budget - stay bound
read-only, while every /tmp path the chain WRITES is dropped, because the root
writer asserts its own run directory does not yet exist.
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
#: read inputs of the recorded chain - the run the candidate grades, and the
#: prior G1 run its budget counts
KEEP = {"/tmp/a6_prepared_run", "/tmp/a7_g1_run3",
        # the recovered v9 key ledger and corrected key the era key owner reads
        "/tmp/a7_key_v9_correction.json", "/tmp/a7_key_v9_gold.json"}
out = []
for ln in io.open(UNIT + "/launcher/recon_map.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if re.match(r"^/tmp/a[467]_", lg) and lg not in KEEP:
        continue
    if lg == S + "/bench_1306":
        src, mode = K + "/bench/bench_1306", "rw"
        sha = boundary.source_sha(src)
    out.append("\t".join([lg, src, sha, mode]))
#: bench-external era inputs the recorded owners read by absolute path. Each
#: is bound read-only at the pin the frozen record states for it.
EXTRA = [(S + "/a5_evidence/frozen_exp5_kit.manifest.json",
          P + "/inputs/frozen_exp5_kit.manifest.json",
          "bf9323bc3bdc75a4")]
for lg, src, short in EXTRA:
    got = boundary.source_sha(src)
    if not got.startswith(short):
        raise SystemExit("REFUSE: %s is %s, not the pin %s" % (lg, got[:16], short))
    out.append("\t".join([lg, src, got, "ro"]))
    print("   RO       %s <- %s" % (lg.replace(S, "S"), src.replace(P + "/", "")))
io.open(UNIT + "/launcher/budget_g1_map.tsv", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("map rows: %d" % len(out))
for l in out:
    c = l.split("\t")
    if c[3] == "rw" or c[0] in KEEP:
        print("   %-8s %s <- %s" % (c[3].upper(), c[0].replace(S, "S"), c[1].replace(P + "/", "")))
