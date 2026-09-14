# -*- coding: utf-8 -*-
"""THE SUCCESSOR FINAL-ADJUDICATION PRE-CALL FREEZE (Codex SEQ 1496 items 2-6).

Zero model calls. Lawful controls first, then every mutation Codex named:
changed population/order, missing/extra target, lead leakage or swap,
prompt/rules/model/effort drift, over-capacity input, receipt/state/raw
mutation, stale prior evidence - each refuses at the package, the prompt
order, the budget or the lifecycle door. The reader/materializer law is
proved on control shards spliced from the REAL bound blind replies (a test
device, never truth), and the wrapper reader is shown to be the locked
owner's on the one row the frozen quote can still read.
"""
import collections
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as A6                                    # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_hard_review_targeted as HRT                 # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402

C = K.C
_pkg = pytest.mark.skipif(not os.path.isdir(FT.PKG_DIR), reason="the successor package is absent")
LIVE = FT.CORRECTION_DOORS[-1]                      # the round whose gates are live now
LIVE_PKG = FT._phase(LIVE)["pkg_dir"]


@pytest.fixture(scope="module")
def live_pkg(tmp_path_factory):
    """The primary package rebuilt LIVE into a scratch directory. The shipped
    primary package is closed history since the run was bound (its owner hash
    is pinned there), so package-owner proofs run on a live rebuild; the live
    gates (preflight/prepare) belong to the correction phase now."""
    d = str(tmp_path_factory.mktemp("live_primary_pkg"))
    FT.build(d)
    return d


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _dump(p, doc):
    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))


