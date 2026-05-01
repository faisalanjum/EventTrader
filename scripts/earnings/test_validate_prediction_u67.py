"""U67 — event-scoped source_id grounding (Tier M+/C).

The validator gains an optional `expected_source_ids` kwarg. When supplied
(production path), each `evidence_ledger[i].source_id` MUST be present in
the bundle's evidence_source_catalog. When None (offline/legacy callers),
the check is skipped — backward-compatible.

Run:
    venv/bin/python -m pytest scripts/earnings/test_validate_prediction_u67.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import (  # noqa: E402
    build_evidence_source_catalog,
    validate_prediction_result,
)


def _valid_payload(*, evidence_ledger=None, source_ids=None) -> dict:
    """Construct a structurally-valid prediction_result.v1 payload.

    Defaults to AVGO Q4 FY2023 with 1 evidence entry citing the canonical
    EX-99.1 anchor.
    """
    if evidence_ledger is None:
        sid = "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S2.exhibit.EX-99.1"
        evidence_ledger = [{
            "metric": "Q4 Revenue",
            "value": "$9,295M",
            "source": "EX-99.1",
            "source_id": sid,
        }]
    return {
        "schema_version": "prediction_result.v1",
        "ticker": "AVGO",
        "quarter_label": "Q4_FY2023",
        "direction": "long",
        "confidence_score": 65,
        "confidence_bucket": "moderate",
        "expected_move_range_pct": [1.0, 3.0],
        "magnitude_bucket": "medium",
        "key_drivers": [
            {"driver": "guidance beat", "direction": "long",
             "evidence": "Q1 FY2024 guide above consensus", "cites_lesson_indices": []}
        ],
        "data_gaps": [],
        "evidence_ledger": evidence_ledger,
        "analysis": "Beat with mixed guidance, expect modest upside.",
        "lesson_labels": [],
        "predicted_at": "2023-12-07T16:30:00-05:00",
        "model_version": "claude-test",
        "prompt_version": "u67-test",
    }


_AVGO_CATALOG = [
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#header",
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#quarter_info",
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S1.consensus",
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S2.8k_packet",
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S2.exhibit.EX-99.1",
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S6.news.N12",
    "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S7.peer.NVDA",
]


class ValidSourceIdPasses(unittest.TestCase):
    """Production path: every evidence entry's source_id is in the catalog."""

    def test_single_valid_entry_passes(self):
        validate_prediction_result(
            _valid_payload(),
            expected_ticker="AVGO",
            expected_quarter="Q4_FY2023",
            expected_source_ids=_AVGO_CATALOG,
        )

    def test_multiple_valid_entries_pass(self):
        validate_prediction_result(
            _valid_payload(evidence_ledger=[
                {"metric": "rev", "value": "x", "source": "y",
                 "source_id": "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S2.exhibit.EX-99.1"},
                {"metric": "peer", "value": "x", "source": "y",
                 "source_id": "SRC:AVGO:Q4_FY2023:0001730168-23-000093#S7.peer.NVDA"},
            ]),
            expected_ticker="AVGO",
            expected_quarter="Q4_FY2023",
            expected_source_ids=_AVGO_CATALOG,
        )


class MissingOrInvalidSourceIdFails(unittest.TestCase):
    """Production path: rejects missing, fake, generic, or wrong-event IDs."""

    def test_missing_source_id_field_rejected(self):
        with self.assertRaises(ValueError) as cm:
            validate_prediction_result(
                _valid_payload(evidence_ledger=[
                    {"metric": "rev", "value": "x", "source": "y"},  # no source_id
                ]),
                expected_ticker="AVGO",
                expected_quarter="Q4_FY2023",
                expected_source_ids=_AVGO_CATALOG,
            )
        self.assertIn("source_id is required", str(cm.exception))

    def test_empty_string_source_id_rejected(self):
        with self.assertRaises(ValueError) as cm:
            validate_prediction_result(
                _valid_payload(evidence_ledger=[
                    {"metric": "rev", "value": "x", "source": "y", "source_id": ""},
                ]),
                expected_ticker="AVGO",
                expected_quarter="Q4_FY2023",
                expected_source_ids=_AVGO_CATALOG,
            )
        self.assertIn("source_id is required", str(cm.exception))

    def test_generic_anchor_rejected(self):
        """Generic IDs like §2, N1, S2.exhibit.EX-99.1 (without event prefix)
        must be rejected — they collide across bundles, defeating race detection."""
        for fake in ("§2", "N1", "S2.exhibit.EX-99.1", "L1", "header"):
            with self.subTest(fake=fake):
                with self.assertRaises(ValueError) as cm:
                    validate_prediction_result(
                        _valid_payload(evidence_ledger=[
                            {"metric": "rev", "value": "x", "source": "y", "source_id": fake},
                        ]),
                        expected_ticker="AVGO",
                        expected_quarter="Q4_FY2023",
                        expected_source_ids=_AVGO_CATALOG,
                    )
                self.assertIn("not in the bundle's evidence_source_catalog", str(cm.exception))

    def test_aapl_prefixed_source_id_rejected_against_avgo_catalog(self):
        """The U65 race scenario: predictor consumed AAPL bundle, output AAPL
        IDs, but is being validated against AVGO's expected catalog."""
        with self.assertRaises(ValueError) as cm:
            validate_prediction_result(
                _valid_payload(evidence_ledger=[
                    {"metric": "iPhone Revenue", "value": "$69.7B", "source": "EX-99.1",
                     "source_id": "SRC:AAPL:Q3_FY2024:0000320193-24-000064#S2.exhibit.EX-99.1"},
                ]),
                expected_ticker="AVGO",
                expected_quarter="Q4_FY2023",
                expected_source_ids=_AVGO_CATALOG,
            )
        self.assertIn("not in the bundle's evidence_source_catalog", str(cm.exception))


