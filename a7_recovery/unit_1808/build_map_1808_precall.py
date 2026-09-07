# -*- coding: utf-8 -*-
"""Read-only preflight map, derived from unit_1803's map (Codex SEQ 1805).

Both of that unit's own writable rows are demoted to freshly hashed read-only
rows, so no earlier byte can be written. The ONLY writable row is this new
unit's logs. The composed views and published owners are reused BY REFERENCE
and nothing is composed again.
"""
import io, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
SRC = R + "/a7_recovery/unit_1806/a7_map_1806.tsv"
UNIT = os.path.dirname(os.path.abspath(__file__))
L = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
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
        demoted.append(lg)
        continue
    if mode == "rw":
        mode, sha = "ro", boundary.source_sha(src)      # fresh hash, existing owner
        demoted.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))
out = UNIT + "/a7_map_1808_precall.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("rows %d, demoted %d, writable %d -> %s"
      % (len(rows), len(demoted),
         sum(1 for r in rows if r.rsplit("\t", 1)[1] == "rw"), out))
