# -*- coding: utf-8 -*-
"""THE FRESH G1 INITIAL-GRADING PRE-CALL FREEZE (Codex SEQ 1524).

Build and freeze ONLY the G1 initial-grading package for the exact completed
producer, through the existing reviewed owners (a7_g1_build, a7_g1_workflow_gate)
UNCHANGED. Attempt 1 only; ZERO grader/model calls are armed here.

Every check is zero-call and derived from the live objects: the candidate/root/
prompt tree rebuild byte-identically, every batch is bound to the current
producer and one same-leg/same-event group, every lane occurs once, the two
blind lanes share one blind prompt and carry no answer, the Workflow script
groups come from the exact 524288-byte boundary, the run is empty and resumable,
and the admission preflight reports zero problems.
"""
import collections
import hashlib
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a7_g1_build as G                                          # noqa: E402
import a7_g1_workflow_gate as W                                  # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402

PRODUCER = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
            "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a6_a5run_1515")
ACCEPTED = "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d"

pytestmark = pytest.mark.skipif(
    not os.path.isfile(os.path.join(PRODUCER, "finalization.json")),
    reason="the finalized producer run is absent")

#: keys a launcher row / published arg may NEVER carry - a grader input that
#: named a verdict, a reply or the gold answer would not be blind.
_ANSWER_KEYS = ("answer", "reply", "verdict", "gold", "score", "result",
                "grade", "ruling", "decision")


def _candidate(tmp, ident, name):
    cd = str(tmp / name)
    path, problems = G.write(cd, ident)
    assert problems == [], problems
    return cd, G._sha_file(path), G._read(path)


def _root(cd, run_dir, cand_sha):
    root, root_sha, problems = G.freeze_root(cd, run_dir, cand_sha)
    assert problems == [], problems
    return root, root_sha


def _plan(cd, root):
    """The whole segment plan, derived read-only through the EXACT renderer."""
    lanes = [r["lane_id"] for r in root["rows"]]
    segs, rem = [], list(lanes)
    while rem:
        pfx, size, problems = W._largest_prefix(cd, root, rem, W.PRIMARY_ATTEMPT)
        assert problems == [] and pfx, (problems, len(pfx))
        segs.append((list(pfx), size))
        rem = rem[len(pfx):]
    return segs


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
    ident = PR.current(PRODUCER, ACCEPTED)
    base = tmp_path_factory.mktemp("g1pkg")
    cd, csha, doc = _candidate(base, ident, "cand")
    rd = str(base / "g1run")
    root, rsha = _root(cd, rd, csha)
    return dict(ident=ident, cd=cd, csha=csha, doc=doc, rd=rd, root=root,
                rsha=rsha, base=str(base))


# ============ 1. candidate / root / prompt tree rebuild byte-identically
def test_candidate_and_prompt_tree_and_root_rebuild_byte_identically(built,
                                                                     tmp_path):
    # candidate + prompt tree are path-independent -> byte-identical rebuild
    cd2, csha2, doc2 = _candidate(tmp_path, built["ident"], "cand2")
    assert csha2 == built["csha"]
    assert G.prompt_tree_sha(cd2, doc2) == built["root"]["prompt_tree_sha256"]
    # the root is byte-identical when rebuilt at the same run_id from the same
    # candidate dir (its only path-varying field is that run_id)
    twin = str(tmp_path / "twin" / os.path.basename(built["rd"]))
    os.makedirs(os.path.dirname(twin))
    _root2, rsha2 = _root(built["cd"], twin, built["csha"])
    assert rsha2 == built["rsha"]


# ============ 2. every batch bound to THIS producer and one same-event group
def test_every_batch_binds_the_current_producer_and_one_same_event(built):
    doc = built["doc"]
    assert doc["producer_identity"] == built["ident"]
    assert doc["producer_identity"]["a6_freeze_sha256"] == ACCEPTED
    assert doc["producer_identity"]["run_dir"] == os.path.abspath(PRODUCER)
    assert doc["producer_identity"]["a4_lock_sha256"]
    legs = set(doc["legs"])
    for row in doc["batch_rows"]:
        assert len(set(row["source_ids"])) == 1          # one event per batch
    # every graded question is a same-leg/same-event binding of a known leg,
    # routed to exactly the batch that names its event
    of_batch = {r["batch_id"]: set(r["source_ids"]) for r in doc["batch_rows"]}
    for q in doc["question_bindings"]:
        assert q["leg"] in legs
        assert of_batch[q["batch_id"]] == {q["source_id"]}


