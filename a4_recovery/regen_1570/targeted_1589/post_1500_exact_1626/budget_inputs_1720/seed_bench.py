# -*- coding: utf-8 -*-
"""Seed the private writable era bench (Codex SEQ 1715 item 1).

A private copy of the constructed bench, plus the base files the recorded chain
never writes for itself. Only one such file is needed - the scorer the route
owner imports - and it is NOT chosen by consensus: the candidate is placed and
the recorded 30-line route-stop result decides, because only the right one can
reproduce it.
"""
import hashlib, io, os, shutil, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
K = P + "/budget_inputs_1720"
UNIT = P + "/out/a4_final_lock_1683"
SEED = sys.argv[1] if len(sys.argv) > 1 else (
    P.replace("/post_1500_exact_1626", "") + "/phase1_targeted_1488/inputs/harness_g1v3/scorers/score_exp5.py")
fsha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
shutil.rmtree(K + "/bench", ignore_errors=True)
os.makedirs(K + "/bench")
shutil.copytree(UNIT + "/bench/bench_1306", K + "/bench/bench_1306")
dst = K + "/bench/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3/scorers/score_exp5.py"
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(SEED, dst)
# the run's own census records repository HEAD cd961e51 unchanged throughout, so
# the driver package of that exact base is the era's driver package. The bench
# carries only the subset the A4 final-lock path reached; this chain reaches the
# whole write path, so the base tree is seeded and every file the bench already
# had is required to be identical.
GB = (R + "/a3_recovery/regen_1541/evidence/git_bases/"
          "cd961e51d55bf13aa9311b79c5d7eca20e9b11cc/driver")
BD = K + "/bench/bench_1306/driver"
kept = 0
for dp, _dn, fn in os.walk(BD):
    for f in fn:
        b = os.path.join(dp, f)
        g = os.path.join(GB, os.path.relpath(b, BD))
        if not os.path.isfile(g) or fsha(g) != fsha(b):
            sys.exit("REFUSE: %s differs from the recorded base" % os.path.relpath(b, BD))
        kept += 1
shutil.rmtree(BD)
shutil.copytree(GB, BD)
print("driver package seeded from the recorded base: %d files (%d already matched)"
      % (sum(len(f) for _d, _s, f in os.walk(BD)), kept))

# the period resolver imports one more skills script by name; the bench already
# carries its two siblings from that exact directory, and this byte is the same
# in every durable copy. Placing it cannot itself reach a database: the private
# namespace has no network, so a live cascade fails closed rather than running.
GS = R + "/.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py"
gd = K + "/bench/bench_1306/.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py"
shutil.copyfile(GS, gd)
print("skills script seeded: guidance_write_cli.py %s" % fsha(gd)[:16])

io.open(K + "/BENCH_SEED.tsv", "w", encoding="utf-8").write(
    "seeded\tsha256\tsource\n.claude/plans/Drivers/experiments/harness_g1v3/scorers/score_exp5.py\t%s\t%s\n"
    % (fsha(dst), SEED.replace(R + "/", "")))
print("private bench: %d files; scorer seeded at %s"
      % (sum(len(f) for _d, _s, f in os.walk(K + "/bench")), fsha(dst)[:16]))
