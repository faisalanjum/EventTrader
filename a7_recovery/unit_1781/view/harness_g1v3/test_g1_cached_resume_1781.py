# -*- coding: utf-8 -*-
"""THE G1 NATIVE-RESUME COMPATIBILITY BOUNDARY (Codex SEQ 1781).

Two behaviours, each with its lawful control and its fail-closed negatives.

The cached rows here are a TEST FIXTURE: a private synthetic progress state
derived from a REAL restored official state, so that every agent id, agent
metadata file and child transcript behind it is genuine. It is never presented
as historical evidence and never as a native completion - it is the shape the
installed runtime emits for a cached return, built so the existing owners can
be asked whether they accept it.

Nothing here re-implements an owner: the decision is always the real
audit_worker_access, and the cached shape is always its own _resumed_cached_row.
"""
import copy
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import audit_worker_access as AUD                                # noqa: E402
import a7_g1_build as G                                          # noqa: E402

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
RUN = S + "/g1_precall_run_1525"
SESSION = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
           "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
STATE = SESSION + "/workflows/wf_85692dcf-0e8.json"
RID_DIR = SESSION + "/subagents/workflows/wf_85692dcf-0e8"
#: the DURABLE physical location of this unit's run, outside the namespace view
DURABLE_SCRIPT = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/"
                  "unit_1781/out/g1_precall_run_1525/grade_batch.seg01.js")

#: the exact progress fields the runtime OMITS on a cached return
OMITTED = ("agentType", "attempt", "toolCalls", "durationMs", "queuedAt",
           "tokens")

_needs = pytest.mark.skipif(not os.path.isfile(STATE),
                            reason="the restored G1 state is not bound")


def _root_and_receipt():
    rsha = G._sha_file(G.root_path(RUN))
    return rsha, G._sha_file(G.receipt_path(RUN, 1))


def _official_path():
    """Where the segment's receipt says its official state lives."""
    receipt = G._read(G.receipt_path(RUN, 1))
    return G._read(receipt["state_path"])["states"][0]


def _audit_through_the_owner():
    """The REAL caller builds every expectation; nothing is reconstructed."""
    rsha, rcpt = _root_and_receipt()
    return G.audit_official_state(RUN, 1, rsha, rcpt)


def _state():
    return json.load(io.open(_official_path(), encoding="utf-8"))


def _cached_state(mutate=None):
    """TEST FIXTURE: the same real state with its rows in the cached shape."""
    st = _state()
    for pr in st["workflowProgress"]:
        if pr.get("type") != "workflow_agent":
            continue
        for k in OMITTED:
            pr.pop(k, None)
        pr["cached"] = True
        pr["model"] = "sonnet"                    # the alias, as the runtime emits
        if mutate:
            mutate(pr)
    return st


def _audit_fixture(st):
    """Present a fixture state at the runtime location, then restore it."""
    p = _official_path()
    original = io.open(p, "rb").read()
    try:
        io.open(p, "w", encoding="utf-8").write(json.dumps(st))
        return _audit_through_the_owner()
    finally:
        io.open(p, "wb").write(original)


# =============================================== 1 the cached-row behaviour
@_needs
def test_control_the_unchanged_fresh_state_is_accepted(tmp_path):
    """The positive control: real rows, unchanged, must still pass."""
    assert _audit_through_the_owner() == []


@_needs
def test_a_lawful_cached_state_is_accepted(tmp_path):
    """The behaviour under correction: cached rows backed by real metadata."""
    assert _audit_fixture(_cached_state()) == []


@_needs
def test_a_cached_claim_with_the_wrong_alias_is_refused(tmp_path):
    got = _audit_fixture(_cached_state(lambda pr: pr.update(model="opus")))
    assert got, got  # refused either way; the correction names it "cached"


@_needs
def test_a_cached_claim_with_an_extra_field_is_refused(tmp_path):
    got = _audit_fixture(_cached_state(lambda pr: pr.update(toolCalls=0)))
    assert got, got  # refused either way; the correction names it "cached"


@_needs
def test_a_cached_flag_that_is_false_is_refused(tmp_path):
    got = _audit_fixture(_cached_state(lambda pr: pr.update(cached=False)))
    assert got, "a cached:false row must not pass as cached"


@_needs
def test_a_cached_claim_for_an_unknown_agent_is_refused(tmp_path):
    got = _audit_fixture(_cached_state(lambda pr: pr.update(agentId="a0000000000000000")))
    assert got, "a cached row with no agent metadata must be refused"


