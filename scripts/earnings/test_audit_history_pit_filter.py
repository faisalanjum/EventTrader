#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.5.2 (B1) — per-lesson audit_history PIT filter.

Pre-commit-2 latent bug: the lesson-level PIT filter (_passes_pit on
source_pit_cutoff) hid lessons created after the predictor's pit_cutoff,
but did NOT filter the lesson's audit_history. A historical replay would
see FUTURE audits attached to a lesson that itself was visible — leaking
hindsight into the predictor's render-time view.

B1 fix: in build_learning_context, after the lesson PIT + self-leak
filters, run _apply_render_view per surviving lesson. _apply_render_view:
  * filters audit_history to entries with audit_pit_cutoff <= pit_cutoff
  * computes status from the PIT-visible subset
  * drops the lesson if status==retired (audit-driven retirement)
  * attaches transient _render_status + _render_audit_counts

This file pins:
  1. _passes_audit_pit live-mode short-circuit (pit_cutoff=None → always True)
  2. _passes_audit_pit historical mode tz-aware comparison
  3. _apply_render_view PIT-filters the audit list it returns
  4. _apply_render_view drops retired lessons (returns None)
  5. _apply_render_view's status reflects only the PIT-visible audits
     (future retire-trigger audits hidden in earlier replays → status
     reverts to active)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import _apply_render_view, _passes_audit_pit


def _audit(audit_pit_cutoff, review="helped", action="keep"):
    return {
        "audit_pit_cutoff": audit_pit_cutoff,
        "review": review, "action": action,
        "auditor_ticker": "X", "auditor_quarter_label": "Q1",
    }


# ── _passes_audit_pit ───────────────────────────────────────────────────


class PassesAuditPitTests(unittest.TestCase):
    def test_live_mode_passes_everything(self):
        # Live mode: pit_cutoff is None — every audit passes regardless of
        # its audit_pit_cutoff value (incl. None).
        for apc in (None, "2024-01-01T00:00:00+00:00",
                    "2099-12-31T23:59:59+00:00"):
            with self.subTest(apc=apc):
                self.assertTrue(_passes_audit_pit({"audit_pit_cutoff": apc}, None))

    def test_historical_audit_before_cutoff_passes(self):
        # Audit at 2024-01-01, cutoff at 2024-06-01 → audit visible.
        self.assertTrue(_passes_audit_pit(
            {"audit_pit_cutoff": "2024-01-01T00:00:00+00:00"},
            "2024-06-01T00:00:00+00:00",
        ))

    def test_historical_audit_after_cutoff_excluded(self):
        # Audit at 2024-12-01, cutoff at 2024-06-01 → audit NOT visible.
        self.assertFalse(_passes_audit_pit(
            {"audit_pit_cutoff": "2024-12-01T00:00:00+00:00"},
            "2024-06-01T00:00:00+00:00",
        ))

    def test_historical_missing_audit_pit_excludes(self):
        # No audit_pit_cutoff in historical mode = defensive exclude.
        self.assertFalse(_passes_audit_pit(
            {}, "2024-06-01T00:00:00+00:00",
        ))

    def test_naive_datetime_excludes(self):
        # Both must be tz-aware (no naive comparisons).
        self.assertFalse(_passes_audit_pit(
            {"audit_pit_cutoff": "2024-01-01T00:00:00"},  # naive
            "2024-06-01T00:00:00+00:00",
        ))

    def test_z_suffix_normalized(self):
        # "Z" must work as +00:00.
        self.assertTrue(_passes_audit_pit(
            {"audit_pit_cutoff": "2024-01-01T00:00:00Z"},
            "2024-06-01T00:00:00+00:00",
        ))

    def test_tz_offset_chronological_not_lexical(self):
        # 2024-06-12T16:19:05-04:00 = 20:19:05 UTC.
        # 2024-06-12T20:18:00+00:00 = 20:18:00 UTC.
        # Lexically src ('16:...') appears earlier, but chronologically
        # it is LATER by 65s. Must use parsed datetime comparison.
        self.assertFalse(_passes_audit_pit(
            {"audit_pit_cutoff": "2024-06-12T16:19:05-04:00"},
            "2024-06-12T20:18:00+00:00",
        ))


