"""Two measured live transport shapes the A1 audit did not handle.

SHAPE 1 (Codex SEQ 1349) - the official `promptPreview` is a DISPLAY prefix
ending in one U+2026, so comparing it raw rejected every lawful call.

SHAPE 2 (Codex SEQ 1349, corrected by SEQ 1350) - when a reply carries no
visible text the runtime RESETS the response: it closes that response, inserts
its own user turn, and the child answers under a NEW response identity. The
earlier test spliced the input INSIDE one response group, which erased the reset
and proved a topology that does not occur. These reproduce the exact live shape:

    user(pinned) -> response A: thinking only, end_turn
                 -> user(added by the runtime)
                 -> response B: end_turn, the answer text

That answer earns ZERO credit and exactly one fresh attempt. Nothing here reads
the injected text or any reply content: the topology is what is owned.

    venv/bin/python -m pytest <this file> -q
"""
import collections
import io
import json
import os

import pytest

import audit_worker_access as AUD
import raw_transport as RT
import test_harness_guards as TG        # the ONE official-run fixture, reused

ELLIPSIS = "…"
_MISSING = object()


def _row(st):
    return st["workflowProgress"][1]


def _audit(tmp_path, mutate_state=None, mutate_tx=None):
    fix = TG._a1_official_run(tmp_path, mutate_state, mutate_tx)
    return TG._a1_audit_in(fix), fix


def _per_key(out):
    per = collections.defaultdict(list)
    for k, o, _w in out["outcomes"]:
        per[tuple(k)].append(o)
    return per


def _credited(out):
    return {tuple(k) for k, _v in out["answers"]}


# ============================ SHAPE 1: the display marker ====================
def test_a_plain_exact_prefix_is_still_accepted(tmp_path):
    """LAWFUL CONTROL: the shape the fixture always used must keep passing."""
    out, _ = _audit(tmp_path)
    assert not any("prompt preview" in p for p in out["problems"])


def test_the_exact_official_ellipsized_prefix_is_accepted(tmp_path):
    def go(st):
        pr = _row(st)
        pr["promptPreview"] = pr["promptPreview"] + ELLIPSIS
    out, _ = _audit(tmp_path, go)
    assert not [p for p in out["problems"] if "prompt preview" in p]


@pytest.mark.parametrize("label", [
    "missing", "non-string", "empty", "ellipsis only",
    "three dots instead of the marker", "a wrong character before the marker",
    "a wrong prefix entirely",
])
def test_every_other_preview_shape_still_refuses(tmp_path, label):
    def go(st):
        pr = _row(st)
        real = pr["promptPreview"]
        if label == "missing":
            pr.pop("promptPreview", None)
        elif label == "non-string":
            pr["promptPreview"] = 17
        elif label == "empty":
            pr["promptPreview"] = ""
        elif label == "ellipsis only":
            pr["promptPreview"] = ELLIPSIS
        elif label == "three dots instead of the marker":
            pr["promptPreview"] = real + "..."
        elif label == "a wrong character before the marker":
            pr["promptPreview"] = real[:-1] + "Z" + ELLIPSIS
        else:
            pr["promptPreview"] = "not the prompt at all" + ELLIPSIS
    out, _ = _audit(tmp_path, go)
    assert any("prompt preview" in p for p in out["problems"]), \
        "%s was accepted" % label


