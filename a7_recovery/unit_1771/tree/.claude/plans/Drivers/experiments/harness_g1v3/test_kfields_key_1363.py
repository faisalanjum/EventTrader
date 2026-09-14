"""The SEQ 1363 boundaries: run integrity, the typed receipt, and the child.

A4 has never run, so a lawful official state cannot be borrowed from history:
the control below is SYNTHESISED and its official LOCATION check is the one
thing patched. Everything else - the launcher binding, state identity, agent
row, transcript identities, the proved chain and the returned result row - is
the owner's real logic against real bytes. Each mutation changes exactly one
field of that lawful control.

    venv/bin/python -m pytest <this file> -q
"""
import copy
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, "/home/faisal/EventMarketDB"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import audit_worker_access as AUD                                # noqa: E402
import build_kfields_key as K                                    # noqa: E402

_PROMPTS = {}


def prompt_for(item):
    if item["packet_id"] not in _PROMPTS:
        _PROMPTS[item["packet_id"]] = K.phase1_prompt(item)
    return _PROMPTS[item["packet_id"]]


@pytest.fixture
def official(tmp_path, monkeypatch):
    """A temp tree that the location owner accepts, and nothing else."""
    session = tmp_path / "projects" / K.PARENT_SESSION
    (session / "workflows").mkdir(parents=True)

    real_locator = AUD._official_location

    def located(state_path):
        real = os.path.realpath(str(state_path))
        if real.startswith(os.path.realpath(str(session))):
            return str(session), K.PARENT_SESSION
        # anything outside the temp tree keeps its REAL answer: this fixture
        # must not blind the owner to the genuine A3 evidence
        return real_locator(state_path)

    monkeypatch.setattr(AUD, "_official_location", located)
    return session


def build_call(session, item, answer, attempt=1, run_id="wf_lawful",
               doc_mutate=None, rec_mutate=None, transcript=True):
    """One lawful official call: state + transcript that agree exactly."""
    prompt = prompt_for(item)
    agent = "agent_" + run_id
    # every identity is unique PER CALL: a real run never reuses a response id,
    # and the owner refuses reuse across the run
    u0, u1 = "u0_" + run_id, "u1_" + run_id
    recs = [
        {"type": "user", "uuid": u0, "parentUuid": None, "agentId": agent,
         "sessionId": K.PARENT_SESSION,
         "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "uuid": u1, "parentUuid": u0,
         "agentId": agent, "sessionId": K.PARENT_SESSION, "effort": K.EFFORT,
         "requestId": "req_" + run_id,
         "message": {"role": "assistant", "id": "msg_" + run_id,
                     "model": K.RUNTIME_MODEL_ID, "stop_reason": "end_turn",
                     "content": [{"type": "text", "text": answer}]}},
    ]
    if rec_mutate:
        rec_mutate(recs)
    if transcript:
        tdir = session / "subagents" / "workflows" / run_id
        tdir.mkdir(parents=True, exist_ok=True)
        with io.open(str(tdir / ("agent-%s.jsonl" % agent)), "w",
                     encoding="utf-8") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
    # THE REAL ONE-AGENT SHAPE: a one-agent Workflow puts the returned value
    # directly on `.result`, and the row is state "done" (precedent
    # wf_a96a6985-aa2). There is no `results` list here.
    doc = {
        "runId": run_id, "status": "completed", "totalToolCalls": 0,
        "script": K.render_launcher(item, attempt),
        "workflowProgress": [{"type": "workflow_agent", "state": "done",
                              "label": item["packet_id"], "agentId": agent,
                              "model": K.RUNTIME_MODEL_ID,
                              "agentType": K.AGENT_TYPE, "toolCalls": 0}],
        "result": {"packet_id": item["packet_id"],
                   "source_id": item["source_id"], "attempt": attempt,
                   "model": K.MODEL, "effort": K.EFFORT,
                   "agentType": K.AGENT_TYPE,
                   "text": recs[-1]["message"]["content"][-1]["text"]
                   if recs[-1].get("type") == "assistant" else None},
    }
    if doc_mutate:
        doc_mutate(doc)
    path = session / "workflows" / ("%s.json" % run_id)
    io.open(str(path), "w", encoding="utf-8").write(json.dumps(doc))
    return str(path)


