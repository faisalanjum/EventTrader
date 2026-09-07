# -*- coding: utf-8 -*-
"""This unit's bind map, derived from unit_1814's map (Codex SEQ 1820 item 1).

The finalized 471-file run is NOT copied: it is bound READ-ONLY at the same
logical run path it was proven at, so this diagnostic cannot alter a single
result byte. The ONLY writable destination is this unit's own logs, which is
where every output goes.
"""
import io, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
A = R + "/a7_recovery"
SRC = A + "/unit_1818/a7_map_1818.tsv"
UNIT = os.path.dirname(os.path.abspath(__file__))
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
RUN_LOGICAL = S + "/g1_precall_run_1525"
FINALIZED = A + "/unit_1814/out/run_1814"
LOGS = "/tmp/a7_logs_1781"
sys.path.insert(0, L + "/launcher")
import boundary                                                  # noqa: E402

rows, demoted = [], []
for ln in io.open(SRC, encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg == LOGS:
        src = UNIT + "/logs"
        os.makedirs(src, exist_ok=True)
        rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))
        continue
    if lg == RUN_LOGICAL:
        # the finalized run, bound where it was proven - read-only, not copied
        rows.append("\t".join([lg, FINALIZED, boundary.source_sha(FINALIZED), "ro"]))
        demoted.append(lg)
        continue
    if mode == "rw":
        mode, sha = "ro", boundary.source_sha(src)
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))
out = UNIT + "/a7_map_1820.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("rows %d, demoted to read-only %d, writable %d -> %s"
      % (len(rows), len(demoted),
         sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw"), out))
