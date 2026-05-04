#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.5.1 (D13) — same-quarter self-leak guard.

build_learning_context must exclude THIS quarter's own emissions from
THIS quarter's bundle. Specifically:

  * ticker_lessons row whose ``quarter_label == current_quarter_label``
    is fully excluded (not just stripped of ``learner_result_path``).
  * global_lessons entry whose ``(source_ticker, quarter_label) ==
    (ticker, current_quarter_label)`` is fully excluded.

Both rules fire regardless of pit_mode (live OR historical). The guard
is identity-based (ticker + quarter), not timestamp-based, so a re-run
in live mode (pit_cutoff=None) still excludes its own prior emission.

A new observability counter ``same_quarter_self_leak`` is logged at the
end of build_learning_context's INFO log alongside the pre-existing
exclusion counters.
"""
from __future__ import annotations

import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

import earnings_orchestrator as orch


def _write_ticker_json(learnings_dir: Path, ticker: str, lessons: list[dict]) -> Path:
    ticker_dir = learnings_dir / "ticker"
    ticker_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ticker_lessons.v2",
        "ticker": ticker.upper(),
        "updated_at": None,
        "lessons": lessons,
    }
    p = ticker_dir / f"{ticker.upper()}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def _write_global_json(learnings_dir: Path, entries: list[dict]) -> Path:
    learnings_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "global_lessons.v2",
        "updated_at": None,
        "entries": entries,
    }
    p = learnings_dir / "global.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


class SelfLeakGuardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.companies_dir = self.tmp / "Companies"
        self.companies_dir.mkdir()
        self.learnings_dir = self.tmp / "learnings"
        self.learnings_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    # ── Ticker scope ────────────────────────────────────────────────────

    def test_ticker_current_quarter_excluded_in_live_mode(self):
        # Live mode (pit_cutoff=None) — guard still fires (identity-based).
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "predictor_lessons": [],
        }])
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertEqual(result["ticker_lessons"], [])

    def test_ticker_current_quarter_excluded_in_historical(self):
        # Historical mode + matching quarter — same exclusion.
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "source_pit_cutoff": "2023-10-01T00:00:00+00:00",
            "predictor_lessons": [],
        }])
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            pit_cutoff="2024-06-01T00:00:00+00:00",
            current_quarter_label="Q4_FY2023",
        )
        self.assertEqual(result["ticker_lessons"], [])

    def test_ticker_other_quarter_kept(self):
        _write_ticker_json(self.learnings_dir, "AAPL", [
            {"quarter_label": "Q3_FY2023", "attributed_at": "2024-01-01T00:00:00+00:00",
             "predictor_lessons": []},
            {"quarter_label": "Q4_FY2023", "attributed_at": "2024-04-01T00:00:00+00:00",
             "predictor_lessons": []},
        ])
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        # Only Q3 should remain (Q4 = current).
        quarters = [l.get("quarter_label") for l in result["ticker_lessons"]]
        self.assertEqual(quarters, ["Q3_FY2023"])

    # ── Global scope ────────────────────────────────────────────────────

    def test_global_same_source_ticker_quarter_excluded(self):
        _write_global_json(self.learnings_dir, [{
            "scope": "macro", "source_ticker": "AAPL",
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "lesson": "macro lesson body",
        }])
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertEqual(result["global_lessons"], [])

    def test_global_different_source_ticker_kept(self):
        _write_global_json(self.learnings_dir, [{
            "scope": "macro", "source_ticker": "MSFT",
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "lesson": "macro from another ticker",
        }])
        # Same quarter_label as AAPL's current quarter, but different source.
        # The guard is on (source_ticker == ticker AND quarter == current),
        # so MSFT's Q4 entry stays.
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertEqual(len(result["global_lessons"]), 1)
        self.assertEqual(result["global_lessons"][0]["source_ticker"], "MSFT")

    def test_global_same_ticker_different_quarter_kept(self):
        _write_global_json(self.learnings_dir, [{
            "scope": "macro", "source_ticker": "AAPL",
            "quarter_label": "Q3_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "lesson": "AAPL prior quarter macro",
        }])
        result = orch.build_learning_context(
            "AAPL", sector="Technology", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2023",
        )
        self.assertEqual(len(result["global_lessons"]), 1)

    # ── Observability counter ───────────────────────────────────────────

    def test_same_quarter_self_leak_counter_logged(self):
        # Both ticker AND global emit current-quarter entries → counter += 2.
        _write_ticker_json(self.learnings_dir, "AAPL", [{
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "predictor_lessons": [],
        }])
        _write_global_json(self.learnings_dir, [{
            "scope": "macro", "source_ticker": "AAPL",
            "quarter_label": "Q4_FY2023",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "lesson": "AAPL Q4 macro",
        }])
        with self.assertLogs(orch.log, level="INFO") as cap:
            orch.build_learning_context(
                "AAPL", sector="Technology", base_dir=self.learnings_dir,
                companies_dir=self.companies_dir,
                current_quarter_label="Q4_FY2023",
            )
        log_text = "\n".join(cap.output)
        self.assertIn("same_quarter_self_leak=", log_text)
        # Counter should be 2 (1 ticker + 1 global).
        self.assertIn("same_quarter_self_leak=2", log_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
