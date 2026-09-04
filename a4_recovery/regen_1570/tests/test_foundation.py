"""The foundation's own boundaries, each beside a positive control (Codex SEQ 1579 test boundaries,
SEQ 1581 additions). Outside the projection the callable path refuses; the source map refuses a
missing or changed dependency or static input, a launch-manifest drift and swapped key-owner epochs;
the stage-to-owner map refuses a wrong, missing or swapped epoch; the census join refuses a missing
or duplicate state mapping; the script identity check refuses a rendered/embedded/projected mismatch;
the baseline check refuses digest, file-count and problem drift; the inventory epoch map refuses an
unrestored or swapped inventory; the Git identity derives only from a store holding the frozen commit; the
freshly built review package holds the freeze-receipt anchors and refuses each mutation; the closure classifier flags one
application read outside the candidate; and the two exported builds hold every anchor and are
byte-identical, for the foundation builds and for the signed-V6 continuation builds alike. The 22 corpus-freeze cases are not repeated here. No coverage framework.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import foundation as FD  # noqa: E402
import foundation_closure as FC  # noqa: E402
import foundation_sources as FS  # noqa: E402

HARNESS_REL = "foundation/bench/.claude/plans/Drivers/experiments/harness"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def test_the_callable_path_refuses_outside_the_projection():
    r = subprocess.run([sys.executable, "-B", FD.__file__, "step"], capture_output=True, text=True, cwd=R)
    assert r.returncode != 0 and "REFUSED" in r.stdout and "not inside the projected" in r.stdout


def _anchors(n):
    p = os.path.join(R, "foundation", "out", str(n), "a4_foundation", "ANCHORS.tsv")
    return [l.split("\t") for l in io.open(p, encoding="utf-8").read().split("\n") if l.strip()]


def _complete_builds():
    """The output roots the wrapper marked complete after the post-run view and the closure both passed."""
    out = os.path.join(R, "foundation", "out")
    return sorted(d for d in os.listdir(out) if os.path.isfile(os.path.join(out, d, "COMPLETE")))


def test_a_reused_or_nonempty_output_root_refuses_before_any_build_work(tmp_path):
    used = tmp_path / "used"; used.mkdir(); (used / "stale").write_bytes(b"x")
    r = subprocess.run([sys.executable, "-B", FD.__file__, "run", str(used)], capture_output=True, text=True, cwd=R)
    assert r.returncode != 0 and "output root is not empty" in r.stdout
    fresh = tmp_path / "fresh"; fresh.mkdir()
    r = subprocess.run([sys.executable, "-B", FD.__file__, "run", str(fresh)], capture_output=True, text=True, cwd=R)
    assert r.returncode != 0 and "not inside the projected" in r.stdout and not os.listdir(fresh)


def _builds_by_kind():
    """Complete roots by what they reached: the foundation alone, or the whole signed-V6 baseline (a lock anchor)."""
    out = {"foundation": [], "v6": []}
    for b in _complete_builds():
        out["v6" if any(r[0] == "lock" for r in _anchors(b)) else "foundation"].append(b)
    return out


def _pinned(kind):
    """The (scope, name) anchors a build of this kind must record: the foundation's, plus the V-chain, lock and V6 accounting."""
    rows = [(l.split("\t")[0], l.split("\t")[1]) for l in io.open(FS.PINS, encoding="utf-8").read().split("\n")[1:] if l.strip()]
    found = {FD.run_root(k) for k in ("phase1", "hardreview", "hrfix")}
    base = {(sc, n) for sc, n in rows if sc in found or sc.endswith("_package") or sc == "derived" or (sc, n) == ("baseline", "a3_baseline.json")
            or (sc, n) == ("inventory", "final") or (sc == "invrev" and n.endswith((".md", ".json")))}
    if kind == "foundation":
        return base
    # a run root's "era manifest" is the receipt-epoch recipe's input pin, never an anchor the runtime records
    return base | {(sc, n) for sc, n in rows if ((sc.startswith("kf-a4-") and sc not in found) or sc in ("lock", "v6")) and n != "era manifest"}