# ====================== SHAPE 2: the measured response reset =================
def _reset_response(tx, _n, answer=None, tools=False):
    """THE EXACT LIVE SHAPE: response A closes with no visible text, the runtime
    adds input, response B answers under a DISTINCT identity."""
    a = tx[1]
    # every id is per-worker: a response identity shared across workers is a
    # DIFFERENT fault the auditor rightly refuses, and would hide this one
    aid = a["agentId"]
    body = [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}] \
        if tools else [{"type": "thinking", "thinking": "..."}]
    tx.insert(1, {"type": "assistant", "uuid": "reset-%s" % aid,
                  "parentUuid": tx[0]["uuid"], "requestId": "req-reset-%s" % aid,
                  "effort": a["effort"], "agentId": aid,
                  "sessionId": a["sessionId"],
                  "message": {"role": "assistant", "id": "msg-reset-%s" % aid,
                              "model": a["message"]["model"],
                              "stop_reason": "end_turn", "content": body}})
    tx.insert(2, {"type": "user", "uuid": "added-%s" % aid,
                  "parentUuid": "reset-%s" % aid, "agentId": aid,
                  "sessionId": a["sessionId"],
                  "message": {"role": "user", "content": "continue"}})
    tx[3]["parentUuid"] = "added-%s" % aid
    if answer is not None:
        tx[3]["message"]["content"] = [{"type": "text", "text": answer}]


def _maxtokens_continuation(tx, _n):
    """A REAL assistant-only continuation: distinct groups, the non-final one
    ending max_tokens, the final ending end_turn, and NO added input."""
    a = tx[1]
    aid = a["agentId"]
    tx.insert(1, {"type": "assistant", "uuid": "cont-%s" % aid,
                  "parentUuid": tx[0]["uuid"], "requestId": "req-cont-%s" % aid,
                  "effort": a["effort"], "agentId": aid,
                  "sessionId": a["sessionId"],
                  "message": {"role": "assistant", "id": "msg-cont-%s" % aid,
                              "model": a["message"]["model"],
                              "stop_reason": "max_tokens",
                              "content": [{"type": "text", "text": "part one "}]}})
    tx[2]["parentUuid"] = "cont-%s" % aid


def _affected(out):
    return {k for k, v in _per_key(out).items() if v != ["served"]}


def test_the_exact_live_reset_is_one_invalid_response_and_nothing_else(tmp_path):
    out, _ = _audit(tmp_path, None, _reset_response)
    per = _per_key(out)
    hit = {k for k, v in per.items() if v == [RT.A1_INVALID_RESPONSE]}
    assert hit, "no key was classified %s: %s" % (
        RT.A1_INVALID_RESPONSE, dict(list(per.items())[:3]))
    for k in hit:
        assert per[k] == [RT.A1_INVALID_RESPONSE], (k, per[k])
    assert not (hit & _credited(out)), "an uncreditable answer was credited"
    assert _affected(out) == hit, (
        "other keys were disturbed: %s" % (_affected(out) - hit))


def test_a_real_max_token_continuation_is_served_credited_and_clean(tmp_path):
    """LAWFUL CONTROL beside the mutation above."""
    out, _ = _audit(tmp_path, None, _maxtokens_continuation)
    per = _per_key(out)
    assert set(sum(per.values(), [])) == {"served"}, \
        {k: v for k, v in per.items() if v != ["served"]}
    assert set(per) == _credited(out), "a served answer was not credited"
    assert not out["problems"], out["problems"][:3]


def test_every_scheduled_key_gets_exactly_one_terminal_outcome(tmp_path):
    out, _ = _audit(tmp_path, None, _reset_response)
    per = _per_key(out)
    many = {k: v for k, v in per.items() if len(v) != 1}
    assert not many, "keys with more than one terminal outcome: %s" % (
        dict(list(many.items())[:3]))
    plan = TG._a1_plan()
    assert len(per) == plan["n_calls"], (
        "%d keys classified against the fixed denominator %d"
        % (len(per), plan["n_calls"]))


@pytest.mark.parametrize("label", ["tool use", "wrong first prompt",
                                   "result text mismatch"])