def _reject_row(doc):
    """The one shape a GENUINE pre-agent rejection has: the runtime's own
    structured evidence, and a returned object whose text is null."""
    doc["workflowProgress"] = [{"type": "workflow_agent", "state": "error",
                                "blocked": True, "error": "no capacity",
                                "label": doc["result"]["packet_id"],
                                "agentType": K.AGENT_TYPE}]
    doc["result"]["text"] = None


def lawful_answer(item):
    """A settled reply that is lawful AND states the derived match truth."""
    body = ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "the '
            'scale marker sits outside the quote"}], "continuity_hints": []}'
            % json.dumps(item["source_id"]))
    settled = K.completed_draft(item, body)
    rows = []
    for d in item["a3_drafts"]:
        # the SAME owner the production path uses; a helper with its own
        # notion of "same answer" would be the second schema Codex forbade
        same = K._same_answer(K.completed_draft(item, d["text"]), settled)
        rows.append('{"lane_id": %s, "exact_match": %s, "why": "compared"}'
                    % (json.dumps(d["lane_id"]), "true" if same else "false"))
    return ('{"packet_id": %s, "settled": %s, "reconciliation": [%s], '
            '"ambiguities": []}'
            % (json.dumps(item["packet_id"]), body, ", ".join(rows)))


def primary_with(tmp_path, session, states):
    """A prepared primary with these built states recorded."""
    out = str(tmp_path / "primary")
    assert K.prepare_run(out)["ok"] is True
    for path in states:
        assert K.record_state(out, path) == []
    return out


# ------------------------------------------------- 1. run-level integrity ---
def test_a_lawful_official_call_is_proved_and_credited(tmp_path, official):
    item = K.phase1_items()[0]
    path = build_call(official, item, lawful_answer(item))
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, problems = K.run_evidence(out, receipt)
    assert problems == [], problems[:3]
    assert proved[item["packet_id"]][0] == "proved"
    doc = K.finalize(out)
    assert doc["ledger"]["valid"] == 1, doc["problems"][:3]


@pytest.mark.parametrize("what", [
    "delete_result", "substitute_result_text", "change_result_packet",
    "change_runid", "change_script", "drop_script", "agent_row_error",
    "change_record_agentid", "change_record_sessionid", "extra_result_key",
    "change_result_attempt", "change_result_agenttype", "change_result_source",
    "change_result_model", "change_result_effort", "wrong_scriptpath",
    "queued_row"])
def test_every_run_integrity_mutation_refuses(tmp_path, official, what):
    item = K.phase1_items()[0]
    answer = lawful_answer(item)

    def dm(doc):
        if what == "delete_result":
            doc.pop("result")
        elif what == "substitute_result_text":
            doc["result"]["text"] = "SUBSTITUTED"
        elif what == "change_result_packet":
            doc["result"]["packet_id"] = "not-this-packet"
        elif what == "change_runid":
            doc["runId"] = "wf_somethingelse"
        elif what == "change_script":
            doc["script"] = "// not the pinned launcher"
        elif what == "drop_script":
            doc.pop("script")
        elif what == "agent_row_error":
            doc["workflowProgress"][0]["state"] = "error"
        elif what == "extra_result_key":
            doc["result"]["sneaky"] = 1
        elif what == "change_result_attempt":
            doc["result"]["attempt"] = 2
        elif what == "change_result_agenttype":
            doc["result"]["agentType"] = "general-purpose"
        elif what == "change_result_source":
            doc["result"]["source_id"] = "another-source"
        elif what == "change_result_model":
            doc["result"]["model"] = "opus"
        elif what == "change_result_effort":
            doc["result"]["effort"] = "low"
        elif what == "wrong_scriptpath":
            doc["scriptPath"] = "/definitely/not/the/reviewed/launcher.js"
        elif what == "queued_row":
            doc["workflowProgress"][0]["state"] = "queued"

    def rm(recs):
        if what == "change_record_agentid":
            recs[1]["agentId"] = "someone-else"
        elif what == "change_record_sessionid":
            recs[1]["sessionId"] = "another-session"

    path = build_call(official, item, answer, doc_mutate=dm, rec_mutate=rm)
    out = primary_with(tmp_path, official, [path])
    doc = K.finalize(out)
    assert doc["ledger"]["valid"] == 0, "%s was credited" % what
    assert doc["retry"] == [], "%s earned a retry" % what
    assert doc["problems"], "%s produced no problem" % what
    # the paid bytes survive every one of them
    raws = os.listdir(os.path.join(out, "raw"))
    if what != "delete_result":
        assert raws, "%s lost the paid raw" % what


