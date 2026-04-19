#!/usr/bin/env python3
"""V1-V24 tests for validate_prediction_result T1 lesson_labels contract.

Per .claude/plans/learner.md Appendix B §9.1:
  V1-V2: valid shapes (empty / populated with confirmed/contradicted/irrelevant)
  V3-V10: shape + enum + non-empty + sentinel discipline
  V11-V14: positional equality with expected_lesson_texts
  V15-V19: cites_lesson_indices: confirmed-only
  V20: expected_lesson_texts=None (audit mode)
  V21: sentinel regression fix (confirmed + "no relevant evidence" rejected)
  V22-V24: analysis-field substring floor

Run:
    venv/bin/python -m unittest scripts.earnings.test_validate_prediction_result -v
    venv/bin/python scripts/earnings/test_validate_prediction_result.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import validate_prediction_result


def _base_payload(**overrides):
    """Minimal valid prediction_result.v1 payload; tests tweak via overrides."""
    base = {
        "schema_version": "prediction_result.v1",
        "ticker": "AVGO",
        "quarter_label": "Q1_FY2023",
        "direction": "short",
        "confidence_score": 55,
        "confidence_bucket": "moderate",
        "expected_move_range_pct": [2.0, 5.0],
        "magnitude_bucket": "medium",
        "key_drivers": [
            {"driver": "d1", "direction": "short", "evidence": "e1", "cites_lesson_indices": []},
        ],
        "data_gaps": [],
        "evidence_ledger": [{"metric": "m", "value": "v", "source": "s"}],
        "analysis": "The main tension is bundle-derived; bundle evidence says short.",
        "lesson_labels": [],
        "predicted_at": "2026-04-19T12:00:00Z",
        "model_version": "claude-opus-4-7",
        "prompt_version": "abc123",
    }
    base.update(overrides)
    return base


class BasicShapeTests(unittest.TestCase):

    def test_V1_empty_labels_and_expected_passes(self):
        """lesson_labels=[] + expected=[] + every driver cites_lesson_indices=[] → passes."""
        payload = _base_payload()
        validate_prediction_result(
            payload, "AVGO", "Q1_FY2023", expected_lesson_texts=[],
        )  # no raise

    def test_V2_populated_valid_mixed_labels(self):
        """3 labels (one of each type); expected matches; drivers cite confirmed only."""
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": "First AI quant is a narrative re-rating signal",
                 "label": "irrelevant",
                 "bundle_evidence": "no relevant evidence"},
                {"lesson_text": "Thin beat plus pre-rally tends short",
                 "label": "confirmed",
                 "bundle_evidence": "5-day return +7.2%, revenue beat 0.4%"},
                {"lesson_text": "Semis with concentrated hyperscaler customers price in raises",
                 "label": "contradicted",
                 "bundle_evidence": "company flagged new non-hyperscaler customer wins"},
            ],
            key_drivers=[
                {"driver": "thin-beat-rally", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": [1]},
                {"driver": "bundle-only", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": []},
            ],
        )
        expected = [
            "First AI quant is a narrative re-rating signal",
            "Thin beat plus pre-rally tends short",
            "Semis with concentrated hyperscaler customers price in raises",
        ]
        validate_prediction_result(
            payload, "AVGO", "Q1_FY2023", expected_lesson_texts=expected,
        )  # no raise


class MissingNullTypeTests(unittest.TestCase):

    def test_V3_missing_lesson_labels(self):
        payload = _base_payload()
        del payload["lesson_labels"]
        with self.assertRaisesRegex(ValueError, r"lesson_labels"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V4_null_lesson_labels(self):
        payload = _base_payload(lesson_labels=None)
        with self.assertRaisesRegex(ValueError, r"(null|list)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V5_lesson_labels_is_string(self):
        payload = _base_payload(lesson_labels="not a list")
        with self.assertRaisesRegex(ValueError, r"list"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")


class EntryShapeEnumTests(unittest.TestCase):

    def test_V6_entry_missing_label(self):
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "x" * 50, "bundle_evidence": "cite"},
        ])
        with self.assertRaisesRegex(ValueError, r"label"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V7_invalid_enum(self):
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "x" * 50, "label": "maybe", "bundle_evidence": "cite"},
        ])
        with self.assertRaisesRegex(ValueError, r"(label|one of)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V8_wrong_case_CONFIRMED(self):
        """Strict lowercase enum — 'CONFIRMED' rejected."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "x" * 50, "label": "CONFIRMED", "bundle_evidence": "cite"},
        ])
        with self.assertRaisesRegex(ValueError, r"(label|one of)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V9_empty_lesson_text(self):
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "", "label": "irrelevant", "bundle_evidence": "cite"},
        ])
        with self.assertRaisesRegex(ValueError, r"lesson_text.*(non-empty|empty)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V10_empty_bundle_evidence(self):
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "x" * 50, "label": "irrelevant", "bundle_evidence": ""},
        ])
        with self.assertRaisesRegex(ValueError, r"bundle_evidence.*(non-empty|empty)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")