def test_the_same_topology_with_another_fault_is_fail_closed(tmp_path, label):
    tx_mut = state_mut = None
    if label == "tool use":
        tx_mut = lambda tx, n: _reset_response(tx, n, tools=True)
    elif label == "wrong first prompt":
        def tx_mut(tx, n):
            _reset_response(tx, n)
            tx[0]["message"]["content"] = "a different prompt entirely"
    else:
        tx_mut = lambda tx, n: _reset_response(tx, n, answer="other text")
    out, _ = _audit(tmp_path, state_mut, tx_mut)
    per = _per_key(out)
    assert RT.A1_INVALID_RESPONSE not in sum(per.values(), []), \
        "%s still produced %s" % (label, RT.A1_INVALID_RESPONSE)
    assert {k for k, v in per.items() if v != ["served"]}, \
        "%s was not refused at all" % label


# ------------------------------- the supported end-to-end path ---------------
def test_audit_to_classification_to_retry_is_the_supported_path(tmp_path):
    """audit -> a1_classify -> finalization -> the existing retry derivation."""
    fix = TG._a1_official_run(tmp_path, None, _reset_response)
    got = TG._a1_finalize_in(fix["work"], fix["run_dir"], fix["projects"])
    assert got.returncode == 0, got.stderr[-2000:]
    fin = json.loads(got.stdout)
    final = {tuple(k): v for k, v in fin["classification"]}
    hit = {k for k, v in final.items() if v == RT.A1_INVALID_RESPONSE}
    assert hit, collections.Counter(final.values())
    assert not {tuple(k) for k, v in fin["validity"]} & hit, \
        "an uncreditable answer reached validity"
    retry = {tuple(c) for c in fin["retry"]}
    assert retry == hit, (
        "the retry set is %d keys, the invalid responses are %d"
        % (len(retry), len(hit)))
    for c in fin["retry"]:
        assert list(fin["retry"]).count(c) == 1, "a key is retried twice"
    assert RT.a1_retry_set(final, {}, sorted(final), 2) == [], \
        "attempt 2 produced a successor"


# ---------------------------------------------- the retry owner, in isolation ---
def test_invalid_response_earns_exactly_one_retry_at_attempt_1_and_none_at_2():
    key = ("p#000", "p#000/L1")
    allowed = [key, ("p#001", "p#001/L1")]
    final = {key: RT.A1_INVALID_RESPONSE, allowed[1]: "served"}
    assert RT.a1_retry_set(final, {allowed[1]: True}, allowed, 1) == [key]
    assert RT.a1_retry_set(final, {allowed[1]: True}, allowed, 2) == []


@pytest.mark.parametrize("outcome", ["integrity_refusal", "tool_violation",
                                     "duplicate", "spawned_without_answer",
                                     "unexpected"])
def test_no_other_outcome_gains_a_retry(outcome):
    key = ("p#000", "p#000/L1")
    assert RT.a1_retry_set({key: outcome}, {}, [key], 1) == []


def test_the_invalid_answer_retry_is_unchanged():
    key = ("p#000", "p#000/L1")
    assert RT.a1_retry_set({key: "served"}, {key: False}, [key], 1) == [key]
    assert RT.a1_retry_set({key: "served"}, {key: True}, [key], 1) == []


def test_the_outcome_string_has_exactly_one_owner():
    assert RT.A1_INVALID_RESPONSE in RT.A1_OUTCOMES
    assert RT.A1_INVALID_RESPONSE in RT.A1_AUDIT_OWNED
    src = open(os.path.join(os.path.dirname(os.path.abspath(RT.__file__)),
                            "raw_transport.py"), encoding="utf-8").read()
    assert src.count('"%s"' % RT.A1_INVALID_RESPONSE) == 1, \
        "the literal is restated instead of naming its owner"


