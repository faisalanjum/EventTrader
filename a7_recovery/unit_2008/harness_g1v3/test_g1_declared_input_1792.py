# -*- coding: utf-8 -*-
"""ONE EXACT EXPECTED INPUT PER LANE (Codex SEQ 1794).

WHY THIS SUITE WAS REWRITTEN
    The first attempt allowed a declared attachment ANYWHERE in a transcript,
    run-wide. Codex SEQ 1793 proved that rule accepts three forged transcripts:
    one with the attachment DELETED, one carrying the right bytes under a WRONG
    OUTER RECORD TYPE, and one with the attachment MOVED to a later position.
    The old suite was green because its negatives never tried any of those.

    Those three are the first three cases below, and they are asked of the
    COMPLETE transcript input path - the real `_g1_transcript`, which runs the
    shape owner, the input owner AND the record chain - not of one owner alone.

WHAT THE RULE IS NOW
    Each lane carries its own expectation, frozen into the run root: either
    "no added input at all", or exactly ONE input at a declared record index,
    with a declared outer record type, whose payload field canonicalises to a
    declared sha256. Presence, position, type and bytes must all hold, and any
    other extra record is refused as it always was. Nothing is read from the
    transcript to decide what is allowed, and no payload appears in any code.

EVERY MUTATION IS ISOLATED
    `_relink` re-threads parentUuid after a structural edit, so the record
    chain stays valid and the ONLY fault left is the one under test. The last
    test deliberately skips the relink to prove the chain is still enforced.
"""
import copy
import hashlib
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import audit_worker_access as AUD                                # noqa: E402

R = "/home/faisal/EventMarketDB-driver-recovery"
CAP = R + "/a7_recovery/unit_1786/capture"
RUN = CAP + "/after/wf_41b934cf-f76"
STATE = CAP + "/after/wf_41b934cf-f76.json"
BEFORE = CAP + "/journal.before.jsonl"
PROFILES = R + "/a7_recovery/unit_1792/evidence/lane_input_profiles.json"
#: the ONE preserved worker that was started and never answered
INCOMPLETE = "a72461c662aeeac39"
#: the refusal the input owner names when the declared input is not where the
#: lane declares it. The tests assert on THIS, not merely on "something failed".
ABSENT = "declares is not at record"

_needs = pytest.mark.skipif(not os.path.isfile(STATE),
                            reason="the captured batch is absent")


# =============================================== the frozen declaration
def profiles():
    return json.load(io.open(PROFILES, encoding="utf-8"))


def served_spec():
    """The ONE input a newly served lane must carry, as frozen data."""
    return profiles()["expected_input_for_served_lanes"]


def canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


