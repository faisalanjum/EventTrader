# -*- coding: utf-8 -*-
"""Place ONE era byte into the private harness_g1v2 at a RECORDED pin.

Usage: place_g1v2.py <harness_rel_path> <sha256> <where_the_pin_is_recorded>

One acceptance rule, no fallback: the caller names the pin that the frozen
record itself states, and a durable copy is accepted only when its bytes hash
to exactly that. No basename agreement, no "nothing disagrees", no guessing a
location - a byte with no recorded pin is not placed at all.
"""
import hashlib, io, os, shutil, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
U = P + "/budget_inputs_1720"
#: which era harness this byte belongs to; the chain spans two of them
HARNESS = os.environ.get("HARNESS", "harness_g1v2")
DST = U + "/bench/bench_1306/.claude/plans/Drivers/experiments/" + HARNESS
ROOTS = [P + "/inputs/owners", P + "/inputs",
         P + "/out/v3_import_closure_1668/owners",
         P.replace("/post_1500_exact_1626", "") + "/phase1_targeted_1488",
         R + "/a3_recovery/regen_1541/bench/.claude/plans/Drivers/experiments",
         R + "/a4_recovery/regen_1570/foundation/a3/bench/.claude/plans/Drivers/experiments",
         "/home/faisal/.core827_backups/recovery_1531",
         R, "/home/faisal/.core827_backups"]

rel, pin, source_of_pin = sys.argv[1], sys.argv[2], sys.argv[3]
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

hit = None
for root in ROOTS:
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
    sys.exit("ABSENT: no durable byte hashes %s (wanted for %s)" % (pin[:16], rel))

dst = os.path.join(DST, rel)
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(hit, dst)
if fsha(dst) != pin:
    sys.exit("REFUSE: placed copy does not re-hash to the pin")
with io.open(U + "/G1V2_SEED.tsv", "a", encoding="utf-8") as fh:
    fh.write("%s/%s\t%s\t%s\tpin recorded at %s\n"
             % (HARNESS, rel, pin, hit.replace(R + "/", "").replace("/home/faisal/", "~/"), source_of_pin))
print("placed %-30s %s  <- %s" % (rel, pin[:16], hit.replace(R + "/", "")))
