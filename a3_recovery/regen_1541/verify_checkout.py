#!/usr/bin/env python3
"""A checkout of the staged index is exact and runnable (Codex SEQ 1562 items 3 and 4).

`export` writes the INDEX's a3_recovery subtree - the staged tree, what a commit would
carry - to a fresh directory with git's own checkout-index. `check_export` requires: every publication-manifest row
present, byte-exact and with its mode; every file under a3_recovery listed in the manifest;
every shell script executable and parseable; every `./name` a script runs resolving to an
executable file in the export; and every shipped copy of the ordered log hashing to its pin.
`failures` does both on a temporary export and removes it.
"""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MANIFEST = os.path.join("a3_recovery", "PUBLICATION_MANIFEST.tsv")
PACKAGE = os.path.join("a3_recovery", "regen_1541")
#: where an export is written: a sibling of this package, never /tmp - the real path masks
#: /tmp inside its mount namespace and an export there vanishes the moment it is armed
EXPORT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pt_harness")
REMOTE_FILE_LIMIT = 100 * 1024 * 1024        # the remote refuses a single blob above this
RUNS = re.compile(r"(?<![\w/.])\./(\w[\w.\-]*)")


def _sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def export(worktree, dest):
    """The INDEX's a3_recovery subtree, exactly as a commit would carry it - the only
    subtree the checks read, so the rest of the repository's 700 MB is never exported."""
    paths = subprocess.run(["git", "-C", worktree, "ls-files", "-z", "--", "a3_recovery"], capture_output=True, check=True).stdout
    subprocess.run(["git", "-C", worktree, "checkout-index", "--prefix=" + dest.rstrip("/") + "/", "-z", "--stdin"],
                   input=paths, check=True)


def internal_manifest_defects(dest):
    """The shipped package verifies ITSELF: its own freeze_package.py --verify, run inside
    the export, must accept the export's PACKAGE_MANIFEST.tsv. A compact export once
    carried the working package's 7,340-entry manifest naming thousands of files it did
    not hold, and passed every public check (Codex SEQ 1564 item 2)."""
    pkg = os.path.join(dest, PACKAGE)
    fp = os.path.join(pkg, "freeze_package.py")
    if not os.path.isfile(fp):
        return ["internal manifest: the checkout ships no freeze_package.py to verify itself with"]
    r = subprocess.run([sys.executable, "-B", fp, "--verify"], cwd=pkg, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    last = (r.stdout.strip().split("\n") or [""])[-1]
    if r.returncode != 0 or not last.startswith("PACKAGE VERIFIES"):
        return ["internal manifest: the checkout's own verifier refuses it: %s" % (last or r.stderr.strip()[-200:])[:200]]
    return []


def check_export(dest):
    bad, rows = [], {}
    man = os.path.join(dest, MANIFEST)
    if not os.path.isfile(man):
        bad.append("no publication manifest at %s" % MANIFEST)
    else:
        for ln in io.open(man, encoding="utf-8").read().split("\n")[1:]:
            if ln.strip():
                mode, path, b, s = ln.split("\t")
                rows[path] = (mode, int(b), s)
    for path, (mode, b, s) in sorted(rows.items()):
        fp = os.path.join(dest, path)
        if b > REMOTE_FILE_LIMIT:
            bad.append("too large for the remote's per-file limit: %s (%d bytes)" % (path, b))
        if not os.path.isfile(fp):
            bad.append("missing from the checkout: %s" % path)
        elif os.path.getsize(fp) != b or _sha(fp) != s:
            bad.append("differs from the publication manifest: %s" % path)
        elif os.access(fp, os.X_OK) != (mode == "100755"):
            bad.append("executable bit differs from the manifest mode %s: %s" % (mode, path))
    top = os.path.join(dest, "a3_recovery")
    for dp, _d, files in os.walk(top):
        for f in sorted(files):
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, dest)
            if rel != MANIFEST and rel not in rows:
                bad.append("%s is not in the publication manifest" % rel)
            if f.endswith(".sh"):
                if not os.access(fp, os.X_OK):
                    bad.append("%s is not executable" % rel)
                if subprocess.run(["bash", "-n", fp], capture_output=True).returncode:
                    bad.append("%s does not parse" % rel)
                for name in sorted(set(RUNS.findall(io.open(fp, encoding="utf-8", errors="replace").read()))):
                    t = os.path.join(dp, name)
                    if not (os.path.isfile(t) and os.access(t, os.X_OK)):
                        bad.append("%s runs ./%s, which is not an executable file in the checkout" % (rel, name))
            if f == "ORDERED_LOG.sha256":
                for ln in io.open(fp, encoding="utf-8").read().splitlines():
                    s, name = ln.split("  ", 1)
                    t = os.path.join(dp, name)
                    if os.path.isfile(t) and _sha(t) != s:
                        bad.append("%s does not hash to ORDERED_LOG.sha256" % os.path.relpath(t, dest))
                    elif not os.path.isfile(t) and not name.startswith("logs/"):
                        bad.append("%s pinned by ORDERED_LOG.sha256 is missing from the checkout" % name)
    bad += internal_manifest_defects(dest)
    return bad


