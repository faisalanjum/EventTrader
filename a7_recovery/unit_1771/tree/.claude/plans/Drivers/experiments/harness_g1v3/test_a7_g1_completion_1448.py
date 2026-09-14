"""RED-FIRST for the six connected completion/binding defects (Codex SEQ 1448).

Written before the fixes. Nothing here reads meaning from a reply; every
expectation is structural or derived from pinned evidence.
"""
import copy, glob, io, json, os, shutil, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import a7_g1_build as G
import a7_g1_complete_v2 as CV
import a7_prepared_run as _PR                                   # noqa: E402

#: THE run these proofs are about, named out loud. Nothing defaults to it.
RUN = _PR.load(G.PRIMARY)

#: HISTORICAL EVIDENCE. The only executed producer run is v1-era, so the
#: live era gate is relaxed for these structural proofs by the ONE named
#: fixture in conftest.py. See its docstring: when the fresh v3 run
#: exists, these must pass without it.
pytestmark = pytest.mark.usefixtures("historical_v1_evidence")
assert os.path.dirname(os.path.abspath(G.__file__)) == HERE, G.__file__

RUN3 = "/tmp/a7_g1_run3"


# ---- 1. the budget, DERIVED from pinned run3 evidence -----------------------
def test_prior_g1_calls_are_derived_from_the_frozen_run3_finalizations():
    calls, provenance = G.prior_g1_calls(RUN3)
    assert calls == 93
    assert len(provenance["files"]) == 26
    assert sum(f["scheduled"] for f in provenance["files"]) == 93
    for f in provenance["files"]:
        assert os.path.isfile(f["path"])
        assert f["sha256"] == G._sha_file(f["path"])


def test_the_candidate_budget_uses_the_derived_baseline(tmp_path):
    import json
    import a6_launch_freeze as A6
    doc, prompts, problems = G.freeze(RUN)
    assert problems == []
    b = doc["budget"]

    # NO FIXED TOTAL. `4932` was the ledger of an earlier round, so this test
    # pinned an answer the owners had already stopped giving. The budget is
    # RECONCILED instead: every term is re-measured from the raw artifacts it
    # claims, and the arithmetic is proved (Codex SEQ 1469 item 7).
    completed, rows = A6.ledger(G.run_of(RUN))
    assert completed == sum(r["calls"] for r in rows), (
        "the A6 ledger total is not the sum of its own provenance rows")
    for r in rows:
        if "finalization_sha256" in r:
            fin = os.path.join(r["run_dir"], "finalization.json")
            assert os.path.isfile(fin), fin
            assert G._sha_file(fin) == r["finalization_sha256"], (
                "%s: provenance names bytes that are not the live file"
                % r["stage"])
            with io.open(fin, encoding="utf-8") as fh:
                assert json.load(fh)["ledger"]["scheduled"] == r["calls"], (
                    "%s: the row's call count is not the artifact's" % r["stage"])

    # ONE OWNER. G1 no longer adds the producer, its retry or the prior
    # grading/probe totals on top: A6 reconciles every completed call once.
    assert b["spent_before"] == completed, (b["spent_before"], completed)
    stages = [r["stage"] for r in rows]
    for owed in ("producer_primary", "prior_grading_and_probes"):
        assert owed in stages, stages
    assert b["initial_grader_calls"] == len(doc["launchers"]["rows"])
    assert b["after_initial"] == b["spent_before"] + b["initial_grader_calls"]
    assert b["after_max"] == b["spent_before"] + b["max_grader_calls"]
    assert b["max_grader_calls"] == b["initial_grader_calls"] \
        * b["max_attempts_per_row"]
    assert b["under_ceiling"] is (b["after_max"] <= b["ceiling"])
    # THE PROVENANCE IS A6'S OWN ROWS. G1 no longer re-reads a second spend
    # owner, so what travels with the budget is what reconciled it.
    assert b["prior_g1_calls"] == rows, "provenance must travel with it"
    assert sum(r["calls"] for r in b["prior_g1_calls"]) == b["spent_before"]


# ---- 6. every decision owner is pinned --------------------------------------
def test_owner_hashes_pin_the_completion_and_scorer_owners():
    owners = G.owner_hashes()
    assert owners["a7_g1_complete_v2"] == G._sha_file(
        os.path.join(HERE, "a7_g1_complete_v2.py"))
    assert owners["score_exp5"] == G._sha_file(
        os.path.join(HERE, "scorers", "score_exp5.py"))


# ---- 4. confirmed vs one-lane-disputed duplicate structure ------------------
def test_a_disputed_one_gold_many_produced_is_NOT_a_confirmed_duplicate():
    """Codex's real case: lane A gold0->p0, lane B gold0->p0,p1."""
    doc = {"question_bindings": [], "launchers": {"lanes": ["G1a", "G1b"]}}
    a, b = {0: (0,)}, {0: (0, 1)}
    accepted, report = G.event_credit(a, b)
    assert accepted == {}
    comp = [c for c in report["components"]
            if c["kind"] == "one_gold_many_produced"]
    assert comp and comp[0]["contested"], "the extra edge is contested"
    assert G.confirmed_duplicate_groups(report) == [], \
        "a contested component must never be a confirmed duplicate"


