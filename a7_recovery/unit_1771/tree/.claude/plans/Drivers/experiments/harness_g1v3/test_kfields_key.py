"""Focused proofs for the ONE active K-fields key owner (Codex SEQ 1359).

RED FIRST: every check here fails before build_kfields_key.py exists, and each
one names a behaviour Codex required, not an implementation detail.

Nothing is hand-listed. Counts, hashes, orders and field names are read from
the frozen artifacts and the existing owners, so a real change moves the proof
instead of silently passing.

    venv/bin/python -m pytest <this file> -q
"""
import copy
import hashlib
import io
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_X = os.path.dirname(_HERE)
for _p in (_HERE, "/home/faisal/EventMarketDB"):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import build_kfields_key as K                                   # noqa: E402
import validate_benchmark_inventory as INV                      # noqa: E402


def sha(t):
    return hashlib.sha256(t.encode("utf-8") if isinstance(t, str)
                          else t).hexdigest()


# ----------------------------------------------------------- lineage (item 3)
def test_history_168_and_final_196_coexist():
    """The frozen package shipped 168 proposals; the accepted review produced
    196 records. Both are true at once and neither is forced onto the other."""
    hist = K.historical_package()
    assert hist["problems"] == [], hist["problems"]
    live = json.load(io.open(INV.INV, encoding="utf-8"))
    assert hist["proposals"] != len(live["records"])
    assert hist["proposals"] == sum(e["proposals"] for e in hist["manifest"]["events"])
    assert len(live["records"]) == live["counts"]["records"]


def test_the_frozen_package_bytes_are_only_read_never_rebuilt():
    """The historical owner and its package must be byte-identical afterwards."""
    before = {p: sha(io.open(p, "rb").read()) for p in K.historical_paths()}
    K.historical_package()
    after = {p: sha(io.open(p, "rb").read()) for p in K.historical_paths()}
    assert before == after


def test_the_missing_original_source_blob_is_recorded_not_synthesized():
    """The manifest names a candidate-inventory sha that no longer exists. The
    gap is reported honestly and no bytes are invented to fill it."""
    gap = K.historical_source_gap()
    named = K.historical_package()["manifest"]["inventory"]["sha256"]
    assert gap["named_sha256"] == named
    assert gap["found"] is False
    assert gap["searched"], "a gap claim with no search is not evidence"
    for path in gap["searched"]:
        assert os.path.exists(path), path
    assert gap["bound_instead"] == "frozen_package_inputs"


# ------------------------------------------------- the adopted seam (item 4)
def test_materialization_reproduces_the_signed_inventory_exactly():
    out = K.materialize()
    assert out["problems"] == [], out["problems"][:5]
    assert sha(out["inventory_text"]) == INV.sha_file(INV.INV)
    assert out["inventory_text"] == io.open(INV.INV, encoding="utf-8").read()


def test_the_reproduced_counts_are_the_accepted_ones():
    inv = json.loads(K.materialize()["inventory_text"])
    live = json.load(io.open(INV.INV, encoding="utf-8"))
    assert inv["counts"] == live["counts"]
    assert len({r["source_id"] for r in inv["records"]}) == \
        live["counts"]["source_events"]


def test_every_hard_class_still_clears_its_own_floor():
    out = K.materialize()
    for cls in INV.HARD_CLASSES:
        assert out["hard_class_counts"][cls] >= INV.TAG_FLOOR, cls


@pytest.mark.parametrize("what", ["drop", "add", "reorder", "alter_quote",
                                  "alter_class", "alter_kind"])
def test_a_mutated_derivation_is_refused(what):
    """MUTATION: the boundary must refuse a swapped, missing, extra, reordered
    or altered row rather than reproduce the signed inventory."""
    out = K.materialize()
    recs = copy.deepcopy(json.loads(out["inventory_text"])["records"])
    if what == "drop":
        recs.pop(0)
    elif what == "add":
        recs.append(copy.deepcopy(recs[0]))
    elif what == "reorder":
        recs[0], recs[-1] = recs[-1], recs[0]
    elif what == "alter_quote":
        recs[0]["quote"] = recs[0]["quote"] + " x"
    elif what == "alter_class":
        recs[0]["proposed_hard_classes"] = []
    else:
        kinds = [k for k in INV.RECORD_KINDS
                 if k != recs[0]["proposed_record_kind"]]
        recs[0]["proposed_record_kind"] = kinds[0]
    assert K.final_boundary_problems(recs), "the mutation was accepted"