@pytest.mark.parametrize("kind", ["foundation", "v6"])
def test_both_fresh_builds_of_each_kind_hold_every_anchor_and_are_byte_identical(kind):
    builds = _builds_by_kind()[kind]
    assert len(builds) == 2, builds
    t1 = io.open(os.path.join(R, "foundation", "out", builds[0], "TREE.tsv"), "rb").read()
    t2 = io.open(os.path.join(R, "foundation", "out", builds[1], "TREE.tsv"), "rb").read()
    assert t1 == t2 and len(t1) > 100
    for b in builds:
        a = _anchors(b)
        assert a and all(row[4] == "ok" for row in a), [r for r in a if r[4] != "ok"]
        assert {(r[0], r[1]) for r in a} == _pinned(kind)


# ---- the source map on a private subset: positive control, then one mutation each ----
SUBSET = ("foundation/inventory/one_item_benchmark_inventory.b137e87e.json",
          "foundation/archives/archive_CODEX_1330.md", "foundation/archives/archive_CODEX_1333.md",
          "foundation/bench/.claude/plans/Drivers/experiments/harness/build_launch_manifest.py",
          "foundation/bench/.claude/plans/Drivers/experiments/harness/kf_lint.py",
          "foundation/bench/.claude/plans/Drivers/experiments/harness/v6_lock_1398.py",
          "foundation/owners/build_kfields_key.13d00b1f.py", "foundation/owners/build_kfields_key.a289601b.py",
          "foundation/tools/a3_reaudit.py", "foundation/tools/a4_regrade.py", "foundation/tools/a4_conflicts.py",
          "foundation/a4_derived/regrade_1370.json", "foundation/a4_derived/conflicts_1370.json")


def _private_map(tmp_path, monkeypatch):
    root = tmp_path / "root"
    for rel in SUBSET:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(R, rel), root / rel)
    lines = io.open(FS.TABLE, encoding="utf-8").read().split("\n")
    inv2 = [l.split("\t")[2] for l in lines[1:] if l.strip() and l.split("\t")[0] == "inventory2"]
    for rel in inv2:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(os.path.join(R, rel), root / rel)
    keep = [lines[0]] + [l for l in lines[1:] if l.strip() and l.split("\t")[2] in SUBSET + tuple(inv2)]
    table = root / "table.tsv"
    io.open(table, "w", encoding="utf-8").write("\n".join(keep) + "\n")
    # the owner pins outside the subset are not at this private harness path: keep only the subset's
    pins = [l for l in io.open(FS.PINS, encoding="utf-8").read().split("\n") if l.strip()]
    keep_pins = [pins[0]] + [l for l in pins[1:] if not (l.startswith("owner\t") and l.split("\t")[1] not in ("build_launch_manifest.py", "kf_lint.py", "build_kfields_key.py", "v6_lock_1398.py"))]
    ppath = root / "pins.tsv"
    io.open(ppath, "w", encoding="utf-8").write("\n".join(keep_pins) + "\n")
    monkeypatch.setattr(FS, "PINS", str(ppath))
    return root, str(table)


def test_the_source_map_positive_control(tmp_path, monkeypatch):
    root, table = _private_map(tmp_path, monkeypatch)
    assert FS.problems(table, str(root)) == []


