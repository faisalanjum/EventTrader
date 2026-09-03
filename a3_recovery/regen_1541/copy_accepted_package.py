#!/usr/bin/env python3
"""Copy the COMPLETE accepted package into the durable recovery worktree, and prove the
copy (Codex SEQ 1559). Run ONLY after the ordered chain has passed in full.

What is copied is exactly what the manifest names - every manifested file, the manifest
itself, and the completed ordered log pinned beside it - into a subdirectory of the
worktree named after the package. Nothing is staged, committed or pushed: the files are
untracked there, and this tool never invokes git. The copy is then verified entry by
entry against the manifest, and refused if anything differs.
"""
import hashlib
import io
import os
import shutil
import sys

R = os.path.dirname(os.path.abspath(__file__))
DEST_ROOT = "/home/faisal/EventMarketDB-driver-recovery"
MANIFEST = os.path.join(R, "PACKAGE_MANIFEST.tsv")


def _sha(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(log_name):
    if not os.path.isdir(DEST_ROOT):
        raise SystemExit("REFUSED: the recovery worktree %s does not exist" % DEST_ROOT)
    dest = os.path.join(DEST_ROOT, "a3_recovery", os.path.basename(R))
    if os.path.exists(dest):
        raise SystemExit("REFUSED: %s already exists; a copy is never overwritten" % dest)
    entries = []
    for ln in io.open(MANIFEST, encoding="utf-8"):
        if ln.strip():
            kind, value, rel = ln.rstrip("\n").split("\t", 2)
            entries.append((kind, rel, value))
    copied = 0
    for kind, rel, value in entries:
        src, dst = os.path.join(R, rel), os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if kind == "link":
            os.symlink(value, dst)
        else:
            shutil.copyfile(src, dst)
            if _sha(dst) != value:
                raise SystemExit("REFUSED: %s does not hash to its manifest entry after copying" % rel)
        copied += 1
    shutil.copyfile(MANIFEST, os.path.join(dest, "PACKAGE_MANIFEST.tsv"))
    log_src = os.path.join(R, "logs", log_name)
    os.makedirs(os.path.join(dest, "logs"), exist_ok=True)
    shutil.copyfile(log_src, os.path.join(dest, "logs", log_name))
    # the chain's OWN pin of that log (taken after its final line) travels with it, so
    # the worktree holds two independent pins of the same bytes: the chain's and this
    # tool's
    pin_src = os.path.splitext(log_src)[0] + ".sha256"
    if os.path.isfile(pin_src):
        shutil.copyfile(pin_src, os.path.join(dest, "logs", os.path.basename(pin_src)))
    io.open(os.path.join(dest, "ORDERED_LOG.sha256"), "w").write(
        "%s  logs/%s\n" % (_sha(log_src), log_name))
    # verify the copy the same way the package verifies itself
    bad = 0
    for kind, rel, value in entries:
        dst = os.path.join(dest, rel)
        if kind == "link":
            bad += os.readlink(dst) != value
        else:
            bad += (not os.path.isfile(dst)) or _sha(dst) != value
    print("copied %d manifested entries + manifest + %s into %s; verification defects: %d"
          % (copied, log_name, dest, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "ordered_1560.txt"))
