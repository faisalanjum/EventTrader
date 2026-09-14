"""EVERY FRESH-RUN STATE, WITHOUT A CRASH (Codex SEQ 1470 item 4).

`effective_slots` read the retry finalization unconditionally and `freeze` read
the retry file unconditionally, so the ORDINARY case - a clean primary that
owes no retry, and therefore has no retry directory at all - was the crashing
one. A crash is not a refusal: an operator cannot tell it from a defect, and it
is not a state the run can be reported in.
"""
import collections
import io
import json
import os
import shutil
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# THE HARNESS COPY OF THE A6 OWNER, BOUND FIRST. A byte-identical copy of
# `a6_launch_freeze` sits at the scratchpad root and derives its pointer paths
# from its own location, so whichever is imported first wins for the whole
# process. `a7_g1_build._a6()` refuses the wrong one - importing the right one
# here is what keeps that refusal from firing.
import a6_launch_freeze as _A6                                   # noqa: E402,F401
import a7_g1_build as G                                          # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402

REAL = G.PRIMARY
RETRY_DIRNAME = "retry"
pytestmark = [pytest.mark.skipif(not os.path.isdir(REAL),
                                 reason="the executed run is absent"),
              # HISTORICAL EVIDENCE: every copy here is of the paid v1 run.
              # See the fixture's docstring in conftest.py.
              pytest.mark.usefixtures("historical_v1_evidence")]


def _copy(tmp_path, name):
    """The real run RELOCATED, still lawfully naming itself.

    A run records where it is - in its receipt's `run_id` and per-call receipt
    paths, and in each finalization's `run_id` and receipt binding - so a copy
    at another path is a different run and the boundary refuses it, correctly.
    These proofs are about retry and receipt states, not relocation, so the
    copy rebases every reference to its own new location and is otherwise
    byte-for-byte the original.
    """
    dest = str(tmp_path / name)
    shutil.copytree(REAL, dest)
    src_abs, dst_abs = os.path.abspath(REAL), os.path.abspath(dest)
    ident = os.path.basename(dst_abs)

    def load(*parts):
        return json.load(io.open(os.path.join(dest, *parts), encoding="utf-8"))

    def save(doc, *parts):
        json.dump(doc, io.open(os.path.join(dest, *parts), "w",
                               encoding="utf-8"))

    # every embedded path first
    for parts in (("receipt.json",), (RETRY_DIRNAME, "receipt.json"),
                  ("finalization.json",),
                  (RETRY_DIRNAME, "finalization.json")):
        path = os.path.join(dest, *parts)
        if os.path.isfile(path):
            text = io.open(path, encoding="utf-8").read()
            io.open(path, "w", encoding="utf-8").write(
                text.replace(src_abs, dst_abs))

    # THEN the bindings, in dependency order: each layer binds the bytes of
    # the one below it, so the primary is settled before the child names it.
    doc = load("receipt.json")
    doc["run_id"] = ident
    save(doc, "receipt.json")

    doc = load("finalization.json")
    doc["run_id"] = ident
    doc["receipt_sha256"] = G._sha_file(os.path.join(dest, "receipt.json"))
    save(doc, "finalization.json")

    if os.path.isfile(os.path.join(dest, RETRY_DIRNAME, "receipt.json")):
        doc = load(RETRY_DIRNAME, "receipt.json")
        doc["run_id"] = RETRY_DIRNAME
        if isinstance(doc.get("parent"), dict):
            doc["parent"]["run_id"] = ident
            doc["parent"]["receipt_sha256"] = G._sha_file(
                os.path.join(dest, "receipt.json"))
            doc["parent"]["finalization_sha256"] = G._sha_file(
                os.path.join(dest, "finalization.json"))
        save(doc, RETRY_DIRNAME, "receipt.json")

        doc = load(RETRY_DIRNAME, "finalization.json")
        doc["run_id"] = RETRY_DIRNAME
        doc["receipt_sha256"] = G._sha_file(
            os.path.join(dest, RETRY_DIRNAME, "receipt.json"))
        save(doc, RETRY_DIRNAME, "finalization.json")
    return dest


def _load_fin(run, *parts):
    with io.open(os.path.join(run, *parts), encoding="utf-8") as fh:
        return json.load(fh)


def _save_fin(doc, run, *parts):
    with io.open(os.path.join(run, *parts), "w", encoding="utf-8") as fh:
        json.dump(doc, fh)



