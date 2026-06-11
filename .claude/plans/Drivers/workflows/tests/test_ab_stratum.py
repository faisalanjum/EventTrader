import json
import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from ab_stratum import (build_rows, degree, percentile_ranks, positions,  # noqa: E402
                        select_indices, select_stratum, shared_token_count)


# ---------- signal helpers ----------

def test_shared_token_count_parses_token_overlap():
    assert shared_token_count("token_overlap:beef,price") == 2
    assert shared_token_count("token_overlap:x,burger,deluxe") == 3
    assert shared_token_count("token_overlap:solo") == 1
    assert shared_token_count("token_overlap:a,b+embedding:0.81") == 2  # tokens before the +
    assert shared_token_count("embedding:0.81") == 0
    assert shared_token_count("") == 0


def test_degree_counts_every_pair_touching_a_record():
    cands = [{"a": "A", "b": "B"}, {"a": "A", "b": "C"}, {"a": "A", "b": "D"},
             {"a": "E", "b": "F"}]
    deg = degree(cands)
    assert deg["a"] == 3   # norm lowercases
    assert deg["b"] == 1 and deg["e"] == 1


def test_positions_reads_index_within_batch():
    plan = {"batches": [{"id": 0, "idx": [7, 3, 9]}, {"id": 1, "idx": [2]}]}
    pos = positions(plan)
    assert pos[7] == (0, 0, 3)
    assert pos[9] == (0, 2, 3)   # last of a 3-pair batch = late
    assert pos[2] == (1, 0, 1)


def test_percentile_ranks_monotonic_with_tie_averaging():
    pr = percentile_ranks([("lo", 1), ("mid", 5), ("hi", 9)])
    assert pr["lo"] == 0.0 and pr["hi"] == 1.0 and 0 < pr["mid"] < 1
    # ties share the average rank
    pr2 = percentile_ranks([("a", 5), ("b", 5), ("c", 1), ("d", 9)])
    assert pr2["a"] == pr2["b"]
    assert pr2["c"] == 0.0 and pr2["d"] == 1.0


# ---------- fixture ----------

