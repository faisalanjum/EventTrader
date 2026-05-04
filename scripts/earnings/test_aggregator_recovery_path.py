#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.2 (D18) — recovery path runs the aggregator.

Recovery (orchestrator:1142-1167) used to re-run only the appends:
  append_ticker_lesson + append_global_lessons → return RECOVERED

D18 fix: the aggregator MUST run in BOTH success AND recovery paths so
audit_history stays up-to-date for the next quarter's bundle, even when
a prior run failed AFTER writing learning/result.json but BEFORE the
audit aggregator landed. Recovery semantics:

  * If sibling files (prediction/result.json, context_bundle.json) are
    missing → return FAILED_RECOVERY_APPEND (do NOT silently skip).
  * If cross-file validation (D19) fails → return FAILED_RECOVERY_APPEND
    (recovery aborts — no H2 retry path because the SDK never re-runs
    in recovery).
  * Otherwise: aggregator runs, library audit_history updated, return RECOVERED.

These tests pin that contract by asserting library state matches what
the success-path aggregator would have produced.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

import earnings_orchestrator as orch
from earnings_orchestrator import (
    LearnerOutcome,
    aggregate_lesson_audits,
    compute_lesson_id,
    run_learner_for_quarter,
)


def _v3_lesson_dict(body, **kw):
    base = {
        "lesson_id":     compute_lesson_id(body, "ticker", "AVGO"),
        "lesson":        body,
        "mechanism":     "the mechanism " * 3,
        "applies_when":  "applies when " * 3,
        "invalid_if":    "invalid if " * 3,
        "evidence_refs": ["E1"],
        "scope":         "ticker",
        "routing_key":   "AVGO",
        "audit_history": [],
        "parent_id":     None,
    }
    base.update(kw)
    return base


def _write_ticker_lib(learnings_dir: Path, ticker: str,
                      quarters: list[tuple[str, list[dict]]]) -> Path:
    ticker_dir = learnings_dir / "ticker"
    ticker_dir.mkdir(parents=True, exist_ok=True)
    p = ticker_dir / f"{ticker.upper()}.json"
    p.write_text(json.dumps({
        "schema_version": "ticker_lessons.v2",
        "ticker": ticker.upper(),
        "updated_at": "2024-01-01T00:00:00+00:00",
        "lessons": [
            {
                "quarter_label":              ql,
                "attributed_at":              "2024-01-01T00:00:00+00:00",
                "source_filed_8k":            "2024-01-01T00:00:00+00:00",
                "source_pit_cutoff":          "2024-01-01T00:00:00+00:00",
                "predictor_lessons":          lessons,
            }
            for ql, lessons in quarters
        ],
    }, indent=2), encoding="utf-8")
    return p


def _make_v3_attribution(ticker, quarter_label, *, lesson_audit, pit_cutoff,
                           filed_8k="2024-04-01T16:00:00-04:00"):
    """Minimal valid attribution_result.v3 payload."""
    return {
        "schema_version": "attribution_result.v3",
        "ticker":         ticker.upper(),
        "quarter_label":  quarter_label,
        "filed_8k":       filed_8k,
        "accession_8k":   "0000123456-24-000001",
        "attributed_at":  "2024-05-01T12:00:00-04:00",
        "model_version":  "claude-opus-4-7",
        "pit_mode":       "historical",
        "pit_cutoff":     pit_cutoff,
        "pit_boundary_source": "next_quarter",
        "actual_return":  {"daily_stock_pct": 1.5, "market_session": "after_hours"},
        "evidence_ledger": [
            {"id": "E1", "claim": "demo", "value": "x", "source": "test", "date": "2024-04-01"}
        ],
        "primary_driver": {"summary": "demo summary", "category": "guidance",
                            "evidence_refs": ["E1"]},
        "contributing_factors": [],
        "feedback": {
            "prediction_comparison": {
                "predicted_direction": "long",
                "predicted_confidence_score": 50,
                "predicted_move_range_pct": [1.0, 3.0],
                "predicted_key_drivers": ["d"],
                "actual_direction": "long",
                "direction_correct": True,
                "magnitude_error_pct": 0.5,
                "comment": "demo",
            },
            "what_worked": [], "what_failed": [], "why": "demo",
            "predictor_lessons": [],
            "data_lessons": [],
        },
        "global_observations": [],
        "missing_inputs": [],
        "data_sources_used": ["test"],
        "context_bundle_ref": "context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
        "lesson_audit": lesson_audit,
    }


