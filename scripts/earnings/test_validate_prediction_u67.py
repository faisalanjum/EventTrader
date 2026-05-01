"""U67 — event-scoped source_id grounding (Tier M+/C).

The validator gains an optional `expected_source_ids` kwarg. When supplied
(production path), each `evidence_ledger[i].source_id` MUST be present in
the bundle's evidence_source_catalog. When None (offline/legacy callers),
the check is skipped — backward-compatible.

Run:
    venv/bin/python -m pytest scripts/earnings/test_validate_prediction_u67.py -q
"""
from __future__ import annotations

import json
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


# ── Fixture-based aggregator coverage (regression guard for the schema-path
#    correctness issue ChatGPT caught: the first-shipped aggregator walked
#    inter_quarter_context.news_events / macro_snapshot.macro_catalysts /
#    guidance_history.quarterly — none of which exist in real bundles). ──

class FixtureAnchorsCoverageTests(unittest.TestCase):
    """Real-bundle anchors must include news, filing, macro, and guidance refs.

    AVGO Q4 FY2023 fixture contains 73 inter-quarter events (69 news + 4
    filings), 30 guidance series entries, and macro catalysts buckets. If
    the aggregator regresses to non-existent paths, none of these will land
    in the catalog and U67 protection becomes a no-op for the most-cited
    bundle sections.
    """

    @classmethod
    def setUpClass(cls):
        import json
        cls.bundle = json.loads(
            (PROJECT_ROOT / "scripts/earnings/tests/fixtures/golden_bundles/AVGO_Q4_FY2023.json").read_text()
        )
        cls.catalog = build_evidence_source_catalog(cls.bundle)

    def test_catalog_contains_news_event_anchor(self):
        # Real AVGO Q4 fixture has news events; at least one must be in the catalog.
        news_anchors = [s for s in self.catalog if "#S6.event.news:" in s]
        self.assertGreater(
            len(news_anchors), 0,
            "no news anchors in catalog — aggregator missed inter_quarter_context.days[].events"
        )

    def test_catalog_contains_filing_event_anchor(self):
        filing_anchors = [s for s in self.catalog if "#S6.event.report:" in s]
        self.assertGreater(
            len(filing_anchors), 0,
            "no filing anchors — aggregator missed filing events under days[].events"
        )

    def test_catalog_contains_rendered_news_alias_N1(self):
        """The renderer (inter_quarter.py:147-150) labels news as N1, N2, ...
        in chronological render order. The catalog MUST emit matching
        #S6.news.N{i} aliases so a predictor that copies "N1" from the rendered
        text finds a match. Without this, the predictor's natural citation
        style ("News N1") fails validation."""
        n1 = next((s for s in self.catalog if s.endswith("#S6.news.N1")), None)
        self.assertIsNotNone(n1, "expected #S6.news.N1 alias in catalog")
        # Should also contain higher-indexed news refs (real fixture has 69)
        n_count = sum(1 for s in self.catalog if "#S6.news.N" in s)
        self.assertGreaterEqual(n_count, 5, f"only {n_count} N{{i}} aliases; expected dozens")

    def test_catalog_contains_rendered_filing_alias_F1(self):
        """The renderer (inter_quarter.py:182-185) labels filings as F1, F2, ...
        Catalog MUST emit matching #S6.filing.F{i} aliases."""
        f1 = next((s for s in self.catalog if s.endswith("#S6.filing.F1")), None)
        self.assertIsNotNone(f1, "expected #S6.filing.F1 alias in catalog")

    def test_catalog_contains_macro_earlier_bz_ids(self):
        """macro_snapshot.catalysts.earlier has shape [[date_str, headline_dict],...]
        — a list of pairs, NOT a list of headline dicts. The aggregator's
        _headline_list must extract item[1] from each pair to surface bz_ids;
        otherwise the renderer shows the headline but the catalog has no
        matching anchor and a predictor citing it fails validation.

        AVGO Q4 fixture has 3 known earlier bz_ids: 36090717, 36093426, 36093424."""
        for expected_bz in ("36090717", "36093426", "36093424"):
            anchor = f"#S8.macro.bz:{expected_bz}"
            found = any(anchor in s for s in self.catalog)
            self.assertTrue(
                found,
                f"earlier macro bz_id {expected_bz} missing from catalog — "
                f"_headline_list likely doesn't unpack [date, headline_dict] pairs"
            )

    def test_catalog_contains_guidance_series_anchor(self):
        guidance_anchors = [s for s in self.catalog if "#S3.guidance[" in s]
        self.assertGreater(
            len(guidance_anchors), 0,
            "no guidance anchors — aggregator missed guidance_history.series[]"
        )

    def test_catalog_contains_macro_anchor(self):
        macro_anchors = [s for s in self.catalog if "#S8.macro" in s]
        self.assertGreater(
            len(macro_anchors), 1,  # >1 — must include actual catalysts, not just the section catch-all
            "no per-headline macro anchors — aggregator missed macro_snapshot.catalysts"
        )

    def test_predict_failure_handler_quarantines_result_json(self):
        """Static guard: the predict-block exception handler MUST move
        result.json out of the canonical path before re-raising. Otherwise
        a rejected prediction stays on disk and a later learner-only run
        consumes it (the learner's prediction_result_path check is
        existence-only, not content-validation)."""
        src_path = PROJECT_ROOT / "scripts/earnings/earnings_orchestrator.py"
        src = src_path.read_text(encoding="utf-8")
        # Locate the predict-failure handler and confirm quarantine logic exists.
        # Look for the rejected-suffix rename pattern inside the except clause.
        self.assertIn(
            'paths["result_path"].with_suffix(".json.rejected")',
            src,
            "predict-failure handler is missing the U67 quarantine step "
            "— rejected result.json would persist for learner consumption"
        )
        self.assertIn(
            'paths["result_path"].rename(rejected)',
            src,
            "predict-failure handler does not rename result.json on quarantine"
        )

    def test_quarantine_is_gated_on_validation_success(self):
        """The quarantine MUST only fire on pre-validation failures. If
        a post-validation step (e.g. run_ledger _close_run write I/O) raises,
        the prediction is valid and result.json must be left untouched.
        Static guard: the except handler must check `prediction_validated`
        before quarantining."""
        src_path = PROJECT_ROOT / "scripts/earnings/earnings_orchestrator.py"
        src = src_path.read_text(encoding="utf-8")
        # The flag must be initialized False, set True after validate, and
        # the quarantine block must be wrapped in `if not prediction_validated`.
        self.assertIn("prediction_validated = False", src,
                      "quarantine flag not initialized")
        self.assertIn("prediction_validated = True", src,
                      "quarantine flag not set after validate_prediction_result")
        self.assertIn("if not prediction_validated:", src,
                      "quarantine block must be gated on prediction_validated")

    def test_catalog_lesson_anchors_match_render_order_count(self):
        """U45+U66 / U67 cross-consistency: the catalog's #S10.lesson.L# count
        MUST equal the render order count from _render_learning_context.
        Both call sites use iter_labeled_lessons; this test guards against
        drift if either is refactored independently."""
        from earnings_orchestrator import _render_learning_context
        _, ordered = _render_learning_context(self.bundle.get("learning_context") or {})
        catalog_l_count = sum(1 for s in self.catalog if "#S10.lesson.L" in s)
        self.assertEqual(
            catalog_l_count, len(ordered),
            f"catalog has {catalog_l_count} S10.lesson anchors, "
            f"renderer ordered has {len(ordered)} items — must match"
        )

    def test_catalog_size_reflects_real_density(self):
        # AVGO Q4: 73 events + 30 guidance + macro headlines + financials + peers + lessons
        # baseline ≈ 100+ anchors. If we still land at ~27, the schema-path bug regressed.
        self.assertGreater(
            len(self.catalog), 60,
            f"catalog has only {len(self.catalog)} anchors; expected 100+ for AVGO Q4 — "
            f"aggregator likely walking wrong paths"
        )

    def test_catalog_preserves_render_order_not_alphabetical(self):
        # If sorted, S10.lesson.L1 comes BEFORE S2.exhibit alphabetically.
        # Render order: header → S1 → S2 → ... → S10. Header should come first.
        self.assertTrue(
            self.catalog[0].endswith("#header"),
            f"first catalog entry is {self.catalog[0]!r}; expected header. "
            f"Likely sorted() snuck back in."
        )


