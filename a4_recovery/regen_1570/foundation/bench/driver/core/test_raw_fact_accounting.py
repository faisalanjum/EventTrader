"""RAW-ITEM -> FACT ACCOUNTING (owner-approved B2/C1, reviewer SEQ 973).

THE LAW THESE TESTS PIN, and nothing wider:

  * a raw item's ZERO-BASED POSITION in the one ordered event request is its only
    reference — no minted id, uuid, hash or content match;
  * provenance stays OUTSIDE PreparedFactV2 (the 5+32 model contract is not
    touched): the run boundary carries the smallest parallel relation
    `prepared_fact_position -> raw_index`, plus the raw count, because a missing
    TAIL raw item is invisible to the relation alone;
  * public rows keep the EXISTING five fields and `index` means the RAW position.
    A lawful split returns SEVERAL flat rows with the SAME index — no aggregate
    word, no winner, no severity order;
  * zero produced facts for a raw item gets EXACTLY ONE typed terminal from the
    existing reason owner — never "everything empty is skipped";
  * fusion (C1) gives every distinct contributing raw index the SAME final
    fact_id and decision, and two fragments of ONE raw item fuse to ONE row, not
    a duplicate;
  * every raw index is linked to >=1 fact row OR has exactly one terminal; every
    fact has >=1 raw origin; anything else is a LOUD internal failure and never a
    fabricated public outcome.

These run through the PUBLIC orchestration entry `run_event`, not a helper, so
they cannot pass against an internal shortcut that the public path does not have.
"""
from decimal import Decimal

import pytest

from driver.core.driver_write_cli import _item, run_event
from driver.core.prepared_fact import RunInputV1
from driver.core.test_driver_write_cli import SRC, FakeStore, fact


def _run(tmp_path, facts, **kw):
    """The public path, with the accounting relation supplied by the caller."""
    store = FakeStore(source=kw.pop("store_source")) if "store_source" in kw \
        else FakeStore()
    ri = RunInputV1.from_dict({"source_id": SRC, "facts": facts})
    return run_event(ri, store=store, audit_dir=str(tmp_path), **kw)


def _rows(res):
    return res["items"]


def _by_index(res):
    out = {}
    for r in _rows(res):
        out.setdefault(r["index"], []).append(r)
    return out


# A different PERIOD makes a genuinely different fact id, so two prepared facts
# from one raw item are a real SPLIT rather than two spellings of one fact.
def _other_period():
    return fact(period_start_date="2025-03-30", period_end_date="2025-06-28",
                fiscal_quarter=2)


# ---------------------------------------------------------------- A ----------
# ---------------------------------------------------------------- C ----------
def test_C_one_raw_item_one_fact_is_one_row_at_that_raw_index(tmp_path):
    res = _run(tmp_path, [fact()], raw_origin=(0,), n_raw=1)
    rows = _rows(res)
    assert len(rows) == 1 and rows[0]["index"] == 0


# ---------------------------------------------------------------- D ----------
def test_D_a_lawful_split_returns_TWO_rows_at_the_SAME_raw_index(tmp_path):
    """FINAL_DESIGN proves a split is real: one stated value on two bases is two
    facts. Neither may be lost, and neither may be collapsed into the other."""
    res = _run(tmp_path, [fact(), _other_period()], raw_origin=(0, 0), n_raw=1)
    by = _by_index(res)
    assert set(by) == {0}, by
    assert len(by[0]) == 2, f"the split lost a result: {by[0]}"
    assert len({r["fact_id"] for r in by[0]}) == 2, "the two facts collapsed into one"


# ---------------------------------------------------------------- E ----------
def test_E_mixed_split_results_stay_BOTH_visible_with_no_worst_collapse(tmp_path):
    """An accepted fact and a refused fact from ONE raw item must BOTH appear.
    A single 'worst' word would hide the accepted half."""
    bad = _other_period()
    # a refusal the EXISTING owner types mid-pipeline (a blank quote is refused
    # at input parse instead, which would never reach the accounting seam)
    # a same-day duration is refused MID-PIPELINE (PERIOD_UNRESOLVED), so it
    # reaches the accounting seam as a fact result — a blank quote or a bad unit
    # would be refused at parse and never get here
    bad["period_start_date"] = bad["period_end_date"]
    res = _run(tmp_path, [fact(), bad], raw_origin=(0, 0), n_raw=1)
    by = _by_index(res)
    assert len(by.get(0, [])) == 2, f"a mixed split was collapsed: {by}"
    assert len({r["decision"] for r in by[0]}) == 2, \
        f"both branches reported the same decision — collapse: {by[0]}"


