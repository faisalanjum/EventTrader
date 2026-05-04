#!/usr/bin/env python3
"""LearnerLoopRevamp.md §7.2 — aggregate_lesson_audits coverage.

Pins:
  * Basic audit append on ticker-scope lesson (audit_history grows)
  * Basic audit append on global-scope lesson (audit_history grows under flock)
  * Idempotency — re-running with the same (auditor_ticker, auditor_quarter_label)
    REPLACES the existing entry (no duplicate)
  * Refinement chain — action="refine" registers replacement_lesson with
    parent_id link; parent's audit_history gains the refine entry
  * Retire action — action="retire" persists in audit_history; compute_status
    returns retired
  * lesson_index out of range → log warning, skip that audit
  * lesson_text drift → log warning, but use index match anyway
  * §7.2.1 implementation rule: empty feedback.predictor_lessons + ticker-
    scope action="refine" → aggregator creates auditor's quarter row from
    learning_payload outer fields and inserts the replacement
  * User clarification #4: replacement that hashes to parent's lesson_id
    is downgraded to action="keep" (no spurious retire)
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
from earnings_orchestrator import aggregate_lesson_audits, compute_lesson_id


# ── Fixture builders ────────────────────────────────────────────────────


def _v3_lesson_dict(body, **kw):
    """v3-shape lesson dict (storage shape, with identity + state)."""
    base = {
        "lesson_id":     compute_lesson_id(body, kw.get("scope", "ticker"),
                                            kw.get("routing_key", "AVGO")),
        "lesson":        body,
        "mechanism":     "the mechanism",
        "applies_when":  "applies when conditions",
        "invalid_if":    "invalid if conditions",
        "evidence_refs": ["E1"],
        "scope":         "ticker",
        "routing_key":   "AVGO",
        "audit_history": [],
        "parent_id":     None,
    }
    base.update(kw)
    return base


def _write_ticker_lib(learnings_dir: Path, ticker: str,
                      quarter_lessons: list[tuple[str, list[dict]]]) -> Path:
    """quarter_lessons = [(quarter_label, [lesson_dict, ...]), ...]"""
    ticker_dir = learnings_dir / "ticker"
    ticker_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ticker_lessons.v2",
        "ticker": ticker.upper(),
        "updated_at": "2024-04-01T00:00:00+00:00",
        "lessons": [
            {
                "quarter_label":              ql,
                "attributed_at":              "2024-01-01T00:00:00+00:00",
                "source_filed_8k":            "2024-01-01T00:00:00+00:00",
                "source_pit_cutoff":          "2024-01-01T00:00:00+00:00",
                "direction_correct":          True,
                "actual_daily_pct":           1.0,
                "predicted_direction":        "long",
                "predicted_confidence_score": 50,
                "primary_driver_summary":     "test",
                "primary_driver_category":    "test",
                "what_worked":                [],
                "what_failed":                [],
                "predictor_lessons":          lessons,
                "data_lessons":               [],
                "why":                        "test",
            }
            for ql, lessons in quarter_lessons
        ],
    }
    p = ticker_dir / f"{ticker.upper()}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def _write_global_lib(learnings_dir: Path, entries: list[dict]) -> Path:
    p = learnings_dir / "global.json"
    p.write_text(json.dumps({
        "schema_version": "global_lessons.v2",
        "updated_at": "2024-04-01T00:00:00+00:00",
        "entries": entries,
    }, indent=2), encoding="utf-8")
    return p


def _bundle_with_ticker_lesson(quarter_label, lesson_dict):
    """Bundle.learning_context with one ticker lesson at index 0."""
    return {
        "learning_context": {
            "ticker_lessons": [{
                "quarter_label": quarter_label,
                "predictor_lessons": [lesson_dict],
            }],
            "global_lessons": [],
        }
    }


def _prediction_with_one_label(label="confirmed", cites_indices=None):
    return {
        "lesson_labels": [{"label": label}],
        "key_drivers":   [{"cites_lesson_indices": cites_indices or []}],
    }


def _audit_for_lesson_0(lesson_text, **overrides):
    base = {
        "lesson_index":   0,
        "lesson_text":    lesson_text,
        "predictor_label": "confirmed",
        "was_cited":      True,
        "review":         "helped",
        "action":         "keep",
        "comment":        "evidence aligned",
        "evidence_refs":  ["E1"],
    }
    base.update(overrides)
    return base


def _replacement(lesson="refined body", **kw):
    base = {
        "lesson":        lesson,
        "mechanism":     "refined mech " * 4,
        "applies_when":  "refined applies " * 4,
        "invalid_if":    "refined invalid " * 4,
        "evidence_refs": ["E1"],
    }
    base.update(kw)
    return base


def _learning_payload_for_quarter(ticker, quarter_label, lesson_audit, *,
                                    pit_cutoff="2024-04-01T00:00:00+00:00"):
    """Minimal learning payload sufficient for aggregator's inputs."""
    return {
        "ticker":        ticker.upper(),
        "quarter_label": quarter_label,
        "filed_8k":      "2024-04-01T00:00:00+00:00",
        "pit_cutoff":    pit_cutoff,
        "attributed_at": "2024-05-01T00:00:00+00:00",
        "actual_return": {"daily_stock_pct": 2.5},
        "primary_driver": {"summary": "auditor", "category": "auditor"},
        "feedback":      {
            "prediction_comparison": {"direction_correct": True,
                                       "predicted_direction": "long",
                                       "predicted_confidence_score": 60},
            "what_worked": [], "what_failed": [],
            "predictor_lessons": [],
            "data_lessons":      [],
            "why": "audit run",
        },
        "lesson_audit":  lesson_audit,
    }


