#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.3 (D6 + D17) — compute_status pure-function table.

Status state machine (live mode = no PIT filter; caller is responsible
for pre-filtering audit_history to PIT-visible audits before calling):

  (a) action="retire" anywhere in audits → retired (terminal)
  (b) action="refine" anywhere in audits → retired (parent retired by
      refinement; replacement is a new lesson with parent_id link)
  (c) misled count in last 5 ≥ 3 → retired
  (d) misled count in last 5 ≥ 2 → watch
      (`missed` never penalizes — predictor underuse, not lesson weakness;
       applied 2026-05-06 per plan §21 partial)
  (e) otherwise → active

D6 invariant: outweighed never penalizes. A lesson with all-outweighed
audits stays active — the lesson logic was sound, other forces won.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import compute_status


def _audit(review="helped", action="keep", **kw):
    base = {"review": review, "action": action,
            "auditor_ticker": "X", "auditor_quarter_label": "Q1"}
    base.update(kw)
    return base


def _lesson(audits=None):
    return {"audit_history": audits or []}


class ComputeStatusTests(unittest.TestCase):

    # ── Empty / new lesson ──
    def test_empty_audits_returns_active(self):
        self.assertEqual(compute_status(_lesson([])), "active")

    def test_no_audit_history_field_returns_active(self):
        self.assertEqual(compute_status({}), "active")

    # ── Terminal action="retire" ──
    def test_single_retire_action_is_terminal(self):
        self.assertEqual(
            compute_status(_lesson([_audit(action="retire")])),
            "retired",
        )

    def test_retire_terminal_among_other_audits(self):
        # Even with helped + outweighed in the window, an explicit retire wins.
        audits = [_audit(review="helped"), _audit(review="outweighed"),
                  _audit(action="retire")]
        self.assertEqual(compute_status(_lesson(audits)), "retired")

    # ── Terminal action="refine" — same semantics as retire for parent ──
    def test_refine_action_retires_parent(self):
        self.assertEqual(
            compute_status(_lesson([_audit(action="refine")])),
            "retired",
        )

    # ── Threshold (c) — 3 misled in last 5 → retired ──
    def test_three_misled_in_last_five_retires(self):
        audits = [_audit(review="misled") for _ in range(3)]
        self.assertEqual(compute_status(_lesson(audits)), "retired")

    def test_three_misled_among_helped_in_window_retires(self):
        # Window of 5: 3 misled + 2 helped — count(misled)=3 → retire
        audits = [_audit(review="helped"), _audit(review="misled"),
                  _audit(review="misled"), _audit(review="helped"),
                  _audit(review="misled")]
        self.assertEqual(compute_status(_lesson(audits)), "retired")

    def test_misled_outside_window_not_counted(self):
        # 3 misled at the start, then 5 helped — only the last 5 count.
        audits = ([_audit(review="misled")] * 3
                  + [_audit(review="helped")] * 5)
        self.assertEqual(compute_status(_lesson(audits)), "active")

    # ── Threshold (d) — 2 misled → watch (`missed` never penalizes; §21) ──
    def test_two_misled_in_last_five_watch(self):
        audits = [_audit(review="misled"), _audit(review="misled"),
                  _audit(review="helped")]
        self.assertEqual(compute_status(_lesson(audits)), "watch")

    def test_two_missed_does_not_trigger_watch(self):
        """`missed` = predictor labeled `irrelevant` when lesson actually
        applied = predictor underuse, NOT lesson weakness. Plan §21 partial
        applied 2026-05-06 — `missed` no longer pushes status to `watch`."""
        audits = [_audit(review="missed"), _audit(review="missed"),
                  _audit(review="neutral")]
        self.assertEqual(compute_status(_lesson(audits)), "active")

    def test_one_misled_one_missed_no_watch(self):
        # Only `misled` counts toward watch (post §21 partial). 1 misled doesn't trip.
        audits = [_audit(review="misled"), _audit(review="missed")]
        self.assertEqual(compute_status(_lesson(audits)), "active")

    # ── D6 invariant: outweighed never penalizes ──
    def test_all_outweighed_stays_active(self):
        audits = [_audit(review="outweighed") for _ in range(5)]
        self.assertEqual(compute_status(_lesson(audits)), "active")

    def test_outweighed_does_not_count_toward_misled(self):
        # 1 misled + 4 outweighed → only 1 misled in window → active
        audits = ([_audit(review="misled")]
                  + [_audit(review="outweighed")] * 4)
        self.assertEqual(compute_status(_lesson(audits)), "active")

    # ── Neutral / unclear are no-pressure ──
    def test_all_neutral_stays_active(self):
        audits = [_audit(review="neutral") for _ in range(5)]
        self.assertEqual(compute_status(_lesson(audits)), "active")

    def test_all_unclear_stays_active(self):
        audits = [_audit(review="unclear") for _ in range(5)]
        self.assertEqual(compute_status(_lesson(audits)), "active")

    # ── Window edge: last 5 ──
    def test_window_size_is_five(self):
        # 6 audits where the first is retire and last 5 are helped.
        # The window-based misled threshold doesn't fire, BUT explicit
        # action="retire" check sweeps the WHOLE history (terminal-action
        # rule (a) is window-independent).
        audits = ([_audit(action="retire")]
                  + [_audit(review="helped")] * 5)
        self.assertEqual(compute_status(_lesson(audits)), "retired")

    def test_misled_only_counts_within_window(self):
        # 2 misled at front, then 5 helped → window=last 5 has 0 misled
        audits = ([_audit(review="misled"), _audit(review="misled")]
                  + [_audit(review="helped")] * 5)
        self.assertEqual(compute_status(_lesson(audits)), "active")

    # ── helped is positive — does not move status ──
    def test_all_helped_stays_active(self):
        audits = [_audit(review="helped") for _ in range(5)]
        self.assertEqual(compute_status(_lesson(audits)), "active")

    # ── Refinement is independent of window (terminal) ──
    def test_old_refine_still_retires_even_outside_window(self):
        # Same window-independence as retire (rule (b)).
        audits = ([_audit(action="refine")]
                  + [_audit(review="helped")] * 10)
        self.assertEqual(compute_status(_lesson(audits)), "retired")


