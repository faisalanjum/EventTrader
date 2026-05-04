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


# ── Commit 2.1 — _full_validate_for_orchestrator sibling totality ──
# A JSON-valid but non-object sibling file (prediction/result.json or
# context_bundle.json being ``[]``, ``"bad"``, ``null``, etc.) used to
# crash _validate_audit_against_prediction's ``.get(...)`` calls. Same
# totality principle as commit 1.5 (validator) — surface a typed
# error so the H2 retry loop can feed it back to the LLM.


import json as _json
import tempfile

from earnings_orchestrator import _full_validate_for_orchestrator


def _valid_v3_payload():
    return {
        "schema_version": "attribution_result.v3",
        "ticker": "AAPL", "quarter_label": "Q1_FY2025",
        "filed_8k": "2025-05-01T16:30:00-04:00",
        "accession_8k": "0000123456-25-000001",
        "attributed_at": "2026-01-01T00:00:00+00:00",
        "model_version": "claude-opus-4-7",
        "pit_mode": "historical",
        "pit_cutoff": "2025-07-31T16:00:00-04:00",
        "pit_boundary_source": "next_quarter",
        "actual_return": {"daily_stock_pct": -5.0, "market_session": "after_hours"},
        "evidence_ledger": [
            {"id": "E1", "claim": "d", "value": "x", "source": "t", "date": "2025-05-01"}
        ],
        "primary_driver": {"summary": "d", "category": "g", "evidence_refs": ["E1"]},
        "contributing_factors": [],
        "feedback": {
            "prediction_comparison": {
                "predicted_direction": "long", "predicted_confidence_score": 50,
                "predicted_move_range_pct": [1.0, 3.0], "predicted_key_drivers": ["d"],
                "actual_direction": "short", "direction_correct": False,
                "magnitude_error_pct": 6.0, "comment": "d",
            },
            "what_worked": [], "what_failed": [], "why": "d",
            "predictor_lessons": [], "data_lessons": [],
        },
        "global_observations": [], "missing_inputs": [],
        "data_sources_used": ["t"],
        "context_bundle_ref": "context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
    }


class FullValidateSiblingTotalityTests(unittest.TestCase):
    """Pin sibling totality (commit 2.1 fix). Each malformed sibling file
    must produce a typed [cross-file] error and never raise."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.pred = self.tmp / "prediction.json"
        self.bundle = self.tmp / "bundle.json"

    def tearDown(self):
        self._tmp.cleanup()

    def _validate(self):
        try:
            return _full_validate_for_orchestrator(
                _valid_v3_payload(), "AAPL", "Q1_FY2025", self.pred, self.bundle,
            )
        except Exception as e:
            raise AssertionError(
                f"_full_validate_for_orchestrator raised {type(e).__name__}: "
                f"{e!r} — totality contract requires errors as a list"
            ) from None

    # ── prediction sibling not a JSON object ──

    def test_prediction_is_list_returns_error(self):
        self.pred.write_text("[]")
        self.bundle.write_text(_json.dumps({"learning_context": {
            "ticker_lessons": [], "global_lessons": []}}))
        errors, pp, bb = self._validate()
        self.assertIsNone(pp); self.assertIsNone(bb)
        self.assertTrue(any("prediction/result.json must be a JSON object" in e
                              for e in errors), errors)
        self.assertTrue(all(e.startswith("[cross-file]") for e in errors), errors)

    def test_prediction_is_string_returns_error(self):
        self.pred.write_text('"bad"')
        self.bundle.write_text(_json.dumps({"learning_context": {
            "ticker_lessons": [], "global_lessons": []}}))
        errors, pp, bb = self._validate()
        self.assertTrue(any("prediction/result.json" in e for e in errors), errors)

    def test_prediction_is_null_returns_error(self):
        self.pred.write_text("null")
        self.bundle.write_text(_json.dumps({"learning_context": {
            "ticker_lessons": [], "global_lessons": []}}))
        errors, pp, bb = self._validate()
        self.assertTrue(any("prediction/result.json" in e for e in errors), errors)

    # ── bundle sibling not a JSON object ──

    def test_bundle_is_list_returns_error(self):
        self.pred.write_text(_json.dumps({"lesson_labels": [], "key_drivers": []}))
        self.bundle.write_text("[]")
        errors, pp, bb = self._validate()
        self.assertTrue(any("context_bundle.json must be a JSON object" in e
                              for e in errors), errors)

    def test_both_siblings_non_object_returns_two_errors(self):
        self.pred.write_text("[]")
        self.bundle.write_text('"bad"')
        errors, pp, bb = self._validate()
        # Both sibling messages should be present
        self.assertTrue(any("prediction/result.json" in e for e in errors))
        self.assertTrue(any("context_bundle.json" in e for e in errors))

    # ── learning_context within a dict bundle ──

    def test_bundle_learning_context_not_dict_returns_error(self):
        self.pred.write_text(_json.dumps({"lesson_labels": [], "key_drivers": []}))
        # Bundle is a dict, but learning_context is a list — would crash
        # iter_labeled_lessons('list').get(...).
        self.bundle.write_text(_json.dumps({"learning_context": []}))
        errors, pp, bb = self._validate()
        self.assertTrue(any(
            "context_bundle.learning_context must be a JSON object" in e
            for e in errors
        ), errors)

    def test_bundle_missing_learning_context_returns_error(self):
        # Missing learning_context (key absent → bundle.get() returns None
        # which is not a dict).
        self.pred.write_text(_json.dumps({"lesson_labels": [], "key_drivers": []}))
        self.bundle.write_text(_json.dumps({"some_other_key": "x"}))
        errors, pp, bb = self._validate()
        self.assertTrue(any("learning_context" in e for e in errors), errors)

    # ── Positive control — both siblings valid → cross-file runs ──

    def test_valid_dict_siblings_returns_no_type_errors(self):
        self.pred.write_text(_json.dumps({"lesson_labels": [], "key_drivers": []}))
        self.bundle.write_text(_json.dumps({"learning_context": {
            "ticker_lessons": [], "global_lessons": []}}))
        errors, pp, bb = self._validate()
        # No type-related errors; pp and bb are loaded.
        self.assertNotIn(pp, (None,))
        self.assertNotIn(bb, (None,))
        # Cross-file runs (no audits, no labels — passes vacuously).
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