def _flip(path):
    b = bytearray(io.open(path, "rb").read()); b[len(b) // 2] ^= 0x01; io.open(path, "wb").write(bytes(b))


@pytest.mark.parametrize("name,mutate,expected", [
    ("changed dependency byte", lambda root: _flip(root / HARNESS_REL / "kf_lint.py"), "differ from the table"),
    ("missing static input", lambda root: os.remove(root / "foundation/tools/a4_regrade.py"), "cannot read the candidate bytes"),
    ("launch manifest drift", lambda root: shutil.copyfile(os.path.join(FS.A3, "bench/.claude/plans/Drivers/experiments/harness/build_launch_manifest.py"), root / HARNESS_REL / "build_launch_manifest.py"), "build_launch_manifest.py"),
    ("swapped key epochs", lambda root: (os.rename(root / "foundation/owners/build_kfields_key.13d00b1f.py", root / "swap"),
                                         os.rename(root / "foundation/owners/build_kfields_key.a289601b.py", root / "foundation/owners/build_kfields_key.13d00b1f.py"),
                                         os.rename(root / "swap", root / "foundation/owners/build_kfields_key.a289601b.py")), "epoch"),
    ("derived file drift", lambda root: _flip(root / "foundation/a4_derived/conflicts_1370.json"), "derived conflicts_1370.json"),
    ("bad b137 inventory", lambda root: _flip(root / "foundation/inventory/one_item_benchmark_inventory.b137e87e.json"), "one_item_benchmark_inventory.b137e87e.json: candidate bytes"),
    ("missing b137 inventory", lambda root: os.remove(root / "foundation/inventory/one_item_benchmark_inventory.b137e87e.json"), "cannot read the candidate bytes"),
    ("archive 1330 drift", lambda root: _flip(root / "foundation/archives/archive_CODEX_1330.md"), "archive_CODEX_1330.md: candidate bytes"),
    ("missing archive 1333", lambda root: os.remove(root / "foundation/archives/archive_CODEX_1333.md"), "cannot read the candidate bytes"),
    ("lock owner drift", lambda root: _flip(root / HARNESS_REL / "v6_lock_1398.py"), "v6_lock_1398.py"),
])
def test_the_source_map_refuses(name, mutate, expected, tmp_path, monkeypatch):
    root, table = _private_map(tmp_path, monkeypatch)
    assert FS.problems(table, str(root)) == []
    mutate(root)
    bad = FS.problems(table, str(root))
    assert bad and any(expected in b for b in bad), (name, bad)


# ---- the two-entry stage-to-owner map ----
def _harness_with(tmp_path, rel):
    h = tmp_path / "harness"; h.mkdir(exist_ok=True)
    if rel:
        shutil.copyfile(os.path.join(R, rel), h / "build_kfields_key.py")
    return str(h)


@pytest.mark.parametrize("owner,stage,ok", [
    ("foundation/owners/build_kfields_key.13d00b1f.py", "phase1", True),
    ("foundation/owners/build_kfields_key.a289601b.py", "hardreview", True),
    ("foundation/owners/build_kfields_key.a289601b.py", "phase1", False),
    ("foundation/owners/build_kfields_key.13d00b1f.py", "hardreview", False),
    ("foundation/owners/build_kfields_key.13d00b1f.py", "final", False),
    ("foundation/tools/a4_regrade.py", "phase1", False),
    (None, "phase1", False),
])
def test_the_epoch_map_accepts_only_the_stages_owner(owner, stage, ok, tmp_path):
    bad = FD.epoch_problems(stage, _harness_with(tmp_path, owner))
    assert (bad == []) is ok, bad


# ---- the two-entry inventory epoch map ----
@pytest.mark.parametrize("epoch,stage,ok", [
    ("history", "inventory", True), ("final", "phase1", True), ("final", "hardreview", True),
    ("history", "phase1", False), ("history", "bridge", False), ("final", "inventory", False), (None, "phase1", False),
])
def test_the_inventory_epoch_map_refuses_an_unrestored_or_swapped_inventory(epoch, stage, ok, tmp_path):
    p = tmp_path / "one_item_benchmark_inventory.json"
    if epoch == "history":
        shutil.copyfile(os.path.join(R, "foundation/inventory/one_item_benchmark_inventory.b137e87e.json"), p)
    elif epoch == "final":
        rel = [r[2] for r in FS.load() if r[0] == "inventory2"][0]
        shutil.copyfile(os.path.join(R, rel), p)
    bad = FD.inventory_problems(stage, str(p))
    assert (bad == []) is ok, bad


# ---- the narrow Git identity ----
def test_git_identity_derives_only_from_a_store_holding_the_frozen_commit(tmp_path):
    assert FD.git_identity_problems("/home/faisal/EventMarketDB") == []
    assert FD.git_identity_problems(str(tmp_path))


# ---- the freshly built review package against the freeze receipt ----
def _review_copy(tmp_path):
    src = os.path.join(R, "foundation", "out", _complete_builds()[0], "bench_1306", ".claude", "plans", "Drivers", "experiments", "inventory_review")
    dst = tmp_path / "inventory_review"
    shutil.copytree(src, dst)
    return dst


def test_the_review_package_anchors_hold_and_each_mutation_refuses(tmp_path):
    d = _review_copy(tmp_path)
    assert FD.invrev_problems(str(d)) == []
    for name, mutate, expected in [
        ("prefix drift", lambda: _flip(d / "prefix.md"), "review package prefix.md"),
        ("missing input", lambda: os.remove(d / "inputs" / sorted(os.listdir(d / "inputs"))[0]), "is missing"),
        ("input drift", lambda: _flip(d / "inputs" / sorted(os.listdir(d / "inputs"))[1]), "input_sha256_shipped"),
        ("manifest drift", lambda: _flip(d / "package.manifest.json"), "review package package.manifest.json"),
    ]:
        shutil.rmtree(d); d = _review_copy(tmp_path)
        mutate()
        bad = FD.invrev_problems(str(d))
        assert bad and any(expected in b for b in bad), (name, bad)


# ---- the census join ----
def test_the_join_finds_each_saved_state_once_and_refuses_a_missing_or_duplicate_mapping():
    rows = FS.census()
    idx = FD.census_index(rows)
    phase, attempt, label = rows[0][0], rows[0][1], rows[0][2]
    assert FD.join(idx, phase, attempt, label)["wf"] == rows[0][3]
    with pytest.raises(SystemExit):
        FD.join(idx, phase, attempt, label + "-missing")
    with pytest.raises(SystemExit):
        FD.census_index(rows + [rows[0]])


# ---- the script identity ----
def test_the_script_identity_check_refuses_any_of_the_three_mismatches():
    a = b"export const meta = {}\n"; h = _sha(a)
    FD.check_script(a, a, a, h, "control")
    for rendered, embedded, on_disk, sha in ((a, a + b" ", a, h), (a, a, a + b" ", h), (a + b" ", a, a, h), (a, a, a, _sha(b"other"))):
        with pytest.raises(SystemExit):
            FD.check_script(rendered, embedded, on_disk, sha, "mutation")


# ---- the baseline facts ----
def test_the_baseline_check_refuses_digest_count_and_problem_drift():
    n = int(FS.pins("baseline")["files"])
    good = {"digest": FS.pins("baseline")["digest"], "files": {str(i): "x" for i in range(n)}, "primary_problems": []}
    assert FD.baseline_problems(good) == []
    assert FD.baseline_problems(dict(good, digest="0" * 64))
    assert FD.baseline_problems(dict(good, files={str(i): "x" for i in range(n - 1)}))
    assert FD.baseline_problems(dict(good, primary_problems=["one"]))


# ---- one application read outside the candidate ----
def test_the_closure_flags_an_outside_read_and_accepts_projected_candidate_and_venv_reads():
    table = io.open(FS.TABLE, encoding="utf-8").read()
    projected = table.split("\n")[1].split("\t")[1]
    lines = ['1 openat(AT_FDCWD, "%s", O_RDONLY|O_CLOEXEC) = 3' % projected,
             '1 openat(AT_FDCWD, "%s", O_RDONLY) = 4' % os.path.join(R, "inputs", "FOUNDATION_PINS.tsv"),
             '1 openat(AT_FDCWD, "%s/lib/python3.11/os.py", O_RDONLY|O_CLOEXEC) = 5' % FC.VENV,
             '1 openat(AT_FDCWD, "/usr/lib/locale/locale-archive", O_RDONLY|O_CLOEXEC) = 6',
             '1 openat(AT_FDCWD, "%s", O_WRONLY|O_CREAT, 0644) = 7' % "/home/faisal/EventMarketDB/x.json"]
    lines += ['1 openat(AT_FDCWD, "%s/pack/pack-abc.idx", O_RDONLY|O_CLOEXEC) = 9' % FC.GIT_OBJECTS,
              '1 openat(AT_FDCWD, ".git/objects/pack/pack-abc.pack", O_RDONLY|O_CLOEXEC) = 10',
              '1 openat(AT_FDCWD, "%s", O_RDONLY|O_CLOEXEC) = 11' % FC.GIT_CONTROL,
              '1 openat(AT_FDCWD, "%s/config", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)' % FC.GIT]
    pr, cand, gen, git, system, outside = FC.classify("\n".join(lines), table)
    assert projected in pr and cand and system and outside == {}
    assert set(git) == {"%s/pack/pack-abc.idx" % FC.GIT_OBJECTS, ".git/objects/pack/pack-abc.pack"} and FC.GIT_CONTROL in gen
    for bad in ("/home/faisal/EventMarketDB/driver/core/prepared_fact_v2.py", ".git/config", ".git/packed-refs", ".git/cursor/crepe/x/metadata.json",
                "/home/faisal/.gitconfig", "%s/config" % FC.GIT, "%s/packed-refs" % FC.GIT, "%s/cursor/crepe/x/metadata.json" % FC.GIT, "relative/other.txt"):
        pr, cand, gen, git, system, outside = FC.classify("\n".join(lines + ['1 openat(AT_FDCWD, "%s", O_RDONLY|O_CLOEXEC) = 12' % bad]), table)
        assert list(outside) == [bad], (bad, outside)
