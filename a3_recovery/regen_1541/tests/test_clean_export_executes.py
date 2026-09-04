"""The staged closure, exported ALONE to a clean checkout, executes the real
resume/finalization path (Codex SEQ 1563 item 2).

A hash-bound untracked byte is not recovery. evidence/CLOSURE.tsv is the measured closure
of the real path - every projection row plus every file the path's processes opened under
the package (closure_trace.py, strace over the whole run). This control stages exactly
that closure into a private repository, exports the index to a fresh directory with no
sibling package and no cache, and runs the real path there through the one executor,
verify_checkout.execute: it must complete clean with the frozen identities. Then one
traced file is removed from the export and the executor must refuse.
"""
import os
import shutil
import subprocess
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [R]
import closure_trace as CT  # noqa: E402
import copy_accepted_package as CAP  # noqa: E402
import verify_checkout as VC  # noqa: E402
import write_publication_manifest as WPM  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, check=True).stdout


def _repo_from_closure(tmp_path, refresh=True):
    repo = str(tmp_path / "repo")
    os.makedirs(repo)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "core.fileMode", "false")
    rows = CT.load(R)
    for rel in rows:
        dst = os.path.join(repo, VC.PACKAGE, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        CAP.copy_file(os.path.join(R, rel), dst)
    _git(repo, "add", "a3_recovery")
    # the closure must carry the package's own verifier, or the checkout cannot verify itself
    assert os.path.isfile(os.path.join(repo, VC.PACKAGE, "freeze_package.py")), "the staged closure ships no freeze_package.py"
    if refresh:
        WPM.refresh_internal_manifest(repo)                     # the stage step's own procedure
    WPM.build(repo)
    _git(repo, "add", WPM.REL)
    return repo, rows


def test_the_closure_alone_executes_the_real_path_and_a_missing_file_refuses(tmp_path):
    repo, rows = _repo_from_closure(tmp_path)
    # THE COMMAND-LINE PATH FIRST, the one the stage step runs: it chooses the export
    # directory itself, and an export under /tmp vanishes inside the real path's namespace
    assert VC.failures(repo, run=True) == [], VC.failures(repo, run=True)[:5]
    dest = str(tmp_path / "export")
    VC.export(repo, dest)
    assert not os.path.exists(os.path.join(dest, VC.PACKAGE, "sibling_cache"))
    assert VC.check_export(dest) == [], VC.check_export(dest)[:5]
    bad = VC.execute(dest)
    assert bad == [], bad[:5]
    traced = sorted(rel for rel, (_b, _s, src) in rows.items() if src == "traced-read" and rel.endswith(".py"))
    assert traced, "the closure records no traced code"
    os.remove(os.path.join(dest, VC.PACKAGE, traced[0]))
    shutil.rmtree(os.path.join(dest, VC.PACKAGE, "reports"), ignore_errors=True)
    bad = VC.execute(dest)
    assert bad and any("did not complete" in b or "no resume report" in b for b in bad), bad


def test_a_stale_internal_manifest_in_the_export_is_refused_and_a_fresh_one_verifies(tmp_path):
    """Codex SEQ 1564 item 2: the compact export carried the working package's 7,340-entry
    PACKAGE_MANIFEST.tsv, naming thousands of files the export does not hold, and the
    export's own `freeze_package.py --verify` failed while the public checks passed. The
    verifier must run the shipped internal verifier; the stage step must regenerate the
    internal manifest FOR the compact export and stage it."""
    repo, _rows = _repo_from_closure(tmp_path, refresh=False)
    dest = str(tmp_path / "export")
    VC.export(repo, dest)
    bad = VC.check_export(dest)
    assert any("internal manifest" in b for b in bad), bad[:5]        # stale: the working package's
    shutil.rmtree(dest)
    WPM.refresh_internal_manifest(repo)                                # regenerated for the compact index, staged
    _git(repo, "add", "a3_recovery")
    WPM.build(repo)
    _git(repo, "add", WPM.REL)
    assert VC.failures(repo, run=True) == [], VC.failures(repo, run=True)[:5]
