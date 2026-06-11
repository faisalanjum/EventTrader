import sys
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKFLOWS))

from ab_differ import (binom_sf_ge, diff_arms, lost_merge, noise_floor,  # noqa: E402
                       position_analysis, wilson_upper)


def rv(idx, verdict):
    return {"idx": idx, "a": f"a{idx}", "b": f"b{idx}", "verdict": verdict}


def arm(rows):
    return {"reviews": rows}


# ---------- math helpers ----------

def test_binom_sf_ge_edges():
    assert binom_sf_ge(0, 50, 0.1) == 1.0          # P(X>=0)=1
    assert binom_sf_ge(1, 10, 0.0) == 0.0          # impossible under p=0
    # significantly above the floor -> tiny tail
    assert binom_sf_ge(20, 50, 0.03) < 0.001
    # at/under the mean -> large tail
    assert binom_sf_ge(2, 50, 0.07) > 0.5


def test_wilson_upper_bounds_zero_count():
    u = wilson_upper(0, 50)
    assert 0 < u < 0.1            # 0/50 still has a non-trivial upper bound
    assert wilson_upper(0, 300) < u   # more data -> tighter


# ---------- lost-merge ----------

def test_lost_merge_counts_solo_same_among_stratum():
    lm = lost_merge([0, 1, 2, 3],
                    arm([rv(0, "SAME"), rv(1, "DIFFERENT"), rv(2, "SAME"), rv(3, "UNCLEAR")]))
    assert lm["lost"] == 2 and lm["n_judged"] == 4 and lm["rate"] == 0.5
    assert sorted(lm["lost_idx"]) == [0, 2]


def test_lost_merge_flags_missing_arm2_coverage():
    lm = lost_merge([0, 1, 2], arm([rv(0, "DIFFERENT"), rv(1, "SAME")]))  # idx2 missing
    assert lm["n_stratum"] == 3 and lm["n_judged"] == 2


# ---------- noise floor ----------

def test_noise_floor_directional_flip_to_same_pooled():
    a3a = arm([rv(0, "DIFFERENT"), rv(1, "DIFFERENT"), rv(2, "SAME"), rv(3, "DIFFERENT")])
    a3b = arm([rv(0, "SAME"), rv(1, "DIFFERENT"), rv(2, "SAME"), rv(3, "DIFFERENT")])
    nf = noise_floor([0, 1, 2, 3], a3a, a3b)
    assert nf["disagree"] == 1 and nf["disagreement_rate"] == 0.25
    # base_notsame trials = idx0(1) + idx1(2) + idx3(2) = 5 ; to_same = 1 (idx0 a->b)
    assert nf["to_same"] == 1 and nf["base_notsame_trials"] == 5
    assert abs(nf["floor_rate"] - 0.2) < 1e-9
    assert nf["degenerate"] is True       # thin floor (base_notsame < 10)


def test_noise_floor_nondegenerate_when_enough_trials():
    a3a = arm([rv(i, "DIFFERENT") for i in range(40)])
    a3b = arm([rv(i, "SAME" if i < 5 else "DIFFERENT") for i in range(40)])
    nf = noise_floor(list(range(40)), a3a, a3b)
    # base_notsame = 40 (a all not-same) + 35 (b not-same) = 75 ; to_same = 5
    assert nf["base_notsame_trials"] == 75 and nf["to_same"] == 5
    assert nf["degenerate"] is False


# ---------- position analysis ----------

def test_position_analysis_late_minus_early_gradient():
    rows = [
        {"idx": 0, "position": 0, "batch_size": 10},   # early
        {"idx": 1, "position": 8, "batch_size": 10},   # late
        {"idx": 2, "position": 9, "batch_size": 10},   # late
        {"idx": 3, "position": 1, "batch_size": 10},   # early
    ]
    a2 = arm([rv(0, "DIFFERENT"), rv(1, "SAME"), rv(2, "SAME"), rv(3, "DIFFERENT")])
    pa = position_analysis(rows, [0, 1, 2, 3], a2)
    assert pa["buckets"]["early"]["same_rate"] == 0.0
    assert pa["buckets"]["late"]["same_rate"] == 1.0
    assert pa["late_minus_early_same_rate"] == 1.0


