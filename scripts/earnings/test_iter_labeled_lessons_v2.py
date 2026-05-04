#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.4 — iter_labeled_lessons skip-retired + v3 dict.

Walk-order contract is unchanged from v1 (ticker_lessons → sector → macro
→ cross_ticker, with L# numbering preserved). v2 additions:

  1. v3 ``predictor_lessons[j]`` dict bodies use ``pl["lesson"]`` for body.
  2. v1 string-form ``predictor_lessons[j]`` still walks (transitional —
     removed in commit 3 alongside renderer migration).
  3. Skip ticker_lessons entries whose transient
     ``_render_status == "retired"`` (attached by build_learning_context's
     _apply_render_view; retired lessons must never reach the renderer).
  4. Skip global_lessons entries whose ``_render_status == "retired"``.
  5. n only increments on yielded lessons (not on skipped ones).

These tests anchor the contract that BOTH renderer/lessons.py AND
build_evidence_source_catalog rely on for #S10.lesson.L# numbering.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from _text_utils import iter_labeled_lessons


def _v3_dict(body, _render_status="active"):
    """v3-shape predictor_lesson dict body."""
    d = {
        "lesson_id":     "lsn_x",
        "lesson":        body,
        "mechanism":     "m",
        "applies_when":  "a",
        "invalid_if":    "i",
        "evidence_refs": ["E1"],
        "scope":         "ticker",
        "routing_key":   "X",
        "audit_history": [],
        "parent_id":     None,
    }
    if _render_status is not None:
        d["_render_status"] = _render_status
    return d


class IterLabeledLessonsTests(unittest.TestCase):

    # ── v3 dict body resolution ─────────────────────────────────────────

    def test_v3_dict_body_yielded(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [_v3_dict("body1")]}],
            "global_lessons": [],
        }
        out = list(iter_labeled_lessons(ctx))
        self.assertEqual(out, [(1, "ticker", ctx["ticker_lessons"][0], "body1")])

    def test_multiple_v3_lessons_in_quarter(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [
                _v3_dict("a"), _v3_dict("b"), _v3_dict("c"),
            ]}],
            "global_lessons": [],
        }
        out = [body for _, _, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, ["a", "b", "c"])

    # ── v1 string fallback REMOVED in commit 4 (round-6 fresh-start) ──

    def test_v1_string_predictor_lessons_skipped(self):
        # Round-6 fresh-start cutover: bare strings in predictor_lessons
        # are no longer walked. Validator + append_ticker_lesson enforce
        # dict shape on writes; iter_labeled_lessons defends against
        # leftover non-dict entries by skipping them silently.
        ctx = {
            "ticker_lessons": [{"predictor_lessons": ["legacy string"]}],
            "global_lessons": [],
        }
        out = list(iter_labeled_lessons(ctx))
        self.assertEqual(out, [], "v1 string fallback must be removed")

    def test_mixed_v3_dict_and_v1_string_skips_string(self):
        # v3 dict entries continue to walk; bare strings are silently dropped.
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [
                _v3_dict("v3 dict"),
                "legacy string",
                _v3_dict("another v3"),
            ]}],
            "global_lessons": [],
        }
        out = [body for _, _, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, ["v3 dict", "another v3"])

    # ── Skip retired (LearnerLoopRevamp v2 addition) ────────────────────

    def test_retired_ticker_lesson_skipped(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [
                _v3_dict("active1", _render_status="active"),
                _v3_dict("retired",  _render_status="retired"),
                _v3_dict("active2", _render_status="active"),
            ]}],
            "global_lessons": [],
        }
        out = [body for _, _, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, ["active1", "active2"])

    def test_n_does_not_increment_on_retired(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [
                _v3_dict("active1"),
                _v3_dict("retired", _render_status="retired"),
                _v3_dict("active2"),
            ]}],
            "global_lessons": [],
        }
        ns = [n for n, *_ in iter_labeled_lessons(ctx)]
        # n should be 1, 2 — not 1, 3 (retired entry doesn't bump n)
        self.assertEqual(ns, [1, 2])

    def test_retired_global_lesson_skipped(self):
        ctx = {
            "ticker_lessons": [],
            "global_lessons": [
                {"scope": "macro", "lesson": "active macro"},
                {"scope": "macro", "lesson": "retired macro",
                 "_render_status": "retired"},
            ],
        }
        out = [body for _, _, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, ["active macro"])

    # ── Walk order contract preserved ───────────────────────────────────

    def test_walk_order_ticker_then_sector_macro_cross(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [_v3_dict("T1")]}],
            "global_lessons": [
                {"scope": "macro",        "lesson": "M1"},
                {"scope": "cross_ticker", "lesson": "C1"},
                {"scope": "sector",       "lesson": "S1"},
            ],
        }
        out = [(scope, body) for _, scope, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, [
            ("ticker",       "T1"),
            ("sector",       "S1"),
            ("macro",        "M1"),
            ("cross_ticker", "C1"),
        ])

    def test_n_numbering_continuous_across_scopes(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [_v3_dict("T1"), _v3_dict("T2")]}],
            "global_lessons": [
                {"scope": "sector", "lesson": "S1"},
                {"scope": "macro",  "lesson": "M1"},
            ],
        }
        ns = [n for n, *_ in iter_labeled_lessons(ctx)]
        self.assertEqual(ns, [1, 2, 3, 4])

    # ── Empty / non-string body skipped ────────────────────────────────

    def test_empty_body_skipped(self):
        ctx = {
            "ticker_lessons": [{"predictor_lessons": [
                _v3_dict(""),         # empty
                _v3_dict("   "),      # whitespace
                _v3_dict("real"),
            ]}],
            "global_lessons": [],
        }
        out = [body for _, _, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, ["real"])

    def test_global_entry_with_empty_lesson_skipped(self):
        ctx = {
            "ticker_lessons": [],
            "global_lessons": [
                {"scope": "macro", "lesson": ""},
                {"scope": "macro", "lesson": "real macro"},
            ],
        }
        out = [body for _, _, _, body in iter_labeled_lessons(ctx)]
        self.assertEqual(out, ["real macro"])

    # ── source_entry handle ─────────────────────────────────────────────

    def test_source_entry_for_ticker_is_quarter_row(self):
        # The 3rd tuple element is the SOURCE ENTRY — the quarter row for
        # ticker scope. Aggregator and renderer rely on this.
        quarter_row = {"quarter_label": "Q1", "predictor_lessons": [_v3_dict("body")]}
        ctx = {"ticker_lessons": [quarter_row], "global_lessons": []}
        out = list(iter_labeled_lessons(ctx))
        self.assertEqual(len(out), 1)
        _, scope, source_entry, _ = out[0]
        self.assertEqual(scope, "ticker")
        self.assertIs(source_entry, quarter_row)

    def test_source_entry_for_global_is_entry_dict(self):
        entry = {"scope": "macro", "lesson": "macro body"}
        ctx = {"ticker_lessons": [], "global_lessons": [entry]}
        out = list(iter_labeled_lessons(ctx))
        self.assertEqual(len(out), 1)
        _, scope, source_entry, _ = out[0]
        self.assertEqual(scope, "macro")
        self.assertIs(source_entry, entry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