def test_a_reused_agent_or_run_identity_refuses(tmp_path, official):
    items = K.phase1_items()[:2]
    a = build_call(official, items[0], lawful_answer(items[0]),
                   run_id="wf_same")
    # a second call whose transcript reuses the first worker's identity
    b = build_call(official, items[1], lawful_answer(items[1]),
                   run_id="wf_other",
                   rec_mutate=lambda recs: [r.__setitem__("agentId",
                                                          "agent_wf_same")
                                            for r in recs])
    out = primary_with(tmp_path, official, [a, b])
    doc = K.finalize(out)
    assert doc["ledger"]["valid"] <= 1
    assert doc["problems"]


# ------------------------------------------------------- 2. typed receipt ---
@pytest.mark.parametrize("field,value", [
    ("run_id", "someone-else"), ("door", "another-door"),
    ("rules_sha256", "0" * 64), ("transport", {}), ("prompts", {}),
    ("a3_binding", {}), ("manifest_sha256", "0" * 64),
    ("allowed", ["only-one"]), ("parent", {"run_id": "x"})])
def test_every_immutable_receipt_field_is_verified(tmp_path, field, value):
    out = str(tmp_path / "r")
    K.prepare_run(out)
    path = os.path.join(out, "receipt.json")
    rec = json.load(io.open(path, encoding="utf-8"))
    rec[field] = value
    io.open(path, "w", encoding="utf-8").write(json.dumps(rec))
    assert K.receipt_problems(out, rec), "%s was accepted" % field


def test_an_unexpected_receipt_field_refuses(tmp_path):
    out = str(tmp_path / "r2")
    K.prepare_run(out)
    rec = json.load(io.open(os.path.join(out, "receipt.json"),
                            encoding="utf-8"))
    rec["sneaky"] = 1
    assert K.receipt_problems(out, rec)


def test_a_forged_parent_hash_earns_no_credit(tmp_path, official):
    """A lawful answer under a forged child receipt must credit nothing."""
    item = K.phase1_items()[0]
    child = str(tmp_path / "p" / "retry")
    os.makedirs(child)
    K._write_receipt(child, 2, [item["packet_id"]],
                     parent={"run_id": "p", "finalization_sha256": "0" * 64})
    path = build_call(official, item, lawful_answer(item), attempt=2)
    assert K.record_state(child, path) == []
    doc = K.finalize(child)
    assert doc["ledger"]["valid"] == 0
    assert doc["problems"]
    assert os.listdir(os.path.join(child, "raw")), "paid raw was lost"


# --------------------------------------------------- 3. the child gate ------
def test_one_invalid_and_the_rest_missing_creates_no_child(tmp_path, official):
    item = K.phase1_items()[0]
    path = build_call(official, item, "{not json at all")
    out = primary_with(tmp_path, official, [path])
    doc = K.finalize(out)
    assert doc["ledger"]["missing"] == doc["ledger"]["scheduled"] - 1
    assert doc["primary_complete"] is False
    assert doc["retry"] == []
    assert not os.path.isdir(os.path.join(out, "retry"))


