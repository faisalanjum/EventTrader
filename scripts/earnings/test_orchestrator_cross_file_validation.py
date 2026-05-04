#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.6 (D19) — orchestrator-level cross-file gate.

The hook validator (validate_attribution_result) is path-blind — stdlib-
only, no prediction-file access — so it treats lesson_audit as
structurally optional. The orchestrator's _validate_audit_against_prediction
is the AUTHORITATIVE coverage gate: it has access to both prediction and
bundle files, and enforces:

  1. len(lesson_audit) == len(prediction.lesson_labels)
  2. len(bundle.learning_context lessons) == len(lesson_labels)
     (defensive — T1 already enforces this; D19 stays self-contained)
  3. each audit's lesson_index == its position
  4. predictor_label matches prediction.lesson_labels[i].label
  5. was_cited matches whether i appears in any cites_lesson_indices
  6. lesson_text matches bundle body at lesson_index (whitespace-norm)

All errors are prefixed with ``[cross-file]`` (E32) so the LLM can
distinguish them from schema errors in the H2 retry payload.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import _validate_audit_against_prediction


def _v3_lesson(body, **overrides):
    base = {
        "lesson_id":     "lsn_x",
        "lesson":        body,
        "mechanism":     "m",
        "applies_when":  "a",
        "invalid_if":    "i",
        "evidence_refs": ["E1"],
    }
    base.update(overrides)
    return base


def _bundle_with_ticker_lessons(bodies):
    return {
        "learning_context": {
            "ticker_lessons": [
                {"predictor_lessons": [_v3_lesson(b) for b in bodies]}
            ],
            "global_lessons": [],
        }
    }


def _audit(idx, body, label="confirmed", was_cited=True, **overrides):
    base = {
        "lesson_index":   idx,
        "lesson_text":    body,
        "predictor_label": label,
        "was_cited":      was_cited,
        "review":         "helped",
        "action":         "keep",
        "comment":        "c",
        "evidence_refs":  ["E1"],
    }
    base.update(overrides)
    return base


def _prediction(labels, key_drivers=None):
    """Build minimal prediction_payload with lesson_labels + key_drivers."""
    return {
        "lesson_labels": labels,
        "key_drivers":   key_drivers or [],
    }