# ---------------------------------------------------------------- F ----------
def test_F_fusion_gives_EVERY_contributing_raw_index_the_same_fact_and_decision(tmp_path):
    """C1: never designate a winner."""
    res = _run(tmp_path, [fact(), fact()], raw_origin=(0, 1), n_raw=2)
    by = _by_index(res)
    assert set(by) == {0, 1}, by
    assert len({r["fact_id"] for rs in by.values() for r in rs}) == 1
    assert len({r["decision"] for rs in by.values() for r in rs}) == 1


# ---------------------------------------------------------------- I ----------
def test_I_two_fragments_of_ONE_raw_item_that_fuse_emit_ONE_row_not_a_duplicate(tmp_path):
    res = _run(tmp_path, [fact(), fact()], raw_origin=(0, 0), n_raw=1)
    by = _by_index(res)
    assert set(by) == {0}, by
    assert len(by[0]) == 1, f"the fused fragments duplicated the raw row: {by[0]}"


# ---------------------------------------------------------------- H ----------
def test_H_byte_identical_raw_items_are_accounted_by_POSITION_never_by_content(tmp_path):
    """Two identical raw items at different positions are two raw items. Joining
    them by content would silently drop one from the ledger."""
    res = _run(tmp_path, [fact(), fact()], raw_origin=(0, 1), n_raw=2)
    assert set(_by_index(res)) == {0, 1}, "identical raw items were content-joined"


# ---------------------------------------------------------------- G ----------
def test_G_one_raw_splits_one_branch_fuses_with_a_second_raw_the_other_stays(tmp_path):
    """raw 0 -> two facts; one of them fuses with raw 1's fact; the other branch
    stays separate. Raw 0 must show BOTH, raw 1 must show the fused one."""
    res = _run(tmp_path, [fact(), _other_period(), fact()],
               raw_origin=(0, 0, 1), n_raw=2)
    by = _by_index(res)
    assert set(by) == {0, 1}, by
    assert len(by[0]) == 2, f"raw 0 lost a branch: {by[0]}"
    fused_id = by[1][0]["fact_id"]
    assert fused_id in {r["fact_id"] for r in by[0]}, \
        "the fused branch did not reach both of its raw origins"


# ---------------------------------------------------------------- B ----------
def test_B_a_raw_item_that_produced_NO_fact_gets_exactly_one_typed_terminal(tmp_path):
    """Zero facts is not automatically `skipped`: the supplied terminal is the
    existing reason owner's word, and it appears exactly once."""
    terminal = {"index": 1, "fact_id": None, "decision": "parked",
                "codes": ["SOURCE_UNAVAILABLE"], "detail": "evidence gap"}
    res = _run(tmp_path, [fact()], raw_origin=(0,), n_raw=2,
               raw_terminals=(terminal,))
    by = _by_index(res)
    assert set(by) == {0, 1}, by
    assert len(by[1]) == 1 and by[1][0]["decision"] == "parked"
    assert by[1][0]["codes"] == ["SOURCE_UNAVAILABLE"]


def test_B_zero_fact_terminals_are_NOT_forced_to_skipped(tmp_path):
    """The lawful control for the test above: a rejected zero-fact item stays
    rejected. Converting every zero to `skipped` loses retryability."""
    terminal = {"index": 0, "fact_id": None, "decision": "rejected",
                "codes": ["XBRL_CONTRACT_INVALID"], "detail": "malformed"}
    res = _run(tmp_path, [], raw_origin=(), n_raw=1, raw_terminals=(terminal,))
    rows = _rows(res)
    assert len(rows) == 1 and rows[0]["decision"] == "rejected"