def test_a_complete_primary_with_one_invalid_creates_one_runnable_child(
        tmp_path, official):
    """The whole lawful route, at full 196 scale."""
    items = K.phase1_items()
    states = []
    for n, item in enumerate(items):
        answer = "{not json" if n == 3 else lawful_answer(item)
        states.append(build_call(official, item, answer,
                                 run_id="wf_%03d" % n))
    out = primary_with(tmp_path, official, states)
    doc = K.finalize(out)
    assert doc["problems"] == [], doc["problems"][:3]
    assert doc["primary_complete"] is True
    assert doc["ledger"]["valid"] == len(items) - 1
    assert doc["ledger"]["invalid_response"] == 1
    assert doc["retry"] == [items[3]["packet_id"]]
    child = doc["child"]
    assert child["invocations"] and len(child["invocations"]) == 1
    assert child["invocations"][0]["packet_id"] == items[3]["packet_id"]
    assert child["invocations"][0]["attempt"] == 2
    assert child["invocations"][0]["script"]
    # and the child closes out with NO successor
    cdoc = K.finalize(child["dir"])
    assert cdoc["retry"] == []


def test_a_proved_transport_no_answer_retries_but_a_proof_fault_does_not(
        tmp_path, official):
    items = K.phase1_items()
    states = []
    for n, item in enumerate(items):
        if n == 7:
            # a GENUINE service rejection, in the runtime's own structured
            # shape: blocked, an error signal, and no worker fields at all
            states.append(build_call(
                official, item, lawful_answer(item), run_id="wf_%03d" % n,
                doc_mutate=_reject_row, transcript=False))
        else:
            states.append(build_call(official, item, lawful_answer(item),
                                     run_id="wf_%03d" % n))
    out = primary_with(tmp_path, official, states)
    doc = K.finalize(out)
    assert doc["ledger"]["transport_no_answer"] == 1, doc["problems"][:3]
    assert doc["primary_complete"] is True
    assert doc["retry"] == [items[7]["packet_id"]]


def test_an_unproved_call_never_retries_and_blocks_the_child(tmp_path,
                                                             official):
    items = K.phase1_items()
    states = []
    for n, item in enumerate(items):
        states.append(build_call(
            official, item, lawful_answer(item), run_id="wf_%03d" % n,
            doc_mutate=(lambda doc: doc.update({"script": "// wrong"}))
            if n == 5 else None))
    out = primary_with(tmp_path, official, states)
    doc = K.finalize(out)
    assert doc["ledger"]["unproved"] == 1
    assert doc["primary_complete"] is False
    assert doc["retry"] == []
    assert not os.path.isdir(os.path.join(out, "retry"))


# ================================ SEQ 1364: the real one-agent seam ========

