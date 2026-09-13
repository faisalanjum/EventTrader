"""THE LIVE CURRENT/HISTORY BOUNDARY (Codex SEQ 1473 item 1).

These proofs deliberately do NOT use the `historical_v1_evidence` fixture: they
are about the live gate itself, which must accept ONLY a run prepared for the
current producer era.
"""
import io
import os
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a6_launch_freeze as _A6                                   # noqa: E402,F401
import build_a5_exp5_kit as A5                                   # noqa: E402
import a7_conservation as C                                      # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import a7_g23_build as B                                         # noqa: E402
import a7_g23_run as R                                           # noqa: E402
import a7_prepared_run as PR                                     # noqa: E402
import a7_reference_inventory as I                               # noqa: E402
from test_a7_trace_1471 import run as saved_run

#: this module's own audit root; these proofs only prove REFUSALS, but they
#: must still not spend the shared accepted-event phase
_AUDIT = tempfile.mkdtemp(prefix="current_audit_")


def _freeze_sha(run):
    """The accepted A6 freeze hash the operator supplies to `current` - the
    exact A6-rendered bytes for this run (Codex SEQ 1517)."""
    import hashlib
    A6 = G._a6()
    # the accepted hash is the run's PRE-LAUNCH view - what `load` pins - so it
    # is the live freeze before execution and the reconstructed pre-call freeze
    # after (Codex SEQ 1521); a no-op on an unexecuted run.
    return hashlib.sha256(
        A6.render(A6.precall_view(A6.freeze(run), run)).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def current(tmp_path_factory, saved_run):
    run = str(tmp_path_factory.mktemp("cur") / "v3")
    assert A5.prepare(run)["ok"]
    return PR.current(run, _freeze_sha(run))


@pytest.fixture(scope="module")
def other(tmp_path_factory):
    run = str(tmp_path_factory.mktemp("cur2") / "v3b")
    assert A5.prepare(run)["ok"]
    return PR.current(run, _freeze_sha(run))


def _historical_identity():
    """The paid v1 identity, built the only way it still can be."""
    return PR.load(G.PRIMARY)


@pytest.mark.skipif(not os.path.isdir(G.PRIMARY),
                    reason="the executed run is absent")
@pytest.mark.parametrize("entry", [
    ("materialize", lambda run: G.materialize(run)),
    ("inventory", lambda run: G.inventory(run)),
    ("questions", lambda run: G.questions(run)),
    ("G1 freeze", lambda run: G.freeze(run)),
    ("conservation", lambda run: C.terminals(run)),
    ("G23 populations", lambda run: R.populations(run, _AUDIT)),
    ("G23 freeze", lambda run: R.freeze(run)),
    ("reference packets", lambda run: I._packets(run)),
    ("reference card", lambda run: B.reference_card({}, "s", 0, run)),
], ids=lambda e: e[0] if isinstance(e, tuple) else str(e))
def test_the_old_v1_run_refuses_at_every_live_entry(entry):
    _label, call = entry
    old = _historical_identity()
    if _label == "G23 freeze":
        # This public entry refuses absent approved G1 before inspecting the
        # producer era. Its current, approved-G1 positive is exercised by
        # test_a7_input_binding and the complete G23 lifecycle module.
        doc, prompts, problems = call(old)
        assert doc is None and not prompts
        assert len(problems) == 1 and problems[0]["reason"] == "g1_lifecycle_required"
        return
    with pytest.raises(ValueError) as exc:
        call(old)
    assert "era" in str(exc.value) or "current producer era" in str(exc.value), \
        str(exc.value)[:160]


def test_two_independently_prepared_current_runs_cannot_cross(current, other):
    assert current["run_dir"] != other["run_dir"]
    assert G.run_of(current) and G.run_of(other)      # each is fine alone
    crossed = dict(current, run_dir=other["run_dir"])
    with pytest.raises(ValueError):
        G.run_of(crossed)


def test_mutation_after_a_WARM_MATERIALIZATION_cache_refuses(current):
    G.materialize(current)                            # warm it
    io.open(os.path.join(current["run_dir"], "a5_menu_backmap.json"),
            "a").write(" ")
    try:
        with pytest.raises(ValueError) as exc:
            G.materialize(current)
        assert "no longer measures" in str(exc.value)
    finally:
        path = os.path.join(current["run_dir"], "a5_menu_backmap.json")
        raw = io.open(path, "rb").read()
        io.open(path, "wb").write(raw[:-1])


def test_mutation_after_a_WARM_INVENTORY_cache_refuses(current):
    """The cache was keyed from the caller's dict BEFORE the run was
    re-measured, so a warm entry answered without noticing drift."""
    B._inventory(current)                             # warm it
    path = os.path.join(current["run_dir"], "a5_menu_backmap.json")
    io.open(path, "a").write(" ")
    try:
        with pytest.raises(ValueError) as exc:
            B._inventory(current)
        assert "no longer measures" in str(exc.value), str(exc.value)[:140]
    finally:
        raw = io.open(path, "rb").read()
        io.open(path, "wb").write(raw[:-1])


def test_a_current_zero_call_run_reports_ONE_named_not_called_state(current):
    arms, meta, problems = G.materialize(current)
    assert {r["status"] for r in meta["trace"]} == {"uncalled"}
    doc, _prompts, freeze_problems = G.freeze(current)
    assert doc is None
    assert len(freeze_problems) == 1, freeze_problems
    assert "has not been called" in freeze_problems[0]


def test_load_accepts_any_era_but_current_refuses_history():
    """THE ONE-OWNER SPLIT (Codex SEQ 1475): `PR.load` validates a lawful
    prepared run of ANY era; `PR.current` alone decides whether a live A7 use
    is current. The ledger owns no second era rule."""
    import a6_launch_freeze as A6
    historical = PR.load(G.PRIMARY)                 # loads, unpatched
    assert historical["contract_suffix"] is None
    # supply the history run's OWN freeze hash so it clears the required-hash
    # gate and reaches the era gate - which alone refuses it as history.
    with pytest.raises(ValueError) as exc:
        PR.current(G.PRIMARY, _freeze_sha(G.PRIMARY))
    assert "current producer era" in str(exc.value)
    # and the no-run ledger is the signed final lock's one closed baseline -
    # there is no producer history in it (PRODUCER_HISTORY is gone, Codex SEQ
    # 1516); a historical run's calls are counted only when it is SUPPLIED.
    total, rows = A6.ledger()
    assert total == sum(r["calls"] for r in rows)
    assert [r["stage"] for r in rows] == ["a4_final_key"], rows
    assert A6.ledger(G.PRIMARY)[0] > total          # supplying it DOES add