# ---------------------------------------------------------------- K ----------
@pytest.mark.parametrize("origin,n_raw,why", [
    ((0,), 2, "raw 1 is never covered and no terminal explains it"),
    ((0, 5), 2, "raw 5 is out of range"),
    ((0, -1), 2, "a negative raw index"),
    ((0, True), 2, "a bool is not an exact int"),
    ((0, "1"), 2, "a string is not an exact int"),
    ((), 1, "a produced fact has no raw origin at all"),
])
def test_K_origin_attacks_fail_LOUDLY_and_never_as_a_public_outcome(
        tmp_path, origin, n_raw, why):
    facts = [fact() for _ in range(max(len(origin), 1))]
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, facts, raw_origin=origin, n_raw=n_raw)
    # A TypeError for an unknown keyword would let this attack pass while the
    # real guard does not exist — the vacuous-catch class. It must be the
    # ACCOUNTING check that refuses, not the signature.
    assert "raw accounting:" in str(exc.value), \
        f"{why}: refused by something OTHER than the accounting guard: "\
        f"{type(exc.value).__name__}: {exc.value}"


def test_K_a_raw_index_with_BOTH_a_fact_and_a_terminal_is_contradictory(tmp_path):
    terminal = {"index": 0, "fact_id": None, "decision": "skipped",
                "codes": ["SOURCE_UNAVAILABLE"], "detail": "abstained"}
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [fact()], raw_origin=(0,), n_raw=1,
             raw_terminals=(terminal,))
    assert "BOTH a produced fact" in str(exc.value), \
        f"refused for the wrong reason: {exc.value}"


def test_K_a_duplicated_terminal_for_one_raw_index_is_LOUD(tmp_path):
    t = {"index": 0, "fact_id": None, "decision": "skipped",
         "codes": ["SOURCE_UNAVAILABLE"], "detail": "abstained"}
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [], raw_origin=(), n_raw=1, raw_terminals=(t, dict(t)))
    assert "more than one terminal" in str(exc.value), \
        f"refused for the wrong reason: {exc.value}"


def test_K_the_lawful_control_for_every_attack_above_still_passes(tmp_path):
    """Without a lawful control an attack suite can pass by refusing everything."""
    res = _run(tmp_path, [fact(), fact()], raw_origin=(0, 1), n_raw=2)
    assert set(_by_index(res)) == {0, 1}


# ---------------------------------------------------------------- L ----------
def test_L_the_same_request_twice_gives_identical_rows_and_fact_ids(tmp_path):
    a = _run(tmp_path, [fact(), _other_period()], raw_origin=(0, 0), n_raw=1)
    b = _run(tmp_path, [fact(), _other_period()], raw_origin=(0, 0), n_raw=1)
    assert _rows(a) == _rows(b)


def test_L_a_permutation_keeps_the_same_facts_after_remapping_raw_positions(tmp_path):
    """Order must not change WHICH fact belongs to WHICH raw item."""
    straight = _run(tmp_path, [fact(), _other_period()],
                    raw_origin=(0, 1), n_raw=2)
    swapped = _run(tmp_path, [_other_period(), fact()],
                   raw_origin=(1, 0), n_raw=2)
    assert {r["index"]: r["fact_id"] for r in _rows(straight)} == \
           {r["index"]: r["fact_id"] for r in _rows(swapped)}


# ---------------------------------------------------------------- N ----------
def test_N_the_relation_is_OPTIONAL_and_V1_behaviour_is_untouched_without_it(tmp_path):
    """The atomic switch has not happened. Omitting the relation must reproduce
    today's behaviour exactly: one row per prepared fact, indexed by position."""
    res = _run(tmp_path, [fact(), _other_period()])
    rows = _rows(res)
    assert [r["index"] for r in rows] == [0, 1]


# ------------------------------------- THE FIVE REPRODUCED FAILURES ---------
def test_a_forged_terminal_can_NEVER_become_a_public_row(tmp_path):
    """Reviewer-reproduced: a hand-authored terminal claiming `written`, a
    fabricated fact_id, an unowned code and an extra field was returned
    byte-for-byte as a public row, bypassing the outcome owner entirely."""
    forged = {"index": 1, "fact_id": "fabricated", "decision": "written",
              "codes": ["NOT_AN_OWNER_CODE"], "detail": "x", "extra": "smuggled"}
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [fact()], raw_origin=(0,), n_raw=2, raw_terminals=(forged,))
    assert "raw accounting:" in str(exc.value)


