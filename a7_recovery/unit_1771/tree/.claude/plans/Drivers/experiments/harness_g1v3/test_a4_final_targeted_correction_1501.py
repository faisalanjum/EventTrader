# -*- coding: utf-8 -*-
"""THE SUCCESSOR CORRECTION FREEZE (Codex SEQ 1501 items 2-7). Zero model calls.

The population derives from ONE bound review receipt (the primary shards' own
open issues verbatim plus the reviewer's findings) - five events / eight rows.
Every prompt: the byte-identical v3 rules first, the complete event, the
affected rows, the exact primary settlement as an untrusted lead, the
findings LAST. The three clean events are preserved byte for byte and the
locked A4 history still holds. Lawful controls first, then every mutation
Codex named.
"""
import collections
import copy
import hashlib
import io
import json
import os
import re
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as A6                                    # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_key as K                                    # noqa: E402

C = K.C
_pkg = pytest.mark.skipif(not os.path.isdir(FT.CORR_PKG_DIR), reason="the correction package is absent")
LIVE = FT.CORRECTION_DOORS[-1]                      # the round whose gates are live now
LIVE_PKG = FT._phase(LIVE)["pkg_dir"]
_live = pytest.mark.skipif(not os.path.isdir(LIVE_PKG), reason="the live round's package is absent")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _dump(p, doc):
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))


@pytest.fixture(scope="module")
def tasks():
    return FT.correction_tasks()


@pytest.fixture(scope="module")
def manifest():
    return _load(os.path.join(FT.CORR_PKG_DIR, FT.CORR_MANIFEST_NAME))


@pytest.fixture(scope="module")
def primary():
    return FT.primary_shards()


@pytest.fixture(scope="module")
def prompts(tasks):
    return collections.OrderedDict((t["task_id"], FT.correction_prompt(t)) for t in tasks)


@pytest.fixture(scope="module")
def live_pkg(tmp_path_factory):
    """The correction package rebuilt LIVE into a scratch directory. The
    shipped one is closed history since run 1504 was bound (its owner hash is
    pinned there), so package-owner proofs run on a live rebuild; the live
    gates (preflight/prepare/lifecycle) belong to the LAST round now."""
    d = str(tmp_path_factory.mktemp("live_corr_pkg"))
    FT.build_correction(d)
    return d


def test_the_live_rebuild_is_lawful_and_the_shipped_package_is_closed_history(live_pkg):
    assert FT.correction_package_problems(live_pkg) == []          # the lawful control, first
    assert FT.prompt_order_problems(FT.CORR_DOOR) == []
    bad = FT.correction_package_problems(FT.CORR_PKG_DIR)
    assert bad and any("derived_from" in b for b in bad), bad       # the owner moved; the bytes it ran under are pinned
    assert FT.proved_spend(FT._closed_run(FT.CORR_DOOR), FT.CORR_DOOR)[0]["calls"] == 5


# ----------------------------------------------------------- the population
def test_five_events_eight_rows_derive_from_the_bound_review_receipt(tasks, primary):
    shards, _raws = primary
    receipt = _load(FT.REVIEW_RECEIPT)
    order = [t["source_id"] for t in FT.event_tasks()]
    with_issues = {sid for sid, sh in shards.items() if sh["open_issues"]}
    reviewed = {sid for sid, fs in receipt["findings"].items() if any(f["kind"] == "reviewer_finding" for f in fs)}
    want = [sid for sid in order if sid in with_issues | reviewed]
    assert [t["source_id"] for t in tasks] == want == FT.correction_events()
    assert len(tasks) == 5 and sum(len(t["rows"]) for t in tasks) == 8
    assert [t["task_id"] for t in tasks] == ["ftc-%03d" % n for n in range(5)]
    by = {t["source_id"]: t for t in FT.event_tasks()}
    for t in tasks:                                  # every affected row, the primary's own index
        assert t["rows"] == by[t["source_id"]]["rows"] and t["event_index"] == by[t["source_id"]]["event_index"]
    # every open issue of the primary sits in the receipt verbatim; the receipt binds the exact primary
    for sid in order:
        declared = [{"what": f["what"], "why": f["why"]} for f in receipt["findings"].get(sid, []) if f["kind"] == "open_issue"]
        assert declared == [{"what": x["what"], "why": x["why"]} for x in shards[sid]["open_issues"]]
    assert receipt["primary_binding"]["binding_sha256"] == _sha(FT.BINDING)
    assert receipt["primary_binding"]["run_dir"] == FT._closed_run()


