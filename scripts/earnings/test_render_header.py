#!/usr/bin/env python3
"""Targeted tests for _render_header — accession_8k + prev_8k_ts surfacing.

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_header -v
    venv/bin/python scripts/earnings/test_render_header.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_header


def _bundle(**qi_overrides) -> dict:
    qi = {
        "accession_8k": "0001730168-23-000093",
        "filed_8k": "2023-12-07T16:18:51-05:00",
        "market_session": "post_market",
        "period_of_report": "2023-10-29",
        "prev_8k_ts": "2023-08-31T17:18:57-04:00",
        "quarter_label": "Q4_FY2023",
    }
    qi.update(qi_overrides)
    return {
        "ticker": "AVGO",
        "quarter_info": qi,
        "pit_cutoff": "2023-12-07T16:18:51-05:00",
    }


class HeaderRenderTests(unittest.TestCase):
    def test_both_fields_present(self):
        text = _render_header(_bundle())
        self.assertIn("Accession: 0001730168-23-000093", text)
        self.assertIn("Prior 8-K: 2023-08-31T17:18:57-04:00 (98 days ago)", text)
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[2].startswith("Accession:"))
        self.assertTrue(lines[3].startswith("Mode:"))

    def test_calendar_delta_not_timedelta_floor(self):
        # cross-DST case where naive timedelta.days gives 97 instead of 98.
        text = _render_header(_bundle())
        self.assertIn("(98 days ago)", text)
        self.assertNotIn("(97 days ago)", text)

    def test_prev_8k_null_keeps_accession_only(self):
        text = _render_header(_bundle(prev_8k_ts=None))
        self.assertIn("Accession: 0001730168-23-000093", text)
        self.assertNotIn("Prior 8-K:", text)
        # No orphan separator after Accession token.
        self.assertNotIn("Accession: 0001730168-23-000093 | ", text)

    def test_accession_null_keeps_prior_only(self):
        text = _render_header(_bundle(accession_8k=None))
        self.assertNotIn("Accession:", text)
        self.assertIn("Prior 8-K: 2023-08-31T17:18:57-04:00 (98 days ago)", text)

    def test_both_null_omits_provenance_line(self):
        text = _render_header(_bundle(accession_8k=None, prev_8k_ts=None))
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertNotIn("Accession:", text)
        self.assertNotIn("Prior 8-K:", text)

    def test_unparseable_filed_falls_back_gracefully(self):
        # filed_8k missing → days cannot be computed; prev token still emits raw ts.
        text = _render_header(_bundle(filed_8k=None))
        self.assertIn("Prior 8-K: 2023-08-31T17:18:57-04:00", text)
        self.assertNotIn("days ago", text)

    def test_unparseable_prev_8k_falls_back_gracefully(self):
        # prev_8k_ts present but unparseable → timestamp prints, days omitted.
        text = _render_header(_bundle(prev_8k_ts="not-a-date"))
        self.assertIn("Prior 8-K: not-a-date", text)
        self.assertNotIn("days ago", text)

    def test_live_mode_still_renders_provenance(self):
        b = _bundle()
        b["pit_cutoff"] = None
        text = _render_header(b)
        self.assertIn("Accession: 0001730168-23-000093", text)
        self.assertIn("Mode: live", text)
        self.assertNotIn("PIT cutoff:", text)


if __name__ == "__main__":
    unittest.main()