def _bare(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    return re.sub(r"\s*```$", "", t)


@pytest.fixture(scope="module")
def tasks():
    return FT.event_tasks()


@pytest.fixture(scope="module")
def manifest():
    return _load(os.path.join(FT.PKG_DIR, FT.MANIFEST_NAME))


@pytest.fixture(scope="module")
def prompts(tasks):
    return collections.OrderedDict((t["task_id"], FT.final_prompt(t)) for t in tasks)


def _blind1(pid):
    return [x for x in FT.leads()[pid] if x[1] == FT.LEAD_ORIGINS[1]][0][3]


def control_text(task, settled_of=None, outcome_of=None, drop_row=None,
                 drop_review=None, drop_lead=None):
    """A LAWFUL CONTROL shard text for one event, splicing the real blind-1
    RAW replies (never re-serialized). Optional mutations for the refusals."""
    rows, review, raw_by = [], [], {}
    for n, pid in enumerate(task["rows"]):
        if drop_row == n:
            continue
        raw = _blind1((settled_of or {}).get(pid, pid))
        raw_by[n] = _bare(raw)
        nfacts = len(K.RT.parse_reply(raw)["facts"])
        outcome = (outcome_of or {}).get(pid, "fact" if nfacts else "exclusion")
        rows.append(collections.OrderedDict([
            ("row_index", n + 1), ("settled", "__SETTLED_%d__" % n),
            ("final_outcome", outcome),
            ("record_kind_note", "control: the frozen proposal is reconciled here")]))
        for i in range(nfacts):
            if drop_review == (n, i):
                continue
            review.append(collections.OrderedDict([
                ("row_index", n + 1), ("fact_index", i), ("hard_classes", []),
                (F.GOLD_ONLY[0], True),
                (F.GOLD_ONLY[1], collections.OrderedDict((k, False) for k in F.GOLD_EXTRA_KEYS)),
                (F.GOLD_ONLY[2], None)]))
    leads = FT.event_leads(task)
    rec = [collections.OrderedDict([("lead_id", x["lead_id"]), ("agrees", False),
                                    ("why", "control device")]) for x in leads]
    if drop_lead is not None:
        rec.pop(drop_lead)
    doc = collections.OrderedDict([
        ("source_id", task["source_id"]), ("rows", rows), ("review", review),
        ("groups", []), ("lead_reconciliation", rec), ("open_issues", [])])
    text = json.dumps(doc, indent=1)
    for n, raw in raw_by.items():
        text = text.replace('"__SETTLED_%d__"' % n, raw)
    return text


# ----------------------------------------------------------- the population
def test_eight_event_tasks_derive_from_the_eleven_items(tasks):
    by = FT.items()
    want = collections.OrderedDict()
    for pid in T.targets():
        want.setdefault(by[pid]["source_id"], []).append(pid)
    assert len(tasks) == 8 and len(T.targets()) == 11
    assert [t["source_id"] for t in tasks] == list(want)
    assert [t["rows"] for t in tasks] == list(want.values())
    assert [t["task_id"] for t in tasks] == ["fta-%03d" % n for n in range(8)]
    assert [t["event_index"] for t in tasks] == list(range(1, 9))
    flat = [p for t in tasks for p in t["rows"]]
    assert sorted(flat) == sorted(T.targets()) and len(set(flat)) == 11
    # groups are DERIVED from the frozen locator groups, restricted to corrected members
    grouped = [set(t["members"]) for t in HR.tasks(FT._a4_run()) if t["kind"] == "group"]
    for t in tasks:
        want_g = [[p for p in t["rows"] if p in g] for g in grouped]
        assert list(t["groups"].values()) == [g for g in want_g if len(g) > 1]
    assert FT.population_problems(tasks) == []


@_pkg
@pytest.mark.parametrize("name", ["reversed", "missing", "extra", "repeated"])
def test_changed_population_or_order_refuses_the_package(name, monkeypatch, live_pkg):
    real = T.targets()
    extra = [i["packet_id"] for i in K.phase1_items() if i["packet_id"] not in real][0]
    forged = {"reversed": list(reversed(real)), "missing": real[:-1],
              "extra": real + [extra], "repeated": real + [real[0]]}[name]
    monkeypatch.setattr(T, "targets", lambda *a, **k: forged)
    bad = FT.package_problems(live_pkg)
    assert bad, name
    if name == "extra":
        assert any("cannot be rebuilt" in b and "not a corrected item" in b for b in bad), bad


# --------------------------------------------------------------- the prompt
def test_the_prefix_is_the_locked_owners_composition_at_the_current_version(manifest):
    stale = F._released_input_sentence()
    # byte for byte the locked composition, except the ONE input sentence made truthful
    assert FT._prefix("").replace(FT.input_sentence(), stale, 1) == F.prompt_prefix()
    assert FT.prompt_prefix() != F.prompt_prefix()                # the version and that sentence differ
    v3 = C.role_rules("drafter", FT.SUFFIX)
    assert FT.prompt_prefix().startswith("[ROLE]\n%s\n\n[RULES]\n%s\n\n" % (F._ROLE, v3))
    assert manifest["semantic_rules_sha256"] == K._sha(v3)
    # the SAME rules the two blinds read (the accepted 1493 package)
    hr = _load(os.path.join(HRT.PKG_DIR, "hard_review.manifest.json"))
    assert hr["semantic_rules_sha256"] == manifest["semantic_rules_sha256"]
    assert manifest["contract_suffix"] == FT.SUFFIX == ".v3"
    assert manifest["role_sha256"] == K._sha(F._ROLE)
    assert manifest["task_section_sha256"] == K._sha(F._task_section())
    assert manifest["output_section_sha256"] == K._sha(F._output_section())


def test_rules_first_event_then_corrected_rows_then_untrusted_leads_last(tasks, prompts):
    assert FT.prompt_order_problems() == []
    corrected = FT.items()
    boundary = HR._boundary_at(FT.SUFFIX)
    for t in tasks:
        text = prompts[t["task_id"]]
        cut = text.find(boundary)
        assert 0 < text.find("[RULES]") < text.find("[OUTPUT]") < text.find("[A4 FINAL TASK]") < cut
        assert cut < text.find(FT.truthful_control()) < text.rfind("[INPUT]\n")
        body = json.loads(text[len(FT.prompt_prefix()):], object_pairs_hook=collections.OrderedDict)
        assert list(body) == list(FT.PAYLOAD_KEYS)
        assert body["event"]["source_id"] == t["source_id"]
        assert [r["row_index"] for r in body["rows"]] == list(range(1, len(t["rows"]) + 1))
        for r, pid in zip(body["rows"], t["rows"]):
            assert r["quote"] == corrected[pid]["quote"]                  # the CORRECTED item
            assert r["raw_label_or_claim"] == corrected[pid]["raw_label_or_claim"]
            assert r["proposed_record_kind"] == dict(F._inventory())[pid]["proposed_record_kind"]
        assert body["groups"] == [] and len(t["groups"]) == 0
        assert "UNTRUSTED LEADS" in F._ROLE and F._ROLE in text[:cut]


def test_leads_are_exactly_the_bound_proved_replies(tasks, manifest):
    by_task = {r["task_id"]: r for r in manifest["tasks"]}
    t_run, h_run = FT._bound_run(T.BINDING), FT._bound_run(HRT.BINDING)
    t_fin = _load(os.path.join(t_run, "finalization.json"))
    valid_t = {lab for lab, o, _w in t_fin["outcomes"] if o == "valid"}
    for t in tasks:
        leads = FT.event_leads(t)
        assert [x["lead_id"] for x in leads] == [x["lead_id"] for x in by_task[t["task_id"]]["leads"]]
        for n, pid in enumerate(t["rows"]):
            mine = [x for x in leads if x["row_index"] == n + 1]
            origins = [x["origin"] for x in mine]
            want = ([FT.LEAD_ORIGINS[0]] if pid in valid_t else []) + [FT.LEAD_ORIGINS[1]] * 2
            assert origins == want, (pid, origins)
            for x in mine:
                assert x["sha256"] == K._sha(x["reply"])
                if x["origin"] == FT.LEAD_ORIGINS[0]:
                    path = os.path.join(t_run, "raw", "%s.attempt1.proved.json" % pid.replace("#", "_"))
                else:
                    label = x["lead_id"].rsplit("/row", 1)[0]
                    path = os.path.join(h_run, "raw", "%s.attempt1.proved.json" % label.replace("/", "_"))
                assert io.open(path, encoding="utf-8").read() == x["reply"]
    assert manifest["counts"]["leads"] == 32
    assert manifest["counts"]["leads_by_origin"] == {"targeted_key_review": 10, "hard_review_blind": 22}
    no_targeted = [pid for t in tasks for pid in t["rows"] if pid not in valid_t]
    assert len(no_targeted) == 1                                   # the one item with no accepted result


def test_no_old_answer_ruling_verdict_or_sibling_leaks_into_a_prompt(tasks, prompts):
    b = A6.bound()
    raws = []
    for run, phase in ((b.events, "events"), (b.corrections, "corrections"), (b.decision, "decision"),
                       (b.decision_correction, "decision_correction"),
                       (b.decision_correction_v5, "decision_correction_v5"),
                       (b.decision_correction_v6, "decision_correction_v6")):
        if run:
            _sh, rw, _bad = F.accepted_shards(run, b, phase)
            raws += [_bare(v) for k, v in rw.items() if k in {t["source_id"] for t in tasks}]
    assert raws                                                     # the locked key's own shards exist
    others = {t["source_id"] for t in F.event_tasks(b.evidence)} - {t["source_id"] for t in tasks}
    for t in tasks:
        text = prompts[t["task_id"]]
        for raw in raws:
            assert raw not in text                                  # no old key answer
        for mark in ("[OWNER RULINGS]", "[DECISION RULES]", "[A4 CORRECTION TASK]", "[V4", "[V5", "[V6"):
            assert mark not in text
        body = json.loads(text[len(FT.prompt_prefix()):], object_pairs_hook=collections.OrderedDict)
        for lead in body["leads"]:
            assert set(lead) == {"lead_id", "row_index", "origin", "sha256", "reply"}
            assert lead["origin"] in FT.LEAD_ORIGINS
        assert not any(sid in text for sid in others)               # no sibling event
    assert "Never vote, never take a majority" in F._ROLE


def test_lead_leakage_or_swap_refuses_the_package(tasks, monkeypatch, live_pkg):
    real = FT.leads()
    a, c = tasks[0]["rows"][0], tasks[1]["rows"][0]
    swapped = dict(real); swapped[a], swapped[c] = real[c], real[a]

    def fake(value):                      # a stand-in cache the operation rule can clear
        f = lambda *k: value              # noqa: E731
        f.cache_clear = lambda: None
        return f
    monkeypatch.setattr(FT, "_leads_cached", fake(swapped))
    bad = FT.package_problems(live_pkg)
    assert bad and any("fta-000" in b or "fta-001" in b for b in bad), bad
    leaked = dict(real)
    leaked[a] = real[a] + [("codex/proposal", "codex_proposal", K._sha("x"), "x")]
    monkeypatch.setattr(FT, "_leads_cached", fake(leaked))
    assert any("lawful origin" in b for b in FT.prompt_order_problems())
    assert FT.package_problems(live_pkg)


# ---------------------------------------------------------- the rule class
ANCHORS = ("One name = one cause; split independent causes into separate facts",
           "Emit each distinct fact exactly ONCE",
           "Change and comparison numbers are SOURCE-STATED only",
           "measurement (`measurement_raw_spans`)",
           "Rule 6 — the period",
           "reuse a menu value when the",
           "abstain (reason only)")


def test_the_served_rules_carry_the_general_rules_the_defect_class_needs():
    shipped = io.open(os.path.join(FT.PKG_DIR, FT.PREFIX_NAME), encoding="utf-8").read()
    rules = C.role_rules("drafter", FT.SUFFIX)
    for anchor in ANCHORS:
        assert anchor in rules and anchor in shipped, anchor
    # the prefix is item-free: no corrected quote, label or id is written into it
    for it in FT.items().values():
        assert it["quote"] not in shipped and it["packet_id"] not in shipped
        assert it["raw_label_or_claim"] not in shipped
    src = io.open(os.path.join(_HERE, "build_kfields_final_targeted.py"), encoding="utf-8").read()
    for it in FT.items().values():
        assert it["packet_id"] not in src and it["source_id"] not in src and it["quote"] not in src


@_pkg
@pytest.mark.parametrize("name", ["rules_version", "role", "task_section", "output_section",
                                  "model", "effort", "boundary"])
def test_rules_prompt_model_or_effort_drift_refuses(name, monkeypatch, live_pkg):
    """The rules and output card are the contract owner's bytes: a change
    there refuses harness-wide (the A3 evidence proof) before any package can
    even rebuild. The drifts a wrapper itself could suffer are exercised."""
    if name == "rules_version":
        monkeypatch.setattr(FT, "SUFFIX", "")                    # the v1 rules instead of v3
    elif name == "role":
        monkeypatch.setattr(F, "_ROLE", F._ROLE + " ")
    elif name == "task_section":
        real = F._task_section
        monkeypatch.setattr(F, "_task_section", lambda: real() + "\nextra")
    elif name == "output_section":
        real = F._output_section
        monkeypatch.setattr(F, "_output_section", lambda: real() + "\nextra")
    elif name == "model":
        monkeypatch.setattr(K, "MODEL", "opus")
    elif name == "effort":
        monkeypatch.setattr(K, "EFFORT", "low")
    else:
        real = HR._boundary_at
        monkeypatch.setattr(HR, "_boundary_at", lambda s: real(s) + "!")
    bad = FT.package_problems(live_pkg)
    assert bad, name
    if name == "rules_version":
        assert any("semantic_rules_sha256" in b or "contract_suffix" in b for b in bad), bad


@_pkg
def test_over_capacity_input_refuses(monkeypatch, live_pkg):
    monkeypatch.setattr(K, "TRANSPORT_LIMIT", 1000)
    got = FT.preflight(live_pkg)
    assert not got["ok"] and got["manifest"] is None
    # the package owner already rejects the pinned capacity block against the
    # live derivation; preflight is terminal on that and reads no field
    assert any("capacity" in p for p in got["problems"]), got["problems"]


@_pkg
def test_stale_or_tampered_prior_evidence_refuses(tmp_path, monkeypatch, live_pkg):
    run = FT._bound_run(HRT.BINDING)
    dst = str(tmp_path / os.path.basename(run)); shutil.copytree(run, dst)
    raw = sorted(os.listdir(os.path.join(dst, "raw")))[0]
    io.open(os.path.join(dst, "raw", raw), "a", encoding="utf-8").write(" ")   # one byte
    binding = {"schema": HRT.BINDING_SCHEMA, "run_dir": dst,
               "attempts": [HRT._measured_attempt(dst, 1)]}                  # rebound AFTER tampering
    b = str(tmp_path / "b.json"); _dump(b, binding)
    monkeypatch.setattr(HRT, "BINDING", b)
    FT._leads_cached.cache_clear()
    with pytest.raises(ValueError):
        FT.leads()                                                    # the accounting owner refuses
    bad = FT.package_problems(live_pkg)
    assert any("cannot be rebuilt" in x for x in bad), bad
    FT._leads_cached.cache_clear()


# ------------------------------------------------------------------ budget
@_pkg
def test_the_budget_is_bound_to_the_receipt_and_the_live_ledger(manifest):
    """The PRIMARY package's budget was bound to its receipt at its freeze
    (5202 -> 5210); the run is now counted, so its package is history and the
    live-ledger check belongs to the correction package."""
    b, receipt = manifest["budget"], _load(FT.BUDGET_RECEIPT)
    assert b["budget_receipt_sha256"] == _sha(FT.BUDGET_RECEIPT)
    assert (b["before"], b["primaries"], b["after_primaries"], b["worst_case_after"]) == (5202, 8, 5210, 5218)
    assert (b["a4_closeout_clean"], b["a4_closeout_worst"], b["global_ceiling"]) == (5211, 5220, 6000)
    assert b["signer_reserve"] == {"primaries": 1, "retry_cap": 1}
    assert receipt["completed_before"] == 5202 == receipt["a4_closeout"]["before"]
    out = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys, json; sys.path.insert(0, %r); sys.path.insert(0, '/home/faisal/EventMarketDB'); "
         "import a6_launch_freeze as A6; print(json.dumps(A6.ledger()))" % _HERE],
        capture_output=True, text=True, cwd="/home/faisal/EventMarketDB")
    assert out.returncode == 0, out.stderr[-400:]
    total, rows = json.loads(out.stdout)
    since = [r for r in rows if r not in receipt["completed_rows"] and r["stage"] != "final_targeted_primary"]
    assert total == b["after_primaries"] + sum(r["calls"] for r in since)   # this run's spend plus every stage bound since
    assert any("live ledger" in x for x in FT.budget_problems(manifest))   # closed: the ledger moved by its own 8
    corr = _load(os.path.join(LIVE_PKG, FT.CORR_MANIFEST_NAME))
    assert FT.budget_problems(corr) == []


