"""Codex SEQ 1380 — focused proof for the A4 37-call evidence/lifecycle route.

Build-only: no model call, no API, no database. Red first. Every negative has a
lawful control beside it, and the lawful fixture is scaffolding for shape and
identity, never evidence.

The shard helpers are IMPORTED from the SEQ 1379 battery, not copied, so a
change there cannot leave a stale twin passing here.
"""
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_final as F                                  # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import test_kfields_final_1379 as T9                             # noqa: E402

K, AUD = F.K, HR.AUD
EV, HRR, FIXR = T9.EV, T9.HRR, T9.FIXR


@pytest.fixture(scope="module")
def tasks():
    return F.event_tasks(EV)


@pytest.fixture
def pkg(tmp_path):
    out = str(tmp_path / "pkg")
    F.build(out, EV, HRR, FIXR)
    return out


@pytest.fixture
def bound(pkg):
    return F.Bound(pkg, EV, HRR, FIXR)


@pytest.fixture
def official(tmp_path, monkeypatch):
    """A temp tree the location owner accepts, and nothing else."""
    session = tmp_path / "projects" / K.PARENT_SESSION
    (session / "workflows").mkdir(parents=True)
    real = AUD._official_location

    def located(path):
        p = os.path.realpath(str(path))
        if p.startswith(os.path.realpath(str(session))):
            return str(session), K.PARENT_SESSION
        return real(path)

    monkeypatch.setattr(AUD, "_official_location", located)
    return session


