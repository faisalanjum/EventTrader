# -*- coding: utf-8 -*-
"""THE ONE-EVENT THIRD CORRECTION PRE-CALL (Codex SEQ 1507 items 1-8). Zero calls.

Run 1506 is bound ONCE and counted (5215 -> 5217); 0000940944-26-000009 is the
accepted second-round settlement. The common correction prefix now serves the
locked A4 owner's exact ten-line final-decision block, sourced from its owning
artifact, once, above the boundary, hash-bound in the package. The third
round's population is derived from the open issues the accepted key still
carries after run 1506; run 1506's raw reply is its sole lead. Composition
proofs use a reader-lawful DEVICE for the one reply that does not exist yet.
Lawful controls first, then every refusal.
"""
import collections
import copy
import hashlib
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as A6                                    # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402

RUN1 = "/tmp/a4_final_targeted_corr_run_1504"
RUN2 = "/tmp/a4_final_targeted_corr2_run_1506"
CORR3 = getattr(FT, "CORR3_DOOR", "a4_final_targeted_correction_3")
BLOCK = "[FINAL DECISION RULES]\n%s\n\n" % F._decision_rules_source().rstrip()
_pkg = pytest.mark.skipif(not os.path.isdir(getattr(FT, "CORR3_PKG_DIR", "/nonexistent")),
                          reason="the third correction package is absent")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)


def _dump(p, doc):
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1, ensure_ascii=False))


@pytest.fixture(scope="module")
def corr2():
    return FT.bound_shards(FT.CORR2_DOOR)


@pytest.fixture(scope="module")
def tasks():
    return FT.correction_tasks(CORR3)


# ------------------------------------------ item 6 (red): the block is served
def test_the_correction_prefix_serves_the_exact_decision_block_once_above_the_boundary():
    text = FT.correction_prefix()
    assert text.count(BLOCK) == 1                                    # the owner's bytes, verbatim, once
    assert text.find(BLOCK) < text.find("[BOUNDARY]\n")
    assert text.find("[RULES]\n") < text.find(BLOCK)                 # existing rules first
    heads = [l for l in text[:text.find("[BOUNDARY]\n")].splitlines() if l.startswith("[") and l.endswith("]")]
    assert heads == list(FT.CORR_PREFIX_MARKS) and "[FINAL DECISION RULES]" in heads
    assert FT._decision_rules_source() == K._read(os.path.join(F._HERE, F.DECISION_RULES_NAME))
    assert len(F._decision_rules_source().rstrip().splitlines()) == 10


def test_a_byte_mutation_of_the_block_refuses(tmp_path, monkeypatch):
    live = FT.correction_prefix()
    mutated = str(tmp_path / F.DECISION_RULES_NAME)
    io.open(mutated, "w", encoding="utf-8").write(F._decision_rules_source().replace("ambiguous_menus", "ambiguous_menu", 1))
    real = F._decision_rules_source
    monkeypatch.setattr(F, "_decision_rules_source", lambda: K._read(mutated))
    assert FT.correction_prefix() != live and BLOCK not in FT.correction_prefix()
    assert any("decision" in b or "prefix" in b for b in FT.correction_package_problems(FT.CORR3_PKG_DIR, CORR3)) \
        if os.path.isdir(getattr(FT, "CORR3_PKG_DIR", "/nonexistent")) else True
    monkeypatch.setattr(F, "_decision_rules_source", real)
    assert FT.correction_prefix() == live


# ---------------------------------------- item 1: run 1506 bound and counted
def test_run_1506_is_bound_once_and_counted_by_its_own_owner():
    binding = _load(FT._phase(FT.CORR2_DOOR)["binding"])
    rec, fin = _load(os.path.join(RUN2, K.RECEIPT_NAME)), _load(os.path.join(RUN2, K.FINALIZATION_NAME))
    assert binding["run_dir"] == RUN2 and binding["package"]["dir"] == FT.CORR2_PKG_DIR
    assert binding["package"]["manifest_sha256"] == rec["manifest_sha256"] == _sha(os.path.join(FT.CORR2_PKG_DIR, FT.CORR_MANIFEST_NAME))
    rows = FT.proved_spend(RUN2, FT.CORR2_DOOR)
    assert len(rows) == 1 and rows[0]["calls"] == fin["ledger"]["scheduled"] == 2
    assert rows[0]["receipt_sha256"] == _sha(os.path.join(RUN2, K.RECEIPT_NAME)) and rows[0]["raw_tree"] == F.raw_tree(RUN2)["sha256"]
    total, ledger = A6.ledger()
    mine = [r for r in ledger if r.get("run_dir") == RUN2]
    assert len(mine) == 1 and mine[0]["stage"] == "final_targeted_correction_2_primary" and mine[0]["calls"] == 2
    assert [r["stage"] for r in ledger if r.get("run_dir") in (RUN1, RUN2)] == ["final_targeted_correction_primary", "final_targeted_correction_2_primary"]
    assert total == sum(r["calls"] for r in ledger) == _load(FT.CORR2_BUDGET_RECEIPT)["completed_before"] + fin["ledger"]["scheduled"]