class U22PeerCatalogRegression(unittest.TestCase):
    """U22+U22a regression: ensure peer anchors stay stable post-renderer-rewrite.

    The aggregator at earnings_orchestrator.py:538-543 emits one
    `#S7.peer.<TICKER>` anchor per peer. U22's renderer rewrite + U22a's
    schema additions must NOT alter catalog generation — only the rendered
    text shape changes.
    """

    @classmethod
    def setUpClass(cls):
        bundle_path = Path(__file__).parent / "tests/fixtures/golden_bundles/AVGO_Q4_FY2023.json"
        with open(bundle_path) as f:
            cls.bundle = json.load(f)
        cls.catalog = build_evidence_source_catalog(cls.bundle)
        cls.peer_anchors = [a for a in cls.catalog if "#S7.peer." in a]
        cls.peers = (cls.bundle.get("peer_earnings_snapshot") or {}).get("peers") or []

    def test_catalog_emits_one_anchor_per_peer_after_option_d_rewrite(self):
        """Anchor count = peer count. AVGO Q4 has 5 peers."""
        self.assertEqual(
            len(self.peer_anchors), len(self.peers),
            f"expected {len(self.peers)} peer anchors, got {len(self.peer_anchors)}"
        )

    def test_catalog_preserves_peer_iteration_order(self):
        """Catalog peer-anchor order matches builder peer-list order (mkt_cap desc).

        Renderer iterates same list order; alignment ensures predictor citations
        remain set-membership valid even if the predictor copies an anchor by
        relative position.
        """
        catalog_tickers = [a.split("#S7.peer.")[1] for a in self.peer_anchors]
        builder_tickers = [(p.get("ticker") or "").upper() for p in self.peers]
        self.assertEqual(catalog_tickers, builder_tickers,
                         "catalog peer-anchor order must match builder peer-list order")

    def test_catalog_has_no_per_headline_anchors_per_user_decision(self):
        """User decision (2026-05-01): keep #S7.peer.<TICKER> catch-all only;
        do NOT add finer #S7.peer.<TICKER>.headline.bz:<id> anchors yet."""
        per_headline_anchors = [a for a in self.catalog if ".headline.bz:" in a]
        self.assertEqual(
            len(per_headline_anchors), 0,
            f"expected zero per-headline anchors; got {len(per_headline_anchors)}"
        )


if __name__ == "__main__":
    unittest.main()
