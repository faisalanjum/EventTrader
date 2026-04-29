#!/usr/bin/env python3
"""Targeted tests for §1.1 — `_render_results_and_expectations` Consensus Bar.

Covers est-vs-actual-vs-surprise rendering when the just-reported row exists,
2-column estimate-only rendering when actuals are absent, and the existing
[NO DATA] / [BUILDER ERROR] paths.

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_results -v
    venv/bin/python -m pytest scripts/earnings/test_render_results.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_results_and_expectations


def _bundle(*, current_row: dict | None = None,
            other_rows: list[dict] | None = None,
            ex991: str | None = "Press release stub",
            consensus_present: bool = True,
            builder_errors: dict | None = None) -> dict:
    rows = []
    if current_row is not None:
        rows.append({**current_row, "is_current_quarter": True})
    rows.extend(other_rows or [])
    consensus = None
    if consensus_present:
        consensus = {
            "schema_version": "consensus.v1",
            "ticker": "AVGO",
            "quarterly_rows": rows,
            "forward_estimates": [],
            "summary": {},
            "gaps": [],
        }
    packet = None
    if ex991 is not None:
        packet = {
            "exhibits_99": [{"exhibit_number": "EX-99.1", "content": ex991}],
        }
    return {
        "ticker": "AVGO",
        "consensus": consensus,
        "8k_packet": packet,
        "builder_errors": builder_errors or {},
    }


class ConsensusBarTests(unittest.TestCase):
    def test_full_beat_renders_4col_table_with_signed_surprise(self):
        # Historical full beat (AVGO Q4 FY2023 shape).
        text = _render_results_and_expectations(_bundle(current_row={
            "fiscalDateEnding": "2023-10-31",
            "estimatedEPS": 1.098,
            "reportedEPS": 1.106,
            "epsSurprisePct": 0.7286,
            "revenueEstimate": None,
            "revenueActual": 9295000000.0,
            "revenueSurprisePct": None,
        }))
        self.assertIn("### Consensus Bar", text)
        self.assertIn("| Metric  | Estimate | Actual | Surprise |", text)
        self.assertIn("$1.098", text)
        self.assertIn("$1.106", text)
        self.assertIn("+0.7%", text)
        # _fmt_money scales >=1e9 to .2f B; binary float rounding is locked here.
        self.assertIn("$9.29B", text)

    def test_revenue_surprise_renders_when_estimate_present(self):
        text = _render_results_and_expectations(_bundle(current_row={
            "estimatedEPS": 1.098,
            "reportedEPS": 1.106,
            "epsSurprisePct": 0.7286,
            "revenueEstimate": 8862740000.0,
            "revenueActual": 8876000000.0,
            "revenueSurprisePct": 0.15,
        }))
        self.assertIn("$8.86B", text)
        self.assertIn("$8.88B", text)
        self.assertIn("+0.1%", text)   # 0.15 rounded to 1dp = 0.1%

    def test_negative_surprise_renders_with_minus_sign(self):
        text = _render_results_and_expectations(_bundle(current_row={
            "estimatedEPS": 1.098,
            "reportedEPS": 1.030,
            "epsSurprisePct": -6.2,
            "revenueEstimate": 8862740000.0,
            "revenueActual": 8728000000.0,
            "revenueSurprisePct": -1.4,
        }))
        self.assertIn("-6.2%", text)
        self.assertIn("-1.4%", text)

    def test_estimate_only_renders_2col_when_no_actuals(self):
        # Pre-actuals — current row exists but reportedEPS / revenueActual absent.
        text = _render_results_and_expectations(_bundle(current_row={
            "estimatedEPS": 1.098,
            "reportedEPS": None,
            "epsSurprisePct": None,
            "revenueEstimate": 8862740000.0,
            "revenueActual": None,
            "revenueSurprisePct": None,
        }))
        self.assertIn("| Metric  | Estimate |", text)
        self.assertNotIn("| Metric  | Estimate | Actual | Surprise |", text)
        self.assertIn("$1.098", text)
        self.assertIn("$8.86B", text)

    def test_no_consensus_emits_no_data(self):
        text = _render_results_and_expectations(_bundle(consensus_present=False))
        self.assertIn("### Consensus Bar\n[NO DATA]", text)

    def test_builder_error_passes_through(self):
        text = _render_results_and_expectations(_bundle(
            consensus_present=False,
            builder_errors={"consensus": "AV rate-limited"},
        ))
        self.assertIn("[BUILDER ERROR: AV rate-limited]", text)


if __name__ == "__main__":
    unittest.main()
