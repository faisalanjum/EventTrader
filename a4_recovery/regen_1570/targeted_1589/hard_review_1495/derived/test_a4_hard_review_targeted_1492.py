# -*- coding: utf-8 -*-
"""THE FROZEN A4 DOUBLE-BLIND REVIEW OF THE CORRECTED ITEMS (Codex SEQ 1492 B-D).

One fixed targeted wrapper over build_kfields_hard_review's ONE lifecycle:
the population is the complete corrected-inventory diff (11 items), each task
one located item read by exactly two independent blind calls under the
current v3 rules, fixed content first and the corrected item last, no draft,
reply, ruling, key or sibling visible. 11 tasks, 22 primary calls,
completed-before 5180, after 5202, worst 5224, ceiling 6000 - derived, never
typed here. Test first; zero calls; nothing frozen is written.
"""
import hashlib
import inspect
import io
import json
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_X = os.path.dirname(_HERE)

import audit_worker_access as AUD                                # noqa: E402
import build_exp5_contract as C                                  # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_hard_review_targeted as HRT                 # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402

TARGETED_RUN = "/tmp/a4_targeted_run_1491"
HR_PKG = os.path.join(_X, "kfields_hard_review")
HR_RUN = io.open(os.path.join(K.EVIDENCE, "a4_dir.txt"), encoding="utf-8").read().strip()


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _sha_text(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _clean_ledger():
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys; sys.path.insert(0, %r); sys.path.insert(0, "
         "'/home/faisal/EventMarketDB'); import a6_launch_freeze as A6; "
         "print(A6.ledger()[0])" % _HERE],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-600:]
    return int(out.stdout.strip())


@pytest.fixture(autouse=True)
def _fresh():
    HR._items.cache_clear()
    HR._source.cache_clear()
    yield
    HR._items.cache_clear()
    HR._source.cache_clear()


# ======================================================= population / numbers
def test_the_population_is_the_complete_corrected_diff_in_its_order():
    tasks = HRT.tasks()
    assert [t["members"] for t in tasks] == [[pid] for pid in T.targets()]
    assert [t["task_id"] for t in tasks] == ["hrt-%03d" % n for n in range(len(tasks))]
    assert {t["kind"] for t in tasks} == {"item"}
    assert len(tasks) == 11


def test_the_denominator_is_two_blind_calls_per_task():
    calls = HRT.canonical_calls()
    assert len(calls) == 2 * len(HRT.tasks()) == 22
    assert len(set(calls)) == 22
    assert calls == [HR.call_label(t["task_id"], b) for t in HRT.tasks() for b in HR.BLINDS]


def test_the_frozen_numbers_are_derived_from_the_ledger_and_the_owners():
    man = HRT.manifest()
    assert man["counts"] == {"tasks": 11, "item_tasks": 11, "group_tasks": 0,
                             "reviewed_packets": 11, "primary_calls": 22}
    b = man["budget"]; receipt = _load(HRT.BUDGET_RECEIPT)
    assert b["budget_receipt_sha256"] == _sha(HRT.BUDGET_RECEIPT)
    assert b["before"] == receipt["completed_before"] == _clean_ledger() == 5180
    assert b["primaries"] == 22 and b["after_primaries"] == 5202
    assert b["max_attempts_per_call"] == HR.MAX_ATTEMPTS == 2
    assert b["worst_case_after"] == 5224 and b["global_ceiling"] == receipt["ceiling"] == 6000
    assert man["semantic_rules_sha256"] == _sha_text(C.role_rules("drafter", BLM.PRODUCER_CONTRACT_SUFFIX))
    assert man["semantic_rules_sha256"] != _sha_text(C.role_rules("drafter"))
    assert man["contract_suffix"] == BLM.PRODUCER_CONTRACT_SUFFIX == ".v3"
    d = man["derived_from"]
    assert d["targets"] == T.targets()
    assert d["corrected_inventory_sha256"] == _sha(T.CORRECTED_INVENTORY)
    assert d["frozen_inventory_sha256"] == _sha(K.INV.INV)
    assert d["targeted_binding"]["binding_sha256"] == _sha(T.BINDING)
    assert d["targeted_binding"]["run_dir"] == TARGETED_RUN
    assert _load(T.BINDING)["attempts"][0]["finalization_sha256"] == _sha(TARGETED_RUN + "/finalization.json")


