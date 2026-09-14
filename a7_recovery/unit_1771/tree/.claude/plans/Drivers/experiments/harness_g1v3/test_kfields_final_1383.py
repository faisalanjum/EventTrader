"""Codex SEQ 1383 — focused proof for the versioned A4 correction path.

Build-only: no model call, no API, no database. Red first, and a compact
PARAMETERIZED matrix rather than one test per anecdote: the class-wide
consequences Codex listed are mutation targets here, never prompt exceptions.

Nothing in this file writes into the real event run. The accepted evidence is
copied into tmp_path first, so a mutation control can never damage history.
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

import build_kfields_final as F                                  # noqa: E402
import test_kfields_final_1379 as T9                             # noqa: E402
import test_kfields_final_1380 as T8                             # noqa: E402

K = F.K
EV, HRR, FIXR = T9.EV, T9.HRR, T9.FIXR
_S = os.environ.get(
    "KF_SCRATCH", "/tmp/claude-1000/-home-faisal-EventMarketDB/"
    "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
LIVE_EVENTS = io.open(os.path.join(_S, "final_dir.txt"),
                      encoding="utf-8").read().strip()


@pytest.fixture(scope="module")
def pkg(tmp_path_factory):
    out = str(tmp_path_factory.mktemp("pkg1383") / "p")
    F.build(out, EV, HRR, FIXR)
    return out


@pytest.fixture
def events(tmp_path):
    """A private copy of the accepted event run. History is never touched."""
    dst = str(tmp_path / "events_v1")
    shutil.copytree(LIVE_EVENTS, dst)
    return dst


@pytest.fixture
def bound(pkg, events):
    return F.Bound(pkg, EV, HRR, FIXR, events)


def _prepare(tmp_path, bound):
    out = str(tmp_path / "corr")
    got = F.prepare_corrections(out, bound)
    return out, got


# ============================================================ denominator ==
def test_the_denominator_is_derived_not_supplied(bound):
    labs = F.correction_labels(bound)
    shards, _r, _b = F.accepted_shards(bound.events, bound)
    order = [t["source_id"] for t in F.event_tasks(EV)]
    assert labs == [s for s in order if shards[s]["open_issues"]]
    assert len(labs) == 32
    assert len(order) == 36


def test_clearing_an_issue_removes_that_event_from_the_denominator(bound,
                                                                   monkeypatch):
    """No caller can hand in a plan: the set follows the accepted answers."""
    real = F.accepted_shards
    labs = F.correction_labels(bound)
    drop = labs[0]

    def cleared(event_dir, b):
        sh, raws, bad = real(event_dir, b)
        sh[drop] = dict(sh[drop], open_issues=[])
        return sh, raws, bad

    monkeypatch.setattr(F, "accepted_shards", cleared)
    again = F.correction_labels(bound)
    assert drop not in again
    assert len(again) == len(labs) - 1


def test_prepare_publishes_exactly_the_derived_set(bound, tmp_path):
    out, got = _prepare(tmp_path, bound)
    assert got["ok"], got["problems"]
    assert [i["label"] for i in got["invocations"]] == F.correction_labels(bound)
    assert all(i["args"] is None for i in got["invocations"])
    for i in got["invocations"]:
        assert K._sha(K._read(i["scriptPath"])) == i["script_sha256"]


# ================================================================= prompt ==
def test_the_ruling_block_is_first_and_byte_identical(bound):
    labs = F.correction_labels(bound)
    prefix = F.correction_prefix(bound.package)
    assert prefix.startswith("[OWNER RULINGS]")
    for label in labs:
        assert F.correction_prompt(bound, label).startswith(prefix)


def test_the_rulings_are_the_authoritys_own_bytes(bound):
    """Served, not paraphrased - and the per-example consequences stay out."""
    served = F.owner_rulings(bound.package)
    assert served.startswith("OWNER RULINGS")
    assert "12." in served and "1." in served
    for anecdote in ("CASMX", "MCD", "ULTA", "Boeing", "BBW", "CLASS-WIDE"):
        assert anecdote not in served, anecdote


def test_the_varying_input_is_last_and_below_the_boundary(bound):
    label = F.correction_labels(bound)[0]
    p = F.correction_prompt(bound, label)
    assert p.count("[BOUNDARY]") == 1
    for key in ("original_final_shard", "original_open_issues"):
        assert p.index(key) > p.index("[BOUNDARY]"), key
    assert p.index("[OWNER RULINGS]") < p.index("[BOUNDARY]")
    assert p.rstrip().endswith("}")


def test_the_old_reply_arrives_as_an_untrusted_lead(bound):
    label = F.correction_labels(bound)[0]
    _sh, raws, _b = F.accepted_shards(bound.events, bound)
    p = F.correction_prompt(bound, label)
    assert K._sha(raws[label]) in p
    assert "a4_final_v1_reply" in p


@pytest.mark.parametrize("what", ["rulings", "source", "original_shard"])
def test_every_prompt_input_drift_changes_the_prompt(bound, monkeypatch, what):
    label = F.correction_labels(bound)[0]
    before = F.correction_prompt(bound, label)
    F.owner_rulings.cache_clear()
    if what == "rulings":
        monkeypatch.setattr(F, "owner_rulings", lambda d: "DIFFERENT\n")
    elif what == "source":
        real = F.payload
        monkeypatch.setattr(F, "payload",
                            lambda *a: dict(real(*a), drifted=True))
    else:
        real = F.accepted_shards

        def drifted(event_dir, b):
            sh, raws, bad = real(event_dir, b)
            raws[label] = raws[label] + " "
            return sh, raws, bad

        monkeypatch.setattr(F, "accepted_shards", drifted)
    assert F.correction_prompt(bound, label) != before
    F.owner_rulings.cache_clear()


def test_a_changed_ruling_file_refuses_the_package(pkg, tmp_path):
    own = str(tmp_path / "own")
    F.build(own, EV, HRR, FIXR)
    assert F.package_problems(own, EV, HRR, FIXR) == []
    doc = K._load(os.path.join(own, F.MANIFEST_NAME))
    assert "owner_rulings" in doc["bound"]
    doc["bound"]["owner_rulings"] = "0" * 64
    io.open(os.path.join(own, F.MANIFEST_NAME), "w",
            encoding="utf-8").write(json.dumps(doc))
    assert F.package_problems(own, EV, HRR, FIXR) != []


def test_the_correction_launcher_keeps_the_released_transport_bytes(bound):
    label = F.correction_labels(bound)[0]
    task = F._task_by_label(EV, label)
    base = F.render_launcher(task, EV, HRR, FIXR, 1).split("\n")
    mine = F.render_correction_launcher(bound, label, 1).split("\n")
    keep = [l for l in base
            if l.strip().startswith(("model:", "agentType:",
                                     "disallowedTools:", "effort:"))
            or l.strip() in ("let text = null", "try {", "  })",
                             "} catch (e) { text = null }")]
    assert len(keep) >= 4
    for line in keep:
        assert line in mine, line


# ================================================================= budget ==
def test_the_budget_is_derived_from_this_schedule(bound):
    b = F.correction_budget(bound)
    n = len(F.correction_labels(bound))
    assert b["planned_corrections"] == n
    assert b["planned_total"] == n + 1
    assert b["worst_case_after"] == b["before"] + (n + 1) * F.MAX_ATTEMPTS
    assert b["phase_ceiling"] == b["worst_case_after"]
    assert F.correction_budget_problems(bound) == []


def test_a_breach_of_the_global_ceiling_refuses(bound, tmp_path, monkeypatch):
    monkeypatch.setattr(F, "GLOBAL_CEILING", 10)
    assert F.correction_budget_problems(bound) != []
    _out, got = _prepare(tmp_path, bound)
    assert not got["ok"] and got["invocations"] == []


# ==================================== the correction run, composition, gate ==
@pytest.fixture
def official(tmp_path, monkeypatch):
    session = tmp_path / "projects" / K.PARENT_SESSION
    (session / "workflows").mkdir(parents=True)
    real = F.HR.AUD._official_location

    def located(path):
        p = os.path.realpath(str(path))
        if p.startswith(os.path.realpath(str(session))):
            return str(session), K.PARENT_SESSION
        return real(path)

    monkeypatch.setattr(F.HR.AUD, "_official_location", located)
    return session


def build_correction_call(session, bound, label, answer, attempt=1,
                          run_id=None, agent=None, script=None,
                          doc_mutate=None, rec_mutate=None):
    """One lawful official correction call: state and transcript that agree."""
    run_id = run_id or ("wfc_" + label.replace("/", "_").replace("#", "_"))
    agent = agent or ("agent_" + run_id)
    prompt, want = F._correction_context(bound, label, attempt)
    task = F._task_by_label(EV, label)
    recs = [
        {"type": "user", "uuid": "u0_" + run_id, "parentUuid": None,
         "agentId": agent, "sessionId": K.PARENT_SESSION,
         "message": {"role": "user", "content": prompt}},
        {"type": "assistant", "uuid": "u1_" + run_id, "parentUuid": "u0_" + run_id,
         "agentId": agent, "sessionId": K.PARENT_SESSION, "effort": K.EFFORT,
         "requestId": "req_" + run_id,
         "message": {"role": "assistant", "id": "msg_" + run_id,
                     "model": K.RUNTIME_MODEL_ID, "stop_reason": "end_turn",
                     "content": [{"type": "text", "text": answer}]}}]
    if rec_mutate:
        rec_mutate(recs)
    tdir = session / "subagents" / "workflows" / run_id
    tdir.mkdir(parents=True, exist_ok=True)
    with io.open(str(tdir / ("agent-%s.jsonl" % agent)), "w",
                 encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    doc = {"runId": run_id, "status": "completed", "totalToolCalls": 0,
           "script": script if script is not None else want,
           "workflowProgress": [{"type": "workflow_agent", "state": "done",
                                 "label": label, "agentId": agent,
                                 "model": K.RUNTIME_MODEL_ID,
                                 "agentType": K.AGENT_TYPE, "toolCalls": 0}],
           "result": {"source_id": label, "event_index": task["event_index"],
                      "rows": list(task["rows"]), "attempt": attempt,
                      "model": K.MODEL, "effort": K.EFFORT,
                      "agentType": K.AGENT_TYPE, "text": answer}}
    if doc_mutate:
        doc_mutate(doc)
    path = session / "workflows" / ("%s.json" % run_id)
    io.open(str(path), "w", encoding="utf-8").write(json.dumps(doc))
    return str(path)


@pytest.fixture(scope="module")
def clean_answers():
    """SCAFFOLDING, NOT EVIDENCE: gate-clean shards for the 32 affected events,
    built by the fixture the event battery already uses. The real corrections
    come from the 32 paid calls, which have not run."""
    return T8.gate_clean_answers(F.event_tasks(EV))


def run_corrections(tmp_path, session, bound, answers=None, skip=(),
                    mutate=None):
    out, got = _prepare(tmp_path, bound)
    assert got["ok"], got["problems"]
    for label in F.correction_labels(bound):
        if label in skip:
            continue
        kw = mutate(label) if mutate else {}
        F.record_state(out, build_correction_call(
            session, bound, label, (answers or {})[label], **kw))
    return out, F.finalize(out, bound)


def test_a_lawful_correction_phase_proves_and_composes(bound, tmp_path,
                                                       official,
                                                       clean_answers):
    out, doc = run_corrections(tmp_path, official, bound, clean_answers)
    assert doc["problems"] == []
    assert doc["ledger"]["valid"] == 32
    assert doc["retry"] == []
    b2 = bound._replace(corrections=out)
    shards, raws, origins, bad = F.corrected_shards(b2)
    assert bad == []
    assert len(shards) == 36
    assert sum(1 for o in origins.values() if o == "a4_final_v2_correction") == 32
    assert sum(1 for o in origins.values() if o == "a4_final_v1") == 4
    assert list(shards) == [t["source_id"] for t in F.event_tasks(EV)]
    ex = F.exhibit(b2)
    assert ex["replaced"] == 32 and ex["kept_original"] == 4
    assert len(ex["events"]) == 36 and ex["problems"] == []


def test_a_missing_correction_refuses_the_composition(bound, tmp_path,
                                                      official, clean_answers):
    gone = F.correction_labels(bound)[0]
    out, _doc = run_corrections(tmp_path, official, bound, clean_answers,
                                skip=(gone,))
    b2 = bound._replace(corrections=out)
    _s, _r, _o, bad = F.corrected_shards(b2)
    assert any("no accepted correction" in x for x in bad)


def test_an_unaffected_event_cannot_be_corrected(bound, tmp_path, official,
                                                 clean_answers, monkeypatch):
    """A clean event has no lawful replacement: composing one refuses."""
    out, _doc = run_corrections(tmp_path, official, bound, clean_answers)
    b2 = bound._replace(corrections=out)
    real = F.correction_labels
    monkeypatch.setattr(F, "correction_labels",
                        lambda b: [l for l in real(b)][:-1])
    _s, _r, _o, bad = F.corrected_shards(b2)
    assert any("never had an open issue" in x for x in bad)


def test_the_composed_gate_passes_and_keeps_every_floor(bound, tmp_path,
                                                        official,
                                                        clean_answers):
    out, _doc = run_corrections(tmp_path, official, bound, clean_answers)
    b2 = bound._replace(corrections=out)
    gate = F.signing_gate(bound.events, b2)
    assert gate["ok"], gate["stops"]
    c = gate["counts"]
    assert c["rows_accounted"] == 196 and c["events_accounted"] == 36
    assert c["open_issues"] == 0
    for tag, n in c["distinct_rows_per_tag"].items():
        assert n >= F.BIR.CLASS_FLOOR, (tag, n)
    assert c["sequential_rows"] >= F.BIR.SEQUENTIAL_FLOOR


@pytest.mark.parametrize("what", [
    "unresolved_issue", "semantic_duplicate", "class_floor", "v1_receipt",
    "v1_finalization"])
def test_every_gate_regression_refuses(bound, tmp_path, official,
                                       clean_answers, monkeypatch, what):
    out, _doc = run_corrections(tmp_path, official, bound, clean_answers)
    b2 = bound._replace(corrections=out)
    assert F.signing_gate(bound.events, b2)["ok"]
    if what == "unresolved_issue":
        real = F.accepted_shards

        def leftover(event_dir, b):
            sh, raws, bad = real(event_dir, b)
            if event_dir == out:
                k = sorted(sh)[0]
                sh[k] = dict(sh[k], open_issues=[{"what": "x", "why": "y"}])
            return sh, raws, bad

        monkeypatch.setattr(F, "accepted_shards", leftover)
        expect = "still carry an open issue"
    elif what == "semantic_duplicate":
        real = F.materialize

        def duped(evidence_dir, shards):
            key, side, probs = real(evidence_dir, shards)
            sid = [s for s in key if key[s]][0]
            key[sid] = list(key[sid]) + [key[sid][0]]
            return key, side, probs

        monkeypatch.setattr(F, "materialize", duped)
        expect = "semantic duplicates"
    elif what == "class_floor":
        monkeypatch.setattr(F.BIR, "CLASS_FLOOR", 999)
        expect = "below the floor"
    else:
        name = (K.RECEIPT_NAME if what == "v1_receipt"
                else K.FINALIZATION_NAME)
        io.open(os.path.join(bound.events, name), "a",
                encoding="utf-8").write(" ")
        expect = "changed"
    gate = F.signing_gate(bound.events, b2)
    assert not gate["ok"]
    assert any(expect in s for s in gate["stops"]), gate["stops"]


def test_a_metric_and_its_surprise_twin_are_not_a_duplicate(bound):
    """Codex SEQ 1383 ruling 9: the twin is a distinct fact, not a dedupe."""
    home = {"fact_type": "metric", "item": {"driver_name": "x",
                                            "driver_state": "increased"}}
    twin = {"fact_type": "surprise", "item": {"driver_name": "x",
                                              "driver_state": "beat"}}
    assert F._semantic_identity(home) != F._semantic_identity(twin)


def test_the_duplicate_check_ignores_only_locator_and_review_metadata(bound):
    """Ruling 10: exact normalized semantic records, never near-duplicates."""
    a = {"fact_type": "metric", "item": {"driver_name": "x"},
         "citation": {"quote": "one place"}, "part_ref": "p1"}
    b = {"fact_type": "metric", "item": {"driver_name": "x"},
         "citation": {"quote": "another place"}, "part_ref": "p9"}
    c = {"fact_type": "metric", "item": {"driver_name": "y"},
         "citation": {"quote": "one place"}, "part_ref": "p1"}
    assert F._semantic_identity(a) == F._semantic_identity(b)
    assert F._semantic_identity(a) != F._semantic_identity(c)


@pytest.mark.parametrize("kw,word", [
    ({"script": "// not the derived correction"}, "correction bytes"),
    ({"doc_mutate": lambda d: d["result"].__setitem__("model", "other")},
     "model"),
    ({"doc_mutate": lambda d: d.__setitem__("totalToolCalls", 1)}, "tool"),
])
def test_every_correction_evidence_mutation_refuses(bound, tmp_path, official,
                                                    clean_answers, kw, word):
    label = F.correction_labels(bound)[0]
    out, got = _prepare(tmp_path, bound)
    assert got["ok"]
    F.record_state(out, build_correction_call(
        official, bound, label, clean_answers[label], **kw))
    receipt = K._load(os.path.join(out, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(out, bound, receipt)
    assert problems != [], word


def test_only_invalid_bytes_buy_one_fresh_child_and_no_successor(
        bound, tmp_path, official, clean_answers):
    bad = F.correction_labels(bound)[0]
    answers = dict(clean_answers)
    answers[bad] = "{not json"
    out, doc = run_corrections(tmp_path, official, bound, answers)
    assert doc["retry"] == [bad]
    child = os.path.join(out, "retry")
    receipt = K._load(os.path.join(child, K.RECEIPT_NAME))
    assert receipt["allowed"] == [bad] and receipt["attempt"] == F.MAX_ATTEMPTS
    assert receipt["prompts"][bad] == \
        K._load(os.path.join(out, K.RECEIPT_NAME))["prompts"][bad]
    assert F.receipt_problems(child, bound, receipt) == []
    F.record_state(child, build_correction_call(
        official, bound, bad, "{still not json", attempt=F.MAX_ATTEMPTS,
        run_id="wfc_child_" + bad.replace("#", "_").replace("/", "_")))
    doc2 = F.finalize(child, bound)
    assert doc2["retry"] == []
    assert not os.path.isdir(os.path.join(child, "retry"))


def test_a_child_that_reuses_a_parent_identity_refuses(bound, tmp_path,
                                                       official,
                                                       clean_answers):
    bad = F.correction_labels(bound)[0]
    answers = dict(clean_answers)
    answers[bad] = "{not json"
    out, doc = run_corrections(tmp_path, official, bound, answers)
    child = os.path.join(out, "retry")
    runs, agents, msgs, reqs = F._spent_identities(out)
    F.record_state(child, build_correction_call(
        official, bound, bad, clean_answers[bad], attempt=F.MAX_ATTEMPTS,
        run_id="wfc_fresh_child", agent=sorted(agents)[0]))
    receipt = K._load(os.path.join(child, K.RECEIPT_NAME))
    _proved, problems = F.run_evidence(child, bound, receipt)
    assert any("already spent" in p for p in problems), problems