# --------------------------------------------------------------- fixtures --
def build_call(session, bound, task, answer, attempt=1, run_id=None,
               script=None, doc_mutate=None, rec_mutate=None,
               session_id=None, transcript=True):
    """One lawful official A4 event call: state and transcript that agree."""
    label = task["source_id"]
    run_id = run_id or ("wf_" + label.replace("/", "_").replace("#", "_"))
    sid = session_id or K.PARENT_SESSION
    prompt = F.final_prompt(bound.evidence, bound.hr, bound.fix, task)
    agent = "agent_" + run_id
    u0, u1 = "u0_" + run_id, "u1_" + run_id
    recs = [
        {"type": "user", "uuid": u0, "parentUuid": None, "agentId": agent,
         "sessionId": sid, "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "uuid": u1, "parentUuid": u0, "agentId": agent,
         "sessionId": sid, "effort": K.EFFORT, "requestId": "req_" + run_id,
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
    doc = {
        "runId": run_id, "status": "completed", "totalToolCalls": 0,
        "script": script if script is not None else F.render_launcher(
            task, bound.evidence, bound.hr, bound.fix, attempt),
        "workflowProgress": [{"type": "workflow_agent", "state": "done",
                              "label": label, "agentId": agent,
                              "model": K.RUNTIME_MODEL_ID,
                              "agentType": K.AGENT_TYPE, "toolCalls": 0}],
        "result": {"source_id": label, "event_index": task["event_index"],
                   "rows": list(task["rows"]), "attempt": attempt,
                   "model": K.MODEL, "effort": K.EFFORT,
                   "agentType": K.AGENT_TYPE, "text": answer},
    }
    if doc_mutate:
        doc_mutate(doc)
    path = session / "workflows" / ("%s.json" % run_id)
    io.open(str(path), "w", encoding="utf-8").write(json.dumps(doc))
    return str(path)


def run_events(tmp_path, session, bound, tasks, answers=None, mutate=None,
               skip=()):
    """Schedule, serve and finalize a whole lawful event phase."""
    out = str(tmp_path / "events")
    prepared = F.prepare_events(out, bound)
    assert prepared["ok"], prepared["problems"]
    texts = answers or {}
    for task in tasks:
        if task["source_id"] in skip:
            continue
        answer = texts.get(task["source_id"]) or T9.shard_text(
            T9.shard_doc(task))
        kw = mutate(task) if mutate else {}
        F.record_state(out, build_call(session, bound, task, answer, **kw))
    return out, F.finalize(out, bound)


# ------------------------------------------------------ B: the schedule ----
def test_the_schedule_is_exactly_the_36_frozen_events_in_order(bound, tasks,
                                                               tmp_path):
    got = F.prepare_events(str(tmp_path / "e"), bound)
    assert got["ok"] and got["problems"] == []
    assert [i["label"] for i in got["invocations"]] == \
        [t["source_id"] for t in tasks]
    assert len(got["invocations"]) == 36


def test_every_invocation_is_a_real_runnable_file_bound_to_its_hash(bound,
                                                                    tmp_path):
    for inv in F.prepare_events(str(tmp_path / "e"), bound)["invocations"]:
        assert inv["args"] is None
        assert os.path.isfile(inv["scriptPath"])
        assert K._sha(K._read(inv["scriptPath"])) == inv["script_sha256"]


def test_a_used_directory_is_never_scheduled_over(bound, tmp_path):
    out = str(tmp_path / "e")
    assert F.prepare_events(out, bound)["ok"]
    again = F.prepare_events(out, bound)
    assert not again["ok"] and again["invocations"] == []


def test_a_dirty_package_is_never_scheduled(bound, tmp_path, monkeypatch):
    monkeypatch.setattr(F, "GLOBAL_CEILING", 10)
    got = F.prepare_events(str(tmp_path / "e"), bound)
    assert not got["ok"] and got["invocations"] == []


def test_the_lawful_receipt_is_accepted(bound, tmp_path):
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    assert F.receipt_problems(out, bound, receipt) == []


@pytest.mark.parametrize("mutate", [
    pytest.param(lambda r: r["allowed"].reverse(), id="swapped"),
    pytest.param(lambda r: r["allowed"].__setitem__(1, r["allowed"][0]),
                 id="duplicated"),
    pytest.param(lambda r: r["allowed"].pop(), id="missing"),
    pytest.param(lambda r: r["allowed"].append("extra"), id="extra"),
    pytest.param(lambda r: r["transport"].__setitem__("model", "other"),
                 id="transport"),
    pytest.param(lambda r: r.__setitem__("manifest_sha256", "0" * 64),
                 id="manifest"),
    pytest.param(lambda r: r["prompts"].__setitem__(
        sorted(r["prompts"])[0], "0" * 64), id="prompt"),
    pytest.param(lambda r: r["bound"].__setitem__("inventory", "0" * 64),
                 id="bound"),
    pytest.param(lambda r: r.__setitem__("surprise", 1), id="extra-field"),
    pytest.param(lambda r: r.__setitem__("attempt", 3), id="attempt"),
    pytest.param(lambda r: r.__setitem__("phase", "other"), id="phase"),
])
def test_every_receipt_mutation_refuses(bound, tmp_path, mutate):
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    mutate(receipt)
    assert F.receipt_problems(out, bound, receipt) != []


def test_a_retry_with_no_finalized_parent_is_an_orphan(bound, tmp_path):
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    receipt["attempt"] = F.MAX_ATTEMPTS
    assert any("orphan" in p for p in F.receipt_problems(out, bound, receipt))


# ------------------------------------------------------- B: the evidence ---
def test_a_lawful_phase_proves_every_call(bound, tasks, tmp_path, official):
    _out, doc = run_events(tmp_path, official, bound, tasks)
    assert doc["problems"] == []
    assert doc["ledger"]["valid"] == 36
    assert doc["phase_complete"] is True
    assert doc["retry"] == []


def test_a_missing_state_is_missing_and_never_silently_dropped(bound, tasks,
                                                               tmp_path,
                                                               official):
    gone = tasks[0]["source_id"]
    _out, doc = run_events(tmp_path, official, bound, tasks, skip=(gone,))
    assert doc["ledger"]["missing"] == 1
    assert doc["phase_complete"] is False
    assert dict((l, o) for l, o, _w in doc["outcomes"])[gone] == "missing"


def test_raw_is_captured_before_any_parse(bound, tasks, tmp_path, official):
    bad = tasks[0]["source_id"]
    out, doc = run_events(tmp_path, official, bound, tasks,
                          answers={bad: "{not json"})
    assert dict((l, o) for l, o, _w in doc["outcomes"])[bad] == \
        "invalid_response"
    raws = os.listdir(os.path.join(out, "raw"))
    assert any(n.endswith(".raw.json") for n in raws)
    assert "{not json" in "".join(
        K._read(os.path.join(out, "raw", n)) for n in raws
        if n.endswith(".raw.json"))


def test_only_an_unreadable_answer_is_retried_and_the_child_is_published(
        bound, tasks, tmp_path, official):
    bad = tasks[0]["source_id"]
    out, doc = run_events(tmp_path, official, bound, tasks,
                          answers={bad: "{not json"})
    assert doc["retry"] == [bad]
    child = os.path.join(out, "retry")
    receipt = K._load(os.path.join(child, K.RECEIPT_NAME))
    assert receipt["attempt"] == F.MAX_ATTEMPTS
    assert receipt["allowed"] == [bad]
    assert receipt["parent"]["run_id"] == doc["run_id"]
    assert F.receipt_problems(child, bound, receipt) == []
    # byte-identical prompt, fresh identity
    parent = K._load(os.path.join(out, K.RECEIPT_NAME))
    assert receipt["prompts"][bad] == parent["prompts"][bad]
    assert receipt["run_id"] != parent["run_id"]


def test_a_schema_valid_answer_is_never_retried(bound, tasks, tmp_path,
                                                official):
    """An open issue is a real answer. Spending a second call would be buying
    a different opinion, not repairing a broken transport."""
    task = tasks[0]
    doc0 = T9.shard_doc(task)
    doc0["open_issues"] = ["this row cannot be settled from the quote"]
    _out, doc = run_events(tmp_path, official, bound, tasks,
                           answers={task["source_id"]: T9.shard_text(doc0)})
    assert doc["retry"] == []
    assert doc["ledger"]["valid"] == 36


def test_a_second_attempt_never_spawns_a_third(bound, tasks, tmp_path,
                                               official):
    bad = tasks[0]["source_id"]
    out, _doc = run_events(tmp_path, official, bound, tasks,
                           answers={bad: "{not json"})
    child = os.path.join(out, "retry")
    task = [t for t in tasks if t["source_id"] == bad][0]
    F.record_state(child, build_call(official, bound, task, "{still not json",
                                     attempt=F.MAX_ATTEMPTS,
                                     run_id="wf_retry_" + bad.replace("#", "_")
                                     .replace("/", "_")))
    doc2 = F.finalize(child, bound)
    assert doc2["retry"] == []
    assert not os.path.isdir(os.path.join(child, "retry"))


@pytest.mark.parametrize("kw,why", [
    ({"doc_mutate": lambda d: d.__setitem__("script", "// other")}, "script"),
    ({"doc_mutate": lambda d: d["result"].__setitem__("model", "other")},
     "model"),
    ({"doc_mutate": lambda d: d["result"].__setitem__("effort", "low")},
     "effort"),
    ({"doc_mutate": lambda d: d["result"].__setitem__("agentType", "other")},
     "agentType"),
    ({"doc_mutate": lambda d: d["result"].__setitem__("rows", [])}, "rows"),
    ({"doc_mutate": lambda d: d["result"].__setitem__("event_index", 99)},
     "event_index"),
    ({"doc_mutate": lambda d: d["result"].pop("attempt")}, "keys"),
    ({"doc_mutate": lambda d: d.__setitem__("status", "failed")}, "status"),
    ({"doc_mutate": lambda d: d.__setitem__("totalToolCalls", 1)}, "tools"),
    ({"session_id": "another-session"}, "parent session"),
    ({"transcript": False}, "transcript"),
])
def test_every_evidence_mutation_refuses(bound, tasks, tmp_path, official,
                                         kw, why):
    task = tasks[0]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    F.record_state(out, build_call(official, bound, task,
                                   T9.shard_text(T9.shard_doc(task)), **kw))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert problems != [], why


def test_a_state_outside_the_official_tree_refuses(bound, tasks, tmp_path,
                                                   official):
    task = tasks[0]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    path = build_call(official, bound, task,
                      T9.shard_text(T9.shard_doc(task)))
    moved = str(tmp_path / "elsewhere.json")
    io.open(moved, "w", encoding="utf-8").write(K._read(path))
    F.record_state(out, moved)
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert any("official" in p for p in problems)


def test_one_call_served_twice_refuses(bound, tasks, tmp_path, official):
    task = tasks[0]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    text = T9.shard_text(T9.shard_doc(task))
    F.record_state(out, build_call(official, bound, task, text, run_id="wf_a"))
    F.record_state(out, build_call(official, bound, task, text, run_id="wf_b"))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert problems != []


def test_a_reused_identity_refuses(bound, tasks, tmp_path, official):
    a, b = tasks[0], tasks[1]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    F.record_state(out, build_call(official, bound, a,
                                   T9.shard_text(T9.shard_doc(a)),
                                   run_id="wf_same"))
    # a second call that reuses the first call's agent and response identity
    F.record_state(out, build_call(
        official, bound, b, T9.shard_text(T9.shard_doc(b)), run_id="wf_other",
        doc_mutate=lambda d: d["workflowProgress"][0].__setitem__(
            "agentId", "agent_wf_same")))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert any("reused" in p for p in problems)


def test_a_swapped_launcher_refuses(bound, tasks, tmp_path, official):
    a, b = tasks[0], tasks[1]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)
    F.record_state(out, build_call(
        official, bound, a, T9.shard_text(T9.shard_doc(a)),
        script=F.render_launcher(b, bound.evidence, bound.hr, bound.fix, 1)))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert any("launcher" in p for p in problems)


def test_a_genuine_rejection_is_not_an_answer(bound, tasks, tmp_path,
                                              official):
    task = tasks[0]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)

    def reject(doc):
        doc["workflowProgress"] = [{
            "type": "workflow_agent", "state": "error", "blocked": True,
            "error": "no capacity", "label": task["source_id"],
            "agentType": K.AGENT_TYPE}]
        doc["result"]["text"] = None

    F.record_state(out, build_call(official, bound, task, "unused",
                                   doc_mutate=reject, transcript=False))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    proved, problems = F.run_evidence(out, bound, receipt)
    assert problems == []
    assert proved[task["source_id"]][0] == "transport_no_answer"


