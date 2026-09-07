# -*- coding: utf-8 -*-
"""The READ-ONLY preflight map (Codex SEQ 1786).

The published proposed map, with its four writable rows demoted to read-only
and freshly measured by the existing boundary owner. No published path can be
written through this map, and nothing else about it changes.
"""
import io, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a7_recovery/unit_1781"
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, L + "/launcher")
import boundary                                                  # noqa: E402

rows, demoted = [], []
for ln in io.open(P + "/a7_map_1781_proposed.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if mode == "rw":
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))
# the ONE writable row: this new unit's own logs, so no published path is written
logs = UNIT + "/logs"
os.makedirs(logs, exist_ok=True)
rows.append("\t".join(["/tmp/a7_logs_1786", logs, boundary.source_sha(logs), "rw"]))
out = UNIT + "/a7_map_1786_readonly.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("writable rows demoted to read-only: %d" % len(demoted))
for d in demoted:
    print("   ", d)
print("rows %d, writable %d"
      % (len(rows), sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw")))
