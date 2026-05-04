#!/usr/bin/env python3
"""LearnerLoopRevamp.md §12 (N4) — full closed-loop round-trip smoke.

True audit-loop coverage requires three quarters because fresh-start has
no priors at Q3:

  Q3: predict (lesson_labels=[] — no priors) → learn (writes new lessons)
  Q4: predict (sees Q3's lessons in bundle, labels them) → learn (audits
      Q3's lessons → aggregator writes audit_history)
  Q5: predict (sees Q3's lessons WITH non-empty audit_history; review
      counts render correctly)

Running three SDK calls is expensive and slow for a smoke test. This file
takes the alternative path documented in §12: synthesize seed lessons +
seed audits directly into the library to compress the loop into a single
quarter. The synthesis exercises the same code paths as the live flow —
``aggregate_lesson_audits`` + ``build_learning_context`` + renderer — and
verifies the post-loop bundle reflects the audit_history correctly.

Pinned invariants:

  * After audit aggregation, parent's audit_history grows by exactly 1
    per (auditor_ticker, auditor_quarter_label) — upsert idempotent.
  * The next quarter's bundle, built via build_learning_context, exposes
    transient ``_render_status`` + ``_render_audit_counts`` on the parent
    lesson (PIT-filtered).
  * The renderer's marker line for the parent lesson includes the
    ``[reviews: ...]`` summary tag with the synthesized audit's review.
  * D20: ``ordered_lesson_texts`` from the renderer contains body-only
    strings — no decoration.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

import earnings_orchestrator as orch
from earnings_orchestrator import (
    aggregate_lesson_audits,
    build_learning_context,
    compute_lesson_id,
    compute_status,
)


def _v3_lesson(body, **overrides):
    base = {
        "lesson_id":     compute_lesson_id(body, "ticker", "AVGO"),
        "lesson":        body,
        "mechanism":     "the causal mechanism " * 2,
        "applies_when":  "applies when conditions hold " * 2,
        "invalid_if":    "invalid if these break " * 2,
        "evidence_refs": ["E1"],
        "scope":         "ticker",
        "routing_key":   "AVGO",
        "audit_history": [],
        "parent_id":     None,
    }
    base.update(overrides)
    return base


def _q_row(quarter_label, predictor_lessons, *,
            attributed_at="2024-01-01T00:00:00+00:00"):
    return {
        "quarter_label":              quarter_label,
        "attributed_at":              attributed_at,
        "source_filed_8k":            "2024-01-01T00:00:00+00:00",
        "source_pit_cutoff":          "2024-01-01T00:00:00+00:00",
        "direction_correct":          True,
        "actual_daily_pct":           1.5,
        "predicted_direction":        "long",
        "predicted_confidence_score": 60,
        "primary_driver_summary":     "summary",
        "primary_driver_category":    "category",
        "what_worked":                [],
        "what_failed":                [],
        "predictor_lessons":          predictor_lessons,
        "data_lessons":               [],
        "why":                        "demo",
    }


def _make_attribution(ticker, quarter_label, lesson_audit, *,
                        pit_cutoff=None,
                        filed_8k="2024-04-01T00:00:00+00:00"):
    return {
        "ticker":         ticker.upper(),
        "quarter_label":  quarter_label,
        "filed_8k":       filed_8k,
        "pit_cutoff":     pit_cutoff,
        "attributed_at":  "2024-05-01T00:00:00+00:00",
        "actual_return":  {"daily_stock_pct": 2.5},
        "primary_driver": {"summary": "auditor", "category": "auditor"},
        "feedback":       {
            "prediction_comparison":  {"direction_correct": True},
            "what_worked": [], "what_failed": [],
            "predictor_lessons":      [],
            "data_lessons":           [],
            "why":                    "audit run",
        },
        "lesson_audit":   lesson_audit,
    }


class FullLoopRoundTripSmokeTests(unittest.TestCase):
    """Compressed loop: seed Q1 with a v3 lesson, audit it from Q2,
    rebuild Q3 bundle, verify rendered output reflects the audit."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.companies_dir = self.tmp / "Companies"
        self.companies_dir.mkdir()
        self.learnings_dir = self.tmp / "learnings"
        self.learnings_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _write_ticker(self, ticker, q_rows):
        ticker_dir = self.learnings_dir / "ticker"
        ticker_dir.mkdir(parents=True, exist_ok=True)
        (ticker_dir / f"{ticker.upper()}.json").write_text(json.dumps({
            "schema_version": "ticker_lessons.v2",
            "ticker": ticker.upper(),
            "updated_at": "2024-04-01T00:00:00+00:00",
            "lessons": q_rows,
        }, indent=2), encoding="utf-8")

    def test_q1_seed_q2_audit_q3_renders_with_review_count(self):
        ticker = "AVGO"
        body = "the prior quarter mechanism for AVGO Q1"

        # ── Step 1: seed Q1 with a v3 lesson ──
        q1_lesson = _v3_lesson(body)
        self._write_ticker(ticker, [_q_row("Q1_FY2024", [q1_lesson])])

        # Sanity: pre-audit, status is "active" with no audits.
        self.assertEqual(compute_status(q1_lesson), "active")

        # ── Step 2: from Q2's perspective, audit Q1's lesson as 'helped' ──
        audit_payload = _make_attribution(
            ticker, "Q2_FY2024",
            lesson_audit=[{
                "lesson_index":   0,
                "lesson_text":    body,
                "predictor_label": "confirmed",
                "was_cited":      True,
                "review":         "helped",
                "action":         "keep",
                "comment":        "outcome aligned",
                "evidence_refs":  ["E1"],
            }],
            pit_cutoff="2024-04-01T00:00:00+00:00",
        )
        prediction_payload = {
            "lesson_labels":  [{"label": "confirmed"}],
            "key_drivers":    [{"cites_lesson_indices": [0]}],
        }
        bundle = {
            "learning_context": {
                "ticker_lessons": [{
                    "quarter_label": "Q1_FY2024",
                    "predictor_lessons": [q1_lesson],
                }],
                "global_lessons": [],
            }
        }
        aggregate_lesson_audits(
            learning_payload=audit_payload,
            prediction_payload=prediction_payload,
            bundle=bundle,
            auditor_ticker=ticker,
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )

        # ── Step 3: verify ticker.json now has audit_history populated ──
        data = json.loads(
            (self.learnings_dir / "ticker" / f"{ticker}.json").read_text()
        )
        q1_row = [r for r in data["lessons"] if r["quarter_label"] == "Q1_FY2024"][0]
        parent = q1_row["predictor_lessons"][0]
        self.assertEqual(len(parent["audit_history"]), 1)
        self.assertEqual(parent["audit_history"][0]["review"], "helped")
        self.assertEqual(parent["audit_history"][0]["auditor_quarter_label"],
                          "Q2_FY2024")

        # ── Step 4: build Q3's learning context and verify the parent
        # lesson now carries _render_status + _render_audit_counts ──
        ctx = build_learning_context(
            ticker, base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q3_FY2024",   # NOT Q1; Q1 is the parent
            pit_cutoff=None,                      # live mode
        )
        self.assertEqual(len(ctx["ticker_lessons"]), 1)
        rendered_q1 = ctx["ticker_lessons"][0]["predictor_lessons"][0]
        self.assertEqual(rendered_q1["_render_status"], "active")
        self.assertEqual(rendered_q1["_render_audit_counts"], {"helped": 1})

        # ── Step 5: render the bundle and check the marker carries the
        # [reviews: 1 helped] tag and ordered_lesson_texts is body-only ──
        from renderer.lessons import _render_learning_context
        text, ordered = _render_learning_context(ctx)
        self.assertIn("[status: active]", text)
        self.assertIn("[reviews: 1 helped]", text)
        self.assertIn(f"Lesson: {body}", text)
        # D20 — body only, no decoration
        self.assertEqual(ordered, [body])

    def test_q1_seed_q2_misled_audit_renders_caution_on_q3_watch(self):
        # Push the lesson into watch by emitting 2 misled audits (threshold).
        ticker = "AVGO"
        body = "lesson destined for watch"

        q1_lesson = _v3_lesson(body)
        self._write_ticker(ticker, [_q_row("Q1_FY2024", [q1_lesson])])

        # Two separate auditor quarters emit misled audits.
        for q in ("Q2_FY2024", "Q3_FY2024"):
            audit_payload = _make_attribution(
                ticker, q,
                lesson_audit=[{
                    "lesson_index":   0,
                    "lesson_text":    body,
                    "predictor_label": "confirmed",
                    "was_cited":      True,
                    "review":         "misled",
                    "action":         "keep",
                    "comment":        "mechanism not present",
                    "evidence_refs":  ["E1"],
                }],
                pit_cutoff="2024-04-01T00:00:00+00:00",
            )
            prediction_payload = {
                "lesson_labels":  [{"label": "confirmed"}],
                "key_drivers":    [{"cites_lesson_indices": [0]}],
            }
            bundle = {
                "learning_context": {
                    "ticker_lessons": [{
                        "quarter_label": "Q1_FY2024",
                        "predictor_lessons": [q1_lesson],
                    }],
                    "global_lessons": [],
                }
            }
            aggregate_lesson_audits(
                learning_payload=audit_payload,
                prediction_payload=prediction_payload,
                bundle=bundle,
                auditor_ticker=ticker,
                auditor_quarter_label=q,
                audit_pit_cutoff="2024-04-01T00:00:00+00:00",
                learnings_dir=self.learnings_dir,
            )

        # Build a future bundle (Q4) and verify watch + CAUTION
        ctx = build_learning_context(
            ticker, base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q4_FY2024",
            pit_cutoff=None,
        )
        rendered = ctx["ticker_lessons"][0]["predictor_lessons"][0]
        self.assertEqual(rendered["_render_status"], "watch")
        self.assertEqual(rendered["_render_audit_counts"], {"misled": 2})

        from renderer.lessons import _render_learning_context
        text, ordered = _render_learning_context(ctx)
        self.assertIn("[status: watch]", text)
        self.assertIn("[reviews: 2 misled]", text)
        self.assertIn("[CAUTION", text)
        # CAUTION precedes the Lesson: line
        self.assertLess(text.index("[CAUTION"), text.index(f"Lesson: {body}"))
        # D20 still holds
        self.assertEqual(ordered, [body])

    def test_q1_seed_three_misled_drops_lesson_in_q2_bundle(self):
        # 3 misled → status=retired → lesson dropped from next bundle.
        ticker = "AVGO"
        body = "lesson destined for retirement"
        q1_lesson = _v3_lesson(body)
        self._write_ticker(ticker, [_q_row("Q1_FY2024", [q1_lesson])])

        for q in ("Q2_FY2024", "Q3_FY2024", "Q4_FY2024"):
            audit_payload = _make_attribution(
                ticker, q,
                lesson_audit=[{
                    "lesson_index":   0,
                    "lesson_text":    body,
                    "predictor_label": "confirmed",
                    "was_cited":      True,
                    "review":         "misled",
                    "action":         "keep",
                    "comment":        "mechanism not present",
                    "evidence_refs":  ["E1"],
                }],
                pit_cutoff="2024-04-01T00:00:00+00:00",
            )
            prediction_payload = {
                "lesson_labels":  [{"label": "confirmed"}],
                "key_drivers":    [{"cites_lesson_indices": [0]}],
            }
            bundle = {
                "learning_context": {
                    "ticker_lessons": [{
                        "quarter_label": "Q1_FY2024",
                        "predictor_lessons": [q1_lesson],
                    }],
                    "global_lessons": [],
                }
            }
            aggregate_lesson_audits(
                learning_payload=audit_payload,
                prediction_payload=prediction_payload,
                bundle=bundle,
                auditor_ticker=ticker,
                auditor_quarter_label=q,
                audit_pit_cutoff="2024-04-01T00:00:00+00:00",
                learnings_dir=self.learnings_dir,
            )

        # Q5's bundle should drop the retired Q1 lesson row entirely
        # (commit 2.1: rows whose predictor_lessons go empty after retire-
        # filter are dropped before the cap).
        ctx = build_learning_context(
            ticker, base_dir=self.learnings_dir,
            companies_dir=self.companies_dir,
            current_quarter_label="Q5_FY2024",
            pit_cutoff=None,
        )
        self.assertEqual(ctx["ticker_lessons"], [],
                          "retired-only quarter row must be dropped from bundle")


if __name__ == "__main__":
    unittest.main(verbosity=2)
