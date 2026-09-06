# -*- coding: utf-8 -*-
"""Point the map's ledger-owner row at the recovered era (Codex SEQ 1737)."""
import io, sys
p = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/out/a4_final_lock_1683/tests/build_1501_map.py")
s = io.open(p, encoding="utf-8").read()
if "a6_round1_7081e9a5" in s:
    print("already pointed at the recovered era")
    raise SystemExit
i = s.find("# DIAGNOSTIC ONLY, and never silently:")
j = s.find('io.open(UNIT + "/launcher/a4_final_map.tsv", "w", encoding="utf-8")')
if i == -1 or j == -1 or j < i:
    sys.exit("REFUSE: the map builder does not have the expected shape")
s = s[:i] + '''# THE LEDGER OWNER OF THE CORRECTION ROUNDS. The accepted map pins the base whose ledger
# has no correction stage at all, so the row is repointed at that base plus the two
# literal substitutions its own saved patch makes.
A6_LOGICAL = (S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
                  "/a6_launch_freeze.py")
A6_SRC = P + "/a4_owner_1726/proved/a6_round1_7081e9a5.py"
A6_SHA = "7081e9a51a94ca43ea8fee281711337fd8674fe19e1501bd2fca7246a5bddd74"
got = boundary.source_sha(A6_SRC)
if got != A6_SHA:
    raise SystemExit("REFUSE: the recovered ledger owner is %s" % got[:16])
hit = [k for k, r in enumerate(rows) if r.split("\\t")[0] == A6_LOGICAL]
if len(hit) != 1:
    raise SystemExit("REFUSE: %d ledger-owner rows in the map" % len(hit))
rows[hit[0]] = "\\t".join([A6_LOGICAL, A6_SRC, got, "ro"])
print("   RO  harness_g1v3/a6_launch_freeze.py <- %s" % got[:16])

''' + s[j:]
io.open(p, "w", encoding="utf-8").write(s)
print("map builder now selects the recovered ledger owner")
