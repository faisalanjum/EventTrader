"""The copied and checked-out checkpoint is runnable and exact (Codex SEQ 1562 items 3 and 4).

copy_accepted_package.py copied bytes without modes, so build_a3_finalization.sh was 775 in
the package and 100644 in commit c89c6225 while run_ordered_1558.sh invokes it as `./...`.
These controls prove the copy preserves the executable bit, that an export of the staged
index carries every publication-manifest row byte-exact with its mode, that every shell
script in it is executable and parses, and that every `./name` a script invokes resolves to
an executable file in the export.
"""
import io
import os
import stat
import subprocess
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [R]
import copy_accepted_package as CAP  # noqa: E402


def test_copy_file_preserves_the_executable_bit(tmp_path):
    for mode in (0o755, 0o644):
        src = tmp_path / ("s%o" % mode)
        src.write_bytes(b"#!/bin/bash\necho hi\n")
        os.chmod(str(src), mode)
        dst = str(tmp_path / ("d%o" % mode))
        CAP.copy_file(str(src), dst)
        assert io.open(dst, "rb").read() == b"#!/bin/bash\necho hi\n"
        assert (stat.S_IMODE(os.stat(dst).st_mode) & 0o111 != 0) == (mode == 0o755)


def test_an_export_missing_the_executable_bit_is_refused(tmp_path):
    import verify_checkout as VC
    ex = tmp_path / "export" / "a3_recovery" / "regen_1541"
    ex.mkdir(parents=True)
    (ex / "run.sh").write_text("#!/bin/bash\n./tool.sh\n")
    (ex / "tool.sh").write_text("#!/bin/bash\necho ok\n")
    man = tmp_path / "export" / "a3_recovery" / "PUBLICATION_MANIFEST.tsv"
    man.write_text("mode\tpath\tbytes\tsha256\n")
    bad = VC.check_export(str(tmp_path / "export"))
    assert any(b.endswith("run.sh is not executable") for b in bad), bad
    assert any("runs ./tool.sh" in b for b in bad), bad
    for f in ("run.sh", "tool.sh"):
        os.chmod(str(ex / f), 0o755)
    bad = VC.check_export(str(tmp_path / "export"))
    assert all("executable" not in b for b in bad), bad
    assert any("not in the publication manifest" in b for b in bad), bad   # unmanifested staged files refuse too


def _git(repo, *args):
    import subprocess
    return subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, check=True).stdout


def test_a_staged_index_exports_byte_exact_and_runnable_and_a_lost_mode_refuses(tmp_path):
    """End to end on a private repository: copy with modes, stage, write the publication
    manifest from the INDEX, export the index, verify - then lose one executable bit."""
    import hashlib
    import verify_checkout as VC
    import write_publication_manifest as WPM
    repo = str(tmp_path / "repo")
    os.makedirs(os.path.join(repo, "a3_recovery", "regen_1541"))
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "core.fileMode", "false")             # as the recovery repository is configured
    src = tmp_path / "src"
    src.mkdir()
    (src / "build.sh").write_text("#!/bin/bash\necho built\n")
    os.chmod(str(src / "build.sh"), 0o755)
    (src / "run.sh").write_text("#!/bin/bash\n./build.sh prove\n")
    os.chmod(str(src / "run.sh"), 0o755)
    (src / "ORDERED_LOG.txt").write_text("log line\n")
    pin = hashlib.sha256(b"log line\n").hexdigest()
    (src / "ORDERED_LOG.sha256").write_text("%s  logs/ordered.txt\n%s  ORDERED_LOG.txt\n" % (pin, pin))
    for f in os.listdir(str(src)):
        CAP.copy_file(str(src / f), os.path.join(repo, "a3_recovery", "regen_1541", f))
    # the package verifies ITSELF in the checkout: ship the real verifier and its own manifest
    pkg = os.path.join(repo, "a3_recovery", "regen_1541")
    CAP.copy_file(os.path.join(R, "freeze_package.py"), os.path.join(pkg, "freeze_package.py"))
    subprocess.run([sys.executable, "-B", os.path.join(pkg, "freeze_package.py")], cwd=pkg, check=True, capture_output=True)
    _git(repo, "add", "a3_recovery")
    assert _git(repo, "ls-files", "-s", "--", "a3_recovery/regen_1541/build.sh").split()[0] == "100644"   # git ignored the mode
    # the working file drifts AFTER staging: the manifest and the export follow the index
    io.open(os.path.join(repo, "a3_recovery", "regen_1541", "ORDERED_LOG.txt"), "a").write("drift\n")
    WPM.build(repo)
    _git(repo, "add", "a3_recovery/PUBLICATION_MANIFEST.tsv")
    assert VC.failures(repo) == [], VC.failures(repo)
    man = io.open(os.path.join(repo, WPM.REL)).read()
    assert "100755\ta3_recovery/regen_1541/build.sh" in man and pin in man
    # the mode is lost in the working tree and re-staged: the export must refuse
    os.chmod(os.path.join(repo, "a3_recovery", "regen_1541", "build.sh"), 0o644)
    _git(repo, "add", "a3_recovery")
    WPM.stage_modes(repo)                                       # the index follows the working file's mode, both ways
    bad = VC.failures(repo)
    assert any("differs from the manifest mode" in b and "build.sh" in b for b in bad), bad
    # the mode restored; the ordered log re-staged with other bytes: only the pin can catch it
    os.chmod(os.path.join(repo, "a3_recovery", "regen_1541", "build.sh"), 0o755)
    io.open(os.path.join(repo, "a3_recovery", "regen_1541", "ORDERED_LOG.txt"), "w").write("other bytes\n")
    _git(repo, "add", "a3_recovery")
    WPM.refresh_internal_manifest(repo)                       # the internal manifest follows the index, as staging does
    WPM.build(repo)
    _git(repo, "add", "a3_recovery/PUBLICATION_MANIFEST.tsv")
    bad = VC.failures(repo)
    assert bad and all("ORDERED_LOG.sha256" in b for b in bad), bad
