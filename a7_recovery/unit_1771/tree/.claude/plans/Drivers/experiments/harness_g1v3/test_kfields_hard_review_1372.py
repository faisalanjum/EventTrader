"""Codex SEQ 1372 E — the corrected boundary, the typed group judgment and
the run lifecycle must all fail closed.

Written RED FIRST. The controls the SEQ 1371 battery did not have are the
prompt-order census (its 47 green controls never checked the assembled
instruction order against the live boundary), the typed group verdict, and
every lifecycle control below.
"""
import copy
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import audit_worker_access as AUD                                # noqa: E402
import build_exp5_contract as C                                  # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402

#: the frozen A4 run whose corrected artifacts this package derives from
RUN = io.open(os.path.join(os.environ.get(
    "KF_SCRATCH", "/tmp/claude-1000/-home-faisal-EventMarketDB/"
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"), "a4_dir.txt"),
    encoding="utf-8").read().strip()

_PROMPTS = {}


def prompt_for(task):
    if task["task_id"] not in _PROMPTS:
        _PROMPTS[task["task_id"]] = HR.blind_prompt(task)
    return _PROMPTS[task["task_id"]]


@pytest.fixture(autouse=True)
def _fresh():
    """Every control re-derives from disk; a cache must never carry drift."""
    HR._items.cache_clear()
    HR._source.cache_clear()
    yield
    HR._items.cache_clear()
    HR._source.cache_clear()


@pytest.fixture
def pkg(tmp_path):
    out = str(tmp_path / "pkg")
    HR.build(out, RUN)
    return out


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
        return real_locator(state_path)

    monkeypatch.setattr(AUD, "_official_location", located)
    return session


def _tasks():
    return HR.tasks(RUN)


def _item_task():
    return [t for t in _tasks() if t["kind"] == "item"][0]


def _group_task():
    return [t for t in _tasks() if t["kind"] == "group"][0]


def _sparse(item):
    """The lawful sparse reply: code owns the locator, not the model."""
    return ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "the '
            'scale marker sits outside the quote"}], "continuity_hints": []}'
            % json.dumps(item["source_id"]))


def _group_reply(task, verdict="true", bad_member=None, swap=False,
                 reason='"the two quotes point at one span"'):
    rows = []
    for n, key in enumerate(task["members"]):
        body = "{}" if n == bad_member else _sparse(HR._items()[key])
        rows.append('{"member_index": %d, "settled": %s}' % (n + 1, body))
    if swap:
        rows[0], rows[1] = rows[1], rows[0]
    return ('{"members": [%s], "members_are_one_fact": %s, "reason": %s}'
            % (", ".join(rows), verdict, reason))


def _answer(task):
    """One lawful blind answer for whichever shape this task has."""
    if task["kind"] == "item":
        return _sparse(HR._items()[task["members"][0]])
    return _group_reply(task)


def build_call(session, task, blind, answer, attempt=1, run_id=None,
               script_path=None, doc_mutate=None, rec_mutate=None,
               transcript=True):
    """One lawful official hard-review call: state + transcript that agree."""
    label = HR.call_label(task["task_id"], blind)
    run_id = run_id or ("wf_" + label.replace("/", "_"))
    prompt = prompt_for(task)
    agent = "agent_" + run_id
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
    doc = {
        "runId": run_id, "status": "completed", "totalToolCalls": 0,
        "script": HR.render_launcher(task, blind, attempt),
        "workflowProgress": [{"type": "workflow_agent", "state": "done",
                              "label": label, "agentId": agent,
                              "model": K.RUNTIME_MODEL_ID,
                              "agentType": K.AGENT_TYPE, "toolCalls": 0}],
        "result": {"task_id": task["task_id"], "kind": task["kind"],
                   "members": list(task["members"]), "blind": blind,
                   "attempt": attempt, "model": K.MODEL, "effort": K.EFFORT,
                   "agentType": K.AGENT_TYPE,
                   "text": recs[-1]["message"]["content"][-1]["text"]
                   if recs[-1].get("type") == "assistant" else None},
    }
    if script_path is not None:
        doc["scriptPath"] = script_path
    if doc_mutate:
        doc_mutate(doc)
    path = session / "workflows" / ("%s.json" % run_id)
    io.open(str(path), "w", encoding="utf-8").write(json.dumps(doc))
    return str(path)


def _reject_row(doc):
    """A GENUINE pre-agent rejection: structured evidence, null answer text."""
    doc["workflowProgress"] = [{"type": "workflow_agent", "state": "error",
                                "blocked": True, "error": "no capacity",
                                "label": doc["workflowProgress"][0]["label"],
                                "agentType": K.AGENT_TYPE}]
    doc["result"]["text"] = None


def full_primary(tmp_path, session, pkg, answers=None, mutate=None):
    """THE public route: prepare, run only what it returned, in order."""
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    assert prep["ok"] is True, prep["problems"]
    by_label = HR._by_label(RUN)
    for inv in prep["invocations"]:                 # ONLY these, in THIS order
        task, blind = by_label[inv["label"]]
        kw = dict(answers or {}).get(inv["label"], {})
        state = build_call(session, task, blind,
                           kw.pop("answer", None) or _answer(task),
                           attempt=inv["attempt"],
                           script_path=inv["scriptPath"], **kw)
        if mutate:
            state = mutate(inv, state) or state
        assert HR.record_state(out, state) == []
    return out, prep


# ============================================ A. the corrected boundary =====
def test_every_prompt_puts_its_instructions_above_the_live_boundary():
    assert HR.prompt_order_problems(RUN) == []
    boundary = HR._boundary()
    census = {"tasks": 0, "task_above": 0, "data_below": 0}
    for task in _tasks():
        text = HR.blind_prompt(task)
        cut = text.find(boundary)
        census["tasks"] += 1
        census["task_above"] += text.find("[A4 HARD REVIEW TASK]") < cut
        census["data_below"] += text.rfind("[INPUT]") > cut
    assert census == {"tasks": 35, "task_above": 35, "data_below": 35}


def test_no_group_prompt_carries_the_singular_one_item_role():
    groups = [t for t in _tasks() if t["kind"] == "group"]
    assert len(groups) == 7
    assert sum(C.ONE_ITEM_ROLE in HR.blind_prompt(t) for t in groups) == 0
    assert all("SEVERAL already-located" in HR.blind_prompt(t) for t in groups)
    items = [t for t in _tasks() if t["kind"] == "item"]
    assert all("ONE already-located" in HR.blind_prompt(t) for t in items)


def test_the_rules_and_output_card_are_the_live_owners_bytes(pkg):
    """Reused mechanically, never summarised and never copied."""
    for kind in ("item", "group"):
        prefix = HR.prompt_prefix(kind)
        assert C.role_rules("drafter") in prefix
        assert C.one_item_output_section().rstrip() in prefix
        assert C.INJECTION_CONTROL in prefix
        assert HR._boundary() in prefix
        assert K._read(os.path.join(pkg, "prompt_prefix_%s.txt" % kind)) \
            == prefix


def test_the_item_prefix_carries_the_live_one_item_role_byte_for_byte(pkg):
    """Codex SEQ 1373: a near-copy read the same but owned nothing."""
    prefix = HR.prompt_prefix("item")
    assert C.ONE_ITEM_ROLE in prefix
    assert prefix.startswith("[ROLE]\n%s\n\n" % C.ONE_ITEM_ROLE)
    assert K._read(os.path.join(pkg, "prompt_prefix_item.txt")) == prefix
    for task in [t for t in _tasks() if t["kind"] == "item"]:
        assert C.ONE_ITEM_ROLE in HR.blind_prompt(task)


def test_an_item_role_owner_change_refuses_the_already_built_package(
        pkg, monkeypatch):
    """The exact drift that used to pass preflight with zero problems."""
    assert HR.preflight(pkg, RUN)["ok"] is True
    monkeypatch.setattr(C, "ONE_ITEM_ROLE",
                        C.ONE_ITEM_ROLE + "\nan added role rule.")
    out = HR.preflight(pkg, RUN)
    assert out["ok"] is False
    assert any("item_role_sha256" in p for p in out["problems"])


def test_a_semantic_rule_change_refuses(pkg, monkeypatch):
    real = C.role_rules
    monkeypatch.setattr(C, "role_rules",           # the owner's real signature
                        lambda role, contract_suffix="": real(role, contract_suffix)
                        + "\nan added semantic rule.")
    assert HR.package_problems(pkg, RUN)


def test_a_boundary_change_refuses(pkg, monkeypatch):
    real = C._section
    monkeypatch.setattr(C, "_section", lambda p, h: real(p, h) + "\nmore.\n")
    assert HR.package_problems(pkg, RUN)


def test_no_blind_prompt_carries_a_draft_or_a_prior_settlement():
    inventory = K._load(os.path.join(RUN, "conflicts_1370.json"))
    settled = [json.dumps(e["settled"], sort_keys=True)
               for e in inventory["items_both_drafts_rejected"]]
    seen = 0
    for task in _tasks():
        text = HR.blind_prompt(task)
        assert K.DRAFTS_MARK not in text and K.RULES_BLOCK not in text
        for key in task["members"]:
            for draft in HR._items()[key]["a3_drafts"]:
                assert draft["text"] not in text
                seen += 1
        for answer in settled:
            assert answer not in text
    assert seen > 0, "the leak control compared nothing"


def test_why_a_task_exists_never_reaches_its_prompt():
    """Structural, not a word search: "unresolved" occurs in the live rules."""
    for task in _tasks():
        other = dict(task, origin="a different reason entirely")
        assert HR.blind_prompt(other) == HR.blind_prompt(task)
        assert HR.render_launcher(other, 1) == HR.render_launcher(task, 1)


def test_a_group_payload_shows_indices_and_never_packet_identity():
    task = _group_task()
    rows = HR.payload(task)["item"]
    assert [r["member_index"] for r in rows] == list(range(1, len(rows) + 1))
    for row, key in zip(rows, task["members"]):
        assert set(row) == set(K._frozen_item(HR._items()[key])) \
            | {"member_index"}
        assert key not in json.dumps(row)


# ====================================== B. the typed group judgment =========
@pytest.mark.parametrize("verdict,want", [("true", True), ("false", False),
                                          ("null", None)])
def test_every_typed_group_verdict_is_accepted(verdict, want):
    task = _group_task()
    obj, bad = HR.read_reply(_group_reply(task, verdict), task)
    assert bad == []
    assert obj["members_are_one_fact"] is want
    assert list(obj["members"]) == task["members"]


@pytest.mark.parametrize("verdict", ['"banana"', '"true"', '1', '0', '[]',
                                     '{}', '"null"'])
def test_a_group_verdict_that_is_not_a_real_boolean_or_null_refuses(verdict):
    """Codex SEQ 1372: a free-text relationship let "banana" through clean."""
    obj, bad = HR.read_reply(_group_reply(_group_task(), verdict),
                             _group_task())
    assert obj is None
    assert any("members_are_one_fact" in b for b in bad)


def test_a_group_reply_with_an_extra_key_refuses():
    task = _group_task()
    doc = json.loads(_group_reply(task))
    doc["relationship"] = "both name the same move"
    obj, bad = HR.read_reply(json.dumps(doc), task)
    assert obj is None and bad


def test_a_group_reply_missing_the_verdict_refuses():
    task = _group_task()
    doc = json.loads(_group_reply(task))
    del doc["members_are_one_fact"]
    obj, bad = HR.read_reply(json.dumps(doc), task)
    assert obj is None and bad


def test_a_group_reply_with_one_bad_sibling_refuses_the_whole_task():
    task = _group_task()
    obj, bad = HR.read_reply(_group_reply(task, bad_member=0), task)
    assert obj is None
    assert any(task["members"][0] in b for b in bad)


def test_group_member_rows_out_of_order_refuse():
    task = _group_task()
    obj, bad = HR.read_reply(_group_reply(task, swap=True), task)
    assert obj is None
    assert any("out of order" in b for b in bad)


def test_a_group_reply_missing_a_member_refuses():
    task = _group_task()
    doc = json.loads(_group_reply(task))
    doc["members"].pop()
    obj, bad = HR.read_reply(json.dumps(doc), task)
    assert obj is None and bad


@pytest.mark.parametrize("reason", ['"   "', '""', 'null', '5'])
def test_a_blank_or_untyped_group_reason_refuses(reason):
    task = _group_task()
    obj, bad = HR.read_reply(_group_reply(task, reason=reason), task)
    assert obj is None and any("reason" in b for b in bad)


def test_a_lawful_one_item_blind_reply_is_accepted():
    task = _item_task()
    obj, bad = HR.read_reply(_sparse(HR._items()[task["members"][0]]), task)
    assert bad == []
    assert obj["settled"]["abstentions"][0]["quote"] \
        == HR._items()[task["members"][0]]["quote"]


@pytest.mark.parametrize("text", [
    "not json at all", "[]", '{"source_id": "x"}',
    '{"source_id": "x", "facts": [], "abstentions": [], '
    '"continuity_hints": [], "extra": 1}'])
def test_a_malformed_one_item_reply_refuses(text):
    obj, bad = HR.read_reply(text, _item_task())
    assert obj is None and bad


def test_a_one_item_reply_sent_to_a_group_task_refuses():
    task = _group_task()
    obj, bad = HR.read_reply(_sparse(HR._items()[task["members"][0]]), task)
    assert obj is None and bad


# ================================================ C. the run lifecycle ======
def test_the_public_route_classifies_all_seventy_calls_exactly_once(
        tmp_path, official, pkg):
    out, prep = full_primary(tmp_path, official, pkg)
    assert len(prep["invocations"]) == 70
    assert [i["label"] for i in prep["invocations"]] == HR.canonical_calls(RUN)
    for inv in prep["invocations"]:                # runnable, not just bytes
        assert os.path.isfile(inv["scriptPath"])
        assert K.INV.sha_file(inv["scriptPath"]) == inv["script_sha256"]
        assert inv["args"] is None
    doc = HR.finalize(out, pkg, RUN)
    assert doc["problems"] == []
    assert doc["ledger"]["scheduled"] == 70
    assert doc["ledger"]["valid"] == 70
    assert len(doc["outcomes"]) == 70
    assert len({row[0] for row in doc["outcomes"]}) == 70
    assert doc["primary_complete"] is True
    assert doc["retry"] == [] and "child" not in doc
    assert doc["budget"]["ledger_after"] == 4230 + 70
    assert doc["budget"]["within_ceiling"] is True


def test_a_semantic_null_is_valid_and_never_retried(tmp_path, official, pkg):
    group = _group_task()
    answers = {HR.call_label(group["task_id"], b):
               {"answer": _group_reply(group, "null")} for b in HR.BLINDS}
    out, _prep = full_primary(tmp_path, official, pkg, answers=answers)
    doc = HR.finalize(out, pkg, RUN)
    assert doc["ledger"]["valid"] == 70
    assert doc["retry"] == [] and "child" not in doc


def test_the_child_carries_exactly_the_invalid_and_unanswered_calls(
        tmp_path, official, pkg):
    tasks = _tasks()
    broken = HR.call_label(tasks[0]["task_id"], 1)
    silent = HR.call_label(tasks[1]["task_id"], 2)
    answers = {broken: {"answer": "not a lawful reply at all"},
               # a pre-agent rejection means NO worker at all, so it must
               # not leave a transcript behind; the owner refuses one that does
               silent: {"doc_mutate": _reject_row, "transcript": False}}
    out, _prep = full_primary(tmp_path, official, pkg, answers=answers)
    doc = HR.finalize(out, pkg, RUN)
    assert doc["problems"] == []
    assert doc["primary_complete"] is True
    assert doc["ledger"]["valid"] == 68
    assert doc["ledger"]["invalid_response"] == 1
    assert doc["ledger"]["transport_no_answer"] == 1
    assert sorted(doc["retry"]) == sorted([broken, silent])
    child = doc["child"]
    assert [i["label"] for i in child["invocations"]] == doc["retry"]
    assert all(i["attempt"] == 2 for i in child["invocations"])


def test_an_unproved_call_blocks_the_child_entirely(tmp_path, official, pkg):
    tasks = _tasks()
    hurt = HR.call_label(tasks[0]["task_id"], 1)
    answers = {hurt: {"transcript": False}}
    out, _prep = full_primary(tmp_path, official, pkg, answers=answers)
    doc = HR.finalize(out, pkg, RUN)
    assert doc["primary_complete"] is False
    assert doc["retry"] == [] and "child" not in doc


def test_the_child_closeout_is_durable_and_publishes_no_successor(
        tmp_path, official, pkg):
    tasks = _tasks()
    broken = HR.call_label(tasks[0]["task_id"], 1)
    out, _prep = full_primary(tmp_path, official, pkg,
                              answers={broken: {"answer": "not lawful"}})
    doc = HR.finalize(out, pkg, RUN)
    child = doc["child"]
    by_label = HR._by_label(RUN)
    for inv in child["invocations"]:
        task, blind = by_label[inv["label"]]
        state = build_call(official, task, blind, _answer(task),
                           attempt=2, run_id="wf_child_" + inv["label"]
                           .replace("/", "_"),
                           script_path=inv["scriptPath"])
        assert HR.record_state(child["dir"], state) == []
    kid = HR.finalize(child["dir"], pkg, RUN)
    assert kid["problems"] == []
    assert kid["attempt"] == 2
    assert kid["ledger"]["scheduled"] == len(child["invocations"])
    assert kid["ledger"]["valid"] == len(child["invocations"])
    assert kid["retry"] == [] and "child" not in kid
    assert os.path.isfile(os.path.join(child["dir"], HR.FINALIZATION_NAME))
    assert kid["budget"]["spent_so_far"] == 70 + len(child["invocations"])
    assert kid["budget"]["within_ceiling"] is True


def test_raw_bytes_survive_a_failed_official_proof(tmp_path, official, pkg):
    """Paid bytes are written before any proof, receipt or parse check."""
    tasks = _tasks()
    hurt = HR.call_label(tasks[0]["task_id"], 1)
    out, _prep = full_primary(tmp_path, official, pkg,
                              answers={hurt: {"transcript": False}})
    doc = HR.finalize(out, pkg, RUN)
    assert doc["primary_complete"] is False
    raw = os.listdir(os.path.join(out, "raw"))
    assert len([n for n in raw if n.endswith(".raw.json")]) == 70
    kept = [n for n in raw if n.startswith("wf_" + hurt.replace("/", "_"))]
    assert kept, "the unproved call's paid bytes were discarded"


def test_a_receipt_fault_preserves_raw_and_grants_no_credit(
        tmp_path, official, pkg):
    out, _prep = full_primary(tmp_path, official, pkg)
    path = os.path.join(out, HR.RECEIPT_NAME)
    doc = json.loads(K._read(path))
    doc["allowed"] = doc["allowed"][:-1]
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    fin = HR.finalize(out, pkg, RUN)
    assert fin["problems"]
    assert fin["ledger"]["valid"] == 0
    assert len([n for n in os.listdir(os.path.join(out, "raw"))
                if n.endswith(".raw.json")]) == 70


def test_a_missing_state_is_missing_and_never_valid(tmp_path, official, pkg):
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    by_label = HR._by_label(RUN)
    for inv in prep["invocations"][:-1]:
        task, blind = by_label[inv["label"]]
        HR.record_state(out, build_call(official, task, blind, _answer(task),
                                        script_path=inv["scriptPath"]))
    doc = HR.finalize(out, pkg, RUN)
    assert doc["ledger"]["missing"] == 1
    assert doc["primary_complete"] is False


def test_a_duplicate_state_for_one_call_refuses(tmp_path, official, pkg):
    out, _prep = full_primary(tmp_path, official, pkg)
    task = _item_task()
    twin = build_call(official, task, 1, _answer(task), run_id="wf_twin")
    assert HR.record_state(out, twin) == []
    doc = HR.finalize(out, pkg, RUN)
    assert any("already served" in p for p in doc["problems"])
    assert doc["primary_complete"] is False


def test_the_same_state_file_cannot_be_recorded_twice(tmp_path, official, pkg):
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    task, blind = HR._by_label(RUN)[prep["invocations"][0]["label"]]
    state = build_call(official, task, blind, _answer(task),
                       script_path=prep["invocations"][0]["scriptPath"])
    assert HR.record_state(out, state) == []
    assert HR.record_state(out, state) == ["that state is already recorded"]


def test_a_substituted_state_from_another_call_earns_nothing(
        tmp_path, official, pkg):
    """A state answering task B recorded where task A was scheduled."""
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    by_label = HR._by_label(RUN)
    first, second = prep["invocations"][0], prep["invocations"][2]
    task_b, blind_b = by_label[second["label"]]
    swapped = build_call(official, task_b, blind_b, _answer(task_b),
                         run_id="wf_" + first["label"].replace("/", "_"),
                         script_path=first["scriptPath"])
    assert HR.record_state(out, swapped) == []
    doc = HR.finalize(out, pkg, RUN)
    assert doc["primary_complete"] is False
    assert doc["ledger"]["valid"] == 0


@pytest.mark.parametrize("what", ["prompt", "script", "blind", "attempt",
                                  "model", "effort", "agentType", "tools",
                                  "task_id"])
def test_every_identity_mutation_refuses(tmp_path, official, pkg, what):
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    inv = prep["invocations"][0]
    task, blind = HR._by_label(RUN)[inv["label"]]

    def doc_mutate(doc):
        if what == "script":
            doc["script"] = doc["script"] + "\n// edited\n"
        elif what == "blind":
            doc["result"]["blind"] = 2 if blind == 1 else 1
        elif what == "attempt":
            doc["result"]["attempt"] = 2
        elif what in ("model", "effort", "agentType"):
            doc["result"][what] = "something-else"
        elif what == "tools":
            doc["totalToolCalls"] = 1
            doc["workflowProgress"][0]["toolCalls"] = 1
        elif what == "task_id":
            doc["result"]["task_id"] = "hr-999"

    def rec_mutate(recs):
        if what == "prompt":
            recs[0]["message"]["content"] += "\nan added instruction.\n"

    HR.record_state(out, build_call(
        official, task, blind, _answer(task), script_path=inv["scriptPath"],
        doc_mutate=doc_mutate, rec_mutate=rec_mutate))
    doc = HR.finalize(out, pkg, RUN)
    assert doc["ledger"]["valid"] == 0, what
    assert doc["primary_complete"] is False, what


def test_a_scriptpath_whose_bytes_moved_refuses(tmp_path, official, pkg):
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    inv = prep["invocations"][0]
    task, blind = HR._by_label(RUN)[inv["label"]]
    state = build_call(official, task, blind, _answer(task),
                       script_path=inv["scriptPath"])
    io.open(inv["scriptPath"], "a", encoding="utf-8").write("// edited\n")
    HR.record_state(out, state)
    doc = HR.finalize(out, pkg, RUN)
    assert doc["ledger"]["valid"] == 0


def test_prepare_refuses_a_dirty_directory_and_a_bad_package(tmp_path, pkg):
    out = str(tmp_path / "primary")
    os.makedirs(out)
    io.open(os.path.join(out, "stray.txt"), "w", encoding="utf-8").write("x")
    assert HR.prepare_run(out, pkg, RUN)["ok"] is False
    empty = str(tmp_path / "nopkg")
    os.makedirs(empty)
    bad = HR.prepare_run(str(tmp_path / "p2"), empty, RUN)
    assert bad["ok"] is False and bad["invocations"] == []


def test_a_caller_selected_subset_is_never_what_prepare_publishes(
        tmp_path, pkg):
    """The denominator is the owner's, not the operator's."""
    out = str(tmp_path / "primary")
    prep = HR.prepare_run(out, pkg, RUN)
    assert [i["label"] for i in prep["invocations"]] == HR.canonical_calls(RUN)
    receipt = K._load(os.path.join(out, HR.RECEIPT_NAME))
    receipt["allowed"] = receipt["allowed"][:10]
    assert HR.receipt_problems(out, pkg, RUN, receipt)


def test_a_third_attempt_is_impossible_at_the_receipt(tmp_path, pkg):
    out = str(tmp_path / "primary")
    HR.prepare_run(out, pkg, RUN)
    receipt = K._load(os.path.join(out, HR.RECEIPT_NAME))
    receipt["attempt"] = 3
    bad = HR.receipt_problems(out, pkg, RUN, receipt)
    assert any("outside 1..2" in b for b in bad)


def test_a_child_with_no_finalized_parent_is_an_orphan(tmp_path, pkg):
    out = str(tmp_path / "primary" / "retry")
    os.makedirs(out)
    receipt = HR.expected_receipt(out, pkg, RUN, 2, HR.canonical_calls(RUN)[:1],
                                  parent=None)
    bad = HR.receipt_problems(out, pkg, RUN, receipt)
    assert any("orphan" in b for b in bad)


def test_a_reordered_allowed_list_refuses(tmp_path, pkg):
    """Codex SEQ 1372 D.5: reordered evidence must fail closed."""
    out = str(tmp_path / "primary")
    HR.prepare_run(out, pkg, RUN)
    receipt = K._load(os.path.join(out, HR.RECEIPT_NAME))
    assert receipt["allowed"] == HR.canonical_calls(RUN)
    receipt["allowed"] = list(reversed(receipt["allowed"]))
    assert HR.receipt_problems(out, pkg, RUN, receipt)


def test_the_child_reruns_the_identical_prompt(tmp_path, official, pkg):
    """Codex SEQ 1372 D.6: identical prompt, fresh official identity."""
    tasks = _tasks()
    broken = HR.call_label(tasks[0]["task_id"], 1)
    out, _prep = full_primary(tmp_path, official, pkg,
                              answers={broken: {"answer": "not lawful"}})
    doc = HR.finalize(out, pkg, RUN)
    by_label = HR._by_label(RUN)
    for inv in doc["child"]["invocations"]:
        task, blind = by_label[inv["label"]]
        assert HR.blind_prompt(task) == prompt_for(task)
        first = HR.render_launcher(task, blind, 1)
        again = HR.render_launcher(task, blind, 2)
        assert K._sha(K._read(inv["scriptPath"])) == K._sha(again)
        assert again != first                      # a fresh call identity
        # ...but the PROMPT the model sees is byte-identical
        cut = "const PROMPT = "
        line = [x for x in again.splitlines() if x.startswith(cut)][0]
        was = [x for x in first.splitlines() if x.startswith(cut)][0]
        assert line == was


def test_a_third_attempt_and_a_third_blind_caller_refuse_at_the_renderer():
    task = _item_task()
    for args in ((1, HR.MAX_ATTEMPTS + 1), (1, 0), (max(HR.BLINDS) + 1, 1)):
        with pytest.raises(ValueError):
            HR.render_launcher(task, *args)


def test_the_two_blind_calls_and_the_retry_differ_by_exactly_one_field():
    """Blind moves two lines because the agent label CARRIES the blind index;
    the retry moves one. Nothing else in either script may move."""
    task = _item_task()
    for a, b, field, lines in ((HR.render_launcher(task, 1),
                                HR.render_launcher(task, 2), "blind", 2),
                               (HR.render_launcher(task, 1, 1),
                                HR.render_launcher(task, 1, 2), "attempt", 1)):
        la, lb = a.splitlines(), b.splitlines()
        diff = [(x, y) for x, y in zip(la, lb) if x != y]
        assert len(la) == len(lb) and len(diff) == lines
        call = [d for d in diff if d[0].startswith("const CALL = ")]
        assert len(call) == 1
        ja = json.loads(call[0][0][len("const CALL = "):])
        jb = json.loads(call[0][1][len("const CALL = "):])
        assert ja.pop(field) != jb.pop(field) and ja == jb
        for other in [d for d in diff if d not in call]:
            assert other[0].strip().startswith("label:")


# ================================================= D. the frozen package ====
def test_the_derivation_is_35_tasks_70_calls_covering_every_frozen_input():
    built = _tasks()
    assert HR.coverage_problems(RUN, built) == []
    assert len(built) == 35
    doc = HR.manifest(RUN)
    assert doc["counts"]["primary_calls"] == 70
    assert doc["counts"]["reviewed_packets"] == 42
    assert len(doc["call_order"]) == len(set(doc["call_order"])) == 70
    assert doc["door"] == "a4_hard_review_double_blind"
    assert HR.LAUNCHER_NAME == "kfields-a4-hard-review"


def test_the_package_double_builds_byte_identically(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    HR.build(a, RUN)
    HR.build(b, RUN)
    for name in sorted(os.listdir(a)):
        assert K.INV.sha_file(os.path.join(a, name)) \
            == K.INV.sha_file(os.path.join(b, name)), name


def test_a_lawful_package_passes_preflight(pkg):
    out = HR.preflight(pkg, RUN)
    assert out["problems"] == []
    assert out["ok"] is True


@pytest.mark.parametrize("field,value", [
    ("MODEL", "claude-opus-5"), ("EFFORT", "medium"),
    ("AGENT_TYPE", "general-purpose")])
def test_a_runtime_change_refuses(pkg, monkeypatch, field, value):
    monkeypatch.setattr(K, field, value)
    assert HR.package_problems(pkg, RUN)


def test_a_tool_change_refuses(pkg, monkeypatch):
    monkeypatch.setattr(K, "DISALLOWED", tuple(K.DISALLOWED[:-1]))
    assert HR.package_problems(pkg, RUN)


def test_a_capacity_change_refuses(pkg, monkeypatch):
    monkeypatch.setattr(K, "TRANSPORT_LIMIT", 1024)
    assert HR.package_problems(pkg, RUN)
    HR.build(pkg, RUN)
    out = HR.preflight(pkg, RUN)
    assert out["ok"] is False
    assert any("transport limit" in p for p in out["problems"])


def test_source_drift_refuses(pkg, monkeypatch):
    real = K.source_input

    def drifted(sid):
        out = copy.deepcopy(real(sid))
        out["text_parts"][0]["content"] += "\nan added sentence.\n"
        return out
    monkeypatch.setattr(K, "source_input", drifted)
    HR._source.cache_clear()
    assert HR.package_problems(pkg, RUN)


def test_menu_drift_refuses(pkg, monkeypatch):
    real = K.a1_reader.readable_menu
    monkeypatch.setattr(K.a1_reader, "readable_menu",
                        lambda t: (list(real(t)[0]) + ["added"], real(t)[1]))
    HR._source.cache_clear()
    assert HR.package_problems(pkg, RUN)


def test_item_drift_refuses(pkg, monkeypatch):
    """Drift a REVIEWED item: the package binds what it uses, not all 196."""
    real = K.phase1_items()
    reviewed = _item_task()["members"][0]

    def drifted():
        out = copy.deepcopy(real)
        for row in out:
            if row["packet_id"] == reviewed:
                row["raw_label_or_claim"] += " (edited)"
        return out
    monkeypatch.setattr(K, "phase1_items", drifted)
    HR._items.cache_clear()
    assert HR.package_problems(pkg, RUN)


def _copied_run(tmp_path):
    drifted = str(tmp_path / "run")
    os.makedirs(drifted)
    for name in ("regrade_1370.json", "conflicts_1370.json",
                 HR.RECEIPT_NAME, HR.FINALIZATION_NAME):
        shutil.copy2(os.path.join(RUN, name), os.path.join(drifted, name))
    return drifted


def test_group_member_drift_refuses(pkg, tmp_path):
    drifted = _copied_run(tmp_path)
    path = os.path.join(drifted, "conflicts_1370.json")
    doc = json.loads(K._read(path))
    doc["conflicting_locator_groups"][0]["members"].pop()
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert HR.package_problems(pkg, drifted)


def test_an_unresolved_key_dropped_from_the_evidence_refuses(pkg, tmp_path):
    drifted = _copied_run(tmp_path)
    path = os.path.join(drifted, "regrade_1370.json")
    doc = json.loads(K._read(path))
    doc["selection"]["unresolved"].pop()
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert HR.package_problems(pkg, drifted)


@pytest.mark.parametrize("mutate", [
    lambda d: d["tasks"].pop(3),
    lambda d: d["tasks"].insert(2, copy.deepcopy(d["tasks"][2])),
    lambda d: d["tasks"].__setitem__(slice(0, 2), d["tasks"][1::-1]),
    lambda d: d["call_order"].__setitem__(1, d["call_order"][0]),
    lambda d: d["tasks"][0].__setitem__("prompt_sha256", "0" * 64)])
def test_every_package_mutation_refuses(pkg, mutate):
    path = os.path.join(pkg, HR.MANIFEST_NAME)
    doc = json.loads(K._read(path))
    mutate(doc)
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert HR.package_problems(pkg, RUN)


def test_a_tampered_shipped_prefix_refuses(pkg):
    io.open(os.path.join(pkg, "prompt_prefix_item.txt"), "a",
            encoding="utf-8").write("\nan added rule.\n")
    assert HR.package_problems(pkg, RUN)


def test_a_missing_manifest_refuses_without_crashing(tmp_path):
    empty = str(tmp_path / "empty")
    os.makedirs(empty)
    out = HR.preflight(empty, RUN)
    assert out["ok"] is False and out["problems"]


def test_the_worst_case_never_breaks_the_global_ceiling(pkg):
    doc = K._load(os.path.join(pkg, HR.MANIFEST_NAME))
    assert doc["budget"]["primaries"] == 70
    assert doc["budget"]["after_primaries"] == doc["budget"]["before"] + 70
    assert doc["budget"]["worst_case_total"] == 140
    assert doc["budget"]["worst_case_after"] <= HR.GLOBAL_CEILING


def test_a_budget_over_the_ceiling_refuses(pkg, monkeypatch):
    monkeypatch.setattr(HR, "GLOBAL_CEILING", 4000)
    out = HR.preflight(pkg, RUN)
    assert out["ok"] is False
    assert any("global ceiling" in p for p in out["problems"])
