"""A TREE SIBLING is not a temporary producer (Codex SEQ 1547 defect 2).

A source under `scratchpad/<tree>/...` has its own committed or recovered history and
is already owned by the sibling resolver; it must be RESOLVED at the consuming cutoff,
not executed as an ephemeral side-file producer against the consuming owner. Only a
genuine temporary file - one with no tree of its own - belongs in a consumer's extra
producer route.

My first version of this suite was not proof: it asserted `writes_this(22765, raw) is
False` while simultaneously REQUIRING 22765 in raw's producer map, which is the very
defect. The controls below are the three live routes, from fresh state.
"""
import contextlib
import hashlib
import io
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
import chrono_replay as CR                                    # noqa: E402
import replay_transcript as RT                                # noqa: E402

H = "bench_1306/.claude/plans/Drivers/experiments/harness/"
SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/"


def route(owner, upto):
    o = CR.tree_origin("bench_1306")
    with contextlib.redirect_stdout(io.StringIO()):
        return CR.route_records(owner, o[0], upto)


def replay_to(owner, upto):
    o = CR.tree_origin("bench_1306")
    recs, prod = route(owner, upto)
    text = RT._committed("/x/" + owner, commit=o[1]) or ""
    refused = []
    side = {}
    for n, rec in recs:
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                text, _ = RT.apply_saved_edits(text, {n: rec}, owner, side=side)
            except Exception as exc:                          # noqa: BLE001
                refused.append((n, type(exc).__name__))
    return recs, prod, text, refused


def test_a_source_with_its_own_TREE_is_not_a_producer():
    """The general rule, stated on paths alone: a tree-qualified source belongs to the
    sibling resolver; only a tree-less scratch file is an ephemeral producer."""
    tree_sibling = (SCRATCH + "s/scratchpad/bench_1306/.claude/plans/Drivers/"
                    "experiments/one_item_benchmark_inventory.json")
    other_tree = (SCRATCH + "s/scratchpad/step1_iso/.claude/plans/Drivers/"
                  "experiments/harness/audit_worker_access.py")
    side_file = "/tmp/claude-1000/rt_keep.py"
    assert CR.is_side_file(tree_sibling) is False
    assert CR.is_side_file(other_tree) is False
    assert CR.is_side_file(side_file) is True


def test_raw_transport_route_carries_only_its_true_side_file():
    recs, prod, text, refused = replay_to(H + "raw_transport.py", 32847)
    assert sorted(prod) == [25922], sorted(prod)
    assert len(recs) == 43, len(recs)
    assert hashlib.sha256(text.encode()).hexdigest() == (
        "12d4aca9a7bfd9a51303271b54433ad55058dad268e771cff757a3ea0b68a14a")
    assert len(text.encode()) == 75368
    assert refused == [(26845, "TypeError")], refused


def test_audit_worker_route_carries_only_its_two_true_side_files():
    """The producer map is the two real side files. The RECORD COUNT stays 28, not 25:
    23488, 24938 and 24948 are ALSO genuine owner records - each does
    `cat > $H/audit_worker_access.py` with `$H` inside bench_1306 - so removing them
    would discard real writes. They entered the producer map only because they also
    named the step1_iso copy as a source; excluding them from PRODUCERS is the fix,
    excluding them from the route is not. The final bytes are identical either way."""
    recs, prod, text, refused = replay_to(H + "audit_worker_access.py", 33828)
    assert sorted(prod) == [25442, 25450], sorted(prod)
    assert len(recs) == 28, len(recs)
    assert hashlib.sha256(text.encode()).hexdigest() == (
        "9e4762e56c527d95c68b3737dd41d1c478337ed6d38ec0017ea048a855c32229")
    assert len(text.encode()) == 50510
    assert refused == [], refused


def test_the_guards_four_extras_are_all_true_side_files():
    _recs, prod = route(H + "test_harness_guards.py", 34187)
    assert sorted(prod) == [24416, 26004, 26171, 26334], sorted(prod)
    for src in prod.values():
        assert CR.is_side_file(src), src


def test_the_three_disputed_records_really_do_write_THIS_owner():
    """Evidence for the count above, from the records themselves."""
    for line in (23488, 24938, 24948):
        rec = RT.lines([line])[line]
        cmd = None
        for b in ((rec.get("message") or {}).get("content") or []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                cmd = (b.get("input") or {}).get("command") or ""
        assert cmd is not None, line
        with contextlib.redirect_stdout(io.StringIO()):
            mine = CR.writes_this(cmd, H + "audit_worker_access.py", line)
            other = CR.writes_this(
                cmd, "step1_iso/.claude/plans/Drivers/experiments/harness/"
                     "audit_worker_access.py", line)
        assert mine is True, line
        assert other is False, line
