#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.4 — v3 lesson rendering with decoration.

New in commit 3:
  * ``[status: <active|watch>]`` tag on the marker line
  * ``[reviews: <Nh> helped, ...]`` summary tag (review counts in stable order)
  * CAUTION line preceding the body when status==watch
  * Mechanism / Applies when / Invalid if blocks below the body
  * D20 invariant: ``ordered_lesson_texts`` contains the LESSON BODY ONLY,
    not the decoration (preserves T1 positional equality)
  * Retired lessons NEVER reach the renderer (filtered by
    build_learning_context); the renderer therefore sees only active/watch
  * v1 string-form lessons + v1-dict global entries continue to render
    bare (no Lesson: prefix, no mechanism block) — backward-compat for
    pre-cutover bundle goldens
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from renderer.lessons import _render_learning_context


# ── v3 lesson dict fixture builders ─────────────────────────────────────


def _v3_ticker_lesson(body: str, **overrides) -> dict:
    """v3-shape predictor_lessons[i] entry — with the discriminator
    fields the renderer uses to switch into v3 decoration mode
    (lesson_id, mechanism, audit_history)."""
    base = {
        "lesson_id":     "lsn_xxxxxxxxxx",
        "lesson":        body,
        "mechanism":     "the causal mechanism explaining why",
        "applies_when":  "bundle preconditions for the lesson",
        "invalid_if":    "conditions that nullify this lesson",
        "evidence_refs": ["E1"],
        "scope":         "ticker",
        "routing_key":   "AVGO",
        "audit_history": [],
        "parent_id":     None,
    }
    base.update(overrides)
    return base


def _v3_global_entry(scope: str, body: str, **overrides) -> dict:
    """v3-shape global_lessons entry (top-level row in global.json)."""
    base = {
        "lesson_id":     "lsn_global0001",
        "lesson":        body,
        "mechanism":     "global-scope mechanism",
        "applies_when":  "global-scope preconditions",
        "invalid_if":    "global-scope nullifiers",
        "evidence_refs": ["E1"],
        "scope":         scope,
        "routing_key":   None if scope == "macro" else "Technology",
        "source_ticker":      "MSFT",
        "source_sector":      "Technology",
        "quarter_label":      "Q1_FY2024",
        "attributed_at":      "2024-01-01T00:00:00+00:00",
        "source_filed_8k":    "2024-01-01T00:00:00+00:00",
        "source_pit_cutoff":  "2024-01-01T00:00:00+00:00",
        "audit_history":      [],
        "parent_id":          None,
    }
    if scope == "sector":
        base["target_sector"] = "Technology"
    elif scope == "cross_ticker":
        base["related_tickers"] = ["AAPL", "MSFT"]
    base.update(overrides)
    return base


def _quarter_row(quarter_label: str, predictor_lessons: list[dict]) -> dict:
    return {
        "quarter_label":       quarter_label,
        "attributed_at":       "2024-01-01T00:00:00+00:00",
        "source_filed_8k":     "2024-01-01T00:00:00+00:00",
        "source_pit_cutoff":   "2024-01-01T00:00:00+00:00",
        "direction_correct":   True,
        "actual_daily_pct":    1.5,
        "predicted_direction": "long",
        "primary_driver_summary":  "x",
        "primary_driver_category": "x",
        "predictor_lessons":   predictor_lessons,
    }


# ── Tests ──────────────────────────────────────────────────────────────