@pytest.mark.parametrize("bad,why", [
    ({"index": 1, "fact_id": "x", "decision": "skipped", "codes": [], "detail": None},
     "a zero-fact terminal must not carry a fact_id"),
    ({"index": 1, "fact_id": None, "decision": "written", "codes": [], "detail": None},
     "`written` is not a terminal for a raw item that produced nothing"),
    ({"index": 1, "fact_id": None, "decision": "skipped",
      "codes": ["NOT_AN_OWNER_CODE"], "detail": None},
     "an unowned code"),
    ({"index": 1, "fact_id": None, "decision": "skipped", "codes": []},
     "a missing public field"),
])
def test_a_terminal_must_come_from_the_existing_typed_owner(tmp_path, bad, why):
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [fact()], raw_origin=(0,), n_raw=2, raw_terminals=(bad,))
    assert "raw accounting:" in str(exc.value), why


def test_an_EARLY_event_failure_still_accounts_by_raw_index(tmp_path):
    """Reviewer-reproduced: the source-missing return bypassed the translation
    and reported raw index 1 for an event whose n_raw was 1."""
    res = _run(tmp_path, [fact(), fact()], raw_origin=(0, 0), n_raw=1,
               store_source=None)
    assert {r["index"] for r in _rows(res)} == {0}, _rows(res)
    # REVIEWER RULING (SEQ 975 finding 1): an event-wide failure MAY yield one
    # row per prepared branch. Preserving evidence beats collapsing, and a
    # failure-group identity must NOT be invented merely to merge them. An
    # earlier version of this test asserted the collapse and was wrong.
    assert len(_rows(res)) == 2, _rows(res)


def test_the_relation_is_FROZEN_before_any_store_callback(tmp_path):
    """Reviewer-reproduced TOCTOU: a caller's mutable list was validated, then
    mutated inside `get_source`, and the public row carried raw index 7."""
    moved = [0]

    class Mutating(FakeStore):
        def get_source(self, *a, **k):
            moved[0] = 7
            return super().get_source(*a, **k)

    ri = RunInputV1.from_dict({"source_id": SRC, "facts": [fact()]})
    res = run_event(ri, store=Mutating(), audit_dir=str(tmp_path),
                    raw_origin=moved, n_raw=1)
    assert [r["index"] for r in res["items"]] == [0], \
        "the checked relation was not frozen — a later mutation moved the row"


def test_the_frozen_relation_is_recorded_in_the_ONE_audit_and_its_run_id(tmp_path):
    """A relation the audit cannot reconstruct is not evidence."""
    import json
    import os
    res = _run(tmp_path, [fact()], raw_origin=(0,), n_raw=1)
    assert res
    docs = [json.load(open(os.path.join(str(tmp_path), f)))
            for f in os.listdir(str(tmp_path)) if f.endswith(".json")]
    assert len(docs) == 1, docs
    acct = docs[0]["input"].get("raw_accounting")
    assert acct == {"n_raw": 1, "origin": [0], "terminals": []}, acct


# ---------------- THE SEQ 975 DENOMINATOR, AS NAMED TESTS --------------------
# HONESTY NOTE: each behaviour below was first proved RED by direct reproduction
# against the live candidate (raw output in the SEQ 816/817 packets). These are
# the NAMED regressions for those reproductions; their teeth are the mutation
# proof, not the mere fact that they pass now.

def _same_code_pair():
    """Two branches of ONE raw item that both park with the SAME owned code."""
    a = fact(period_start_date="2025-03-30", period_end_date="2025-03-30",
             fiscal_quarter=2)
    b = fact(period_start_date="2025-06-28", period_end_date="2025-06-28",
             fiscal_quarter=3)
    return [a, b]


def test_two_split_branches_with_the_SAME_code_BOTH_remain(tmp_path):
    """The recall loss: content equality cannot prove two failures are one
    relation, so a null-fact_id row is never deduped by value."""
    res = _run(tmp_path, _same_code_pair(), raw_origin=(0, 0), n_raw=1)
    rows = _by_index(res)[0]
    assert len(rows) == 2, f"a failed split branch was lost: {rows}"
    assert {tuple(r["codes"]) for r in rows} == {("PERIOD_UNRESOLVED",)}