def test_a_confirmed_one_gold_many_produced_IS_a_duplicate_group():
    a = b = {0: (0, 1)}
    accepted, report = G.event_credit(a, dict(b))
    assert accepted == {}
    got = G.confirmed_duplicate_groups(report)
    assert len(got) == 1 and got[0]["contested"] == []


# ---- 5. scorer problems must BLOCK ------------------------------------------
def test_a_scorer_problem_blocks_completion(monkeypatch):
    legs, totals, meta, arms, gold, probs = G.inventory(RUN)
    assert probs == []
    leg, sid = G.expected_groups(legs)[0]
    row = legs[leg][sid]
    doc, _p, _pr = G.freeze(RUN)
    rel = {g: () for g in row["unmatched_gold"]}
    bid = next(r["batch_id"] for r in doc["batch_rows"]
               if r["question_ids"][0] == G.question_id(leg, sid,
                                                        row["unmatched_gold"][0]))
    lanes = doc["launchers"]["lanes"]
    per_lane = {"%s/%s" % (bid, lanes[0]): rel,
                "%s/%s" % (bid, lanes[1]): dict(rel)}
    from scorers import score_exp5 as SCO
    monkeypatch.setattr(SCO, "grade_unmatched",
                        lambda *a, **k: ([], [{"sid": sid, "reason": "forced"}]))
    result, problems = CV.complete(doc, legs, per_lane)
    assert problems, "a scorer problem must reach the blocking return"
    assert any("forced" in json.dumps(p) for p in problems)


# ---- 2. the completion owner must be executable over a REAL run -------------
def test_the_completion_owner_exposes_a_run_evidence_entry_point():
    assert hasattr(CV, "evidence"), "no owner can turn a run into relations"


def test_attempt_selection_prefers_attempt_two_then_falls_back():
    assert CV.select_attempt({1: ({}, ["bad"]), 2: ({0: (5,)}, [])}) == (2, {0: (5,)})
    assert CV.select_attempt({1: ({0: (5,)}, []), 2: ({}, ["bad"])}) == (1, {0: (5,)})
    assert CV.select_attempt({1: ({}, ["x"]), 2: ({}, ["y"])}) is None


def test_complete_itself_never_reports_a_contested_group_as_confirmed():
    """CODEX'S OWN REPRODUCTION, asserted on `complete` - not on the helper.

    My first version of this check tested `confirmed_duplicate_groups` in
    isolation, so a mutation inside `complete` that bypassed it stayed green.
    This drives `complete`, which is where the defect actually lived.
    """
    legs, totals, meta, arms, gold, probs = G.inventory(RUN)
    assert probs == []
    leg, sid = "P1", "0000006201-26-000031"
    row = legs[leg][sid]
    doc, _p, _pr = G.freeze(RUN)
    g0 = row["unmatched_gold"][0]
    p0, p1 = row["unmatched_produced"][0], row["unmatched_produced"][1]
    bid = next(r["batch_id"] for r in doc["batch_rows"]
               if r["question_ids"][0] == G.question_id(leg, sid, g0))
    lanes = doc["launchers"]["lanes"]
    a = {g: () for g in row["unmatched_gold"]}
    a[g0] = (p0,)
    b = dict(a)
    b[g0] = tuple(sorted((p0, p1)))
    result, problems = CV.complete(doc, legs, {
        "%s/%s" % (bid, lanes[0]): a, "%s/%s" % (bid, lanes[1]): b})
    assert problems == [], problems
    cats = {k: v for k, v in result["terminal_counts"].items() if v}
    assert result["duplicate_emission_groups"] == [], \
        "a contested component must never reach the confirmed duplicate bar"
    disputed = result["disputed_identity_groups"]
    assert len(disputed) == 1
    assert disputed[0]["leg"] == leg and disputed[0]["source_id"] == sid
    assert disputed[0]["contested"], "and it is kept as unresolved evidence"


def test_complete_DOES_report_a_both_lane_confirmed_duplicate():
    legs, totals, meta, arms, gold, probs = G.inventory(RUN)
    leg, sid = "P1", "0000006201-26-000031"
    row = legs[leg][sid]
    doc, _p, _pr = G.freeze(RUN)
    g0 = row["unmatched_gold"][0]
    p0, p1 = row["unmatched_produced"][0], row["unmatched_produced"][1]
    bid = next(r["batch_id"] for r in doc["batch_rows"]
               if r["question_ids"][0] == G.question_id(leg, sid, g0))
    lanes = doc["launchers"]["lanes"]
    a = {g: () for g in row["unmatched_gold"]}
    a[g0] = tuple(sorted((p0, p1)))
    result, problems = CV.complete(doc, legs, {
        "%s/%s" % (bid, lanes[0]): a, "%s/%s" % (bid, lanes[1]): dict(a)})
    assert problems == [], problems
    assert len(result["duplicate_emission_groups"]) == 1
    assert result["duplicate_emission_groups"][0]["contested"] == []
    assert result["disputed_identity_groups"] == []
