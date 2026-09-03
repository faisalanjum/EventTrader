"""Relocation is refused unless the historical tree is projected from package bytes.

Codex SEQ 1561 item 1. The accepted A3 audit derives the run id and every launcher path
from the run directory's absolute path, so (a) the package's own run directory refuses
by name and by path, (b) an ordinary symlink carrying the historical name still refuses
on the paths, (c) the exact package-backed projection verifies, and (d) a changed
projected byte or any unmapped /tmp read refuses in the one read classifier.
"""
import hashlib
import io
import json
import os
import shutil
import sys

R = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path[:0] = [R]
import project_historical_tree as PHT  # noqa: E402
import run_resume_path as RRP  # noqa: E402

HARNESS = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments", "harness")


def _audit():
    os.environ.setdefault("GUIDANCE_SCRIPTS_DIR", os.path.join(R, "bench", ".claude", "skills", "earnings-orchestrator", "scripts"))
    os.environ["KFIELDS_EVIDENCE"] = os.path.join(R, "bench", ".claude", "plans", "Drivers", "experiments")
    cwd = os.getcwd()
    os.chdir(HARNESS)
    sys.path.insert(0, HARNESS)
    try:
        import raw_transport as A
        return A
    finally:
        os.chdir(cwd)


def _receipt():
    return json.load(io.open(os.path.join(R, PHT.PACKAGE_RUN, "receipt.json"), encoding="utf-8"))


def test_the_package_run_directory_refuses_by_name_and_path():
    A = _audit()
    cwd = os.getcwd(); os.chdir(HARNESS)
    try:
        bad = A.a1_run_contract_problems(_receipt(), os.path.join(R, PHT.PACKAGE_RUN))
    finally:
        os.chdir(cwd)
    assert any("run_id" in b for b in bad) and any("receipts" in b for b in bad)


def test_an_ordinary_symlink_with_the_historical_name_still_refuses(tmp_path):
    A = _audit()
    _ev, run = PHT.historical_roots()
    link = tmp_path / "runs" / os.path.basename(run)
    link.parent.mkdir(parents=True)
    os.symlink(os.path.join(R, PHT.PACKAGE_RUN), str(link))
    cwd = os.getcwd(); os.chdir(HARNESS)
    try:
        bad = A.a1_run_contract_problems(_receipt(), str(link))
    finally:
        os.chdir(cwd)
    assert not any("run_id" in b for b in bad)           # the name is right ...
    assert any("receipts" in b for b in bad)             # ... the absolute paths are not


def _view(tmp_path):
    """An exact projected view built from the table, under a temporary root."""
    root = str(tmp_path / "view")
    for _ph, hist, rel, _b, _s in PHT.load():
        dst = PHT.view_path(root, hist)            # the one guarded mapping, never a join
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(R, rel), dst)
    return root


def test_the_exact_package_backed_projection_verifies(tmp_path):
    assert PHT.verify(_view(tmp_path)) == []


def test_a_symlinked_projected_entry_refuses(tmp_path):
    root = _view(tmp_path)
    _ph, hist, rel, _b, _s = [r for r in PHT.load() if r[0] == "input"][0]
    v = PHT.view_path(root, hist)
    os.remove(v)
    os.symlink(os.path.join(R, rel), v)
    assert any("symlink" in d for d in PHT.verify(root))


def test_a_changed_projected_byte_refuses(tmp_path):
    root = _view(tmp_path)
    _ph, hist, _rel, _b, _s = [r for r in PHT.load() if r[0] == "input"][0]
    v = PHT.view_path(root, hist)
    b = bytearray(io.open(v, "rb").read()); b[0] ^= 0x01; io.open(v, "wb").write(bytes(b))
    assert any("differ" in d for d in PHT.verify(root))


def test_an_extra_file_in_the_projected_tree_refuses(tmp_path):
    root = _view(tmp_path)
    io.open(os.path.join(root, "not_package_backed.txt"), "w").write("x")
    assert any("extra file" in d for d in PHT.verify(root))


def test_the_read_classifier_covers_only_mapped_equal_bytes_under_tmp(tmp_path):
    p = str(tmp_path / "projected.json")                 # wherever pytest's temp dir lives
    io.open(p, "w").write("{}")
    digest = hashlib.sha256(b"{}").hexdigest()
    mapped = {p: ("bench/x.json", digest)}
    assert RRP.classify_read(p, set(), mapped) == "covered"
    io.open(p, "w").write("{ }")                          # a changed projected byte: never covered
    assert RRP.classify_read(p, set(), mapped) != "covered"
    # under /tmp the verdict is temporary, mapped-but-changed and unmapped alike
    tmp_mapped = "/tmp/claude-1000/x/projected.json"      # absent on disk: cannot be covered
    assert RRP.classify_read(tmp_mapped, set(), {tmp_mapped: ("bench/x.json", digest)}) == "temporary"
    assert RRP.classify_read("/tmp/claude-1000/x/unmapped.json", set(), mapped) == "temporary"
    assert RRP.classify_read("/tmp/claude-1000/x/unmapped.json", set(), None) == "temporary"   # the ordinary default
    # a session-directory path is covered by the map alone, never by its name
    home_like = "/home/faisal/.claude/projects/x/workflows/wf_1.json"
    assert RRP.classify_read(home_like, set(), {home_like: ("evidence/workflow_states/wf_1.json", digest)}) == "unmanifested"  # not on disk
    assert RRP.classify_read(home_like, set(), None) == "unmanifested"


def test_the_projection_inputs_are_explicit_and_paired():
    import pytest
    with pytest.raises(SystemExit):
        RRP.projection_inputs(["--projection", PHT.TSV])
    with pytest.raises(SystemExit):
        RRP.projection_inputs(["--evidence-root", "/tmp/somewhere", "--projection", PHT.TSV])
    assert RRP.projection_inputs([]) == (None, None)


def test_the_projection_carries_every_official_state_the_receipts_name():
    states = {h for ph, h, _r, _b, _s in PHT.load() if ph == "state"}
    assert states and states == set(PHT.state_paths())
    for _ph, h, rel, _b, _s in PHT.load():
        if _ph == "state":
            assert rel == os.path.join("evidence", "workflow_states", os.path.basename(h))


def test_a_state_row_maps_inside_the_view_never_outside(tmp_path):
    import pytest
    root = str(tmp_path / "view")
    state = [h for ph, h, _r, _b, _s in PHT.load() if ph == "state"][0]
    assert PHT.view_path(root, state).startswith(root + os.sep)
    with pytest.raises(ValueError):
        PHT.view_path(root, "/etc/hostname")