def test_the_unmutated_derivation_is_accepted():
    """LAWFUL CONTROL beside the mutations: a battery where everything fails
    is a broken check, not a strong one."""
    recs = json.loads(K.materialize()["inventory_text"])["records"]
    assert K.final_boundary_problems(recs) == []


def test_evidence_may_not_be_borrowed_across_sources():
    """MUTATION: a row that keeps its quote but claims another event refuses."""
    recs = copy.deepcopy(json.loads(K.materialize()["inventory_text"])["records"])
    other = [r for r in recs if r["source_id"] != recs[0]["source_id"]][0]
    recs[0]["source_id"] = other["source_id"]
    assert K.final_boundary_problems(recs)


# --------------------------------------------------- the adopted lock shape
def test_the_lock_rederives_and_every_bound_value_refuses_when_mutated():
    lock = K.lock()
    assert K.lock_problems(lock) == [], K.lock_problems(lock)[:3]
    for field in sorted(lock["artifacts"]):
        bad = copy.deepcopy(lock)
        bad["artifacts"][field] = "0" * 64
        assert K.lock_problems(bad), "artifact %s does not refuse" % field
    for field in ("signed", "blocked", "run_id", "agent_id", "raw_sha256"):
        bad = copy.deepcopy(lock)
        bad["signer"][field] = "tampered"
        assert K.lock_problems(bad), "signer %s does not refuse" % field


def test_a_stale_lock_refuses():
    """MUTATION: a lock whose counts no longer match the live derivation."""
    bad = copy.deepcopy(K.lock())
    first = sorted(bad["counts"])[0]
    bad["counts"][first] = -1
    assert K.lock_problems(bad)


# ------------------------------------------------------- A4 phase 1 (item 5)
def test_phase1_is_one_call_per_frozen_item_in_a_fixed_order():
    items = K.phase1_items()
    live = json.load(io.open(INV.INV, encoding="utf-8"))
    assert len(items) == len(live["records"])
    assert [i["packet_id"] for i in items] == \
        sorted({i["packet_id"] for i in items}, key=[i["packet_id"] for i in items].index)
    assert len({i["packet_id"] for i in items}) == len(items)
    assert K.phase1_items() == items, "the order is not deterministic"


def test_every_item_carries_exactly_two_a3_drafts():
    for item in K.phase1_items():
        assert len(item["a3_drafts"]) == 2, item["packet_id"]
        assert len({d["lane_id"] for d in item["a3_drafts"]}) == 2


def test_the_rules_prefix_is_byte_identical_across_every_call():
    prefixes = {K.phase1_prompt(i).split(K.SOURCE_MARK, 1)[0]
                for i in K.phase1_items()}
    assert len(prefixes) == 1, "the fixed rules block drifts between calls"


def test_the_drafts_come_last_and_the_source_is_never_shortened():
    for item in K.phase1_items()[:12]:
        text = K.phase1_prompt(item)
        assert text.index(K.SOURCE_MARK) < text.index(K.DRAFTS_MARK)
        assert text.index(K.ITEM_MARK) < text.index(K.DRAFTS_MARK)
        for part in K.source_parts(item["source_id"]).values():
            assert part in text, "source context was shortened"


def test_the_prompt_never_leaks_the_answer_key():
    """No machine tag, record kind or other adjudicator's conclusion."""
    live = json.load(io.open(INV.INV, encoding="utf-8"))
    by_packet = {i["packet_id"]: i for i in K.phase1_items()}
    for rec, item in zip(live["records"], K.phase1_items()):
        text = K.phase1_prompt(item)
        assert rec["proposed_record_kind"] not in text
        for cls in rec["proposed_hard_classes"]:
            assert cls not in text
    assert by_packet, "no items"


def test_one_item_only_per_call():
    items = K.phase1_items()
    text = K.phase1_prompt(items[0])
    assert text.count(K.ITEM_MARK) == 1
    other = items[1]
    assert other["quote"] not in text.split(K.ITEM_MARK, 1)[1] \
        or other["quote"] in K.source_parts(items[0]["source_id"]).values()


