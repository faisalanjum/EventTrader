# -*- coding: utf-8 -*-
"""Materialise ONE round's writable run directory from what the earlier stages
already preserved (Codex SEQ 1737, rounds 2 and 3).

`record_state` rewrites the run receipt in place, so the run has to be bound
WRITABLE - and the namespace keeps nothing, so the durable copy under runs_rw
is the only thing that carries a round's prepared receipt and launchers from
one attempt to the next. That copy is built here from out/, where the
preparation stage preserved exactly those files, under the same `__` = `/`
name rule the map builder already uses.

A name ending in the owner's own atomic-write suffix (`.tmp`) is the leftover
of a write that never completed, so it is never seeded as a run file.

Every copy is re-hashed, an existing differing byte is REFUSED rather than
overwritten, and a run directory that already holds a file keeps it.

Usage: seed_runs_rw.py <run_name>
"""
import hashlib
import os
import shutil
import sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = UNIT + "/out"
RW = UNIT + "/runs_rw"


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


run = sys.argv[1]
pre = run + "__"
placed, kept, problems = [], [], []

for name in sorted(os.listdir(OUT)):
    src = os.path.join(OUT, name)
    if not name.startswith(pre) or not os.path.isfile(src):
        continue
    rel = name[len(pre):].replace("__", "/")
    if rel.endswith(".tmp"):
        print("   skip (incomplete write) %s" % name)
        continue
    dst = os.path.join(RW, run, rel)
    h = fsha(src)
    if os.path.isfile(dst):
        (kept if fsha(dst) == h else problems).append(rel)
        continue
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    if fsha(dst) != h:
        problems.append(rel)
        continue
    placed.append((rel, h))

for rel, h in placed:
    print("   + %-46s %s" % (rel, h[:16]))
print("%s: placed %d  already present %d  refused %d"
      % (run, len(placed), len(kept), len(problems)))
if problems:
    for rel in problems:
        print("   REFUSE differing byte: %s" % rel)
    sys.exit(1)
