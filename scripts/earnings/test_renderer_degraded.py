"""Layer 3: synthetic degraded fixtures for placeholder/edge-case coverage.

Real production bundles don't exercise every [BUILDER ERROR] / [NO DATA]
branch or every formatter edge case (None, NaN, ±Inf, very large/small).
These synthetic minimal-input bundles cover the gap.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from earnings_orchestrator import render_bundle_text  # noqa: E402  ← OLD path

# Fixture builders defined in tests/_degraded_fixtures.py
sys.path.insert(0, str(THIS_DIR / "tests"))
from _degraded_fixtures import DEGRADED_BUILDERS  # noqa: E402

GOLDEN_DEG = THIS_DIR / "tests" / "fixtures" / "golden_renders" / "degraded"


@pytest.mark.regression
@pytest.mark.parametrize("name,build_bundle", DEGRADED_BUILDERS)
def test_degraded_byte_equality(name, build_bundle):
    actual = render_bundle_text(build_bundle())
    expected = (GOLDEN_DEG / f"{name}.txt").read_text(encoding="utf-8")
    assert actual == expected
