# -*- coding: utf-8 -*-
"""Re-pin the unit_1881 bind map into a NEW file, reporting every moved row."""
import io, os, sys
L = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/"
     "targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
sys.path.insert(0, L)
import boundary as BD

U = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1881"
src, dst = U + "/a7_map_1881.tsv", U + "/a7_map_1881b.tsv"
rows, moved = [], []
for line in io.open(src, encoding="utf-8").read().splitlines():
    if not line.strip():
        continue
    logical, source, want, mode = line.split("\t")
    if mode == "rw":
        rows.append(line); continue
    got = BD.source_sha(source)
    if got != want:
        moved.append((logical, want[:16], got[:16]))
        line = "\t".join([logical, source, got, mode])
    rows.append(line)
io.open(dst, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("rows", len(rows), "moved", len(moved))
for m in moved:
    print("  ", m[0], m[1], "->", m[2])