def test_the_accepted_key_after_run_1506_keeps_seven_settlements_and_one_open_issue(corr2):
    shards, raws = corr2
    assert [s for s in shards if shards[s]["open_issues"]] == [s for s in shards if shards[s]["open_issues"]] and len(shards) == 2
    out, oraws, origins, bad = FT.successor_shards(RUN1, RUN2)
    assert bad == [] and len(out) == 8
    left = [s for s in out if out[s]["open_issues"]]
    assert len(left) == 1 and sum(len(out[s]["open_issues"]) for s in out) == 1
    for sid in shards:
        assert origins[sid] == "final_targeted_correction_2" and oraws[sid] == raws[sid]
    assert FT.preservation_problems(RUN1, RUN2) == [] and FT.full_preservation_problems(RUN1, RUN2) == []
    counts = FT.full_counts(RUN1, RUN2)
    assert (counts["events"], counts["unique_rows"], counts["replaced"]) == (36, 196, 11)
    key, sidecar, problems = FT.full_materialize(RUN1, RUN2)
    assert problems == [] and len(sidecar["open_issues"]) == 1 and sidecar["open_issues"][0]["source_id"] == left[0]


# ------------------------------- item 3: the population, derived, never listed
def test_the_third_population_is_exactly_the_open_issue_events_after_run_1506(tasks):
    out, _r, _o, _b = FT.successor_shards(RUN1, RUN2)
    want = [s for s in out if out[s]["open_issues"]]
    assert FT.correction_events(CORR3) == want and len(want) == 1
    assert [t["source_id"] for t in tasks] == want
    src = io.open(FT.__file__, encoding="utf-8").read()
    assert want[0] not in src and "0000940944-26-000009" not in src
    assert FT.CORRECTION_DOORS == (FT.CORR_DOOR, FT.CORR2_DOOR, CORR3)


@pytest.mark.parametrize("how", ["drop_event", "extra_event", "reworded_issue", "finding_without_rule", "unbound"])
def test_a_receipt_that_does_not_cover_exactly_the_open_issue_event_refuses(how, tmp_path, monkeypatch):
    doc = _load(FT.CORR3_REVIEW_RECEIPT)
    out, _r, _o, _b = FT.successor_shards(RUN1, RUN2)
    pop = [s for s in out if out[s]["open_issues"]]
    clean = [s for s in out if not out[s]["open_issues"]][0]
    if how == "drop_event":
        del doc["findings"][pop[0]]
    elif how == "extra_event":
        doc["findings"][clean] = [collections.OrderedDict([("kind", "reviewer_finding"), ("source", "device"), ("text", "device"), ("rules", ["Rule 6"])])]
    elif how == "reworded_issue":
        [x for x in doc["findings"][pop[0]] if x["kind"] == "open_issue"][0]["what"] += " (reworded)"
    elif how == "finding_without_rule":
        [x for x in doc["findings"][pop[0]] if x["kind"] == "reviewer_finding"][0]["rules"] = []
    else:
        doc[FT._round(CORR3)["receipt_key"]]["binding_sha256"] = "0" * 64
    p = str(tmp_path / "receipt.json"); _dump(p, doc)
    monkeypatch.setattr(FT, "CORR3_REVIEW_RECEIPT", p)
    with pytest.raises(ValueError):
        FT.correction_events(CORR3)


