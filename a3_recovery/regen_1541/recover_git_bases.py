#!/usr/bin/env python3
"""ONE-TIME RECOVERY TOOL, not a proof step: copy the committed objects the routes
resolve out of git and into evidence/git_bases/, keyed by FULL commit id.

This is the only file in the package that runs `git`. The proof never does: the replay
reads the store, and a missing entry is a refusal. The list of objects comes from an
enumeration of the routes with an EMPTY sibling cache (scratch: git_reads.json), so it
is measured, not hand-written. Re-running this tool against the same commits must
reproduce GIT_BASES.tsv byte for byte.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = "/home/faisal/EventMarketDB"
R = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(R, "evidence", "git_bases")


def main(*enumerations):
    # several measured lists (the empty-cache enumeration plus every misses file a
    # later recovery run dumped) are unioned; the store is regenerated WHOLE from the
    # union, so the same inputs always reproduce the same GIT_BASES.tsv
    d = {"show_objects": sorted({o for f in enumerations
                                 for o in json.load(io.open(f, encoding="utf-8"))["show_objects"]})}
    os.makedirs(STORE, exist_ok=True)
    rows = []
    commits = sorted({o.split(":", 1)[0] for o in d["show_objects"]})
    full = {c: subprocess.run(["git", "-C", REPO, "rev-parse", c], capture_output=True,
                              text=True, check=True).stdout.strip() for c in commits}
    for c in commits:
        names = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only",
                                full[c]], capture_output=True, text=True, check=True).stdout
        io.open(os.path.join(STORE, full[c] + ".tree"), "w", encoding="utf-8").write(names)
        rows.append((full[c], "<tree>", len(names.encode("utf-8")),
                     hashlib.sha256(names.encode("utf-8")).hexdigest()))
    for o in sorted(d["show_objects"]):
        c, rel = o.split(":", 1)
        got = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (full[c], rel)],
                             capture_output=True, check=True).stdout
        dst = os.path.join(STORE, full[c], rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        io.open(dst, "wb").write(got)
        rows.append((full[c], rel, len(got), hashlib.sha256(got).hexdigest()))
    io.open(os.path.join(STORE, "GIT_BASES.tsv"), "w", encoding="utf-8").write(
        "commit\trel\tbytes\tsha256\n" + "".join("%s\t%s\t%d\t%s\n" % r for r in rows))
    print("store: %d objects + %d trees" % (len(rows) - len(commits), len(commits)))


if __name__ == "__main__":
    main(*sys.argv[1:])