class PositionalTests(unittest.TestCase):

    def test_V11_length_short(self):
        """expected has 3, labels has 2 → rejected."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "lesson-one-and-then-some-filler-to-be-at-least-30-chars",
             "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
            {"lesson_text": "lesson-two-and-then-some-filler-to-be-at-least-30-chars",
             "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
        ])
        with self.assertRaisesRegex(ValueError, r"(entries|length|expected)"):
            validate_prediction_result(
                payload, "AVGO", "Q1_FY2023",
                expected_lesson_texts=[
                    "lesson-one-and-then-some-filler-to-be-at-least-30-chars",
                    "lesson-two-and-then-some-filler-to-be-at-least-30-chars",
                    "lesson-three-that-should-have-been-emitted-but-wasnt",
                ],
            )

    def test_V12_length_long_fabrication(self):
        """expected has 2, labels has 3 (fabricated extra) → rejected."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "a" * 50, "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
            {"lesson_text": "b" * 50, "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
            {"lesson_text": "c-fabricated-" * 5, "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
        ])
        with self.assertRaisesRegex(ValueError, r"(entries|length|expected)"):
            validate_prediction_result(
                payload, "AVGO", "Q1_FY2023",
                expected_lesson_texts=["a" * 50, "b" * 50],
            )

    def test_V13_content_mismatch_at_position(self):
        """Length matches but lesson_text differs → rejected."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "actually-different-text-at-position-zero",
             "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
        ])
        with self.assertRaisesRegex(ValueError, r"(match|position)"):
            validate_prediction_result(
                payload, "AVGO", "Q1_FY2023",
                expected_lesson_texts=["expected-text-that-is-very-different"],
            )

    def test_V14_whitespace_normalized_equal(self):
        """Trailing/interior whitespace + case diff → normalized equal → passes."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "  AI Revenue  Beat   Consensus   ",
             "label": "confirmed",
             "bundle_evidence": "actual cite from bundle"},
        ])
        validate_prediction_result(
            payload, "AVGO", "Q1_FY2023",
            expected_lesson_texts=["ai revenue beat consensus"],
        )  # no raise


class CitationTests(unittest.TestCase):

    def test_V15_missing_cites_lesson_indices(self):
        payload = _base_payload(
            key_drivers=[
                {"driver": "d", "direction": "short", "evidence": "e"},
            ],
        )
        with self.assertRaisesRegex(ValueError, r"cites_lesson_indices"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V16_cites_irrelevant(self):
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": "lesson A of sufficient length to pass all validations",
                 "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
            ],
            key_drivers=[
                {"driver": "bad", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": [0]},
            ],
        )
        with self.assertRaisesRegex(ValueError, r"confirmed"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V17_cites_contradicted(self):
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": "lesson B of sufficient length to pass all validations",
                 "label": "contradicted",
                 "bundle_evidence": "bundle shows opposite mechanism"},
            ],
            key_drivers=[
                {"driver": "bad", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": [0]},
            ],
        )
        with self.assertRaisesRegex(ValueError, r"confirmed"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V18_index_out_of_range(self):
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": "lesson C of sufficient length",
                 "label": "confirmed", "bundle_evidence": "cite"},
            ],
            key_drivers=[
                {"driver": "bad", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": [5]},
            ],
        )
        with self.assertRaisesRegex(ValueError, r"(range|out of)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V19_bool_as_int_rejected(self):
        """Python quirk: isinstance(True, int) is True. Explicit guard rejects bool."""
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": "lesson D of sufficient length",
                 "label": "confirmed", "bundle_evidence": "cite"},
            ],
            key_drivers=[
                {"driver": "bad", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": [True]},
            ],
        )
        with self.assertRaisesRegex(ValueError, r"(int|bool)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")