@_pkg
@pytest.mark.parametrize("how", ["dropped_event", "extra_event", "issue_reworded", "issue_dropped", "finding_without_rule", "unbound_receipt"])
def test_a_changed_or_unbound_review_receipt_refuses_the_package(how, tmp_path, monkeypatch, live_pkg):
    doc = _load(FT.REVIEW_RECEIPT)
    order = [t["source_id"] for t in FT.event_tasks()]
    clean = [s for s in order if s not in doc["findings"]][0]
    reviewed_only = [s for s, fs in doc["findings"].items() if all(f["kind"] == "reviewer_finding" for f in fs)][0]
    issued = [s for s, fs in doc["findings"].items() if any(f["kind"] == "open_issue" for f in fs)][0]
    if how == "dropped_event":
        del doc["findings"][reviewed_only]                       # 4 events instead of 5
    elif how == "extra_event":
        doc["findings"][clean] = [{"kind": "reviewer_finding", "source": "x", "text": "extra", "rules": ["Rule 6"]}]
    elif how == "issue_reworded":
        [f for f in doc["findings"][issued] if f["kind"] == "open_issue"][0]["what"] += " (reworded)"
    elif how == "issue_dropped":
        doc["findings"][issued] = [f for f in doc["findings"][issued] if f["kind"] != "open_issue"]
    elif how == "finding_without_rule":
        [f for f in doc["findings"][reviewed_only] if f["kind"] == "reviewer_finding"][0]["rules"] = []
    else:
        doc["primary_binding"]["binding_sha256"] = "0" * 64
    forged = str(tmp_path / "review.json"); _dump(forged, doc)
    monkeypatch.setattr(FT, "REVIEW_RECEIPT", forged)
    if how in ("dropped_event", "extra_event"):
        assert len(FT.correction_events()) == (4 if how == "dropped_event" else 6)
    else:
        with pytest.raises(ValueError):
            FT.correction_events()
    bad = FT.correction_package_problems(live_pkg)
    assert bad, how
    assert not FT.correction_preflight(live_pkg)["ok"]


# --------------------------------------------------------------- the prompt
def test_rules_first_event_rows_primary_lead_then_findings_last(tasks, prompts, primary, manifest):
    assert FT.prompt_order_problems(FT.CORR_DOOR) == []
    shards, raws = primary
    receipt = _load(FT.REVIEW_RECEIPT)
    boundary = HR._boundary_at(FT.SUFFIX)
    v3 = C.role_rules("drafter", FT.SUFFIX)
    prefix = FT.correction_prefix()
    assert prefix.startswith("[ROLE]\n%s\n\n[RULES]\n%s\n\n" % (F._ROLE, v3))
    assert manifest["semantic_rules_sha256"] == K._sha(v3) == _load(os.path.join(_load(FT.BINDING)["package"]["dir"], FT.MANIFEST_NAME))["semantic_rules_sha256"]
    # the primary prefix, transformed: the owner's decision block and the correction task join the trusted block and the one sentence moves
    assert prefix.replace(FT._decision_block(), "", 1).replace("[A4 CORRECTION TASK]\n%s\n\n" % FT._CORRECTION_TASK, "", 1).replace(
        FT.correction_input_sentence(), FT.input_sentence(), 1) == FT.prompt_prefix()
    for t in tasks:
        text = prompts[t["task_id"]]
        cut = text.find(boundary)
        assert 0 < text.find("[RULES]") < text.find("[A4 FINAL TASK]") < text.find("[A4 CORRECTION TASK]") < cut
        assert cut < text.find(FT.correction_control()) < text.rfind("[INPUT]\n")
        assert F._released_input_sentence() not in text and FT.input_sentence() not in text
        body = json.loads(text[len(prefix):], object_pairs_hook=collections.OrderedDict)
        assert list(body) == list(FT.CORR_PAYLOAD_KEYS)          # the findings are LAST
        assert body["event"]["source_id"] == t["source_id"]
        assert [r["row_index"] for r in body["rows"]] == list(range(1, len(t["rows"]) + 1))
        assert [dict(l) for l in body["leads"]] == [{"lead_id": "primary/%s" % t["source_id"], "origin": FT.CORR_LEAD_ORIGIN,
                                                    "sha256": K._sha(raws[t["source_id"]]), "reply": raws[t["source_id"]]}]
        assert body["reviewer_findings"] == receipt["findings"][t["source_id"]]
        for f in body["reviewer_findings"]:           # a finding points at rules; it never carries an answer
            assert set(f) <= {"kind", "what", "why", "source", "text", "rules"}
            assert f["kind"] in FT.FINDING_KINDS
        names = re.findall(r"`([a-z_]+)`", FT.correction_input_sentence())
        assert names == list(body) == list(FT.CORR_PAYLOAD_KEYS)
        for mark in ("[OWNER RULINGS]", "[DECISION RULES]", "[V4", "[V5", "[V6"):
            assert mark not in text
    assert manifest["counts"] == {"tasks": 5, "targets": 8, "groups": 0, "leads": 5,
                                  "findings": sum(len(v) for v in receipt["findings"].values()),
                                  "preserved_events": 3, "primary_calls": 5}


