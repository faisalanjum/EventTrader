#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.1 (D10) — lesson_id stability + D22 collision tests.

compute_lesson_id properties (D10):
  * Same body + scope + routing → same id (idempotent under re-runs)
  * Refinement (different body) → different id (chain via parent_id)
  * Cross-scope same-text → different id (scope is in the hash)
  * cross_ticker routing_key normalized (tuple, sorted, uppercase)
  * Whitespace + case normalization in lesson body (matches T1 norm)

assert_no_id_collision (D22):
  * No-op when library file does not exist
  * No-op when same id maps to identical content (idempotent re-emit)
  * Raises DuplicateLessonIdError on different content under same id
  * Three insertion sites (append_ticker_lesson, append_global_lessons,
    _register_replacement) — covered by checking the helper directly
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import (
    DuplicateLessonIdError,
    assert_no_id_collision,
    compute_lesson_id,
    _content_matches,
    _routing_key_from_source,
)


# ── compute_lesson_id stability ─────────────────────────────────────────


class ComputeLessonIdTests(unittest.TestCase):
    def test_idempotent_same_inputs(self):
        a = compute_lesson_id("body text", "ticker", "AVGO")
        b = compute_lesson_id("body text", "ticker", "AVGO")
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("lsn_"))
        self.assertEqual(len(a), 14)  # "lsn_" + 10 hex chars

    def test_different_body_different_id(self):
        a = compute_lesson_id("body one", "ticker", "AVGO")
        b = compute_lesson_id("body two", "ticker", "AVGO")
        self.assertNotEqual(a, b)

    def test_different_scope_different_id(self):
        a = compute_lesson_id("same body", "ticker", "AVGO")
        b = compute_lesson_id("same body", "sector", "Technology")
        self.assertNotEqual(a, b)

    def test_different_routing_different_id(self):
        a = compute_lesson_id("same body", "ticker", "AVGO")
        b = compute_lesson_id("same body", "ticker", "QCOM")
        self.assertNotEqual(a, b)

    def test_macro_scope_none_routing(self):
        # macro lessons have routing_key=None — no crash, deterministic id
        a = compute_lesson_id("macro lesson", "macro", None)
        b = compute_lesson_id("macro lesson", "macro", None)
        self.assertEqual(a, b)

    def test_cross_ticker_routing_normalized(self):
        # Tuple sorting + uppercase normalization
        a = compute_lesson_id("x", "cross_ticker", ("AVGO", "QCOM"))
        b = compute_lesson_id("x", "cross_ticker", ("QCOM", "AVGO"))  # reversed
        c = compute_lesson_id("x", "cross_ticker", ["avgo", "qcom"])  # list+lowercase
        self.assertEqual(a, b)
        self.assertEqual(a, c)

    def test_whitespace_normalization(self):
        a = compute_lesson_id("body text", "ticker", "X")
        b = compute_lesson_id("body  text", "ticker", "X")
        c = compute_lesson_id("  body text  ", "ticker", "X")
        d = compute_lesson_id("BODY TEXT", "ticker", "X")
        self.assertEqual(a, b)
        self.assertEqual(a, c)
        self.assertEqual(a, d)

    def test_id_format(self):
        i = compute_lesson_id("anything", "ticker", "X")
        self.assertTrue(i.startswith("lsn_"))
        # 10 hex chars after the prefix
        self.assertEqual(len(i), 14)
        hex_part = i[4:]
        # Each char must be a valid hex digit
        for c in hex_part:
            self.assertIn(c.lower(), "0123456789abcdef")


# ── _routing_key_from_source ────────────────────────────────────────────


class RoutingKeyTests(unittest.TestCase):
    def test_ticker_requires_hint(self):
        with self.assertRaises(ValueError):
            _routing_key_from_source("ticker", {})

    def test_ticker_uses_hint(self):
        rk = _routing_key_from_source("ticker", {}, ticker_hint="avgo")
        self.assertEqual(rk, "AVGO")

    def test_sector_uses_target_sector(self):
        rk = _routing_key_from_source("sector", {"target_sector": "Technology"})
        self.assertEqual(rk, "Technology")

    def test_macro_returns_none(self):
        self.assertIsNone(_routing_key_from_source("macro", {}))

    def test_cross_ticker_sorted_uppercase_tuple(self):
        rk = _routing_key_from_source("cross_ticker", {"related_tickers": ["qcom", "avgo"]})
        self.assertEqual(rk, ("AVGO", "QCOM"))

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            _routing_key_from_source("unknown", {})


# ── _content_matches ────────────────────────────────────────────────────


