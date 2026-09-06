# -*- coding: utf-8 -*-
"""Seed the era harness_g1v2 the 64861/64992 writers run inside (Codex SEQ 1720).

The g1v2 directory is a copy of the frozen harness plus a recorded edit chain,
so nothing here is chosen by agreement: every owner the recorded root result
pins is placed AT THAT PIN and refused otherwise. The build owner is not on
disk anywhere - it is the epoch-2 endpoint of the already-proved three-epoch
derivation, republished by that same engine and checked against the same pin.

The backup's own `.__UNKNOWN__` names mark bytes it could not verify; no owner
reads such a name, and unverified bytes do not belong in an evidence tree, so
they are dropped and counted.
"""
import hashlib, io, os, shutil

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
U = P + "/budget_inputs_1720"
MB = ("/home/faisal/.core827_backups/recovery_1531/model/tmp/claude-1000"
      "/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
      "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v2")
DST = U + "/bench/bench_1306/.claude/plans/Drivers/experiments/harness_g1v2"
OWN = P + "/inputs/owners"

fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

# every owner the recorded 64998 result pins, and where its exact byte comes from
PLACE = {
    "a7_g1_build.py":      (U + "/owner_derive/a7_g1_build.g1v2.py",
                            "f308259b74a245d3402f4e8dc9d45e930ee2754736ef6367cc9bb8635594de8d"),
    "raw_transport.py":    (OWN + "/raw_transport_64429e5f.py",
                            "64429e5fb59d19b63bbabe4af8809177755c3822a400e976532c579e15d77df5"),
    "audit_worker_access.py": (OWN + "/audit_worker_access_40639f42.py",
                            "40639f42a7150d397c25d2984278376afa1a4eb6a5921f063fa4140e0334ef3e"),
}
# owners the backup already carries at the pin; placing them would prove nothing
CARRIED = {
    "a7_g1_complete_v2.py":  "33daa5d75f1ceb9ae0b75d1d39d8b2d898756a46b42004766c60699a16070a23",
    "a7_g1_workflow_gate.py": "e2386da5f64260acdc7da1a1b44c40c3fcad5a624affd3755b01448ce32d0703",
    "scorers/score_exp5.py": "2901f1a615e988af30eba07d18e70bb5ad0473b52de6c537847f1bf3912b3a90",
    "scorers/grade_batch.js": "806a7560002a14ed5f3a4c79a78d85be0fac8abf773f8fdf9457c3d902e8abd6",
}

shutil.rmtree(DST, ignore_errors=True)
shutil.copytree(MB, DST)
dropped = 0
for dp, _dn, fn in os.walk(DST):
    for f in fn:
        if f.endswith(".__UNKNOWN__"):
            os.remove(os.path.join(dp, f)); dropped += 1

rows = []
for rel, (src, pin) in sorted(PLACE.items()):
    if fsha(src) != pin:
        raise SystemExit("REFUSE: source %s is %s, not the pin" % (src, fsha(src)[:16]))
    dst = os.path.join(DST, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != pin:
        raise SystemExit("REFUSE: placed %s does not re-hash to its pin" % rel)
    rows.append((rel, pin, src.replace(R + "/", "").replace("/home/faisal/", "~/")))
for rel, pin in sorted(CARRIED.items()):
    got = fsha(os.path.join(DST, rel))
    if got != pin:
        raise SystemExit("REFUSE: carried %s is %s, not the pin" % (rel, got[:16]))
    rows.append((rel, pin, "carried by the backup copy"))

LIVE = "/home/faisal/EventMarketDB/.claude/agents/lean-probe.md"
rows.append(("lean_probe_agent (live, read-only bind)", fsha(LIVE), LIVE))

with io.open(U + "/G1V2_SEED.tsv", "w", encoding="utf-8") as fh:
    fh.write("harness_rel\tsha256\tsource\n")
    for r in rows:
        fh.write("%s\t%s\t%s\n" % r)
        print("%-42s %s" % (r[0], r[1][:16]))
print("harness_g1v2 seeded: %d files (%d unverified names dropped)"
      % (sum(len(f) for _d, _s, f in os.walk(DST)), dropped))
