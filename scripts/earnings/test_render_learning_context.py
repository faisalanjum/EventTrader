#!/usr/bin/env python3
"""Tests for _render_learning_context (U45+U66 format).

Format invariants (post U45+U66):
  - Outer header `## Prior Lessons (from learner)` always present
  - Allowlist block ### Allowed learner reports for this prediction (when non-empty)
  - `## Lessons To Label (verbatim, in order)` — clean L# blocks (when lessons exist)
  - `## Context-Only (not labeled)` — header metadata + R3 fields + data_lessons + why + learner_result paths
  - Tuple element 2 (`ordered`) is byte-identical to pre-U45 behavior

Critical regression tests:
  - test_l_marker_body_round_trip_equals_ordered  ← cross-surface invariant
  - test_R7_ordered_tuple_unchanged_with_or_without_paths  ← validator-source byte identity

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_learning_context -v
    venv/bin/python -m pytest scripts/earnings/test_render_learning_context.py -q
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_learning_context, _normalize_lesson_text


def _parse_l_blocks(text: str) -> list[str]:
    """Parse ## Lessons To Label section. Return list of body strings (one per L#).

    Each L# marker is on its own line. The body is the next non-empty line(s)
    until either the next L# marker, a blank line, or the next ## section.
    """
    if "## Lessons To Label" not in text:
        return []
    after = text.split("## Lessons To Label", 1)[1]
    section = after.split("\n## ", 1)[0]
    bodies: list[str] = []
    current: list[str] = []
    in_block = False
    marker_re = re.compile(r"^L\d+\.(\s+\[.+?\])?\s*$")
    for line in section.split("\n"):
        if marker_re.match(line):
            if in_block and current:
                bodies.append("\n".join(current).rstrip())
            current = []
            in_block = True
        elif in_block:
            if line.strip() == "":
                if current:
                    bodies.append("\n".join(current).rstrip())
                    current = []
                    in_block = False
            else:
                current.append(line)
    if in_block and current:
        bodies.append("\n".join(current).rstrip())
    return bodies


class RenderLearningContextTests(unittest.TestCase):
    """Tuple-return renderer: (text, ordered_lesson_texts)."""

    def test_R1_empty_context_returns_empty_list(self):
        """Empty learning_context → outer header + 'No prior lessons' message + ordered=[]."""
        text, ordered = _render_learning_context({})
        self.assertIsInstance(text, str)
        self.assertIn("## Prior Lessons (from learner)", text)
        self.assertIn("No prior lessons available", text)
        self.assertEqual(ordered, [])
        # ChatGPT note 3: ## Lessons To Label section is ABSENT in empty case
        self.assertNotIn("## Lessons To Label", text)

    def test_R1b_explicit_empty_arrays(self):
        """ticker_lessons=[] and global_lessons=[] explicitly set → ordered=[], no Lessons To Label."""
        text, ordered = _render_learning_context({"ticker_lessons": [], "global_lessons": []})
        self.assertEqual(ordered, [])
        self.assertIn("## Prior Lessons (from learner)", text)
        self.assertIn("No prior lessons available", text)
        self.assertNotIn("## Lessons To Label", text)

    def test_R2_ticker_lessons_split_label_vs_context(self):
        """predictor_lessons go to ## Lessons To Label; data_lessons + why go to ## Context-Only."""
        ctx = {
            "ticker_lessons": [
                {
                    "quarter_label": "Q1_FY2023",
                    "direction_correct": True,
                    "actual_daily_pct": 2.5,
                    "predicted_direction": "long",
                    "primary_driver_category": "eps_surprise",
                    "predictor_lessons": [
                        {"lesson": "Lesson P1 should be labeled"},
                        {"lesson": "Lesson P2 also labeled"},
                    ],
                    "data_lessons": ["Data fetch heuristic D1 NOT labeled"],
                    "why": "This is metadata why — NOT labeled",
                },
            ],
            "global_lessons": [],
        }
        text, ordered = _render_learning_context(ctx)
        self.assertEqual(ordered, [
            "Lesson P1 should be labeled",
            "Lesson P2 also labeled",
        ])
        # Both predictor lessons appear in ## Lessons To Label as L# bodies
        self.assertIn("## Lessons To Label", text)
        self.assertIn("L1.", text)
        self.assertIn("L2.", text)
        self.assertIn("Lesson P1 should be labeled", text)
        # data_lessons + why appear in ## Context-Only, NOT in Lessons To Label
        self.assertIn("## Context-Only", text)
        self.assertIn("- Data: Data fetch heuristic D1 NOT labeled", text)
        self.assertIn("- Why: This is metadata why", text)
        # Old `- Predictor:` prefix is GONE (the U46 fix)
        self.assertNotIn("- Predictor:", text)
        # data_lessons NOT in ordered (still excluded from validator)
        self.assertNotIn("Data fetch heuristic D1 NOT labeled", ordered)

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
        self.assertEqual(ordered, [
            "SEC-A sector lesson",
            "SEC-B sector lesson",
            "MA-A macro lesson",
            "CT-A cross_ticker lesson",
            "CT-B cross_ticker lesson",
        ])
        # Inline scope tags in L# markers (U45 format)
        self.assertIn("L1. [sector: Technology]", text)
        self.assertIn("L2. [sector: Healthcare]", text)
        self.assertIn("L3. [macro]", text)
        self.assertIn("L4. [cross: AAPL,MSFT]", text)
        self.assertIn("L5. [cross: NVDA]", text)
        # Old per-scope sub-headings (### Sector Lessons etc.) are GONE
        self.assertNotIn("### Sector Lessons", text)
        self.assertNotIn("### Macro Lessons", text)
        self.assertNotIn("### Cross-Ticker Lessons", text)

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
                    "predictor_lessons": [{"lesson": "T1-Q1-pl1"}, {"lesson": "T1-Q1-pl2"}],
                    "data_lessons": ["IGNORE-data"],
                },
                {
                    "quarter_label": "Q2_FY2023",
                    "direction_correct": True,
                    "actual_daily_pct": 1.2,
                    "predicted_direction": "short",
                    "primary_driver_category": "eps_surprise",
                    "predictor_lessons": [{"lesson": "T2-Q2-pl1"}],
                },
            ],
            "global_lessons": [
                {"scope": "macro", "source_ticker": "AAPL", "lesson": "G-macro-1"},
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "AAPL", "lesson": "G-sector-1"},
            ],
        }
        text, ordered = _render_learning_context(ctx)
        # Expected order preserved (validator-critical invariant)
        self.assertEqual(ordered, [
            "T1-Q1-pl1",
            "T1-Q1-pl2",
            "T2-Q2-pl1",
            "G-sector-1",
            "G-macro-1",
        ])
        # data_lesson appears in render (Context-Only) but NOT in ordered
        self.assertNotIn("IGNORE-data", ordered)
        self.assertIn("IGNORE-data", text)


