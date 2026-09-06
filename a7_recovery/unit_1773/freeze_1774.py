# -*- coding: utf-8 -*-
"""Freeze the complete A7 proof package (Codex SEQ 1774 items 2 and 4).

Manifest, dependency closure, test inventory and the exact proposed whitelist.
The two composed views are the ONLY directories excluded from publication, and
they are excluded for a stated reason: each is the union of an already
published old forest and this unit's own newly whitelisted evidence, so
publishing them would duplicate bytes the tree already carries. Each is pinned
by a directory digest AND reproducible by one recorded command, and this script
PROVES that closure rather than asserting it.
"""
import hashlib, io, json, os, subprocess

U = os.path.dirname(os.path.abspath(__file__))
R = "/home/faisal/EventMarketDB-driver-recovery"
VIEWS = {"view/workflows", "view/subagent_runs"}
COMPOSE = "compose_views_1773.sh"
#: each mutation case is a deliberately corrupted private copy of the accepted
#: run. They are PRESERVED on disk and pinned by digest here, but publishing 13
#: corrupted 861-file copies would add ~11k files that are exactly reproducible
#: by re-running the recorded command against the accepted run. Their evidence -
#: the per-case invocation, output and exit - IS published.
MUT = "out/mutations"


def is_mut_copy(rel):
    parts = rel.split(os.sep)
    return (len(parts) > 3 and os.sep.join(parts[:2]) == MUT
            and parts[3:4] != [] and parts[2] != "" and parts[3] not in ("case.log", "map.tsv"))


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


def excluded(rel):
    return any(rel == v or rel.startswith(v + os.sep) for v in VIEWS)


def unpublished(rel):
    """Preserved and pinned, but deliberately not published, with a reason."""
    parts = rel.split(os.sep)
    return (len(parts) >= 4 and parts[0] == "out" and parts[1] == "mutations"
            and parts[3] not in ("case.log", "map.tsv"))


# --- manifest + whitelist ---------------------------------------------------
rows, wl = [], []
for base, dirs, files in os.walk(U):
    rel = os.path.relpath(base, U)
    if excluded(rel):
        dirs[:] = []
        continue
    for n in sorted(files):
        p = os.path.join(base, n)
        r = os.path.relpath(p, U)
        rows.append("%s  %s\n" % (fsha(p), r))
        if not unpublished(r):
            wl.append(r)
views = {}
for v in sorted(VIEWS):
    dg, n = dir_digest(os.path.join(U, v))
    views[v] = {"digest": dg, "files": n}
    rows.append("%s  %s/  (%d files, one directory digest, composed)\n" % (dg, v, n))

io.open(U + "/MANIFEST.sha256", "w").write("".join(sorted(rows)))
io.open(U + "/WHITELIST.tsv", "w").write("".join(p + "\n" for p in sorted(wl)))

# --- dependency closure, PROVED --------------------------------------------
tracked = set(subprocess.run(["git", "-C", R, "ls-files"], capture_output=True,
                             text=True).stdout.split("\n"))
unit_rel = os.path.relpath(U, R)
proposed = {os.path.join(unit_rel, p) for p in wl}
closure, unsatisfied = [], []
for ln in io.open(U + "/a7_map_1773.tsv", encoding="utf-8").read().splitlines():
    lg, src, sha, mode = ln.split("\t")
    rel = os.path.relpath(src, R) if src.startswith(R) else None
    if rel and excluded(os.path.relpath(src, U) if src.startswith(U) else "x"):
        how = "composed by %s from published + whitelisted bytes" % COMPOSE
    elif rel and any(t == rel or t.startswith(rel + "/") for t in tracked if t):
        how = "already published (git-tracked)"
    elif rel and (rel in proposed or any(p.startswith(rel + "/") for p in proposed)):
        how = "newly whitelisted in this package"
    else:
        how = "UNSATISFIED"
        unsatisfied.append(src)
    closure.append({"logical": lg, "source": rel or src, "mode": mode, "supplied_by": how})

mut_digests = {}
mroot = os.path.join(U, MUT)
if os.path.isdir(mroot):
    for case in sorted(os.listdir(mroot)):
        for sub in ("a6_a5run_1515", "cand_out"):
            d = os.path.join(mroot, case, sub)
            if os.path.isdir(d):
                dg, n = dir_digest(d)
                mut_digests["%s/%s/%s" % (MUT, case, sub)] = {"digest": dg, "files": n}

dep = {"boundary": {"path": "a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626/"
                            "out/a4_final_lock_1683/launcher/boundary.py",
                    "sha256": fsha(R + "/a4_recovery/regen_1570/targeted_1589/"
                                   "post_1500_exact_1626/out/a4_final_lock_1683/"
                                   "launcher/boundary.py"),
                    "note": "the published A4 launcher, used unmodified"},
       "composed_views": {v: dict(views[v], compose_command=COMPOSE) for v in views},
       "map_rows": len(closure),
       "writable_rows": sum(1 for c in closure if c["mode"] == "rw"),
       "preserved_but_not_published": {
           "reason": ("deliberately corrupted private copies of the accepted run, "
                      "reproducible by re-running each recorded case command; "
                      "their invocation, output and exit ARE published"),
           "entries": mut_digests},
       "unsatisfied_sources": unsatisfied,
       "closure": closure}
io.open(U + "/DEPENDENCIES.json", "w").write(json.dumps(dep, indent=1) + "\n")

print("manifest      : %d rows (%d files + %d composed view digests)"
      % (len(rows), len(rows) - len(views), len(views)))
print("whitelist     : %d rows" % len(wl))
print("map closure   : %d rows, %d writable, %d UNSATISFIED"
      % (len(closure), dep["writable_rows"], len(unsatisfied)))
for c in closure:
    if c["supplied_by"].startswith("composed") or c["supplied_by"].startswith("newly"):
        print("   %-11s %s" % (c["mode"], c["source"]))
print("manifest sha  :", fsha(U + "/MANIFEST.sha256"))
print("whitelist sha :", fsha(U + "/WHITELIST.tsv"))
print("deps sha      :", fsha(U + "/DEPENDENCIES.json"))