def test_every_item_still_locates_through_the_existing_locator_owner():
    for item in K.phase1_items():
        assert K.locator_problems(item) == [], item["packet_id"]


def test_a_moved_locator_refuses():
    """MUTATION: shifting the occurrence index must refuse."""
    item = copy.deepcopy(K.phase1_items()[0])
    item["occurrence_in_part"] = (item["occurrence_in_part"] or 1) + 99
    assert K.locator_problems(item)


# -------------------------------------------------- the frozen package build
def test_double_build_is_byte_identical(tmp_path):
    a = K.build_phase1(str(tmp_path / "a"))
    b = K.build_phase1(str(tmp_path / "b"))
    assert a["manifest_sha256"] == b["manifest_sha256"]
    assert K.package_problems(str(tmp_path / "a")) == []


def test_the_built_package_declares_the_exact_denominator_and_budget(tmp_path):
    man = K.build_phase1(str(tmp_path / "p"))
    live = json.load(io.open(INV.INV, encoding="utf-8"))
    assert man["calls"] == len(live["records"])
    assert man["budget"]["before"] == K.LEDGER_BEFORE
    assert man["budget"]["after"] == K.LEDGER_BEFORE + man["calls"]
    assert man["transport"]["model_alias"] == K.MODEL
    assert man["transport"]["runtime_model_id"] == K.RUNTIME_MODEL_ID
    assert man["transport"]["runtime_model_id"] != K.MODEL, \
        "the runtime id must be the proved one, not the launcher alias"
    assert man["transport"]["effort"] == K.EFFORT
    assert man["transport"]["agentType"] == K.AGENT_TYPE
    assert man["transport"]["disallowedTools"]
    assert man["budget"]["retry_cap"] == 1
    assert man["budget"]["abort_ceiling"] == K.LEDGER_BEFORE + 2 * man["calls"]


@pytest.mark.parametrize("what", ["drop_call", "swap_order", "alter_prompt"])
def test_a_mutated_package_is_refused(what, tmp_path):
    out = str(tmp_path / "p")
    man = K.build_phase1(out)
    doc = json.load(io.open(os.path.join(out, "phase1.manifest.json"),
                            encoding="utf-8"))
    if what == "drop_call":
        doc["items"].pop()
    elif what == "swap_order":
        doc["items"][0], doc["items"][1] = doc["items"][1], doc["items"][0]
    else:
        doc["items"][0]["prompt_sha256"] = "0" * 64
    io.open(os.path.join(out, "phase1.manifest.json"), "w",
            encoding="utf-8").write(json.dumps(doc, indent=1))
    assert K.package_problems(out), "the mutated package was accepted"
    assert man["calls"]


# --------------------------------------------------------- A3 stays untouched
def test_the_protected_a3_dependency_digest_has_not_moved():
    base = json.load(io.open(K.A3_BASELINE, encoding="utf-8"))
    now = K.a3_dependency_digest()
    assert now == base["digest"], "an A3 dependency byte moved"


def test_a3_still_reaudits_clean():
    assert K.a3_problems() == []


def test_the_menu_is_the_readable_reversible_one_not_a_python_dump():
    """The menu block must be the OWNER's display tokens, one per line, and
    every shown token must restore to its original through the same owner."""
    import a1_reader
    item = K.phase1_items()[0]
    shown = K.phase1_prompt(item).split(K.MENU_MARK, 1)[1].split(
        K.ITEM_MARK, 1)[0].strip()
    display, back = a1_reader.readable_menu(
        K.source_input(item["source_id"])["menu_tokens"])
    assert shown.splitlines() == display, "the menu is not the readable display"
    assert "{" not in shown and "[" not in shown, \
        "a python structure leaked into the menu block"
    for line in shown.splitlines():
        assert a1_reader.restore_menu_pick(line, back) in \
            K.source_input(item["source_id"])["menu_tokens"]


def test_the_retried_lane_ships_its_valid_answer_not_the_refused_one():
    """The A3 receipts own which answer is final. The one lane that was retried
    must ship the retry's answer; shipping the refused primary text would put a
    known-bad lead in front of the key owner."""
    run = io.open(os.path.join(K.EVIDENCE, "a3_serial_dir.txt"),
                  encoding="utf-8").read().strip()
    retry = json.load(io.open(os.path.join(run, "retry", "receipt.json"),
                              encoding="utf-8"))
    (packet, lane), = [tuple(k) for k in retry["allowed"]]
    raw_dir = os.path.join(run, "retry", "raw")
    want = io.open(os.path.join(raw_dir, sorted(os.listdir(raw_dir))[0]),
                   encoding="utf-8").read()
    item, = [i for i in K.phase1_items() if i["packet_id"] == packet]
    shipped, = [d["text"] for d in item["a3_drafts"] if d["lane_id"] == lane]
    assert shipped == want, "the refused primary answer was shipped"