def test_two_split_branches_with_the_SAME_code_AND_detail_BOTH_remain(tmp_path):
    """Even byte-identical failure rows are two branches, not one."""
    same = fact(period_start_date="2025-03-30", period_end_date="2025-03-30",
                fiscal_quarter=2)
    res = _run(tmp_path, [same, dict(same)], raw_origin=(0, 0), n_raw=1)
    assert len(_by_index(res)[0]) == 2


def test_a_one_shot_iterable_is_frozen_once_and_never_silently_lost(tmp_path):
    """Validated, exhausted, then copied as empty — the terminal vanished."""
    t = {"index": 0, "fact_id": None, "decision": "parked",
         "codes": ["SOURCE_UNAVAILABLE"], "detail": "gap"}
    res = _run(tmp_path, [], raw_origin=(), n_raw=1,
               raw_terminals=(x for x in [t]))
    assert len(_rows(res)) == 1, f"a one-shot terminal was lost: {_rows(res)}"


@pytest.mark.parametrize("kw", [
    {"n_raw": 1},
    {"raw_terminals": ({"index": 0, "fact_id": None, "decision": "parked",
                        "codes": ["SOURCE_UNAVAILABLE"], "detail": None},)},
    {"n_raw": 1, "raw_terminals": ()},
])
def test_every_partial_argument_set_RAISES_before_any_store_callback(tmp_path, kw):
    """A partial set silently reverted to legacy per-fact rows."""
    class Exploding(FakeStore):
        def get_source(self, *a, **k):
            raise AssertionError("I/O ran before the argument check")
    ri = RunInputV1.from_dict({"source_id": SRC, "facts": [fact()]})
    with pytest.raises(RuntimeError) as exc:
        run_event(ri, store=Exploding(), audit_dir=str(tmp_path), **kw)
    assert "ONE argument set" in str(exc.value), exc.value


@pytest.mark.parametrize("bad", [True, 1.0, "0"])
def test_only_an_EXACT_builtin_int_is_a_raw_position(tmp_path, bad):
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [fact()], raw_origin=(bad,), n_raw=2)
    assert "raw accounting:" in str(exc.value)


def test_an_int_SUBCLASS_is_refused_and_never_travels_out_as_the_index(tmp_path):
    class Position(int):
        pass
    with pytest.raises(RuntimeError):
        _run(tmp_path, [fact()], raw_origin=(Position(0),), n_raw=1)
    # the lawful control: a plain int at the same position is accepted
    assert _by_index(_run(tmp_path, [fact()], raw_origin=(0,), n_raw=1)) == \
        _by_index(_run(tmp_path, [fact()], raw_origin=(0,), n_raw=1))


def test_a_split_permutation_is_compared_as_a_MULTISET_not_a_dict(tmp_path):
    """A dict comprehension keyed by index DISCARDS repeated raw indexes, so a
    lost split branch would be invisible to the comparison itself."""
    def multiset(res):
        return sorted((r["index"], r["fact_id"], r["decision"],
                       tuple(r["codes"])) for r in _rows(res))
    a, b = _same_code_pair()
    straight = _run(tmp_path, [a, b], raw_origin=(0, 0), n_raw=1)
    swapped = _run(tmp_path, [b, a], raw_origin=(0, 0), n_raw=1)
    assert multiset(straight) == multiset(swapped)
    assert len(_rows(straight)) == 2, "the multiset itself must see both branches"


def test_J_an_event_wide_failure_reaches_every_distinct_raw_origin(tmp_path):
    """Two raw items, one event-level failure: BOTH raw origins are accounted."""
    res = _run(tmp_path, [fact(), fact()], raw_origin=(0, 1), n_raw=2,
               store_source=None)
    assert set(_by_index(res)) == {0, 1}, _rows(res)
    assert {r["decision"] for r in _rows(res)} == {"rejected"}


def test_the_WRITE_GATE_refusal_still_accounts_by_raw_index(tmp_path):
    """Accounting must survive every return path, not just the normal one."""
    res = _run(tmp_path, [fact(), _other_period()], raw_origin=(0, 0), n_raw=1,
               enable_writes=True)          # ENABLE_DRIVER_WRITES is unset
    assert set(_by_index(res)) == {0}, _rows(res)


