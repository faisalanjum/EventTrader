# -*- coding: utf-8 -*-
"""Prove the accepted budget_inputs_1720 unit is exactly its manifest (Codex SEQ 1726).

Both directions: every manifested path still hashes to its recorded value, and the unit
carries no file the manifest does not list. The two private benches are excluded exactly
as the manifest excludes them.
"""
import hashlib, io, os, sys
U = os.environ.get("PRIOR_UNIT") or ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/budget_inputs_1720")
man = {l.split("\t")[0]: l.split("\t")[1]
       for l in io.open(U + "/MANIFEST_g23.sha256", encoding="utf-8").read().splitlines()[1:]}
bad, extra = [], []
for dp, dn, fn in os.walk(U):
    dn[:] = [d for d in dn if d not in ("bench", "bench_g23", "__pycache__")]
    for f in fn:
        rel = os.path.relpath(os.path.join(dp, f), U)
        if rel == "MANIFEST_g23.sha256":
            continue
        if rel not in man:
            extra.append(rel)
        elif hashlib.sha256(io.open(os.path.join(U, rel), "rb").read()).hexdigest() != man[rel]:
            bad.append(rel)
# A manifested file that was DELETED is invisible to a walk of what still exists, so the
# listed paths are checked for presence too - the direction the walk cannot see.
missing = [rel for rel in man if not os.path.isfile(os.path.join(U, rel))]
print("rows %d mismatched %d extra %d missing %d"
      % (len(man), len(bad), len(extra), len(missing)))
for rel in (bad + extra + missing)[:5]:
    print("   problem: %s" % rel)
sys.exit(1 if (bad or extra or missing) else 0)