# --------------------------------- items 4-5: the prompt, the lead, the context
@_pkg
def test_the_prompt_carries_the_1506_reply_as_the_sole_lead_and_the_findings_last(tasks, corr2):
    shards, raws = corr2
    man = _load(os.path.join(FT.CORR3_PKG_DIR, FT.CORR_MANIFEST_NAME))
    receipt = _load(FT.CORR3_REVIEW_RECEIPT)
    prefix = FT.correction_prefix()
    assert K._sha(prefix) == man["prefix_sha256"] and man["decision_rules_sha256"] == K._sha(F._decision_rules_source())
    assert man["derived_from"]["decision_rules"]["sha256"] == _sha(os.path.join(F._HERE, F.DECISION_RULES_NAME))
    pinned2 = _load(os.path.join(FT.CORR2_PKG_DIR, FT.CORR_MANIFEST_NAME))
    assert prefix == K._read(os.path.join(FT.CORR2_PKG_DIR, FT.CORR_PREFIX_NAME)).replace("[A4 CORRECTION TASK]\n", BLOCK + "[A4 CORRECTION TASK]\n", 1)
    for fld in ("semantic_rules_sha256", "correction_task_sha256", "role_sha256", "task_section_sha256", "boundary_sha256", "injection_control_sha256"):
        assert man[fld] == pinned2[fld], fld                          # the prefix moved by exactly the block
    assert len(tasks) == 1 and man["call_order"] == [tasks[0]["source_id"]]
    t = tasks[0]; sid = t["source_id"]
    text = FT.correction_prompt(t, door=CORR3)
    assert text.startswith(prefix)
    body = json.loads(text[len(prefix):], object_pairs_hook=collections.OrderedDict)
    assert list(body) == list(FT.CORR_PAYLOAD_KEYS) and list(body)[-1] == "reviewer_findings"
    assert [dict(l) for l in body["leads"]] == [{"lead_id": "correction_2/%s" % sid, "origin": "final_targeted_correction_2",
                                                 "sha256": K._sha(raws[sid]), "reply": raws[sid]}]
    assert raws[sid] == io.open(os.path.join(RUN2, "raw", "%s.attempt1.proved.json" % sid), encoding="utf-8").read()
    assert body["reviewer_findings"] == receipt["findings"][sid]
    issues = [collections.OrderedDict([("what", f["what"]), ("why", f["why"])]) for f in body["reviewer_findings"] if f["kind"] == "open_issue"]
    assert issues == [collections.OrderedDict([("what", x["what"]), ("why", x["why"])]) for x in shards[sid]["open_issues"]]
    rulings = [f for f in body["reviewer_findings"] if f["kind"] == "reviewer_finding"]
    assert len(rulings) == 4 and all(f["rules"] and f["text"].strip() for f in rulings)
    assert text.count(json.dumps(raws[sid])) == 1
    boundary = FT.HR._boundary_at(FT.SUFFIX)
    head = text[:text.find(boundary)]
    for f in rulings:
        assert f["text"][:40] not in head                              # review context, never a rule
    assert FT.prompt_order_problems(CORR3) == []


@_pkg
def test_the_third_package_builds_twice_byte_identical_within_capacity_and_budget(tmp_path):
    a, b = str(tmp_path / "a"), str(tmp_path / "b")
    FT.build_correction(a, CORR3); FT.build_correction(b, CORR3)
    for n in sorted(os.listdir(FT.CORR3_PKG_DIR)):
        assert _sha(os.path.join(a, n)) == _sha(os.path.join(b, n)) == _sha(os.path.join(FT.CORR3_PKG_DIR, n)), n
    man = _load(os.path.join(FT.CORR3_PKG_DIR, FT.CORR_MANIFEST_NAME))
    assert man["door"] == CORR3 and man["authority"] == "Codex SEQ 1507" and man["counts"]["primary_calls"] == 1
    assert man["derived_from"]["final_targeted_owner_sha256"] == _sha(FT.__file__)
    lead = man["derived_from"][FT._round(CORR3)["receipt_key"]]
    assert lead["binding_path"] == FT._phase(FT.CORR2_DOOR)["binding"] and lead["run_dir"] == RUN2
    assert man["capacity"]["at_or_over_transport_limit"] == [] and man["capacity"]["largest_script_bytes"] < man["capacity"]["transport_limit_bytes"] == 524288
    receipt = _load(FT.CORR3_BUDGET_RECEIPT); b = man["budget"]
    before = receipt["completed_before"]
    assert before == A6.ledger()[0] == _load(FT.CORR2_BUDGET_RECEIPT)["completed_before"] + 2
    assert (b["before"], b["primaries"], b["after_primaries"], b["worst_case_after"]) == (before, 1, before + 1, before + FT.MAX_ATTEMPTS)
    assert (b["a4_closeout_clean"], b["a4_closeout_worst"]) == (before + 2, before + 2 * FT.MAX_ATTEMPTS) and b["a4_closeout_worst"] <= receipt["ceiling"]
    assert FT.correction_package_problems(FT.CORR3_PKG_DIR, CORR3) == []
    assert FT.correction_preflight(FT.CORR3_PKG_DIR, CORR3)["ok"] is True
    out = str(tmp_path / "run"); got = FT.prepare_correction_run(out, CORR3)
    assert got["ok"] and [i["label"] for i in got["invocations"]] == man["call_order"]
    assert sorted(os.listdir(out)) == [K.RECEIPT_NAME, "scripts"]