# ------------------------------------------------------------ double build
@_pkg
def test_the_package_builds_twice_byte_identical(tmp_path, live_pkg):
    d1, d2 = str(tmp_path / "one"), str(tmp_path / "two")
    a, b = FT.build(d1), FT.build(d2)
    for name in (FT.MANIFEST_NAME, FT.PREFIX_NAME):
        assert _sha(os.path.join(d1, name)) == _sha(os.path.join(d2, name)) == _sha(os.path.join(live_pkg, name))
    assert a["manifest_sha256"] == b["manifest_sha256"]
    assert FT.package_problems(live_pkg) == []
    # the shipped primary package differs from the live rebuild by exactly the pinned owner hash
    pinned = _load(os.path.join(FT.PKG_DIR, FT.MANIFEST_NAME)); live = _load(os.path.join(d1, FT.MANIFEST_NAME))
    assert {k for k in live if live[k] != pinned[k]} == {"derived_from"}
    assert {k for k in live["derived_from"] if live["derived_from"][k] != pinned["derived_from"][k]} == {"final_targeted_owner_sha256"}
    with pytest.raises((ValueError, OSError)):                       # write-once
        FT.build(d1)
    forged = str(tmp_path / "forged"); shutil.copytree(live_pkg, forged)
    doc = _load(os.path.join(forged, FT.MANIFEST_NAME)); doc["version"] = "other"
    _dump(os.path.join(forged, FT.MANIFEST_NAME), doc)
    got = FT.preflight(forged)
    assert not got["ok"] and any("version" in p for p in got["problems"])


