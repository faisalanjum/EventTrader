"""U64 — accession-masking tests for quarter_identity.resolve_quarter_info.

The Cypher CASE WHEN gate hides any matched periodic whose `q.created` is
strictly after `r.created` (the 8-K's filing time). Final returned
`accession_periodic` reflects the gated value; raw `matched_accession_periodic`
remains internal (used only for XBRL denylist + fiscal-label resolution).

Run:
    venv/bin/python -m pytest scripts/earnings/test_quarter_identity_u64.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

import quarter_identity as qi  # noqa: E402


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def single(self):
        return self._row


class _FakeSession:
    def __init__(self, row):
        self._row = row
        self.calls = []

    def run(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return _FakeResult(self._row)


def _row(**overrides):
    """AVGO Q4 FY2023 baseline. Override individual keys per test."""
    base = {
        "filed_8k": "2023-12-07T16:18:51-05:00",
        "market_session": "post_market",
        "prev_8k_ts": "2023-08-31T17:18:57-04:00",
        "period_of_report": "2023-10-29",          # 10-K's actual SEC period
        "form_type_periodic": "10-K",
        "accession_periodic": None,                # gated value (Cypher CASE WHEN)
        "matched_accession_periodic": "0001730168-23-000096",  # raw
        "xbrl_period": "FY",
        "xbrl_year": "2023",
        "fye_month": 10,
    }
    base.update(overrides)
    return base


class CypherShapeTests(unittest.TestCase):
    """Static guards against regression of the Cypher mask shape."""

    def test_query_has_case_when_pit_gate(self):
        self.assertIn(
            "WHEN q.created IS NOT NULL AND datetime(q.created) <= datetime(r.created)",
            qi._QUERY,
        )

    def test_query_returns_both_raw_and_gated_accession(self):
        # Raw matched accession (internal use).
        self.assertIn("q.accessionNo AS matched_accession_periodic", qi._QUERY)
        # Gated accession (predictor-visible).
        self.assertIn("END AS accession_periodic", qi._QUERY)

    def test_query_does_not_pit_filter_where_clause(self):
        # The WHERE clause must NOT add datetime(q.created) <= datetime(r.created)
        # — that would cause the resolver to fall through to a prior-quarter
        # periodic and shift period_of_report off the SEC date.
        where_block = qi._QUERY.split("OPTIONAL CALL (r, c) {", 1)[1].split("}", 1)[0]
        self.assertNotIn("AND datetime(q.created) <= datetime(r.created)", where_block)


class FutureFiledAccessionMaskingTests(unittest.TestCase):
    """AVGO Q4 FY2023 — the canonical leak case.

    8-K filed 2023-12-07. Matching 10-K filed 2023-12-14 (7 days post-PIT).
    Cypher's CASE WHEN gate hides the future accession; period and form
    type stay populated from the matched row, so labeling and U1 keep
    working.
    """

    def test_future_accession_is_hidden(self):
        # Cypher already gated `accession_periodic` to None (q.created > r.created).
        session = _FakeSession(_row(accession_periodic=None))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000093", session=session)
        self.assertEqual(out["accession_periodic"], "")

    def test_period_of_report_preserved_from_matched(self):
        session = _FakeSession(_row(accession_periodic=None))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000093", session=session)
        # Exact SEC date — must NOT shift to calendar 2023-10-31.
        self.assertEqual(out["period_of_report"], "2023-10-29")

    def test_form_type_periodic_preserved_from_matched(self):
        session = _FakeSession(_row(accession_periodic=None))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000093", session=session)
        self.assertEqual(out["form_type_periodic"], "10-K")

    def test_quarter_label_correct(self):
        session = _FakeSession(_row(accession_periodic=None))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000093", session=session)
        self.assertEqual(out["quarter_label"], "Q4_FY2023")

    def test_source_indicates_matched_periodic(self):
        session = _FakeSession(_row(accession_periodic=None))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000093", session=session)
        self.assertTrue(out["quarter_identity_source"].startswith("matched_periodic"))


class PitVisibleAccessionPreservedTests(unittest.TestCase):
    """When the matched periodic was filed BEFORE the 8-K, the gate lets
    its accession through. Used for legitimate same-quarter backfills."""

    def test_pit_visible_accession_passes_through(self):
        # 8-K filed Aug 31, matched Q3 10-Q filed Aug 30 → gate passes.
        session = _FakeSession(_row(
            filed_8k="2023-08-31T17:18:57-04:00",
            period_of_report="2023-07-30",
            form_type_periodic="10-Q",
            accession_periodic="0001730168-23-000077",       # gate passed
            matched_accession_periodic="0001730168-23-000077",
            xbrl_period="Q3",
            xbrl_year="2023",
        ))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000074", session=session)
        self.assertEqual(out["accession_periodic"], "0001730168-23-000077")
        self.assertEqual(out["period_of_report"], "2023-07-30")
        self.assertEqual(out["form_type_periodic"], "10-Q")


class StaleMatchedRowDoesNotLeakTests(unittest.TestCase):
    """If gap_days > 150, matched row is rejected as stale; resolver falls
    through to fiscal_math. The stale row's accession must NOT leak into
    the final returned value."""

    def test_stale_match_drops_to_fiscal_math_with_empty_accession(self):
        # 8-K filed Dec 2024, matched periodic from Jan 2024 → ~330 days stale.
        session = _FakeSession(_row(
            filed_8k="2024-12-07T16:18:51-05:00",
            period_of_report="2024-01-15",                  # ~330 days before filed_8k
            form_type_periodic="10-Q",
            accession_periodic="OLD-ACCESSION-123",
            matched_accession_periodic="OLD-ACCESSION-123",
            xbrl_period="Q1",
            xbrl_year="2024",
        ))
        out = qi.resolve_quarter_info("AVGO", "any-acc", session=session)
        self.assertEqual(out["accession_periodic"], "")
        self.assertEqual(out["quarter_identity_source"], "fiscal_math")


class FallbackFormTypeFromEventQuarterTests(unittest.TestCase):
    """When falling through to fiscal_math, form_type_periodic must be
    derived from event_q (Q4 → 10-K, else 10-Q) so consensus.py's U1
    `_provider_fde_for_period` keeps producing the AV-convention FDE."""

    def test_fiscal_math_fallback_q4_yields_10k(self):
        # No matched periodic at all (e.g. fresh IPO, no prior periodic in DB).
        session = _FakeSession(_row(
            period_of_report=None,
            form_type_periodic=None,
            accession_periodic=None,
            matched_accession_periodic=None,
            xbrl_period=None,
            xbrl_year=None,
        ))
        out = qi.resolve_quarter_info("AVGO", "0001730168-23-000093", session=session)
        # filed_8k Dec 7, fye=10 → Q4 event → 10-K expected.
        self.assertEqual(out["quarter_label"], "Q4_FY2023")
        self.assertEqual(out["form_type_periodic"], "10-K")
        self.assertEqual(out["accession_periodic"], "")
        self.assertEqual(out["quarter_identity_source"], "fiscal_math")

    def test_fiscal_math_fallback_non_q4_yields_10q(self):
        session = _FakeSession(_row(
            filed_8k="2023-08-31T17:18:57-04:00",
            period_of_report=None,
            form_type_periodic=None,
            accession_periodic=None,
            matched_accession_periodic=None,
            xbrl_period=None,
            xbrl_year=None,
        ))
        out = qi.resolve_quarter_info("AVGO", "any-acc", session=session)
        self.assertEqual(out["quarter_label"], "Q3_FY2023")
        self.assertEqual(out["form_type_periodic"], "10-Q")
        self.assertEqual(out["accession_periodic"], "")


if __name__ == "__main__":
    unittest.main()