# =================================================== the A4 phase-1 door ====
# Lawful controls first: a battery where everything refuses proves nothing.

def _envelope(item, settled_text, lanes=None, amb="[]", packet=None):
    """One A4 envelope as TEXT, so the drafter's exact numbers survive.

    `exact_match` is the DERIVED truth, computed the same way the owner does,
    so a lawful control stays lawful instead of smuggling in a mutation.
    """
    lanes = [d["lane_id"] for d in item["a3_drafts"]] if lanes is None else lanes
    settled = K.completed_draft(item, settled_text)
    rec = ", ".join(
        '{"lane_id": %s, "exact_match": %s, "why": "compared"}'
        % (json.dumps(l),
           "true" if (settled is not None and K.completed_draft(
               item, [d for d in item["a3_drafts"]
                      if d["lane_id"] == l][0]["text"]) == settled)
           else "false")
        for l in lanes)
    return ('{"packet_id": %s, "settled": %s, "reconciliation": [%s], '
            '"ambiguities": %s}'
            % (json.dumps(packet or item["packet_id"]), settled_text, rec, amb))


def _draft_body(item, lane=0):
    """A real A3 four-field reply, verbatim, fences removed."""
    t = item["a3_drafts"][lane]["text"]
    return t.split("```json", 1)[1].rsplit("```", 1)[0] if "```json" in t else t


def _first_with(n_facts):
    for item in K.phase1_items():
        for lane in (0, 1):
            try:
                body = json.loads(_draft_body(item, lane))
            except Exception:
                continue
            if len(body.get("facts") or []) == n_facts:
                return item, _draft_body(item, lane)
    return None, None


def test_a_lawful_fact_reply_is_accepted_whole():
    item, body = _first_with(1)
    ok, bad = K.read_reply(_envelope(item, body), item)
    assert ok is not None, bad[:3]
    assert ok["settled"]["facts"] and not ok["settled"]["abstentions"]


def test_a_lawful_abstention_is_accepted_and_carries_the_no_fact_reason():
    item = K.phase1_items()[0]
    body = ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "the '
            'scale marker sits outside the quote"}], "continuity_hints": []}'
            % json.dumps(item["source_id"]))
    ok, bad = K.read_reply(_envelope(item, body), item)
    assert ok is not None, bad[:3]
    assert ok["settled"]["abstentions"][0]["reason"]


def test_a_lawful_multirow_sibling_reply_is_accepted():
    item, body = _first_with(2)
    if item is None:
        pytest.skip("no two-row draft in the frozen evidence")
    ok, bad = K.read_reply(_envelope(item, body), item)
    assert ok is not None, bad[:3]
    assert len(ok["settled"]["facts"]) == 2


def test_a_lawful_ambiguity_is_recorded_separately():
    item = K.phase1_items()[0]
    body = ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "r"}], '
            '"continuity_hints": []}' % json.dumps(item["source_id"]))
    amb = '[{"what": "period", "why": "two readings are equally supported"}]'
    ok, bad = K.read_reply(_envelope(item, body, amb=amb), item)
    assert ok is not None, bad[:3]
    assert ok["ambiguities"] and ok["settled"]["continuity_hints"] == []


def test_a_malformed_continuity_hint_refuses():
    """The reader owns the continuity shape; a bare string is not one."""
    item = K.phase1_items()[0]
    body = ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "r"}], '
            '"continuity_hints": ["not an object"]}'
            % json.dumps(item["source_id"]))
    ok, bad = K.read_reply(_envelope(item, body), item)
    assert ok is None and bad


def test_a_displayed_menu_pick_is_restored_by_the_reader():
    """The readable menu is reversible: a shown token comes back as its own."""
    import a1_reader
    for item in K.phase1_items():
        src = K.source_input(item["source_id"])
        display, back = a1_reader.readable_menu(src["menu_tokens"])
        picks = [d for d in display if back[d] != d]
        if not picks:
            continue
        assert a1_reader.restore_menu_pick(picks[0], back) in src["menu_tokens"]
        return
    pytest.skip("no decoded menu token in the frozen evidence")


