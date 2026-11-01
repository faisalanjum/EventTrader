from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_historical_baskets import best_candidate  # noqa: E402


def _candidate(
    verdict: str,
    observations: int,
    mae: float,
    minimum_coverage: float = 0.8,
):
    return {
        "method": verdict,
        "minimum_weight_coverage": minimum_coverage,
        "comparison": {
            "numerical_verdict": verdict,
            "full_period": {
                "observations": observations,
                "mean_absolute_error_pp": mae,
            },
        },
    }


def test_best_candidate_prefers_verdict_then_error_then_history():
    candidates = [
        _candidate("context_only", 800, 0.10),
        _candidate("strong", 700, 0.20),
        _candidate("strong", 800, 0.30),
        _candidate("strong", 799, 0.15),
    ]

    assert best_candidate(candidates)["comparison"]["full_period"][
        "mean_absolute_error_pp"
    ] == 0.15


def test_best_candidate_can_exclude_low_coverage_sensitivity_runs():
    candidates = [
        _candidate("strong", 830, 0.10, minimum_coverage=0.75),
        _candidate("context_only", 800, 0.20, minimum_coverage=0.8),
    ]

    assert best_candidate(
        candidates,
        decision_minimum_coverage=0.8,
    )["comparison"]["numerical_verdict"] == "context_only"


def test_best_candidate_prefers_more_history_when_all_candidates_reject():
    candidates = [
        _candidate("reject", 8, 0.12),
        _candidate("reject", 617, 0.20),
    ]

    assert best_candidate(candidates)["comparison"]["full_period"][
        "observations"
    ] == 617
