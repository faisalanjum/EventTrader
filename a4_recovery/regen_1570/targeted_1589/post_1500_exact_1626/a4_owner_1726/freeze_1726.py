# -*- coding: utf-8 -*-
"""One checked manifest for the later-era owner recovery unit (Codex SEQ 1726)."""
import hashlib, io, os
A = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589"
     "/post_1500_exact_1626/a4_owner_1726")
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
rows = []
for dp, dn, fn in os.walk(A):
    dn[:] = [d for d in dn if d != "__pycache__"]
    for f in sorted(fn):
        rel = os.path.relpath(os.path.join(dp, f), A)
        if rel != "MANIFEST_1726.sha256":
            rows.append((rel, fsha(os.path.join(A, rel)), os.path.getsize(os.path.join(A, rel))))
with io.open(A + "/MANIFEST_1726.sha256", "w", encoding="utf-8") as fh:
    fh.write("path\tsha256\tbytes\n")
    for r in sorted(rows):
        fh.write("%s\t%s\t%d\n" % r)
bad = [r[0] for r in rows if fsha(os.path.join(A, r[0])) != r[1]]
print("manifest rows %d, re-verified %d, mismatched %d" % (len(rows), len(rows) - len(bad), len(bad)))
print("MANIFEST_1726.sha256 %s" % fsha(A + "/MANIFEST_1726.sha256")[:16])
