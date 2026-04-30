#!/usr/bin/env python3
"""Targeted tests for §1.1 — `_render_results_and_expectations` Consensus Bar.

Covers est-vs-actual-vs-surprise rendering when the just-reported row exists,
2-column estimate-only rendering when actuals are absent, and the existing
[NO DATA] / [BUILDER ERROR] paths.

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_results -v
    venv/bin/python -m pytest scripts/earnings/test_render_results.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_results_and_expectations, _render_reference


def _bundle(*, current_row: dict | None = None,
            other_rows: list[dict] | None = None,
            ex991: str | None = "Press release stub",
            consensus_present: bool = True,
            builder_errors: dict | None = None,
            gaps: list | None = None,
            items: list | None = None) -> dict:
    rows = []
    if current_row is not None:
        rows.append({**current_row, "is_current_quarter": True})
    rows.extend(other_rows or [])
    consensus = None
    if consensus_present:
        consensus = {
            "schema_version": "consensus.v1",
            "ticker": "AVGO",
            "quarterly_rows": rows,
            "forward_estimates": [],
            "summary": {},
            "gaps": gaps or [],
        }
    packet = None
    if ex991 is not None or items is not None:
        packet = {
            "exhibits_99": [{"exhibit_number": "EX-99.1", "content": ex991}] if ex991 else [],
            "items": items or [],
        }
    return {
        "ticker": "AVGO",
        "consensus": consensus,
        "8k_packet": packet,
        "builder_errors": builder_errors or {},
    }


class ConsensusBarTests(unittest.TestCase):
    def test_full_beat_renders_4col_table_with_signed_surprise(self):
        # Historical full beat (AVGO Q4 FY2023 shape).
        text = _render_results_and_expectations(_bundle(current_row={
            "fiscalDateEnding": "2023-10-31",
            "estimatedEPS": 1.098,
            "reportedEPS": 1.106,
            "epsSurprisePct": 0.7286,
            "revenueEstimate": None,
            "revenueActual": 9295000000.0,
            "revenueSurprisePct": None,
        }))
        self.assertIn("### Consensus Bar", text)
        self.assertIn("| Metric  | Estimate | Actual | Surprise |", text)
        self.assertIn("$1.098", text)
        self.assertIn("$1.106", text)
        self.assertIn("+0.7%", text)
        # _fmt_money scales >=1e9 to .2f B; binary float rounding is locked here.
        self.assertIn("$9.29B", text)

    def test_revenue_surprise_renders_when_estimate_present(self):
        text = _render_results_and_expectations(_bundle(current_row={
            "estimatedEPS": 1.098,
            "reportedEPS": 1.106,
            "epsSurprisePct": 0.7286,
            "revenueEstimate": 8862740000.0,
            "revenueActual": 8876000000.0,
            "revenueSurprisePct": 0.15,
        }))
        self.assertIn("$8.86B", text)
        self.assertIn("$8.88B", text)
        self.assertIn("+0.1%", text)   # 0.15 rounded to 1dp = 0.1%

    def test_negative_surprise_renders_with_minus_sign(self):
        text = _render_results_and_expectations(_bundle(current_row={
            "estimatedEPS": 1.098,
            "reportedEPS": 1.030,
            "epsSurprisePct": -6.2,
            "revenueEstimate": 8862740000.0,
            "revenueActual": 8728000000.0,
            "revenueSurprisePct": -1.4,
        }))
        self.assertIn("-6.2%", text)
        self.assertIn("-1.4%", text)

    def test_estimate_only_renders_2col_when_no_actuals(self):
        # Pre-actuals — current row exists but reportedEPS / revenueActual absent.
        text = _render_results_and_expectations(_bundle(current_row={
            "estimatedEPS": 1.098,
            "reportedEPS": None,
            "epsSurprisePct": None,
            "revenueEstimate": 8862740000.0,
            "revenueActual": None,
            "revenueSurprisePct": None,
        }))
        self.assertIn("| Metric  | Estimate |", text)
        self.assertNotIn("| Metric  | Estimate | Actual | Surprise |", text)
        self.assertIn("$1.098", text)
        self.assertIn("$8.86B", text)

    def test_no_consensus_emits_no_data(self):
        text = _render_results_and_expectations(_bundle(consensus_present=False))
        self.assertIn("### Consensus Bar\n[NO DATA]", text)

    def test_builder_error_passes_through(self):
        text = _render_results_and_expectations(_bundle(
            consensus_present=False,
            builder_errors={"consensus": "AV rate-limited"},
        ))
        self.assertIn("[BUILDER ERROR: AV rate-limited]", text)

    # ── U3: disambiguate the three empty-Consensus-Bar failure modes ──

    def test_u3_upstream_error_distinct_message(self):
        """AV upstream failure → distinct stub mentioning the failure reason."""
        text = _render_results_and_expectations(_bundle(
            current_row=None, other_rows=[], consensus_present=True,
            gaps=[
                {"type": "upstream_error", "reason": "AV EARNINGS failed for AVGO"},
                {"type": "upstream_error", "reason": "AV EARNINGS_ESTIMATES failed for AVGO"},
            ],
        ))
        self.assertIn("Consensus unavailable", text)
        self.assertIn("AV upstream failed", text)
        self.assertIn("AV EARNINGS failed for AVGO", text)
        self.assertIn("AV EARNINGS_ESTIMATES failed for AVGO", text)
        self.assertNotIn("[No current-quarter row found]", text)
        self.assertNotIn("[No quarterly data]", text)

    def test_u3_empty_rows_no_upstream_says_no_quarterly_data(self):
        """consensus exists but rows empty AND no upstream_error → '[No quarterly data]'."""
        text = _render_results_and_expectations(_bundle(
            current_row=None, other_rows=[], consensus_present=True, gaps=[],
        ))
        self.assertIn("[No quarterly data]", text)
        self.assertNotIn("[No current-quarter row found]", text)
        self.assertNotIn("Consensus unavailable", text)

    def test_u3_rows_present_no_match_keeps_aci_class_stub(self):
        """rows present but none flagged is_current_quarter → genuine ACI-class
        fallback keeps the existing '[No current-quarter row found]' message."""
        text = _render_results_and_expectations(_bundle(
            current_row=None,
            other_rows=[{"fiscalDateEnding": "2023-10-31", "estimatedEPS": 1.098,
                         "reportedEPS": 1.106, "is_current_quarter": False}],
            consensus_present=True, gaps=[],
        ))
        self.assertIn("[No current-quarter row found]", text)
        self.assertNotIn("[No quarterly data]", text)
        self.assertNotIn("Consensus unavailable", text)

    # ── U6: "Other items in this 8-K" line in §1.1 ────────────────────

    def test_u6_avgo_style_non_routine_items_render(self):
        """AVGO Q4 FY2023 carries Item 2.02 + 2.05 + 8.01 + 9.01.
        Renderer should surface 2.05 and 8.01 in §1.1 between Consensus Bar
        and Reported Results, with the verbatim labels after the colon."""
        text = _render_results_and_expectations(_bundle(
            current_row={"estimatedEPS": 1.098, "reportedEPS": 1.106,
                         "epsSurprisePct": 0.7286},
            items=[
                "Item 2.02: Results of Operations and Financial Condition",
                "Item 2.05: Cost Associated with Exit or Disposal Activities",
                "Item 8.01: Other Events",
                "Item 9.01: Financial Statements and Exhibits",
            ],
        ))
        self.assertIn("Other items in this 8-K:", text)
        self.assertIn("Item 2.05 (Cost Associated with Exit or Disposal Activities)", text)
        self.assertIn("Item 8.01 (Other Events)", text)
        # Routine items (2.02 + 9.01) must NOT appear in the Other-items line.
        otheritems_idx = text.index("Other items in this 8-K:")
        line_end = text.index("\n", otheritems_idx) if "\n" in text[otheritems_idx:] else len(text)
        line = text[otheritems_idx:line_end]
        self.assertNotIn("Item 2.02", line)
        self.assertNotIn("Item 9.01", line)
        # Line must sit BEFORE Reported Results.
        self.assertLess(text.index("Other items in this 8-K:"),
                        text.index("### Reported Results"))

    def test_u6_clean_filing_omits_line_entirely(self):
        """Item 2.02 + 9.01 only (clean earnings) → no Other-items line."""
        text = _render_results_and_expectations(_bundle(
            current_row={"estimatedEPS": 1.098, "reportedEPS": 1.106},
            items=[
                "Item 2.02: Results of Operations and Financial Condition",
                "Item 9.01: Financial Statements and Exhibits",
            ],
        ))
        self.assertNotIn("Other items in this 8-K", text)

    def test_u6_missing_items_omits_line(self):
        """packet without items key → line absent, no crash."""
        text = _render_results_and_expectations(_bundle(
            current_row={"estimatedEPS": 1.098, "reportedEPS": 1.106},
            items=None,
        ))
        self.assertNotIn("Other items in this 8-K", text)

    def test_u6_item_without_colon_renders_bare(self):
        """Item with no descriptive label after colon renders as just 'Item N.NN'."""
        text = _render_results_and_expectations(_bundle(
            current_row={"estimatedEPS": 1.098, "reportedEPS": 1.106},
            items=["Item 2.02", "Item 5.02"],
        ))
        self.assertIn("Other items in this 8-K:", text)
        self.assertIn("Item 5.02", text)


# ── U36: Filing Metadata extra fields in §1.8 ──────────────────────────

def _ref_bundle(*, cik=None, is_amendment=False, accession_periodic=None,
                form_type_periodic=None, items=None):
    return {
        "ticker": "AVGO",
        "quarter_info": {
            "accession_8k": "0001730168-23-000093",
            "filed_8k": "2023-12-07T16:18:51-05:00",
            "period_of_report": "2023-10-29",
            "accession_periodic": accession_periodic,
            "form_type_periodic": form_type_periodic,
        },
        "8k_packet": {
            "accession_8k": "0001730168-23-000093",
            "form_type": "8-K",
            "items": items or ["Item 2.02: Results of Operations and Financial Condition"],
            "cik": cik,
            "is_amendment": is_amendment,
            "content_inventory": {"section_names": ["Stub"], "exhibit_numbers": ["EX-99.1"]},
            "exhibits_99": [{"exhibit_number": "EX-99.1", "content": "stub"}],
            "exhibits_other": [],
            "sections": [],
            "filing_text": None,
        },
        "builder_errors": {},
    }


class ReferenceMetadataTests(unittest.TestCase):
    def test_u36_avgo_full_metadata_renders(self):
        """All four U36 fields surface in Filing Metadata block."""
        text = _render_reference(_ref_bundle(
            cik="0001730168",
            is_amendment=False,
            accession_periodic="0001730168-23-000096",
            form_type_periodic="10-K",
        ))
        self.assertIn("CIK: 0001730168", text)
        self.assertIn("Periodic: 0001730168-23-000096 (10-K)", text)
        self.assertIn("Amendment: no", text)

    def test_u36_amendment_yes_renders(self):
        """is_amendment=True → 'Amendment: yes'."""
        text = _render_reference(_ref_bundle(
            cik="0001730168", is_amendment=True,
            accession_periodic="0001730168-23-000096",
            form_type_periodic="10-K/A",
        ))
        self.assertIn("Amendment: yes", text)
        self.assertIn("Periodic: 0001730168-23-000096 (10-K/A)", text)

    def test_u36_missing_fields_render_dash(self):
        """Missing optional fields render '—' instead of crashing or showing 'None'."""
        text = _render_reference(_ref_bundle(
            cik=None, is_amendment=False,
            accession_periodic=None, form_type_periodic=None,
        ))
        self.assertIn("CIK: —", text)
        self.assertIn("Periodic: —", text)
        # is_amendment=False is still rendered as 'no' (not '—')
        self.assertIn("Amendment: no", text)


if __name__ == "__main__":
    unittest.main()
