# -*- coding: utf-8 -*-
"""Put ONE era owner into the bench the projection is built from (Codex SEQ 1696 epoch rule).

A bound historical run is re-proved with the owner of ITS OWN era, and the bench is the
single place the projection reads that owner from - so the swap happens here, before the
map is built, and the map re-measures the bench row afterwards.

The wanted owner is named by its COMPLETE hash and located by hash among the proved
owners, never by a file name. Every swap is appended to BENCH_OWNER_SWAPS.tsv so the
frozen candidate says which owner each round actually ran under.

Usage: place_era_owner.py <basename> <sha256>
"""
import hashlib
import io
import os
import shutil
import sys
import time

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.dirname(os.path.dirname(UNIT))
PROVED = P + "/a4_owner_1726/proved"
BENCH = UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"

fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
name, want = sys.argv[1], sys.argv[2]
dst = os.path.join(BENCH, name)
if not os.path.isfile(dst):
    sys.exit("REFUSE: the bench carries no %s" % name)
had = fsha(dst)
if had == want:
    print("%s already at %s" % (name, want[:16]))
    raise SystemExit(0)
src = next((os.path.join(PROVED, f) for f in sorted(os.listdir(PROVED))
            if os.path.isfile(os.path.join(PROVED, f))
            and fsha(os.path.join(PROVED, f)) == want), None)
if src is None:
    sys.exit("REFUSE: no proved owner at %s" % want[:16])
shutil.copyfile(src, dst)
got = fsha(dst)
if got != want:
    sys.exit("REFUSE: the bench now holds %s" % got[:16])
row = "\t".join([time.strftime("%Y-%m-%dT%H:%M:%S"), name, had, got,
                 os.path.relpath(src, P)])
man = UNIT + "/manifest/BENCH_OWNER_SWAPS.tsv"
with io.open(man, "a" if os.path.isfile(man) else "w", encoding="utf-8") as fh:
    fh.write(row + "\n")
print("%s  %s -> %s" % (name, had[:16], got[:16]))