@pytest.mark.parametrize("what", [
    "missing_key", "extra_key", "wrong_packet", "settled_not_object",
    "settled_extra_key", "bad_fact_type", "bad_slot", "one_lane",
    "wrong_lane", "match_not_bool", "blank_why", "bad_ambiguity"])
def test_every_malformed_reply_refuses_whole(what):
    item, body = _first_with(1)
    lanes = [d["lane_id"] for d in item["a3_drafts"]]
    text = _envelope(item, body)
    obj = json.loads(text)
    if what == "missing_key":
        obj.pop("ambiguities")
    elif what == "extra_key":
        obj["extra"] = 1
    elif what == "wrong_packet":
        obj["packet_id"] = "not-this-packet"
    elif what == "settled_not_object":
        obj["settled"] = []
    elif what == "settled_extra_key":
        obj["settled"]["surprise"] = 1
    elif what == "bad_fact_type":
        obj["settled"]["facts"][0]["fact_type"] = "not_a_fact_type"
    elif what == "bad_slot":
        for f in obj["settled"]["facts"]:
            for k, v in list(f["item"].items()):
                if isinstance(v, dict) and "scale_multiplier" in v:
                    v.pop("scale_multiplier")
    elif what == "one_lane":
        obj["reconciliation"] = obj["reconciliation"][:1]
    elif what == "wrong_lane":
        obj["reconciliation"][0]["lane_id"] = "someone/else"
    elif what == "match_not_bool":
        obj["reconciliation"][0]["exact_match"] = "no"
    elif what == "blank_why":
        obj["reconciliation"][0]["why"] = "   "
    else:
        obj["ambiguities"] = [{"what": "only"}]
    ok, bad = K.read_reply(json.dumps(obj), item)
    assert ok is None and bad, "%s was accepted" % what
    assert lanes


def test_a_semantically_different_but_lawful_reply_is_still_accepted():
    """Semantics are the key owner's to decide: a lawful reply that disagrees
    with both drafts is accepted, and earns no retry."""
    item = K.phase1_items()[0]
    body = ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "I read '
            'this differently from both drafts"}], "continuity_hints": []}'
            % json.dumps(item["source_id"]))
    ok, bad = K.read_reply(_envelope(item, body), item)
    assert ok is not None, bad[:3]


# ------------------------------------------- A3 evidence drift must refuse --
def test_a3_evidence_is_taken_only_from_the_auditor(monkeypatch):
    """MUTATION Codex proved: swapped answer bytes must not become evidence."""
    import audit_worker_access as AUD
    real = AUD.audit

    def swapped(path, *a, **k):
        out = real(path, *a, **k)
        if out["answers"]:
            key = sorted(out["answers"])[0]
            out["answers"] = dict(out["answers"])
            out["answers"].pop(key)
        return out

    monkeypatch.setattr(AUD, "audit", swapped)
    assert K.a3_evidence()["problems"], "a missing proved answer was accepted"


def test_a3_evidence_refuses_when_the_auditor_refuses(monkeypatch):
    import audit_worker_access as AUD
    real = AUD.audit
    monkeypatch.setattr(AUD, "audit",
                        lambda p, *a, **k: dict(real(p, *a, **k),
                                                problems=["forced"]))
    assert K.a3_evidence()["problems"]


def test_phase1_refuses_to_build_on_unproved_a3(monkeypatch):
    monkeypatch.setattr(K, "a3_evidence",
                        lambda: {"answers": {}, "problems": ["forced"],
                                 "binding": {}})
    with pytest.raises(RuntimeError):
        K.phase1_items()


# --------------------------------------------- official state proof (real) --
def _retry_state():
    run, retry = K.a3_run_dirs()
    rec = json.load(io.open(os.path.join(retry, "receipt.json"),
                            encoding="utf-8"))
    return rec["states"][0]


