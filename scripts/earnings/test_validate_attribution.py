#!/usr/bin/env python3
"""V1–V20 validator tests for attribution_result.v2 schema.

Enforces the structured-routing + scope_key-removal contract from
.claude/plans/learner-edits.md §6.1.
"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root (for config.*)
sys.path.insert(0, str(Path(__file__).resolve().parent))       # this dir (for validate_attribution)

from validate_attribution import validate_attribution_result


# Minimal-valid attribution skeleton — every required top-level field present
# and schema-correct except global_observations, which tests will manipulate.
def _skeleton(global_observations=None):
    return {
        "schema_version": "attribution_result.v2",
        "ticker": "AAPL",
        "quarter_label": "Q1_FY2025",
        "filed_8k": "2025-05-01T16:30:00-04:00",
        "accession_8k": "0000320193-25-000055",
        "attributed_at": "2026-04-17T12:00:00-04:00",
        "model_version": "claude-opus-4-7",
        "pit_mode": "historical",
        "pit_cutoff": "2025-07-31T16:00:00-04:00",
        "pit_boundary_source": "next_quarter",
        "actual_return": {"daily_stock_pct": -5.28, "market_session": "after_hours"},
        "evidence_ledger": [
            {"id": "E1", "claim": "demo", "value": "x", "source": "test", "date": "2025-05-01"}
        ],
        "primary_driver": {
            "summary": "demo",
            "category": "guidance_change",
            "evidence_refs": ["E1"],
        },
        "contributing_factors": [],
        "feedback": {
            "prediction_comparison": {
                "predicted_direction": "long",
                "predicted_confidence_score": 50,
                "predicted_move_range_pct": [1.0, 3.0],
                "predicted_key_drivers": ["demo"],
                "actual_direction": "short",
                "direction_correct": False,
                "magnitude_error_pct": 6.28,
                "comment": "demo",
            },
            "what_worked": [],
            "what_failed": [],
            "why": "demo",
            "predictor_lessons": [],
            "data_lessons": [],
        },
        "global_observations": global_observations if global_observations is not None else [],
        "missing_inputs": [],
        "data_sources_used": ["test"],
        "context_bundle_ref": "prediction/context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
    }


def _validate(payload):
    return validate_attribution_result(payload, "AAPL", "Q1_FY2025")


class ValidatorTests(unittest.TestCase):
    """V1–V20 per .claude/plans/learner-edits.md §7.1."""

    # ── V1: Full valid attribution, zero global_observations ──
    def test_V1_valid_no_globals(self):
        self.assertEqual(_validate(_skeleton([])), [])

    # ── V2: Valid cross_ticker ──
    def test_V2_cross_ticker_valid(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": ["ROST"], "lesson": "x"}
        ]))
        self.assertEqual(errors, [], f"expected no errors, got {errors}")

    # ── V3: cross_ticker with empty related_tickers list ──
    def test_V3_cross_ticker_empty_list(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": [], "lesson": "x"}
        ]))
        self.assertTrue(any("related_tickers" in e and "non-empty" in e for e in errors), errors)

    # ── V4: cross_ticker missing related_tickers ──
    def test_V4_cross_ticker_missing_rt(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "lesson": "x"}
        ]))
        self.assertTrue(any("related_tickers" in e for e in errors), errors)

    # ── V5: cross_ticker with lowercase tickers ──
    def test_V5_cross_ticker_lowercase(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": ["rost"], "lesson": "x"}
        ]))
        self.assertTrue(any("invalid tickers" in e for e in errors), errors)

    # ── V6: cross_ticker with too-long ticker ──
    def test_V6_cross_ticker_toolong(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": ["TOOLONG"], "lesson": "x"}
        ]))
        self.assertTrue(any("invalid tickers" in e for e in errors), errors)

    # ── V7: cross_ticker with duplicates (also V20) ──
    def test_V7_cross_ticker_duplicates(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": ["ROST", "ROST"], "lesson": "x"}
        ]))
        self.assertTrue(any("duplicates" in e for e in errors), errors)

    # ── V8: cross_ticker exceeds 8-ticker cap ──
    def test_V8_cross_ticker_cap(self):
        nine = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": nine, "lesson": "x"}
        ]))
        self.assertTrue(any("exceeds cap" in e for e in errors), errors)

    # ── V9: cross_ticker with target_sector present (must be rejected) ──
    def test_V9_cross_ticker_has_target_sector(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": ["ROST"],
             "target_sector": "Technology", "lesson": "x"}
        ]))
        self.assertTrue(any("target_sector must not be present" in e and "cross_ticker" in e for e in errors), errors)

    # ── V10: sector with valid target_sector ──
    def test_V10_sector_valid(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "target_sector": "Technology", "lesson": "x"}
        ]))
        self.assertEqual(errors, [], f"expected no errors, got {errors}")

    # ── V11: sector with non-canonical target_sector ──
    def test_V11_sector_noncanonical(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "target_sector": "semiconductors", "lesson": "x"}
        ]))
        self.assertTrue(any("target_sector must be one of" in e for e in errors), errors)

    # ── V12: sector missing target_sector ──
    def test_V12_sector_missing_target(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "lesson": "x"}
        ]))
        self.assertTrue(any("target_sector must be one of" in e for e in errors), errors)

    # ── V13: sector with related_tickers present (must be rejected) ──
    def test_V13_sector_has_related_tickers(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "target_sector": "Technology",
             "related_tickers": ["AAPL"], "lesson": "x"}
        ]))
        self.assertTrue(any("related_tickers must not be present" in e and "sector" in e for e in errors), errors)

    # ── V14: macro with neither routing field ──
    def test_V14_macro_valid(self):
        errors = _validate(_skeleton([
            {"scope": "macro", "lesson": "x"}
        ]))
        self.assertEqual(errors, [], f"expected no errors, got {errors}")

    # ── V15: macro with related_tickers ──
    def test_V15_macro_has_related_tickers(self):
        errors = _validate(_skeleton([
            {"scope": "macro", "related_tickers": ["AAPL"], "lesson": "x"}
        ]))
        self.assertTrue(any("related_tickers must not be present" in e and "macro" in e for e in errors), errors)

    # ── V16: macro with target_sector ──
    def test_V16_macro_has_target_sector(self):
        errors = _validate(_skeleton([
            {"scope": "macro", "target_sector": "Technology", "lesson": "x"}
        ]))
        self.assertTrue(any("target_sector must not be present" in e and "macro" in e for e in errors), errors)

    # ── V17: Existing top-level missing-field rule still fires ──
    def test_V17_existing_rules_still_fire(self):
        bad = _skeleton([])
        del bad["evidence_ledger"]
        errors = _validate(bad)
        self.assertTrue(any("evidence_ledger" in e for e in errors), errors)

    # ── V18: Unknown scope value ──
    def test_V18_unknown_scope(self):
        errors = _validate(_skeleton([
            {"scope": "foo", "lesson": "x"}
        ]))
        self.assertTrue(any(".scope invalid" in e for e in errors), errors)

    # ── V19: scope_key rejected across ALL scopes (new invariant) ──
    def test_V19_scope_key_rejected_on_cross_ticker(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": ["ROST"],
             "scope_key": "anything", "lesson": "x"}
        ]))
        self.assertTrue(any("scope_key has been removed" in e for e in errors), errors)

    def test_V19_scope_key_rejected_on_sector(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "target_sector": "Technology",
             "scope_key": "anything", "lesson": "x"}
        ]))
        self.assertTrue(any("scope_key has been removed" in e for e in errors), errors)

    def test_V19_scope_key_rejected_on_macro(self):
        errors = _validate(_skeleton([
            {"scope": "macro", "scope_key": "anything", "lesson": "x"}
        ]))
        self.assertTrue(any("scope_key has been removed" in e for e in errors), errors)

    # ── V20 is covered by V7 (validator is dedupe authority) ──

    # ── V21–V24: null-injection MUST be rejected (regression from contract hole) ──
    # Amendment 2026-04-17 — the contract says forbidden fields "MUST NOT be
    # present". Prior implementation used `is not None` which silently permitted
    # explicit-null injections. Fix uses key-presence (`in obs`) to match
    # the scope_key rejection pattern and close the hole.
    def test_V21_macro_null_related_tickers_rejected(self):
        errors = _validate(_skeleton([
            {"scope": "macro", "related_tickers": None, "lesson": "x"},
        ]))
        self.assertTrue(
            any("related_tickers must not be present" in e and "macro" in e for e in errors),
            errors,
        )

    def test_V22_macro_null_target_sector_rejected(self):
        errors = _validate(_skeleton([
            {"scope": "macro", "target_sector": None, "lesson": "x"},
        ]))
        self.assertTrue(
            any("target_sector must not be present" in e and "macro" in e for e in errors),
            errors,
        )

    def test_V23_sector_null_related_tickers_rejected(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "related_tickers": None,
             "target_sector": "Technology", "lesson": "x"},
        ]))
        self.assertTrue(
            any("related_tickers must not be present" in e and "sector" in e for e in errors),
            errors,
        )

    def test_V24_cross_ticker_null_target_sector_rejected(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "target_sector": None,
             "related_tickers": ["MSFT"], "lesson": "x"},
        ]))
        self.assertTrue(
            any("target_sector must not be present" in e and "cross_ticker" in e for e in errors),
            errors,
        )

    # ── Bonus: string-instead-of-list emits "did you mean" hint ──
    def test_did_you_mean_for_string_rt(self):
        errors = _validate(_skeleton([
            {"scope": "cross_ticker", "related_tickers": "ROST_BURL", "lesson": "x"}
        ]))
        # Must reject AND suggest the list form
        self.assertTrue(any("non-empty" in e for e in errors), errors)
        self.assertTrue(any("did you mean" in e and "ROST" in e and "BURL" in e for e in errors), errors)

    # ── Bonus: did-you-mean hint for near-miss target_sector ──
    def test_did_you_mean_for_near_miss_target_sector(self):
        errors = _validate(_skeleton([
            {"scope": "sector", "target_sector": "Technolgy", "lesson": "x"}  # typo
        ]))
        self.assertTrue(any("did you mean" in e and "Technology" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
