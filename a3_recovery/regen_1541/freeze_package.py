#!/usr/bin/env python3
"""Freeze ONE self-verifying manifest over the whole executable package (SEQ 1543).

The previous split was not a package: a top manifest that verified only itself, a bench
manifest whose paths were relative to the wrong root so it could not verify at all, and
a runtime that reached outside through a symlink into the dirty main checkout. One
manifest now covers every file the package needs, recorded relative to the package root
so `--verify` works from anywhere.

Symlinks are recorded as their TARGET rather than followed, because a link is part of
the package's shape: a link that later points somewhere else is a different package even
if the bytes it reaches are identical.

`--verify` re-measures everything from disk and reports the first mismatch. Nothing is
written outside this directory.
"""
import hashlib
import io
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
NAME = "PACKAGE_MANIFEST.tsv"
#: caches and working notes are byproducts, not package content
# the sibling cache IS manifested: after the chain it holds only entries recomputed from
# the fixed inputs under a key bound to them, and a future resume must reproduce them
SKIP_DIRS = {"logs", "__pycache__", ".pt", ".pytest_tmp"}
#: `reports/tests.json` is the TRANSCRIPT of a verification run, not package
#: content: the run that writes it contains the test that verifies this
#: manifest, so manifesting it makes the manifest unverifiable by
#: construction. Every other report is written before the freeze.
SKIP_NAMES = {NAME, "tests.json"}


def entries():
    """-> sorted [(kind, relpath, value)] for every file and symlink in the package."""
    out = []
    for dp, dirs, files in os.walk(R):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if f in SKIP_NAMES or f.endswith(".pyc"):
                continue
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, R)
            if os.path.islink(fp):
                out.append(("link", rel, os.readlink(fp)))
            else:
                out.append(("file", rel,
                            hashlib.sha256(io.open(fp, "rb").read()).hexdigest()))
        for d in list(dirs):
            dfp = os.path.join(dp, d)
            if os.path.islink(dfp):
                out.append(("link", os.path.relpath(dfp, R), os.readlink(dfp)))
                dirs.remove(d)
    return sorted(out, key=lambda e: e[1])


def write():
    rows = entries()
    io.open(os.path.join(R, NAME), "w", encoding="utf-8").write(
        "".join("%s\t%s\t%s\n" % (k, v, p) for k, p, v in rows))
    print("%d entries (%d files, %d links)" % (
        len(rows), sum(1 for r in rows if r[0] == "file"),
        sum(1 for r in rows if r[0] == "link")))
    print("manifest sha256 %s" % hashlib.sha256(
        io.open(os.path.join(R, NAME), "rb").read()).hexdigest()[:16])


def verify():
    want = {}
    for ln in io.open(os.path.join(R, NAME), encoding="utf-8"):
        if not ln.strip():
            continue
        kind, value, rel = ln.rstrip("\n").split("\t", 2)
        want[rel] = (kind, value)
    got = dict((p, (k, v)) for k, p, v in entries())
    missing = sorted(set(want) - set(got))
    added = sorted(set(got) - set(want))
    changed = sorted(p for p in set(want) & set(got) if want[p] != got[p])
    for tag, rows in (("MISSING", missing), ("UNMANIFESTED", added),
                      ("CHANGED", changed)):
        for p in rows[:8]:
            print("%s %s" % (tag, p))
    ok = not (missing or added or changed)
    print("PACKAGE %s: %d entries, %d missing, %d unmanifested, %d changed" % (
        "VERIFIES" if ok else "FAILS", len(want), len(missing), len(added),
        len(changed)))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(verify() if "--verify" in sys.argv[1:] else write())