@_needs
def test_a_fresh_row_missing_its_agent_type_is_still_refused(tmp_path):
    """Ordinary fresh rows stay strict: dropping a field must not pass."""
    st = _state()
    for pr in st["workflowProgress"]:
        if pr.get("type") == "workflow_agent":
            pr.pop("agentType", None)
    got = _audit_fixture(st)
    assert got, "a fresh row missing agentType must still be refused"


# =============================================== 2 the durable script alias
@_needs
def test_control_the_exact_published_script_path_is_accepted(tmp_path):
    assert _audit_through_the_owner() == []


@_needs
def test_the_same_file_under_its_durable_path_is_accepted(tmp_path):
    """The REAL alias: the logical bind and the durable file are one file."""
    published = G._read(G.receipt_path(RUN, 1))["script_path"]
    # THE REAL ALIAS: a native Workflow runs OUTSIDE this namespace and names
    # the durable file on disk, while the publication names the logical bound
    # path. They are one file, reached by two names.
    durable = DURABLE_SCRIPT
    assert durable != published, "the two names must differ for this to test anything"
    st = _state()
    st["scriptPath"] = durable
    got = _audit_fixture(st)
    same = os.path.samefile(durable, published)
    assert same, "the boundary did not present one file under two paths"
    assert got == [], got


@_needs
def test_a_different_file_with_identical_bytes_is_refused(tmp_path):
    published = G._read(G.receipt_path(RUN, 1))["script_path"]
    twin = str(tmp_path / "twin.js")
    io.open(twin, "wb").write(io.open(published, "rb").read())
    st = _state()
    st["scriptPath"] = twin
    got = _audit_fixture(st)
    assert got, "identical bytes in a different file must not be accepted"


@_needs
def test_a_missing_script_path_is_refused(tmp_path):
    st = _state()
    st["scriptPath"] = str(tmp_path / "absent.js")
    assert _audit_fixture(st), "a missing script must be refused"


@_needs
def test_a_malformed_script_path_is_refused(tmp_path):
    st = _state()
    st["scriptPath"] = None
    assert _audit_fixture(st), "a null script path must be refused"


# ===================================================================
# THE FULL AFFECTED BOUNDARY (Codex SEQ 1782 item 1).
#
# Every negative below is ISOLATED - one thing wrong at a time - and each is
# paired with the lawful control above, so a refusal can never be credited to
# an unrelated root or hash mismatch. The agent directory these tests corrupt
# is a PRIVATE COPY bound only for this unit; published evidence and the live
# session are never written.
# ===================================================================
AGENTS = SESSION + "/subagents/workflows/wf_85692dcf-0e8"


def _first_agent_id():
    st = _state()
    for pr in st["workflowProgress"]:
        if pr.get("type") == "workflow_agent":
            return pr["agentId"]
    raise AssertionError("no agent row")


def _with_file(path, new_bytes):
    """Swap one private file, run the owner, restore it whatever happens."""
    original = io.open(path, "rb").read() if os.path.isfile(path) else None
    try:
        if new_bytes is None:
            if original is not None:
                os.unlink(path)
        else:
            io.open(path, "wb").write(new_bytes)
        return _audit_fixture(_cached_state())
    finally:
        if original is None:
            if os.path.isfile(path):
                os.unlink(path)
        else:
            io.open(path, "wb").write(original)


def _meta(agent_id):
    return os.path.join(AGENTS, "agent-%s.meta.json" % agent_id)


def _jsonl(agent_id):
    return os.path.join(AGENTS, "agent-%s.jsonl" % agent_id)


# ---- every cached key must be required -----------------------------------
@_needs
@pytest.mark.parametrize("key", sorted(AUD.CACHED_ROW_KEYS))
def test_a_cached_row_missing_any_required_key_is_refused(key):
    def drop(pr):
        pr.pop(key, None)
    got = _audit_fixture(_cached_state(drop))
    assert got, "a cached row without %r must be refused" % key


@_needs
@pytest.mark.parametrize("value", [None, 1, "true", 0, [], {}])
def test_a_non_boolean_cached_claim_is_refused(value):
    got = _audit_fixture(_cached_state(lambda pr: pr.update(cached=value)))
    assert got, "cached=%r must not be accepted" % (value,)


@_needs
def test_a_row_with_no_cached_key_at_all_is_judged_as_fresh():
    """Absent claim: it must be held to the strict fresh rules, not skipped."""
    def drop(pr):
        pr.pop("cached", None)
    got = _audit_fixture(_cached_state(drop))
    assert got, "a row with no cached key must face the fresh checks"