def _proved_prompt(state_path):
    """The exact first user prompt, read from the proved transcript itself."""
    import audit_worker_access as AUD
    doc = json.load(io.open(state_path, encoding="utf-8"))
    row = [r for r in doc["workflowProgress"]
           if r.get("type") == "workflow_agent"][0]
    session_dir, _sid = AUD._official_location(state_path)
    tp = os.path.join(session_dir, "subagents", "workflows",
                      os.path.splitext(os.path.basename(state_path))[0],
                      "agent-%s.jsonl" % row["agentId"])
    for r in AUD._jsonl(tp):
        if r.get("type") == "user":
            return r["message"]["content"]
    raise AssertionError("no user turn")


def test_a_real_official_state_is_proved_and_returns_its_answer():
    """LAWFUL CONTROL for the evidence core, on real official bytes."""
    state = _retry_state()
    text, bad = K.official_answer(state, _proved_prompt(state))
    assert bad == [], bad[:3]
    assert isinstance(text, str) and text.strip()


def test_a_changed_prompt_refuses_the_state():
    state = _retry_state()
    _text, bad = K.official_answer(state, _proved_prompt(state) + " x")
    assert bad


@pytest.mark.parametrize("what", ["tool_use", "effort", "model"])
def test_transcript_drift_refuses(monkeypatch, what):
    import audit_worker_access as AUD
    state = _retry_state()
    prompt = _proved_prompt(state)
    real = AUD._jsonl

    def drifted(path):
        recs = real(path)
        for r in recs:
            if r.get("type") != "assistant":
                continue
            if what == "effort":
                r["effort"] = "low"
            elif what == "model":
                r["message"]["model"] = "claude-opus-5"
            else:
                (r["message"].setdefault("content", [])
                 .append({"type": "tool_use", "name": "Read", "input": {}}))
            break
        return recs

    monkeypatch.setattr(AUD, "_jsonl", drifted)
    _text, bad = K.official_answer(state, prompt)
    assert bad, "%s drift was accepted" % what


# ------------------------------------------------------- run bookkeeping ----
def test_the_caller_cannot_choose_the_attempt_or_the_subset():
    """prepare_run takes ONE argument. A narrowed primary, an orphan retry, a
    duplicate key and an all-key retry are no longer expressible."""
    import inspect
    assert list(inspect.signature(K.prepare_run).parameters) == ["run_dir"]


def test_a_run_directory_must_be_fresh(tmp_path):
    d = tmp_path / "used"
    d.mkdir()
    (d / "stray.json").write_text("{}")
    assert K.prepare_run(str(d))["ok"] is False


def test_the_lawful_route_accounts_for_every_item_exactly(tmp_path):
    out = K.prepare_run(str(tmp_path / "full"))
    assert out["ok"] is True, out["problems"][:3]
    items = K.phase1_items()
    assert len(out["invocations"]) == len(items)
    assert [i["packet_id"] for i in out["invocations"]] == \
        [i["packet_id"] for i in items]
    receipt = json.load(io.open(str(tmp_path / "full" / "receipt.json"),
                                encoding="utf-8"))
    assert receipt["allowed"] == [i["packet_id"] for i in items]
    assert len(set(receipt["allowed"])) == len(receipt["allowed"])


def test_the_primary_receipt_must_be_the_whole_canonical_set(tmp_path):
    """MUTATION: a narrowed or duplicated primary refuses at finalization."""
    out = str(tmp_path / "narrow")
    K.prepare_run(out)
    path = os.path.join(out, "receipt.json")
    rec = json.load(io.open(path, encoding="utf-8"))
    rec["allowed"] = rec["allowed"][:1]
    io.open(path, "w", encoding="utf-8").write(json.dumps(rec))
    doc = K.finalize(out)
    # behaviour, not prose: it refuses, credits nothing and offers no retry
    assert doc["problems"] and doc["ledger"]["valid"] == 0
    assert doc["retry"] == [] and doc["primary_complete"] is False

    out2 = str(tmp_path / "dup")
    K.prepare_run(out2)
    path2 = os.path.join(out2, "receipt.json")
    rec2 = json.load(io.open(path2, encoding="utf-8"))
    rec2["allowed"] = [rec2["allowed"][0]] * 2
    io.open(path2, "w", encoding="utf-8").write(json.dumps(rec2))
    doc2 = K.finalize(out2)
    assert doc2["problems"] and doc2["ledger"]["valid"] == 0
    assert doc2["retry"] == []