@_pkg
def test_lead_or_finding_leakage_or_swap_refuses(tasks, primary, monkeypatch, live_pkg):
    shards, raws = primary
    a, b = tasks[0]["source_id"], tasks[1]["source_id"]
    swapped = collections.OrderedDict(raws); swapped[a], swapped[b] = raws[b], raws[a]

    def fake(value):
        f = lambda *k: value              # noqa: E731
        f.cache_clear = lambda: None
        return f
    monkeypatch.setattr(FT, "_bound_cached", fake((shards, swapped)))
    bad = FT.correction_package_problems(live_pkg)
    assert bad and any("ftc-000" in x or "ftc-001" in x for x in bad), bad
    monkeypatch.undo()
    real = FT.correction_findings
    monkeypatch.setattr(FT, "correction_findings", lambda task, door=FT.CORR_DOOR: real(task, door) + [collections.OrderedDict(
        [("kind", "expected_answer"), ("text", "{}")])])
    assert any("lawful kind" in x for x in FT.prompt_order_problems(FT.CORR_DOOR))
    assert FT.correction_package_problems(live_pkg)


# ------------------------------------------------- replacement and preservation
def _replacements(shards, sids):
    return collections.OrderedDict((s, copy.deepcopy(shards[s])) for s in sids)


@_pkg
def test_lawful_full_replacement_preserves_the_three_clean_shards(primary, tasks, monkeypatch):
    shards, raws = primary
    pop = [t["source_id"] for t in tasks]
    repl = _replacements(shards, pop)
    fake_raws = collections.OrderedDict((s, raws[s] + "\n") for s in pop)   # distinct bytes for the corrected five
    real = FT.accepted_shards                     # the bound primary keeps its own proof
    monkeypatch.setattr(FT, "accepted_shards", lambda run: real(run) if run == FT._closed_run() else (repl, fake_raws, []))
    out, oraws, origins, bad = FT.successor_shards("/tmp/any_correction_run")
    assert bad == [] and list(out) == [t["source_id"] for t in FT.event_tasks()]
    for sid in out:
        if sid in pop:
            assert origins[sid] == "final_targeted_correction" and oraws[sid] == fake_raws[sid]
        else:
            assert origins[sid] == "final_targeted_primary" and oraws[sid] == raws[sid]   # byte for byte
    assert FT.preservation_problems("/tmp/any_correction_run") == []
    bound = {a["attempt"]: a for a in _load(FT.BINDING)["attempts"]}[1]["raw_files"]
    for sid in set(out) - set(pop):
        assert bound["%s.attempt1.proved.json" % sid] == K._sha(oraws[sid])