def _lawful_zero_retry(tmp_path, name="lawful"):
    """A GENUINELY self-consistent run that owes no retry.

    Emptying `finalization.retry` while leaving the classifications, validity
    and ledger that DERIVE an owed retry is not a lawful positive - it is a
    run contradicting itself, and the boundary validator now says so. This
    builds a real one: the slot whose attempt 1 was invalid gets the VALID
    attempt-2 bytes, so the primary really is clean, and every derived field is
    recomputed by the accounting owners rather than typed here.
    """
    import raw_transport as RT
    run = _copy(tmp_path, name)
    fin = _load_fin(run, "finalization.json")
    plan = RT.a1_plan_for_run(run)
    owed = [tuple(c) for c in fin["retry"]]
    assert owed, "the source run owes no retry; this helper has nothing to do"

    ordinals = RT.a1_ordinals(plan)
    for key in owed:
        n = ordinals[key]
        good = os.path.join(run, "retry", "answers",
                            "%05d.attempt2.complete.raw.json" % n)
        live = os.path.join(run, "answers",
                            "%05d.attempt1.complete.raw.json" % n)
        shutil.copyfile(good, live)          # the primary now holds VALID bytes
    shutil.rmtree(os.path.join(run, "retry"))

    # every derived field, from the owners that derive it
    fin["validity"] = [[list(k), True] if tuple(k) in owed else [list(k), v]
                       for k, v in [(tuple(r[0]), r[1])
                                    for r in fin["validity"]]]
    fin["retry"] = RT.a1_primary_retry_keys(fin, plan)
    keys = [tuple(r[0]) for r in fin["classification"]]
    outcomes = [r[1] for r in fin["classification"]]
    validity = dict((tuple(r[0]), r[1]) for r in fin["validity"])
    final = collections.OrderedDict(zip(keys, outcomes))
    fin["ledger"] = RT.a1_ledger(final, validity,
                                 len(RT.a1_canonical_calls(plan, 1)), 1)
    fin["run_id"] = os.path.basename(os.path.abspath(run))
    fin["receipt_sha256"] = G._sha_file(os.path.join(run, "receipt.json"))
    _save_fin(fin, run, "finalization.json")
    return run


def _slots(run):
    return G.effective_slots(PR.load(run))


def test_the_real_run_is_the_control(tmp_path):
    slots, _plan, problems = _slots(_copy(tmp_path, "control"))
    assert problems == [], problems[:2]
    assert len(slots) == 392


def test_a_clean_primary_owing_no_retry_needs_no_retry_directory(tmp_path):
    """THE ORDINARY CASE, which used to raise FileNotFoundError."""
    run = _lawful_zero_retry(tmp_path, "clean")
    slots, _plan, problems = _slots(run)
    assert problems == [], problems[:2]
    assert len(slots) == 392
    # every slot takes its own attempt 1; nothing was substituted
    assert {sel for _n, _k, _a, sel in slots} == {1}
    arms, meta, mp = G.materialize(PR.load(run))
    assert mp == [], mp[:2]
    assert all(r["status"] == "answered" for r in meta["trace"])


def test_a_contradictory_finalization_is_REFUSED_not_trusted(tmp_path):
    """Emptying `retry` while the classifications still derive one."""
    run = _copy(tmp_path, "contradiction")
    fin = _load_fin(run, "finalization.json")
    assert fin["retry"], "the source run must owe a retry for this control"
    fin["retry"] = []
    _save_fin(fin, run, "finalization.json")
    with pytest.raises(ValueError) as exc:
        PR.load(run)
    assert "does not hold" in str(exc.value)


def test_an_owed_retry_that_is_not_finalized_is_a_NAMED_wait(tmp_path):
    run = _copy(tmp_path, "owed")
    os.remove(os.path.join(run, "retry", "finalization.json"))
    _slots_out, _plan, problems = _slots(run)
    assert problems, "an unfinished retry was accepted"
    assert any("owes" in p and "not finalized" in p for p in problems), \
        problems[:2]


def test_a_stray_retry_when_none_is_owed_REFUSES(tmp_path):
    """A finalized retry beside a primary that lawfully derives none."""
    clean = _lawful_zero_retry(tmp_path, "stray")
    # put a finalized retry back, though nothing is owed
    shutil.copytree(os.path.join(REAL, "retry"),
                    os.path.join(clean, RETRY_DIRNAME))
    doc = _load_fin(clean, RETRY_DIRNAME, "finalization.json")
    doc["run_id"] = RETRY_DIRNAME
    _save_fin(doc, clean, RETRY_DIRNAME, "finalization.json")
    # REFUSED AT THE BOUNDARY, before any answer can be selected: a retry
    # that closes out keys its primary never owed cannot be a lawful record of
    # this run.
    # REFUSED AT THE BOUNDARY, before any answer can be selected. A retry
    # grafted onto a primary that lawfully derives none cannot bind that
    # primary, so it is refused at the retry's own receipt or finalization -
    # either way, nothing is read from it.
    with pytest.raises(ValueError) as exc:
        PR.load(clean)
    assert "retry" in str(exc.value), str(exc.value)[:140]