# ------------------------------------------ the reader / materializer law
def test_the_lawful_primary_composes_and_materializes_through_the_locked_owner():
    """The eight bound primary shards, composed into the signed 196-row key
    and materialized by F.materialize alone (Codex SEQ 1502 item 1)."""
    key, side, problems = FT.full_materialize(None)
    assert problems == [], problems[:3]
    assert len(side["packet_to_gold"]) == 196
    assert side["exclusions"] and any(a["packet_id"].endswith("#072") for a in side["abstentions"])
    assert not hasattr(FT, "materialize")


def test_every_shape_defect_refuses(tasks):
    two = [t for t in tasks if len(t["rows"]) == 2][0]
    for kw, why in ((dict(drop_row=0), "rows must be"), (dict(drop_review=(0, 0)), "review rows are"),
                    (dict(drop_lead=0), "lead_reconciliation must be"),
                    (dict(outcome_of={two["rows"][0]: "control"}), "cannot carry a fact")):
        obj, bad = FT.read_shard(control_text(two, **kw), two, FT.event_leads(two))
        assert obj is None and any(why in b for b in bad), (kw, bad)


def test_a_same_event_repeat_is_refused_not_carried_twice(tasks, monkeypatch):
    two = [t for t in tasks if len(t["rows"]) == 2][0]
    rep = control_text(two, settled_of={two["rows"][1]: two["rows"][0]})   # row 2 restates row 1
    obj, bad = FT.read_shard(rep, two, FT.event_leads(two))
    assert bad == []                                                # the shape is lawful
    shards, raws = FT.primary_shards()
    shards[two["source_id"]] = obj
    monkeypatch.setattr(FT, "successor_shards", lambda run: (shards, raws, {s: "final_targeted_primary" for s in shards}, []))
    _key, _side, problems = FT.full_materialize(None)
    assert any("same event" in p and two["source_id"] in p for p in problems), problems


