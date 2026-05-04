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


# ── Commit 2.1 — retired-only rows dropped before ticker cap ──
# build_learning_context cap is on rows (8 newest). Without the post-
# _apply_render_view "drop empty predictor_lessons" filter, 8 retired-only
# rows could fill the cap and crowd out a 9th row whose lessons are still
# active — a violation of "retired lessons must never consume cap slots"
# (user clarification #2). Reproducer + regression test.


class RetiredOnlyRowDoesNotConsumeCapTests(unittest.TestCase):
    """Pin user-#2 invariant for the ticker-row cap (commit 2.1 fix)."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.companies_dir = self.tmp / "Companies"
        self.companies_dir.mkdir()
        self.learnings_dir = self.tmp / "learnings"
        self.learnings_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _lesson(self, body, audit_actions=()):
        from earnings_orchestrator import compute_lesson_id
        return {
            "lesson_id":     compute_lesson_id(body, "ticker", "AVGO"),
            "lesson":        body, "mechanism": "m", "applies_when": "a",
            "invalid_if":    "i", "evidence_refs": ["E1"],
            "scope": "ticker", "routing_key": "AVGO",
            "audit_history": [
                {"action": a, "review": "misled",
                 "audit_pit_cutoff": None,
                 "auditor_ticker": "X", "auditor_quarter_label": f"Q{i}"}
                for i, a in enumerate(audit_actions)
            ],
            "parent_id": None,
        }

    def _write_ticker(self, lessons):
        import json as _json
        ticker_dir = self.learnings_dir / "ticker"
        ticker_dir.mkdir(parents=True, exist_ok=True)
        (ticker_dir / "AVGO.json").write_text(_json.dumps({
            "schema_version": "ticker_lessons.v2", "ticker": "AVGO",
            "updated_at": None, "lessons": lessons,
        }), encoding="utf-8")

    def test_eight_retired_rows_do_not_crowd_out_active_row(self):
        # 8 newest rows have only-retired lessons; 9th (oldest) row has
        # an active lesson. After commit 2.1, the active row must survive
        # the cap — even though it's the oldest by attributed_at.
        import earnings_orchestrator as orch
        rows = []
        for i in range(8):
            rows.append({
                "quarter_label":  f"Q{i:02d}_FY2024",
                "attributed_at":  f"2024-{i+1:02d}-01T00:00:00+00:00",
                "predictor_lessons": [self._lesson(f"r{i}", audit_actions=("retire",))],
            })
        rows.append({
            "quarter_label":  "Q99_FY2023",
            "attributed_at":  "2023-12-01T00:00:00+00:00",
            "predictor_lessons": [self._lesson("active body")],
        })
        self._write_ticker(rows)
        result = orch.build_learning_context(
            "AVGO", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        visible_quarters = [r["quarter_label"] for r in result["ticker_lessons"]]
        self.assertIn("Q99_FY2023", visible_quarters,
                      "active row was crowded out by retired-only rows")

    def test_originally_empty_rows_also_dropped(self):
        # A row with no predictor_lessons (e.g., learner emitted 0 new
        # lessons) is also dropped before the cap. Its Context-Only
        # block utility is secondary; freeing the slot for lesson-bearing
        # quarters takes priority.
        import earnings_orchestrator as orch
        self._write_ticker([
            {"quarter_label":  "Q1_FY2024",
             "attributed_at":  "2024-01-01T00:00:00+00:00",
             "predictor_lessons": []},
            {"quarter_label":  "Q2_FY2024",
             "attributed_at":  "2024-04-01T00:00:00+00:00",
             "predictor_lessons": [self._lesson("active body")]},
        ])
        result = orch.build_learning_context(
            "AVGO", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        visible = [r["quarter_label"] for r in result["ticker_lessons"]]
        self.assertEqual(visible, ["Q2_FY2024"])

    def test_partially_retired_row_survives(self):
        # A row with mixed retired + active lessons survives the cap
        # (predictor_lessons is non-empty after _apply_render_view).
        import earnings_orchestrator as orch
        self._write_ticker([{
            "quarter_label":  "Q1_FY2024",
            "attributed_at":  "2024-01-01T00:00:00+00:00",
            "predictor_lessons": [
                self._lesson("retired_one", audit_actions=("retire",)),
                self._lesson("active_one"),
            ],
        }])
        result = orch.build_learning_context(
            "AVGO", base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
        )
        self.assertEqual(len(result["ticker_lessons"]), 1)
        # Only the active lesson should remain
        surviving = result["ticker_lessons"][0]["predictor_lessons"]
        self.assertEqual(len(surviving), 1)
        self.assertEqual(surviving[0]["lesson"], "active_one")


if __name__ == "__main__":
    unittest.main(verbosity=2)