class NormalizeLessonTextTests(unittest.TestCase):
    """Helper used for positional comparison and analysis substring floor."""

    def test_normalize_whitespace_collapsed(self):
        self.assertEqual(_normalize_lesson_text("  Hello   World\t\tnewlines\n"),
                         "hello world newlines")

    def test_normalize_case_folded(self):
        self.assertEqual(_normalize_lesson_text("AI Revenue Surge"), "ai revenue surge")

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
            "predictor_lessons": [{"lesson": "pl1"}],
            "data_lessons": ["dl1"],
            "why": "why-text",
        }
        L.update(overrides)
        if with_path:
            L["learner_result_path"] = self._PATH_AAPL_Q1
        return L

    def test_R5_ticker_lesson_emits_learner_result_in_context_only(self):
        """Ticker lesson with learner_result_path → Context-Only sub-block has the line."""
        ctx = {
            "ticker_lessons": [self._ticker_lesson(with_path=True)],
            "global_lessons": [],
        }
        text, _ = _render_learning_context(ctx)
        # Path appears as Context-Only sub-bullet under ### Ticker — Q1_FY2023
        expected_line = f"- learner_result: {self._PATH_AAPL_Q1}"
        self.assertIn(expected_line, text)
        # Located inside Context-Only, NOT in ## Lessons To Label
        ll_idx = text.index("## Lessons To Label")
        co_idx = text.index("## Context-Only")
        line_idx = text.index(expected_line)
        self.assertGreater(line_idx, co_idx,
                           "learner_result must be inside ## Context-Only")
        self.assertGreater(line_idx, ll_idx)

    def test_R5b_ticker_lesson_no_line_when_path_absent(self):
        ctx = {
            "ticker_lessons": [self._ticker_lesson(with_path=False)],
            "global_lessons": [],
        }
        text, _ = _render_learning_context(ctx)
        self.assertNotIn("learner_result:", text)

    def test_R6_global_lesson_emits_learner_result_in_context_only_block(self):
        """Global lesson with path → ### Global lesson source events line carries it."""
        ctx = {
            "ticker_lessons": [],
            "global_lessons": [{
                "scope": "sector",
                "target_sector": "Technology",
                "source_ticker": "MSFT",
                "lesson": "sector lesson body",
                "source_quarter_label": "Q2_FY2024",
                "learner_result_path": self._PATH_MSFT_Q2,
            }],
        }
        text, _ = _render_learning_context(ctx)
        # New format: under ### Global lesson source events
        self.assertIn("### Global lesson source events", text)
        self.assertIn(f"learner_result: {self._PATH_MSFT_Q2}", text)
        # The line includes L# + scope + source ticker
        self.assertIn("L1 sector — source: MSFT Q2_FY2024", text)

    def test_R7_ordered_tuple_unchanged_with_or_without_paths(self):
        """Validator's source of truth must be byte-identical regardless of path attachment."""
        ctx_no = {
            "ticker_lessons": [self._ticker_lesson(predictor_lessons=[{"lesson": "P1"}, {"lesson": "P2"}])],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "MSFT", "lesson": "sec-A"},
                {"scope": "macro", "source_ticker": "GOOG", "lesson": "mac-A"},
            ],
        }
        ctx_with = {
            "ticker_lessons": [self._ticker_lesson(
                predictor_lessons=[{"lesson": "P1"}, {"lesson": "P2"}],
                learner_result_path=self._PATH_AAPL_Q1,
            )],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "MSFT", "lesson": "sec-A",
                 "learner_result_path": self._PATH_MSFT_Q2},
                {"scope": "macro", "source_ticker": "GOOG", "lesson": "mac-A",
                 "learner_result_path":
                     "earnings-analysis/Companies/GOOG/events/Q2_FY2024/learning/result.md"},
            ],
        }
        _, ordered_no = _render_learning_context(ctx_no)
        _, ordered_with = _render_learning_context(ctx_with)
        self.assertEqual(ordered_no, ordered_with,
                         "Tuple element 2 must be byte-identical regardless of path attachment")

    def test_A1_allowlist_block_appears_before_lessons_to_label(self):
        """ChatGPT note 2: allowlist block must appear BEFORE ## Lessons To Label."""
        ctx = {
            "_allowed_learner_paths": [self._PATH_AAPL_Q1, self._PATH_MSFT_Q2],
            "ticker_lessons": [self._ticker_lesson(with_path=True)],
            "global_lessons": [],
        }
        text, _ = _render_learning_context(ctx)
        allowlist_heading = "### Allowed learner reports for this prediction"
        labels_heading = "## Lessons To Label"
        self.assertIn(allowlist_heading, text)
        self.assertIn(labels_heading, text)
        self.assertLess(
            text.index(allowlist_heading), text.index(labels_heading),
            "allowlist block must appear BEFORE ## Lessons To Label",
        )
        for p in [self._PATH_AAPL_Q1, self._PATH_MSFT_Q2]:
            self.assertIn(f"- {p}", text)

    def test_A2_empty_allowlist_omits_block(self):
        ctx = {
            "_allowed_learner_paths": [],
            "ticker_lessons": [self._ticker_lesson(with_path=False)],
            "global_lessons": [],
        }
        text, _ = _render_learning_context(ctx)
        self.assertNotIn("Allowed learner reports for this prediction", text)


