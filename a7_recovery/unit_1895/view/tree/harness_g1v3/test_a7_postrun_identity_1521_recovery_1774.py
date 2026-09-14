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
import a7_g1_build as G                                          # noqa: E402
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


@_needs_run
def test_omitted_or_wrong_freeze_hash_refuses():
    with pytest.raises(ValueError) as e1:
        PR.current(COMPLETED_RUN)
    assert "requires the accepted A6 freeze hash" in str(e1.value)
    with pytest.raises(ValueError) as e2:
        PR.current(COMPLETED_RUN, "0" * 64)
    assert "not the required" in str(e2.value)












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