def test_a_completed_retry_keeps_BOTH_attempts_and_selects_the_second(tmp_path):
    run = _copy(tmp_path, "retried")
    arms, meta, problems = G.materialize(PR.load(run))
    assert problems == [], problems[:2]
    both = [r for r in meta["trace"] if len(r["attempts"]) > 1]
    assert len(both) == 1, [r["lane_id"] for r in both]
    row = both[0]
    assert [a["attempt"] for a in row["attempts"]] == [1, 2]
    assert row["attempts"][0]["readable"] is False, "attempt 1 was not invalid"
    assert row["selected_attempt"] == 2 and row["status"] == "answered"


def test_saved_answers_without_a_primary_finalization_REFUSE(tmp_path):
    run = _copy(tmp_path, "nofinal")
    os.remove(os.path.join(run, "finalization.json"))
    with pytest.raises(ValueError) as exc:
        PR.load(run)
    assert "no finalization" in str(exc.value)


def test_freeze_needs_no_retry_file_when_none_is_owed(tmp_path):
    """`freeze` read the retry ledger unconditionally too."""
    run = _lawful_zero_retry(tmp_path, "freezeclean")
    doc, _prompts, problems = G.freeze(PR.load(run))
    assert problems == [], problems[:2]
    assert doc["budget"]["spent_before"] > 0


# ---- Codex SEQ 1471 item 2: one mutation at a time, each refused by name ----
def _mutate_retry(fin):
    """claim a retry the classifications do not derive"""
    fin["retry"] = [list(fin["classification"][0][0])]


def _mutate_classification(fin):
    fin["classification"] = fin["classification"][:-1]


def _mutate_validity(fin):
    fin["validity"] = [[r[0], not r[1]] for r in fin["validity"]]


def _mutate_ledger(fin):
    fin["ledger"] = dict(fin["ledger"],
                         scheduled=fin["ledger"]["scheduled"] + 1)


def _mutate_identity(fin):
    fin["run_id"] = "some-other-run"


def _mutate_receipt_binding(fin):
    fin["receipt_sha256"] = "0" * 64


def _mutate_attempt(fin):
    fin["attempt"] = 2


@pytest.mark.parametrize("mutate", [
    _mutate_retry, _mutate_classification, _mutate_validity, _mutate_ledger,
    _mutate_identity, _mutate_receipt_binding, _mutate_attempt,
], ids=["retry", "classification", "validity", "ledger", "identity",
        "receipt-binding", "attempt-shape"])
def test_one_mutation_of_the_primary_finalization_REFUSES(mutate, tmp_path):
    """From the LAWFUL positive, change exactly one thing.

    The consumer used to only HASH these files, so every one of these
    contradictions was accepted and an answer was then selected from a run
    that disagrees with itself (Codex SEQ 1471 item 2).
    """
    run = _lawful_zero_retry(tmp_path, "mut_" + mutate.__name__)
    assert PR.load(run), "the control must load before it is mutated"
    fin = _load_fin(run, "finalization.json")
    mutate(fin)
    _save_fin(fin, run, "finalization.json")
    with pytest.raises(ValueError) as exc:
        PR.load(run)
    assert "does not hold" in str(exc.value), str(exc.value)[:140]


# ---- Codex SEQ 1471 item 3: ONE run, rederived at the point of use ---------
def test_a_mutation_after_identity_capture_refuses_before_any_answer(tmp_path):
    """Shape-checking a caller-owned dict proved only that a caller can build a
    dict. The run could move, be re-finalized or have a byte change after the
    identity was captured and every consumer would still read its answers."""
    run = _copy(tmp_path, "mutated")
    ident = PR.load(run)
    assert G.run_of(ident) == os.path.abspath(run)      # the control
    io.open(os.path.join(run, "a5_menu_backmap.json"), "a").write(" ")
    with pytest.raises(ValueError) as exc:
        G.run_of(ident)
    assert "no longer measures the supplied identity" in str(exc.value)