# ================================================================ prompts
def _payload_of(prompt):
    return json.loads(prompt[prompt.rindex("[INPUT]\n") + len("[INPUT]\n"):])


def test_every_prompt_is_fixed_content_first_and_the_corrected_item_last():
    frozen = {"%s#%03d" % (r["source_id"], n): r
              for n, r in enumerate(_load(K.INV.INV)["records"])}
    corrected = {"%s#%03d" % (r["source_id"], n): r
                 for n, r in enumerate(_load(T.CORRECTED_INVENTORY)["records"])}
    prefix = HRT.prompt_prefix("item")
    assert C.role_rules("drafter", ".v3") in prefix
    assert C.ONE_ITEM_ROLE in prefix and C.INJECTION_CONTROL in prefix
    for task in HRT.tasks():
        pid = task["members"][0]
        p = HRT.blind_prompt(task)
        assert p.startswith(prefix)
        payload = _payload_of(p)
        assert list(payload) == ["menu", "event", "item"]
        assert payload["item"] == {k: corrected[pid][k] for k in
                                   ("part_ref", "occurrence_in_part", "quote", "raw_label_or_claim")}
        assert payload["item"]["quote"] != frozen[pid]["quote"]        # the CORRECTED quote
        assert payload["event"]["source_id"] == corrected[pid]["source_id"]
    assert HRT.prompt_order_problems() == []


def test_no_prompt_or_package_byte_carries_a_draft_reply_ruling_key_or_sibling():
    items = {i["packet_id"]: i for i in T.targeted_items()}
    proved = []
    for base in (TARGETED_RUN, TARGETED_RUN + "/retry"):
        rawd = os.path.join(base, "raw")
        proved += [io.open(os.path.join(rawd, f), encoding="utf-8").read()
                   for f in os.listdir(rawd) if f.endswith(".proved.json")]
    prompts = [HRT.blind_prompt(t) for t in HRT.tasks()]
    prompts.append(io.open(os.path.join(HRT.PKG_DIR, "prompt_prefix_item.txt"), encoding="utf-8").read())
    for text in prompts:                      # what a blind call can SEE
        assert "codex" not in text.lower()
    texts = prompts + [io.open(os.path.join(HRT.PKG_DIR, f), encoding="utf-8").read()
                       for f in os.listdir(HRT.PKG_DIR)]
    for text in texts:                        # nothing in the package carries an answer
        for item in items.values():
            for d in item["a3_drafts"]:
                assert d["text"] not in text
        for reply in proved:
            assert reply not in text
            body = reply.strip().strip("`").strip()
            assert body[:200] not in text
    # no sibling: each prompt names exactly ONE located item and one event
    for t in HRT.tasks():
        payload = _payload_of(HRT.blind_prompt(t))
        assert isinstance(payload["item"], dict)


def test_two_blind_identities_share_the_prompt_and_differ_only_in_the_blind():
    for task in HRT.tasks():
        s1, s2 = HRT.render_launcher(task, 1), HRT.render_launcher(task, 2)
        assert s1 != s2
        line = lambda s: [l for l in s.splitlines() if l.startswith("const PROMPT = ")][0]
        assert line(s1) == line(s2)
        assert HR.call_label(task["task_id"], 1) in s1 and HR.call_label(task["task_id"], 2) in s2
        with pytest.raises(ValueError):
            HRT.render_launcher(task, 3)
        with pytest.raises(ValueError):
            HRT.render_launcher(task, 1, attempt=3)