def execute(dest):
    """Run the REAL resume/finalization path inside the exported checkout alone - no
    sibling package, an empty cache - and require it to complete clean with the frozen
    identities (Codex SEQ 1563 item 2). A hash-bound untracked byte is not recovery; a
    checkout that runs is. -> defects"""
    pkg = os.path.join(dest, PACKAGE)
    shutil.rmtree(os.path.join(pkg, "sibling_cache"), ignore_errors=True)
    bad = []
    if not os.path.isfile(os.path.join(pkg, "build_a3_finalization.sh")):
        return ["the checkout has no build_a3_finalization.sh to run"]
    r = subprocess.run(["./build_a3_finalization.sh", "prove"], cwd=pkg, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if r.returncode != 0:
        bad.append("the real path did not complete in the checkout: rc=%d: %s" % (r.returncode, (r.stdout + r.stderr).strip().split("\n")[-1][:200]))
    rp = os.path.join(pkg, "reports", "resume_path.json")
    rep = json.load(io.open(rp, encoding="utf-8")) if os.path.isfile(rp) else None
    if rep is None:
        bad.append("the checkout run wrote no resume report")
    else:
        if rep.get("result") != "completed" or not rep.get("clean"):
            bad.append("the checkout resume is not completed and clean: result=%r clean=%r" % (rep.get("result"), rep.get("clean")))
        for k in ("resolved_into_dirty_main", "unmanifested_reads", "temporary_reads", "unaudited_children"):
            if rep.get(k):
                bad.append("the checkout resume read outside the checkout: %s=%d" % (k, len(rep[k])))
    bp = os.path.join(pkg, "reports", "a3_evidence_boundary.json")
    b = json.load(io.open(bp, encoding="utf-8")) if os.path.isfile(bp) else None
    if b is None or not b.get("proved"):
        bad.append("the pinned evidence boundary is not proved in the checkout")
    # THE FROZEN IDENTITIES, from the one authority the closure carries: every `identity`
    # row of the projection - what the run must GENERATE - present and byte-exact in the
    # checkout after the run
    tsv = os.path.join(pkg, "evidence", "PROJECTION.tsv")
    if not os.path.isfile(tsv):
        bad.append("the checkout has no PROJECTION.tsv to name the frozen identities")
    else:
        n = 0
        for ln in io.open(tsv, encoding="utf-8").read().split("\n")[1:]:
            if ln.strip():
                ph, _hist, rel, nbytes, sha = ln.split("\t")
                if ph != "identity":
                    continue
                fp = os.path.join(pkg, rel)
                n += 1
                if not os.path.isfile(fp) or os.path.getsize(fp) != int(nbytes) or _sha(fp) != sha:
                    bad.append("frozen identity not met in the checkout: %s" % rel)
        if n == 0:
            bad.append("the projection names no identity row")
    return bad


def failures(worktree, run=False):
    os.makedirs(EXPORT_ROOT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="checkout_", dir=EXPORT_ROOT)
    try:
        export(worktree, tmp)
        bad = check_export(tmp)
        if run:
            bad += execute(tmp)
        return bad
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv):
    run = "--execute" in argv
    bad = failures([a for a in argv if not a.startswith("--")][0], run=run)
    for b in bad[:40]:
        print("  DEFECT", b)
    print("CHECKOUT %s" % (("OK: the exported index is byte-exact to the publication manifest, every script executable and parseable, every ./invocation resolvable, the ordered log pinned"
                           + (", and the real resume/finalization path COMPLETED CLEAN inside the checkout alone with the frozen identities" if run else ""))
                          if not bad else "REJECTED (%d defects)" % len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