def test_a_rejection_carrying_answer_text_refuses(bound, tasks, tmp_path,
                                                  official):
    task = tasks[0]
    out = str(tmp_path / "e")
    F.prepare_events(out, bound)

    def reject(doc):
        doc["workflowProgress"] = [{
            "type": "workflow_agent", "state": "error", "blocked": True,
            "error": "no capacity", "label": task["source_id"],
            "agentType": K.AGENT_TYPE}]

    F.record_state(out, build_call(official, bound, task,
                                   T9.shard_text(T9.shard_doc(task)),
                                   doc_mutate=reject, transcript=False))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert problems != []


# ------------------------------------------------- C: the gate before ink --
def test_a_clean_phase_opens_the_gate(bound, tasks, tmp_path, official):
    out, doc = run_events(tmp_path, official, bound, tasks)
    assert doc["phase_complete"]
    gate = F.signing_gate(out, bound)
    assert len(gate["shards"]) == 36
    assert gate["counts"]["rows_accounted"] == 196


def test_a_missing_accepted_shard_stops_the_gate(bound, tasks, tmp_path,
                                                 official):
    out, _doc = run_events(tmp_path, official, bound, tasks,
                           skip=(tasks[0]["source_id"],))
    gate = F.signing_gate(out, bound)
    assert not gate["ok"]
    assert any("no accepted shard" in s for s in gate["stops"])


