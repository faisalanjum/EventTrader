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
from scripts.earnings.renderer.header import _format_assembled_at


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


# U61 helper: bundle factory that accepts custom assembled_at value
# (or omits the key entirely via the _OMIT sentinel).
_OMIT = object()


def _bundle_with_assembled(asm=_OMIT, **kwargs) -> dict:
    """Build a bundle, optionally setting bundle['assembled_at']."""
    bundle = _bundle(**kwargs)
    if asm is not _OMIT:
        bundle["assembled_at"] = asm
    return bundle


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


class U61AssembledAtTests(unittest.TestCase):
    """U61/R1 — surface bundle.assembled_at in §1.0 Mode line."""

    # ─── Helper: _format_assembled_at ─────────────────────────────────

    def test_format_strips_microseconds_and_renders_z_suffix(self):
        # Canonical orchestrator output: ISO with microseconds + +00:00
        out = _format_assembled_at("2026-04-19T17:47:35.272294+00:00")
        self.assertEqual(out, "2026-04-19T17:47:35Z")

    def test_format_handles_z_suffix_input(self):
        # Some upstreams emit Z form directly
        out = _format_assembled_at("2026-04-19T17:47:35Z")
        self.assertEqual(out, "2026-04-19T17:47:35Z")

    def test_format_handles_z_suffix_with_microseconds(self):
        out = _format_assembled_at("2026-04-19T17:47:35.272294Z")
        self.assertEqual(out, "2026-04-19T17:47:35Z")

    def test_format_normalizes_non_utc_offset_to_utc(self):
        # -05:00 means "5 hours behind UTC" → 17:47:35-05:00 == 22:47:35Z
        out = _format_assembled_at("2026-04-19T17:47:35-05:00")
        self.assertEqual(out, "2026-04-19T22:47:35Z")

    def test_format_rejects_naive_datetime(self):
        # Naive (no tz) input is malformed by orchestrator contract
        out = _format_assembled_at("2026-04-19T17:47:35")
        self.assertIsNone(out)

    def test_format_returns_none_for_missing(self):
        self.assertIsNone(_format_assembled_at(None))

    def test_format_returns_none_for_empty_string(self):
        self.assertIsNone(_format_assembled_at(""))

    def test_format_returns_none_for_non_string(self):
        self.assertIsNone(_format_assembled_at(12345))
        self.assertIsNone(_format_assembled_at({"x": 1}))
        self.assertIsNone(_format_assembled_at(["2026-04-19"]))

    def test_format_returns_none_for_unparseable(self):
        self.assertIsNone(_format_assembled_at("not-a-date"))
        self.assertIsNone(_format_assembled_at("TBD"))
        self.assertIsNone(_format_assembled_at("2026/04/19"))

    # ─── Mode-line integration via _render_header ─────────────────────

    def test_assembled_at_appended_in_historical_mode(self):
        b = _bundle_with_assembled("2026-04-19T17:47:35.272294+00:00")
        text = _render_header(b)
        mode_line = next(l for l in text.splitlines() if l.startswith("Mode:"))
        self.assertEqual(
            mode_line,
            "Mode: historical | PIT cutoff: 2023-12-07T16:18:51-05:00 "
            "| Assembled: 2026-04-19T17:47:35Z",
        )

    def test_assembled_at_appended_in_live_mode(self):
        b = _bundle_with_assembled("2026-04-19T17:47:35.272294+00:00")
        b["pit_cutoff"] = None
        text = _render_header(b)
        mode_line = next(l for l in text.splitlines() if l.startswith("Mode:"))
        self.assertEqual(mode_line, "Mode: live | Assembled: 2026-04-19T17:47:35Z")

    def test_assembled_at_omitted_when_bundle_field_missing(self):
        b = _bundle_with_assembled()  # asm omitted via sentinel
        text = _render_header(b)
        self.assertNotIn("Assembled:", text)

    def test_assembled_at_omitted_when_bundle_field_none(self):
        b = _bundle_with_assembled(None)
        text = _render_header(b)
        self.assertNotIn("Assembled:", text)

    def test_assembled_at_omitted_when_bundle_field_unparseable(self):
        b = _bundle_with_assembled("not-a-date")
        text = _render_header(b)
        self.assertNotIn("Assembled:", text)

    def test_assembled_at_omitted_when_bundle_field_naive(self):
        # Naive ISO → helper returns None → segment omitted
        b = _bundle_with_assembled("2026-04-19T17:47:35")
        text = _render_header(b)
        self.assertNotIn("Assembled:", text)

    def test_existing_4_line_shape_preserved_when_assembled_at_missing(self):
        # When the field is absent, output must be byte-identical to today.
        b = _bundle_with_assembled()
        text = _render_header(b)
        lines = text.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[3], "Mode: historical | PIT cutoff: 2023-12-07T16:18:51-05:00")


if __name__ == "__main__":
    unittest.main()