# --------------------------------- item 6: composition with a lawful device
def _device_text(text, sid):
    """A reader-lawful DEVICE for the one future reply: the run-1504 settlement
    of this event (facts with aligned review rows) with no open issue, its
    one lead reconciled. A shape for the mechanics, never evidence."""
    body = text.strip(); body = body[body.find("{"):body.rfind("}") + 1]
    obj = json.loads(body, object_pairs_hook=collections.OrderedDict)
    obj["open_issues"] = []
    obj["lead_reconciliation"] = [collections.OrderedDict([("lead_id", "correction_2/%s" % sid), ("agrees", False), ("why", "device")])]
    return "```json\n%s\n```" % json.dumps(obj, indent=2, ensure_ascii=False)


@pytest.fixture(scope="module")
def device(tasks):
    t = tasks[0]; sid = t["source_id"]
    text = _device_text(io.open(os.path.join(RUN1, "raw", "%s.attempt1.proved.json" % sid), encoding="utf-8").read(), sid)
    obj, why = FT.read_shard(text, t, FT.correction_leads(t, door=CORR3))
    assert why == [], why
    return collections.OrderedDict([(sid, obj)]), collections.OrderedDict([(sid, text)])


def _patched(monkeypatch, repl, rraws):
    real = FT.accepted_shards
    bound = {os.path.abspath(FT._closed_run(d)) for d in (FT.DOOR, FT.CORR_DOOR, FT.CORR2_DOOR)}
    monkeypatch.setattr(FT, "accepted_shards", lambda run: real(run) if os.path.abspath(run) in bound else (repl, rraws, []))
    return "/tmp/any_third_correction_run"


def test_the_lawful_device_replaces_only_the_one_and_clears_every_open_issue(tasks, device, corr2, monkeypatch):
    repl, rraws = device
    sid = tasks[0]["source_id"]
    dev = _patched(monkeypatch, repl, rraws)
    out, oraws, origins, bad = FT.successor_shards(RUN1, RUN2, dev)
    assert bad == [] and origins[sid] == "final_targeted_correction_3" and oraws[sid] == rraws[sid]
    shards2, raws2 = corr2
    before, braws, borig, _ = FT.successor_shards(RUN1, RUN2)
    for s in out:
        if s != sid:
            assert out[s] == before[s] and oraws[s] == braws[s] and origins[s] == borig[s]   # seven settlements byte-identical
    assert FT.preservation_problems(RUN1, RUN2, dev) == []
    counts = FT.full_counts(RUN1, RUN2, dev)
    assert (counts["events"], counts["rows"], counts["unique_rows"], counts["replaced"], counts["preserved"]) == (36, 196, 196, 11, 185)
    assert FT.full_preservation_problems(RUN1, RUN2, dev) == []
    key, sidecar, problems = FT.full_materialize(RUN1, RUN2, dev)
    assert problems == [] and len(sidecar["open_issues"]) == 0


@pytest.mark.parametrize("how", ["issue_retained", "second_target", "target_omitted"])
def test_every_refusal_fails_closed_after_a_lawful_control(how, tasks, device, monkeypatch):
    repl, rraws = device
    sid = tasks[0]["source_id"]
    dev = _patched(monkeypatch, repl, rraws)
    assert FT.successor_shards(RUN1, RUN2, dev)[3] == []              # the lawful control, first
    monkeypatch.undo()
    out, _r, _o, _b = FT.successor_shards(RUN1, RUN2)
    other = [s for s in out if s != sid][0]
    if how == "issue_retained":
        r2 = copy.deepcopy(repl); r2[sid]["open_issues"] = [collections.OrderedDict([("what", "device"), ("why", "device")])]
        dev = _patched(monkeypatch, r2, rraws)
        _k, sidecar, problems = FT.full_materialize(RUN1, RUN2, dev)
        assert problems == [] and len(sidecar["open_issues"]) == 1     # the signer's stop, counted
    elif how == "second_target":
        r2, w2 = copy.deepcopy(repl), collections.OrderedDict(rraws)
        r2[other], w2[other] = copy.deepcopy(out[other]), "device"
        dev = _patched(monkeypatch, r2, w2)
        assert any("outside the derived population" in b for b in FT.successor_shards(RUN1, RUN2, dev)[3])
    else:
        dev = _patched(monkeypatch, collections.OrderedDict(), collections.OrderedDict())
        assert any("no accepted correction" in b for b in FT.successor_shards(RUN1, RUN2, dev)[3])