class AuditModeTests(unittest.TestCase):

    def test_V20_expected_lesson_texts_none_skips_positional(self):
        """expected=None → positional check skipped; shape/enum still fire."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "anything-but-long-enough",
             "label": "irrelevant", "bundle_evidence": "no relevant evidence"},
        ])
        validate_prediction_result(payload, "AVGO", "Q1_FY2023")  # no raise
        # But bad label still rejects:
        bad = _base_payload(lesson_labels=[
            {"lesson_text": "anything", "label": "maybe", "bundle_evidence": "cite"},
        ])
        with self.assertRaises(ValueError):
            validate_prediction_result(bad, "AVGO", "Q1_FY2023")


class SentinelDisciplineTests(unittest.TestCase):

    def test_V21_confirmed_with_sentinel_rejected(self):
        """Rev-1 regression fix: confirmed + 'no relevant evidence' → rejected."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "lesson with sufficient length to pass length check",
             "label": "confirmed",
             "bundle_evidence": "no relevant evidence"},
        ])
        with self.assertRaisesRegex(ValueError, r"(sentinel|reserved|specific)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V21b_contradicted_with_sentinel_rejected(self):
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "lesson with sufficient length to pass length check",
             "label": "contradicted",
             "bundle_evidence": "NO relevant EVIDENCE"},  # case-insensitive match
        ])
        with self.assertRaisesRegex(ValueError, r"(sentinel|reserved|specific)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V21c_irrelevant_with_sentinel_allowed(self):
        """irrelevant is the one scope where sentinel is valid."""
        payload = _base_payload(lesson_labels=[
            {"lesson_text": "lesson with sufficient length to pass length check",
             "label": "irrelevant",
             "bundle_evidence": "no relevant evidence"},
        ])
        validate_prediction_result(payload, "AVGO", "Q1_FY2023")  # no raise


class AnalysisFloorTests(unittest.TestCase):

    def test_V22_analysis_verbatim_irrelevant_rejected(self):
        """analysis contains verbatim lesson_text of an irrelevant label ≥30 chars → rejected."""
        lesson = "first AI quantification is a narrative re-rating signal for this issuer"
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": lesson, "label": "irrelevant",
                 "bundle_evidence": "no relevant evidence"},
            ],
            analysis=f"Bundle evidence points short; but also note {lesson} could be relevant here.",
        )
        with self.assertRaisesRegex(ValueError, r"(analysis|verbatim|quote)"):
            validate_prediction_result(payload, "AVGO", "Q1_FY2023")

    def test_V23_analysis_verbatim_confirmed_allowed(self):
        """confirmed label allowed to be cited in analysis (semantically fine)."""
        lesson = "thin beat plus pre-rally tends short on next session reaction"
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": lesson, "label": "confirmed",
                 "bundle_evidence": "5-day return +7.2%"},
            ],
            key_drivers=[
                {"driver": "thin-beat", "direction": "short", "evidence": "e",
                 "cites_lesson_indices": [0]},
            ],
            analysis=f"Given that {lesson} applies here, short is warranted.",
        )
        validate_prediction_result(payload, "AVGO", "Q1_FY2023")  # no raise

    def test_V24_paraphrase_passes_shortlesson_passes(self):
        """analysis paraphrases an irrelevant lesson — passes (substring floor only catches verbatim)."""
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": "first AI quantification drives narrative re-rating",
                 "label": "irrelevant",
                 "bundle_evidence": "no relevant evidence"},
            ],
            analysis="The AI disclosure theme is present but not first-of-kind here; different mechanism at play.",
        )
        validate_prediction_result(payload, "AVGO", "Q1_FY2023")  # no raise (paraphrase evades floor)

    def test_V24b_short_lesson_skips_substring_check(self):
        """Lesson <30 chars normalized → skipped per length guard (innocent-collision protection)."""
        short = "margin pressure continued"  # 25 chars normalized
        payload = _base_payload(
            lesson_labels=[
                {"lesson_text": short, "label": "irrelevant",
                 "bundle_evidence": "no relevant evidence"},
            ],
            analysis=f"The bundle shows {short} into Q1 — bundle-derived signal.",
        )
        # Short lessons: substring check is SKIPPED per §3 invariant 6
        # (innocent-collision risk on common short phrases)
        validate_prediction_result(payload, "AVGO", "Q1_FY2023")  # no raise


if __name__ == "__main__":
    unittest.main(verbosity=2)
