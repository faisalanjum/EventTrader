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


class RenderLearningContextPathsTests(unittest.TestCase):
    """R5/R5b/R6/R7/A1/A2 — learner_result path emission + allowlist block."""

    _PATH_AAPL_Q1 = "earnings-analysis/Companies/AAPL/events/Q1_FY2023/learning/result.md"
    _PATH_MSFT_Q2 = "earnings-analysis/Companies/MSFT/events/Q2_FY2024/learning/result.md"

    def _ticker_lesson(self, *, with_path: bool = False, **overrides) -> dict:
        L = {
            "quarter_label": "Q1_FY2023",
            "direction_correct": True,
            "actual_daily_pct": 1.0,
            "predicted_direction": "long",
            "primary_driver_category": "eps_surprise",
            "predictor_lessons": ["pl1"],
            "data_lessons": ["dl1"],
            "why": "why-text",
        }
        L.update(overrides)
        if with_path:
            L["learner_result_path"] = self._PATH_AAPL_Q1
        return L

    # ── R5: ticker-quarter learner_result line is emitted as last sub-bullet ──
    def test_R5_ticker_lesson_emits_learner_result_line_when_path_present(self):
        ctx = {
            "ticker_lessons": [self._ticker_lesson(with_path=True)],
            "global_lessons": [],
        }
        text, ordered = _render_learning_context(ctx)
        expected_line = f"  - learner_result: {self._PATH_AAPL_Q1}"
        self.assertIn(expected_line, text)
        # Must be the LAST sub-bullet of the quarter block (immediately before
        # the trailing blank-line separator). Find the line and verify it is
        # immediately followed by a blank line (split('\n') yields '' next).
        lines = text.split("\n")
        idx = lines.index(expected_line)
        self.assertEqual(lines[idx + 1], "",
                         "learner_result line must be the last sub-bullet (followed by blank separator)")

    # ── R5b: no line when ticker_lesson lacks the path ──
    def test_R5b_ticker_lesson_no_line_when_path_absent(self):
        ctx = {
            "ticker_lessons": [self._ticker_lesson(with_path=False)],
            "global_lessons": [],
        }
        text, ordered = _render_learning_context(ctx)
        self.assertNotIn("learner_result:", text)

    # ── R6: global-lesson continuation line under each scope bullet ──
    def test_R6_global_lesson_emits_learner_result_line_when_path_present(self):
        ctx = {
            "ticker_lessons": [],
            "global_lessons": [{
                "scope": "sector",
                "target_sector": "Technology",
                "source_ticker": "MSFT",
                "lesson": "sector lesson body",
                "learner_result_path": self._PATH_MSFT_Q2,
            }],
        }
        text, ordered = _render_learning_context(ctx)
        # 2-space continuation (NOT a sub-bullet — no leading `- `)
        expected_line = f"  learner_result: {self._PATH_MSFT_Q2}"
        self.assertIn(expected_line, text)
        # Specifically NOT the ticker-style "  - learner_result: ..." form
        self.assertNotIn(f"  - learner_result: {self._PATH_MSFT_Q2}", text)

    # ── R7: ordered-tuple element 2 (validator's source of truth) is unchanged
    #         whether or not learner_result_path keys are present ──
    def test_R7_ordered_tuple_unchanged_with_or_without_paths(self):
        # Without paths
        ctx_no = {
            "ticker_lessons": [
                self._ticker_lesson(predictor_lessons=["P1", "P2"]),
            ],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "MSFT", "lesson": "sec-A"},
                {"scope": "macro",
                 "source_ticker": "GOOG", "lesson": "mac-A"},
            ],
        }
        # With paths attached to same logical content
        ctx_with = {
            "ticker_lessons": [
                self._ticker_lesson(
                    predictor_lessons=["P1", "P2"],
                    learner_result_path=self._PATH_AAPL_Q1,
                ),
            ],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "MSFT", "lesson": "sec-A",
                 "learner_result_path": self._PATH_MSFT_Q2},
                {"scope": "macro",
                 "source_ticker": "GOOG", "lesson": "mac-A",
                 "learner_result_path":
                     "earnings-analysis/Companies/GOOG/events/Q2_FY2024/learning/result.md"},
            ],
        }
        _, ordered_no = _render_learning_context(ctx_no)
        _, ordered_with = _render_learning_context(ctx_with)
        self.assertEqual(ordered_no, ordered_with,
                         "Tuple element 2 (validator's source of truth) must be byte-identical regardless of path attachment")

    # ── A1: allowlist block appears BEFORE the ### Ticker Lessons heading ──
    def test_renderer_emits_allowlist_block_before_lesson_bodies(self):
        ctx = {
            "_allowed_learner_paths": [self._PATH_AAPL_Q1, self._PATH_MSFT_Q2],
            "ticker_lessons": [self._ticker_lesson(with_path=True)],
            "global_lessons": [],
        }
        text, _ = _render_learning_context(ctx)
        heading = "### Allowed learner reports for this prediction"
        ticker_heading = "### Ticker Lessons"
        self.assertIn(heading, text)
        self.assertIn(ticker_heading, text)
        self.assertLess(
            text.index(heading), text.index(ticker_heading),
            "allowlist block must appear BEFORE ### Ticker Lessons (per Q5)",
        )
        # Each path appears as a `- <path>` line
        for p in [self._PATH_AAPL_Q1, self._PATH_MSFT_Q2]:
            self.assertIn(f"- {p}", text)

    # ── A2: empty allowlist → no block emitted at all ──
    def test_renderer_omits_allowlist_block_when_list_empty(self):
        ctx = {
            "_allowed_learner_paths": [],
            "ticker_lessons": [self._ticker_lesson(with_path=False)],
            "global_lessons": [],
        }
        text, _ = _render_learning_context(ctx)
        self.assertNotIn("Allowed learner reports for this prediction", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