def test_the_reader_and_materializer_are_the_locked_owners_through_a_restored_scope(tasks, monkeypatch):
    """Codex SEQ 1497 item 4 / 1502 item 1: no copied bodies. The wrapper
    delegates to F.read_shard / F.materialize inside serial try/finally
    scopes that supply the corrected items / inventory and restore every
    owner after success AND after a raised error."""
    real_items, real_inv = HR._items, F._inventory
    src = io.open(os.path.join(_HERE, "build_kfields_final_targeted.py"), encoding="utf-8").read()
    assert "obj = K.RT.parse_reply(text)" not in src and "review_by = {" not in src   # no copied bodies
    key, side, problems = FT.full_materialize(None)
    assert problems == [] and len(key) == 36 and HR._items is real_items and F._inventory is real_inv
    two = [t for t in tasks if len(t["rows"]) == 2][0]
    obj, bad = FT.read_shard(control_text(two), two, FT.event_leads(two))
    assert bad == [] and HR._items is real_items

    class Marker(Exception):
        pass

    def boom(*a, **k):
        raise Marker()
    monkeypatch.setattr(F, "read_shard", boom)
    with pytest.raises(Marker):
        FT.read_shard(control_text(two), two, FT.event_leads(two))
    assert HR._items is real_items
    monkeypatch.setattr(F, "materialize", boom)
    with pytest.raises(Marker):
        FT.full_materialize(None)
    assert F._inventory is real_inv


