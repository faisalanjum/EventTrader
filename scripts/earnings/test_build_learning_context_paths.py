#!/usr/bin/env python3
"""Path-attach + allowlist + invariant tests for build_learning_context.

Covers the plan's 16 builder cases per
.claude/plans/skill-md-proposal-approved-mossy-stroustrup.md §6.1:

  Path-attach / allowlist build (11):
    1.  ticker_lesson path attached when result.md exists
    2.  ticker_lesson path omitted when result.md missing
    3.  PIT guard omits current-quarter for ticker_lessons
    4.  global_lesson path uses source_ticker
    5.  global_lesson PIT guard skips on (source_ticker, quarter) match
    6.  attached path is repo-relative string
    7.  current_quarter_label=None bypasses PIT guard (safety-hatch mode)
    8.  _allowed_learner_paths is in EXACT render-order (Q2)
    9.  _allowed_learner_paths excludes current-quarter self-path
    10. _allowed_learner_paths dedupes when multiple lessons share a source
    11. _allowed_learner_paths is empty when no result.md files exist

  Invariant function (4):
    12  (A) raises on cross-surface drift
    12b      passes on consistent state (full context: all 3 clauses positive)
    12c (B)  raises on duplicate paths in allowlist
    12d (C)  raises on self-path leak in allowlist when context is provided

  Orchestrator call-site (1):
    13  build_prediction_bundle propagates current_quarter_label

The 4 invariant tests do NOT need a tmp tree — they call
``orch._assert_learner_paths_invariant(...)`` directly on hand-crafted lc dicts.

Run:
    venv/bin/python -m pytest scripts/earnings/test_build_learning_context_paths.py -v
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

# Module-level alias (per C3): private helpers may not exist yet during TDD red
# phase; using `from ... import _decorate_with_learner_paths` would error at
# file import time. Dotted-attribute access fails per-test (clean red) instead.
import earnings_orchestrator as orch


# ── Helpers ──────────────────────────────────────────────────────────


def _make_learning_md(companies_dir: Path, ticker: str, quarter: str) -> Path:
    """Create a placeholder learning/result.md inside the tmp companies tree."""
    p = companies_dir / ticker.upper() / "events" / quarter / "learning" / "result.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Synthetic learner result for {ticker} {quarter}\n", encoding="utf-8")
    return p


def _write_ticker_json(learnings_dir: Path, ticker: str, lessons: list[dict]) -> Path:
    """Write learnings/ticker/{TICKER}.json with the provided lessons list."""
    ticker_dir = learnings_dir / "ticker"
    ticker_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ticker_lessons.v1",
        "ticker": ticker.upper(),
        "updated_at": None,
        "lessons": lessons,
    }
    p = ticker_dir / f"{ticker.upper()}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def _write_global_json(learnings_dir: Path, entries: list[dict]) -> Path:
    """Write learnings/global.json with the provided entries list."""
    learnings_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "global_lessons.v1",
        "updated_at": None,
        "entries": entries,
    }
    p = learnings_dir / "global.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def _expected_path(ticker: str, quarter: str) -> str:
    return (
        f"earnings-analysis/Companies/{ticker.upper()}"
        f"/events/{quarter}/learning/result.md"
    )


# ── Path-attach / allowlist build tests (cases #1–#11) ───────────────


class BuildLearningContextPathsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.companies_dir = self.tmp / "Companies"
        self.companies_dir.mkdir()
        self.learnings_dir = self.tmp / "learnings"
        self.learnings_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    # #1
    def test_ticker_lesson_path_attached_when_md_exists(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q1_FY2023")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        self.assertEqual(
            result["ticker_lessons"][0]["learner_result_path"],
            _expected_path("AAPL", "Q1_FY2023"),
        )

    # #2
    def test_ticker_lesson_path_omitted_when_md_missing(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        # NB: NOT calling _make_learning_md
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        self.assertNotIn("learner_result_path", result["ticker_lessons"][0])

    # #3
    def test_pit_guard_omits_current_quarter_for_ticker(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q4_FY2023")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertNotIn("learner_result_path", result["ticker_lessons"][0])

    # #4
    def test_global_lesson_path_uses_source_ticker(self):
        _write_global_json(self.learnings_dir, [{
            "scope": "macro",
            "source_ticker": "MSFT",
            "quarter_label": "Q2_FY2024",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "lesson": "macro lesson body",
        }])
        _make_learning_md(self.companies_dir, "MSFT", "Q2_FY2024")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        self.assertEqual(
            result["global_lessons"][0]["learner_result_path"],
            _expected_path("MSFT", "Q2_FY2024"),
        )

    # #5
    def test_global_lesson_pit_guard_skips_when_source_ticker_quarter_match_current(self):
        _write_global_json(self.learnings_dir, [{
            "scope": "macro",
            "source_ticker": "AAPL",
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "lesson": "macro from same ticker+quarter",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q4_FY2023")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertNotIn("learner_result_path", result["global_lessons"][0])

    # #6
    def test_path_is_repo_relative_string(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q1_FY2023")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        p = result["ticker_lessons"][0]["learner_result_path"]
        self.assertFalse(p.startswith("/"))
        self.assertTrue(p.startswith("earnings-analysis/"))

    # #7
    def test_builder_default_when_current_quarter_label_is_none_attaches_all_existing_paths(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q1_FY2023")
        # current_quarter_label deliberately None — safety-hatch mode
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label=None,
        )
        self.assertEqual(
            result["ticker_lessons"][0]["learner_result_path"],
            _expected_path("AAPL", "Q1_FY2023"),
        )

    # #8 — exact render-order (per Q2 + Fix #3)
    def test_allowed_learner_paths_in_exact_render_order(self):
        # 2 ticker_lessons, recency-desc by attributed_at
        _write_ticker_json(self.learnings_dir, "AAPL", [
            {"quarter_label": "Q1_FY2023", "attributed_at": "2024-09-01T00:00:00+00:00"},   # T_older
            {"quarter_label": "Q2_FY2023", "attributed_at": "2024-12-01T00:00:00+00:00"},   # T_recent
        ])
        # 1 sector + 1 macro + 1 cross_ticker
        _write_global_json(self.learnings_dir, [
            {"scope": "sector", "target_sector": "Technology",
             "source_ticker": "MSFT", "quarter_label": "Q1_FY2024",
             "attributed_at": "2024-02-01T00:00:00+00:00", "lesson": "sector lesson"},
            {"scope": "macro",
             "source_ticker": "GOOG", "quarter_label": "Q2_FY2024",
             "attributed_at": "2024-03-01T00:00:00+00:00", "lesson": "macro lesson"},
            {"scope": "cross_ticker", "related_tickers": ["AAPL", "META"],
             "source_ticker": "META", "quarter_label": "Q3_FY2024",
             "attributed_at": "2024-04-01T00:00:00+00:00", "lesson": "cross lesson"},
        ])
        for tk, q in [("AAPL", "Q1_FY2023"), ("AAPL", "Q2_FY2023"),
                      ("MSFT", "Q1_FY2024"), ("GOOG", "Q2_FY2024"),
                      ("META", "Q3_FY2024")]:
            _make_learning_md(self.companies_dir, tk, q)
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        self.assertEqual(result["_allowed_learner_paths"], [
            _expected_path("AAPL", "Q2_FY2023"),  # T_recent first (recency-desc)
            _expected_path("AAPL", "Q1_FY2023"),  # T_older
            _expected_path("MSFT", "Q1_FY2024"),  # sector
            _expected_path("GOOG", "Q2_FY2024"),  # macro
            _expected_path("META", "Q3_FY2024"),  # cross_ticker
        ])

    # #9
    def test_allowed_learner_paths_excludes_current_quarter_self(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q4_FY2023")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertNotIn(
            _expected_path("AAPL", "Q4_FY2023"),
            result["_allowed_learner_paths"],
        )
        self.assertEqual(result["_allowed_learner_paths"], [])

    # #10
    def test_allowed_learner_paths_dedupe_when_multiple_lessons_share_source(self):
        # ticker_lesson AAPL Q1_FY2023 + global lesson with source=AAPL Q1_FY2023
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _write_global_json(self.learnings_dir, [{
            "scope": "macro",
            "source_ticker": "AAPL",
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-02-01T00:00:00+00:00",
            "lesson": "macro lesson body",
        }])
        _make_learning_md(self.companies_dir, "AAPL", "Q1_FY2023")
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        path = _expected_path("AAPL", "Q1_FY2023")
        self.assertEqual(result["_allowed_learner_paths"].count(path), 1)
        self.assertEqual(result["_allowed_learner_paths"], [path])

    # #11
    def test_allowed_learner_paths_empty_when_no_files_exist(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q1_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }])
        _write_global_json(self.learnings_dir, [{
            "scope": "macro",
            "source_ticker": "MSFT",
            "quarter_label": "Q2_FY2024",
            "attributed_at": "2024-02-01T00:00:00+00:00",
            "lesson": "macro lesson",
        }])
        # no _make_learning_md calls
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        self.assertEqual(result["_allowed_learner_paths"], [])


# ── Invariant function tests (cases #12, #12b, #12c, #12d) ───────────


class AssertLearnerPathsInvariantTests(unittest.TestCase):
    """Hand-crafted lc dicts call orch._assert_learner_paths_invariant directly."""

    # #12 (A) — cross-surface drift
    def test_invariant_A_raises_on_cross_surface_drift(self):
        lc = {
            "ticker_lessons": [{"learner_result_path": "earnings-analysis/X/A.md"}],
            "global_lessons": [],
            "_allowed_learner_paths": [],   # decorated path missing from allowlist
        }
        with self.assertRaises(AssertionError) as cm:
            orch._assert_learner_paths_invariant(lc)
        msg = str(cm.exception)
        self.assertIn("invariant (A) violated", msg)
        self.assertIn("earnings-analysis/X/A.md", msg)

    # #12b — full positive (A + B + C all pass with full context)
    def test_invariant_passes_on_consistent_state_with_full_context(self):
        path = _expected_path("AAPL", "Q1_FY2023")
        lc = {
            "ticker_lessons": [{
                "learner_result_path": path,
                "quarter_label": "Q1_FY2023",
            }],
            "global_lessons": [],
            "_allowed_learner_paths": [path],
        }
        # No exception expected. ticker=AAPL with current_quarter_label=Q4_FY2023
        # → self-path would be the Q4 path which is NOT present, so C passes too.
        orch._assert_learner_paths_invariant(
            lc, ticker="AAPL", current_quarter_label="Q4_FY2023",
        )

    # #12c (B) — duplicate paths in allowlist
    def test_invariant_B_raises_on_duplicate_in_allowlist(self):
        lc = {
            "ticker_lessons": [{"learner_result_path": "X.md"}],
            "global_lessons": [],
            "_allowed_learner_paths": ["X.md", "X.md"],
        }
        with self.assertRaises(AssertionError) as cm:
            orch._assert_learner_paths_invariant(lc)
        msg = str(cm.exception)
        self.assertIn("invariant (B) violated", msg)
        # Ensure the dup-list is rendered in the message
        self.assertEqual(msg.count("X.md"), 2)

    # #12d (C) — self-path in allowlist when context provided
    def test_invariant_C_raises_on_self_path_in_allowlist(self):
        self_path = _expected_path("AAPL", "Q4_FY2023")
        lc = {
            "ticker_lessons": [{"learner_result_path": self_path}],
            "global_lessons": [],
            "_allowed_learner_paths": [self_path],   # leaks self-path
        }
        with self.assertRaises(AssertionError) as cm:
            orch._assert_learner_paths_invariant(
                lc, ticker="AAPL", current_quarter_label="Q4_FY2023",
            )
        msg = str(cm.exception)
        self.assertIn("invariant (C) violated", msg)
        self.assertIn("self-path leaked into _allowed_learner_paths", msg)


# ── Orchestrator call-site static-analysis guard (case #13) ──────────


class OrchestratorCallSiteTests(unittest.TestCase):
    """Static-analysis test: ensure build_prediction_bundle keeps propagating
    current_quarter_label. Regression guard against future drops."""

    def test_orchestrator_call_site_passes_non_none_current_quarter_label(self):
        src = (_REPO_ROOT / "scripts" / "earnings" / "earnings_orchestrator.py").read_text(encoding="utf-8")
        # Locate build_prediction_bundle definition
        idx = src.find("def build_prediction_bundle(")
        self.assertGreater(idx, 0, "build_prediction_bundle definition not found")
        # Take a window from the def onwards (capture the body that contains the call site)
        body = src[idx:idx + 4000]
        self.assertIn(
            'current_quarter_label=quarter_info.get("quarter_label")',
            body,
            "build_prediction_bundle must propagate current_quarter_label="
            'quarter_info.get("quarter_label") to build_learning_context',
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
