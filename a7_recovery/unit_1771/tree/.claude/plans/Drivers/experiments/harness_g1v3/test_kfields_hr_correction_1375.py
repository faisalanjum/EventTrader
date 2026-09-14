"""Codex SEQ 1375 item 7 — the focused proof for the correction packet only.

Nothing here re-runs an accepted A4 control. The saved 21 group attempts are
the red/green evidence: the 11 malformed ones must still refuse through the
UNCHANGED reader, and the 10 lawful ones must still pass.
"""
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_hr_correction as FIX                        # noqa: E402

K = HR.K
_SCRATCH = os.environ.get(
    "KF_SCRATCH", "/tmp/claude-1000/-home-faisal-EventMarketDB/"
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
EVIDENCE = io.open(os.path.join(_SCRATCH, "a4_dir.txt"),
                   encoding="utf-8").read().strip()
RUN = io.open(os.path.join(_SCRATCH, "hr_dir.txt"),
              encoding="utf-8").read().strip()
PKG = os.path.join(os.path.dirname(EVIDENCE), "..", "kfields_hard_review")
PKG = os.path.normpath(os.path.join(
    _SCRATCH, "bench_1306/.claude/plans/Drivers/experiments/"
    "kfields_hard_review"))


@pytest.fixture(autouse=True)
def _fresh():
    HR._items.cache_clear()
    HR._source.cache_clear()
    yield
    HR._items.cache_clear()
    HR._source.cache_clear()


@pytest.fixture
def packet(tmp_path):
    out = str(tmp_path / "packet")
    FIX.build(out, RUN, EVIDENCE, PKG)
    return out


def _saved_group_attempts():
    """Every group reply this hard review actually paid for. -> [(task, text)]"""
    by = HR._by_label(EVIDENCE)
    out = []
    for base in (RUN, os.path.join(RUN, "retry")):
        receipt = K._load(os.path.join(base, HR.RECEIPT_NAME))
        for state in receipt["states"]:
            doc = K._load(state)
            row = [r for r in doc["workflowProgress"]
                   if r.get("type") == "workflow_agent"][0]
            task, _blind = by[row["label"]]
            if task["kind"] == "group":
                out.append((row["label"], task, K.direct_result(doc)["text"]))
    return out


def _copied_run(tmp_path):
    """A writable copy of both finalizations, for parent/denominator drift."""
    dst = str(tmp_path / "run")
    os.makedirs(os.path.join(dst, "retry"))
    for rel in (HR.FINALIZATION_NAME,
                os.path.join("retry", HR.FINALIZATION_NAME)):
        shutil.copy2(os.path.join(RUN, rel), os.path.join(dst, rel))
    return dst


# ================================ the saved evidence, unchanged reader ======
def test_the_saved_group_attempts_split_exactly_eleven_bad_ten_good():
    """Codex SEQ 1375: 11 of 21 malformed. The reader is NOT widened."""
    bad = good = 0
    for _lab, task, text in _saved_group_attempts():
        obj, problems = FIX.read_reply(text, task)
        if problems:
            bad += 1
            assert obj is None
        else:
            good += 1
            assert set(obj) == set(HR.GROUP_REPLY_KEYS)
    assert (bad, good) == (11, 10)
    assert bad + good == 21


def test_every_malformed_attempt_still_refuses_for_the_same_reason():
    seen = 0
    for _lab, task, text in _saved_group_attempts():
        obj, problems = FIX.read_reply(text, task)
        if not problems:
            continue
        seen += 1
        assert obj is None
        assert any("keys must be EXACTLY" in p or "not exactly" in p
                   for p in problems), problems
    assert seen == 11


def test_the_reader_is_the_released_one_not_a_widened_copy():
    """Same verdict AND same problem text on all 21, not merely same count."""
    for _lab, task, text in _saved_group_attempts():
        assert FIX.read_reply(text, task) == HR.read_reply(text, task)


# ============================================== the derived denominator =====
def test_the_denominator_is_derived_and_is_exactly_the_four():
    labels = FIX.correction_labels(RUN, EVIDENCE)
    assert labels == ["hr-029/b2", "hr-033/b1", "hr-033/b2", "hr-034/b1"]
    canon = HR.canonical_calls(EVIDENCE)
    assert labels == [lab for lab in canon if lab in set(labels)]
    by = HR._by_label(EVIDENCE)
    assert all(by[lab][0]["kind"] == "group" for lab in labels)


def test_a_wrong_parent_finalization_refuses(tmp_path):
    drifted = _copied_run(tmp_path)
    path = os.path.join(drifted, HR.FINALIZATION_NAME)
    doc = json.loads(K._read(path))
    doc["run_id"] = "some-other-run"
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    with pytest.raises(ValueError):
        FIX.correction_labels(drifted, EVIDENCE)


def test_a_changed_child_outcome_set_refuses(tmp_path):
    drifted = _copied_run(tmp_path)
    path = os.path.join(drifted, "retry", HR.FINALIZATION_NAME)
    doc = json.loads(K._read(path))
    # flip a row that really IS invalid; flipping an already-valid one is a
    # no-op mutation and would prove nothing
    for row in doc["outcomes"]:
        if row[1] == "invalid_response":
            row[1] = "valid"
            break
    else:
        raise AssertionError("the bound child has no invalid row to flip")
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    with pytest.raises(ValueError):
        FIX.correction_labels(drifted, EVIDENCE)


def test_canonical_order_drift_refuses(monkeypatch):
    """The order check must be reachable on its own.

    Mutating the child file cannot prove it: the parent-hash binding refuses
    first, so with the order check deleted the whole battery still passed.
    The reachable drift is the A4 canon moving under a byte-identical child.
    """
    real = HR.canonical_calls
    monkeypatch.setattr(HR, "canonical_calls",
                        lambda run: list(reversed(real(run))))
    with pytest.raises(ValueError):
        FIX.correction_labels(RUN, EVIDENCE)


def test_a_label_that_is_no_longer_a_scheduled_group_call_refuses(monkeypatch):
    real = HR._by_label

    def drifted(run):
        out = dict(real(run))
        lab = FIX.correction_labels.__globals__["HR"].canonical_calls(run)[0]
        task, blind = out[lab]
        out["hr-029/b2"] = (dict(task, kind="item"), blind)
        return out
    monkeypatch.setattr(HR, "_by_label", drifted)
    with pytest.raises(ValueError):
        FIX.correction_labels(RUN, EVIDENCE)


def test_a_reordered_child_outcome_list_refuses(tmp_path):
    drifted = _copied_run(tmp_path)
    path = os.path.join(drifted, "retry", HR.FINALIZATION_NAME)
    doc = json.loads(K._read(path))
    doc["outcomes"] = list(reversed(doc["outcomes"]))
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    with pytest.raises(ValueError):
        FIX.correction_labels(drifted, EVIDENCE)


def test_a_missing_finalization_refuses(tmp_path):
    empty = str(tmp_path / "nothing")
    os.makedirs(empty)
    with pytest.raises(ValueError):
        FIX.correction_labels(empty, EVIDENCE)


# ===================================================== the one correction ===
def test_the_corrected_prompt_names_the_exact_nested_four_key_shape():
    assert FIX.prompt_problems(RUN, EVIDENCE) == []
    boundary = HR._boundary()
    by = HR._by_label(EVIDENCE)
    for lab in FIX.correction_labels(RUN, EVIDENCE):
        task, _blind = by[lab]
        head = FIX.blind_prompt(task).split(boundary)[0]
        assert "`settled`" in head
        for key in HR.ITEM_REPLY_KEYS:
            assert ("`%s`" % key) in head
        assert "`facts` is the ARRAY that holds the sparse fact rows" in head
        assert "All four keys are required" in head


def test_only_the_group_output_block_moved_above_the_boundary():
    released, corrected = HR.prompt_prefix("group"), FIX.prompt_prefix()
    assert released != corrected
    spliced = released.replace(HR._output("group"), FIX.group_output(), 1)
    assert spliced == corrected
    # everything outside that one block is byte-identical
    assert released.replace(HR._output("group"), "") \
        == corrected.replace(FIX.group_output(), "")


def test_nothing_below_the_boundary_changed():
    boundary = HR._boundary()
    released, corrected = HR.prompt_prefix("group"), FIX.prompt_prefix()
    assert released[released.find(boundary):] \
        == corrected[corrected.find(boundary):]
    assert HR.C.INJECTION_CONTROL in corrected
    assert HR.C.role_rules("drafter") in corrected
    assert HR.C.one_item_output_section().rstrip() in corrected


def test_the_untrusted_payload_and_source_are_byte_unchanged():
    by = HR._by_label(EVIDENCE)
    corrected = FIX.prompt_prefix()
    for lab in FIX.correction_labels(RUN, EVIDENCE):
        task, _blind = by[lab]
        assert FIX.blind_prompt(task) \
            == corrected + json.dumps(HR.payload(task), indent=1)
        assert HR.blind_prompt(task).endswith(
            json.dumps(HR.payload(task), indent=1))


def test_the_item_prefix_is_untouched_by_this_correction():
    """The correction reviews group calls only; item prompts must not move."""
    assert HR.prompt_prefix("item") == HR.prompt_prefix("item")
    item_task = [t for t in HR.tasks(EVIDENCE) if t["kind"] == "item"][0]
    with pytest.raises(ValueError):
        FIX.blind_prompt(item_task)


def test_the_correction_refuses_if_the_released_wrapper_moved(monkeypatch):
    monkeypatch.setattr(HR, "_output", lambda kind: "a different block")
    with pytest.raises(ValueError):
        FIX.group_output()


# ============================================================ the packet ====
def test_the_packet_double_builds_byte_identically(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    FIX.build(a, RUN, EVIDENCE, PKG)
    FIX.build(b, RUN, EVIDENCE, PKG)
    for name in sorted(os.listdir(a)):
        assert K.INV.sha_file(os.path.join(a, name)) \
            == K.INV.sha_file(os.path.join(b, name)), name


def test_a_lawful_packet_passes_preflight(packet):
    out = FIX.preflight(packet, RUN, EVIDENCE, PKG)
    assert out["problems"] == []
    assert out["ok"] is True


def test_the_four_call_census_and_budget_are_exact(packet):
    doc = K._load(os.path.join(packet, FIX.MANIFEST_NAME))
    assert doc["counts"]["calls"] == 4
    assert doc["counts"]["tasks"] == 3
    assert doc["call_order"] == FIX.correction_labels(RUN, EVIDENCE)
    b = doc["budget"]
    assert (b["before"], b["after_primaries"], b["worst_case_after"]) \
        == (4307, 4311, 4315)
    assert b["worst_case_total"] == 8
    assert b["worst_case_after"] <= FIX.GLOBAL_CEILING == 4382


def test_capacity_is_measured_on_the_serialized_script(packet):
    doc = K._load(os.path.join(packet, FIX.MANIFEST_NAME))
    cap = doc["capacity"]
    assert cap["at_or_over_transport_limit"] == []
    assert cap["transport_limit_bytes"] == K.TRANSPORT_LIMIT
    assert cap["largest_script_bytes"] < K.TRANSPORT_LIMIT
    by = HR._by_label(EVIDENCE)
    for row in doc["calls"]:
        task, blind = by[row["label"]]
        assert row["script_sha256"] == K._sha(FIX.render_launcher(task, blind))


@pytest.mark.parametrize("mutate", [
    lambda d: d["calls"].pop(0),
    lambda d: d["calls"].insert(0, dict(d["calls"][0], label="hr-999/b1")),
    lambda d: d["call_order"].reverse(),
    lambda d: d["calls"][0].__setitem__("prompt_sha256", "0" * 64),
    lambda d: d.__setitem__("released_group_prefix_sha256", "0" * 64),
    lambda d: d["parent"].__setitem__("child_finalization_sha256", "0" * 64),
    lambda d: d["budget"].__setitem__("primaries", 8),
])
def test_every_packet_mutation_refuses(packet, mutate):
    path = os.path.join(packet, FIX.MANIFEST_NAME)
    doc = json.loads(K._read(path))
    mutate(doc)
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    assert FIX.package_problems(packet, RUN, EVIDENCE, PKG)


def test_a_tampered_shipped_prefix_refuses(packet):
    io.open(os.path.join(packet, FIX.PREFIX_NAME), "a",
            encoding="utf-8").write("\nan added rule.\n")
    assert FIX.package_problems(packet, RUN, EVIDENCE, PKG)


def test_a_released_builder_change_refuses(packet, monkeypatch):
    """The packet is bound to the released builder's exact bytes."""
    real = K.INV.sha_file

    def drifted(path):
        if path.endswith("build_kfields_hard_review.py"):
            return "0" * 64
        return real(path)
    monkeypatch.setattr(K.INV, "sha_file", drifted)
    assert FIX.package_problems(packet, RUN, EVIDENCE, PKG)


def test_a_third_attempt_and_a_third_blind_caller_refuse():
    by = HR._by_label(EVIDENCE)
    task, blind = by[FIX.correction_labels(RUN, EVIDENCE)[0]]
    for args in ((blind, FIX.MAX_ATTEMPTS + 1), (blind, 0),
                 (max(FIX.BLINDS) + 1, 1)):
        with pytest.raises(ValueError):
            FIX.render_launcher(task, *args)


def test_the_retry_keeps_the_identical_prompt():
    by = HR._by_label(EVIDENCE)
    task, blind = by[FIX.correction_labels(RUN, EVIDENCE)[0]]
    first, again = (FIX.render_launcher(task, blind, 1),
                    FIX.render_launcher(task, blind, 2))
    assert first != again
    line = "const PROMPT = "
    assert [x for x in first.splitlines() if x.startswith(line)] \
        == [x for x in again.splitlines() if x.startswith(line)]


def test_the_transport_is_the_frozen_one(packet):
    doc = K._load(os.path.join(packet, FIX.MANIFEST_NAME))
    t = doc["transport"]
    # the launcher REQUESTS the alias; the runtime RESOLVES it to the pinned
    # model id, and the official states carry the resolved id
    assert t["model_alias"] == K.MODEL == "sonnet"
    assert t["runtime_model_id"] == K.RUNTIME_MODEL_ID == "claude-sonnet-5"
    assert t["effort"] == K.EFFORT == "high"
    assert t["agentType"] == K.AGENT_TYPE == "lean-probe"
    # the runtime reads this from the environment, so it is the string form
    assert t["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == K.MAX_OUTPUT
    assert int(t["CLAUDE_CODE_MAX_OUTPUT_TOKENS"]) == 128000


# ================================================ SEQ 1376 — the run seam ===
# The official-state builder, the temp-session fixture and the lawful group
# reply are imported from the released 1372 suite, not written again.
import test_kfields_hard_review_1372 as T1372                    # noqa: E402

official = T1372.official                                        # noqa: F811


@pytest.fixture
def bound(packet):
    return FIX.Bound(packet=packet, run=RUN, evidence=EVIDENCE, released=PKG)


def _fix_call(session, task, blind, answer, attempt=1, run_id=None,
              script_path=None, doc_mutate=None, rec_mutate=None,
              transcript=True):
    """One official state for a CORRECTION call: the released builder, driven
    with the corrected prompt and the corrected launcher."""
    def mutate(doc):
        doc["script"] = FIX.render_launcher(task, blind, attempt)
        if doc_mutate:
            doc_mutate(doc)
    monkey = T1372._PROMPTS
    saved = monkey.get(task["task_id"])
    monkey[task["task_id"]] = FIX.blind_prompt(task)     # the corrected prompt
    try:
        return T1372.build_call(session, task, blind, answer, attempt=attempt,
                                run_id=run_id, script_path=script_path,
                                doc_mutate=mutate, rec_mutate=rec_mutate,
                                transcript=transcript)
    finally:
        if saved is None:
            monkey.pop(task["task_id"], None)
        else:
            monkey[task["task_id"]] = saved


def _lawful(task):
    return T1372._group_reply(task)


def full_route(tmp_path, session, bound, answers=None):
    """THE public route, using only what prepare_run returned."""
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    assert prep["ok"] is True, prep["problems"]
    by = HR._by_label(EVIDENCE)
    for inv in prep["invocations"]:
        task, blind = by[inv["label"]]
        kw = dict(answers or {}).get(inv["label"], {})
        state = _fix_call(session, task, blind,
                          kw.pop("answer", None) or _lawful(task),
                          attempt=inv["attempt"],
                          script_path=inv["scriptPath"], **kw)
        assert FIX.record_state(out, state) == []
    return out, prep


def test_prepare_publishes_exactly_four_literal_invocations(tmp_path, bound):
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    assert prep["ok"] is True and prep["problems"] == []
    assert [i["label"] for i in prep["invocations"]] \
        == FIX.correction_labels(RUN, EVIDENCE)
    assert len(prep["invocations"]) == 4
    by = HR._by_label(EVIDENCE)
    for inv in prep["invocations"]:
        assert inv["attempt"] == 1 and inv["args"] is None
        assert os.path.isfile(inv["scriptPath"])
        task, blind = by[inv["label"]]
        assert K._read(inv["scriptPath"]) == FIX.render_launcher(task, blind)
        assert K.INV.sha_file(inv["scriptPath"]) == inv["script_sha256"]


def test_prepare_refuses_a_dirty_directory(tmp_path, bound):
    out = str(tmp_path / "correction")
    os.makedirs(out)
    io.open(os.path.join(out, "stray"), "w", encoding="utf-8").write("x")
    assert FIX.prepare_run(out, bound)["ok"] is False


def test_a_lawful_four_call_route_closes_four_valid(tmp_path, official, bound):
    out, prep = full_route(tmp_path, official, bound)
    doc = FIX.finalize(out, bound)
    assert doc["problems"] == []
    assert doc["ledger"]["scheduled"] == 4
    assert doc["ledger"]["valid"] == 4
    assert doc["primary_complete"] is True
    assert doc["retry"] == [] and "child" not in doc
    assert len(doc["harvested_raw"]) == 4
    assert doc["budget"]["ledger_after"] == 4307 + 4
    assert doc["budget"]["within_ceiling"] is True


def test_one_schema_invalid_call_yields_exactly_one_child_then_closes(
        tmp_path, official, bound):
    labels = FIX.correction_labels(RUN, EVIDENCE)
    broken = labels[0]
    out, _prep = full_route(tmp_path, official, bound,
                            answers={broken: {"answer": "not a lawful reply"}})
    doc = FIX.finalize(out, bound)
    assert doc["problems"] == []
    assert doc["primary_complete"] is True
    assert doc["ledger"]["valid"] == 3
    assert doc["ledger"]["invalid_response"] == 1
    assert doc["retry"] == [broken]
    child = doc["child"]
    assert [i["label"] for i in child["invocations"]] == [broken]
    assert all(i["attempt"] == 2 for i in child["invocations"])

    by = HR._by_label(EVIDENCE)
    for inv in child["invocations"]:
        task, blind = by[inv["label"]]
        state = _fix_call(official, task, blind, _lawful(task), attempt=2,
                          run_id="wf_fixchild_" + inv["label"].replace("/", "_"),
                          script_path=inv["scriptPath"])
        assert FIX.record_state(child["dir"], state) == []
    kid = FIX.finalize(child["dir"], bound)
    assert kid["problems"] == []
    assert kid["attempt"] == 2
    assert kid["ledger"] == {"scheduled": 1, "valid": 1, "invalid_response": 0,
                             "transport_no_answer": 0, "unproved": 0,
                             "missing": 0}
    assert kid["retry"] == [] and "child" not in kid
    assert os.path.isfile(os.path.join(child["dir"], HR.FINALIZATION_NAME))
    assert kid["budget"]["spent_so_far"] == 5


def test_a_missing_state_is_missing_and_blocks_the_child(tmp_path, official,
                                                         bound):
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    by = HR._by_label(EVIDENCE)
    for inv in prep["invocations"][:-1]:
        task, blind = by[inv["label"]]
        FIX.record_state(out, _fix_call(official, task, blind, _lawful(task),
                                        script_path=inv["scriptPath"]))
    doc = FIX.finalize(out, bound)
    assert doc["ledger"]["missing"] == 1
    assert doc["primary_complete"] is False
    assert doc["retry"] == [] and "child" not in doc


def test_a_duplicate_state_refuses_with_raw_preserved(tmp_path, official,
                                                      bound):
    out, _prep = full_route(tmp_path, official, bound)
    by = HR._by_label(EVIDENCE)
    task, blind = by[FIX.correction_labels(RUN, EVIDENCE)[0]]
    twin = _fix_call(official, task, blind, _lawful(task), run_id="wf_fixtwin")
    assert FIX.record_state(out, twin) == []
    doc = FIX.finalize(out, bound)
    assert any("already served" in p for p in doc["problems"])
    assert doc["primary_complete"] is False
    assert len([n for n in os.listdir(os.path.join(out, "raw"))
                if n.endswith(".raw.json")]) == 5


def test_the_same_file_cannot_be_recorded_twice(tmp_path, official, bound):
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    task, blind = HR._by_label(EVIDENCE)[prep["invocations"][0]["label"]]
    state = _fix_call(official, task, blind, _lawful(task),
                      script_path=prep["invocations"][0]["scriptPath"])
    assert FIX.record_state(out, state) == []
    assert FIX.record_state(out, state) == ["that state is already recorded"]


def test_a_wrong_order_allowed_list_refuses(tmp_path, bound):
    out = str(tmp_path / "correction")
    FIX.prepare_run(out, bound)
    receipt = K._load(os.path.join(out, HR.RECEIPT_NAME))
    receipt["allowed"] = list(reversed(receipt["allowed"]))
    assert FIX.receipt_problems(out, bound, receipt)


def test_a_caller_subset_refuses(tmp_path, bound):
    out = str(tmp_path / "correction")
    FIX.prepare_run(out, bound)
    receipt = K._load(os.path.join(out, HR.RECEIPT_NAME))
    receipt["allowed"] = receipt["allowed"][:2]
    assert FIX.receipt_problems(out, bound, receipt)


def test_a_third_attempt_is_impossible_at_the_receipt(tmp_path, bound):
    out = str(tmp_path / "correction")
    FIX.prepare_run(out, bound)
    receipt = K._load(os.path.join(out, HR.RECEIPT_NAME))
    receipt["attempt"] = 3
    assert any("outside 1..2" in p
               for p in FIX.receipt_problems(out, bound, receipt))


def test_a_state_carrying_the_released_prompt_refuses(tmp_path, official,
                                                      bound):
    """The corrected run must not accept an answer to the OLD prompt."""
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    inv = prep["invocations"][0]
    task, blind = HR._by_label(EVIDENCE)[inv["label"]]
    stale = T1372.build_call(official, task, blind, _lawful(task),
                             script_path=inv["scriptPath"])
    FIX.record_state(out, stale)
    doc = FIX.finalize(out, bound)
    assert doc["ledger"]["valid"] == 0
    assert doc["primary_complete"] is False
    assert len([n for n in os.listdir(os.path.join(out, "raw"))
                if n.endswith(".raw.json")]) == 1


def test_a_receipt_fault_preserves_raw_and_grants_no_credit(tmp_path, official,
                                                            bound):
    out, _prep = full_route(tmp_path, official, bound)
    path = os.path.join(out, HR.RECEIPT_NAME)
    doc = json.loads(K._read(path))
    doc["correction_of"]["child_finalization_sha256"] = "0" * 64
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    fin = FIX.finalize(out, bound)
    assert fin["problems"]
    assert fin["ledger"]["valid"] == 0
    assert len([n for n in os.listdir(os.path.join(out, "raw"))
                if n.endswith(".raw.json")]) == 4


def test_the_old_failed_replies_are_never_credited(tmp_path, official, bound):
    """A saved malformed answer replayed into the corrected run stays invalid."""
    saved = {lab: text for lab, task, text in _saved_group_attempts()
             if FIX.read_reply(text, task)[1]}
    broken = FIX.correction_labels(RUN, EVIDENCE)[0]
    assert broken in saved
    out, _prep = full_route(tmp_path, official, bound,
                            answers={broken: {"answer": saved[broken]}})
    doc = FIX.finalize(out, bound)
    assert dict((lab, o) for lab, o, _w in doc["outcomes"])[broken] \
        == "invalid_response"


def test_a_state_whose_recorded_script_is_not_the_corrected_launcher_refuses(
        tmp_path, official, bound):
    """Isolates the launcher check.

    The transcript carries the CORRECTED prompt, so the official-proof input
    hash is happy; only the recorded `script` bytes are wrong. Without this the
    launcher guard could be deleted and the whole battery still passed.
    """
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    inv = prep["invocations"][0]
    task, blind = HR._by_label(EVIDENCE)[inv["label"]]
    FIX.record_state(out, _fix_call(
        official, task, blind, _lawful(task), script_path=inv["scriptPath"],
        doc_mutate=lambda d: d.__setitem__(
            "script", HR.render_launcher(task, blind, 1))))
    doc = FIX.finalize(out, bound)
    assert doc["ledger"]["valid"] == 0
    assert any("corrected launcher bytes" in p for p in doc["problems"])
    assert len([n for n in os.listdir(os.path.join(out, "raw"))
                if n.endswith(".raw.json")]) == 1


def test_a_scriptpath_whose_bytes_moved_refuses(tmp_path, official, bound):
    out = str(tmp_path / "correction")
    prep = FIX.prepare_run(out, bound)
    inv = prep["invocations"][0]
    task, blind = HR._by_label(EVIDENCE)[inv["label"]]
    state = _fix_call(official, task, blind, _lawful(task),
                      script_path=inv["scriptPath"])
    io.open(inv["scriptPath"], "a", encoding="utf-8").write("// edited\n")
    FIX.record_state(out, state)
    doc = FIX.finalize(out, bound)
    assert doc["ledger"]["valid"] == 0
    assert any("scriptPath bytes" in p for p in doc["problems"])
