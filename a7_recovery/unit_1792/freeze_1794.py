# -*- coding: utf-8 -*-
"""Freeze this unit in the one order that can be self-consistent (SEQ 1794).

    1 every record is already complete on disk
    2 DEPENDENCIES.json - the closure over the bind map this unit runs under
    3 WHITELIST.tsv    - the exact publication set
    4 MANIFEST.sha256  - LAST, over the final bytes of everything above

A manifest cannot contain its own final hash, so exactly ONE path is excluded
and the exclusion is named inside the manifest itself. The workflow-state view
is 625 files this tree already carries; it is supplied by a recipe over
published bytes and recorded as one directory digest instead of republished.
"""
import hashlib
import io
import json
import os
import subprocess

U = os.path.dirname(os.path.abspath(__file__))
R = "/home/faisal/EventMarketDB-driver-recovery"
VIEWS = {"view/workflows"}
COMPOSE = "compose_views_1792.sh"
SELF = "MANIFEST.sha256"
MAPS = ["a7_map_1792.tsv", "a7_map_1792_candidate.tsv",
        "a7_map_1792_candidate_intake.tsv"]


def fsha(path):
    h = hashlib.sha256()
    with io.open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dir_digest(d):
    rows = []
    for base, _dirs, files in os.walk(d):
        for name in files:
            p = os.path.join(base, name)
            rows.append("%s  ./%s\n" % (fsha(p), os.path.relpath(p, d)))
    return hashlib.sha256("".join(sorted(rows)).encode()).hexdigest(), len(rows)


def is_view(rel):
    return any(rel == v or rel.startswith(v + os.sep) for v in VIEWS)


def walk_files():
    for base, dirs, files in os.walk(U):
        rel = os.path.relpath(base, U)
        if is_view(rel):
            dirs[:] = []
            continue
        for name in sorted(files):
            yield os.path.relpath(os.path.join(base, name), U)


# ---- 2. the closure, over the whitelist this freeze is about to write -------
whitelist = sorted(walk_files())
tracked = {t for t in subprocess.run(["git", "-C", R, "ls-files"],
                                     capture_output=True, text=True).stdout.split("\n") if t}
unit_rel = os.path.relpath(U, R)
proposed = {os.path.join(unit_rel, p) for p in whitelist}
closure, unsatisfied, seen = [], [], set()
for mapfile in MAPS:
    for line in io.open(U + "/" + mapfile, encoding="utf-8").read().splitlines():
        logical, src, _sha, mode = line.split("\t")
        if (logical, src, mode) in seen:
            continue
        seen.add((logical, src, mode))
        rel = os.path.relpath(src, R) if src.startswith(R) else None
        inside = os.path.relpath(src, U) if src.startswith(U) else "x"
        if rel and is_view(inside):
            how = ("composed by %s: unit_1781's own already-published 624-file "
                   "view plus the one official state unit_1786 captured, which "
                   "becomes available in this SAME checkpoint and is not "
                   "published before it" % COMPOSE)
        elif rel and any(t == rel or t.startswith(rel + "/") for t in tracked):
            how = "already published (git-tracked)"
        elif rel and (rel in proposed or any(p.startswith(rel + "/") for p in proposed)):
            how = "newly whitelisted in this package"
        elif rel and "/view/" in "/" + rel:
            unit = rel.split("/")[1]
            how = ("composed by a7_recovery/%s/compose_views_%s.sh with %s as "
                   "its target, from published bytes"
                   % (unit, unit.split("_")[-1], unit))
        else:
            how = "UNSATISFIED"
            unsatisfied.append(src)
        closure.append({"logical": logical, "source": rel or src,
                        "mode": mode, "supplied_by": how})

views = {}
for v in sorted(VIEWS):
    digest, count = dir_digest(os.path.join(U, v))
    views[v] = {"digest": digest, "files": count, "compose_command": COMPOSE}

bp = ("a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/"
      "a4_final_lock_1683/launcher/boundary.py")
io.open(U + "/DEPENDENCIES.json", "w", encoding="utf-8").write(json.dumps({
    "boundary": {"path": bp, "sha256": fsha(os.path.join(R, bp)),
                 "note": "the published A4 launcher, used unmodified"},
    "maps": {m: fsha(U + "/" + m) for m in MAPS},
    "composed_views": views,
    "map_rows": len(closure),
    "writable_rows": sum(1 for c in closure if c["mode"] == "rw"),
    "scoped_override": {
        "logical": "<run>/grade_batch.seg04.js",
        "source": "a7_recovery/unit_1781/out/proposed_run/grade_batch.seg04.js",
        "mode": "ro",
        "why": ("the segment-4 intake must resolve to the EXACT immutable file "
                "the native call executed, not a byte-identical copy; the "
                "boundary mounts rows in order and supports this. Nothing is "
                "written to it and no file on disk is moved or relinked.")},
    "manifest_self_reference_exclusion": {
        "path": SELF,
        "reason": "a manifest cannot contain its own final hash",
        "everything_else_included": True},
    "unsatisfied_sources": unsatisfied,
    "closure": closure}, indent=1) + "\n")

# ---- 3. the exact publication set -------------------------------------------
whitelist = sorted(walk_files())
io.open(U + "/WHITELIST.tsv", "w", encoding="utf-8").write(
    "".join(p + "\n" for p in whitelist))

# ---- 4. the manifest, LAST, over the final bytes -----------------------------
rows = ["%s  %s\n" % (fsha(os.path.join(U, rel)), rel)
        for rel in sorted(walk_files()) if rel != SELF]
for v in sorted(views):
    rows.append("%s  %s/  (%d files, one directory digest, composed by %s)\n"
                % (views[v]["digest"], v, views[v]["files"], COMPOSE))
io.open(U + "/" + SELF, "w", encoding="utf-8").write("".join(sorted(rows)))
print("  whitelist rows : %d" % len(whitelist))
print("  manifest rows  : %d  (excludes only %s)" % (len(rows), SELF))
print("  views          : %s" % {v: views[v]["files"] for v in views})
print("  unsatisfied    : %d" % len(unsatisfied))