# ============ 3. every lane occurs exactly once
def test_every_lane_occurs_exactly_once(built):
    lanes = [r["lane_id"] for r in built["root"]["rows"]]
    assert len(lanes) == len(set(lanes))
    assert len(lanes) == built["doc"]["launchers"]["count"]
    assert len(lanes) == built["doc"]["batching"]["batches"] * len(G.GRADER_LANES)


# ============ 4. the two blind lanes share one blind prompt and see no answer
def test_two_blind_lanes_are_blind_and_carry_no_answer(built):
    root = built["root"]
    by_batch = collections.defaultdict(dict)
    for r in root["rows"]:
        batch, lane = r["lane_id"].split("/")
        by_batch[batch][lane] = r["prompt_sha256"]
    for batch, lanes in by_batch.items():
        # exactly the two named blind lanes, and a single shared blind prompt
        assert sorted(lanes) == sorted(G.GRADER_LANES)
        assert len(set(lanes.values())) == 1             # identical blind input
    # no published row (root or launcher) carries a verdict/reply/answer key
    for r in root["rows"] + built["doc"]["launchers"]["rows"]:
        assert not (set(r) & set(_ANSWER_KEYS))
    for key in G.ARG_KEYS:                                # the only args published
        assert key not in _ANSWER_KEYS


# ============ 5. Workflow script groups come from the exact 524288 boundary
def test_workflow_groups_are_maximal_under_the_exact_byte_boundary(built):
    cd, root = built["cd"], built["root"]
    segs = _plan(cd, root)
    covered = [lane for pfx, _s in segs for lane in pfx]
    assert covered == [r["lane_id"] for r in root["rows"]]   # cover, in order
    assert len(covered) == len(set(covered))
    for i, (pfx, size) in enumerate(segs):
        assert 0 < size <= W.SCRIPT_BYTE_LIMIT
        # MAXIMAL: every non-final segment is full - one more lane overflows
        if i + 1 < len(segs):
            nxt = segs[i + 1][0][0]
            over, problems = W._script_bytes(cd, root, pfx + [nxt],
                                             W.PRIMARY_ATTEMPT)
            assert problems == [] and over > W.SCRIPT_BYTE_LIMIT


# ============ 6. the run is empty and resumable
def test_the_run_is_empty_and_resumable(built):
    assert sorted(os.listdir(built["rd"])) == ["root.json"]
    assert G.segments(built["rd"]) == []
    lanes, size, problems = W.next_admissible(built["cd"], built["rd"],
                                              built["rsha"])
    assert problems == [] and lanes and 0 < size <= W.SCRIPT_BYTE_LIMIT
    # the admission gate's first segment IS the plan's first segment
    assert lanes == _plan(built["cd"], built["root"])[0][0]


# ============ 7. preflight (admission) reports zero problems; budget 5612->5818
def test_preflight_zero_problems_and_attempt1_budget_under_ceiling(built):
    _lanes, _size, problems = W.next_admissible(built["cd"], built["rd"],
                                                built["rsha"])
    assert problems == []
    b = built["doc"]["budget"]
    assert b["spent_before"] == 5612
    assert b["initial_grader_calls"] == built["doc"]["launchers"]["count"]
    assert b["after_initial"] == 5818 == b["spent_before"] + b["initial_grader_calls"]
    assert b["after_initial"] < b["ceiling"] == 6000
    # the retry worst-case is disclosed and NOT admitted: attempt 1 only
    assert b["after_max"] == 6024 > b["ceiling"]
    assert built["root"]["max_attempts"] == 2

    print("\nG1_PRECALL_COUNTS batches=%d launchers=%d lanes=%d "
          "segments=%d seg_lanes=%s script_bytes=%s prompt_min=%d prompt_max=%d "
          "spent_before=%d after_initial=%d after_max=%d ceiling=%d"
          % (built["doc"]["batching"]["batches"],
             built["doc"]["launchers"]["count"], len(built["root"]["rows"]),
             len(_plan(built["cd"], built["root"])),
             [len(p) for p, _s in _plan(built["cd"], built["root"])],
             [s for _p, s in _plan(built["cd"], built["root"])],
             built["doc"]["prompt_bytes"]["min"],
             built["doc"]["prompt_bytes"]["max"],
             b["spent_before"], b["after_initial"], b["after_max"], b["ceiling"]))