# ---------- full differ verdict ----------

def _rows(n):
    return [{"idx": i, "position": 0, "batch_size": 10} for i in range(n)]


def test_diff_arms_go_when_lost_within_noise_floor():
    stratum = {"stratum_idx": list(range(50)), "noise_idx": list(range(40)), "rows": _rows(50)}
    a2 = arm([rv(i, "SAME" if i < 2 else "DIFFERENT") for i in range(50)])   # lost 2/50 = 0.04
    a3a = arm([rv(i, "DIFFERENT") for i in range(40)])
    a3b = arm([rv(i, "SAME" if i < 5 else "DIFFERENT") for i in range(40)])  # floor ~0.067, non-degenerate
    rep = diff_arms(stratum, a2, a3a, a3b)
    assert rep["noise"]["degenerate"] is False
    assert rep["gate"]["lost_merge_rate"] <= rep["gate"]["noise_floor_rate"]
    assert rep["gate"]["significant_excess"] is False
    assert rep["verdict"] == "GO"


def test_diff_arms_nogo_on_significant_excess():
    stratum = {"stratum_idx": list(range(50)), "noise_idx": list(range(40)), "rows": _rows(50)}
    a2 = arm([rv(i, "SAME" if i < 20 else "DIFFERENT") for i in range(50)])  # lost 20/50 = 0.4
    a3a = arm([rv(i, "DIFFERENT") for i in range(40)])
    a3b = arm([rv(i, "SAME" if i < 2 else "DIFFERENT") for i in range(40)])  # floor ~0.026, non-degenerate
    rep = diff_arms(stratum, a2, a3a, a3b)
    assert rep["noise"]["degenerate"] is False
    assert rep["gate"]["significant_excess"] is True
    assert rep["verdict"] == "NO-GO"


def test_diff_arms_degenerate_floor_flagged():
    stratum = {"stratum_idx": list(range(50)), "noise_idx": list(range(40)), "rows": _rows(50)}
    a2 = arm([rv(i, "SAME" if i < 3 else "DIFFERENT") for i in range(50)])
    a3a = arm([rv(i, "DIFFERENT") for i in range(40)])
    a3b = arm([rv(i, "DIFFERENT") for i in range(40)])     # zero flips -> degenerate floor
    rep = diff_arms(stratum, a2, a3a, a3b)
    assert rep["noise"]["degenerate"] is True
    assert any("DEGENERATE" in f for f in rep["flags"])
    assert rep["basis"].startswith("degenerate-floor")


def test_diff_arms_late_position_smoking_gun_flag():
    rows = [{"idx": i, "position": (9 if i < 8 else 0), "batch_size": 10} for i in range(50)]
    stratum = {"stratum_idx": list(range(50)), "noise_idx": list(range(40)), "rows": rows}
    # the 8 late pairs all flip to SAME under solo judging -> anchoring signal
    a2 = arm([rv(i, "SAME" if i < 8 else "DIFFERENT") for i in range(50)])
    a3a = arm([rv(i, "DIFFERENT") for i in range(40)])
    a3b = arm([rv(i, "SAME" if i < 6 else "DIFFERENT") for i in range(40)])
    rep = diff_arms(stratum, a2, a3a, a3b)
    assert rep["position"]["late_minus_early_same_rate"] > 0
    assert any("LATE-POSITION" in f for f in rep["flags"])


def test_diff_arms_coverage_gap_flag():
    stratum = {"stratum_idx": list(range(50)), "noise_idx": list(range(40)), "rows": _rows(50)}
    a2 = arm([rv(i, "DIFFERENT") for i in range(45)])      # 5 stratum pairs unjudged
    a3a = arm([rv(i, "DIFFERENT") for i in range(40)])
    a3b = arm([rv(i, "DIFFERENT") for i in range(40)])
    rep = diff_arms(stratum, a2, a3a, a3b)
    assert any("COVERAGE GAP" in f for f in rep["flags"])