# ============================================================ the package
def test_the_package_builds_twice_identically_and_is_compared_whole(tmp_path):
    a = HRT.build(str(tmp_path / "a"))
    b = HRT.build(str(tmp_path / "b"))
    assert a["manifest_sha256"] == b["manifest_sha256"] == _sha(os.path.join(HRT.PKG_DIR, HR.MANIFEST_NAME))
    assert HRT.package_problems(HRT.PKG_DIR) == []
    assert HRT.package_problems(str(tmp_path / "a")) == []


@pytest.mark.parametrize("path,value", [
    (("budget", "before"), 5168),
    (("counts", "primary_calls"), 21),
    (("call_order", 0), "hrt-000/b9"),
    (("tasks", 0, "prompt_sha256"), "0" * 64),
    (("semantic_rules_sha256",), "0" * 64),
    (("derived_from", "targets", 0), "x#000"),
])
def test_any_manifest_drift_arms_zero(tmp_path, path, value):
    pkg = str(tmp_path / "pkg")
    HRT.build(pkg)
    man = os.path.join(pkg, HR.MANIFEST_NAME)
    doc = _load(man)
    node = doc
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    io.open(man, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert HRT.package_problems(pkg), path
    with pytest.MonkeyPatch.context() as m:
        m.setattr(HRT, "PKG_DIR", pkg)
        got = HRT.prepare_run(str(tmp_path / "run"))
    assert got["ok"] is False and got["invocations"] == []


def test_the_public_doors_are_fixed_and_the_historical_ones_unchanged():
    assert list(inspect.signature(HRT.prepare_run).parameters) == ["out_dir"]
    assert list(inspect.signature(HRT.finalize).parameters) == ["out_dir"]
    assert list(inspect.signature(HR.prepare_run).parameters) == ["out_dir", "pkg_dir", "evidence_dir"]
    assert list(inspect.signature(HR.finalize).parameters) == ["out_dir", "pkg_dir", "evidence_dir"]
    assert list(inspect.signature(HR.build).parameters) == ["out_dir", "run_dir"]
    assert HRT.record_state is HR.record_state
    # the historical package still derives byte for byte from its own evidence
    # through the factored owner, except the one pin Codex already accepted
    # changing at SEQ 1488/1489: derived_from.owner_sha256 (build_kfields_key)
    assert HR.package_problems(HR_PKG, HR_RUN) == ["the pinned derived_from is not the live one"]
    pinned = _load(os.path.join(HR_PKG, HR.MANIFEST_NAME)); live = HR.manifest(HR_RUN)
    diff = {k for k in set(pinned) | set(live) if pinned.get(k) != live.get(k)}
    assert diff == {"derived_from"}
    dd = {k for k in pinned["derived_from"] if pinned["derived_from"][k] != live["derived_from"].get(k)}
    assert dd == {"owner_sha256"}
    assert live["derived_from"]["owner_sha256"] == _sha(os.path.join(_HERE, "build_kfields_key.py"))
    hist = _load(os.path.join(io.open(os.path.join(K.EVIDENCE, "hr_dir.txt")).read().strip(), "receipt.json"))
    assert hist["manifest_sha256"] == _sha(os.path.join(HR_PKG, HR.MANIFEST_NAME))
    assert hist["derived_from"]["owner_sha256"] == pinned["derived_from"]["owner_sha256"]


# ========================================================== the lifecycle
@pytest.fixture
def official(tmp_path, monkeypatch):
    session = tmp_path / "projects" / K.PARENT_SESSION
    (session / "workflows").mkdir(parents=True)
    real = AUD._official_location

    def located(state_path):
        p = os.path.realpath(str(state_path))
        if p.startswith(os.path.realpath(str(session))):
            return str(session), K.PARENT_SESSION
        return real(state_path)
    monkeypatch.setattr(AUD, "_official_location", located)
    return session


def _sparse(source_id):
    return ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "the two '
            'causes in this row cannot be split from the quote"}], '
            '"continuity_hints": []}' % json.dumps(source_id))


