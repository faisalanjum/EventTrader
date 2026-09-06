# -*- coding: utf-8 -*-
"""The A6 bind map: the accepted A5 map, read-only, with the A6 owner overlaid.

The A5 unit is published, so every row that A5 kept writable is demoted to
read-only here - A6 must not be able to write published bytes, least of all the
preserved prelaunch fixture it reads. The only additions are the recovered A6
owner over the A5 view's older incidental copy, and A6's own fresh output mounts.
"""
import io
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
A5 = R + "/a5_recovery/unit_1758"
U = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
UNIT = os.path.dirname(os.path.abspath(__file__))
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
sys.path.insert(0, U + "/launcher")
import boundary                                              # noqa: E402

#: the recovered owner, selected only inside A6's private view
#: the A6 harness view: the published A5 view harness, with the recovered A6 owner and
#: the six A6/A7 suites the recorded affected command names. A file cannot be bound into
#: a read-only directory mount, so the smallest workable unit is this one directory.
RO = {X + "/harness_g1v3": UNIT + "/view/harness_g1v3",
      # the already recovered and PUBLISHED reference document, reused where its owner
      # names it. Bound read-only straight from the published tree - never copied or
      # regenerated. Its host basename preserves the logical /tmp prefix as tmp__.
      "/tmp/a7_reference_inventory.json":
          R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/budget_inputs_1720/"
              "out_g23/tmp__a7_reference_inventory.json"}
#: A6's own outputs, in fresh A6-only durable directories
RW = {"/tmp/a6_freeze_1765_a": UNIT + "/out/freeze_a",
      "/tmp/a6_freeze_1765_b": UNIT + "/out/freeze_b",
      "/tmp/a6_logs_1765": UNIT + "/logs"}

rows, demoted = [], []
for ln in io.open(A5 + "/a5_map_1758.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg in RO:
        continue                                   # replaced by the recovered owner below
    if mode == "rw":
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))

for lg, src in sorted(RO.items()):
    if not os.path.exists(src):
        raise SystemExit("REFUSED: missing A6 view source at %s" % src)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))
for lg, src in sorted(RW.items()):
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))

out = UNIT + "/a6_map_1765.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("published A5 rows demoted to read-only: %d" % len(demoted))
for d in demoted:
    print("   ", d.replace(S, "S"))
print("A6 owner overlaid read-only:")
for lg in sorted(RO):
    print("   ", lg.replace(S, "S"))
print("A6-only writable outputs:")
for lg in sorted(RW):
    print("   ", lg)
n_rw = sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw")
print("map rows: %d  (%d writable, all A6-only) -> %s" % (len(rows), n_rw, out))