def test_an_open_issue_stops_the_gate(bound, tasks, tmp_path, official):
    task = tasks[0]
    doc0 = T9.shard_doc(task)
    doc0["open_issues"] = ["this row cannot be settled from the quote"]
    out, _doc = run_events(tmp_path, official, bound, tasks,
                           answers={task["source_id"]: T9.shard_text(doc0)})
    gate = F.signing_gate(out, bound)
    assert not gate["ok"]
    assert any("open issue" in s for s in gate["stops"])


def test_a_short_class_stops_and_reports_rather_than_substituting(
        bound, tasks, tmp_path, official, monkeypatch):
    """Both the sequential door and a short correction/amendment class stop.
    Nothing is substituted; the class is named so it can be read."""
    monkeypatch.setattr(F.INV, "TAG_FLOOR", 999)
    out, _doc = run_events(tmp_path, official, bound, tasks)
    gate = F.signing_gate(out, bound)
    assert not gate["ok"]
    named = " ".join(gate["stops"])
    assert "corrections_and_amendments" in named
    assert "sequential" in named and "ULTA-to-LUV" in named


def test_the_gate_never_substitutes_a_row_for_a_short_class(bound, tasks,
                                                            tmp_path, official,
                                                            monkeypatch):
    monkeypatch.setattr(F.INV, "TAG_FLOOR", 999)
    out, _doc = run_events(tmp_path, official, bound, tasks)
    before = F.signing_gate(out, bound)["counts"]["distinct_rows_per_tag"]
    after = F.signing_gate(out, bound)["counts"]["distinct_rows_per_tag"]
    assert before == after