def test_two_valid_runs_cannot_cross(tmp_path):
    """One run's identity must not open another run, even when both are
    lawful."""
    a = _copy(tmp_path, "runA")
    b = _copy(tmp_path, "runB")
    ia, ib = PR.load(a), PR.load(b)
    assert G.run_of(ia) and G.run_of(ib)                # both lawful alone
    crossed = dict(ia, run_dir=ib["run_dir"])
    with pytest.raises(ValueError):
        G.run_of(crossed)


def test_the_reference_lookup_has_no_default_run(tmp_path):
    """`_packets` fell back to the module default, so an inventory built for a
    fresh run silently bound the OLD run's packets."""
    import a7_reference_inventory as R
    import a7_g23_build as B
    with pytest.raises(ValueError):
        R._packets(None)
    with pytest.raises(ValueError):
        B.reference_card({}, "sid", 0)          # no run supplied


# ---- Codex SEQ 1472 item 7: ONE CUMULATIVE completed-call ledger ----------
def _ledger():
    import a6_launch_freeze as A6
    return A6


def test_the_ledger_is_the_sum_of_its_own_provenance():
    """The no-run baseline is the signed final A4 lock's ONE closed row - no
    producer history is embedded (PRODUCER_HISTORY, the all_prior_calls walk
    and the V6 walk are gone, Codex SEQ 1516) - and the total is still exactly
    the sum of the provenance rows it reports."""
    import build_a5_exp5_kit as A5
    A6 = _ledger()
    total, rows = A6.ledger()
    assert total == sum(r["calls"] for r in rows), rows
    assert [r["stage"] for r in rows] == ["a4_final_key"], rows
    assert total == A5.a4_lock()["call_accounting"]["ledger_after"] > 0


def test_the_completed_history_is_counted_with_no_run_supplied():
    """`ledger()` must not drop the calls the signed final lock already sealed:
    with no run supplied the total is that closed A4 baseline, never zero
    (Codex SEQ 1515/1516). It used to silently drop already-spent calls."""
    import build_a5_exp5_kit as A5
    A6 = _ledger()
    bare, rows = A6.ledger()
    assert bare == A5.a4_lock()["call_accounting"]["ledger_after"]
    assert bare == sum(r["calls"] for r in rows) > 0


def test_a_fresh_zero_call_run_does_not_lose_the_history(tmp_path):
    """A LAWFULLY PREPARED run that has not been called adds nothing AND
    subtracts nothing - and a directory that merely looks like one refuses."""
    import build_a5_exp5_kit as A5
    A6 = _ledger()
    fresh = str(tmp_path / "zerocall")
    assert A5.prepare(fresh)["ok"]                 # the POSITIVE control
    before, _r = A6.ledger()
    assert A6.ledger(fresh)[0] == before

    # a bare `plan/` is NOT a prepared run - it is refused at plan
    # resolution, before the receipt is even reached
    sham = str(tmp_path / "sham")
    os.makedirs(os.path.join(sham, "plan"))
    # THE EXACT OWNER, not a bare Exception: this is a fail-closed assertion,
    # and a broad catch would pass on any error at all.
    import raw_transport as RT
    with pytest.raises(RT.RawTransportError) as exc:
        A6.ledger(sham)
    assert "holds no plan document" in str(exc.value), str(exc.value)[:120]

    # and a directory with NO plan and no receipt refuses by name
    bare = str(tmp_path / "bare")
    os.makedirs(bare)
    with pytest.raises(ValueError) as exc2:
        A6.ledger(bare)
    assert "not a prepared run" in str(exc2.value)


def test_the_same_run_supplied_twice_is_counted_once(tmp_path):
    """The ledger is a pure read of the lock plus the supplied run: each of the
    run's validated attempts is counted once, and supplying the SAME run again
    gives the same total - never a running sum (Codex SEQ 1516)."""
    A6 = _ledger()
    run = _lawful_zero_retry(tmp_path, "twice")
    a, rows_a = A6.ledger(run)
    b, _rows_b = A6.ledger(run)
    assert a == b                                  # pure: same run, same total
    added = [r["stage"] for r in rows_a
             if r["stage"].startswith("current_producer")]
    assert added == ["current_producer_primary"]   # one attempt, not doubled
    assert len(added) == len(set(added))


def test_a_distinct_finalized_run_ADDS_its_calls(tmp_path):
    A6 = _ledger()
    before, _r = A6.ledger()
    run = _lawful_zero_retry(tmp_path, "distinct")
    after, rows = A6.ledger(run)
    added = [r for r in rows if r["stage"].startswith("current_producer")]
    assert added, [r["stage"] for r in rows]
    assert after == before + sum(r["calls"] for r in added)
    # a clean run owes no retry, so no retry row is added for it
    assert not [r for r in added if r["stage"].endswith("_retry")]