def test_lead_content_never_enters_the_parse(tasks):
    """Two agreeing blinds cannot bypass any rule: the reader binds lead IDS
    only; the lead bytes are never read by code."""
    t = tasks[0]
    leads = FT.event_leads(t)
    shuffled = [dict(x, reply="not the lead", sha256="0" * 64) for x in leads]
    text = control_text(t)
    a = FT.read_shard(text, t, leads); b = FT.read_shard(text, t, shuffled)
    assert a[1] == b[1] == [] and json.dumps(a[0], default=str) == json.dumps(b[0], default=str)


# --------------------------------------------------------- the lifecycle
@_pkg
def test_prepare_finalize_and_every_precall_refusal(tmp_path):
    """The primary phase is closed (its calls were made); the same lifecycle
    is exercised on the live correction phase."""
    manifest = _load(os.path.join(LIVE_PKG, FT.CORR_MANIFEST_NAME))
    run = str(tmp_path / "a4_final_targeted_probe")
    got = FT.prepare_correction_run(run, LIVE)
    assert got["ok"], got["problems"]
    assert [i["label"] for i in got["invocations"]] == manifest["call_order"]
    assert [i["script_sha256"] for i in got["invocations"]] == [r["script_sha256"] for r in manifest["tasks"]]
    for i in got["invocations"]:
        assert _sha(i["scriptPath"]) == i["script_sha256"]
        assert "CLAUDE_CODE_MAX_OUTPUT_TOKENS" not in io.open(i["scriptPath"]).read()   # env, not script
    receipt = _load(os.path.join(run, "receipt.json"))
    assert receipt["allowed"] == manifest["call_order"] and receipt["attempt"] == 1
    assert receipt["prompts"] == {r["source_id"]: r["prompt_sha256"] for r in manifest["tasks"]}
    assert receipt["version"] == FT.VERSION and receipt["manifest_sha256"] == _sha(os.path.join(LIVE_PKG, FT.CORR_MANIFEST_NAME))
    assert FT.receipt_problems(run, receipt) == []
    assert not FT.prepare_correction_run(run, LIVE)["ok"]           # never twice into one directory
    # a state that is not an official state of this door: refused before anything else
    hrt = _load(os.path.join(FT._bound_run(HRT.BINDING), "receipt.json"))["states"][0]
    foreign = str(tmp_path / "foreign.json")
    doc_f = _load(hrt)                                             # a scheduled label, an unofficial place
    [r for r in doc_f["workflowProgress"] if r.get("type") == "workflow_agent"][0]["label"] = manifest["call_order"][0]
    _dump(foreign, doc_f)
    for state, why in ((hrt, "not a scheduled event"), (foreign, "not where the runtime puts")):
        rec = json.loads(json.dumps(receipt)); rec["states"] = [state]
        _proved, problems = FT.run_evidence(run, rec)
        assert any(why in p for p in problems), (why, problems)
    # a raw byte that is not the official text is a recorded problem, never credit
    run_id = os.path.splitext(os.path.basename(hrt))[0]
    os.makedirs(os.path.join(run, "raw"))
    io.open(os.path.join(run, "raw", "%s.000.raw.json" % run_id), "w").write("tampered")
    FT.record_state(run, hrt)
    doc = FT.finalize(run)
    assert not doc["primary_complete"] and doc["retry"] == [] and "child" not in doc
    assert any("not the official returned text" in p for p in doc["problems"])
    assert doc["ledger"]["missing"] == len(manifest["call_order"])
    assert doc["budget"]["ledger_after"] == manifest["budget"]["after_primaries"]
    with pytest.raises((ValueError, OSError)):                       # finalize is write-once
        FT.finalize(run)
    # a tampered receipt is refused whole
    run2 = str(tmp_path / "a4_final_targeted_probe2"); assert FT.prepare_correction_run(run2, LIVE)["ok"]
    p = os.path.join(run2, "receipt.json"); rec = _load(p)
    rec["allowed"][0], rec["allowed"][1] = rec["allowed"][1], rec["allowed"][0]; _dump(p, rec)
    assert FT.receipt_problems(run2, rec)
    doc2 = FT.finalize(run2)
    assert doc2["problems"] and all(o == "unproved" for _l, o, _w in doc2["outcomes"])
    # attempt 2 without a finalized parent is an orphan; attempt 3 does not exist
    assert FT.receipt_problems(str(tmp_path / "orphan"), dict(receipt, attempt=2))
    assert FT.receipt_problems(run, dict(receipt, attempt=3))
    with pytest.raises(ValueError):
        FT.render_launcher(FT.event_tasks()[0], 3)


