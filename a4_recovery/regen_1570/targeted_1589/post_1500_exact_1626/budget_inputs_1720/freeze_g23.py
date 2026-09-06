# -*- coding: utf-8 -*-
"""Freeze the recovered inputs and their evidence (Codex SEQ 1722/1724 item 4).

Compact by construction: the two private benches are NOT listed, because they are
rebuilt deterministically from the seed tables that ARE listed, and listing 2400
regenerable files would bury the evidence. Everything else durable in the unit is
hashed and then re-read and re-hashed, so the manifest is checked, not asserted.
"""
import hashlib, io, os

U = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/budget_inputs_1720")
SKIP = ("bench", "bench_g23", "__pycache__")
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

rows = []
for dp, dn, fn in os.walk(U):
    dn[:] = [d for d in dn if d not in SKIP]
    for f in sorted(fn):
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, U)
        if rel == "MANIFEST_g23.sha256":
            continue
        rows.append((rel, fsha(p), os.path.getsize(p)))

with io.open(U + "/MANIFEST_g23.sha256", "w", encoding="utf-8") as fh:
    fh.write("path\tsha256\tbytes\n")
    for r in sorted(rows):
        fh.write("%s\t%s\t%d\n" % r)

bad = [r[0] for r in rows if fsha(os.path.join(U, r[0])) != r[1]]
print("manifest rows: %d  re-verified: %d  mismatched: %d"
      % (len(rows), len(rows) - len(bad), len(bad)))
if bad:
    raise SystemExit("REFUSE: %s" % bad[:5])
print("MANIFEST_g23.sha256 %s" % fsha(U + "/MANIFEST_g23.sha256")[:16])
