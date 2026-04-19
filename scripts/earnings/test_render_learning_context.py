#!/usr/bin/env python3
"""R1-R4 tests for _render_learning_context tuple refactor (T1).

Per .claude/plans/learner.md Appendix B §9.2:
  R1: Empty learning_context → (text_with_first_prediction_message, [])
  R2: Ticker lessons with predictor_lessons + data_lessons + why → list excludes data + why
  R3: Globals: 2 sector + 1 macro + 2 cross_ticker → list order is sector, sector, macro, cross, cross
  R4: Mixed ticker + global → render text contains all bullets; list contains only
      labeled lessons in order

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_learning_context -v
    venv/bin/python scripts/earnings/test_render_learning_context.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_learning_context, _normalize_lesson_text


class RenderLearningContextTests(unittest.TestCase):
    """Tuple-return renderer: (text, ordered_lesson_texts)."""

    def test_R1_empty_context_returns_empty_list(self):
        """Empty learning_context → (text with 'No prior lessons...' message, [])."""
        ctx: dict = {}
        text, ordered = _render_learning_context(ctx)
        self.assertIsInstance(text, str)
        self.assertIn("Prior Lessons", text)
        self.assertIn("No prior lessons available", text)
        self.assertEqual(ordered, [])

    def test_R1b_explicit_empty_arrays(self):
        """ticker_lessons=[] and global_lessons=[] explicitly set → ordered=[]."""
        ctx = {"ticker_lessons": [], "global_lessons": []}
        text, ordered = _render_learning_context(ctx)
        self.assertEqual(ordered, [])
        self.assertIn("No prior lessons available", text)

    def test_R2_ticker_lessons_exclude_data_and_why(self):
        """predictor_lessons labeled; data_lessons + why excluded from list."""
        ctx = {
            "ticker_lessons": [
                {
                    "quarter_label": "Q1_FY2023",
                    "direction_correct": True,
                    "actual_daily_pct": 2.5,
                    "predicted_direction": "long",
                    "primary_driver_category": "eps_surprise",
                    "predictor_lessons": [
                        "Lesson P1 should be labeled",
                        "Lesson P2 also labeled",
                    ],
                    "data_lessons": [
                        "Data fetch heuristic D1 NOT labeled",
                    ],
                    "why": "This is metadata why — NOT labeled",
                },
            ],
            "global_lessons": [],
        }
        text, ordered = _render_learning_context(ctx)
        # List must contain only the 2 predictor_lessons, in order
        self.assertEqual(ordered, [
            "Lesson P1 should be labeled",
            "Lesson P2 also labeled",
        ])
        # Render must contain ALL bullets (Predictor + Data + Why) for operator visibility
        self.assertIn("Lesson P1 should be labeled", text)
        self.assertIn("Data fetch heuristic D1 NOT labeled", text)
        self.assertIn("This is metadata why", text)
        self.assertIn("- Predictor:", text)
        self.assertIn("- Data:", text)
        self.assertIn("- Why:", text)

    def test_R3_global_scope_order_sector_macro_cross_ticker(self):
        """Global lessons emitted in scope order: sector, then macro, then cross_ticker."""
        ctx = {
            "ticker_lessons": [],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "AAPL", "lesson": "SEC-A sector lesson"},
                {"scope": "cross_ticker", "related_tickers": ["AAPL", "MSFT"],
                 "source_ticker": "AAPL", "lesson": "CT-A cross_ticker lesson"},
                {"scope": "macro", "source_ticker": "AAPL", "lesson": "MA-A macro lesson"},
                {"scope": "sector", "target_sector": "Healthcare",
                 "source_ticker": "JNJ", "lesson": "SEC-B sector lesson"},
                {"scope": "cross_ticker", "related_tickers": ["NVDA"],
                 "source_ticker": "NVDA", "lesson": "CT-B cross_ticker lesson"},
            ],
        }
        text, ordered = _render_learning_context(ctx)
        # Expected order: sector (2), then macro (1), then cross_ticker (2)
        self.assertEqual(ordered, [
            "SEC-A sector lesson",
            "SEC-B sector lesson",
            "MA-A macro lesson",
            "CT-A cross_ticker lesson",
            "CT-B cross_ticker lesson",
        ])
        # Render contains all 5
        for expected in ordered:
            self.assertIn(expected, text)
        # Headings present
        self.assertIn("Sector Lessons", text)
        self.assertIn("Macro Lessons", text)
        self.assertIn("Cross-Ticker Lessons", text)

    def test_R4_mixed_ticker_and_global_preserves_order(self):
        """Ticker lessons first (in array order), then scope-ordered globals."""
        ctx = {
            "ticker_lessons": [
                {
                    "quarter_label": "Q1_FY2023",
                    "direction_correct": False,
                    "actual_daily_pct": -3.1,
                    "predicted_direction": "long",
                    "primary_driver_category": "guidance_change",
                    "predictor_lessons": ["T1-Q1-pl1", "T1-Q1-pl2"],
                    "data_lessons": ["IGNORE-data"],
                },
                {
                    "quarter_label": "Q2_FY2023",
                    "direction_correct": True,
                    "actual_daily_pct": 1.2,
                    "predicted_direction": "short",
                    "primary_driver_category": "eps_surprise",
                    "predictor_lessons": ["T2-Q2-pl1"],
                },
            ],
            "global_lessons": [
                {"scope": "macro", "source_ticker": "AAPL", "lesson": "G-macro-1"},
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "AAPL", "lesson": "G-sector-1"},
            ],
        }
        text, ordered = _render_learning_context(ctx)
        # Expected: ticker lessons first (Q1 pl1, Q1 pl2, Q2 pl1), then sector, then macro
        self.assertEqual(ordered, [
            "T1-Q1-pl1",
            "T1-Q1-pl2",
            "T2-Q2-pl1",
            "G-sector-1",
            "G-macro-1",
        ])
        # data_lesson must NOT be in ordered
        self.assertNotIn("IGNORE-data", ordered)
        # But it IS in rendered text
        self.assertIn("IGNORE-data", text)


class NormalizeLessonTextTests(unittest.TestCase):
    """Helper used for positional comparison and analysis substring floor."""

    def test_normalize_whitespace_collapsed(self):
        self.assertEqual(
            _normalize_lesson_text("  Hello   World\t\tnewlines\n"),
            "hello world newlines",
        )

    def test_normalize_case_folded(self):
        self.assertEqual(
            _normalize_lesson_text("AI Revenue Surge"),
            "ai revenue surge",
        )

    def test_normalize_none_returns_empty(self):
        self.assertEqual(_normalize_lesson_text(None), "")

    def test_normalize_empty_returns_empty(self):
        self.assertEqual(_normalize_lesson_text(""), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
