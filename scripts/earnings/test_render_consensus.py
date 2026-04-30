#!/usr/bin/env python3
"""U8 — Forward Estimates renderer schema rename + delta columns.

Verifies that `_render_consensus_history` reads the actual builder field
names (epsEstimateAverage, epsRevisionXdAgo, epsRevisionDeltaXd, etc.)
and renders an 11-column table including raw revision values, delta
columns, and analyst counts for both EPS and Revenue.

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_consensus -v
    venv/bin/python -m pytest scripts/earnings/test_render_consensus.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_consensus_history


def _bundle_with_forward(forward_rows):
    return {
        "consensus": {
            "schema_version": "consensus.v1",
            "ticker": "TST",
            "source_mode": "live",
            "quarterly_rows": [],
            "forward_estimates": forward_rows,
            "summary": {},
            "gaps": [],
        },
        "builder_errors": {},
    }


class ForwardEstimatesTests(unittest.TestCase):
    def test_u8_full_row_renders_all_columns(self):
        """All builder fields produce populated cells; period uses horizon tag."""
        text = _render_consensus_history(_bundle_with_forward([{
            "fiscalDateEnding": "2026-04-30",
            "horizon": "fiscal quarter",
            "epsEstimateAverage": 1.739,
            "epsRevision7dAgo": 1.739,
            "epsRevision30dAgo": 1.793,
            "epsRevision60dAgo": 1.787,
            "epsRevision90dAgo": 1.804,
            "epsRevisionDelta30d": -0.054,
            "epsRevisionDelta90d": -0.065,
            "revenueEstimateAverage": 2_781_164_760.0,
            "epsAnalystCount": 16,
            "revenueAnalystCount": 14,
        }]))
        # Header signals new schema
        self.assertIn("Forward Estimates", text)
        self.assertIn("EPS Cur", text)
        self.assertIn("Δ30d", text)
        self.assertIn("Δ90d", text)
        self.assertIn("Revenue Est", text)
        self.assertIn("EPS Analysts", text)
        self.assertIn("Rev Analysts", text)
        # Period tag from horizon
        self.assertIn("2026-04-30 (Q)", text)
        # Raw values
        self.assertIn("$1.739", text)
        self.assertIn("$1.804", text)
        # Signed deltas
        self.assertIn("-$0.054", text)
        self.assertIn("-$0.065", text)
        # Revenue + analyst counts
        self.assertIn("$2.78B", text)
        self.assertIn("| 16 |", text)
        self.assertIn("| 14 |", text)

    def test_u8_fiscal_year_period_tag(self):
        """horizon='fiscal year' → (FY) tag."""
        text = _render_consensus_history(_bundle_with_forward([{
            "fiscalDateEnding": "2027-01-31",
            "horizon": "fiscal year",
            "epsEstimateAverage": 11.441,
            "revenueEstimateAverage": 12.7e9,
        }]))
        self.assertIn("2027-01-31 (FY)", text)

    def test_u8_missing_fields_render_as_dash(self):
        """Bare row with only fiscalDateEnding still renders without crash."""
        text = _render_consensus_history(_bundle_with_forward([{
            "fiscalDateEnding": "2026-04-30",
            "horizon": "fiscal quarter",
        }]))
        self.assertIn("2026-04-30", text)
        self.assertIn("—", text)

    def test_u8_positive_delta_has_plus_sign(self):
        text = _render_consensus_history(_bundle_with_forward([{
            "fiscalDateEnding": "2026-04-30",
            "horizon": "fiscal quarter",
            "epsRevisionDelta30d": 0.075,
        }]))
        self.assertIn("+$0.075", text)

    def test_u8_zero_delta_no_sign(self):
        """Zero delta renders as '$0.000' without sign (true zero, not — )."""
        text = _render_consensus_history(_bundle_with_forward([{
            "fiscalDateEnding": "2026-04-30",
            "horizon": "fiscal quarter",
            "epsRevisionDelta30d": 0.0,
        }]))
        self.assertIn("$0.000", text)

    def test_u8_zero_analyst_count_not_swallowed_to_dash(self):
        """epsAnalystCount=0 must render as '0', NOT '—' (regression for or-falsy bug)."""
        text = _render_consensus_history(_bundle_with_forward([{
            "fiscalDateEnding": "2026-04-30",
            "horizon": "fiscal quarter",
            "epsAnalystCount": 0,
            "revenueAnalystCount": 0,
        }]))
        self.assertIn("| 0 |", text)


if __name__ == "__main__":
    unittest.main()