class RecoveryPathAggregatorTests(unittest.TestCase):
    """Compare library state after success-path aggregator vs recovery-path
    aggregator — D18 says they must produce identical results."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.companies_dir = self.tmp / "Companies"
        self.companies_dir.mkdir()
        self.learnings_dir = self.tmp / "learnings"
        self.learnings_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _make_event_files(self, ticker, quarter_label, *,
                            attribution_payload, prediction_payload, bundle):
        """Stage the per-event files the recovery path expects."""
        event_dir = (self.companies_dir / ticker.upper() / "events" / quarter_label)
        learning_dir = event_dir / "learning"
        prediction_dir = event_dir / "prediction"
        learning_dir.mkdir(parents=True, exist_ok=True)
        prediction_dir.mkdir(parents=True, exist_ok=True)
        (learning_dir / "result.json").write_text(
            json.dumps(attribution_payload, indent=2), encoding="utf-8",
        )
        (prediction_dir / "result.json").write_text(
            json.dumps(prediction_payload, indent=2), encoding="utf-8",
        )
        (event_dir / "context_bundle.json").write_text(
            json.dumps(bundle, indent=2), encoding="utf-8",
        )
        return event_dir

    def test_recovery_runs_aggregator_when_sibling_files_present(self):
        """E5 + D18: a re-run with existing learning/result.json must
        produce the same audit_history as a fresh success run would."""
        ticker = "AVGO"
        body = "the prior quarter lesson"
        prior_lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, ticker,
                          [("Q1_FY2024", [prior_lesson])])

        # Auditor's quarter — Q2 — emitted lesson_audit on Q1's lesson.
        auditor_quarter = "Q2_FY2024"
        attribution = _make_v3_attribution(
            ticker, auditor_quarter,
            lesson_audit=[{
                "lesson_index":   0,
                "lesson_text":    body,
                "predictor_label": "confirmed",
                "was_cited":      True,
                "review":         "helped",
                "action":         "keep",
                "comment":        "evidence aligned",
                "evidence_refs":  ["E1"],
            }],
            pit_cutoff="2024-04-01T16:00:00-04:00",
        )
        prediction = {
            "lesson_labels":  [{"label": "confirmed"}],
            "key_drivers":    [{"cites_lesson_indices": [0]}],
        }
        bundle = {
            "learning_context": {
                "ticker_lessons": [{
                    "quarter_label": "Q1_FY2024",
                    "predictor_lessons": [prior_lesson],
                }],
                "global_lessons": [],
            }
        }
        self._make_event_files(
            ticker, auditor_quarter,
            attribution_payload=attribution,
            prediction_payload=prediction,
            bundle=bundle,
        )

        # Patch the orchestrator's LEARNINGS_DIR + COMPANIES_DIR (used
        # internally by run_learner_for_quarter via attr_paths).
        with mock.patch.object(orch, "LEARNINGS_DIR", self.learnings_dir), \
             mock.patch.object(orch, "COMPANIES_DIR", self.companies_dir):
            payload, outcome = run_learner_for_quarter(
                events=[], current_index=0,
                ticker=ticker,
                quarter_info={"quarter_label": auditor_quarter,
                               "accession_8k": attribution["accession_8k"]},
                pit_mode="historical",
                live_state_path=None,
            )

        self.assertEqual(outcome, LearnerOutcome.RECOVERED, f"got {outcome}")
        # Library state: the parent's audit_history must have grown.
        ticker_path = self.learnings_dir / "ticker" / f"{ticker}.json"
        data = json.loads(ticker_path.read_text())
        # Find the Q1 row (parent's row) — note that recovery runs
        # append_ticker_lesson(existing) which UPSERTS by quarter_label,
        # so Q2's auditor row is also created (with empty predictor_lessons).
        q1_rows = [r for r in data["lessons"] if r["quarter_label"] == "Q1_FY2024"]
        self.assertEqual(len(q1_rows), 1)
        parent_lesson = q1_rows[0]["predictor_lessons"][0]
        self.assertEqual(len(parent_lesson["audit_history"]), 1,
                         "recovery aggregator did not update audit_history")
        self.assertEqual(parent_lesson["audit_history"][0]["auditor_ticker"], ticker)
        self.assertEqual(parent_lesson["audit_history"][0]["auditor_quarter_label"],
                          auditor_quarter)

    def test_recovery_aborts_when_sibling_files_missing(self):
        """D18 + plan §7.2 round-9: missing prediction/result.json or
        context_bundle.json → return FAILED_RECOVERY_APPEND. Do NOT
        silently skip the aggregator."""
        ticker = "AVGO"
        body = "lesson"
        prior_lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, ticker,
                          [("Q1_FY2024", [prior_lesson])])

        auditor_quarter = "Q2_FY2024"
        attribution = _make_v3_attribution(
            ticker, auditor_quarter,
            lesson_audit=[{
                "lesson_index":   0,
                "lesson_text":    body,
                "predictor_label": "confirmed",
                "was_cited":      True,
                "review":         "helped",
                "action":         "keep",
                "comment":        "demo",
                "evidence_refs":  ["E1"],
            }],
            pit_cutoff="2024-04-01T16:00:00-04:00",
        )
        # Stage learning/result.json AND prediction/result.json (so hard
        # gate 1 passes), but DELIBERATELY OMIT context_bundle.json so the
        # recovery path's sibling-existence check fires.
        event_dir = (self.companies_dir / ticker / "events" / auditor_quarter)
        learning_dir = event_dir / "learning"
        prediction_dir = event_dir / "prediction"
        learning_dir.mkdir(parents=True, exist_ok=True)
        prediction_dir.mkdir(parents=True, exist_ok=True)
        (learning_dir / "result.json").write_text(
            json.dumps(attribution, indent=2), encoding="utf-8",
        )
        # Minimal prediction payload — passes hard gate 1; recovery's D19
        # check is what we want to exercise.
        (prediction_dir / "result.json").write_text(json.dumps({
            "lesson_labels":  [{"label": "confirmed"}],
            "key_drivers":    [{"cites_lesson_indices": [0]}],
        }), encoding="utf-8")
        # NB: context_bundle.json intentionally missing.

        with mock.patch.object(orch, "LEARNINGS_DIR", self.learnings_dir), \
             mock.patch.object(orch, "COMPANIES_DIR", self.companies_dir):
            payload, outcome = run_learner_for_quarter(
                events=[], current_index=0,
                ticker=ticker,
                quarter_info={"quarter_label": auditor_quarter,
                               "accession_8k": attribution["accession_8k"]},
                pit_mode="historical",
                live_state_path=None,
            )

        self.assertEqual(outcome, LearnerOutcome.FAILED_RECOVERY_APPEND)


if __name__ == "__main__":
    unittest.main(verbosity=2)