# ================= the single-response marker class (Codex SEQ 1352 item 1) ==
# A response the runtime completes in ONE contiguous identity may carry markers
# on more than its last record. That is not a continuation and never was: a
# continuation is what `max_tokens` means. So for exactly one response identity
# any number of markers is lawful while EVERY present marker is `end_turn`, the
# one-terminal-text rule is untouched, and a `max_tokens` there still refuses.
# The multi-response rule is deliberately left strict.
def _one_group(tx, markers, texts=None):
    """Rebuild the single assistant response as N records of ONE identity.

    `markers[i]` is that record's stop_reason; `texts[i]` its text (default:
    only the last record carries the answer). Nothing else about the fixture
    changes, so every other proof still has to pass.
    """
    a = tx[1]
    aid, answer = a["agentId"], a["message"]["content"]
    texts = [None] * (len(markers) - 1) + [answer] if texts is None else texts
    rebuilt, parent = [], tx[0]["uuid"]
    for i, (mark, body) in enumerate(zip(markers, texts)):
        rebuilt.append({
            "type": "assistant", "uuid": "grp-%s-%d" % (aid, i),
            "parentUuid": parent, "requestId": "req-grp-%s" % aid,
            "effort": a["effort"], "agentId": aid, "sessionId": a["sessionId"],
            "message": {"role": "assistant", "id": "msg-grp-%s" % aid,
                        "model": a["message"]["model"], "stop_reason": mark,
                        "content": body if body is not None
                        else [{"type": "thinking", "thinking": "..."}]}})
        parent = rebuilt[-1]["uuid"]
    tx[1:] = rebuilt


def _served_only(out):
    return set(sum(_per_key(out).values(), [])) == {"served"}


@pytest.mark.parametrize("label,markers", [
    ("one record ending end_turn", ["end_turn"]),
    ("one record carrying no marker at all", [None]),
    ("two records, only the last marked", [None, "end_turn"]),
    ("two records, both marked end_turn", ["end_turn", "end_turn"]),
])
def test_every_lawful_single_response_marker_shape_is_served(tmp_path, label,
                                                             markers):
    out, _ = _audit(tmp_path, None, lambda tx, n: _one_group(tx, markers))
    assert _served_only(out), (label, out["problems"][:2])
    assert set(_per_key(out)) == _credited(out), "a served answer was not credited"


@pytest.mark.parametrize("label,markers", [
    ("a noncompletion marker on the single response", ["max_tokens"]),
    ("a noncompletion marker on an earlier record", ["max_tokens", "end_turn"]),
    ("an unknown marker", ["stop_sequence"]),
])
def test_any_non_end_turn_marker_on_one_response_still_refuses(tmp_path, label,
                                                              markers):
    out, _ = _audit(tmp_path, None, lambda tx, n: _one_group(tx, markers))
    assert not _served_only(out), "%s was served" % label
    assert RT.A1_INVALID_RESPONSE not in sum(_per_key(out).values(), []), \
        "%s was mistaken for the added-input class" % label


def test_text_on_an_earlier_record_of_one_response_still_refuses(tmp_path):
    """LAWFUL CONTROL's opposite: exactly one terminal text record, unchanged."""
    def go(tx, _n):
        a = dict(tx[1]["message"])
        _one_group(tx, ["end_turn", "end_turn"],
                   texts=[a["content"], a["content"]])
    out, _ = _audit(tmp_path, None, go)
    assert not _served_only(out), "two text-bearing records were served"


def test_a_multi_response_missing_its_final_marker_still_refuses(tmp_path):
    def go(tx, _n):
        _maxtokens_continuation(tx, _n)
        tx[-1]["message"]["stop_reason"] = None
    out, _ = _audit(tmp_path, None, go)
    assert not _served_only(out), "a multi-response with no final marker was served"


def test_the_lawful_multi_response_continuation_is_unchanged(tmp_path):
    """LAWFUL CONTROL: non-final max_tokens, final end_turn, still served."""
    out, _ = _audit(tmp_path, None, _maxtokens_continuation)
    assert _served_only(out), out["problems"][:2]