@_pkg
@pytest.mark.parametrize("how", ["partial", "outside_population", "primary_only"])
def test_partial_or_outside_replacement_is_named(how, primary, tasks, monkeypatch):
    shards, raws = primary
    pop = [t["source_id"] for t in tasks]
    clean = [s for s in shards if s not in pop][0]
    if how == "partial":
        sids = pop[:-1]
    elif how == "outside_population":
        sids = pop + [clean]
    else:
        sids = []
    repl = _replacements(shards, sids)
    real = FT.accepted_shards
    monkeypatch.setattr(FT, "accepted_shards", lambda run: real(run) if run == FT._closed_run()
                        else (repl, collections.OrderedDict((s, raws[s]) for s in sids), []))
    out, _r, origins, bad = FT.successor_shards("/tmp/any")
    if how == "partial":
        assert any("no accepted correction" in b for b in bad)
    elif how == "outside_population":
        assert any("outside the derived population" in b for b in bad) and origins[clean] == "final_targeted_primary"
    else:
        assert any("no accepted correction" in b for b in bad)
    assert FT.successor_shards(None)[3] == [] and FT.preservation_problems(None) == []


@_pkg
def test_changed_primary_evidence_refuses_everything(tmp_path, monkeypatch, live_pkg):
    run = FT._closed_run()
    dst = str(tmp_path / os.path.basename(run)); shutil.copytree(run, dst)
    p = os.path.join(dst, "raw", sorted(os.listdir(os.path.join(dst, "raw")))[0])
    io.open(p, "a", encoding="utf-8").write(" ")
    b = _load(FT.BINDING); b["run_dir"] = dst; b["attempts"] = [FT._measured_attempt(dst, 1)]
    forged = str(tmp_path / "binding.json"); _dump(forged, b)
    monkeypatch.setattr(FT, "BINDING", forged)
    with pytest.raises(ValueError):
        FT.primary_shards()                          # the tampered copy fails the pinned proofs
    bad = FT.correction_package_problems(live_pkg)
    assert any("cannot be rebuilt" in x for x in bad), bad
    assert not FT.correction_preflight(live_pkg)["ok"]
    assert FT.preservation_problems(None)


def test_open_issues_survive_the_parse_and_a_disagreement_is_never_invalid(tasks, primary):
    shards, raws = primary
    two = [t for t in tasks if len(t["rows"]) == 2][0]      # the event whose primary abstained on both rows
    obj, bad = FT.read_shard(raws[two["source_id"]], two, FT.correction_leads(two)) if False else (None, None)
    # a correction reply in the primary's exact shape (the primary text with its lead ids rewritten to this
    # phase's one lead) parses whole, and its open issues are preserved as evidence, not repaired or refused
    text = raws[two["source_id"]]
    parsed = K.RT.parse_reply(text)
    parsed["lead_reconciliation"] = [{"lead_id": "primary/%s" % two["source_id"], "agrees": False, "why": "control device"}]
    control = json.dumps(parsed, default=str)
    obj, bad = FT.read_shard(control, two, FT.correction_leads(two))
    assert bad == [], bad
    assert obj["open_issues"] == shards[two["source_id"]]["open_issues"] and obj["open_issues"]
    assert FT.RETRYABLE == ("invalid_response", "transport_no_answer")   # a semantic disagreement is neither


# --------------------------------------------------------------- the budget
@_pkg
def test_the_budget_and_transport_are_frozen_from_the_owners(manifest):
    """The package's budget is its receipt's, and the run it governed was made
    and bound: the ledger holds exactly its five calls under its own stage."""
    b, receipt = manifest["budget"], _load(FT.CORR_BUDGET_RECEIPT)
    assert b["budget_receipt_sha256"] == _sha(FT.CORR_BUDGET_RECEIPT)
    before = receipt["completed_before"]
    assert before == receipt["a4_closeout"]["before"] == b["before"]
    assert (b["primaries"], b["after_primaries"], b["worst_case_after"]) == (5, before + 5, before + 10)
    assert (b["a4_closeout_clean"], b["a4_closeout_worst"], b["global_ceiling"]) == (before + 6, before + 12, receipt["ceiling"])
    total, rows = A6.ledger()
    assert total == sum(r["calls"] for r in rows)
    assert sum(r["calls"] for r in rows if r["stage"].startswith("final_targeted_correction")) == b["primaries"]
    assert total >= b["after_primaries"]
    assert any("live ledger" in x for x in FT.budget_problems(manifest))   # closed: the ledger moved by its own 5
    assert manifest["transport"] == K._transport_block()
    assert manifest["transport"]["runtime_model_id"] == "claude-sonnet-5" and manifest["transport"]["disallowedTools"] == ["Read"]