def test_a_conflicting_row_for_the_SAME_raw_and_fact_RAISES_never_chooses():
    """The one guard that CANNOT be reached through the public router, because a
    public path producing it would already be the bug. Tested at the nearest
    existing owner, `_raw_rows`, and named as such rather than dressed up as an
    end-to-end proof. A mutation that let this pick a winner was NOT caught by
    any other test in this file — that gap is why this exists."""
    from driver.core.driver_write_cli import _raw_rows
    same_fact = [
        {"index": 0, "fact_id": "du:x", "decision": "written",
         "codes": [], "detail": None},
        {"index": 1, "fact_id": "du:x", "decision": "parked",
         "codes": ["EXECUTION_FAILED"], "detail": "other"},
    ]
    with pytest.raises(RuntimeError) as exc:
        _raw_rows(same_fact, (0, 0), ())
    assert "internal inconsistency" in str(exc.value), exc.value
    # lawful control: the SAME result twice collapses to one row, never raises
    agree = [dict(same_fact[0]), dict(same_fact[0], index=1)]
    assert len(_raw_rows(agree, (0, 0), ())) == 1


# ------------- ONE FAILED FUSION GROUP IS ONE RELATION PER RAW ITEM ----------
def _ambiguous_three():
    """The EXISTING three-fragment FUSION_AMBIGUOUS case, reused not rebuilt."""
    return [
        fact(),
        fact(level_low=None, level_high=None, level_unit_raw=None,
             change_value=Decimal("12"), change_unit_raw="%"),
        fact(level_low=Decimal("101"), level_high=Decimal("101")),
    ]


def test_one_raw_item_with_three_ambiguous_fragments_yields_ONE_park(tmp_path):
    """Three fragments of ONE raw item that fail fusion TOGETHER are ONE failed
    group, so the raw item gets ONE outcome — not one per fragment."""
    res = _run(tmp_path, _ambiguous_three(), raw_origin=(0, 0, 0), n_raw=1)
    rows = _by_index(res)[0]
    assert len(rows) == 1, f"one failed fusion group reported {len(rows)} times: {rows}"
    assert rows[0]["codes"] == ["FUSION_AMBIGUOUS"]


def test_a_failed_fusion_group_reaches_EVERY_distinct_raw_contributor_once(tmp_path):
    """Same group, two raw origins: exactly one outcome per distinct raw item."""
    res = _run(tmp_path, _ambiguous_three(), raw_origin=(0, 0, 1), n_raw=2)
    by = _by_index(res)
    assert set(by) == {0, 1}, by
    assert [len(v) for v in (by[0], by[1])] == [1, 1], by


def test_group_collapse_does_NOT_reintroduce_the_split_recall_loss(tmp_path):
    """THE control that keeps the two rules apart: two INDEPENDENT branches with
    the same null fact_id, code and detail are NOT one group and stay TWO."""
    res = _run(tmp_path, _same_code_pair(), raw_origin=(0, 0), n_raw=1)
    assert len(_by_index(res)[0]) == 2


def test_a_fragment_permutation_preserves_the_full_multiset(tmp_path):
    a, b, c = _ambiguous_three()
    def ms(r):
        return sorted((x["index"], x["decision"], tuple(x["codes"]))
                      for x in _rows(r))
    assert ms(_run(tmp_path, [a, b, c], raw_origin=(0, 0, 1), n_raw=2)) == \
           ms(_run(tmp_path, [c, b, a], raw_origin=(1, 0, 0), n_raw=2))


# ------------- SEQ 977 RESIDUAL 2-6: every return path, and the freeze -------
import os


def _enabled(tmp_path, facts, store, **kw):
    """The EXISTING real-write harness, reused: fixed clock, gate set, restored."""
    os.environ["ENABLE_DRIVER_WRITES"] = "1"
    try:
        ri = RunInputV1.from_dict({"source_id": SRC, "facts": facts})
        return run_event(ri, store=store, audit_dir=str(tmp_path),
                         enable_writes=True,
                         now_fn=lambda: "2026-07-17T20:00:00.000000", **kw)
    finally:
        del os.environ["ENABLE_DRIVER_WRITES"]


