"""The copy into the recovery worktree proves itself and refuses the unsafe cases
(Codex SEQ 1559): never over an existing copy, never a byte that does not hash."""
import hashlib
import io
import os
import sys

import pytest

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
import copy_accepted_package as CAP                            # noqa: E402


def _fake_package(tmp_path):
    pkg = tmp_path / "pkg"; (pkg / "sub").mkdir(parents=True); (pkg / "logs").mkdir()
    a = b"alpha\n"; b = b"beta\n"
    (pkg / "a.txt").write_bytes(a); (pkg / "sub" / "b.txt").write_bytes(b)
    (pkg / "PACKAGE_MANIFEST.tsv").write_text(
        "file\t%s\ta.txt\nfile\t%s\tsub/b.txt\n" % (hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest()))
    (pkg / "logs" / "ordered_x.txt").write_text("== done\n")
    return pkg


def _bind(monkeypatch, pkg, dest_root):
    monkeypatch.setattr(CAP, "R", str(pkg))
    monkeypatch.setattr(CAP, "MANIFEST", str(pkg / "PACKAGE_MANIFEST.tsv"))
    monkeypatch.setattr(CAP, "DEST_ROOT", str(dest_root))


def test_it_copies_every_manifested_entry_and_verifies_the_copy(tmp_path, monkeypatch):
    pkg = _fake_package(tmp_path); dest = tmp_path / "worktree"; dest.mkdir()
    _bind(monkeypatch, pkg, dest)
    assert CAP.main("ordered_x.txt") == 0
    out = dest / "a3_recovery" / "pkg"
    assert (out / "a.txt").read_bytes() == b"alpha\n" and (out / "sub" / "b.txt").read_bytes() == b"beta\n"
    assert (out / "PACKAGE_MANIFEST.tsv").exists() and (out / "logs" / "ordered_x.txt").exists()
    assert (out / "ORDERED_LOG.sha256").read_text().split()[0] == hashlib.sha256(b"== done\n").hexdigest()


def test_it_REFUSES_when_the_worktree_is_missing(tmp_path, monkeypatch):
    pkg = _fake_package(tmp_path)
    _bind(monkeypatch, pkg, tmp_path / "absent")
    with pytest.raises(SystemExit):
        CAP.main("ordered_x.txt")


def test_it_REFUSES_to_overwrite_an_existing_copy(tmp_path, monkeypatch):
    pkg = _fake_package(tmp_path); dest = tmp_path / "worktree"
    (dest / "a3_recovery" / "pkg").mkdir(parents=True)
    _bind(monkeypatch, pkg, dest)
    with pytest.raises(SystemExit):
        CAP.main("ordered_x.txt")


def test_it_REFUSES_a_source_that_no_longer_hashes_to_the_manifest(tmp_path, monkeypatch):
    pkg = _fake_package(tmp_path); dest = tmp_path / "worktree"; dest.mkdir()
    (pkg / "a.txt").write_bytes(b"ALTERED\n")
    _bind(monkeypatch, pkg, dest)
    with pytest.raises(SystemExit):
        CAP.main("ordered_x.txt")