# ════════════════════════════════════════════════════════════════════════
# U45+U66 — new tests for Lessons To Label / Context-Only split format
# ════════════════════════════════════════════════════════════════════════

class U45_NewFormatTests(unittest.TestCase):
    """Cross-surface invariants for the Lessons To Label / Context-Only split."""

    def _full_ctx(self) -> dict:
        return {
            "ticker_lessons": [{
                "quarter_label": "Q1_FY2024",
                "direction_correct": True,
                "actual_daily_pct": 2.5,
                "predicted_direction": "long",
                "predicted_confidence_score": 65,
                "primary_driver_category": "eps_beat",
                "primary_driver_summary": "Strong AI tailwind",
                "what_worked": ["Identified AI demand", "Used peer cluster"],
                "what_failed": ["Missed transcript signal"],
                "predictor_lessons": [{"lesson": "TICKER-PL1"}, {"lesson": "TICKER-PL2"}],
                "data_lessons": ["DATA-D1"],
                "why": "WHY-text-paragraph",
            }],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "AAPL", "lesson": "SECTOR-LESSON"},
                {"scope": "macro", "source_ticker": "AAPL",
                 "lesson": "MACRO-LESSON"},
                {"scope": "cross_ticker", "related_tickers": ["AAPL", "MSFT"],
                 "source_ticker": "AAPL", "lesson": "CROSS-LESSON"},
            ],
        }

    # ── CRITICAL: cross-surface round-trip invariant (ChatGPT instruction #6) ──
    def test_l_marker_body_round_trip_equals_ordered(self):
        """Parse rendered L# bodies; assert each equals ordered[i] byte-identically.

        This is the load-bearing regression test: if it fires, the predictor's
        verbatim copy from rendered text will mismatch the validator's expected
        list, causing legitimate predictions to fail validation.
        """
        ctx = self._full_ctx()
        text, ordered = _render_learning_context(ctx)
        parsed = _parse_l_blocks(text)
        self.assertEqual(len(parsed), len(ordered),
                         f"L# count {len(parsed)} != ordered count {len(ordered)}")
        for i, (got, want) in enumerate(zip(parsed, ordered)):
            self.assertEqual(got, want,
                             f"L{i+1} body mismatch:\n  parsed:   {got!r}\n  expected: {want!r}")

    def test_lessons_to_label_section_present_with_lessons(self):
        text, _ = _render_learning_context(self._full_ctx())
        self.assertIn("## Lessons To Label (verbatim, in order)", text)

    def test_lessons_to_label_section_absent_when_no_lessons(self):
        """ChatGPT note 3: outer ## Prior Lessons stays; ## Lessons To Label is absent."""
        text, _ = _render_learning_context({})
        self.assertIn("## Prior Lessons (from learner)", text)
        self.assertIn("No prior lessons available", text)
        self.assertNotIn("## Lessons To Label", text)

    def test_context_only_carries_R3_fields(self):
        """ChatGPT decision 1: predicted_confidence, primary_driver, what_worked,
        what_failed all surface under ### Ticker — <quarter>."""
        text, _ = _render_learning_context(self._full_ctx())
        self.assertIn("## Context-Only", text)
        self.assertIn("### Ticker — Q1_FY2024", text)
        self.assertIn("- predicted_confidence: 65", text)
        self.assertIn("- primary_driver: Strong AI tailwind", text)
        self.assertIn("- what_worked: Identified AI demand", text)
        self.assertIn("- what_worked: Used peer cluster", text)
        self.assertIn("- what_failed: Missed transcript signal", text)

    def test_context_only_carries_data_lessons_and_why(self):
        """data_lessons + why move from inline (under predictor_lessons) to Context-Only."""
        text, _ = _render_learning_context(self._full_ctx())
        co_idx = text.index("## Context-Only")
        d_idx = text.index("- Data: DATA-D1")
        w_idx = text.index("- Why: WHY-text-paragraph")
        self.assertGreater(d_idx, co_idx, "Data: must be inside Context-Only")
        self.assertGreater(w_idx, co_idx, "Why: must be inside Context-Only")

    def test_empty_related_tickers_omits_cross_tag(self):
        """ChatGPT decision 2: cross_ticker with related_tickers=[] → bare L#. (no [cross:...] tag)."""
        ctx = {
            "ticker_lessons": [],
            "global_lessons": [{
                "scope": "cross_ticker", "related_tickers": [],
                "source_ticker": "AAPL", "lesson": "CROSS-NO-RELATED",
            }],
        }
        text, ordered = _render_learning_context(ctx)
        self.assertEqual(ordered, ["CROSS-NO-RELATED"])
        # The marker line for the lesson must NOT contain "[cross:" because the
        # related list is empty (would produce just `[cross:]` which is noise).
        self.assertNotIn("[cross:", text)
        # But marker line and body still emitted
        self.assertIn("L1.", text)
        self.assertIn("CROSS-NO-RELATED", text)

    def test_global_lesson_scope_tag_present_in_marker_line(self):
        """Each non-ticker scope renders its tag in the marker line, not as a sub-section heading."""
        text, _ = _render_learning_context(self._full_ctx())
        # 2 ticker lessons (L1, L2), then sector (L3), macro (L4), cross (L5)
        self.assertIn("L3. [sector: Technology]", text)
        self.assertIn("L4. [macro]", text)
        self.assertIn("L5. [cross: AAPL,MSFT]", text)

    def test_ticker_lesson_marker_has_no_scope_tag(self):
        """L1, L2 (ticker lessons) have bare markers — no scope tag."""
        text, _ = _render_learning_context(self._full_ctx())
        # Match the marker line exactly: `L1.` followed by newline
        self.assertRegex(text, r"\nL1\.\nTICKER-PL1\n")
        self.assertRegex(text, r"\nL2\.\nTICKER-PL2\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