# ── Commit 2.1 — compute_status totality ──
# compute_status is on the bundle-assembly hot path. A corrupt
# audit_history in any library file would otherwise crash every
# prediction's bundle build. Same totality contract as commit 1.5/1.6
# applied to the validator: published functions return a value,
# never raise on malformed input.


class ComputeStatusTotalityTests(unittest.TestCase):
    """Each malformed input must produce a value (not raise)."""

    def _check(self, lesson, expected="active"):
        try:
            actual = compute_status(lesson)
        except Exception as e:
            self.fail(f"compute_status raised {type(e).__name__}: {e!r} — "
                      f"contract violation; must return a string")
        self.assertEqual(actual, expected,
                          f"unexpected status for input {lesson!r}")

    def test_lesson_is_none(self):
        self._check(None)

    def test_lesson_is_string(self):
        self._check("legacy v1 lesson body")

    def test_lesson_is_list(self):
        self._check(["not", "a", "dict"])

    def test_audit_history_is_string(self):
        self._check({"audit_history": "bad"})

    def test_audit_history_is_dict(self):
        self._check({"audit_history": {"a": "b"}})

    def test_audit_history_is_int(self):
        self._check({"audit_history": 42})

    def test_audit_history_contains_none(self):
        self._check({"audit_history": [None]})

    def test_audit_history_contains_string(self):
        self._check({"audit_history": ["bad"]})

    def test_review_unhashable_list_excluded_from_counter(self):
        # An unhashable review value would crash Counter; the guard skips
        # it. With only one (skipped) audit, status is "active".
        self._check({"audit_history": [{"review": [], "action": "keep"}]})

    def test_review_unhashable_dict_excluded_from_counter(self):
        self._check({"audit_history": [{"review": {}, "action": "keep"}]})

    def test_action_unhashable_does_not_trigger_retire(self):
        # action="retire" check uses tuple membership (== compare), not
        # hash — unhashable action just compares unequal and is ignored.
        self._check({"audit_history": [{"review": "helped", "action": []}]})

    def test_partial_corruption_still_processes_valid_entries(self):
        # 1 valid misled + 1 corrupt entry → only valid one counts.
        # Threshold for retire is 3 misled, so result is "active".
        self._check({"audit_history": [
            {"review": "misled", "action": "keep"},
            None,  # corrupt — skipped
            {"review": [], "action": "keep"},  # corrupt review — review skipped
        ]})

    def test_three_misled_with_corrupt_entries_still_retires(self):
        # 3 valid misled + interleaved corrupt entries → still hits retire
        # threshold over the last-5 window.
        self._check({"audit_history": [
            {"review": "misled", "action": "keep"},
            None,
            {"review": "misled", "action": "keep"},
            "garbage",
            {"review": "misled", "action": "keep"},
        ]}, expected="retired")

    def test_explicit_retire_among_corrupt_is_terminal(self):
        # action="retire" survives; corrupt entries are skipped.
        self._check({"audit_history": [
            None,
            {"action": "retire"},
            "garbage",
        ]}, expected="retired")


if __name__ == "__main__":
    unittest.main(verbosity=2)
