"""Layer 1: full-bundle byte equality + sha256 for the renderer.

These tests load each saved bundle from tests/fixtures/golden_bundles/,
re-render via render_bundle_text(), and assert byte-equality against the
captured golden. Failure means the renderer produces different output for
the same input — the load-bearing safety net for the renderer extraction.

Tests use the OLD path (`from earnings_orchestrator import render_bundle_text`)
so they pass against the unchanged orchestrator AND throughout the migration
via the consolidated shim block.
"""
from __future__ import annotations
import json
import hashlib
import sys
from pathlib import Path
import pytest

# sys.path setup matches existing test_*.py convention in this repo
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from earnings_orchestrator import render_bundle_text   # noqa: E402

FIX = THIS_DIR / "tests" / "fixtures"
BUNDLES = FIX / "golden_bundles"
GOLDEN = FIX / "golden_renders" / "full"
EVENTS = [
    ("CHRW", "Q4_FY2025"),
    ("AVGO", "Q3_FY2023"),
    ("AVGO", "Q4_FY2023"),
    ("CXM",  "Q4_FY2026"),
]


@pytest.mark.regression
@pytest.mark.parametrize("ticker,quarter", EVENTS)
def test_full_bundle_byte_equality(ticker, quarter):
    bundle = json.loads(
        (BUNDLES / f"{ticker}_{quarter}.json").read_text(encoding="utf-8")
    )
    actual = render_bundle_text(bundle)
    expected = (GOLDEN / f"{ticker}_{quarter}.txt").read_text(encoding="utf-8")
    assert actual == expected, f"renderer drift detected for {ticker} {quarter}"


@pytest.mark.regression
@pytest.mark.parametrize("ticker,quarter", EVENTS)
def test_full_bundle_sha256(ticker, quarter):
    bundle = json.loads(
        (BUNDLES / f"{ticker}_{quarter}.json").read_text(encoding="utf-8")
    )
    actual_hash = hashlib.sha256(render_bundle_text(bundle).encode("utf-8")).hexdigest()
    expected_hash = (GOLDEN / f"{ticker}_{quarter}.sha256").read_text(encoding="utf-8").strip()
    assert actual_hash == expected_hash
