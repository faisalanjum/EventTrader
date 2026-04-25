"""Layer 5: documentation-as-test for the renderer's new public API.

Strictly redundant with `test_renderer_imports`' identity check + the golden
tests' OLD-path execution. Kept anyway because:

  1. **Documentation-as-test**: explicitly demonstrates that the intended
     public usage `from scripts.earnings.renderer import render_bundle_text`
     works as a callable end-to-end (not just an importable reference).
  2. **Defense-in-depth**: catches any future regression where someone
     modifies renderer/__init__.py in a way that wraps the function or
     breaks the import chain in a manner the identity test wouldn't notice.

Cost: 4 byte-equality calls against the golden fixtures already on disk.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

# IMPORTANT: this is the NEW path (via renderer package's __init__.py),
# distinct from every other test file which imports via `from
# earnings_orchestrator import render_bundle_text`.
from scripts.earnings.renderer import render_bundle_text  # noqa: E402

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
def test_new_path_render_bundle_text(ticker, quarter):
    """`from scripts.earnings.renderer import render_bundle_text` is callable
    end-to-end and produces byte-identical output to the captured golden."""
    bundle = json.loads(
        (BUNDLES / f"{ticker}_{quarter}.json").read_text(encoding="utf-8")
    )
    actual = render_bundle_text(bundle)
    expected = (GOLDEN / f"{ticker}_{quarter}.txt").read_text(encoding="utf-8")
    assert actual == expected, f"new-path render drift for {ticker} {quarter}"