def _make_run(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    cands = [
        {"a": "A", "b": "B", "reason": "token_overlap:t1,t2,t3", "n_companies": 2},  # 0
        {"a": "A", "b": "C", "reason": "token_overlap:t1", "n_companies": 2},         # 1
        {"a": "A", "b": "D", "reason": "token_overlap:t1", "n_companies": 2},         # 2
        {"a": "E", "b": "F", "reason": "token_overlap:t1,t2", "n_companies": 2},      # 3
        {"a": "G", "b": "H", "reason": "token_overlap:t1", "n_companies": 2},         # 4
        {"a": "I", "b": "J", "reason": "token_overlap:t1", "n_companies": 2},         # 5
        {"a": "K", "b": "L", "reason": "token_overlap:t1", "n_companies": 2},         # 6 -> SAME
        {"a": "M", "b": "N", "reason": "token_overlap:t1", "n_companies": 2},         # 7 -> unjudged
    ]
    # idx0 engineered to dominate all three signals: top adjacency (A-hub), latest position, top reason
    plan = {"batches": [{"id": 0, "idx": [3, 4, 0]},      # idx0 is LAST -> frac 1.0
                        {"id": 1, "idx": [1, 2, 5]}]}
    review = {"reviews": [
        {"idx": 0, "a": "A", "b": "B", "verdict": "DIFFERENT"},
        {"idx": 1, "a": "A", "b": "C", "verdict": "DIFFERENT"},
        {"idx": 2, "a": "A", "b": "D", "verdict": "UNCLEAR"},
        {"idx": 3, "a": "E", "b": "F", "verdict": "DIFFERENT"},
        {"idx": 4, "a": "G", "b": "H", "verdict": "DIFFERENT"},
        {"idx": 5, "a": "I", "b": "J", "verdict": "UNCLEAR"},
        {"idx": 6, "a": "K", "b": "L", "verdict": "SAME"},      # excluded (merged, not a hunting ground)
        # idx7 deliberately absent -> unjudged -> excluded
    ]}
    (run / "repair_candidates.json").write_text(json.dumps({"candidates": cands, "count": len(cands)}))
    (run / "repair_plan.json").write_text(json.dumps(plan))
    (run / "repair_review.json").write_text(json.dumps(review))
    return run


def test_eligible_excludes_same_and_unjudged(tmp_path):
    run = _make_run(tmp_path)
    rows = build_rows(json.load(open(run / "repair_candidates.json"))["candidates"],
                      json.load(open(run / "repair_plan.json")),
                      json.load(open(run / "repair_review.json")))
    idxs = {r["idx"] for r in rows}
    assert 6 not in idxs   # SAME excluded
    assert 7 not in idxs   # unjudged excluded
    assert idxs == {0, 1, 2, 3, 4, 5}


def test_top_ranked_pair_dominates_all_three_signals(tmp_path):
    run = _make_run(tmp_path)
    rows = build_rows(json.load(open(run / "repair_candidates.json"))["candidates"],
                      json.load(open(run / "repair_plan.json")),
                      json.load(open(run / "repair_review.json")))
    top = rows[0]
    assert top["idx"] == 0
    assert top["reason_score"] == 3
    assert top["adjacency"] == 4          # deg(A)=3 + deg(B)=1
    assert top["position"] == 2 and top["batch_size"] == 3 and top["position_frac"] == 1.0
    assert top["composite"] == max(r["composite"] for r in rows)


def test_confirm_flipped_rows_are_excluded(tmp_path):
    # proposer SAME -> blind isolated confirm DIFFERENT (confirmed:true): already isolated,
    # NOT an anchoring hunting ground.
    run = tmp_path / "run"
    run.mkdir()
    cands = [{"a": "A", "b": "B", "reason": "token_overlap:t1,t2", "n_companies": 2},   # 0 proposer-DIFF
             {"a": "C", "b": "D", "reason": "token_overlap:t1", "n_companies": 2}]       # 1 confirm-flipped
    plan = {"batches": [{"id": 0, "idx": [0, 1]}]}
    review = {"reviews": [
        {"idx": 0, "a": "A", "b": "B", "verdict": "DIFFERENT"},                  # eligible
        {"idx": 1, "a": "C", "b": "D", "verdict": "DIFFERENT", "confirmed": True},  # excluded
    ]}
    (run / "repair_candidates.json").write_text(json.dumps({"candidates": cands, "count": 2}))
    (run / "repair_plan.json").write_text(json.dumps(plan))
    (run / "repair_review.json").write_text(json.dumps(review))
    blob = select_stratum(run, n_stratum=100, n_noise=40)
    assert blob["n_eligible"] == 1
    assert blob["stratum_idx"] == [0]
    assert blob["n_confirm_flipped_excluded"] == 1


def _srow(idx, adj, pos, rsn, comp):
    return {"idx": idx, "adjacency": adj, "position_frac": pos, "reason_score": rsn,
            "composite": comp}


def test_select_indices_guarantees_each_signal_extreme():
    rows = [
        _srow(0, 0.99, 0.50, 0.50, 0.99),   # adjacency extreme + top composite
        _srow(1, 0.90, 0.99, 0.40, 0.95),   # position extreme
        _srow(2, 0.20, 0.20, 0.99, 0.10),   # reason extreme BUT low composite -> must still be in
        _srow(3, 0.85, 0.80, 0.60, 0.90),
        _srow(4, 0.70, 0.70, 0.55, 0.80),
        _srow(5, 0.60, 0.60, 0.45, 0.70),
        _srow(6, 0.50, 0.50, 0.35, 0.60),
    ]
    ranked, noise, admitted = select_indices(rows, n_stratum=6, n_noise=3, per_signal=2)
    assert 2 in ranked                       # low-composite reason extreme is guaranteed in
    assert "reason" in admitted[2]
    assert "adjacency" in admitted[0]
    assert "position" in admitted[1]
    assert ranked[-1] == 2                    # but it ranks LAST (lowest composite)
    filler = [i for i in ranked if admitted[i] == ["composite"]]
    assert all(i not in (0, 1, 2, 3) for i in filler)


def test_select_indices_noise_spread_not_top40():
    # 100 eligible, strictly decreasing composite so composite-rank == idx
    rows = [_srow(i, 1 - i / 100, 1 - i / 100, 1 - i / 100, 1 - i / 1000) for i in range(100)]
    ranked, noise, _ = select_indices(rows, n_stratum=100, n_noise=40, per_signal=25)
    assert len(ranked) == 100 and len(noise) == 40
    assert noise[0] == ranked[0] and noise[-1] == ranked[99]   # spans the whole range
    assert noise != ranked[:40]                                # NOT the top-40
    expected_ranks = sorted({round(j * 99 / 39) for j in range(40)})
    assert [ranked.index(i) for i in noise] == expected_ranks


def test_select_stratum_writes_file_with_tags(tmp_path):
    run = _make_run(tmp_path)
    blob = select_stratum(run, n_stratum=4, n_noise=2, per_signal=2)
    assert blob["n_eligible"] == 6
    assert blob["n_stratum"] == 4 and blob["n_noise"] == 2
    assert set(blob["noise_idx"]).issubset(set(blob["stratum_idx"]))
    assert "admit_counts" in blob
    on_disk = json.load(open(run / "ab_stratum.json"))
    assert on_disk["stratum_idx"] == blob["stratum_idx"]
    srows = [r for r in on_disk["rows"] if r["in_stratum"]]
    assert all(r["admitted_by"] and isinstance(r["rank"], int) for r in srows)
