#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.3 (D6 + D17) — compute_status pure-function table.

Status state machine (live mode = no PIT filter; caller is responsible
for pre-filtering audit_history to PIT-visible audits before calling):

  (a) action="retire" anywhere in audits → retired (terminal)
  (b) action="refine" anywhere in audits → retired (parent retired by
      refinement; replacement is a new lesson with parent_id link)
  (c) misled count in last 5 ≥ 3 → retired
  (d) misled count in last 5 ≥ 2 OR missed count in last 5 ≥ 2 → watch
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

    # ── Threshold (d) — 2 misled or 2 missed → watch ──
    def test_two_misled_in_last_five_watch(self):
        audits = [_audit(review="misled"), _audit(review="misled"),
                  _audit(review="helped")]
        self.assertEqual(compute_status(_lesson(audits)), "watch")

    def test_two_missed_in_last_five_watch(self):
        audits = [_audit(review="missed"), _audit(review="missed"),
                  _audit(review="neutral")]
        self.assertEqual(compute_status(_lesson(audits)), "watch")

    def test_one_misled_one_missed_no_watch(self):
        # Threshold is 2 of EITHER review type — 1+1 doesn't trigger.
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