@_pkg
@pytest.mark.parametrize("name", ["model", "effort", "task_text"])
def test_transport_or_prompt_drift_refuses(name, monkeypatch, live_pkg):
    if name == "model":
        monkeypatch.setattr(K, "MODEL", "opus")
    elif name == "effort":
        monkeypatch.setattr(K, "EFFORT", "low")
    else:
        monkeypatch.setattr(FT, "_CORRECTION_TASK", FT._CORRECTION_TASK + " ")
    assert FT.correction_package_problems(live_pkg), name


# ------------------------------------------------------ package and lifecycle
@_pkg
@_live
def test_the_correction_package_builds_twice_byte_identical_and_binds_its_owner(tmp_path, manifest, live_pkg):
    d1, d2 = str(tmp_path / "one"), str(tmp_path / "two")
    a, b = FT.build_correction(d1), FT.build_correction(d2)
    for name in (FT.CORR_MANIFEST_NAME, FT.CORR_PREFIX_NAME):
        assert _sha(os.path.join(d1, name)) == _sha(os.path.join(d2, name)) == _sha(os.path.join(live_pkg, name))
    assert a["manifest_sha256"] == b["manifest_sha256"]
    live = _load(os.path.join(live_pkg, FT.CORR_MANIFEST_NAME))
    assert live["derived_from"]["final_targeted_owner_sha256"] == _sha(FT._OWNER)
    assert manifest["derived_from"]["final_targeted_owner_sha256"] != _sha(FT._OWNER)   # the shipped package ran under the owner it pins
    assert _load(FT.CORR_BINDING)["package"]["manifest_sha256"] == _sha(os.path.join(FT.CORR_PKG_DIR, FT.CORR_MANIFEST_NAME))
    block = "[FINAL DECISION RULES]\n%s\n\n" % F._decision_rules_source().rstrip()
    shipped = K._read(os.path.join(FT.CORR_PKG_DIR, FT.CORR_PREFIX_NAME))
    assert K._read(os.path.join(live_pkg, FT.CORR_PREFIX_NAME)) == shipped.replace("[A4 CORRECTION TASK]\n", block + "[A4 CORRECTION TASK]\n", 1)   # moved by exactly the owner's block (SEQ 1507)
    assert [r["payload_sha256"] for r in live["tasks"]] == [r["payload_sha256"] for r in manifest["tasks"]]   # not one data byte moved
    for doc in (live, manifest):
        assert doc["derived_from"]["primary_binding"]["binding_sha256"] == _sha(FT.BINDING)
        assert doc["derived_from"]["review_receipt"]["sha256"] == _sha(FT.REVIEW_RECEIPT)
    assert FT.correction_package_problems(live_pkg) == [] and FT.correction_preflight(door=LIVE)["ok"]
    forged = str(tmp_path / "forged"); shutil.copytree(live_pkg, forged)
    doc = _load(os.path.join(forged, FT.CORR_MANIFEST_NAME))
    doc["tasks"].reverse(); doc["call_order"].reverse()
    _dump(os.path.join(forged, FT.CORR_MANIFEST_NAME), doc)
    got = FT.correction_preflight(forged)
    assert not got["ok"] and got["manifest"] is None