# =============================================== the real population
def population():
    """Served workers, from the journal AND the official rows - not the directory."""
    served = {}
    for line in io.open(RUN + "/journal.jsonl", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("type") == "result":
            served[rec["agentId"]] = rec
    state = json.load(io.open(STATE, encoding="utf-8"))
    official = {p["agentId"] for p in state.get("workflowProgress", [])
                if p.get("type") == "workflow_agent" and p.get("agentId")}
    assert set(served) == official, set(served) ^ official
    cached = {json.loads(l)["agentId"] for l in io.open(BEFORE, encoding="utf-8")
              if l.strip() and json.loads(l).get("type") == "result"}
    return sorted(served), sorted(cached), sorted(set(served) - cached)


def transcript(agent_id):
    """The owners' OWN whole-file reader: None if any line is malformed."""
    recs = AUD._jsonl(os.path.join(RUN, "agent-%s.jsonl" % agent_id))
    assert recs is not None, "agent %s has a malformed transcript line" % agent_id
    return recs


# =============================================== the complete input path
def judge(recs, agent_id, spec, tmp_path, rid="wf_under_test"):
    """The REAL `_g1_transcript` - shape, input topology AND record chain.

    Model and effort come from the transcript's own answer records: this suite
    is about the INPUT path, and the real caller's model/effort expectations are
    proved separately by the whole-run integration proof.
    """
    where = os.path.join(str(tmp_path), "subagents", "workflows", rid)
    os.makedirs(where, exist_ok=True)
    io.open(os.path.join(where, "agent-%s.jsonl" % agent_id), "w",
            encoding="utf-8").write("".join(json.dumps(r) + "\n" for r in recs))
    answer = next((r for r in recs if AUD._role(r) == "assistant"), {})
    content = (recs[0].get("message") or {}).get("content")
    pin = hashlib.sha256(content.encode("utf-8")).hexdigest() \
        if isinstance(content, str) else "?" * 64
    problems, _final, _complete = AUD._g1_transcript(
        str(tmp_path), recs[0].get("sessionId"), rid, agent_id, pin,
        (answer.get("message") or {}).get("model"), answer.get("effort"), {}, spec)
    return problems


def _fresh_uuid(recs):
    """A uuid no record in this transcript already carries."""
    used = {r.get("uuid") for r in recs}
    candidate = "00000000-0000-4000-8000-000000000000"
    while candidate in used:
        candidate = candidate[:-1] + "1"
    return candidate


def _extra_input_at(problems, index):
    """Was record `index` refused for being an input the lane never declared?"""
    return any(("record %d" % index) in str(p) and "message, not an object" in str(p)
               for p in problems)


def _identity_or_chain_problems(problems):
    """Anything the mutation was NOT meant to trip: identity, uuid or chain."""
    return [p for p in problems
            if "names agent" in str(p) or "names session" in str(p)
            or "repeats uuid" in str(p) or "does not link" in str(p)]


def _relink(recs):
    """Re-thread parentUuid so the ONLY remaining fault is the one under test."""
    out = [copy.deepcopy(r) for r in recs]
    for i, rec in enumerate(out):
        rec["parentUuid"] = out[i - 1].get("uuid") if i else None
    return out


def served_donor(min_records=0):
    """The first newly served worker with room for the case under test.

    Chosen by STRUCTURE, never by agent name: nineteen of the served workers
    answered in one record and eleven in two, and a case that needs a later
    lawful position needs one of the latter.
    """
    _served, _cached, new = population()
    for agent_id in new:
        recs = transcript(agent_id)
        if len(recs) >= min_records:
            return agent_id, recs
    pytest.skip("no served worker has %d records" % min_records)


# ---- THE THREE FORGERIES CODEX SEQ 1793 PROVED THE OLD RULE ACCEPTED --------
def forge_deleted(spec):
    """The declared input is simply GONE, and the chain is closed over it."""
    agent_id, recs = served_donor()
    return agent_id, _relink([r for i, r in enumerate(recs)
                              if i != spec["record_index"]])


def forge_wrong_outer_type(spec):
    """The declared BYTES, carried by a record of another outer type."""
    agent_id, recs = served_donor()
    out = [copy.deepcopy(r) for r in recs]
    out[spec["record_index"]]["type"] = "system"
    return agent_id, out


def forge_moved(spec):
    """The declared input, intact, at a LATER LAWFUL position.

    It must land somewhere the transcript still ends on its terminal answer,
    or the existing after-terminal rule refuses it for an unrelated reason and
    the case proves nothing - hence the donor with room after the move.
    """
    agent_id, recs = served_donor(spec["record_index"] + 3)
    out = [copy.deepcopy(r) for r in recs]
    out.insert(spec["record_index"] + 1, out.pop(spec["record_index"]))
    return agent_id, _relink(out)


FORGERIES = {"deleted": forge_deleted,
             "wrong_outer_type": forge_wrong_outer_type,
             "moved": forge_moved}


# =============================================== the population itself
@_needs
def test_the_served_population_is_the_thirty_four_the_receipt_pins():
    served, cached, new = population()
    assert (len(served), len(cached), len(new)) == (34, 4, 30)
    assert INCOMPLETE not in served, "the incomplete worker is not a served answer"
    assert os.path.isfile(RUN + "/agent-%s.jsonl" % INCOMPLETE), \
        "the incomplete worker's transcript must still be preserved"


@_needs
def test_the_frozen_declaration_covers_every_lane_and_matches_the_population():
    doc = profiles()
    per_lane = doc["profiles"]
    _served, cached, new = population()
    assert sum(1 for v in per_lane.values() if v is None) == len(cached)
    assert sum(1 for v in per_lane.values() if v is not None) == len(new)
    assert all(v == doc["expected_input_for_served_lanes"]
               for v in per_lane.values() if v is not None)


# =============================================== the real positives
@_needs
def test_control_every_newly_served_worker_passes_with_its_declared_input(tmp_path):
    _served, _cached, new = population()
    for agent_id in new:
        assert judge(transcript(agent_id), agent_id, served_spec(),
                     tmp_path / agent_id) == [], agent_id


@_needs
def test_control_every_precall_cached_worker_passes_with_no_added_input(tmp_path):
    _served, cached, _new = population()
    for agent_id in cached:
        assert judge(transcript(agent_id), agent_id, None,
                     tmp_path / agent_id) == [], agent_id


# =============================================== the three proved false accepts
@_needs
@pytest.mark.parametrize("name", sorted(FORGERIES))
def test_the_forgeries_codex_proved_are_refused(name, tmp_path):
    spec = served_spec()
    agent_id, recs = FORGERIES[name](spec)
    assert judge(recs, agent_id, spec, tmp_path), "%s must be refused" % name


@_needs
def test_a_missing_input_is_refused_by_name(tmp_path):
    """Refused FOR THE RIGHT REASON: the lane declares an input and has none."""
    spec = served_spec()
    agent_id, recs = forge_deleted(spec)
    got = judge(recs, agent_id, spec, tmp_path)
    assert any(ABSENT in str(p) for p in got), got


@_needs
def test_a_displaced_input_is_refused_where_it_actually_sits(tmp_path):
    """POSITION is the fault. One place later the record matches nothing, so it
    is refused as the message-less record it is, named at its real index - the
    shape owner reaches it before the absence is reported, and either way the
    lane refuses."""
    spec = served_spec()
    agent_id, recs = forge_moved(spec)
    got = judge(recs, agent_id, spec, tmp_path)
    assert any("record %d" % (spec["record_index"] + 1) in str(p) for p in got), got


@_needs
def test_the_forged_bytes_are_really_the_declared_ones():
    """The wrong-type forgery must carry the EXACT declared payload, and the
    moved one must stay lawful everywhere else, or neither proves anything."""
    spec = served_spec()
    _agent, recs = forge_wrong_outer_type(spec)
    rec = recs[spec["record_index"]]
    assert canon_sha(rec[spec["payload_field"]]) == spec["payload_sha256"]
    assert rec["type"] != spec["record_type"]
    _agent, moved = forge_moved(spec)
    assert moved[-1].get("type") == "assistant", \
        "the moved case must still end on the terminal answer"
    assert canon_sha(moved[spec["record_index"] + 1][spec["payload_field"]]) \
        == spec["payload_sha256"]


# =============================================== the cached control
@_needs
def test_the_approved_payload_injected_into_a_cached_worker_is_refused(tmp_path):
    """A lane that declares NO added input refuses this payload like any other.

    This is what binds the declaration to the lane: the four precall-cached
    lanes carry `null`, so the input the thirty served lanes legitimately carry
    buys nothing here.

    THE CASE IS ISOLATED. The donor record is copied for its PAYLOAD only: it is
    re-stamped with the cached worker's own agent and session identity and given
    a distinct uuid, and the chain is re-threaded, so the identity, uuid and
    chain owners have nothing to say and the ONLY fault left is the extra input
    (Codex SEQ 1795 item 1).
    """
    _served, cached, new = population()
    spec = served_spec()
    agent_id = cached[0]
    recs = transcript(agent_id)
    injected = copy.deepcopy(transcript(new[0])[spec["record_index"]])
    injected["agentId"] = recs[0].get("agentId")
    injected["sessionId"] = recs[0].get("sessionId")
    injected["uuid"] = _fresh_uuid(recs)
    forged = _relink(recs[:1] + [injected] + list(recs[1:]))
    assert canon_sha(forged[spec["record_index"]][spec["payload_field"]]) \
        == spec["payload_sha256"], "the injected payload must be the declared one"
    got = judge(forged, agent_id, None, tmp_path)
    assert _extra_input_at(got, spec["record_index"]), got
    assert not _identity_or_chain_problems(got), got


@_needs
def test_every_cached_lane_is_frozen_with_no_added_input():
    doc = profiles()
    cached_lanes = [k for k, v in doc["profiles"].items() if v is None]
    assert len(cached_lanes) == len(doc["precall_completed_agents"])
    assert cached_lanes, "the derivation must name the cached lanes"


# =============================================== the ordinary negatives
@_needs
def test_an_undeclared_payload_is_refused(tmp_path):
    _served, _cached, new = population()
    spec = served_spec()
    recs = [copy.deepcopy(r) for r in transcript(new[0])]
    field = spec["payload_field"]
    recs[spec["record_index"]][field] = dict(recs[spec["record_index"]][field],
                                             url="https://elsewhere")
    assert judge(recs, new[0], spec, tmp_path)


@_needs
def test_a_second_copy_of_the_declared_input_is_refused(tmp_path):
    """ISOLATED: only the synthetic extra copy is new, it carries its OWN uuid,
    and the chain is lawful - so the refusal is the extra input at the position
    the lane never declared, not a repeated uuid (Codex SEQ 1795 item 1)."""
    _served, _cached, new = population()
    spec = served_spec()
    agent_id = new[0]
    recs = transcript(agent_id)
    extra = copy.deepcopy(recs[spec["record_index"]])
    extra["uuid"] = _fresh_uuid(recs)
    forged = _relink(recs[:spec["record_index"] + 1] + [extra]
                     + list(recs[spec["record_index"] + 1:]))
    got = judge(forged, agent_id, spec, tmp_path)
    assert _extra_input_at(got, spec["record_index"] + 1), got
    assert not _identity_or_chain_problems(got), got


@_needs
def test_the_declared_input_may_not_displace_the_prompt(tmp_path):
    _served, _cached, new = population()
    spec = served_spec()
    recs = transcript(new[0])
    forged = _relink([copy.deepcopy(recs[spec["record_index"]])] + list(recs))
    assert judge(forged, new[0], spec, tmp_path)


@_needs
@pytest.mark.parametrize("spec", [
    None, {}, [], "", 0,
    {"record_index": 1, "record_type": "attachment", "payload_field": "attachment"},
    {"record_index": 1, "record_type": "attachment", "payload_field": "attachment",
     "payload_sha256": "25394a53"},
    {"record_index": True, "record_type": "attachment", "payload_field": "attachment",
     "payload_sha256": "2" * 64},
    {"record_index": 0, "record_type": "attachment", "payload_field": "attachment",
     "payload_sha256": "2" * 64}])
def test_a_malformed_or_absent_declaration_admits_nothing(spec, tmp_path):
    """With nothing lawfully declared, the served worker is refused as before -
    which is also the closed A1 route, untouched."""
    _served, _cached, new = population()
    assert judge(transcript(new[0]), new[0], spec, tmp_path)


@_needs
def test_the_record_chain_is_still_enforced(tmp_path):
    """Proof that `_relink` is what isolates the other cases: the same deletion
    WITHOUT re-threading is refused for the chain as well."""
    _served, _cached, new = population()
    spec = served_spec()
    recs = transcript(new[0])
    broken = [r for i, r in enumerate(recs) if i != spec["record_index"]]
    got = judge(broken, new[0], spec, tmp_path)
    assert any("does not link to the record before it" in str(p) for p in got), got
@_needs
def test_a_declared_index_past_the_end_of_the_transcript_is_refused(tmp_path):
    """A lane that declares an input nothing can satisfy refuses, rather than
    quietly accepting a transcript that simply has no such record.

    The refusal names record 1 rather than the absence: with the declaration
    pointing elsewhere, the record that IS there matches nothing and the shape
    owner reaches it first. Either way the lane refuses."""
    _served, _cached, new = population()
    recs = transcript(new[0])
    spec = dict(served_spec(), record_index=len(recs) + 5)
    got = judge(recs, new[0], spec, tmp_path)
    assert got, "an unsatisfiable declaration must refuse"


@_needs
def test_a_message_bearing_record_cannot_carry_the_declared_input(tmp_path):
    """The declared input is a message-LESS record. Giving it a message does
    not smuggle it past the topology owner."""
    _served, _cached, new = population()
    spec = served_spec()
    recs = [copy.deepcopy(r) for r in transcript(new[0])]
    recs[spec["record_index"]]["message"] = {"role": "user", "content": "anything"}
    got = judge(recs, new[0], spec, tmp_path)
    assert got, "a message-bearing record must not satisfy the declaration"
    assert any(ABSENT in str(p) for p in got), got