# 2 -------------------------------------------------------------------------
def test_a_fact_lost_INSIDE_core_RAISES_and_never_becomes_a_public_park(tmp_path):
    """`INTERNAL_UNTRACKED` is a CLI bug. Under the accounting law it must stop
    the run loudly; publishing it as a park would invent an outcome for a fact
    nobody can account for."""
    from driver.core.driver_write_cli import _raw_rows
    lost = [_item(0, "parked", ["INTERNAL_UNTRACKED"], detail="vanished")]
    with pytest.raises(RuntimeError) as exc:
        _raw_rows(lost, (0,), (), {})
    assert "disappeared inside" in str(exc.value), exc.value
    # lawful control: a normal parked row at the same position is published
    ok = [_item(0, "parked", ["PERIOD_UNRESOLVED"], detail="x")]
    assert _raw_rows(ok, (0,), (), {})[0]["index"] == 0


# 3 -------------------------------------------------------------------------
def test_the_COMPANY_AMBIGUOUS_path_accounts_by_raw_index(tmp_path):
    """Reusing the existing ambiguous-company fixture, adding only the
    accounting assertion."""
    ri = RunInputV1.from_dict({"source_id": SRC, "facts": [fact(), fact()]})
    res = run_event(ri, store=FakeStore(companies=["AAPL", "AAPL2"]),
                    audit_dir=str(tmp_path), raw_origin=(0, 0), n_raw=1)
    assert set(_by_index(res)) == {0}, _rows(res)
    assert all(r["codes"] == ["SOURCE_COMPANY_AMBIGUOUS"] for r in _rows(res))


def test_the_WRITER_BUSY_lock_path_accounts_by_raw_index(tmp_path):
    """The existing lock fixture: a second writer holding the flock."""
    import fcntl
    lock_path = str(tmp_path / "w.lock")
    with open(lock_path, "w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        res = _enabled(tmp_path, [fact(), fact()], FakeStore(),
                       lock_path=lock_path, raw_origin=(0, 0), n_raw=1)
    assert res["code"] == "WRITER_BUSY"
    assert set(_by_index(res)) == {0}, _rows(res)


def test_the_ROLLBACK_path_accounts_by_raw_index(tmp_path):
    """The existing fail_apply fixture: a real transaction that rolls back."""
    res = _enabled(tmp_path, [fact(), fact()], FakeStore(fail_apply=True),
                   raw_origin=(0, 1), n_raw=2)
    assert res["code"] == "EXECUTION_FAILED"
    assert set(_by_index(res)) == {0, 1}, _rows(res)


# 4 -------------------------------------------------------------------------
def test_changing_the_frozen_relation_CHANGES_the_audit_run_identity(tmp_path):
    """Presence is not binding. With the clock held fixed, a different relation
    must produce a different run id, or the audit does not pin the accounting."""
    import json
    a = tmp_path / "a"
    b = tmp_path / "b"
    _enabled(a, [fact(), fact()], FakeStore(), raw_origin=(0, 0), n_raw=1)
    _enabled(b, [fact(), fact()], FakeStore(), raw_origin=(0, 1), n_raw=2)

    def ident(d):
        names = [f for f in os.listdir(str(d)) if f.endswith(".json")]
        assert len(names) == 1, names
        doc = json.load(open(os.path.join(str(d), names[0])))
        return doc["run_id"], doc["input"]["raw_accounting"]
    (id_a, acct_a), (id_b, acct_b) = ident(a), ident(b)
    assert acct_a == {"n_raw": 1, "origin": [0, 0], "terminals": []}
    assert acct_b == {"n_raw": 2, "origin": [0, 1], "terminals": []}
    assert id_a != id_b, "the same run id for two different relations — unbound"


