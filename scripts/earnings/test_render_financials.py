#!/usr/bin/env python3
"""U12 — Derivation notes footer in §5 Prior Financial Trends.

Renderer-only addition: per-quarter block listing derived_metrics[] entries
(method + input accessions) so predictor can distinguish exact-extract from
arithmetic-derived numbers. Source of truth: `quarters[].derived_metrics`,
NOT `quarters[]._provenance` (which contains entries for non-derived
metrics too — would produce noise).

Run:
    venv/bin/python -m unittest scripts.earnings.test_render_financials -v
    venv/bin/python -m pytest scripts/earnings/test_render_financials.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import _render_prior_financials


def _quarter(label, derived_metrics=None, provenance=None,
             revenue=None, cost_of_revenue=None):
    return {
        "fiscal_label": label,
        "fiscal_year": 2023, "fiscal_quarter": 3,
        "primary_source": "xbrl",
        "primary_form": "10-Q",
        "primary_accession": f"0001730168-23-{label}",
        "revenue": revenue,
        "cost_of_revenue": cost_of_revenue,
        "_provenance": provenance or {},
        "derived_metrics": derived_metrics or [],
    }


def _bundle(quarters):
    return {
        "prior_financials": {
            "schema_version": "prior_financials.v1",
            "ticker": "AVGO",
            "quarters": quarters,
            "summary": {"quarter_count": len(quarters),
                        "primary_source_breakdown": {"xbrl": len(quarters)}},
            "gaps": [],
        },
        "builder_errors": {},
    }


_AVGO_Q3_DERIVED = [
    {"metric": "operating_cash_flow", "method": "9m_ytd_minus_h1",
     "inputs": [
         {"accession": "0001730168-23-000077", "form": "10-Q", "source": "xbrl", "role": "9m_ytd"},
         {"accession": "0001730168-23-000064", "form": "10-Q", "source": "xbrl", "role": "h1_ytd"},
     ]},
    {"metric": "capital_expenditures", "method": "9m_ytd_minus_h1",
     "inputs": [
         {"accession": "0001730168-23-000077", "form": "10-Q", "source": "xbrl", "role": "9m_ytd"},
         {"accession": "0001730168-23-000064", "form": "10-Q", "source": "xbrl", "role": "h1_ytd"},
     ]},
]


class DerivationNotesTests(unittest.TestCase):
    def test_u12_avgo_q3_two_derived_metrics_render(self):
        """Both inputs render with role + accession + form."""
        text = _render_prior_financials(_bundle([
            _quarter("Q3_FY2023", derived_metrics=_AVGO_Q3_DERIVED, revenue=8.7e9),
        ]))
        self.assertIn("### Derivation notes", text)
        self.assertIn("**Q3_FY2023**", text)
        self.assertIn("operating_cash_flow", text)
        self.assertIn("9m_ytd_minus_h1", text)
        self.assertIn("9m_ytd from 0001730168-23-000077 (10-Q)", text)
        self.assertIn("h1_ytd from 0001730168-23-000064 (10-Q)", text)
        self.assertIn("capital_expenditures", text)

    def test_u12_multiple_quarters_each_get_own_block(self):
        """Q3 + Q2 with different methods → both quarters appear with their bullets."""
        q2_derived = [{"metric": "operating_cash_flow", "method": "h1_ytd_minus_q1",
                       "inputs": [
                           {"accession": "0001730168-23-000064", "form": "10-Q", "source": "xbrl", "role": "h1_ytd"},
                           {"accession": "0001730168-23-000050", "form": "10-Q", "source": "xbrl", "role": "q1"},
                       ]}]
        text = _render_prior_financials(_bundle([
            _quarter("Q3_FY2023", derived_metrics=_AVGO_Q3_DERIVED, revenue=8.7e9),
            _quarter("Q2_FY2023", derived_metrics=q2_derived, revenue=8.5e9),
        ]))
        self.assertIn("**Q3_FY2023**", text)
        self.assertIn("**Q2_FY2023**", text)
        self.assertIn("9m_ytd_minus_h1", text)
        self.assertIn("h1_ytd_minus_q1", text)

    def test_u12_no_derivations_anywhere_no_section(self):
        """All quarters with empty derived_metrics → entire section omitted."""
        text = _render_prior_financials(_bundle([
            _quarter("Q3_FY2023", derived_metrics=[], revenue=8.7e9),
            _quarter("Q2_FY2023", derived_metrics=[], revenue=8.5e9),
        ]))
        self.assertNotIn("### Derivation notes", text)
        # Sanity: rest of the section still renders.
        self.assertIn("Prior Financial Trends", text)

    def test_u12_mixed_quarters_only_derived_appear(self):
        """Q3 derived, Q2 not → Q2 NOT in derivation notes block."""
        text = _render_prior_financials(_bundle([
            _quarter("Q3_FY2023", derived_metrics=_AVGO_Q3_DERIVED, revenue=8.7e9),
            _quarter("Q2_FY2023", derived_metrics=[], revenue=8.5e9),
        ]))
        self.assertIn("### Derivation notes", text)
        self.assertIn("**Q3_FY2023**", text)
        # Q2 has no derivations → shouldn't appear inside the Derivation notes
        # section (it WILL appear elsewhere in the document as a column header)
        deriv_idx = text.index("### Derivation notes")
        deriv_section = text[deriv_idx:]
        # Stop at next section if any (Data notes line)
        end_marker = deriv_section.find("\nData notes:") if "\nData notes:" in deriv_section else len(deriv_section)
        deriv_section = deriv_section[:end_marker]
        self.assertNotIn("**Q2_FY2023**", deriv_section)

    def test_u12_missing_inputs_or_method_render_gracefully(self):
        """Malformed entries don't crash the renderer."""
        bad_derived = [
            {"metric": "weird_metric"},   # no method, no inputs
            {"metric": "another", "method": "some_method"},  # method but no inputs
        ]
        text = _render_prior_financials(_bundle([
            _quarter("Q3_FY2023", derived_metrics=bad_derived, revenue=8.7e9),
        ]))
        self.assertIn("### Derivation notes", text)
        self.assertIn("weird_metric", text)
        self.assertIn("another", text)

    def test_u12_provenance_populated_but_derived_metrics_empty_no_section(self):
        """Defensive regression: source of truth is `derived_metrics[]`, NOT
        `_provenance{}`. A quarter with rich `_provenance` entries (direct
        extracts marked `derived: False`) but empty `derived_metrics` must
        produce ZERO derivation notes."""
        # Realistic AVGO Q2 FY2023 shape: 17 _provenance keys, only 2 of which
        # are derived. With derived_metrics=[] the section should be omitted.
        provenance = {
            "revenue": {"derived": False, "source": "xbrl", "accession": "x"},
            "cost_of_revenue": {"derived": False, "source": "xbrl", "accession": "x"},
            "gross_profit": {"derived": False, "source": "xbrl", "accession": "x"},
        }
        text = _render_prior_financials(_bundle([
            _quarter("Q3_FY2023", derived_metrics=[], provenance=provenance, revenue=8.7e9),
        ]))
        self.assertNotIn("### Derivation notes", text)


if __name__ == "__main__":
    unittest.main()
