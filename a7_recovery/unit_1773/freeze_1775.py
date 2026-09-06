# -*- coding: utf-8 -*-
"""Freeze the A7 package in the ONE order that can be self-consistent.

Codex SEQ 1775 item 1. freeze_1774 hashed MANIFEST.sha256 and WHITELIST.tsv and
then replaced both, so the manifest recorded bytes that no longer existed. The
retained red proof is logs/manifest_red_1775.log.

The order here is the accepted A6 one, and it is the whole fix:

    1 every record is already complete on disk
    2 write DEPENDENCIES.json (the closure over the final proposed whitelist)
    3 write WHITELIST.tsv - the exact publication set
    4 write MANIFEST.sha256 LAST, over the final bytes of everything above

A manifest cannot contain its own final hash, so exactly ONE path is excluded -
MANIFEST.sha256 - and the exclusion is named inside the manifest itself rather
than left for a reader to infer. There is no second self-hashing pass.
"""
import hashlib, io, json, os, subprocess

U = os.path.dirname(os.path.abspath(__file__))
R = "/home/faisal/EventMarketDB-driver-recovery"
VIEWS = {"view/workflows", "view/subagent_runs"}
COMPOSE = "compose_views_1773.sh"
SELF = "MANIFEST.sha256"


def fsha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dir_digest(d):
    L = []
    for base, _x, fs in os.walk(d):
        for n in fs:
            p = os.path.join(base, n)
            L.append("%s  ./%s\n" % (fsha(p), os.path.relpath(p, d)))
    return hashlib.sha256("".join(sorted(L)).encode()).hexdigest(), len(L)


def is_view(rel):
    return any(rel == v or rel.startswith(v + os.sep) for v in VIEWS)


def unpublished(rel):
    """Preserved and pinned, deliberately not published, with a stated reason."""
    parts = rel.split(os.sep)
    return (len(parts) >= 4 and parts[0] == "out" and parts[1] == "mutations"
            and parts[3] not in ("case.log", "map.tsv"))


def walk_files():
    for base, dirs, files in os.walk(U):
        rel = os.path.relpath(base, U)
        if is_view(rel):
            dirs[:] = []
            continue
        for n in sorted(files):
            yield os.path.relpath(os.path.join(base, n), U)


# ---- 2. dependencies, over the whitelist this freeze is about to write ------
wl = sorted(p for p in walk_files() if not unpublished(p))
tracked = {t for t in subprocess.run(["git", "-C", R, "ls-files"],
                                     capture_output=True, text=True).stdout.split("\n") if t}
unit_rel = os.path.relpath(U, R)
proposed = {os.path.join(unit_rel, p) for p in wl}
closure, unsatisfied = [], []
for ln in io.open(U + "/a7_map_1773.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    rel = os.path.relpath(src, R) if src.startswith(R) else None
    inside = os.path.relpath(src, U) if src.startswith(U) else "x"
    if rel and is_view(inside):
        how = "composed by %s from published + whitelisted bytes" % COMPOSE
    elif rel and any(t == rel or t.startswith(rel + "/") for t in tracked):
        how = "already published (git-tracked)"
    elif rel and (rel in proposed or any(p.startswith(rel + "/") for p in proposed)):
        how = "newly whitelisted in this package"
    else:
        how = "UNSATISFIED"
        unsatisfied.append(src)
    closure.append({"logical": lg, "source": rel or src, "mode": mode,
                    "supplied_by": how})

views = {}
for v in sorted(VIEWS):
    dg, n = dir_digest(os.path.join(U, v))
    views[v] = {"digest": dg, "files": n, "compose_command": COMPOSE}

mut, mroot = {}, os.path.join(U, "out", "mutations")
if os.path.isdir(mroot):
    for case in sorted(os.listdir(mroot)):
        for sub in ("a6_a5run_1515", "cand_out"):
            d = os.path.join(mroot, case, sub)
            if os.path.isdir(d):
                dg, n = dir_digest(d)
                mut["out/mutations/%s/%s" % (case, sub)] = {"digest": dg, "files": n}

bp = ("a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/out/"
      "a4_final_lock_1683/launcher/boundary.py")
io.open(U + "/DEPENDENCIES.json", "w").write(json.dumps({
    "boundary": {"path": bp, "sha256": fsha(os.path.join(R, bp)),
                 "note": "the published A4 launcher, used unmodified"},
    "composed_views": views,
    "map_rows": len(closure),
    "writable_rows": sum(1 for c in closure if c["mode"] == "rw"),
    "manifest_self_reference_exclusion": {
        "path": SELF,
        "reason": "a manifest cannot contain its own final hash",
        "everything_else_included": True},
    "preserved_but_not_published": {
        "reason": ("deliberately corrupted private copies of the accepted run, "
                   "reproducible by re-running each recorded case command; their "
                   "invocation, output and exit ARE published"),
        "entries": mut},
    "unsatisfied_sources": unsatisfied,
    "closure": closure}, indent=1) + "\n")

# ---- 3. the exact publication set ------------------------------------------
wl = sorted(p for p in walk_files() if not unpublished(p))
io.open(U + "/WHITELIST.tsv", "w").write("".join(p + "\n" for p in wl))

# ---- 4. the manifest, LAST, over the final bytes ---------------------------
rows = ["%s  %s\n" % (fsha(os.path.join(U, rel)), rel)
        for rel in sorted(walk_files()) if rel != SELF]
for v in sorted(views):
    rows.append("%s  %s/  (%d files, one directory digest, composed by %s)\n"
                % (views[v]["digest"], v, views[v]["files"], COMPOSE))
rows.append("# EXCLUDED %s - a manifest cannot contain its own final hash; "
            "every other file above is included\n" % SELF)
io.open(U + "/MANIFEST.sha256", "w").write("".join(rows))

print("write order   : records -> dependencies -> whitelist -> manifest (last)")
print("manifest rows : %d (%d files + %d view digests + 1 exclusion note)"
      % (len(rows), len(rows) - len(views) - 1, len(views)))
print("whitelist     : %d rows" % len(wl))
print("map closure   : %d rows, %d writable, %d UNSATISFIED"
      % (len(closure), sum(1 for c in closure if c["mode"] == "rw"), len(unsatisfied)))
print("excluded      : %s (self-reference, named in the manifest)" % SELF)
print("whitelist sha :", fsha(U + "/WHITELIST.tsv"))
print("deps sha      :", fsha(U + "/DEPENDENCIES.json"))
print("manifest sha  :", fsha(U + "/MANIFEST.sha256"))