def test_a_two_response_continuation_binds_final_and_parses_complete(
        tmp_path, official):
    """The chain owner keeps FINAL and COMPLETE distinct, and so must we: the
    returned text is the LAST segment, while parsing consumes the whole answer.
    A run that compared the result to `complete`, or parsed `final`, fails here.
    """
    item = K.phase1_items()[0]
    whole = lawful_answer(item)
    cut = len(whole) // 2
    head, tail = whole[:cut], whole[cut:]
    run_id, agent = "wf_cont", "agent_wf_cont"

    def rec_mutate(recs):
        recs[1]["message"]["stop_reason"] = "max_tokens"
        recs[1]["message"]["content"] = [{"type": "text", "text": head}]
        recs.append({
            "type": "assistant", "uuid": "u2_" + run_id, "parentUuid":
            "u1_" + run_id, "agentId": agent, "sessionId": K.PARENT_SESSION,
            "effort": K.EFFORT, "requestId": "req2_" + run_id,
            "message": {"role": "assistant", "id": "msg2_" + run_id,
                        "model": K.RUNTIME_MODEL_ID,
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": tail}]}})

    path = build_call(official, item, whole, run_id=run_id,
                      rec_mutate=rec_mutate)
    doc_json = json.load(io.open(path, encoding="utf-8"))
    assert doc_json["result"]["text"] == tail, "the control must return FINAL"
    out = primary_with(tmp_path, official, [path])
    doc = K.finalize(out)
    assert doc["problems"] == [], doc["problems"][:3]
    assert doc["ledger"]["valid"] == 1, "the whole answer was not parsed"


def test_a_result_equal_to_complete_instead_of_final_refuses(tmp_path,
                                                            official):
    """MUTATION: returning the CONCATENATION instead of the final segment."""
    item = K.phase1_items()[0]
    whole = lawful_answer(item)
    cut = len(whole) // 2
    head, tail = whole[:cut], whole[cut:]
    run_id, agent = "wf_cont2", "agent_wf_cont2"

    def rec_mutate(recs):
        recs[1]["message"]["stop_reason"] = "max_tokens"
        recs[1]["message"]["content"] = [{"type": "text", "text": head}]
        recs.append({
            "type": "assistant", "uuid": "u2_" + run_id, "parentUuid":
            "u1_" + run_id, "agentId": agent, "sessionId": K.PARENT_SESSION,
            "effort": K.EFFORT, "requestId": "req2_" + run_id,
            "message": {"role": "assistant", "id": "msg2_" + run_id,
                        "model": K.RUNTIME_MODEL_ID,
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": tail}]}})

    path = build_call(official, item, whole, run_id=run_id,
                      rec_mutate=rec_mutate,
                      doc_mutate=lambda d: d["result"].update({"text": whole}))
    out = primary_with(tmp_path, official, [path])
    doc = K.finalize(out)
    assert doc["ledger"]["valid"] == 0
    assert doc["retry"] == []


def test_an_arbitrary_error_row_is_unproved_and_never_retries(tmp_path,
                                                              official):
    """Only the runtime's OWN structured rejection may retry."""
    item = K.phase1_items()[0]

    def dm(doc):
        doc["workflowProgress"][0]["state"] = "error"   # no blocked flag

    path = build_call(official, item, lawful_answer(item), doc_mutate=dm)
    out = primary_with(tmp_path, official, [path])
    doc = K.finalize(out)
    assert doc["ledger"]["unproved"] == 1
    assert doc["ledger"]["transport_no_answer"] == 0
    assert doc["retry"] == []


def test_the_a3_audit_is_never_cached(monkeypatch):
    """A dependency may drift while the receipt stays byte-identical, so a
    receipt-keyed cache would keep returning a stale clean answer."""
    import audit_worker_access as AUD
    first = K.a3_evidence()
    assert first["problems"] == [], first["problems"][:2]
    real = AUD.audit
    monkeypatch.setattr(AUD, "audit",
                        lambda p, *a, **k: dict(real(p, *a, **k),
                                                problems=["DEPENDENCY DRIFT"]))
    again = K.a3_evidence()
    assert any("DEPENDENCY DRIFT" in p for p in again["problems"]), \
        "a stale cached audit survived a dependency drift"


# ============ SEQ 1365: a rejection must be OFFICIAL before it may retry ====

def _rejection_call(session, item, run_id="wf_reject", doc_mutate=None):
    """A lawful pre-agent rejection: official, no worker, null-text object."""
    def dm(doc):
        _reject_row(doc)
        if doc_mutate:
            doc_mutate(doc)
    return build_call(session, item, lawful_answer(item), run_id=run_id,
                      doc_mutate=dm, transcript=False)


def test_a_lawful_pre_agent_rejection_is_the_one_retryable_outcome(
        tmp_path, official):
    """LAWFUL CONTROL: official, structured, no worker, null text."""
    item = K.phase1_items()[0]
    path = _rejection_call(official, item)
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, problems = K.run_evidence(out, receipt)
    assert problems == [], problems[:3]
    assert proved[item["packet_id"]][0] == "transport_no_answer"


def test_codexs_non_official_blocked_probe_is_unproved(tmp_path, official):
    """MUTATION: the exact hand-written file that used to earn a paid retry."""
    item = K.phase1_items()[0]
    probe = str(tmp_path / "a4_nonofficial_blocked_probe.json")
    doc = {"runId": "a4_nonofficial_blocked_probe", "status": "completed",
           "script": K.render_launcher(item, 1), "totalToolCalls": 0,
           "workflowProgress": [{"type": "workflow_agent", "state": "error",
                                 "blocked": True, "error": "no capacity",
                                 "label": item["packet_id"],
                                 "agentType": K.AGENT_TYPE}],
           "result": None}
    io.open(probe, "w", encoding="utf-8").write(json.dumps(doc))
    out = primary_with(tmp_path, official, [probe])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, problems = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved"
    assert problems
    doc2 = K.finalize(out)
    assert doc2["retry"] == [] and doc2["ledger"]["valid"] == 0


def test_a_blocked_row_with_a_real_transcript_is_a_contradiction(tmp_path,
                                                                 official):
    """MUTATION: a lane rejected before any model response cannot also answer."""
    item = K.phase1_items()[0]
    path = build_call(official, item, lawful_answer(item),
                      run_id="wf_contradiction", doc_mutate=_reject_row,
                      transcript=True)
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved"


@pytest.mark.parametrize("what", ["bad_runid", "wrong_script",
                                  "wrong_scriptpath", "result_none",
                                  "wrong_result_packet", "text_not_null",
                                  "not_completed", "not_blocked"])
def test_the_common_checks_run_before_the_rejection_branch(tmp_path, official,
                                                           what):
    """Every common check must bite on the REJECTION path too."""
    item = K.phase1_items()[0]

    def dm(doc):
        if what == "bad_runid":
            doc["runId"] = "wf_somethingelse"
        elif what == "wrong_script":
            doc["script"] = "// not the reviewed launcher"
        elif what == "wrong_scriptpath":
            doc["scriptPath"] = "/definitely/not/the/reviewed/launcher.js"
        elif what == "result_none":
            doc["result"] = None
        elif what == "wrong_result_packet":
            doc["result"]["packet_id"] = "not-this-packet"
        elif what == "text_not_null":
            doc["result"]["text"] = "an answer a rejected lane cannot have"
        elif what == "not_completed":
            doc["status"] = "failed"
        elif what == "not_blocked":
            doc["workflowProgress"][0].pop("blocked")

    path = _rejection_call(official, item, run_id="wf_r_" + what,
                           doc_mutate=dm)
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved", "%s was accepted" % what


# ==== SEQ 1366: pre-agent means zero worker and zero tools =================

def test_a_user_only_ghost_transcript_refuses_the_rejection(tmp_path,
                                                            official):
    """MUTATION: a transcript with only a user record still proves a worker
    was spawned, which a pre-agent rejection cannot have."""
    item = K.phase1_items()[0]
    path = _rejection_call(official, item, run_id="wf_ghost")
    tdir = official / "subagents" / "workflows" / "wf_ghost"
    tdir.mkdir(parents=True, exist_ok=True)
    io.open(str(tdir / "agent-ghost.jsonl"), "w", encoding="utf-8").write(
        json.dumps({"type": "user", "uuid": "g0", "parentUuid": None,
                    "agentId": "ghost", "sessionId": K.PARENT_SESSION,
                    "message": {"role": "user", "content": "x"}}) + "\n")
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved"


def test_a_rejection_recording_tool_calls_refuses(tmp_path, official):
    """MUTATION: totalToolCalls 1 means work happened before the claim."""
    item = K.phase1_items()[0]
    path = _rejection_call(official, item, run_id="wf_tools",
                           doc_mutate=lambda d: d.update({"totalToolCalls": 1}))
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved"


# ==== SEQ 1367: zero tool use must be a RECORDED integer zero ==============

_NOT_ZERO = [("absent", "ABSENT"), ("null", None), ("false", False),
             ("empty_text", ""), ("empty_list", []), ("empty_object", {}),
             ("float_zero", 0.0)]


def test_a_recorded_integer_zero_is_the_lawful_control(tmp_path, official):
    """LAWFUL CONTROL: the field is present, an int, and exactly 0."""
    item = K.phase1_items()[0]
    path = _rejection_call(official, item, run_id="wf_int0",
                           doc_mutate=lambda d: d.update({"totalToolCalls": 0}))
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "transport_no_answer"


@pytest.mark.parametrize("name,value", _NOT_ZERO,
                         ids=[n for n, _v in _NOT_ZERO])
def test_untyped_or_missing_tool_counts_refuse(tmp_path, official, name,
                                               value):
    """MUTATION: none of these prove zero tool use."""
    item = K.phase1_items()[0]

    def dm(doc):
        if value == "ABSENT":
            doc.pop("totalToolCalls", None)
        else:
            doc["totalToolCalls"] = value

    path = _rejection_call(official, item, run_id="wf_tz_" + name,
                           doc_mutate=dm)
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved", "%s was accepted" % name


# ==== SEQ 1368: the zero-tool proof class, closed on BOTH paths ============

_NOT_ZERO_DONE = [("absent", "ABSENT"), ("null", None), ("false", False),
                  ("empty_text", ""), ("empty_list", []),
                  ("empty_object", {}), ("float_zero", 0.0)]


def test_an_answered_call_with_recorded_integer_zeros_is_proved(tmp_path,
                                                                official):
    """LAWFUL CONTROL for the DONE path: both counts are real integer zeros."""
    item = K.phase1_items()[0]
    path = build_call(official, item, lawful_answer(item), run_id="wf_z_ok")
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, problems = K.run_evidence(out, receipt)
    assert problems == [], problems[:3]
    assert proved[item["packet_id"]][0] == "proved"


@pytest.mark.parametrize("where", ["row_toolCalls", "run_totalToolCalls"])
@pytest.mark.parametrize("name,value", _NOT_ZERO_DONE,
                         ids=[n for n, _v in _NOT_ZERO_DONE])
def test_an_untyped_tool_count_refuses_on_the_done_path(tmp_path, official,
                                                        where, name, value):
    """MUTATION: neither count may be absent or wrongly typed."""
    item = K.phase1_items()[0]

    def dm(doc):
        target = (doc["workflowProgress"][0] if where == "row_toolCalls"
                  else doc)
        key = "toolCalls" if where == "row_toolCalls" else "totalToolCalls"
        if value == "ABSENT":
            target.pop(key, None)
        else:
            target[key] = value

    path = build_call(official, item, lawful_answer(item),
                      run_id="wf_z_%s_%s" % (where, name), doc_mutate=dm)
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved", \
        "%s/%s was accepted" % (where, name)


def test_a_recorded_last_tool_name_refuses_even_with_a_clean_transcript(
        tmp_path, official):
    """MUTATION: the official state contradicts the transcript. The state's own
    evidence must not be silently ignored because the transcript looks clean."""
    item = K.phase1_items()[0]
    path = build_call(
        official, item, lawful_answer(item), run_id="wf_z_lasttool",
        doc_mutate=lambda d: d["workflowProgress"][0].update(
            {"lastToolName": "Read"}))
    out = primary_with(tmp_path, official, [path])
    receipt = json.load(io.open(os.path.join(out, "receipt.json"),
                                encoding="utf-8"))
    proved, _p = K.run_evidence(out, receipt)
    assert proved[item["packet_id"]][0] == "unproved"