def build_call(session, task, blind, answer, attempt=1, run_id=None,
               doc_mutate=None, rec_mutate=None):
    label = HR.call_label(task["task_id"], blind)
    run_id = run_id or ("wf_" + label.replace("/", "_") + "_a%d" % attempt)
    prompt = HRT.blind_prompt(task)
    agent = "agent_" + run_id
    u0, u1 = "u0_" + run_id, "u1_" + run_id
    recs = [
        {"type": "user", "uuid": u0, "parentUuid": None, "agentId": agent,
         "sessionId": K.PARENT_SESSION, "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "uuid": u1, "parentUuid": u0, "agentId": agent,
         "sessionId": K.PARENT_SESSION, "effort": K.EFFORT, "requestId": "req_" + run_id,
         "message": {"role": "assistant", "id": "msg_" + run_id, "model": K.RUNTIME_MODEL_ID,
                     "stop_reason": "end_turn", "content": [{"type": "text", "text": answer}]}},
    ]
    if rec_mutate:
        rec_mutate(recs)
    tdir = session / "subagents" / "workflows" / run_id
    tdir.mkdir(parents=True, exist_ok=True)
    with io.open(str(tdir / ("agent-%s.jsonl" % agent)), "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    doc = {"runId": run_id, "status": "completed", "totalToolCalls": 0,
           "script": HRT.render_launcher(task, blind, attempt),
           "workflowProgress": [{"type": "workflow_agent", "state": "done", "label": label,
                                 "agentId": agent, "model": K.RUNTIME_MODEL_ID,
                                 "agentType": K.AGENT_TYPE, "toolCalls": 0}],
           "result": {"task_id": task["task_id"], "kind": task["kind"], "members": list(task["members"]),
                      "blind": blind, "attempt": attempt, "model": K.MODEL, "effort": K.EFFORT,
                      "agentType": K.AGENT_TYPE, "text": answer}}
    if doc_mutate:
        doc_mutate(doc)
    path = session / "workflows" / ("%s.json" % run_id)
    io.open(str(path), "w", encoding="utf-8").write(json.dumps(doc))
    return str(path)


def _items():
    return {i["packet_id"]: i for i in T.targeted_items()}


def test_a_valid_primary_finalizes_raw_first_and_write_once(tmp_path, official):
    items = _items()
    run = str(tmp_path / "hrt")
    got = HRT.prepare_run(run)
    assert got["ok"], got["problems"][:3]
    assert [i["label"] for i in got["invocations"]] == HRT.canonical_calls()
    for inv in got["invocations"]:
        assert _sha(inv["scriptPath"]) == inv["script_sha256"]
    rec = _load(os.path.join(run, HR.RECEIPT_NAME))
    assert rec["manifest_sha256"] == _sha(os.path.join(HRT.PKG_DIR, HR.MANIFEST_NAME))
    assert rec["allowed"] == HRT.canonical_calls()
    for task in HRT.tasks():
        for b in HR.BLINDS:
            s = build_call(official, task, b, _sparse(items[task["members"][0]]["source_id"]))
            assert HRT.record_state(run, s) == []
    doc = HRT.finalize(run)
    assert doc["problems"] == [] and doc["primary_complete"] is True
    assert doc["ledger"] == {"scheduled": 22, "valid": 22, "invalid_response": 0,
                             "transport_no_answer": 0, "unproved": 0, "missing": 0}
    assert doc["retry"] == [] and "child" not in doc
    assert doc["budget"]["ledger_before"] == 5180 and doc["budget"]["global_ceiling"] == 6000
    raw = os.listdir(os.path.join(run, "raw"))
    assert len([f for f in raw if f.endswith(".raw.json")]) == 22
    first = _sha(os.path.join(run, HR.FINALIZATION_NAME))
    with pytest.raises(ValueError):
        HRT.finalize(run)
    assert _sha(os.path.join(run, HR.FINALIZATION_NAME)) == first