def test_a_duplicate_gold_fact_stops_the_gate(bound, tasks, tmp_path,
                                              official, monkeypatch):
    out, _doc = run_events(tmp_path, official, bound, tasks)
    real = F.counts

    def duped(key, sidecar):
        c = real(key, sidecar)
        c["duplicate_gold_facts"] = 1
        return c

    monkeypatch.setattr(F, "counts", duped)
    gate = F.signing_gate(out, bound)
    assert not gate["ok"]
    assert any("duplicate gold" in s for s in gate["stops"])


# ------------------------------------------------------- D: the signature --
def test_the_signer_is_never_prepared_over_a_dirty_gate(bound, tasks,
                                                        tmp_path, official):
    out, _doc = run_events(tmp_path, official, bound, tasks,
                           skip=(tasks[0]["source_id"],))
    b = bound._replace(events=out)
    got = F.prepare_signer(str(tmp_path / "s"), b)
    assert not got["ok"] and got["invocations"] == []


def test_the_signer_capacity_is_measured_on_the_real_rendered_bytes(
        bound, tasks, tmp_path, official):
    out, _doc = run_events(tmp_path, official, bound, tasks)
    b = bound._replace(events=out)
    got = F.prepare_signer(str(tmp_path / "s"), b)
    assert got["ok"], got["problems"]
    script = K._read(got["invocations"][0]["scriptPath"])
    assert got["signer_bytes"] == len(script.encode("utf-8"))
    assert got["signer_bytes"] < K.TRANSPORT_LIMIT


def test_the_signer_over_the_limit_refuses(bound, tasks, tmp_path, official,
                                           monkeypatch):
    out, _doc = run_events(tmp_path, official, bound, tasks)
    b = bound._replace(events=out)
    monkeypatch.setattr(K, "TRANSPORT_LIMIT", 1024)
    got = F.prepare_signer(str(tmp_path / "s"), b)
    assert not got["ok"] and got["invocations"] == []


def test_the_signer_script_is_derived_from_the_accepted_raw_shards(
        bound, tasks, tmp_path, official):
    out, _doc = run_events(tmp_path, official, bound, tasks)
    b = bound._replace(events=out)
    gate = F.signing_gate(out, bound)
    script = F.signer_script(b)
    for raw in gate["raws"].values():
        assert K._sha(raw) in script


@pytest.mark.parametrize("text,ok", [
    ('{"signed": true, "blocked": [], "why": "every gate is clean"}', True),
    ('{"signed": false, "blocked": ["row 7 is unresolved"], "why": "no"}',
     True),
    ('{"signed": true, "blocked": ["row 7"], "why": "yes"}', False),
    ('{"signed": false, "blocked": [], "why": "no"}', False),
    ('{"signed": "true", "blocked": [], "why": "y"}', False),
    ('{"signed": 1, "blocked": [], "why": "y"}', False),
    ('{"signed": true, "blocked": [], "why": "  "}', False),
    ('{"signed": true, "blocked": [], "why": "y", "extra": 1}', False),
    ('{"signed": true, "blocked": []}', False),
    ('not json', False),
])
def test_the_signature_shape_is_checked(text, ok):
    obj, bad = F.read_signature(text)
    assert (bad == []) is ok
    assert (obj is not None) is ok


