"""Every proof owner must REFUSE, not report (Codex SEQ 1557 item 3).

The shell runner propagates a nonzero status correctly, but the Python owners printed
their verdict and exited zero: `NOT ACCEPTABLE` on FALSE/ERROR/drift, an inventory with
untested or unmutated branches, a census with a checkpoint mismatch. A proof that
announces its own failure and returns success is worse than no proof, because the
ordered runner carries on and the freeze happens anyway.

Each control injects one bad condition and requires a nonzero verdict.
"""
import io
import pytest
import os
import sys

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "ledger"))
sys.path.insert(0, os.path.join(_R, "proofs"))
import branch_inventory as BI                                  # noqa: E402
import audit_verdict as AV                                     # noqa: E402


def test_the_audit_REFUSES_a_false_row():
    assert AV.verdict({"FALSE": 1, "ERROR": 0}, []) != 0


def test_the_audit_REFUSES_an_error_row():
    assert AV.verdict({"FALSE": 0, "ERROR": 1}, []) != 0


def test_the_audit_REFUSES_state_drift():
    assert AV.verdict({"FALSE": 0, "ERROR": 0}, ["_SIBLING_CACHE"]) != 0


def test_the_audit_ACCEPTS_only_a_clean_result():
    assert AV.verdict({"FALSE": 0, "ERROR": 0}, []) == 0


#: EXACTLY the keys `branches()` emits. The previous controls invented a `tested` key,
#: so they proved the rule against a schema this module never produces - and the rule
#: read that invented key, which meant an untested row passed in the live inventory.
GENERATED_KEYS = {"branch", "test", "mutation", "control_only"}


def _generated_row(**over):
    row = {"branch": "b", "test": "t", "mutation": "m"}
    row.update(over)
    assert set(row) <= GENERATED_KEYS, sorted(set(row) - GENERATED_KEYS)
    return row


def test_the_control_rows_match_the_REAL_generated_schema():
    """The guard against the defect that hid the last one: if `branches()` ever emits a
    different key set, these controls must fail rather than keep testing a fiction."""
    import json
    real = json.load(io.open(os.path.join(_R, "reports", "branch_inventory.json"),
                             encoding="utf-8"))["branches"]
    for row in real:
        assert set(row) <= GENERATED_KEYS, sorted(set(row) - GENERATED_KEYS)
    assert "tested" not in set().union(*(set(r) for r in real))


def test_the_inventory_REFUSES_a_row_whose_test_is_missing():
    assert BI.verdict([_generated_row(test=None)]) != 0


def test_the_inventory_REFUSES_a_row_whose_test_is_empty():
    assert BI.verdict([_generated_row(test="")]) != 0


def test_the_inventory_REFUSES_a_branch_with_no_mutation():
    assert BI.verdict([_generated_row(mutation=None)]) != 0


def test_the_inventory_ACCEPTS_a_covered_branch():
    rows = [_generated_row(),
            _generated_row(mutation=None, control_only="a byte pin")]
    assert BI.verdict(rows) == 0


@pytest.mark.reads_chain_outputs
def test_the_inventory_ACCEPTS_the_REAL_generated_rows():
    """The live rows, not a fixture - the inventory the chain regenerates AFTER its
    mutation step, so this can only be judged once those outputs exist (a row added
    tonight has no mutation report until step 4 runs; before that the verdict is 1)."""
    import json
    real = json.load(io.open(os.path.join(_R, "reports", "branch_inventory.json"),
                             encoding="utf-8"))["branches"]
    assert BI.verdict(real) == 0


def _census_routes():
    """-> the census's own `routes()`, without running the census.

    The census performs a full replay at import, so its refusals cannot be exercised by
    importing it. The loader is lifted and compiled on its own, which is the same trick
    the audit's verdict rule uses and for the same reason.
    """
    src = io.open(os.path.join(_R, "proofs", "open_population.py"),
                  encoding="utf-8").read()
    body = src[src.index("def routes():"):src.index("HARNESS = ")]
    ns = {"os": os, "io": io, "R": _R, "sys": sys}
    exec(compile(body, "<routes>", "exec"), ns)
    return ns["routes"]


def test_the_census_REFUSES_a_missing_inventory(tmp_path, monkeypatch):
    routes = _census_routes()
    monkeypatch.setitem(routes.__globals__, "R", str(tmp_path))   # no inventory there
    try:
        routes()
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("the census accepted a missing accepted-checkpoint inventory")


def test_the_census_REFUSES_a_malformed_inventory(tmp_path, monkeypatch):
    os.makedirs(str(tmp_path / "products"))
    io.open(str(tmp_path / "products" / "ACCEPTED_CHECKPOINTS.tsv"), "w",
            encoding="utf-8").write("owner\tcutoff\n" + "only\ttwo\tfields\n")
    routes = _census_routes()
    monkeypatch.setitem(routes.__globals__, "R", str(tmp_path))
    try:
        routes()
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("the census accepted a malformed inventory row")


def test_an_external_source_change_is_REPORTED_not_restored_away():
    """The harness must never rewrite package sources (Codex SEQ 1558 item 5).

    The old rule restored the bytes captured at start, which is indistinguishable from
    clobbering: it erased a guard added and tested while a run was in flight, and the
    run then reported a fix that no longer existed. This proves the replacement both
    NOTICES the change and LEAVES IT ALONE.
    """
    import mutations as MU
    probe = os.path.join(_R, "zz_source_drift_probe.py")
    io.open(probe, "w", encoding="utf-8").write("MARK = 'original'\n")
    try:
        before = MU._source_files()
        assert probe in before, "the probe is not treated as a package source"
        io.open(probe, "w", encoding="utf-8").write("MARK = 'an author edited this'\n")
        changed = MU.changed_sources(before)
        assert os.path.basename(probe) in changed, changed
        # and, decisively, the edit SURVIVES
        assert "an author edited this" in io.open(probe, encoding="utf-8").read()
    finally:
        os.remove(probe)