@_live
def test_prepare_finalize_and_the_precall_refusals(tmp_path):
    """Round one is closed (its calls were made and bound); the same lifecycle
    is exercised on the live round."""
    manifest = _load(os.path.join(LIVE_PKG, FT.CORR_MANIFEST_NAME))
    run = str(tmp_path / "a4_final_targeted_corr_probe")
    got = FT.prepare_correction_run(run, LIVE)
    assert got["ok"], got["problems"]
    assert [i["label"] for i in got["invocations"]] == manifest["call_order"]
    assert [i["script_sha256"] for i in got["invocations"]] == [r["script_sha256"] for r in manifest["tasks"]]
    for i in got["invocations"]:
        assert _sha(i["scriptPath"]) == i["script_sha256"] and i["attempt"] == 1
    receipt = _load(os.path.join(run, "receipt.json"))
    assert receipt["door"] == LIVE and receipt["allowed"] == manifest["call_order"]
    assert receipt["prompts"] == {r["source_id"]: r["prompt_sha256"] for r in manifest["tasks"]}
    assert FT.receipt_problems(run, receipt) == []
    assert not FT.prepare_correction_run(run, LIVE)["ok"]
    # a state of an EARLIER bound run that names a scheduled event is spent, never served again
    spent = [s for d in (FT.DOOR,) + FT.CORRECTION_DOORS[:-1]
             for s in _load(os.path.join(FT._closed_run(d), "receipt.json"))["states"]
             if K._state_label(_load(s)) in receipt["allowed"]]
    assert spent
    rec = json.loads(json.dumps(receipt)); rec["states"] = spent[:1]
    _proved, problems = FT.run_evidence(run, rec)
    assert problems and any("was already spent" in p for p in problems), problems
    doc = FT.finalize(run)
    assert doc["door"] == LIVE and not doc["primary_complete"] and doc["retry"] == [] and "child" not in doc
    assert doc["ledger"]["missing"] == len(manifest["call_order"])
    assert doc["budget"]["ledger_after"] == manifest["budget"]["after_primaries"]
    with pytest.raises((ValueError, OSError)):
        FT.finalize(run)
    p = os.path.join(run, "receipt.json"); rec = _load(p)
    rec["allowed"][0], rec["allowed"][1] = rec["allowed"][1], rec["allowed"][0]; _dump(p, rec)
    assert FT.receipt_problems(run, rec)
    with pytest.raises(ValueError):
        FT.render_correction_launcher(FT.correction_tasks(LIVE)[0], 3, door=LIVE)


# ---------------- Codex SEQ 1502 item 1: the REAL full 196-row successor composition
@pytest.fixture(scope="module")
def full():
    return FT.full_successor(None)


def test_the_full_successor_composes_exactly_the_eleven_into_the_signed_196(full, primary):
    shards, raws, prov, problems = full
    assert problems == []
    b = A6.bound()
    base, braws, _o, bbad = F.v6_shards(b)
    assert bbad == [] and list(shards) == list(base) and len(shards) == 36
    tasks = {t["source_id"]: t for t in F.event_tasks(b.evidence)}
    rows = [p for sid in shards for p in shards[sid]["rows"]]
    assert len(rows) == 196 == len(set(rows))
    import build_kfields_key_targeted as T
    diff = set(T.targets()); assert len(diff) == 11
    replaced = {p for sid in prov["events"] if prov["events"][sid]["composed"] for p in prov["events"][sid]["replaced"]}
    assert replaced == diff
    composed = [sid for sid in shards if prov["events"][sid]["composed"]]
    untouched = [sid for sid in shards if not prov["events"][sid]["composed"]]
    assert len(composed) == 8 and len(untouched) == 28
    assert sum(len(tasks[s]["rows"]) for s in untouched) == 149 and sum(len(tasks[s]["rows"]) for s in composed) == 47
    preserved = 0
    for sid in shards:
        for pid in tasks[sid]["rows"]:
            if pid in diff:
                continue
            assert shards[sid]["rows"][pid] == base[sid]["rows"][pid] and shards[sid]["outcomes"][pid] == base[sid]["outcomes"][pid]
            preserved += 1
    assert preserved == 185
    for sid in untouched:
        assert raws[sid] == braws[sid] and shards[sid] == base[sid]     # byte-preserved raw shards
    tshards, traws = primary
    for sid in composed:                                # honest component provenance, never synthesized raw evidence
        assert raws[sid] is None
        p = prov["events"][sid]
        assert p["base_raw_sha256"] == K._sha(braws[sid]) and p["targeted_raw_sha256"] == K._sha(traws[sid])
        index = {pid: n + 1 for n, pid in enumerate(tasks[sid]["rows"])}
        tindex = {n + 1: pid for n, pid in enumerate([t for t in FT.event_tasks() if t["source_id"] == sid][0]["rows"])}
        want = sorted([r for r in base[sid]["review"] if tasks[sid]["rows"][r["row_index"] - 1] not in diff]
                      + [dict(r, row_index=index[tindex[r["row_index"]]]) for r in tshards[sid]["review"]],
                      key=lambda r: (r["row_index"], r["fact_index"]))
        assert [dict(r) for r in shards[sid]["review"]] == want   # remapped to the FULL event positions
        for pid in p["replaced"]:
            assert shards[sid]["rows"][pid] == tshards[sid]["rows"][pid]
        assert shards[sid]["groups"] == base[sid]["groups"]        # the full baseline groups are preserved
    assert prov["corrected_inventory_sha256"] == _sha(T.CORRECTED_INVENTORY)
    assert FT.full_preservation_problems(None) == []
    counts = FT.full_counts(None)
    assert counts == {"events": 36, "rows": 196, "unique_rows": 196, "replaced": 11, "preserved": 185,
                      "untouched_events": 28, "untouched_rows": 149, "affected_events": 8, "affected_unchanged_rows": 36}


