# -*- coding: utf-8 -*-
"""Freeze and then verify one sorted manifest of the whole unit (Codex SEQ 1718).

Every regular file under budget_inputs_1720 except the manifest itself, sorted by
its unit-relative path, each with its sha256 and size. The manifest is written
and then re-read and checked line by line against the live bytes, so a row that
does not describe what is on disk fails here.
"""
import hashlib, io, os, sys
K = ("/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570/targeted_1589/"
     "post_1500_exact_1626/budget_inputs_1720")
NAME = "MANIFEST.sha256"
fsha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()

rows = []
for dp, dn, fn in os.walk(K):
    dn.sort()
    for f in sorted(fn):
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, K)
        if rel == NAME or os.path.islink(p) or not os.path.isfile(p):
            continue
        rows.append((rel, fsha(p), os.path.getsize(p)))
rows.sort()
with io.open(os.path.join(K, NAME), "w", encoding="utf-8") as fh:
    for rel, h, n in rows:
        fh.write("%s\t%d\t%s\n" % (h, n, rel))
print("manifest rows: %d" % len(rows))

bad = 0
for ln in io.open(os.path.join(K, NAME), encoding="utf-8"):
    h, n, rel = ln.rstrip("\n").split("\t", 2)
    p = os.path.join(K, rel)
    if not os.path.isfile(p) or fsha(p) != h or os.path.getsize(p) != int(n):
        print("MISMATCH %s" % rel); bad += 1
print("verified %d of %d rows against live bytes" % (len(rows) - bad, len(rows)))
print("manifest sha256: %s" % fsha(os.path.join(K, NAME)))
sys.exit(1 if bad else 0)