def test_a_finalized_run_with_no_states_credits_nothing(tmp_path):
    out = str(tmp_path / "empty")
    K.prepare_run(out)
    doc = K.finalize(out)
    assert doc["ledger"]["valid"] == 0
    assert doc["ledger"]["missing"] == doc["ledger"]["scheduled"]
    assert doc["retry"] == []


def test_no_launcher_script_is_at_or_over_the_transport_limit():
    pf = K.preflight()
    assert pf["problems"] == [], pf["problems"][:3]
    assert pf["calls"] == len(json.load(io.open(INV.INV,
                                                encoding="utf-8"))["records"])


def test_an_oversized_script_refuses_before_any_call(monkeypatch):
    monkeypatch.setattr(K, "render_launcher",
                        lambda i, attempt=1: "x" * K.TRANSPORT_LIMIT)
    assert any("transport limit" in p for p in K.preflight()["problems"])


# ============================== SEQ 1362: the three reopened boundaries ====
# 1. exact_match is DERIVED, never trusted.

def test_exact_match_true_is_accepted_when_the_draft_really_matches():
    """LAWFUL CONTROL: settled == that draft, and the row says true."""
    item, body = _first_with(1)
    lanes = [d["lane_id"] for d in item["a3_drafts"]]
    rec = ('{"lane_id": %s, "exact_match": true, "why": "identical"}, '
           '{"lane_id": %s, "exact_match": %s, "why": "compared"}'
           % (json.dumps(lanes[0]), json.dumps(lanes[1]),
              "true" if K.completed_draft(item, item["a3_drafts"][1]["text"])
              == K.completed_draft(item, item["a3_drafts"][0]["text"])
              else "false"))
    text = ('{"packet_id": %s, "settled": %s, "reconciliation": [%s], '
            '"ambiguities": []}' % (json.dumps(item["packet_id"]), body, rec))
    ok, bad = K.read_reply(text, item)
    assert ok is not None, bad[:3]


def test_same_but_false_is_refused():
    """MUTATION Codex proved: the draft IS the settled reply, row says false."""
    item, body = _first_with(1)
    lanes = [d["lane_id"] for d in item["a3_drafts"]]
    rec = ", ".join('{"lane_id": %s, "exact_match": false, "why": "claimed '
                    'different"}' % json.dumps(l) for l in lanes)
    text = ('{"packet_id": %s, "settled": %s, "reconciliation": [%s], '
            '"ambiguities": []}' % (json.dumps(item["packet_id"]), body, rec))
    ok, bad = K.read_reply(text, item)
    assert ok is None and any("exact_match" in b for b in bad), bad[:3]


def test_different_but_true_is_refused():
    """MUTATION the other way: settled differs from both drafts, row says true."""
    item = K.phase1_items()[0]
    body = ('{"source_id": %s, "facts": [], "abstentions": [{"reason": "I read '
            'this differently"}], "continuity_hints": []}'
            % json.dumps(item["source_id"]))
    lanes = [d["lane_id"] for d in item["a3_drafts"]]
    rec = ", ".join('{"lane_id": %s, "exact_match": true, "why": "claimed '
                    'identical"}' % json.dumps(l) for l in lanes)
    text = ('{"packet_id": %s, "settled": %s, "reconciliation": [%s], '
            '"ambiguities": []}' % (json.dumps(item["packet_id"]), body, rec))
    ok, bad = K.read_reply(text, item)
    assert ok is None and any("exact_match" in b for b in bad), bad[:3]


def test_an_unreadable_draft_can_only_be_false():
    item, body = _first_with(1)
    assert K.completed_draft(item, "not json at all") is None


# 2. the primary and the child are the owner's, not the caller's.

def _fake_state(path, run_id, label, text, official=True):
    """An official-state-SHAPED object. Only refusal paths use it."""
    # the REAL one-agent shape: the returned value sits directly on `.result`
    # and the row is state "done" (Codex SEQ 1364 item 1)
    doc = {"runId": run_id, "status": "completed", "totalToolCalls": 0,
           "workflowProgress": [{"type": "workflow_agent", "state": "done",
                                 "label": label,
                                 "agentId": "a" + run_id, "model":
                                 K.RUNTIME_MODEL_ID, "agentType":
                                 K.AGENT_TYPE, "toolCalls": 0}],
           "result": {"packet_id": label, "source_id": label.split("#")[0],
                      "attempt": 1, "model": K.MODEL, "effort": K.EFFORT,
                      "agentType": K.AGENT_TYPE, "text": text}}
    io.open(path, "w", encoding="utf-8").write(json.dumps(doc))
    return path