# ============== the immutable superseded run, re-audited (SEQ 1352 item 3) ===
def run_armed_against(runs_root, plan_sha):
    """THE run whose receipt names this exact plan, and only that one.

    Identity, never a name: selecting by directory prefix, by date or by
    counting runs breaks the moment a second primary exists beside the first
    (Codex SEQ 1353). A receipt states the plan it was armed against, so the
    rebuilt plan picks its own run, and anything other than exactly one match
    is a refusal rather than a guess.
    """
    hits = []
    for name in sorted(os.listdir(runs_root)):
        receipt = os.path.join(runs_root, name, "receipt.json")
        if not os.path.isfile(receipt):
            continue
        try:
            armed = json.load(io.open(receipt, encoding="utf-8"))
        except Exception:                                 # noqa: BLE001
            continue
        if isinstance(armed, dict) and armed.get("manifest_sha256") == plan_sha:
            hits.append(os.path.realpath(os.path.join(runs_root, name)))
    assert len(hits) == 1, (
        "expected exactly one run armed against plan %s, found %d: %s"
        % (plan_sha[:12], len(hits), [os.path.basename(h) for h in hits]))
    return hits[0]


# RETIRED (Codex SEQ 1478): `test_the_superseded_run_reaudits_as_378_served_
# and_14_unrun` rebuilt SIGNED, CLOSED evidence with today's builders. The
# rebuild no longer reproduces the launcher bytes the run was armed with, so
# the re-audit read every slot as unanswered - a fact about the rebuild, not
# about the historical run, which is present and unmodified. The signed A4
# lock is the authority for that work and it is not re-run or patched here.
# `run_armed_against` below is KEPT, and its four selector proofs are the
# lawful controls for this file.


# --------------------------------------------- the selector itself (SEQ 1353) ---
def _fake_run(root, name, plan_sha):
    os.makedirs(os.path.join(root, name))
    io.open(os.path.join(root, name, "receipt.json"), "w",
            encoding="utf-8").write(json.dumps({"run_id": name,
                                                "manifest_sha256": plan_sha}))


def test_the_selector_ignores_a_run_armed_against_another_plan(tmp_path):
    """THE CASE THAT BROKE IT: a second primary with the SAME name prefix. Only
    the plan hash decides, so the newcomer is simply not this plan's run."""
    root = str(tmp_path / "runs")
    os.makedirs(root)
    _fake_run(root, "kf-a3-one-item-196x2-primary-OLD", "a" * 64)
    _fake_run(root, "kf-a3-one-item-196x2-primary-NEW", "b" * 64)
    assert os.path.basename(run_armed_against(root, "a" * 64)).endswith("OLD")
    assert os.path.basename(run_armed_against(root, "b" * 64)).endswith("NEW")


def test_the_selector_refuses_when_no_run_names_the_plan(tmp_path):
    root = str(tmp_path / "runs")
    os.makedirs(root)
    _fake_run(root, "kf-a3-one-item-196x2-primary-NEW", "b" * 64)
    with pytest.raises(AssertionError, match="found 0"):
        run_armed_against(root, "a" * 64)


def test_the_selector_refuses_when_two_runs_name_the_same_plan(tmp_path):
    """Two receipts naming one plan is ambiguous evidence, never a pick."""
    root = str(tmp_path / "runs")
    os.makedirs(root)
    _fake_run(root, "kf-a3-one-item-196x2-primary-A", "a" * 64)
    _fake_run(root, "kf-a3-one-item-196x2-primary-B", "a" * 64)
    with pytest.raises(AssertionError, match="found 2"):
        run_armed_against(root, "a" * 64)


def test_the_selector_ignores_directories_without_a_readable_receipt(tmp_path):
    """LAWFUL CONTROL: junk beside the runs never changes the answer."""
    root = str(tmp_path / "runs")
    os.makedirs(root)
    _fake_run(root, "kf-a3-one-item-196x2-primary-OLD", "a" * 64)
    os.makedirs(os.path.join(root, "no-receipt-here"))
    os.makedirs(os.path.join(root, "broken"))
    io.open(os.path.join(root, "broken", "receipt.json"), "w").write("{not json")
    assert os.path.basename(run_armed_against(root, "a" * 64)).endswith("OLD")