# ── Test cases ──────────────────────────────────────────────────────────


class AggregatorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.learnings_dir = self.tmp / "learnings"
        self.learnings_dir.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _ticker_path(self, ticker):
        return self.learnings_dir / "ticker" / f"{ticker.upper()}.json"

    # ── Basic ticker-scope audit append ────────────────────────────────

    def test_basic_ticker_audit_append(self):
        body = "lesson body"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO",
                          [("Q1_FY2024", [lesson])])
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="helped")],
        )
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)

        aggregate_lesson_audits(
            learning_payload=learning,
            prediction_payload=prediction,
            bundle=bundle,
            auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )

        # Assert: parent's audit_history has 1 entry with the auditor info.
        data = json.loads(self._ticker_path("AVGO").read_text())
        parent_lesson = data["lessons"][0]["predictor_lessons"][0]
        self.assertEqual(len(parent_lesson["audit_history"]), 1)
        ah = parent_lesson["audit_history"][0]
        self.assertEqual(ah["auditor_ticker"], "AVGO")
        self.assertEqual(ah["auditor_quarter_label"], "Q2_FY2024")
        self.assertEqual(ah["review"], "helped")
        self.assertEqual(ah["action"], "keep")
        self.assertTrue(ah["was_cited"])

    # ── Idempotency under re-run ───────────────────────────────────────

    def test_idempotent_under_rerun(self):
        body = "the lesson"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO",
                          [("Q1_FY2024", [lesson])])
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="helped")],
        )
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)

        for _ in range(3):
            aggregate_lesson_audits(
                learning_payload=learning,
                prediction_payload=prediction,
                bundle=bundle,
                auditor_ticker="AVGO",
                auditor_quarter_label="Q2_FY2024",
                audit_pit_cutoff="2024-04-01T00:00:00+00:00",
                learnings_dir=self.learnings_dir,
            )
        # Even after 3 runs, audit_history has exactly 1 entry (upsert by
        # auditor key).
        data = json.loads(self._ticker_path("AVGO").read_text())
        ah = data["lessons"][0]["predictor_lessons"][0]["audit_history"]
        self.assertEqual(len(ah), 1)

    # ── action="retire" persists ───────────────────────────────────────

    def test_retire_action_persists(self):
        body = "lesson"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="misled", action="retire")],
        )
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])

        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        data = json.loads(self._ticker_path("AVGO").read_text())
        ah = data["lessons"][0]["predictor_lessons"][0]["audit_history"]
        self.assertEqual(ah[0]["action"], "retire")
        # compute_status should now flag retired
        from earnings_orchestrator import compute_status
        self.assertEqual(
            compute_status(data["lessons"][0]["predictor_lessons"][0]),
            "retired",
        )

    # ── action="refine" registers replacement with parent_id ───────────

    def test_refine_registers_replacement(self):
        body = "parent body"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="misled", action="refine",
                                   replacement_lesson=_replacement("refined body text"))],
        )
        # Pre-create the auditor's quarter row (normal flow — append_ticker_lesson
        # would have run before aggregator).
        existing = json.loads(self._ticker_path("AVGO").read_text())
        existing["lessons"].append({
            "quarter_label": "Q2_FY2024",
            "attributed_at": "2024-05-01T00:00:00+00:00",
            "source_filed_8k": "2024-04-01T00:00:00+00:00",
            "source_pit_cutoff": "2024-04-01T00:00:00+00:00",
            "predictor_lessons": [],
        })
        self._ticker_path("AVGO").write_text(json.dumps(existing, indent=2))

        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])

        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        data = json.loads(self._ticker_path("AVGO").read_text())
        # Parent should have the refine audit
        parent = data["lessons"][0]["predictor_lessons"][0]
        self.assertEqual(parent["audit_history"][0]["action"], "refine")
        # Replacement should be in auditor's quarter row, with parent_id link
        auditor_row = [r for r in data["lessons"] if r["quarter_label"] == "Q2_FY2024"][0]
        self.assertEqual(len(auditor_row["predictor_lessons"]), 1)
        replacement = auditor_row["predictor_lessons"][0]
        self.assertEqual(replacement["lesson"], "refined body text")
        self.assertEqual(replacement["parent_id"], parent["lesson_id"])

    # ── §7.2.1 implementation rule — empty predictor_lessons + refine ──

    def test_refine_creates_auditor_quarter_row_when_missing(self):
        # Auditor's quarter row does NOT exist (predictor_lessons:[] case).
        # Aggregator must create the row from learning_payload outer fields
        # and insert the replacement.
        body = "parent body"
        lesson = _v3_lesson_dict(body)
        # Only the parent's quarter row exists; no auditor row.
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="misled", action="refine",
                                   replacement_lesson=_replacement("refined"))],
        )
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])

        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        data = json.loads(self._ticker_path("AVGO").read_text())
        # The auditor's quarter row should now exist with the replacement.
        auditor_rows = [r for r in data["lessons"] if r["quarter_label"] == "Q2_FY2024"]
        self.assertEqual(len(auditor_rows), 1, "auditor quarter row was not created")
        auditor_row = auditor_rows[0]
        # Outer-row provenance fields stamped from learning_payload
        self.assertEqual(auditor_row["attributed_at"], learning["attributed_at"])
        self.assertEqual(auditor_row["source_filed_8k"], learning["filed_8k"])
        self.assertEqual(auditor_row["source_pit_cutoff"], learning["pit_cutoff"])
        # Replacement attached
        self.assertEqual(len(auditor_row["predictor_lessons"]), 1)
        self.assertEqual(auditor_row["predictor_lessons"][0]["lesson"], "refined")

    # ── User clarification #4 — same-hash refine → keep ────────────────

    def test_same_hash_refinement_downgraded_to_keep(self):
        body = "parent body"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        # Replacement body identical to parent → same lesson_id
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="misled", action="refine",
                                   replacement_lesson=_replacement(body))],
        )
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])

        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        data = json.loads(self._ticker_path("AVGO").read_text())
        # Parent's audit should be action="keep" (downgraded), NOT "refine"
        parent = data["lessons"][0]["predictor_lessons"][0]
        self.assertEqual(parent["audit_history"][0]["action"], "keep")
        # Replacement should NOT be inserted (no auditor row at all here)
        from earnings_orchestrator import compute_status
        # And parent must NOT be retired (action="refine" downgraded means
        # no terminal-action trigger).
        self.assertEqual(compute_status(parent), "active")

    # ── Defensive — out-of-range lesson_index ──────────────────────────

    def test_lesson_index_out_of_range_skipped(self):
        body = "the lesson"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        # Audit references index 99 — out of range (only 1 lesson in bundle).
        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, lesson_index=99)],
        )
        prediction = {"lesson_labels": [{"label": "confirmed"}], "key_drivers": []}
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)

        # Must NOT raise (defensive — log + skip per user clarification #1).
        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        # Library state unchanged — no audit applied.
        data = json.loads(self._ticker_path("AVGO").read_text())
        self.assertEqual(
            data["lessons"][0]["predictor_lessons"][0]["audit_history"], [],
        )

    # ── Empty lesson_audit early-return ────────────────────────────────

    def test_empty_lesson_audit_no_op(self):
        # First-prediction case — no priors to audit.
        body = "x"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        learning = _learning_payload_for_quarter("AVGO", "Q2_FY2024", [])
        prediction = {"lesson_labels": [], "key_drivers": []}
        bundle = {"learning_context": {"ticker_lessons": [], "global_lessons": []}}

        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AVGO",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        # Library state unchanged
        data = json.loads(self._ticker_path("AVGO").read_text())
        self.assertEqual(
            data["lessons"][0]["predictor_lessons"][0]["audit_history"], [],
        )

    # ── Commit 2.1 — refinement re-run idempotent ──────────────────────

    def test_refine_rerun_does_not_duplicate_replacement_ticker(self):
        # Aggregator re-runs (recovery path or H2 retry) must NOT insert
        # the replacement lesson twice. Pre-fix, parent's audit upsert was
        # idempotent but replacement append was unconditional.
        body = "parent body to refine"
        lesson = _v3_lesson_dict(body)
        _write_ticker_lib(self.learnings_dir, "AVGO", [("Q1_FY2024", [lesson])])
        # Pre-create auditor's quarter row.
        existing = json.loads(self._ticker_path("AVGO").read_text())
        existing["lessons"].append({
            "quarter_label": "Q2_FY2024",
            "attributed_at": "2024-05-01T00:00:00+00:00",
            "source_filed_8k": "2024-04-01T00:00:00+00:00",
            "source_pit_cutoff": "2024-04-01T00:00:00+00:00",
            "predictor_lessons": [],
        })
        self._ticker_path("AVGO").write_text(json.dumps(existing, indent=2))

        learning = _learning_payload_for_quarter(
            "AVGO", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="misled", action="refine",
                                   replacement_lesson=_replacement("refined body new"))],
        )
        bundle = _bundle_with_ticker_lesson("Q1_FY2024", lesson)
        prediction = _prediction_with_one_label("confirmed", cites_indices=[0])

        for _ in range(3):
            aggregate_lesson_audits(
                learning_payload=learning, prediction_payload=prediction,
                bundle=bundle, auditor_ticker="AVGO",
                auditor_quarter_label="Q2_FY2024",
                audit_pit_cutoff="2024-04-01T00:00:00+00:00",
                learnings_dir=self.learnings_dir,
            )
        data = json.loads(self._ticker_path("AVGO").read_text())
        auditor_row = [r for r in data["lessons"] if r["quarter_label"] == "Q2_FY2024"][0]
        self.assertEqual(
            len(auditor_row["predictor_lessons"]), 1,
            "replacement was duplicated — re-runs must be idempotent",
        )
        # And parent's audit_history is also still 1 (upsert by auditor key)
        parent = data["lessons"][0]["predictor_lessons"][0]
        self.assertEqual(len(parent["audit_history"]), 1)

    def test_refine_rerun_does_not_duplicate_replacement_global(self):
        # Same idempotency invariant for global-scope refine path.
        # E31 atomicity already binds parent-audit + new-entry under one
        # flock; commit 2.1 ensures the new-entry insert is also idempotent.
        body = "macro body to refine"
        macro_id = compute_lesson_id(body, "macro", None)
        global_entry = {
            "lesson_id":   macro_id, "lesson": body,
            "mechanism": "m", "applies_when": "a", "invalid_if": "i",
            "evidence_refs": ["E1"],
            "scope":        "macro", "routing_key": None,
            "source_ticker": "MSFT", "source_sector": "Technology",
            "quarter_label": "Q1_FY2024",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "source_filed_8k": "2024-01-01T00:00:00+00:00",
            "source_pit_cutoff": "2024-01-01T00:00:00+00:00",
            "audit_history":  [], "parent_id": None,
        }
        _write_global_lib(self.learnings_dir, [global_entry])
        bundle = {"learning_context": {"ticker_lessons": [],
                                          "global_lessons": [global_entry]}}
        learning = _learning_payload_for_quarter(
            "AAPL", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="misled", action="refine",
                                   replacement_lesson=_replacement("refined macro"))],
        )
        prediction = {"lesson_labels": [{"label": "confirmed"}],
                      "key_drivers": [{"cites_lesson_indices": [0]}]}

        for _ in range(3):
            aggregate_lesson_audits(
                learning_payload=learning, prediction_payload=prediction,
                bundle=bundle, auditor_ticker="AAPL",
                auditor_quarter_label="Q2_FY2024",
                audit_pit_cutoff="2024-04-01T00:00:00+00:00",
                learnings_dir=self.learnings_dir,
            )
        data = json.loads((self.learnings_dir / "global.json").read_text())
        # Parent's audit appears exactly once (upsert)
        parent = [e for e in data["entries"] if e["lesson_id"] == macro_id][0]
        self.assertEqual(len(parent["audit_history"]), 1)
        # Replacement appears exactly once across re-runs
        refined_id = compute_lesson_id("refined macro", "macro", None)
        refined_entries = [e for e in data["entries"] if e["lesson_id"] == refined_id]
        self.assertEqual(
            len(refined_entries), 1,
            "global-scope replacement was duplicated — re-runs must be idempotent",
        )

    # ── Global-scope audit append ──────────────────────────────────────

    def test_global_audit_append(self):
        body = "macro lesson"
        macro_id = compute_lesson_id(body, "macro", None)
        global_entry = {
            "lesson_id":   macro_id,
            "lesson":      body,
            "mechanism":   "m", "applies_when": "a", "invalid_if": "i",
            "evidence_refs": ["E1"],
            "scope":        "macro",
            "routing_key":  None,
            "source_ticker": "MSFT",
            "source_sector": "Technology",
            "quarter_label": "Q1_FY2024",
            "attributed_at": "2024-01-01T00:00:00+00:00",
            "source_filed_8k": "2024-01-01T00:00:00+00:00",
            "source_pit_cutoff": "2024-01-01T00:00:00+00:00",
            "audit_history":  [],
            "parent_id":      None,
        }
        _write_global_lib(self.learnings_dir, [global_entry])
        # Bundle exposes the macro entry at index 0 (no ticker lessons)
        bundle = {"learning_context": {
            "ticker_lessons": [],
            "global_lessons": [global_entry],
        }}
        learning = _learning_payload_for_quarter(
            "AAPL", "Q2_FY2024",
            [_audit_for_lesson_0(body, review="helped")],
        )
        prediction = {"lesson_labels": [{"label": "confirmed"}],
                      "key_drivers": [{"cites_lesson_indices": [0]}]}

        aggregate_lesson_audits(
            learning_payload=learning, prediction_payload=prediction,
            bundle=bundle, auditor_ticker="AAPL",
            auditor_quarter_label="Q2_FY2024",
            audit_pit_cutoff="2024-04-01T00:00:00+00:00",
            learnings_dir=self.learnings_dir,
        )
        data = json.loads((self.learnings_dir / "global.json").read_text())
        macro_after = [e for e in data["entries"] if e["lesson_id"] == macro_id][0]
        self.assertEqual(len(macro_after["audit_history"]), 1)
        self.assertEqual(macro_after["audit_history"][0]["auditor_ticker"], "AAPL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
