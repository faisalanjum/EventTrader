#!/usr/bin/env python3
"""The compact PUBLICATION manifest of the staged checkpoint (Codex SEQ 1562 item 4).

Distinct from the 7,319-row runtime package manifest: one row per file STAGED under
a3_recovery/ in the recovery worktree - mode, path, bytes, sha256 of the staged blob - read
from git's index, never from the working files, so it describes exactly what a commit of
this index would carry. The manifest cannot list itself and is the one omission.
"""
import hashlib
import io
import os
import subprocess
import sys

REL = os.path.join("a3_recovery", "PUBLICATION_MANIFEST.tsv")


def staged(worktree):
    """-> [(mode, path, blob)] of every staged file under a3_recovery, from the index."""
    out = subprocess.run(["git", "-C", worktree, "ls-files", "-s", "--", "a3_recovery"],
                         capture_output=True, text=True, check=True).stdout
    rows = []
    for ln in out.splitlines():
        meta, path = ln.split("\t", 1)
        mode, blob, _stage = meta.split()
        rows.append((mode, path, blob))
    return rows


def stage_modes(worktree, subtree="a3_recovery"):
    """Give every staged file under `subtree` the executable bit its WORKING file has.
    The recovery repository sets core.fileMode=false, so `git add` records 100644 for a
    new file whatever its mode on disk: that is how commit c89c6225 came to carry the
    775 build_a3_finalization.sh as 100644. -> [(path, new mode)] changed"""
    changed = []
    for mode, path, _blob in staged(worktree):
        want = "100755" if os.access(os.path.join(worktree, path), os.X_OK) else "100644"
        if mode != want:
            subprocess.run(["git", "-C", worktree, "update-index", "--chmod=" + ("+x" if want == "100755" else "-x"), path], check=True)
            changed.append((path, want))
    return changed


def refresh_internal_manifest(worktree):
    """Regenerate the package's OWN manifest for the compact staged index: export the index
    beside the package, run the shipped freeze_package.py there so PACKAGE_MANIFEST.tsv
    describes exactly that export (both root log files included), bring the manifest back
    and stage it. The publication manifest must be rebuilt afterwards, since this file's
    hash changed (Codex SEQ 1564 item 2). -> the staged manifest's sha256"""
    import shutil
    import tempfile
    import verify_checkout as VC
    os.makedirs(VC.EXPORT_ROOT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="manifest_", dir=VC.EXPORT_ROOT)
    try:
        VC.export(worktree, tmp)
        pkg = os.path.join(tmp, VC.PACKAGE)
        r = subprocess.run([sys.executable, "-B", os.path.join(pkg, "freeze_package.py")], cwd=pkg, capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), check=True)
        src = os.path.join(pkg, "PACKAGE_MANIFEST.tsv")
        dst = os.path.join(worktree, VC.PACKAGE, "PACKAGE_MANIFEST.tsv")
        shutil.copyfile(src, dst)
        subprocess.run(["git", "-C", worktree, "add", os.path.join(VC.PACKAGE, "PACKAGE_MANIFEST.tsv")], check=True)
        print("internal manifest regenerated for the compact export and staged: %s" % r.stdout.strip().split("\n")[-1][:120])
        return hashlib.sha256(io.open(dst, "rb").read()).hexdigest()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def build(worktree):
    for path, mode in stage_modes(worktree):
        print("index mode set from the working file: %s %s" % (mode, path))
    rows = []
    for mode, path, blob in staged(worktree):
        if path == REL:
            continue
        data = subprocess.run(["git", "-C", worktree, "cat-file", "blob", blob], capture_output=True, check=True).stdout
        rows.append((mode, path, len(data), hashlib.sha256(data).hexdigest()))
    rows.sort(key=lambda r: r[1])
    io.open(os.path.join(worktree, REL), "w", encoding="utf-8").write(
        "mode\tpath\tbytes\tsha256\n" + "".join("%s\t%s\t%d\t%s\n" % r for r in rows))
    print("publication manifest: %d staged files, %d bytes, %d executable"
          % (len(rows), sum(r[2] for r in rows), sum(1 for r in rows if r[0] == "100755")))
    return 0


if __name__ == "__main__":
    sys.exit(build(sys.argv[1]))
