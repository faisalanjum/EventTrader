# -*- coding: utf-8 -*-
"""The A5 bind map: the accepted A4 map with the harness swapped for the A5 view.

The A4 bench is left exactly as it is. Its harness is overlaid by the A5-era view,
so the pipeline sees the A5 packet/raw/audit owners instead of the older bases the
bench carries, and nothing else changes. The two A4-era file overlays that sit
inside that harness are dropped, because they would otherwise win over the view.
"""
import io
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
U = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683"
UNIT = os.path.dirname(os.path.abspath(__file__))
VIEW = UNIT + "/view"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
sys.path.insert(0, U + "/launcher")
import boundary                                              # noqa: E402

#: read-only overlays that make the private view the A5 era
RO = {X: VIEW + "/experiments",
      # the signed A4 lock lives in a run directory the bench does not carry, so the
      # runs directory is presented as the bench's own eleven runs plus that one
      X + "/runs": VIEW + "/runs_composed",
      # runtime-reached inputs the A5 plan pins but the bench does not carry
      S + "/bench_1306/driver/core": VIEW + "/driver_core"}
#: the drift control must mutate a frozen source byte and restore it. That subtree is
#: this unit's own disposable copy, never accepted A4 evidence, so it is bound writable
#: and re-hashed afterwards to prove nothing was left behind.
RW_VIEW = {X + "/keys": VIEW + "/experiments/keys"}
#: the build's own outputs, under the historical names the recorded build used
RW = {S + "/a5_build_a_1758": UNIT + "/out/a5_build_a_1758",
      S + "/a5_build_b_1758": UNIT + "/out/a5_build_b_1758",
      S + "/a5_candidate_1758": UNIT + "/out/a5_candidate_1758",
      # the prelaunch fixture, under the run identity Codex SEQ 1517 named
      S + "/a6_a5run_1515": UNIT + "/out/a6_a5run_1515",
      # complete raw test evidence, one named log per run
      "/tmp/a5_logs_1758": UNIT + "/logs"}

rows, dropped, frozen = [], [], []
# the ACCEPTED A4 map is the base: it is the one whose claimed bytes still match disk
# after A4's authorized bench owner swaps. Every A4 output row is demoted to read-only,
# because an A5 build must not be able to write accepted A4 evidence.
for ln in io.open(U + "/launcher/a4_final_map.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    if lg.startswith(X + "/harness_g1v3/"):
        dropped.append(lg)          # an A4-era owner inside the harness we are replacing
        continue
    if mode == "rw":
        mode, sha = "ro", boundary.source_sha(src)
        frozen.append(lg)
    rows.append("\t".join([lg, src, sha, mode]))

for lg, src in sorted(RO.items()):
    if not os.path.exists(src):
        raise SystemExit("REFUSED: missing view source %s" % src)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "ro"]))
for lg, src in sorted(RW_VIEW.items()):
    rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))
for lg, src in sorted(RW.items()):
    os.makedirs(src, exist_ok=True)
    rows.append("\t".join([lg, src, boundary.source_sha(src), "rw"]))

out = UNIT + "/a5_map_1758.tsv"
io.open(out, "w", encoding="utf-8").write("\n".join(rows) + "\n")
print("A4 output rows demoted to read-only:")
for f in frozen:
    print("   ", f.replace(S, "S"))
print("dropped A4-era harness overlays:")
for d in dropped:
    print("   ", d.replace(S, "S"))
print("added read-only view overlays:")
for lg in sorted(RO):
    print("   ", lg.replace(S, "S"))
print("added writable outputs:")
for lg in sorted(RW):
    print("   ", lg.replace(S, "S"))
print("map rows: %d -> %s" % (len(rows), out))
