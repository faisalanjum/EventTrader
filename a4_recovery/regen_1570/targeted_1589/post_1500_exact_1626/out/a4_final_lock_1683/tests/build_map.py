# -*- coding: utf-8 -*-
"""Derive the private-namespace bind map from the durable projection.

The logical scratch root S stays a writable tmpfs, because the correction-round
owners legitimately WRITE their new bindings and pointers into it. Every
RECOVERED input is bound read-only on top of that root, one declared and
hash-pinned row per entry, so a recovered byte can never be modified while the
reconstruction's own outputs remain possible.

Rows are derived from what the projection actually contains - never hand-listed -
so a newly projected input cannot be silently left unbound.
"""
import io
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
UNIT = (R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
            "/out/a4_final_lock_1683")
L = UNIT + "/launcher"
sys.path.insert(0, L)
import boundary                                          # noqa: E402

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
EV = UNIT + "/evidence"

rows = []                                                # (logical, source, mode)

# 1. every recovered entry at the logical S root, except the bench mountpoint
#    (bench is bound separately below) - one row per entry, ro.
for name in sorted(os.listdir(EV)):
    if name == "bench_1306":
        continue
    rows.append((S + "/" + name, os.path.join(EV, name), "ro"))

# 2. the constructed bench tree at its logical path
rows.append((S + "/bench_1306", UNIT + "/bench/bench_1306", "ro"))

# 3. the session store at the hardcoded PROJECTS_ROOT the owners read
rows.append(("/home/faisal/.claude/projects", UNIT + "/session_store/projects", "ro"))

# 4. any reconstructed logical run directory, and any separate launch directory
#    a receipt names, each at its exact historical /tmp name
#    An entry may be a pointer to evidence already proved elsewhere in the
#    recovery worktree, so the row records the REAL durable path: the map then
#    names the exact bytes that are bound, never an indirection.
for base in (UNIT + "/runs", UNIT + "/launch", UNIT + "/tmpfiles"):
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            rows.append(("/tmp/" + name,
                         os.path.realpath(os.path.join(base, name)), "ro"))

missing = [(lg, src) for lg, src, _m in rows if not os.path.exists(src)]
if missing:
    for lg, src in missing:
        print("MISSING projection source for %s: %s" % (lg, src))
    sys.exit(1)

with io.open(L + "/recon_map.tsv", "w", encoding="utf-8") as fh:
    for lg, src, mode in rows:
        fh.write("%s\t%s\t%s\t%s\n" % (lg, src, boundary.source_sha(src), mode))

print("bind rows: %d" % len(rows))
for lg, _src, _m in rows:
    print("   %s" % lg.replace(S, "S"))