def test_only_actually_finalized_retries_increase_it(tmp_path):
    """A retry that never happened is never counted."""
    A6 = _ledger()
    clean = _lawful_zero_retry(tmp_path, "noretry")
    with_retry = _copy(tmp_path, "withretry")
    a, rows_a = A6.ledger(clean)
    b, rows_b = A6.ledger(with_retry)
    # `with_retry` IS the historical run's content at a new path, so it adds
    # both of its finalized attempts; `clean` adds only its primary.
    assert not [r for r in rows_a
                if r["stage"] == "current_producer_retry"]
    assert [r for r in rows_b if r["stage"] == "current_producer_retry"]
    assert b > a


def test_g1_consumes_the_one_ledger_and_adds_nothing(tmp_path):
    A6 = _ledger()
    run = _copy(tmp_path, "consume")
    doc, _p, problems = G.freeze(PR.load(run))
    assert problems == [], problems[:2]
    completed, rows = A6.ledger(run)
    assert doc["budget"]["spent_before"] == completed
    assert doc["budget"]["prior_g1_calls"] == rows


# ---- Codex SEQ 1472 item 2: the LIVE receipt contract at the boundary ------
def _rewrite_receipt(run, *parts, **change):
    """Change a receipt field AND recompute the finalization hash that binds
    it, so the pair is self-consistent - the case a hash-only check accepts."""
    rpath = os.path.join(run, *(parts + ("receipt.json",)))
    doc = json.load(io.open(rpath, encoding="utf-8"))
    doc.update(change)
    json.dump(doc, io.open(rpath, "w", encoding="utf-8"))
    fpath = os.path.join(run, *(parts + ("finalization.json",)))
    fin = json.load(io.open(fpath, encoding="utf-8"))
    fin["receipt_sha256"] = G._sha_file(rpath)
    json.dump(fin, io.open(fpath, "w", encoding="utf-8"))


def test_a_correlated_primary_receipt_and_finalization_REFUSES(tmp_path):
    """The finalization binds the receipt only by HASH, so a changed receipt
    with a recomputed hash used to be accepted."""
    run = _copy(tmp_path, "recmut")
    assert PR.load(run), "the control must load first"
    _rewrite_receipt(run, _smuggled_field=True)
    with pytest.raises(ValueError) as exc:
        PR.load(run)
    assert "receipt" in str(exc.value), str(exc.value)[:140]


def test_a_correlated_RETRY_receipt_and_finalization_REFUSES(tmp_path):
    run = _copy(tmp_path, "retryrecmut")
    assert PR.load(run), "the control must load first"
    _rewrite_receipt(run, RETRY_DIRNAME, _smuggled_field=True)
    with pytest.raises(ValueError) as exc:
        PR.load(run)
    assert "receipt" in str(exc.value), str(exc.value)[:140]


# ---- Codex SEQ 1473 item 3: the ledger VALIDATES before counting ----------
def test_the_distinct_clean_run_reaches_5542(tmp_path):
    """The fourth measured control: history plus one clean finalized 392."""
    import a6_launch_freeze as A6
    before, _r = A6.ledger()
    run = _lawful_zero_retry(tmp_path, "clean392")
    after, rows = A6.ledger(run)
    added = [r for r in rows if r["stage"].startswith("current_producer")]
    assert [r["stage"] for r in added] == ["current_producer_primary"], added
    assert after == before + added[0]["calls"]
    assert added[0]["calls"] == G.REQUIRED["answers"]


@pytest.mark.parametrize("corrupt", [
    lambda fin: fin["ledger"].__setitem__(
        "scheduled", fin["ledger"]["scheduled"] + 1000),
    lambda fin: fin.__setitem__("classification", fin["classification"][:-1]),
    lambda fin: fin.__setitem__("run_id", "some-other-run"),
], ids=["inflated ledger", "short classification", "wrong identity"])
def test_correlated_corruption_REFUSES_before_counting(corrupt, tmp_path):
    """Reading any present finalization and trusting its ledger let a
    corrupted record move the call ceiling (Codex SEQ 1473 item 3)."""
    import a6_launch_freeze as A6
    run = _lawful_zero_retry(tmp_path, "corrupt_" + str(id(corrupt)))
    assert A6.ledger(run)[0] > 0                    # the control counts
    fin = _load_fin(run, "finalization.json")
    corrupt(fin)
    _save_fin(fin, run, "finalization.json")
    with pytest.raises(ValueError) as exc:
        A6.ledger(run)
    assert "does not hold" in str(exc.value), str(exc.value)[:140]
