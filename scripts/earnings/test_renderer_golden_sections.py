"""Layer 2: per-section byte equality for diagnostic granularity.

When the full-bundle goldens (Layer 1) fail, you know SOMETHING regressed
but not which renderer. These section-level tests pinpoint the broken
section. 40 parametrized cases (10 sections × 4 fixtures) + 8 lessons
cases (text + ordered_list per fixture).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from earnings_orchestrator import (   # noqa: E402  ← OLD path (works pre/during/post)
    _render_header,
    _render_results_and_expectations,
    _render_forward_guidance,
    _render_consensus_history,
    _render_prior_financials,
    _render_inter_quarter,
    _render_peer_earnings,
    _render_macro,
    _render_reference,
    _render_learning_context,
)

FIX = THIS_DIR / "tests" / "fixtures"
BUNDLES = FIX / "golden_bundles"
GOLDEN_SEC = FIX / "golden_renders" / "sections"
EVENTS = [
    ("CHRW", "Q4_FY2025"),
    ("AVGO", "Q3_FY2023"),
    ("AVGO", "Q4_FY2023"),
    ("CXM",  "Q4_FY2026"),
]

# (section_name, renderer) — lessons handled separately because tuple return
SECTIONS = [
    ("header",        _render_header),
    ("results",       _render_results_and_expectations),
    ("guidance",      _render_forward_guidance),
    ("consensus",     _render_consensus_history),
    ("financials",    _render_prior_financials),
    ("inter_quarter", _render_inter_quarter),
    ("peers",         _render_peer_earnings),
    ("macro",         _render_macro),
    ("reference",     _render_reference),
]


@pytest.mark.regression
@pytest.mark.parametrize("section,renderer", SECTIONS)
@pytest.mark.parametrize("ticker,quarter", EVENTS)
def test_section_byte_equality(section, renderer, ticker, quarter):
    bundle = json.loads(
        (BUNDLES / f"{ticker}_{quarter}.json").read_text(encoding="utf-8")
    )
    actual = renderer(bundle)
    expected = (GOLDEN_SEC / section / f"{ticker}_{quarter}.txt").read_text(encoding="utf-8")
    assert actual == expected


@pytest.mark.regression
@pytest.mark.parametrize("ticker,quarter", EVENTS)
def test_lessons_section_byte_equality(ticker, quarter):
    """_render_learning_context returns tuple (text, ordered_list)."""
    bundle = json.loads(
        (BUNDLES / f"{ticker}_{quarter}.json").read_text(encoding="utf-8")
    )
    lc = bundle.get("learning_context") or {}
    text, ordered = _render_learning_context(lc)
    expected_text = (GOLDEN_SEC / "lessons" / f"{ticker}_{quarter}.txt").read_text(encoding="utf-8")
    expected_ordered = json.loads(
        (GOLDEN_SEC / "lessons" / f"{ticker}_{quarter}.json").read_text(encoding="utf-8")
    )
    assert text == expected_text
    assert ordered == expected_ordered