# ── _apply_render_view ──────────────────────────────────────────────────


class ApplyRenderViewTests(unittest.TestCase):
    def test_live_mode_keeps_all_audits(self):
        lesson = {
            "lesson": "x", "audit_history": [
                _audit(None),
                _audit("2024-01-01T00:00:00+00:00"),
                _audit("2099-01-01T00:00:00+00:00"),
            ],
        }
        view = _apply_render_view(lesson, pit_cutoff=None)
        self.assertEqual(len(view["audit_history"]), 3)
        self.assertEqual(view["_render_status"], "active")

    def test_historical_filters_future_audits(self):
        # 2 past, 1 future (2099). Replay at 2024-06-01 should see 2.
        lesson = {
            "lesson": "x", "audit_history": [
                _audit("2024-01-01T00:00:00+00:00", review="helped"),
                _audit("2024-03-01T00:00:00+00:00", review="helped"),
                _audit("2099-01-01T00:00:00+00:00", review="misled"),
            ],
        }
        view = _apply_render_view(lesson, pit_cutoff="2024-06-01T00:00:00+00:00")
        self.assertEqual(len(view["audit_history"]), 2)
        self.assertEqual(view["_render_status"], "active")
        self.assertEqual(view["_render_audit_counts"].get("helped"), 2)
        self.assertNotIn("misled", view["_render_audit_counts"])

    def test_drop_retired_returns_none(self):
        # 3 misled audits all visible → status=retired → return None
        lesson = {
            "lesson": "x", "audit_history": [
                _audit("2024-01-01T00:00:00+00:00", review="misled"),
                _audit("2024-02-01T00:00:00+00:00", review="misled"),
                _audit("2024-03-01T00:00:00+00:00", review="misled"),
            ],
        }
        view = _apply_render_view(lesson, pit_cutoff="2024-06-01T00:00:00+00:00")
        self.assertIsNone(view, "retired lesson must be dropped from render")

    def test_future_retirement_hidden_in_earlier_replay(self):
        # B1 critical: lesson with 3 misled audits ALL in 2099. At a
        # 2024 PIT replay, those audits are hidden, so the lesson
        # should be active (not retired).
        lesson = {
            "lesson": "x", "audit_history": [
                _audit("2099-01-01T00:00:00+00:00", review="misled"),
                _audit("2099-02-01T00:00:00+00:00", review="misled"),
                _audit("2099-03-01T00:00:00+00:00", review="misled"),
            ],
        }
        view = _apply_render_view(lesson, pit_cutoff="2024-06-01T00:00:00+00:00")
        self.assertIsNotNone(view, "future audits must be PIT-filtered out")
        self.assertEqual(view["_render_status"], "active")
        self.assertEqual(len(view["audit_history"]), 0)

    def test_action_retire_at_future_pit_hidden_in_earlier_replay(self):
        # Same B1 invariant for the explicit-action terminal rule.
        lesson = {
            "lesson": "x", "audit_history": [
                _audit("2099-01-01T00:00:00+00:00", action="retire"),
            ],
        }
        view = _apply_render_view(lesson, pit_cutoff="2024-06-01T00:00:00+00:00")
        self.assertIsNotNone(view)
        self.assertEqual(view["_render_status"], "active")

    def test_v1_string_lesson_passes_through(self):
        # Legacy v1 string-bodied lesson — no audit_history field; treat
        # as active by construction. The transitional str-fallback is
        # preserved until renderer migration in commit 3.
        view = _apply_render_view("legacy string lesson", pit_cutoff=None)
        # Implementation choice: returns the input unchanged for non-dicts
        # so the renderer can format the string body directly.
        self.assertEqual(view, "legacy string lesson")

    def test_audit_count_dict_shape(self):
        lesson = {
            "lesson": "x", "audit_history": [
                _audit("2024-01-01T00:00:00+00:00", review="helped"),
                _audit("2024-02-01T00:00:00+00:00", review="helped"),
                _audit("2024-03-01T00:00:00+00:00", review="outweighed"),
            ],
        }
        view = _apply_render_view(lesson, pit_cutoff=None)
        self.assertEqual(view["_render_audit_counts"], {"helped": 2, "outweighed": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