def test_the_full_key_materializes_through_the_locked_owner_only(full):
    shards, _raws, _prov, _problems = full
    real_inv, real_tasks = F._inventory, F.event_tasks
    key, sidecar, problems = FT.full_materialize(None)
    assert problems == [], problems[:3]
    assert len(sidecar["packet_to_gold"]) == 196 and len({m["packet_id"] for m in sidecar["packet_to_gold"]}) == 196
    assert F._inventory is real_inv and F.event_tasks is real_tasks
    assert not hasattr(FT, "materialize")            # the partial 11-row materializer is gone


@pytest.mark.parametrize("how", ["replacement_id", "inside_row", "untouched_shard", "component_hash", "review_index", "group_precondition"])
def test_every_composition_mutation_refuses(how, full, primary, monkeypatch):
    import build_kfields_key_targeted as T
    shards, raws, prov, _ = full
    diff = set(T.targets())
    b = A6.bound()
    tasks = {t["source_id"]: t for t in F.event_tasks(b.evidence)}
    composed = [sid for sid in shards if prov["events"][sid]["composed"]]
    untouched = [sid for sid in shards if not prov["events"][sid]["composed"]]
    tshards, traws = primary
    if how == "replacement_id":
        sid = composed[0]; ts = copy.deepcopy(tshards)
        pid = [p for p in tasks[sid]["rows"] if p in diff][0]; other = [p for p in tasks[sid]["rows"] if p not in diff][0]
        ts[sid]["rows"][other] = ts[sid]["rows"].pop(pid); ts[sid]["outcomes"][other] = ts[sid]["outcomes"].pop(pid)
        monkeypatch.setattr(FT, "successor_shards", lambda run: (ts, traws, {s: "final_targeted_primary" for s in ts}, []))
    elif how == "inside_row":                       # the COMPOSED output moves an unchanged row
        sid = composed[0]; other = [p for p in tasks[sid]["rows"] if p not in diff][0]
        real = FT.full_successor
        def forged(run=None):
            sh, rw, pv, pb = real(run); sh = copy.deepcopy(sh); sh[sid]["rows"][other]["abstentions"] = [{"reason": "forged"}]; return sh, rw, pv, pb
        monkeypatch.setattr(FT, "full_successor", forged)
    elif how == "untouched_shard":                  # the COMPOSED output carries a moved untouched shard
        sid = untouched[0]
        real = FT.full_successor
        def forged(run=None):
            sh, rw, pv, pb = real(run); rw = collections.OrderedDict(rw); rw[sid] = rw[sid] + " "; return sh, rw, pv, pb
        monkeypatch.setattr(FT, "full_successor", forged)
    elif how == "component_hash":
        real = FT.full_successor
        def forged(run=None):
            sh, rw, pv, pb = real(run); pv = copy.deepcopy(pv); pv["events"][composed[0]]["base_raw_sha256"] = "0" * 64; return sh, rw, pv, pb
        monkeypatch.setattr(FT, "full_successor", forged)
    elif how == "review_index":
        sid = composed[0]; ts = copy.deepcopy(tshards)
        ts[sid]["review"][0]["row_index"] = 99
        monkeypatch.setattr(FT, "successor_shards", lambda run: (ts, traws, {s: "final_targeted_primary" for s in ts}, []))
    else:                                           # the precondition: a changed packet inside a full group
        sid = composed[0]; pid = [p for p in tasks[sid]["rows"] if p in diff][0]
        baseline = FT._baseline()                    # the real signed baseline, parsed with the real groups
        monkeypatch.setattr(FT, "_baseline", lambda: baseline)
        real = F.event_tasks
        def forged(evidence_dir):
            out = copy.deepcopy(real(evidence_dir))
            for t in out:
                if t["source_id"] == sid:
                    t["groups"]["forged"] = [pid, tasks[sid]["rows"][0]]
            return out
        monkeypatch.setattr(F, "event_tasks", forged)
    bad = FT.full_preservation_problems(None)
    assert bad, how
    if how == "group_precondition":
        assert any("locator group" in x for x in bad), bad


