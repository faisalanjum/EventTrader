from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_all63_replacement_matrix import (  # noqa: E402
    candidate_summary,
    classify_replacement,
)


def test_candidate_summary_keeps_decision_evidence():
    candidate = {
        "size": 50,
        "method": "daily_price_drift",
        "minimum_weight_coverage": 0.75,
        "comparison": {
            "numerical_verdict": "strong",
            "coverage": {
                "fraction": 0.997,
                "overlap_return_dates": 829,
                "target_return_dates": 831,
            },
            "full_period": {
                "observations": 829,
                "correlation": 0.991,
                "beta": 1.01,
                "mean_absolute_error_pp": 0.11,
            },
        },
    }

    assert candidate_summary(candidate) == {
        "verdict": "strong",
        "observations": 829,
        "target_coverage": 0.997,
        "correlation": 0.991,
        "beta": 1.01,
        "mean_absolute_error_pp": 0.11,
        "minimum_selected_weight": 0.75,
        "basket_size": 50,
        "method": "daily_price_drift",
    }


def test_replacement_classification_separates_ready_from_diagnostic():
    strong = {"verdict": "strong"}
    context = {"verdict": "context_only"}
    reject = {"verdict": "reject"}

    assert classify_replacement(
        exact_lse=True,
        invalid_mapping=False,
        historical_strict=reject,
        recent_strict=reject,
        historical_sensitivity=reject,
        recent_sensitivity=reject,
    ) == "exact_lse_recent"

    assert classify_replacement(
        exact_lse=False,
        invalid_mapping=True,
        historical_strict=None,
        recent_strict=None,
        historical_sensitivity=None,
        recent_sensitivity=None,
    ) == "invalid_production_mapping"

    assert classify_replacement(
        exact_lse=False,
        invalid_mapping=False,
        historical_strict=strong,
        recent_strict=strong,
        historical_sensitivity=strong,
        recent_sensitivity=strong,
    ) == "basket_strong_strict_both"

    assert classify_replacement(
        exact_lse=False,
        invalid_mapping=False,
        historical_strict=reject,
        recent_strict=reject,
        historical_sensitivity=strong,
        recent_sensitivity=strong,
    ) == "basket_strong_only_with_lower_coverage"

    assert classify_replacement(
        exact_lse=False,
        invalid_mapping=False,
        historical_strict=strong,
        recent_strict=context,
        historical_sensitivity=strong,
        recent_sensitivity=context,
    ) == "basket_partial_or_context"

    assert classify_replacement(
        exact_lse=False,
        invalid_mapping=False,
        historical_strict=reject,
        recent_strict=reject,
        historical_sensitivity=reject,
        recent_sensitivity=reject,
    ) == "no_supported_replacement"