class EmptyLedgerFailsInProductionPasses(unittest.TestCase):
    """Production validation rejects empty evidence_ledger; offline accepts it."""

    def test_empty_ledger_rejected_when_source_ids_supplied(self):
        with self.assertRaises(ValueError) as cm:
            validate_prediction_result(
                _valid_payload(evidence_ledger=[]),
                expected_ticker="AVGO",
                expected_quarter="Q4_FY2023",
                expected_source_ids=_AVGO_CATALOG,
            )
        self.assertIn("evidence_ledger must be non-empty", str(cm.exception))

    def test_empty_ledger_accepted_when_source_ids_none(self):
        # Offline/legacy validation does not enforce U67 grounding.
        validate_prediction_result(
            _valid_payload(evidence_ledger=[]),
            expected_ticker="AVGO",
            expected_quarter="Q4_FY2023",
            expected_source_ids=None,
        )


class LegacyCallerBackwardCompat(unittest.TestCase):
    """Old fixtures lack source_id; legacy validator path must keep passing them."""

    def test_legacy_payload_no_source_id_passes_offline(self):
        validate_prediction_result(
            _valid_payload(evidence_ledger=[
                {"metric": "rev", "value": "x", "source": "y"},  # no source_id (legacy)
            ]),
            expected_ticker="AVGO",
            expected_quarter="Q4_FY2023",
            expected_source_ids=None,
        )


class AggregatorTests(unittest.TestCase):
    """Aggregator generates event-scoped IDs, no overlap across bundles."""

    def test_avgo_q4_catalog_has_event_prefix(self):
        bundle = {
            "ticker": "AVGO",
            "quarter_info": {
                "ticker": "AVGO",
                "quarter_label": "Q4_FY2023",
                "accession_8k": "0001730168-23-000093",
            },
            "8k_packet": {"exhibits_99": [{"exhibit_number": "EX-99.1"}]},
        }
        catalog = build_evidence_source_catalog(bundle)
        for sid in catalog:
            self.assertTrue(
                sid.startswith("SRC:AVGO:Q4_FY2023:0001730168-23-000093#"),
                f"{sid!r} does not have the AVGO event prefix",
            )

    def test_two_bundles_have_zero_overlap(self):
        avgo = {
            "ticker": "AVGO",
            "quarter_info": {"ticker": "AVGO", "quarter_label": "Q4_FY2023",
                             "accession_8k": "0001730168-23-000093"},
            "8k_packet": {"exhibits_99": [{"exhibit_number": "EX-99.1"}]},
        }
        aapl = {
            "ticker": "AAPL",
            "quarter_info": {"ticker": "AAPL", "quarter_label": "Q3_FY2024",
                             "accession_8k": "0000320193-24-000064"},
            "8k_packet": {"exhibits_99": [{"exhibit_number": "EX-99.1"}]},
        }
        a = set(build_evidence_source_catalog(avgo))
        b = set(build_evidence_source_catalog(aapl))
        # The whole point of event-scoping: NO ANCHOR is shared between bundles.
        self.assertEqual(a & b, set(),
                         "AVGO and AAPL catalogs must have zero overlap (event prefix invariant)")

    def test_minimal_bundle_still_emits_baseline_anchors(self):
        bundle = {
            "ticker": "X",
            "quarter_info": {"ticker": "X", "quarter_label": "Q1_FY2024",
                             "accession_8k": "0000111-24-000001"},
        }
        catalog = build_evidence_source_catalog(bundle)
        self.assertIn("SRC:X:Q1_FY2024:0000111-24-000001#header", catalog)
        self.assertIn("SRC:X:Q1_FY2024:0000111-24-000001#quarter_info", catalog)


if __name__ == "__main__":
    unittest.main()
