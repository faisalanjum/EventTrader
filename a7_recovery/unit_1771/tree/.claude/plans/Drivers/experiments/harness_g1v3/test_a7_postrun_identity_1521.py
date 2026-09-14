# -*- coding: utf-8 -*-
"""THE POST-RUN LIFECYCLE SEAM (Codex SEQ 1521, hardened SEQ 1522).

A6 is a PRE-LAUNCH guard: `freeze()` reflects the live run, so once a run has
lawfully executed its zeros, receipt-file hash and completed ledger differ from
the accepted pre-call freeze. Three defects followed:

  1. `a7_prepared_run.current(run, accepted_hash)` refused a completed run
     because the live re-derived A6 bytes no longer equal the accepted pre-call
     freeze - the identity pin compared the executed doc, not the run's accepted
     pre-launch identity.
  2. `freeze()` subtracted EVERY post-lock call from the primary schedule. With
     P completed primary calls and R completed retry calls that is P-(P+R) = -R,
     a negative plan that hides the retry spend from `producer_primary_after`
     (Codex SEQ 1522 item 1). Only the validated PRIMARY calls are subtracted
     now; a completed retry stays in `completed_actual` and is never subtracted
     from primary work twice.
  3. `precall_view` rendered the receipt with its own `json.dumps`, a second
     serializer beside raw_transport's receipt writer. Both now share the ONE
     `raw_transport.receipt_bytes` (Codex SEQ 1522 item 2).

The fix keeps every immutable launch binding pinned to the exact accepted
freeze, while the post-run ledger counts the returned producer calls exactly
once and never as a future plan.
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

import a6_launch_freeze as _A6                                   # noqa: E402,F401
import a7_conservation as C                                     # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g23_run as R                                           # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402
import build_a5_exp5_kit as A5                                   # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import raw_transport as RT                                       # noqa: E402

#: the live, finalized A7 primary producer run and its accepted pre-call freeze
COMPLETED_RUN = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
                 "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a6_a5run_1515")
ACCEPTED = "4123bb693f6b040af48f4ea53c533b2ad800e80102113844adb5afc69c65052d"
#: baseline (closed A4 lock) and the run's producer calls
BASELINE = 5220
PRODUCER = 392
AFTER = BASELINE + PRODUCER          # 5612, counted once
CEILING = 6000

_needs_run = pytest.mark.skipif(
    not os.path.isfile(os.path.join(COMPLETED_RUN, "finalization.json")),
    reason="the finalized producer run is absent")


def _freeze_sha(run):
    """The accepted A6 freeze hash the operator supplies: the run's PRE-LAUNCH
    view - what `load` pins - a no-op before execution (Codex SEQ 1521)."""
    a6 = G._a6()
    return hashlib.sha256(
        a6.render(a6.precall_view(a6.freeze(run), run)).encode("utf-8")).hexdigest()


def _fresh(tmp_path, name="v3"):
    run = str(tmp_path / name)
    assert A5.prepare(run)["ok"]
    return run


# ============================================================ 1. THE RED
@_needs_run
def test_completed_run_loads_against_accepted_freeze_and_reports_5612_once():
    """THE DEFECT: a completed run must still pin to its exact accepted pre-call
    freeze, and its ledger must read its producer calls once (5612), never as a
    future plan (6004)."""
    ident = PR.current(COMPLETED_RUN, ACCEPTED)
    assert ident["a6_freeze_sha256"] == ACCEPTED
    assert ident["scheduled_calls"] == PRODUCER
    # the immutable launch bindings are still the accepted ones
    assert ident["a4_lock_sha256"] == A5.A4_LOCK_SHA
    assert ident["corrected_inventory_sha256"] == hashlib.sha256(
        io.open(A5.CORRECTED_INVENTORY_PATH, "rb").read()).hexdigest()
    # the ledger counts the returned producer calls exactly once
    total, rows = G._a6().ledger(COMPLETED_RUN)
    assert total == AFTER
    assert total == sum(r["calls"] for r in rows)
    assert [r["stage"] for r in rows] == ["a4_final_key", "current_producer_primary"]


# ================================== 2. retry accounting counts primary once
@_needs_run
def test_completed_run_freeze_budget_counts_once_not_as_future_plan():
    """`freeze()` on a completed run must not re-add the returned calls as a
    plan: producer_primary_after is 5612, under the ceiling - never 6004."""
    b = G._a6().freeze(COMPLETED_RUN)["budget"]
    assert b["producer_primary_after"] == AFTER
    assert b["planned_producer_primary"] == 0      # nothing left to schedule
    assert b["under_ceiling"] is True
    # the grader's own reading (planned = 0 more) agrees
    gb = G._a6().budget(0, COMPLETED_RUN)
    assert gb["producer_primary_after"] == AFTER and gb["under_ceiling"] is True


def _row(stage, calls):
    return collections.OrderedDict([("stage", stage), ("calls", calls)])


def _rows(primary=None, retry=None):
    """A synthetic ledger: the closed baseline, plus this run's own validated
    primary/retry rows - the exact shape `ledger()` returns."""
    out = [_row("a4_final_key", BASELINE)]
    if primary is not None:
        out.append(_row("current_producer_primary", primary))
    if retry is not None:
        out.append(_row("current_producer_retry", retry))
    return out


def test_inmemory_zero_completed_primary_owes_the_whole_schedule():
    rows = _rows()                                  # nothing spent yet
    assert _A6._remaining_primary(PRODUCER, rows) == PRODUCER
    b = _A6.budget(PRODUCER, measured=(BASELINE, rows))
    assert b["completed_actual"] == BASELINE
    assert b["producer_primary_after"] == AFTER and b["under_ceiling"] is True


def test_inmemory_completed_primary_without_retry_owes_nothing():
    rows = _rows(primary=PRODUCER)
    assert _A6._remaining_primary(PRODUCER, rows) == 0
    b = _A6.budget(0, measured=(AFTER, rows))
    assert b["completed_actual"] == AFTER
    assert b["producer_primary_after"] == AFTER and b["under_ceiling"] is True


def test_inmemory_completed_primary_plus_retry_preserves_retry_and_owes_zero():
    """The class fix: a completed retry stays counted and never reduces primary
    twice. Remaining primary is 0 and the retry spend survives in the total."""
    retry = 7
    rows = _rows(primary=PRODUCER, retry=retry)
    completed = AFTER + retry                        # baseline + primary + retry
    assert _A6._remaining_primary(PRODUCER, rows) == 0        # owes zero primary
    b = _A6.budget(0, measured=(completed, rows))
    assert b["completed_actual"] == completed        # retry preserved, once
    assert b["producer_primary_after"] == completed  # never hidden as -R


def test_inmemory_impossible_over_schedule_primary_refuses():
    """More validated primary than the schedule is impossible and refuses,
    rather than returning a negative plan (Codex SEQ 1522 item 1)."""
    rows = _rows(primary=PRODUCER + 1)
    with pytest.raises(ValueError) as e:
        _A6._remaining_primary(PRODUCER, rows)
    assert "above the %d-call primary schedule" % PRODUCER in str(e.value)


# ================================================= 3. the refusals still refuse
def test_a_fresh_zero_call_run_loads_against_its_own_freeze(tmp_path):
    """The accepted zero-call control still holds: a prepared, unexecuted run
    loads against its own freeze hash, and its budget is baseline + full plan."""
    run = _fresh(tmp_path)
    ident = PR.current(run, _freeze_sha(run))
    assert ident["scheduled_calls"] == PRODUCER and ident["executed"] is None
    b = G._a6().freeze(run)["budget"]
    assert b["completed_actual"] == BASELINE
    assert b["producer_primary_after"] == AFTER and b["under_ceiling"] is True


@_needs_run
def test_omitted_or_wrong_freeze_hash_refuses():
    with pytest.raises(ValueError) as e1:
        PR.current(COMPLETED_RUN)
    assert "requires the accepted A6 freeze hash" in str(e1.value)
    with pytest.raises(ValueError) as e2:
        PR.current(COMPLETED_RUN, "0" * 64)
    assert "not the required" in str(e2.value)


def test_a_substituted_run_refuses_against_the_accepted_hash(tmp_path):
    other = _fresh(tmp_path)
    assert _freeze_sha(other) != ACCEPTED
    with pytest.raises(ValueError):
        PR.current(other, ACCEPTED)


@_needs_run
def test_a_changed_receipt_refuses(tmp_path):
    """A DIRECT receipt mutation: an extra top-level key breaks the exact run
    contract, so the copy no longer counts as the accepted run (Codex SEQ 1522
    item 3)."""
    copy_run = str(tmp_path / "crcpt")
    shutil.copytree(COMPLETED_RUN, copy_run)
    rp = os.path.join(copy_run, "receipt.json")
    rec = json.load(io.open(rp, encoding="utf-8"))
    rec["injected_field"] = 1
    # write through the ONE canonical serializer, so the injected key is the
    # only byte-meaning change under receipt_bytes (Codex SEQ 1523 item 4).
    io.open(rp, "wb").write(RT.receipt_bytes(rec))
    with pytest.raises(ValueError):
        PR.current(copy_run, ACCEPTED)


@_needs_run
def test_a_changed_finalization_refuses(tmp_path):
    """A copy whose finalization is corrupted no longer counts as the run."""
    copy_run = str(tmp_path / "cfin")
    shutil.copytree(COMPLETED_RUN, copy_run)
    fp = os.path.join(copy_run, "finalization.json")
    fin = json.load(io.open(fp, encoding="utf-8"))
    fin["ledger"] = dict(fin["ledger"], primary_valid=fin["ledger"]["primary_valid"] + 1)
    io.open(fp, "w", encoding="utf-8").write(json.dumps(fin, indent=1))
    with pytest.raises(ValueError):
        PR.current(copy_run, ACCEPTED)


@_needs_run
def test_a_changed_raw_tree_refuses(tmp_path):
    """A copy whose preserved raw bytes changed cannot count its spend."""
    copy_run = str(tmp_path / "craw")
    shutil.copytree(COMPLETED_RUN, copy_run)
    raw = os.path.join(copy_run, "raw")
    name = sorted(os.listdir(raw))[0]
    with io.open(os.path.join(raw, name), "ab") as fh:
        fh.write(b" ")
    with pytest.raises(ValueError):
        PR.current(copy_run, ACCEPTED)


def test_a_middle_state_run_refuses(tmp_path):
    """Saved answers but no finalization: neither uncalled nor complete."""
    mid = _fresh(tmp_path)
    os.makedirs(os.path.join(mid, "answers"))
    io.open(os.path.join(mid, "answers", "00000.json"), "w").write("{}")
    with pytest.raises(ValueError) as e:
        PR.load(mid)
    assert "no finalization" in str(e.value)


# ===================== 4. exact ceiling proof, through the one budget owner
def test_a_genuinely_derived_over_ceiling_future_budget_is_under_ceiling_false():
    """A GENUINE plan past the ceiling is derived as under_ceiling=False by the
    owner itself - not by hand-setting a field (Codex SEQ 1522 item 3)."""
    b = G._a6().budget(CEILING, None)               # baseline + a genuine 6000 plan
    assert b["producer_primary_after"] == BASELINE + CEILING
    assert b["producer_primary_after"] > b["global_abort_ceiling"]
    assert b["under_ceiling"] is False


@_needs_run
def test_re_adding_the_completed_392_yields_6004_and_breaches_the_ceiling():
    """Re-adding the completed producer calls as a fresh plan is exactly the
    class bug: it yields 6004 and is rejected FOR THAT CONDITION - the ceiling
    breach - not because some unrelated field differs (Codex SEQ 1522 item 3)."""
    b = G._a6().budget(PRODUCER, COMPLETED_RUN)     # 5612 completed + 392 re-added
    assert b["completed_actual"] == AFTER
    assert b["producer_primary_after"] == AFTER + PRODUCER == 6004
    assert b["under_ceiling"] is False


# ============== 5. G1 / conservation / preliminary G2-G3 inventories,
#                   derived twice, identical, every problem list empty
@_needs_run
def test_grading_inventories_derive_twice_identically_with_zero_problems(tmp_path):
    """RELATIONAL proof (Codex SEQ 1523): the inventories are not merely
    nonempty - every count is tied to another live-derived quantity, so an empty
    prompt map, empty population or a doctored count cannot pass. The final
    G2/G3 freeze is NOT called before G1 (its AAL_2026-04-23T08.30 gold-0
    failure correctly proves that dependency); only the PRELIMINARY populations
    are measured. None of these observed numbers is hardcoded."""
    ident = PR.current(COMPLETED_RUN, ACCEPTED)

    # THE ONE VALIDATED ANCHOR: this run's validated primary calls, read from
    # the ledger's own current_producer_primary row - never a literal.
    _total, _lrows = G._a6().ledger(COMPLETED_RUN)
    validated = sum(r["calls"] for r in _lrows
                    if r["stage"] == "current_producer_primary")
    assert validated > 0

    # materialization: nonempty, stable (a fresh meta each time), and its trace
    # is exactly one row per validated scheduled call.
    a = G.materialize(ident)
    b = G.materialize(ident)
    assert a == b and a[1] is not b[1]
    arms_a, meta_a, mprob_a = a
    assert mprob_a == []
    assert len(meta_a["trace"]) == validated

    # G1: nonempty doc, empty problems, identical content + prompt map twice;
    # the prompt map's size equals the document's derived batch count, and the
    # derived launcher count equals batches x lanes.
    doc1, pr1, gp1 = G.freeze(ident)
    doc2, pr2, gp2 = G.freeze(ident)
    assert doc1 is not None and gp1 == [] and gp2 == []
    assert doc1["budget"]["spent_before"] == AFTER  # reads the spend once (5612)
    assert pr1 and pr2                              # both prompt maps nonempty
    batches = doc1["batching"]["batches"]
    lanes = len(doc1["launchers"]["lanes"])
    assert len(pr1) == batches and len(pr2) == batches
    assert doc1["launchers"]["per_batch"] == lanes
    assert doc1["launchers"]["count"] == batches * lanes
    # the doc carries exact-decimal facts (Decimal("16.5")); one canonical
    # rendering both times.
    g1_doc_sha = hashlib.sha256(
        json.dumps(doc1, sort_keys=True, default=str).encode()).hexdigest()
    assert g1_doc_sha == hashlib.sha256(
        json.dumps(doc2, sort_keys=True, default=str).encode()).hexdigest()
    g1_prompt_sha = hashlib.sha256(
        json.dumps(pr1, sort_keys=True, default=str).encode()).hexdigest()
    assert g1_prompt_sha == hashlib.sha256(
        json.dumps(pr2, sort_keys=True, default=str).encode()).hexdigest()

    # conservation: equal AND nonempty, both problem lists empty; scheduled_calls
    # equals both the packet count and the validated schedule; branch_total
    # equals a nonzero branch-list length.
    cdoc_a, cprob_a = C.terminals(ident, str(tmp_path / "consv_a"))
    cdoc_b, cprob_b = C.terminals(ident, str(tmp_path / "consv_b"))
    assert cprob_a == [] and cprob_b == []
    assert cdoc_a == cdoc_b and cdoc_a
    assert cdoc_a["scheduled_calls"] == len(cdoc_a["packets"]) == validated
    assert cdoc_a["branch_total"] == len(cdoc_a["branches"]) > 0

    # preliminary G2/G3 populations: every semantic component of the two
    # derivations equal (the whole tuple), both maps nonempty, both problem
    # lists empty, and both unroutable lists EXACTLY empty.
    p_a = R.populations(ident, str(tmp_path / "g23_a"))
    p_b = R.populations(ident, str(tmp_path / "g23_b"))
    assert p_a == p_b                              # every semantic component
    g2, g3, pop_arms, _gd, _mt, pprob, unroutable, _dv = p_a
    assert g2 and g3                               # both group maps nonempty
    assert pprob == []
    assert unroutable == []                        # exactly empty

    # EXACT counts for the report (printed; captured under -s). g2_groups /
    # g3_groups are nonempty leg-event GROUPS across the population's legs;
    # population_legs = P1/P2/UNION; conservation_arms = the two CALLED producer
    # arms P1/P2 (UNION is derived, never called).
    print("\nINVENTORY_COUNTS validated_primary=%d trace=%d "
          "g1_batches=%d g1_prompts=%d launcher_lanes=%d launcher_count=%d "
          "conservation_scheduled=%d packets=%d branch_total=%d "
          "conservation_arms=%d conservation_problems=%d g1_problems=%d "
          "g2_groups=%d g3_groups=%d population_legs=%d "
          "population_problems=%d unroutable=%d"
          % (validated, len(meta_a["trace"]),
             batches, len(pr1), lanes, doc1["launchers"]["count"],
             cdoc_a["scheduled_calls"], len(cdoc_a["packets"]),
             cdoc_a["branch_total"], len(cdoc_a["arms"]), len(cprob_a), len(gp1),
             len(g2), len(g3), len(pop_arms), len(pprob), len(unroutable)))