# 5 -------------------------------------------------------------------------
def test_the_nested_terminal_CONTENT_is_frozen_before_any_callback(tmp_path):
    """The origin freeze was proved; the terminal DICT is the other half. A
    caller mutating its content during a store callback must not move the row."""
    live = {"index": 1, "fact_id": None, "decision": "parked",
            "codes": ["SOURCE_UNAVAILABLE"], "detail": "gap"}

    class Mutating(FakeStore):
        def get_source(self, *a, **k):
            live["decision"] = "written"       # forge, after validation
            live["codes"] = ["NOT_AN_OWNER_CODE"]
            return super().get_source(*a, **k)

    ri = RunInputV1.from_dict({"source_id": SRC, "facts": [fact()]})
    res = run_event(ri, store=Mutating(), audit_dir=str(tmp_path),
                    raw_origin=(0,), n_raw=2, raw_terminals=(live,))
    row = _by_index(res)[1][0]
    assert row["decision"] == "parked" and row["codes"] == ["SOURCE_UNAVAILABLE"], \
        f"a post-check mutation reached the public row: {row}"


# 6 -------------------------------------------------------------------------
def test_an_EMPTY_event_with_a_MISSING_source_still_fails_closed(tmp_path):
    """The real control the old A test only claimed: zero raw items must not
    become a silent success when the source itself is absent."""
    res = _run(tmp_path, [], raw_origin=(), n_raw=0, store_source=None)
    assert res["status"] == "failed" and res["code"] == "SOURCE_MISSING"
    assert _rows(res) == []


def test_an_EMPTY_event_with_a_VALID_source_is_lawfully_empty(tmp_path):
    """The lawful control beside it."""
    res = _run(tmp_path, [], raw_origin=(), n_raw=0)
    assert _rows(res) == [] and res["status"] == "dry_run"


# ---------------- SEQ 979: the codeless terminal, and public-path proof ------
def test_a_terminal_with_NO_code_fails_closed(tmp_path):
    """BUILD 838-843: every emitting non-written branch carries an EXPLICIT code.
    A codeless terminal published a public outcome with no machine reason."""
    codeless = {"index": 0, "fact_id": None, "decision": "skipped",
                "codes": [], "detail": "abstained"}
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [], raw_origin=(), n_raw=1, raw_terminals=(codeless,))
    assert "no explicit code" in str(exc.value), exc.value


def test_the_lawful_control_a_terminal_WITH_an_owned_code_is_published(tmp_path):
    owned = {"index": 0, "fact_id": None, "decision": "parked",
             "codes": ["SOURCE_UNAVAILABLE"], "detail": "gap"}
    res = _run(tmp_path, [], raw_origin=(), n_raw=1, raw_terminals=(owned,))
    assert _rows(res) == [owned]


def test_a_lost_fact_RAISES_through_the_PUBLIC_run_event_boundary(tmp_path,
                                                                  monkeypatch):
    """SEQ 977 item 2 at the PUBLIC boundary, not only the nearest owner: the
    planner loses a surviving fact and the run must stop, never publish a park."""
    import driver.core.driver_write_cli as cli
    monkeypatch.setattr(cli, "plan_event_write",
                        lambda facts, graph, prior_series_units=None: [])
    with pytest.raises(RuntimeError) as exc:
        _run(tmp_path, [fact()], raw_origin=(0,), n_raw=1)
    assert "disappeared inside" in str(exc.value), exc.value


def test_changing_ONLY_a_frozen_TERMINAL_changes_the_audit_identity(tmp_path):
    """The origin/n_raw pair was already proved. This catches SELECTIVE omission
    of the terminals: same origin, same n_raw, one terminal field different."""
    import json
    def go(sub, detail):
        t = {"index": 1, "fact_id": None, "decision": "parked",
             "codes": ["SOURCE_UNAVAILABLE"], "detail": detail}
        _enabled(sub, [fact()], FakeStore(), raw_origin=(0,), n_raw=2,
                 raw_terminals=(t,))
        names = [f for f in os.listdir(str(sub)) if f.endswith(".json")]
        assert len(names) == 1, names
        doc = json.load(open(os.path.join(str(sub), names[0])))
        return doc["run_id"], doc["input"]["raw_accounting"]["terminals"]
    a, b = tmp_path / "ta", tmp_path / "tb"
    (id_a, term_a), (id_b, term_b) = go(a, "gap one"), go(b, "gap two")
    assert term_a[0]["detail"] == "gap one" and term_b[0]["detail"] == "gap two"
    assert id_a != id_b, "a terminal field changed but the run identity did not"
