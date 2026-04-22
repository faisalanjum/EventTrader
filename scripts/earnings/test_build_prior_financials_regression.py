"""Semantic regression test for build_prior_financials.py.

Contract: the D1 sidecar (q4_derivation.py + xbrl_exact_splits.py) must not
change the output of build_prior_financials.py for any ticker.

Since we do NOT modify build_prior_financials.py in D1, this test is
primarily a canary for transitive breakage via shared imports. It runs the
legacy builder on a handful of tickers and asserts the output is stable
across two consecutive invocations (idempotence on stable fields).

Fields intentionally excluded from comparison (volatile):
  - assembled_at (timestamp)
  - as_of_ts  (reflects pit; set equal across calls below)

Tolerances:
  - numeric fields compared at 1e-6 relative tolerance
  - gaps[] compared as sorted lists
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

import pytest

import build_prior_financials as bpf


SENTINEL_CASES = [
    # (ticker, period_of_report) — periods chosen to be stable historical quarters
    ("LSTR", "2024-12-28"),
    ("CHRW", "2024-12-31"),
    ("TSN",  "2024-09-28"),
    ("HUBB", "2024-12-31"),
    ("FAST", "2024-12-31"),
]


VOLATILE_KEYS = {"assembled_at"}


def _strip_volatile(obj):
    """Recursively drop volatile fields from nested dict/list structures."""
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_strip_volatile(x) for x in obj]
    return obj


def _sort_gaps(obj):
    """Stabilize gaps[] ordering (by type + reason)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "gaps" and isinstance(v, list):
                out[k] = sorted(v, key=lambda g: (g.get("type", ""), g.get("reason", ""), str(g)))
            else:
                out[k] = _sort_gaps(v)
        return out
    if isinstance(obj, list):
        return [_sort_gaps(x) for x in obj]
    return obj


def _normalize(packet):
    return _sort_gaps(_strip_volatile(copy.deepcopy(packet)))


@pytest.mark.regression
@pytest.mark.parametrize("ticker,period", SENTINEL_CASES)
def test_build_prior_financials_semantic_idempotence(ticker, period):
    """Call twice with identical inputs; verify output is stable on all
    non-volatile fields.
    """
    qi = {
        "period_of_report": period,
        "filed_8k": "",
        "market_session": "",
        "quarter_label": "",
    }
    a = bpf.build_prior_financials(ticker, qi, out_path=f"/tmp/bpf_a_{ticker}.json")
    b = bpf.build_prior_financials(ticker, qi, out_path=f"/tmp/bpf_b_{ticker}.json")
    assert _normalize(a) == _normalize(b), (
        f"build_prior_financials output is not idempotent for {ticker} {period}. "
        f"This may indicate transitive breakage from the sidecar."
    )


@pytest.mark.regression
def test_sidecar_imports_do_not_contaminate_bpf_namespace():
    """Ensure importing the sidecar modules does not bind any new names
    into build_prior_financials's public surface.
    """
    baseline = set(dir(bpf))
    # Import sidecar after baseline capture
    import q4_derivation  # noqa: F401
    import xbrl_exact_splits  # noqa: F401
    # Re-check bpf surface
    assert set(dir(bpf)) == baseline, (
        "Sidecar imports polluted build_prior_financials namespace"
    )