class CrossFileValidationTests(unittest.TestCase):

    # ── Pass case ──────────────────────────────────────────────────────

    def test_full_alignment_passes(self):
        bundle = _bundle_with_ticker_lessons(["body1", "body2"])
        prediction = _prediction(
            [{"label": "confirmed"}, {"label": "irrelevant"}],
            key_drivers=[{"cites_lesson_indices": [0]}],
        )
        learning = {"lesson_audit": [
            _audit(0, "body1", label="confirmed", was_cited=True),
            _audit(1, "body2", label="irrelevant", was_cited=False),
        ]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertEqual(errors, [])

    def test_zero_audits_zero_labels_passes(self):
        # First-prediction case — no priors to label, no audits.
        bundle = {"learning_context": {"ticker_lessons": [], "global_lessons": []}}
        prediction = _prediction([])
        learning = {"lesson_audit": []}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertEqual(errors, [])

    # ── Count mismatches ───────────────────────────────────────────────

    def test_audit_count_less_than_label_count(self):
        bundle = _bundle_with_ticker_lessons(["b1", "b2"])
        prediction = _prediction([{"label": "confirmed"}, {"label": "confirmed"}])
        learning = {"lesson_audit": [_audit(0, "b1")]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("count 1" in e and "count 2" in e for e in errors), errors)
        self.assertTrue(all(e.startswith("[cross-file]") for e in errors), errors)

    def test_audit_count_greater_than_label_count(self):
        bundle = _bundle_with_ticker_lessons(["b1"])
        prediction = _prediction([{"label": "confirmed"}])
        learning = {"lesson_audit": [_audit(0, "b1"), _audit(1, "extra")]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("count 2" in e and "count 1" in e for e in errors), errors)

    def test_lesson_audit_not_a_list(self):
        bundle = _bundle_with_ticker_lessons(["b1"])
        prediction = _prediction([{"label": "confirmed"}])
        learning = {"lesson_audit": {"not": "list"}}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("must be a list" in e for e in errors), errors)

    def test_bundle_lesson_count_mismatch(self):
        # Bundle has 2 lessons, prediction labels 1 — D19 catches even
        # though T1 would already reject this case.
        bundle = _bundle_with_ticker_lessons(["b1", "b2"])
        prediction = _prediction([{"label": "confirmed"}])
        learning = {"lesson_audit": [_audit(0, "b1")]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(
            any("bundle.learning_context lesson count" in e for e in errors),
            errors,
        )

    # ── Per-audit field mismatches ─────────────────────────────────────

    def test_lesson_index_drift(self):
        bundle = _bundle_with_ticker_lessons(["b1", "b2"])
        prediction = _prediction([{"label": "confirmed"}, {"label": "confirmed"}])
        learning = {"lesson_audit": [
            _audit(0, "b1"),
            _audit(99, "b2"),  # wrong index
        ]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("lesson_index = 99" in e for e in errors), errors)

    def test_predictor_label_mismatch(self):
        bundle = _bundle_with_ticker_lessons(["b1"])
        prediction = _prediction([{"label": "irrelevant"}])
        learning = {"lesson_audit": [_audit(0, "b1", label="confirmed")]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("predictor_label" in e for e in errors), errors)

    def test_was_cited_mismatch_predictor_cites_audit_says_no(self):
        bundle = _bundle_with_ticker_lessons(["b1"])
        prediction = _prediction(
            [{"label": "confirmed"}],
            key_drivers=[{"cites_lesson_indices": [0]}],  # cites lesson 0
        )
        learning = {"lesson_audit": [_audit(0, "b1", was_cited=False)]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("was_cited" in e for e in errors), errors)

    def test_was_cited_mismatch_audit_says_cited_predictor_didnt(self):
        bundle = _bundle_with_ticker_lessons(["b1"])
        prediction = _prediction(
            [{"label": "irrelevant"}],
            key_drivers=[],  # no cites
        )
        learning = {"lesson_audit": [_audit(0, "b1", label="irrelevant",
                                              was_cited=True)]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("was_cited" in e for e in errors), errors)

    def test_lesson_text_drift(self):
        bundle = _bundle_with_ticker_lessons(["actual body"])
        prediction = _prediction([{"label": "confirmed"}])
        learning = {"lesson_audit": [_audit(0, "DIFFERENT body")]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertTrue(any("lesson_text drift" in e for e in errors), errors)

    def test_lesson_text_whitespace_normalized(self):
        # Whitespace + case differences must NOT trigger drift.
        bundle = _bundle_with_ticker_lessons(["the body text"])
        prediction = _prediction(
            [{"label": "confirmed"}],
            key_drivers=[{"cites_lesson_indices": [0]}],
        )
        learning = {"lesson_audit": [_audit(0, "  THE   BODY   TEXT  ",
                                              was_cited=True)]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertEqual(errors, [])

    # ── Multi-cite key_drivers ─────────────────────────────────────────

    def test_was_cited_aggregates_across_key_drivers(self):
        bundle = _bundle_with_ticker_lessons(["b1", "b2", "b3"])
        prediction = _prediction(
            [{"label": "confirmed"}, {"label": "confirmed"}, {"label": "confirmed"}],
            key_drivers=[
                {"cites_lesson_indices": [0, 1]},  # cites L1+L2
                {"cites_lesson_indices": [2]},     # cites L3
            ],
        )
        learning = {"lesson_audit": [
            _audit(0, "b1", was_cited=True),
            _audit(1, "b2", was_cited=True),
            _audit(2, "b3", was_cited=True),
        ]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertEqual(errors, [])

    # ── Error prefix invariant ─────────────────────────────────────────

    def test_all_errors_have_cross_file_prefix(self):
        # Every error from this function must be tagged so the H2 retry
        # prompt can distinguish cross-file from schema errors.
        bundle = _bundle_with_ticker_lessons(["b1"])
        prediction = _prediction([{"label": "irrelevant"}])
        learning = {"lesson_audit": [
            _audit(99, "DIFFERENT", label="confirmed", was_cited=True),
        ]}
        errors = _validate_audit_against_prediction(learning, prediction, bundle)
        self.assertGreater(len(errors), 0)
        for e in errors:
            self.assertTrue(
                e.startswith("[cross-file]"),
                f"error missing [cross-file] prefix: {e!r}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