# ------------------------------------------- Codex SEQ 1497: four pre-call defects
@_pkg
def test_the_package_binds_its_own_owner(tmp_path, monkeypatch, live_pkg):
    owner = os.path.join(_HERE, "build_kfields_final_targeted.py")
    assert _load(os.path.join(live_pkg, FT.MANIFEST_NAME))["derived_from"]["final_targeted_owner_sha256"] == _sha(owner)
    assert _load(os.path.join(LIVE_PKG, FT.CORR_MANIFEST_NAME))["derived_from"]["final_targeted_owner_sha256"] == _sha(owner)
    mutated = str(tmp_path / "build_kfields_final_targeted.py"); shutil.copy(owner, mutated)
    io.open(mutated, "a", encoding="utf-8").write("\n# one byte\n")
    monkeypatch.setattr(FT, "_OWNER", mutated)
    bad = FT.package_problems(live_pkg)
    assert any("derived_from" in b for b in bad), bad
    assert not FT.preflight(live_pkg)["ok"] and not FT.correction_preflight(door=LIVE)["ok"]


@_pkg
def test_a_second_operation_starts_from_a_fresh_owner_proof(tasks, monkeypatch, live_pkg):
    assert FT.package_problems(live_pkg) == []                   # warm, lawful

    def refuse(run):
        raise ValueError("the targeted evidence refuses")
    monkeypatch.setattr(T, "proved_spend", refuse)
    bad = FT.package_problems(live_pkg)                          # a SECOND operation, no manual clear
    assert any("cannot be rebuilt" in b and "refuses" in b for b in bad), bad
    assert not FT.preflight(live_pkg)["ok"] and not FT.correction_preflight(door=LIVE)["ok"]
    with pytest.raises(ValueError):
        FT.manifest()
    monkeypatch.undo()
    assert FT.package_problems(live_pkg) == []                   # and lawful again
    pid = tasks[0]["rows"][0]
    got = FT.leads(); got[pid].append(("junk", "junk", "0" * 64, "junk"))
    assert FT.leads()[pid] != got[pid]                           # a returned object stays isolated


def test_the_data_boundary_sentence_is_truthful(tasks, prompts, manifest):
    stale = F._released_input_sentence()
    boundary = HR._boundary_at(FT.SUFFIX)
    for t in tasks:
        text = prompts[t["task_id"]]
        control = text[text.find(boundary):text.rfind("[INPUT]\n")]
        assert stale not in control and "`item`" not in control
        assert control.count(FT.input_sentence()) == 1
        body = json.loads(text[len(FT.prompt_prefix()):], object_pairs_hook=collections.OrderedDict)
        named = re.findall(r"`([a-z_]+)`", FT.input_sentence())
        assert named == list(body) == list(FT.PAYLOAD_KEYS)
    assert manifest["injection_control_sha256"] == K._sha(FT.truthful_control()) != K._sha(C.INJECTION_CONTROL)
    assert FT.truthful_control() == C.INJECTION_CONTROL.replace(stale, FT.input_sentence(), 1)


# ------------------------- Codex SEQ 1498: expected IO failures are named refusals
def _no_raise(fn, *a):
    """The gate contract: a named problem, never an exception, for EXPECTED failures."""
    try:
        return fn(*a)
    except (OSError, ValueError) as exc:
        pytest.fail("the gate raised %s: %s" % (type(exc).__name__, exc))


@_pkg
def test_a_missing_or_unreadable_bound_evidence_file_is_a_named_refusal(tmp_path, monkeypatch, live_pkg):
    assert FT.package_problems(live_pkg) == []                   # the lawful outer operation, warm
    absent = str(tmp_path / "definitely_absent_binding.json")
    monkeypatch.setattr(HRT, "BINDING", absent)
    bad = _no_raise(FT.package_problems, live_pkg)               # a SECOND public operation, no manual clear
    assert bad and any("cannot be rebuilt" in b for b in bad), bad
    got = _no_raise(FT.preflight, live_pkg)
    assert got["ok"] is False and got["problems"]
    run = str(tmp_path / "a4_final_targeted_never")
    got = _no_raise(FT.prepare_correction_run, run, LIVE)
    assert got["ok"] is False and got["invocations"] == [] and not os.path.exists(run)
    unreadable = str(tmp_path / "unreadable_binding.json"); shutil.copy(HRT.BINDING if os.path.exists(HRT.BINDING) else os.path.join(K.EVIDENCE, "hard_review_targeted_binding.json"), unreadable)
    os.chmod(unreadable, 0)
    monkeypatch.setattr(HRT, "BINDING", unreadable)
    bad = _no_raise(FT.package_problems, live_pkg)
    assert bad and any("cannot be rebuilt" in b for b in bad), bad
    os.chmod(unreadable, 0o600)
    monkeypatch.undo()
    assert FT.package_problems(live_pkg) == [] and FT.correction_preflight(door=LIVE)["ok"]   # clean again