class V3LessonRenderingTests(unittest.TestCase):
    """Pin the v3 marker + body decoration."""

    def _render(self, lc):
        return _render_learning_context(lc)

    def test_v3_ticker_active_status_marker(self):
        ll = _v3_ticker_lesson("body text",
                                _render_status="active",
                                _render_audit_counts={})
        text, ordered = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", [ll])],
            "global_lessons": [],
        })
        self.assertIn("L1. [status: active]", text)
        self.assertIn("Lesson: body text", text)
        self.assertIn("Mechanism: the causal mechanism explaining why", text)
        self.assertIn("Applies when: bundle preconditions for the lesson", text)
        self.assertIn("Invalid if: conditions that nullify this lesson", text)
        # D20 — body only
        self.assertEqual(ordered, ["body text"])

    def test_v3_watch_status_renders_caution(self):
        ll = _v3_ticker_lesson("body text",
                                _render_status="watch",
                                _render_audit_counts={"misled": 2, "helped": 1})
        text, ordered = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", [ll])],
            "global_lessons": [],
        })
        self.assertIn("[status: watch]", text)
        self.assertIn("[CAUTION", text)
        # CAUTION line must precede the Lesson: body line so the predictor
        # sees it ahead of the body it would copy verbatim.
        caution_idx = text.index("[CAUTION")
        lesson_idx = text.index("Lesson: body text")
        self.assertLess(caution_idx, lesson_idx)
        # D20 — body only (no CAUTION, no decoration in ordered)
        self.assertEqual(ordered, ["body text"])
        # ordered must NOT contain the CAUTION line or any prefix
        for item in ordered:
            self.assertNotIn("CAUTION", item)
            self.assertFalse(item.startswith("Lesson:"))

    def test_v3_reviews_summary_tag(self):
        ll = _v3_ticker_lesson("body",
                                _render_status="active",
                                _render_audit_counts={"helped": 3, "outweighed": 1})
        text, _ = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", [ll])],
            "global_lessons": [],
        })
        # Review counts ordered: helped, outweighed, misled, missed, ...
        self.assertIn("[reviews: 3 helped, 1 outweighed]", text)

    def test_v3_reviews_summary_skips_zero_counts(self):
        ll = _v3_ticker_lesson("body",
                                _render_status="active",
                                _render_audit_counts={"helped": 2, "misled": 0,
                                                       "outweighed": 1})
        text, _ = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", [ll])],
            "global_lessons": [],
        })
        self.assertIn("[reviews: 2 helped, 1 outweighed]", text)
        self.assertNotIn("0 misled", text)

    def test_v3_no_reviews_tag_when_empty_counts(self):
        ll = _v3_ticker_lesson("body",
                                _render_status="active",
                                _render_audit_counts={})
        text, _ = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", [ll])],
            "global_lessons": [],
        })
        self.assertIn("[status: active]", text)
        self.assertNotIn("[reviews:", text)

    # ── Per-scope decoration ──

    def test_v3_sector_marker_combines_scope_and_status(self):
        e = _v3_global_entry("sector", "sector body",
                              _render_status="active",
                              _render_audit_counts={"helped": 1})
        text, ordered = self._render({
            "ticker_lessons": [],
            "global_lessons": [e],
        })
        self.assertIn("L1. [sector: Technology] [status: active] [reviews: 1 helped]",
                      text)
        self.assertIn("Lesson: sector body", text)
        self.assertEqual(ordered, ["sector body"])

    def test_v3_macro_marker(self):
        e = _v3_global_entry("macro", "macro body",
                              _render_status="active", _render_audit_counts={})
        text, _ = self._render({
            "ticker_lessons": [],
            "global_lessons": [e],
        })
        self.assertIn("L1. [macro] [status: active]", text)

    def test_v3_cross_ticker_marker(self):
        e = _v3_global_entry("cross_ticker", "cross body",
                              related_tickers=["AAPL", "MSFT"],
                              _render_status="active", _render_audit_counts={})
        text, _ = self._render({
            "ticker_lessons": [],
            "global_lessons": [e],
        })
        self.assertIn("L1. [cross: AAPL,MSFT] [status: active]", text)

    # ── D20 — ordered_lesson_texts is body-only across all decorations ──

    def test_d20_ordered_is_body_only_across_all_v3_states(self):
        # Build a bundle with every status/scope combination; the ordered
        # list must contain ONLY the lesson body strings.
        lessons = [
            _v3_ticker_lesson("ticker active body",
                                _render_status="active", _render_audit_counts={}),
            _v3_ticker_lesson("ticker watch body",
                                _render_status="watch",
                                _render_audit_counts={"misled": 2}),
        ]
        text, ordered = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", lessons)],
            "global_lessons": [
                _v3_global_entry("sector", "sector body",
                                  _render_status="active", _render_audit_counts={}),
                _v3_global_entry("macro", "macro body",
                                  _render_status="active", _render_audit_counts={}),
            ],
        })
        self.assertEqual(ordered, [
            "ticker active body",
            "ticker watch body",
            "sector body",
            "macro body",
        ])
        # Sanity — none of the ordered entries carry the prefix or tags
        for body in ordered:
            self.assertFalse(body.startswith("Lesson:"))
            self.assertNotIn("[status:", body)
            self.assertNotIn("[reviews:", body)
            self.assertNotIn("CAUTION", body)
            self.assertNotIn("Mechanism:", body)

    # ── Mixed v1/v3 transitional rendering ──

    def test_v1_string_lesson_renders_without_decoration(self):
        # v1 string-form predictor_lessons (transitional, removed in
        # commit 4 cutover) must continue to render bare so existing
        # renderer goldens stay byte-stable.
        text, ordered = self._render({
            "ticker_lessons": [{
                "quarter_label": "Q1_FY2024",
                "predictor_lessons": ["legacy v1 string body"],
            }],
            "global_lessons": [],
        })
        self.assertIn("L1.\nlegacy v1 string body", text)
        self.assertNotIn("Lesson: legacy v1 string body", text)
        self.assertNotIn("[status:", text)
        self.assertEqual(ordered, ["legacy v1 string body"])

    def test_v1_dict_global_entry_renders_bare(self):
        # Pre-commit-2 dict-form global entries (lesson + scope but no
        # lesson_id/mechanism/audit_history) must render bare to keep
        # golden bundles byte-stable until commit 4 cutover.
        v1_dict_entry = {
            "scope":         "macro",
            "lesson":        "macro body",
            "source_ticker": "MSFT",
            "quarter_label": "Q1_FY2024",
            "attributed_at": "2024-01-01T00:00:00+00:00",
        }
        text, ordered = self._render({
            "ticker_lessons": [],
            "global_lessons": [v1_dict_entry],
        })
        # No "Lesson: " prefix, no mechanism block.
        self.assertIn("L1. [macro]\nmacro body", text)
        self.assertNotIn("Lesson: macro body", text)
        self.assertNotIn("Mechanism:", text)
        self.assertEqual(ordered, ["macro body"])

    # ── Field absence in v3 dict ──

    def test_v3_dict_with_missing_optional_fields_still_renders_lesson(self):
        # A v3 dict with lesson_id but missing mechanism/applies_when/
        # invalid_if (e.g., a partial transitional payload) renders the
        # Lesson: line without the missing blocks.
        partial = {
            "lesson_id":     "lsn_partial001",
            "lesson":        "partial body",
            "evidence_refs": ["E1"],
            "scope":         "ticker", "routing_key": "X",
            "audit_history": [], "parent_id": None,
            "_render_status": "active", "_render_audit_counts": {},
        }
        text, _ = self._render({
            "ticker_lessons": [_quarter_row("Q1_FY2024", [partial])],
            "global_lessons": [],
        })
        self.assertIn("Lesson: partial body", text)
        self.assertNotIn("Mechanism:", text)
        self.assertNotIn("Applies when:", text)
        self.assertNotIn("Invalid if:", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
