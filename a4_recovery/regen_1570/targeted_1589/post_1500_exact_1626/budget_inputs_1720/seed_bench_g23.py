# -*- coding: utf-8 -*-
"""A FRESH private writable bench for the final G2/G3 writer (Codex SEQ 1722 item 3).

Built from the frozen bench, never from the partially mutated stopped one, and then
carrying exactly the era source bytes recovered from the record - each placed at the
hash the recovery produced and re-hashed after the copy. The G1 owner epoch this
writer runs beside is the one the proved recovery owner republished.
"""
import hashlib, io, os, shutil

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
U = P + "/budget_inputs_1720"
SRC = U + "/sources_g23"
FROZEN = P + "/out/a4_final_lock_1683/bench/bench_1306"
BENCH = U + "/bench_g23/bench_1306"
V3 = BENCH + "/.claude/plans/Drivers/experiments/harness_g1v3"
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

shutil.rmtree(U + "/bench_g23", ignore_errors=True)
os.makedirs(U + "/bench_g23")
shutil.copytree(FROZEN, BENCH)

# the driver package of the era's recorded repository base, as the v9 bench seeds it
GB = (R + "/a3_recovery/regen_1541/evidence/git_bases/"
          "cd961e51d55bf13aa9311b79c5d7eca20e9b11cc/driver")
shutil.rmtree(BENCH + "/driver", ignore_errors=True)
shutil.copytree(GB, BENCH + "/driver")
GS = R + "/.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py"
gd = BENCH + "/.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py"
os.makedirs(os.path.dirname(gd), exist_ok=True)
shutil.copyfile(GS, gd)

rows = []
for dp, _dn, fn in os.walk(SRC):
    for f in sorted(fn):
        if f == "SOURCE_OPS.tsv":
            continue
        s = os.path.join(dp, f)
        rel = os.path.relpath(s, SRC)
        d = os.path.join(V3, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copyfile(s, d)
        if fsha(d) != fsha(s):
            raise SystemExit("REFUSE: %s did not survive the copy" % rel)
        rows.append(("harness_g1v3/" + rel, fsha(d), "recovered era source"))

# THE A5/A6 OWNERS THIS WRITER ACTUALLY IMPORTS, AT THEIR PRE-WRITER EPOCH.
# The bench copies are later bytes: the A6 locked-rows path and its final-A4-lock
# rewrite are August 26 and 29 operations, and this writer ran on August 25, so they
# cannot be its inputs. Each is placed at the LAST value the record states before the
# writer, and refused at anything else.
ERA = [("a6_launch_freeze.py",
        "bf82339907b97bb781d1f5bd47c95d42468527fb96ee56d320c1c70f36843848"),
       ("build_a5_exp5_kit.py",
        "53386d2cb85642f69878fda5b40d8001423f568bae08c7c482f59c5bf8a441b2"),
       ("scorers/grade_batch.js",
        "806a7560002a14ed5f3a4c79a78d85be0fac8abf773f8fdf9457c3d902e8abd6")]
for rel, pin in ERA:
    hit = None
    for root in (P + "/inputs", "/home/faisal/.core827_backups", R):
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                c = os.path.join(dp, f)
                try:
                    if os.path.getsize(c) and fsha(c) == pin:
                        hit = c
                        break
                except OSError:
                    continue
            if hit:
                break
        if hit:
            break
    if hit is None:
        raise SystemExit("REFUSE: no durable byte hashes %s for %s" % (pin[:16], rel))
    os.makedirs(os.path.dirname(V3 + "/" + rel), exist_ok=True)
    shutil.copyfile(hit, V3 + "/" + rel)
    if fsha(V3 + "/" + rel) != pin:
        raise SystemExit("REFUSE: %s is not at its pin after the copy" % rel)
    rows.append(("harness_g1v3/" + rel, pin, "last recorded value before writer 69853"))

# the G1 owner epoch this writer imports, from the proved recovery owner
OWNER = ("a7_g1_build.py", U + "/owner_derive/a7_g1_build.g23.py",
         "48d8b32812e9e799d9d550174a2c7a4a7b2febb70aa814e2eb390ccd23d71d5d")
shutil.copyfile(OWNER[1], V3 + "/" + OWNER[0])
if fsha(V3 + "/" + OWNER[0]) != OWNER[2]:
    raise SystemExit("REFUSE: the G1 owner epoch is not at its pin")
rows.append(("harness_g1v3/" + OWNER[0], OWNER[2], "proved recovery owner, epoch-3 step 69830"))

with io.open(U + "/BENCH_G23_SEED.tsv", "w", encoding="utf-8") as fh:
    fh.write("bench_rel\tsha256\tsource\n")
    for r in rows:
        fh.write("%s\t%s\t%s\n" % r)
        print("%-42s %s" % (r[0], r[1][:16]))
print("fresh bench: %d files" % sum(len(f) for _d, _s, f in os.walk(U + "/bench_g23")))