# ---- the agent metadata behind the claim ----------------------------------
@_needs
def test_a_cached_row_with_missing_metadata_is_refused():
    assert _with_file(_meta(_first_agent_id()), None)


@_needs
def test_a_cached_row_with_malformed_metadata_is_refused():
    assert _with_file(_meta(_first_agent_id()), b"{not json")


@_needs
@pytest.mark.parametrize("bad", [
    {"agentType": "other", "spawnDepth": 1, "model": "sonnet"},
    {"agentType": "lean-probe", "spawnDepth": 2, "model": "sonnet"},
    {"agentType": "lean-probe", "spawnDepth": 1, "model": "opus"},
    {"agentType": "lean-probe", "spawnDepth": 1},
    {"agentType": "lean-probe", "spawnDepth": 1, "model": "sonnet", "x": 1},
])
def test_a_cached_row_with_wrong_metadata_is_refused(bad):
    assert _with_file(_meta(_first_agent_id()),
                      json.dumps(bad).encode("utf-8")), bad


# ---- the child transcript is still fully checked --------------------------
def _corrupt_transcript(agent_id, mutate):
    recs = [json.loads(l) for l in io.open(_jsonl(agent_id), encoding="utf-8")
            if l.strip()]
    mutate(recs)
    body = "".join(json.dumps(r) + "\n" for r in recs).encode("utf-8")
    return _with_file(_jsonl(agent_id), body)


@_needs
def test_a_cached_row_with_a_corrupted_prompt_is_refused():
    def m(recs):
        recs[0]["message"]["content"] = "a different prompt entirely"
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_a_cached_row_with_a_corrupted_model_is_refused():
    def m(recs):
        for r in recs:
            if r.get("type") == "assistant":
                r["message"]["model"] = "claude-opus-4"
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_a_cached_row_with_a_corrupted_effort_is_refused():
    def m(recs):
        for r in recs:
            if "effort" in r:
                r["effort"] = "low"
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_a_cached_row_with_a_corrupted_session_is_refused():
    def m(recs):
        recs[0]["sessionId"] = "00000000-0000-0000-0000-000000000000"
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_a_cached_row_with_a_corrupted_agent_id_is_refused():
    def m(recs):
        for r in recs:
            r["agentId"] = "a0000000000000000"
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_a_cached_row_that_used_a_tool_is_refused():
    def m(recs):
        for r in recs:
            if r.get("type") == "assistant":
                c = r["message"]["content"]
                if isinstance(c, list):
                    c.append({"type": "tool_use", "id": "tu_1", "name": "Read",
                              "input": {}})
                    return
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_a_cached_row_with_corrupted_returned_text_is_refused():
    def m(recs):
        for r in reversed(recs):
            if r.get("type") == "assistant":
                c = r["message"]["content"]
                if isinstance(c, list) and c and isinstance(c[-1], dict):
                    c[-1]["text"] = "not the answer that was returned"
                    return
    assert _corrupt_transcript(_first_agent_id(), m)


@_needs
def test_two_lanes_reusing_one_response_identity_are_refused():
    """Cross-worker response reuse: one paid reply cannot answer two lanes."""
    st = _cached_state()
    rows = [pr for pr in st["workflowProgress"]
            if pr.get("type") == "workflow_agent"]
    rows[1]["agentId"] = rows[0]["agentId"]
    assert _audit_fixture(st), "one agent answering two lanes must be refused"


# ---- lawful mixed state ---------------------------------------------------
@_needs
def test_a_mixed_cached_and_fresh_state_is_accepted():
    """A real resume returns cached rows beside freshly spawned ones."""
    st = _state()
    rows = [pr for pr in st["workflowProgress"]
            if pr.get("type") == "workflow_agent"]
    for pr in rows[:len(rows) // 2]:
        for k in OMITTED:
            pr.pop(k, None)
        pr["cached"] = True
        pr["model"] = "sonnet"
    assert _audit_fixture(st) == [], "a lawful mixed state must be accepted"


# ---- the saved rows reconcile to the owner's own results -------------------
@_needs
def test_the_saved_rows_reconcile_to_the_owner_results():
    """The finite saved evidence, counted by the owners, not by this test."""
    total = valid = invalid = 0
    for n in (1, 2, 3):
        fin = G._read(os.path.join(RUN, "finalization.seg%02d.json" % n))
        led = fin["ledger"]
        total += led["scheduled"]
        valid += led["valid"]
        invalid += led["invalid"]
    assert total == 83, total
    assert valid == 82, valid
    assert invalid == 1, invalid          # the schema-invalid row, kept separate