# ---------------- Codex SEQ 1502 item 2: unambiguous prompts, truthful roles
def test_the_review_context_is_event_specific_and_the_roles_are_truthful(tasks, prompts):
    receipt = _load(FT.REVIEW_RECEIPT)
    texts = collections.Counter(f["text"] for fs in receipt["findings"].values() for f in fs if f["kind"] == "reviewer_finding")
    assert texts and max(texts.values()) == 1                # no paragraph repeated across events
    for t in tasks:
        fs = receipt["findings"][t["source_id"]]
        assert any(f["kind"] == "reviewer_finding" for f in fs)
    task = FT._CORRECTION_TASK
    assert "`leads` carries ONE prior settlement" in task and "`lead_reconciliation` reconciles" in task
    assert "`reviewer_findings`" in task and "last field" in task and "not a lead" in task
    assert "shown LAST below" not in task                     # only the findings field is last
    for t in tasks:
        body = json.loads(prompts[t["task_id"]][len(FT.correction_prefix()):], object_pairs_hook=collections.OrderedDict)
        assert list(body)[-1] == "reviewer_findings" and len(body["leads"]) == 1


# ---------------- Codex SEQ 1503: the one contradiction in the correction task
def test_the_correction_task_never_forbids_what_the_schema_requires(tasks, prompts, primary):
    old = "Do not repair, grade, defer to or explain either; decide the event"
    new = "Do not repair or defer to either; decide the event"
    assert old not in FT._CORRECTION_TASK and new in FT._CORRECTION_TASK
    assert "yourself under the rules above, in the SAME reply schema." in FT._CORRECTION_TASK   # the next line unchanged
    shards, raws = primary
    for t in tasks:
        text = prompts[t["task_id"]]
        assert old not in text and new in text
        body = json.loads(text[len(FT.correction_prefix()):], object_pairs_hook=collections.OrderedDict)
        assert list(body)[-1] == "reviewer_findings" and len(body["leads"]) == 1
    # the one lead is still reconciled, with `why`; the findings are outside reconciliation
    two = [t for t in tasks if len(t["rows"]) == 2][0]
    parsed = K.RT.parse_reply(raws[two["source_id"]])
    lead_id = "primary/%s" % two["source_id"]
    parsed["lead_reconciliation"] = [{"lead_id": lead_id, "agrees": False, "why": "control device"}]
    obj, bad = FT.read_shard(json.dumps(parsed, default=str), two, FT.correction_leads(two))
    assert bad == [] and [r["lead_id"] for r in obj["lead_reconciliation"]] == [lead_id]
    parsed["lead_reconciliation"] = [{"lead_id": lead_id, "agrees": False, "why": ""}]
    obj, bad = FT.read_shard(json.dumps(parsed, default=str), two, FT.correction_leads(two))
    assert obj is None and any("why" in b for b in bad)
    parsed["lead_reconciliation"] = [{"lead_id": lead_id, "agrees": False, "why": "x"},
                                     {"lead_id": "finding/0", "agrees": True, "why": "a finding is not a lead"}]
    obj, bad = FT.read_shard(json.dumps(parsed, default=str), two, FT.correction_leads(two))
    assert obj is None and any("one row per lead" in b for b in bad)