def test_one_invalid_blind_call_earns_one_identical_child_and_never_a_third(tmp_path, official):
    items = _items()
    run = str(tmp_path / "hrt")
    assert HRT.prepare_run(run)["ok"]
    tasks = HRT.tasks()
    bad_task = tasks[4]
    for task in tasks:
        for b in HR.BLINDS:
            answer = "{not json" if (task is bad_task and b == 2) else _sparse(items[task["members"][0]]["source_id"])
            assert HRT.record_state(run, build_call(official, task, b, answer)) == []
    doc = HRT.finalize(run)
    bad_label = HR.call_label(bad_task["task_id"], 2)
    assert doc["ledger"]["valid"] == 21 and doc["ledger"]["invalid_response"] == 1
    assert doc["retry"] == [bad_label]
    child = doc["child"]
    assert [i["label"] for i in child["invocations"]] == [bad_label]
    assert child["invocations"][0]["attempt"] == 2
    assert io.open(child["invocations"][0]["scriptPath"], encoding="utf-8").read() == \
        HRT.render_launcher(bad_task, 2, 2)
    crec = _load(os.path.join(child["dir"], HR.RECEIPT_NAME))
    assert crec["allowed"] == [bad_label]
    assert crec["parent"]["finalization_sha256"] == _sha(os.path.join(run, HR.FINALIZATION_NAME))
    s2 = build_call(official, bad_task, 2, _sparse(items[bad_task["members"][0]]["source_id"]), attempt=2)
    assert HRT.record_state(child["dir"], s2) == []
    cdoc = HRT.finalize(child["dir"])
    assert cdoc["problems"] == [] and cdoc["ledger"]["valid"] == 1
    assert cdoc["retry"] == [] and "child" not in cdoc
    third = str(tmp_path / "third")
    HR._write_receipt(third, HRT.PKG_DIR, None, 3, [bad_label], ctx=HRT._ctx()) if hasattr(HR, "_ctx_receipt") else None


def test_a_tampered_state_is_unproved_and_blocks_the_child(tmp_path, official):
    items = _items()
    run = str(tmp_path / "hrt")
    assert HRT.prepare_run(run)["ok"]
    task = HRT.tasks()[0]

    def tamper(recs):
        recs[0]["message"]["content"] += " x"
    s = build_call(official, task, 1, _sparse(items[task["members"][0]]["source_id"]), rec_mutate=tamper)
    assert HRT.record_state(run, s) == []
    doc = HRT.finalize(run)
    outcomes = {k: o for k, o, _w in doc["outcomes"]}
    assert outcomes[HR.call_label(task["task_id"], 1)] == "unproved"
    assert doc["primary_complete"] is False and doc["retry"] == [] and "child" not in doc
    assert any(f.endswith(".raw.json") for f in os.listdir(os.path.join(run, "raw")))


# ========================================================== budget receipt
def test_the_new_budget_receipt_is_derived_and_the_old_one_untouched():
    new = _load(HRT.BUDGET_RECEIPT); old = _load("/tmp/a7_budget_receipt_1488.json")
    prev = _load("/tmp/a7_budget_receipt_1492.json")
    assert old["schema"] == "a7_call_budget_receipt/1488" and old["completed_before"] == 5168
    assert prev["schema"] == "a7_call_budget_receipt/1492" and prev["completed_before"] == 5180
    assert new["schema"] == "a7_call_budget_receipt/1493"
    assert new["completed_before"] == 5180 and new["ceiling"] == 6000
    s = {r["stage"]: r for r in new["stages"]}
    assert s["key_review"]["actual"] == 12 and s["key_review"]["shape"] == 0
    assert s["key_review"]["binding_sha256"] == _sha(T.BINDING)      # the ONE binding, reused
    assert s["hard_review"]["shape"] == 22 and s["hard_review"]["max"] == 44
    assert new["expected_shape_total"] == 5180 + sum(r["shape"] for r in new["stages"])
    assert new["expected_shape_total"] == 5931 and new["headroom_at_shape"] == 69
    assert new["calls_armed"] == 0
