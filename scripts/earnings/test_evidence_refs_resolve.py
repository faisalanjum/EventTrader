#!/usr/bin/env python3
"""B3 phantom-ID rejection (LearnerLoopRevamp.md §8.3, decision D16/B3).

Every ``evidence_refs`` ID emitted in an attribution_result.v3 payload must
resolve to an entry in the same payload's ``evidence_ledger``. Phantom IDs
(referenced but not in the ledger) are rejected loudly so the learner cannot
fabricate evidence pointers.

Coverage — phantom IDs in each of the 4 ref-bearing locations:
  1. feedback.predictor_lessons[i].evidence_refs (N3)
  2. global_observations[i].evidence_refs (N3)
  3. lesson_audit[i].evidence_refs (B3 + #3)
  4. lesson_audit[i].replacement_lesson.evidence_refs (#4 — same rule
     applies to the refined lesson)

Plus negative controls:
  * Resolved IDs pass (positive control)
  * Mixed valid + phantom → only phantom flagged (granularity check)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))       # this dir

from validate_learning import validate_attribution_result
from test_validate_learning_v3 import (
    _skeleton, _global_obs, _predictor_lesson, _lesson_audit, _replacement,
)


def _validate(payload):
    return validate_attribution_result(payload, "AAPL", "Q1_FY2025")


def _add_ledger_entry(payload, eid):
    """Helper — extend evidence_ledger with a second entry."""
    payload["evidence_ledger"].append(
        {"id": eid, "claim": "demo", "value": "x", "source": "test", "date": "2025-05-01"}
    )
    return payload


class PhantomEvidenceRefTests(unittest.TestCase):

    # ── 1. predictor_lessons.evidence_refs ──
    def test_phantom_id_in_predictor_lesson_rejected(self):
        errors = _validate(_skeleton(predictor_lessons=[
            _predictor_lesson(evidence_refs=["E_PHANTOM"])
        ]))
        self.assertTrue(
            any("predictor_lessons[0].evidence_refs" in e and "E_PHANTOM" in e for e in errors),
            errors,
        )

    def test_phantom_among_valid_in_predictor_lesson_flagged(self):
        # Only the phantom ID should error; valid ID stays silent.
        payload = _add_ledger_entry(_skeleton(predictor_lessons=[
            _predictor_lesson(evidence_refs=["E1", "E_PHANTOM"])
        ]), "E2")
        errors = _validate(payload)
        phantom_errors = [e for e in errors if "E_PHANTOM" in e]
        self.assertEqual(len(phantom_errors), 1, errors)
        self.assertFalse(any("'E1'" in e for e in errors), errors)

    # ── 2. global_observations.evidence_refs ──
    def test_phantom_id_in_global_obs_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("sector", evidence_refs=["E_PHANTOM"])
        ]))
        self.assertTrue(
            any("global_observations[0].evidence_refs" in e and "E_PHANTOM" in e for e in errors),
            errors,
        )

    def test_phantom_id_in_macro_obs_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("macro", evidence_refs=["E_NOPE"])
        ]))
        self.assertTrue(
            any("global_observations[0].evidence_refs" in e and "E_NOPE" in e for e in errors),
            errors,
        )

    # ── 3. lesson_audit.evidence_refs ──
    def test_phantom_id_in_lesson_audit_rejected(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(evidence_refs=["E_PHANTOM"])
        ]))
        self.assertTrue(
            any("lesson_audit[0].evidence_refs" in e and "E_PHANTOM" in e for e in errors),
            errors,
        )

    def test_multiple_phantoms_in_audit_each_flagged(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(evidence_refs=["E_BAD1", "E_BAD2"])
        ]))
        bad1 = [e for e in errors if "E_BAD1" in e]
        bad2 = [e for e in errors if "E_BAD2" in e]
        self.assertEqual(len(bad1), 1, errors)
        self.assertEqual(len(bad2), 1, errors)

    # ── 4. replacement_lesson.evidence_refs ──
    def test_phantom_id_in_replacement_lesson_rejected(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(review="misled", action="refine",
                          replacement_lesson=_replacement(evidence_refs=["E_PHANTOM"]))
        ]))
        self.assertTrue(
            any("replacement_lesson.evidence_refs" in e and "E_PHANTOM" in e for e in errors),
            errors,
        )

    # ── Positive control: every ID resolves → no errors ──
    def test_all_resolved_ids_pass(self):
        payload = _add_ledger_entry(_skeleton(
            predictor_lessons=[_predictor_lesson(evidence_refs=["E1", "E2"])],
            global_observations=[_global_obs("sector", evidence_refs=["E2"])],
            lesson_audit=[_lesson_audit(evidence_refs=["E1"])],
        ), "E2")
        self.assertEqual(_validate(payload), [])

    # ── Cross-section: phantom in one section doesn't mask valid in another ──
    def test_phantom_in_one_section_doesnt_mask_other_sections(self):
        payload = _skeleton(
            predictor_lessons=[_predictor_lesson(evidence_refs=["E1"])],
            global_observations=[_global_obs("sector", evidence_refs=["E_PHANTOM"])],
            lesson_audit=[_lesson_audit(evidence_refs=["E1"])],
        )
        errors = _validate(payload)
        # Exactly one phantom error, in the global_observations location.
        phantom_errors = [e for e in errors if "E_PHANTOM" in e]
        self.assertEqual(len(phantom_errors), 1, errors)
        self.assertIn("global_observations[0]", phantom_errors[0])

    # ── Sanity: existing primary_driver.evidence_refs check still fires ──
    # (B3 is the v3-side audit/lesson check; primary_driver was already
    # ref-checked in v2 common-core. Belt-and-suspenders sanity test.)
    def test_phantom_in_primary_driver_rejected(self):
        payload = _skeleton()
        payload["primary_driver"]["evidence_refs"] = ["E_PHANTOM"]
        errors = _validate(payload)
        self.assertTrue(
            any("primary_driver.evidence_refs" in e and "E_PHANTOM" in e for e in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