@_pkg
@pytest.mark.parametrize("how", ["missing", "unreadable", "malformed", "not_this_shape"])
def test_a_missing_unreadable_or_malformed_packaged_manifest_is_a_named_refusal(how, tmp_path, live_pkg):
    pkg = str(tmp_path / "pkg"); shutil.copytree(live_pkg, pkg)
    man = os.path.join(pkg, FT.MANIFEST_NAME)
    if how == "missing":
        os.remove(man)
    elif how == "unreadable":
        os.chmod(man, 0)
    elif how == "malformed":
        io.open(man, "w").write("{")
    else:
        io.open(man, "w").write("[]")
    try:
        bad = _no_raise(FT.package_problems, pkg)
        assert bad and any("manifest" in b for b in bad), bad
        got = _no_raise(FT.preflight, pkg)
        assert got == {"ok": False, "problems": got["problems"], "manifest": None} and got["problems"]
    finally:
        if how == "unreadable":
            os.chmod(man, 0o600)


@_pkg
def test_a_missing_or_malformed_budget_receipt_or_ledger_is_a_named_refusal(manifest, tmp_path, monkeypatch, live_pkg):
    monkeypatch.setattr(FT, "BUDGET_RECEIPT", str(tmp_path / "absent_receipt.json"))
    bad = _no_raise(FT.package_problems, live_pkg)
    assert bad and any("cannot be rebuilt" in b for b in bad), bad
    assert _no_raise(FT.budget_problems, manifest)
    malformed = str(tmp_path / "malformed_receipt.json"); io.open(malformed, "w").write("{")
    monkeypatch.setattr(FT, "BUDGET_RECEIPT", malformed)
    assert any("budget receipt" in b for b in _no_raise(FT.budget_problems, manifest))
    monkeypatch.undo()
    real = A6._read_ptr
    monkeypatch.setattr(A6, "_read_ptr", lambda name: real(name) if name != "hard_review_targeted_dir.txt" else io.open(str(tmp_path / "absent_pointer")).read())
    bad = _no_raise(FT.budget_problems, manifest)
    assert any("live ledger" in b for b in bad), bad
    monkeypatch.undo()
    corr = _load(os.path.join(LIVE_PKG, FT.CORR_MANIFEST_NAME))
    assert FT.budget_problems(corr) == []


# ------------------ Codex SEQ 1499: a rejected package is terminal for preflight
@_pkg
def test_a_rejected_package_is_terminal_for_preflight_and_prepare(tmp_path, live_pkg):
    assert FT.correction_preflight(door=LIVE)["ok"]                       # the lawful control (the live phase)
    pkg = str(tmp_path / "pkg"); shutil.copytree(live_pkg, pkg)
    man = os.path.join(pkg, FT.MANIFEST_NAME)
    doc = _load(man); doc["capacity"] = []; _dump(man, doc)      # a valid object, one nested field malformed
    bad = _no_raise(FT.package_problems, pkg)
    assert bad and any("capacity" in b for b in bad), bad
    got = _no_raise(FT.preflight, pkg)
    assert got == {"ok": False, "problems": bad, "manifest": None}
    run = str(tmp_path / "a4_final_targeted_never")
    real = FT.PKG_DIR
    try:
        FT.PKG_DIR = pkg
        got = _no_raise(FT.prepare_run, run)
    finally:
        FT.PKG_DIR = real
    assert got["ok"] is False and got["invocations"] == [] and not os.path.exists(run)


@_pkg
def test_once_the_package_owner_refuses_no_later_owner_is_consulted(monkeypatch, live_pkg):
    """The whole class, not one field: after package_problems returns a
    problem, preflight touches neither the prompts nor any packaged field."""
    called = []
    monkeypatch.setattr(FT, "package_problems", lambda pkg_dir=None, door=None: ["the package owner refuses"])
    monkeypatch.setattr(FT, "prompt_order_problems", lambda: called.append("prompts") or [])
    monkeypatch.setattr(FT, "budget_problems", lambda doc: called.append("budget") or [])
    monkeypatch.setattr(K, "_load", lambda path: called.append("manifest") or (_ for _ in ()).throw(AssertionError("read")))
    got = FT.preflight(live_pkg)
    assert got == {"ok": False, "problems": ["the package owner refuses"], "manifest": None}
    assert called == []