# ------------------------------------------------------------- E: the lock -
def _signed(tmp_path, official, bound, events, text):
    out = str(tmp_path / "s")
    b = bound._replace(events=events)
    prepared = F.prepare_signer(out, b)
    assert prepared["ok"], prepared["problems"]
    script = K._read(prepared["invocations"][0]["scriptPath"])
    run_id = "wf_signer"
    agent = "agent_" + run_id
    tdir = official / "subagents" / "workflows" / run_id
    tdir.mkdir(parents=True, exist_ok=True)
    recs = [{"type": "assistant", "uuid": "u1", "parentUuid": None,
             "agentId": agent, "sessionId": K.PARENT_SESSION,
             "effort": K.EFFORT, "requestId": "req_" + run_id,
             "message": {"role": "assistant", "id": "msg_" + run_id,
                         "model": K.RUNTIME_MODEL_ID,
                         "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": text}]}}]
    with io.open(str(tdir / ("agent-%s.jsonl" % agent)), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    doc = {"runId": run_id, "status": "completed", "totalToolCalls": 0,
           "script": script,
           "workflowProgress": [{"type": "workflow_agent", "state": "done",
                                 "label": "a4-final-signer", "agentId": agent,
                                 "model": K.RUNTIME_MODEL_ID,
                                 "agentType": K.AGENT_TYPE, "toolCalls": 0}],
           "result": {"role": "signer", "attempt": 1, "model": K.MODEL,
                      "effort": K.EFFORT, "agentType": K.AGENT_TYPE,
                      "text": text}}
    path = official / "workflows" / ("%s.json" % run_id)
    io.open(str(path), "w", encoding="utf-8").write(json.dumps(doc))
    F.record_state(out, str(path))
    F.finalize(out, b)
    return out, b


def test_a_lawful_signature_locks_and_binds_the_ordered_raw_shards(
        bound, tasks, tmp_path, official):
    events, _doc = run_events(tmp_path, official, bound, tasks)
    sdir, b = _signed(tmp_path, official, bound, events,
                      '{"signed": true, "blocked": [], "why": "clean"}')
    locked = F.lock(sdir, b)
    assert locked["state"] == "LOCKED"
    gate = F.signing_gate(events, bound)
    assert [s["source_id"] for s in locked["key_shards"]] == \
        list(gate["raws"])
    assert [s["sha256"] for s in locked["key_shards"]] == \
        [K._sha(r) for r in gate["raws"].values()]
    assert locked["loader"]["sha256"] == F.INV.sha_file(
        os.path.join(F._HERE, "build_kfields_final.py"))
    assert F.lock_problems(locked, sdir, b) == []


def test_a_refusal_never_locks(bound, tasks, tmp_path, official):
    events, _doc = run_events(tmp_path, official, bound, tasks)
    sdir, b = _signed(tmp_path, official, bound, events,
                      '{"signed": false, "blocked": ["row 7"], "why": "no"}')
    with pytest.raises(ValueError):
        F.lock(sdir, b)


def test_an_unproved_signature_never_locks(bound, tasks, tmp_path, official):
    events, _doc = run_events(tmp_path, official, bound, tasks)
    sdir, b = _signed(tmp_path, official, bound, events,
                      '{"signed": true, "blocked": [], "why": "clean"}')
    state = os.path.join(str(official), "workflows", "wf_signer.json")
    doc = K._load(state)
    doc["script"] = "// a different signer"
    io.open(state, "w", encoding="utf-8").write(json.dumps(doc))
    with pytest.raises(ValueError):
        F.lock(sdir, b)


@pytest.mark.parametrize("field", [
    "package_manifest_sha256", "bound_owners", "loader", "key_shards",
    "event_finalization_sha256", "signer_raw_sha256", "counts", "signature"])
def test_every_locked_value_is_rederived_and_a_mutation_refuses(
        bound, tasks, tmp_path, official, field):
    events, _doc = run_events(tmp_path, official, bound, tasks)
    sdir, b = _signed(tmp_path, official, bound, events,
                      '{"signed": true, "blocked": [], "why": "clean"}')
    locked = F.lock(sdir, b)
    locked[field] = "tampered"
    assert F.lock_problems(locked, sdir, b) != []
