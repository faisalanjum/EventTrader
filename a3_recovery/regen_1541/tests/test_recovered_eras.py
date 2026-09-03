"""A recovered artefact belongs to an ERA (Codex SEQ 1546, corrected by SEQ 1547).

`one_item_benchmark_inventory.json` is one path with six bodies across the campaign.
My first version of this suite was too weak to be evidence: the pre-first assertion
allowed ANY non-v1 answer, so it passed while an era-less stale body was served into a
window that body never occupied. When a path has a timed series, nothing may fill the
window before its first timed body.
"""
import hashlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR                                    # noqa: E402

INV = "/x/.claude/plans/Drivers/experiments/one_item_benchmark_inventory.json"
A2 = "/x/.claude/plans/Drivers/experiments/harness/a2_runtime_freeze.json"
#: (record that produced it, digest prefix) for the six proven eras
ERAS = [(22523, "165be143"), (22667, "561fb483"), (22741, "920e2c47"),
        (22765, "98570f86"), (28659, "f7ea9af4"), (29136, "b137e87e")]


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_before_the_first_timed_body_the_answer_is_exactly_None():
    """Not "something else" - None. The file had no such content yet, and serving a
    later era's body there hands a record bytes it never saw."""
    for cutoff in (1, 22000, 22523):
        assert CR._recovered(INV, cutoff) is None, cutoff


def test_the_producer_boundary_is_exact():
    """A body produced AT a record is available to the records AFTER it, not to it."""
    assert CR._recovered(INV, 22523) is None
    assert sha(CR._recovered(INV, 22524)).startswith("165be143")


def test_between_two_eras_the_earlier_body_is_served():
    """A cutoff inside an era window gets that era, not the newest one."""
    assert sha(CR._recovered(INV, 22666)).startswith("165be143")
    assert sha(CR._recovered(INV, 22700)).startswith("561fb483")
    assert sha(CR._recovered(INV, 24066)).startswith("98570f86")


def test_each_era_is_served_at_its_own_window():
    for produced_at, want in ERAS:
        got = CR._recovered(INV, produced_at + 1)
        assert got is not None, produced_at
        assert sha(got).startswith(want), produced_at


def test_after_the_last_era_the_latest_body_is_served():
    assert sha(CR._recovered(INV, 10 ** 9)).startswith("b137e87e")


def test_a_body_that_does_not_match_its_digest_is_REFUSED(tmp_path):
    """Digest-gating survives the era rule: a tampered body serves nothing."""
    idx = os.path.join(R, "recovered", "RECOVERED.tsv")
    saved_dir = CR._RECOVERED_DIR
    stage = str(tmp_path)
    io.open(os.path.join(stage, "RECOVERED.tsv"), "w", encoding="utf-8").write(
        "%s\t.claude/x/thing.json\t100\tthing.json\n" % ("0" * 64))
    io.open(os.path.join(stage, "thing.json"), "w", encoding="utf-8").write("{}\n")
    CR._RECOVERED_DIR = stage
    try:
        assert CR._recovered("/x/.claude/x/thing.json", 200) is None
    finally:
        CR._RECOVERED_DIR = saved_dir
    assert os.path.isfile(idx)


def test_an_ERA_LESS_fallback_still_works_for_a_path_that_has_no_series():
    """The two rules coexist: a path with no timed body keeps its plain fallback."""
    got = CR._recovered(A2, 22000)
    assert got is not None
    assert sha(got).startswith("c534022d")
    assert CR._recovered(A2, 10 ** 9) is not None


def test_no_stale_era_less_body_is_registered_for_a_timed_path():
    """The index itself must not carry both shapes for one path."""
    timed, plain = set(), set()
    for line in io.open(os.path.join(R, "recovered", "RECOVERED.tsv"),
                        encoding="utf-8"):
        if not line.strip():
            continue
        parts = line.rstrip("\n").split("\t")
        (timed if len(parts) > 2 else plain).add(parts[1])
    assert not (timed & plain), sorted(timed & plain)
