"""Completed CURRENT producer proofs, replacing the old 1515/5612 fixtures."""
import os

import a6_launch_freeze as A6
import a7_conservation as C
import a7_g1_build as G
import a7_g23_run as R
import a7_prepared_run as PR
import build_a5_exp5_kit as A5
import raw_transport as RT
from test_a7_input_binding import run, inputs, g1


def test_completed_current_run_keeps_its_pin_and_counts_each_return_once(run):
    assert PR.current(run["run_dir"], run["a6_freeze_sha256"]) == run
    fin = G._read(os.path.join(run["run_dir"], RT.FINALIZATION_NAME))
    plan = RT.a1_plan_for_run(run["run_dir"])
    required = len(RT.a1_schedule(plan))
    assert len(fin["classification"]) == required == run["scheduled_calls"] > 0
    assert fin["retry"] == []
    assert not os.path.exists(os.path.join(run["run_dir"], RT.RETRY_DIRNAME))
    total, rows = A6.ledger(run["run_dir"])
    closed = A5.a4_lock()["call_accounting"]["ledger_after"]
    assert total == sum(r["calls"] for r in rows) == closed + required
    budget = A6.freeze(run["run_dir"])["budget"]
    assert budget["completed_actual"] == total
    assert budget["planned_producer_primary"] == 0
    assert budget["producer_primary_after"] == total


def test_completed_current_run_materializes_and_freezes_without_retry_file(run):
    first = G.materialize(run)
    second = G.materialize(run)
    assert first == second and first[1] is not second[1]
    arms, meta, problems = first
    assert arms and problems == []
    assert len(meta["trace"]) == run["scheduled_calls"]
    assert all(row["status"] == "answered" for row in meta["trace"])
    a, pa, problems = G.freeze(run)
    b, pb, other_problems = G.freeze(run)
    assert problems == other_problems == [] and a == b and pa == pb and pa
    assert a["budget"]["spent_before"] == A6.ledger(run["run_dir"])[0]
    assert a["launchers"]["count"] == len(pa) * len(a["launchers"]["lanes"])


def test_current_accounting_and_approved_g23_rebuild_identically(run, inputs, g1, tmp_path):
    ca, cp = C.terminals(run, str(tmp_path / "conservation_a"))
    cb, cq = C.terminals(run, str(tmp_path / "conservation_b"))
    assert cp == cq == [] and ca == cb
    assert ca["scheduled_calls"] == len(ca["packets"]) == run["scheduled_calls"]
    assert ca["branch_total"] == len(ca["branches"]) > 0
    da, pa, ea = R.freeze(run, inputs=inputs, g1=g1, audit_root=str(tmp_path / "g23_a"))
    db, pb, eb = R.freeze(run, inputs=inputs, g1=g1, audit_root=str(tmp_path / "g23_b"))
    assert ea == eb == [] and da == db and pa == pb and pa
    assert sum(map(len, da["g2_pairs"].values())) > 0
    assert sum(map(len, da["g3_idxs"].values())) > 0


def test_current_counts_and_names_do_not_consult_historical_values(run, monkeypatch):
    import a7_reference_inventory as I

    assert A5.APPROVED_KEY_DIR
    plan = RT.a1_plan_for_run(run["run_dir"])
    before = I.expected_document(run)
    assert before["rows"] and before["override_rows"] == 0
    signed = I._approved_reference_names()
    assert all(r["reference_name"] == signed[(r["packet_id"], r["fact_index"])]
               for r in before["rows"])

    class ForbiddenHistoricalData(dict):
        def get(self, *args):
            raise AssertionError("current input consulted old positional names")

    monkeypatch.setattr(I, "SPAN_OVERRIDES", ForbiddenHistoricalData())
    monkeypatch.setattr(G, "REQUIRED", dict.fromkeys(G.REQUIRED, -1))
    assert I.expected_document(run) == before
    assert G._required(plan) == {
        "events": len({p["source_id"] for p in plan["packets"]}),
        "packets": len(plan["packets"]),
        "accepted_gold": len(before["rows"]),
        "answers": len(RT.a1_schedule(plan)),
    }
    # A changed population uses its own declared counts, not this test's size.
    monkeypatch.setattr(A5, "a4_lock", lambda: {
        "counts": {"du_worthy_facts": 7, "accepted_facts": 11}})
    assert G._required({"n_events": 3, "n_packets": 5, "arms": ["a", "b"]}) == {
        "events": 3, "packets": 5, "accepted_gold": 7, "answers": 10}