def test_a_partial_primary_earns_no_retry_for_unattempted_work(tmp_path):
    out = str(tmp_path / "partial")
    K.prepare_run(out)
    doc = K.finalize(out)
    assert doc["ledger"]["missing"] == doc["ledger"]["scheduled"]
    assert doc["retry"] == []
    assert not os.path.isdir(os.path.join(out, "retry"))


def test_an_orphan_child_refuses(tmp_path):
    """MUTATION: a child with no finalized parent."""
    child = str(tmp_path / "lonely" / "retry")
    K._write_receipt(child, 2, [K.canonical_keys()[0]],
                     parent={"run_id": "x", "finalization_sha256": "0" * 64})
    assert any("orphan" in p for p in K.finalize(child)["problems"])


def test_a_third_attempt_refuses(tmp_path):
    d = str(tmp_path / "third")
    K._write_receipt(d, 3, K.canonical_keys()[:1])
    assert any("outside 1..2" in p for p in K.finalize(d)["problems"])


def test_record_state_refuses_a_duplicate_and_a_missing_state(tmp_path):
    out = str(tmp_path / "rec")
    K.prepare_run(out)
    keys = K.canonical_keys()
    state = _fake_state(str(tmp_path / "s4.json"), "s4", keys[0], "x")
    assert K.record_state(out, state) == []
    assert K.record_state(out, state)          # duplicate
    assert K.record_state(out, str(tmp_path / "nope.json"))


# 3. every readable raw is preserved before any proof.

def _raws(run_dir):
    d = os.path.join(run_dir, "raw")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def test_a_readable_raw_is_preserved_even_when_the_proof_refuses(tmp_path):
    """MUTATION Codex proved: a bad official location cost the paid bytes."""
    out = str(tmp_path / "harvest")
    K.prepare_run(out)
    keys = K.canonical_keys()
    state = _fake_state(str(tmp_path / "h1.json"), "h1", keys[0],
                        "PAID RAW SENTINEL")
    K.record_state(out, state)
    doc = K.finalize(out)
    saved = _raws(out)
    assert saved, "the paid raw was lost"
    body = io.open(os.path.join(out, "raw", saved[0]), encoding="utf-8").read()
    assert body == "PAID RAW SENTINEL"
    assert doc["ledger"]["valid"] == 0        # zero credit
    assert doc["retry"] == []                 # and zero retry


@pytest.mark.parametrize("what", ["bad_label", "corrupt_state", "duplicate"])
def test_raw_survives_every_proof_failure(tmp_path, what):
    out = str(tmp_path / ("keep_" + what))
    K.prepare_run(out)
    keys = K.canonical_keys()
    p1 = _fake_state(str(tmp_path / (what + "1.json")), what + "1",
                     keys[0] if what != "bad_label" else "not-a-packet",
                     "SENTINEL ONE")
    K.record_state(out, p1)
    if what == "corrupt_state":
        io.open(p1, "w", encoding="utf-8").write("{ this is not json")
    if what == "duplicate":
        p2 = _fake_state(str(tmp_path / (what + "2.json")), what + "2",
                         keys[0], "SENTINEL TWO")
        K.record_state(out, p2)
    doc = K.finalize(out)
    if what == "corrupt_state":
        assert _raws(out) == []               # nothing readable existed
    else:
        bodies = [io.open(os.path.join(out, "raw", f), encoding="utf-8").read()
                  for f in _raws(out)]
        assert "SENTINEL ONE" in bodies
        if what == "duplicate":
            assert "SENTINEL TWO" in bodies, "the duplicate's paid bytes were lost"
    assert doc["ledger"]["valid"] == 0
    assert doc["retry"] == []

# NOTE (Codex SEQ 1363): three tests here asserted the SUPERSEDED
# behaviour in which a PARTIAL primary could publish a child. They are
# removed rather than repaired, because test_kfields_key_1363.py now
# proves the same ground at full 196 scale under the completeness gate:
#   a complete primary with one invalid -> exactly one runnable child
#   a forged parent hash -> zero valid credit
#   every immutable receipt field, including parent and allowed