class ContentMatchesTests(unittest.TestCase):
    def _row(self, **kw):
        base = {
            "lesson":       "the lesson body",
            "mechanism":    "the mechanism",
            "applies_when": "applies when",
            "invalid_if":   "invalid if",
            "scope":        "ticker",
            "routing_key":  "AVGO",
        }
        base.update(kw)
        return base

    def test_identical_matches(self):
        self.assertTrue(_content_matches(self._row(), self._row()))

    def test_lesson_text_normalization(self):
        # whitespace + case should not break match
        a = self._row(lesson="The Lesson Body")
        b = self._row(lesson="the  lesson   body  ")
        self.assertTrue(_content_matches(a, b))

    def test_mechanism_diff_breaks_match(self):
        self.assertFalse(_content_matches(
            self._row(mechanism="A"), self._row(mechanism="B"),
        ))

    def test_scope_diff_breaks_match(self):
        self.assertFalse(_content_matches(
            self._row(scope="ticker"), self._row(scope="sector"),
        ))

    def test_routing_key_normalization(self):
        # cross_ticker tuples should compare regardless of order/casing
        a = self._row(scope="cross_ticker", routing_key=["AVGO", "QCOM"])
        b = self._row(scope="cross_ticker", routing_key=["qcom", "avgo"])
        self.assertTrue(_content_matches(a, b))


# ── assert_no_id_collision (D22) ────────────────────────────────────────


class AssertNoIdCollisionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.ticker_path = self.tmp / "AVGO.json"
        self.global_path = self.tmp / "global.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _write_ticker(self, lessons_in_quarter: list[dict]):
        self.ticker_path.write_text(json.dumps({
            "schema_version": "ticker_lessons.v2",
            "ticker": "AVGO",
            "updated_at": None,
            "lessons": [{"quarter_label": "Q1", "predictor_lessons": lessons_in_quarter}],
        }), encoding="utf-8")

    def _write_global(self, entries: list[dict]):
        self.global_path.write_text(json.dumps({
            "schema_version": "global_lessons.v2",
            "updated_at": None,
            "entries": entries,
        }), encoding="utf-8")

    def test_missing_file_no_op(self):
        # No file = no candidates, no raise.
        assert_no_id_collision(
            self.ticker_path, "ticker", "lsn_aaaaaaaaaa",
            {"lesson": "body", "scope": "ticker", "routing_key": "AVGO"},
        )

    def test_idempotent_identical_content(self):
        new_content = {
            "lesson_id": "lsn_dead0fbeef",
            "lesson":    "body text",
            "mechanism": "mech",
            "applies_when": "appl",
            "invalid_if": "inv",
            "scope":      "ticker",
            "routing_key": "AVGO",
        }
        self._write_ticker([new_content])
        # Same content under same id → no-op
        assert_no_id_collision(self.ticker_path, "ticker",
                                "lsn_dead0fbeef", new_content)

    def test_collision_with_different_content_raises(self):
        existing = {
            "lesson_id": "lsn_dead0fbeef",
            "lesson":    "body text ORIGINAL",
            "mechanism": "mech",
            "applies_when": "appl",
            "invalid_if": "inv",
            "scope":      "ticker",
            "routing_key": "AVGO",
        }
        self._write_ticker([existing])
        # Different lesson body under same id → raise
        new_content = {**existing, "lesson": "body text DIFFERENT"}
        with self.assertRaises(DuplicateLessonIdError):
            assert_no_id_collision(self.ticker_path, "ticker",
                                    "lsn_dead0fbeef", new_content)

    def test_no_collision_returns_silently(self):
        existing = {
            "lesson_id": "lsn_aaaaaaaaaa",
            "lesson":    "body A", "mechanism": "m", "applies_when": "a",
            "invalid_if": "i", "scope": "ticker", "routing_key": "AVGO",
        }
        self._write_ticker([existing])
        # Different id — no candidates, no raise.
        assert_no_id_collision(
            self.ticker_path, "ticker", "lsn_bbbbbbbbbb",
            {**existing, "lesson_id": "lsn_bbbbbbbbbb"},
        )

    def test_global_collision_detection(self):
        existing = {
            "lesson_id": "lsn_global0001",
            "lesson":    "macro body original",
            "mechanism": "m", "applies_when": "a", "invalid_if": "i",
            "scope": "macro", "routing_key": None,
        }
        self._write_global([existing])
        new_content = {**existing, "lesson": "macro body DIFFERENT"}
        with self.assertRaises(DuplicateLessonIdError):
            assert_no_id_collision(self.global_path, "macro",
                                    "lsn_global0001", new_content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
