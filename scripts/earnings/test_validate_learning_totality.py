#!/usr/bin/env python3
"""Validator totality regression tests (LearnerLoopRevamp.md commit 1.5).

The validator's contract: ``validate_attribution_result`` MUST return a list
of error strings. It MUST NOT raise on any JSON-decodable input. This is
load-bearing for the orchestrator's H2 informed-retry loop:

  scripts/earnings/earnings_orchestrator.py:1217:
    errors = validate_attribution_result(payload, ticker, ql)

If the validator raises here, the orchestrator never builds the structured
error list it feeds back to the LLM on retry — the H2 loop bypasses entirely
and the run fails noisily instead of producing actionable validation errors.

Pre-commit-1.5 crash sites (verified via direct repro):

  1. ``feedback = "bad"`` → ``AttributeError: 'str' object has no attribute 'get'``
     (``_validate_v3`` did ``fb.get(...)`` without a dict guard)
  2. ``lesson_audit[0].predictor_label = []`` → ``TypeError: unhashable type: 'list'``
     (enum membership ``x in SET`` with non-hashable x)
  3. ``lesson_audit[0].review = []`` → same TypeError
  4. ``global_observations[0].scope = []`` → same TypeError

Plus a wider sweep of analogous holes:

  5. ``lesson_audit[0].action = []``
  6. ``lesson_audit[0].evidence_refs = [{}]`` (unhashable ref vs ledger_ids set)
  7. ``feedback.predictor_lessons[0].evidence_refs = [[]]`` (same pattern, v3 layer)
  8. ``primary_driver.evidence_refs = [{}]`` (same pattern, common-core layer)
  9. ``global_observations[0].related_tickers = [["nested"]]`` (unhashable in
     ``set(rt)`` dedupe check)
  10. ``pit_mode = []`` (common-core enum check)
  11. ``prediction_comparison.predicted_direction = []`` (common-core enum check)
  12. ``evidence_ledger[0].id = []`` (unhashable id in ``set(...)`` ledger_ids)

All cases must produce ``errors != []`` — never an exception.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))       # this dir

from validate_learning import validate_attribution_result


def _base_payload() -> dict:
    """Minimal-valid v3 payload — tests mutate one field per case."""
    return {
        "schema_version": "attribution_result.v3",
        "ticker": "AAPL",
        "quarter_label": "Q1_FY2025",
        "filed_8k": "2025-05-01T16:30:00-04:00",
        "accession_8k": "0000320193-25-000055",
        "attributed_at": "2026-04-17T12:00:00-04:00",
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
                "predicted_direction": "long",
                "predicted_confidence_score": 50,
                "predicted_move_range_pct": [1.0, 3.0],
                "predicted_key_drivers": ["d"],
                "actual_direction": "short",
                "direction_correct": False,
                "magnitude_error_pct": 6.0,
                "comment": "d",
            },
            "what_worked": [],
            "what_failed": [],
            "why": "d",
            "predictor_lessons": [],
            "data_lessons": [],
        },
        "global_observations": [],
        "missing_inputs": [],
        "data_sources_used": ["t"],
        "context_bundle_ref": "context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
    }


def _audit(**overrides) -> dict:
    """Minimal v3-shape lesson_audit entry; overrides mutate one field."""
    base = {
        "lesson_index": 0,
        "lesson_text": "lesson body",
        "predictor_label": "confirmed",
        "was_cited": True,
        "review": "helped",
        "action": "keep",
        "comment": "c",
        "evidence_refs": ["E1"],
    }
    base.update(overrides)
    return base


def _validate_must_return(payload: dict, case_name: str) -> list[str]:
    """Helper: assert the validator returns a list (never raises) and
    returns it for follow-up assertions on error contents."""
    try:
        errors = validate_attribution_result(payload, "AAPL", "Q1_FY2025")
    except Exception as e:  # noqa: BLE001 — the totality contract is "no exceptions"
        raise AssertionError(
            f"{case_name}: validator raised {type(e).__name__}: {e!r} — "
            f"contract violation; must return list of errors instead"
        ) from None
    if not isinstance(errors, list):
        raise AssertionError(
            f"{case_name}: validator returned {type(errors).__name__}, expected list"
        )
    return errors


class ValidatorTotalityTests(unittest.TestCase):
    """Each test mutates ONE field to a malformed value and asserts the
    validator returns a non-empty error list (never raises)."""

    # ── 1–4: ChatGPT-verified crashes ──
    def test_feedback_non_dict_string(self):
        p = _base_payload()
        p["feedback"] = "bad"
        errs = _validate_must_return(p, "feedback='bad'")
        self.assertTrue(any("feedback" in e and "object" in e for e in errs), errs)

    def test_audit_predictor_label_unhashable(self):
        p = _base_payload()
        p["lesson_audit"] = [_audit(predictor_label=[])]
        errs = _validate_must_return(p, "audit.predictor_label=[]")
        self.assertTrue(any("predictor_label" in e for e in errs), errs)

    def test_audit_review_unhashable(self):
        p = _base_payload()
        p["lesson_audit"] = [_audit(review=[])]
        errs = _validate_must_return(p, "audit.review=[]")
        self.assertTrue(any("review" in e for e in errs), errs)

    def test_global_obs_scope_unhashable(self):
        p = _base_payload()
        p["global_observations"] = [{"scope": [], "lesson": "x" * 40}]
        errs = _validate_must_return(p, "global_obs.scope=[]")
        self.assertTrue(any("scope invalid" in e for e in errs), errs)

    # ── 5–7: extended unhashable / wrong-type sweep ──
    def test_audit_action_unhashable(self):
        p = _base_payload()
        p["lesson_audit"] = [_audit(action=[])]
        errs = _validate_must_return(p, "audit.action=[]")
        self.assertTrue(any("action" in e for e in errs), errs)

    def test_audit_evidence_refs_with_dict_item(self):
        p = _base_payload()
        p["lesson_audit"] = [_audit(evidence_refs=[{}])]
        errs = _validate_must_return(p, "audit.evidence_refs=[{}]")
        self.assertTrue(
            any("evidence_refs" in e and "string" in e for e in errs),
            errs,
        )

    def test_predictor_lessons_evidence_refs_with_list_item(self):
        p = _base_payload()
        p["feedback"]["predictor_lessons"] = [{
            "lesson":        "x" * 40,
            "mechanism":     "y" * 40,
            "applies_when":  "z" * 40,
            "invalid_if":    "w" * 40,
            "evidence_refs": [[]],
        }]
        errs = _validate_must_return(p, "predictor_lessons[0].evidence_refs=[[]]")
        self.assertTrue(
            any("evidence_refs" in e and "string" in e for e in errs),
            errs,
        )

    def test_primary_driver_evidence_refs_with_dict_item(self):
        p = _base_payload()
        p["primary_driver"]["evidence_refs"] = [{}]
        errs = _validate_must_return(p, "primary_driver.evidence_refs=[{}]")
        self.assertTrue(
            any("primary_driver.evidence_refs" in e and "string" in e for e in errs),
            errs,
        )

    # ── 8: dedupe with unhashable element ──
    def test_related_tickers_with_nested_list_element(self):
        p = _base_payload()
        p["global_observations"] = [{
            "scope": "cross_ticker",
            "related_tickers": [["nested"]],
            "lesson":        "x" * 40,
            "mechanism":     "y" * 40,
            "applies_when":  "z" * 40,
            "invalid_if":    "w" * 40,
            "evidence_refs": ["E1"],
        }]
        errs = _validate_must_return(p, "related_tickers=[['nested']]")
        # The bad-element check should fire on the nested list, NOT a TypeError.
        self.assertTrue(
            any("related_tickers" in e and "invalid" in e for e in errs),
            errs,
        )

    # ── 9–11: common-core enum totality ──
    def test_pit_mode_unhashable(self):
        p = _base_payload()
        p["pit_mode"] = []
        errs = _validate_must_return(p, "pit_mode=[]")
        self.assertTrue(any("pit_mode" in e for e in errs), errs)

    def test_pit_boundary_source_unhashable(self):
        p = _base_payload()
        p["pit_boundary_source"] = []
        errs = _validate_must_return(p, "pit_boundary_source=[]")
        self.assertTrue(any("pit_boundary_source" in e for e in errs), errs)

    def test_predicted_direction_unhashable(self):
        p = _base_payload()
        p["feedback"]["prediction_comparison"]["predicted_direction"] = []
        errs = _validate_must_return(p, "predicted_direction=[]")
        self.assertTrue(any("predicted_direction" in e for e in errs), errs)

    def test_actual_direction_unhashable(self):
        p = _base_payload()
        p["feedback"]["prediction_comparison"]["actual_direction"] = []
        errs = _validate_must_return(p, "actual_direction=[]")
        self.assertTrue(any("actual_direction" in e for e in errs), errs)

    # ── 12: ledger.id unhashable (set comprehension exposure) ──
    def test_evidence_ledger_id_unhashable(self):
        p = _base_payload()
        p["evidence_ledger"] = [
            {"id": [], "claim": "d", "value": "x", "source": "t", "date": "2025-05-01"}
        ]
        # Force a downstream evidence_ref check so the ledger_ids set is used.
        p["primary_driver"]["evidence_refs"] = ["E1"]
        errs = _validate_must_return(p, "evidence_ledger[0].id=[]")
        # The unhashable id is dropped from ledger_ids; downstream "E1" then
        # fails to resolve. Critically: the ledger_ids comprehension itself
        # must not crash.
        self.assertTrue(
            any("not found in evidence_ledger" in e for e in errs),
            errs,
        )

    # ── Bonus: payload is not a dict-of-strings (defensive — the wrapper's
    # schema_version branch handles missing/wrong type before we reach v3) ──
    def test_unknown_schema_version(self):
        p = _base_payload()
        p["schema_version"] = "attribution_result.v99"
        errs = _validate_must_return(p, "schema_version='v99'")
        self.assertTrue(any("unsupported schema_version" in e for e in errs), errs)

    # ── Bonus: feedback as a list (truthy non-dict — distinct from string) ──
    def test_feedback_as_list(self):
        p = _base_payload()
        p["feedback"] = ["not a dict"]
        errs = _validate_must_return(p, "feedback=['list']")
        self.assertTrue(any("feedback" in e and "object" in e for e in errs), errs)

    # ── Bonus: full malformed payload kitchen sink — validator must not crash ──
    def test_kitchen_sink_malformed_payload(self):
        p = _base_payload()
        p["pit_mode"] = []
        p["feedback"] = "bad"
        p["global_observations"] = [{"scope": [], "lesson": "x" * 40}]
        p["lesson_audit"] = [_audit(predictor_label=[], review=[], action=[],
                                     evidence_refs=[{}, [], 42])]
        p["primary_driver"]["evidence_refs"] = [{}]
        # The validator must NOT raise; should produce many errors.
        errs = _validate_must_return(p, "kitchen-sink")
        self.assertGreater(len(errs), 5,
                           "kitchen-sink should produce multiple error strings")


if __name__ == "__main__":
    unittest.main(verbosity=2)
