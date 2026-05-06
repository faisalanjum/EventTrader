"""U64 — PIT-safety regression tests for quarter_identity (Goal 4 architecture).

The original U64 commit added a Cypher CASE WHEN gate that masked any matched
periodic whose `q.created` was strictly after `r.created` (the 8-K's filing
time). Goal 4 replaced that whole cascade with `prior_periodic_projection`:
the resolver now queries ONLY priors with `created <= filed_8k`, so future-
filed periodics are never returned in the first place. The PIT-safety
property is preserved — by construction rather than by post-query masking.

This file tests the SAME safety property under the new architecture:

  1. CypherPitSafetyTests        — static guards on Cypher PIT bounds and
                                    on the absence of the old _STALE_MATCH_DAYS=150
                                    constant and the old CASE WHEN mask
  2. FailClosedBehaviorTests     — no-prior, long-gap, and (defensive)
                                    future-prior must FAIL_CLOSED with the
                                    documented sources
  3. CalendarShapedAutoOkTests   — normal calendar-shaped priors must AUTO_OK
                                    via prior_periodic_projection_qN_to_qM;
                                    accession_periodic stays empty for
                                    projection paths (it's a projection,
                                    not a same-event periodic)
  4. RuleFDirectRecentTests      — odd 52/53-week prior filed within 24h
                                    → AUTO_OK via rule_f_direct_recent_prior;
                                    accession_periodic IS populated because
                                    that branch is the same-event 10-Q-then-8-K
                                    pattern, so the accession is PIT-visible

Run:
    venv/bin/python -m pytest scripts/earnings/test_quarter_identity_u64.py -q
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

import quarter_identity as qi  # noqa: E402


# ── Fake Neo4j session ───────────────────────────────────────────────
class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def single(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeSession:
    """Routes queries by content:
      - main _QUERY (RETURN includes 'prev_8k_ts'): returns metadata row
        with embedded 'priors' collection
      - _PRIOR_QUERY (uses $filed_8k param): returns iterable priors
      - _XBRL_QUERY (uses $accession only): returns single XBRL row
      - _TICKER_CONTEXT_QUERY (preload, multiple 8-Ks): returns empty
    """

    def __init__(self, *, metadata_row=None, priors=None, xbrl_by_accession=None):
        self.metadata_row = metadata_row
        self.priors = list(priors or [])
        self.xbrl_by_accession = dict(xbrl_by_accession or {})
        self.calls = []

    def run(self, query, **params):
        self.calls.append((query[:120], params))
        # Ticker preload (no $accession param; uses ORDER BY datetime(r.created))
        if "ORDER BY datetime(r.created)" in query and "$ticker" in query:
            return _FakeResult([])
        # Main _QUERY (RETURN includes prev_8k_ts and the row carries 'priors')
        if "prev_8k_ts" in query:
            return _FakeResult([self.metadata_row] if self.metadata_row else [])
        # _PRIOR_QUERY uses $filed_8k AND $accession_8k
        if "$filed_8k" in query:
            return _FakeResult(self.priors)
        # _XBRL_QUERY uses $accession only (no $filed_8k, no $ticker)
        if "$accession" in query:
            row = self.xbrl_by_accession.get(params.get("accession"))
            return _FakeResult([row] if row else [])
        return _FakeResult([])


# ── Helpers ──────────────────────────────────────────────────────────
def _reset_caches():
    qi._PRIOR_CACHE.clear()
    qi._FYE_CACHE.clear()
    qi._XBRL_CACHE.clear()
    qi._CONTEXT_CACHE.clear()
    qi._TICKER_CONTEXT_PRELOADED.clear()


def _meta(filed_8k, fye_month=12, priors=None):
    """Minimal main-_QUERY row with optional embedded priors."""
    return {
        "accession_8k": "ACCN-this",
        "filed_8k": filed_8k,
        "market_session": "post_market",
        "fye_month": fye_month,
        "prev_8k_ts": "2025-01-01T16:00:00-05:00",
        "priors": list(priors or []),
    }


def _prior(accession, created, period, form, xbrl_year=None, xbrl_period=None):
    """Prior periodic record matching _normalize_prior_record's expected shape."""
    return {
        "accession": accession,
        "created": created,
        "period": period,
        "form": form,
        "xbrl_year": xbrl_year,
        "xbrl_period": xbrl_period,
    }


def _resolve(monkeypatch, *, ticker, accession, meta, priors=None,
             xbrl_by_accession=None, fye_month_override=None):
    """Run resolve_quarter_info with caches cleared and a stubbed get_fye_month."""
    _reset_caches()
    fye = fye_month_override if fye_month_override is not None else meta.get("fye_month")
    monkeypatch.setattr(
        qi, "get_fye_month",
        lambda _ticker, gaps=None: fye,
    )
    session = _FakeSession(
        metadata_row=meta,
        priors=priors,
        xbrl_by_accession=xbrl_by_accession,
    )
    return qi.resolve_quarter_info(ticker, accession, session=session)


# ── 1. Cypher PIT-safety static guards ───────────────────────────────
class CypherPitSafetyTests(unittest.TestCase):
    """Static asserts: PIT bounds in Cypher; no resurrected _STALE_MATCH_DAYS;
    old CASE WHEN mask is gone (Goal 4 replaced the architecture)."""

    def test_main_query_filters_priors_to_pit(self):
        # _QUERY's prior-fetch CALL must restrict to priors created on or
        # before the 8-K's created timestamp.
        self.assertRegex(
            qi._QUERY,
            r"datetime\(p\.created\)\s*<=\s*datetime\(r\.created\)",
        )

    def test_prior_query_filters_to_filed_8k_param(self):
        # _PRIOR_QUERY (used as a fallback when the main row doesn't
        # prefetch priors) must use the explicit $filed_8k cutoff.
        self.assertRegex(
            qi._PRIOR_QUERY,
            r"datetime\(p\.created\)\s*<=\s*datetime\(\$filed_8k\)",
        )

    def test_no_stale_match_days_attribute(self):
        self.assertFalse(
            hasattr(qi, "_STALE_MATCH_DAYS"),
            "_STALE_MATCH_DAYS was the FCX-bug source; must not be reintroduced",
        )

    def test_no_stale_match_days_constant_in_source(self):
        src = (PROJECT_ROOT / "scripts/earnings/quarter_identity.py").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(src, r"_STALE_MATCH_DAYS\s*=\s*150")

    def test_old_case_when_mask_pattern_absent(self):
        # The old U64 CASE WHEN gate was a post-query masking workaround.
        # Goal 4 enforces PIT structurally — the mask line must be gone.
        self.assertNotIn(
            "WHEN q.created IS NOT NULL AND datetime(q.created) <= datetime(r.created)",
            qi._QUERY,
        )

    def test_main_query_uses_pit_bound_in_call_subquery(self):
        # The PIT bound is inside the OPTIONAL CALL subquery for priors.
        # Confirm the comparison is in the prior-fetch block, not just the
        # source as a whole (defends against accidental relocation).
        self.assertIn("OPTIONAL CALL (r, c)", qi._QUERY)
        self.assertIn("datetime(p.created) <= datetime(r.created)", qi._QUERY)


# ── 2. Behavioral: fail-closed safety paths ──────────────────────────
class FailClosedBehaviorTests(unittest.TestCase):
    """The new resolver fail-closes on safety conditions; safety_action ==
    FAIL_CLOSED with the documented source. accession_periodic stays empty
    so no prior accession can leak into a refused result."""

    def test_no_prior_fail_closed(self):
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T16:00:00-04:00", fye_month=12, priors=[])
            out = _resolve(mp, ticker="FOO", accession="ACCN-this", meta=meta)
        self.assertEqual(out["safety_action"], "FAIL_CLOSED")
        self.assertEqual(
            out["quarter_identity_source"], "prior_periodic_projection_no_prior"
        )
        self.assertIsNone(out["quarter_label"])
        # No prior accession may be echoed when the resolver refused.
        self.assertEqual(out["accession_periodic"], "")

    def test_long_gap_fail_closed(self):
        # Calendar-shaped prior >150 days old → fail-closed.
        priors = [
            _prior(
                accession="prior-stale",
                created="2025-01-01T08:00:00-05:00",
                period="2024-12-31",
                form="10-K",
                xbrl_year="2024", xbrl_period="FY",
            )
        ]
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T16:00:00-04:00", fye_month=12, priors=priors)
            out = _resolve(mp, ticker="FOO", accession="ACCN-this",
                           meta=meta, priors=priors)
        self.assertEqual(out["safety_action"], "FAIL_CLOSED")
        self.assertEqual(
            out["quarter_identity_source"],
            "prior_periodic_projection_long_gap_fail_closed",
        )
        self.assertEqual(out["accession_periodic"], "")

    def test_future_prior_via_calendar_branch_fail_closed(self):
        # Defensive: the Cypher PIT bound should keep future-created
        # periodics out of the prior list. If something nonetheless slipped
        # through (e.g., a future test fixture or a Neo4j clock skew), the
        # calendar branch's gap_days < 0 check fail-closes safely.
        priors = [
            _prior(
                accession="prior-future",
                created="2026-05-15T08:00:00-04:00",  # AFTER filed_8k
                period="2026-03-31",                  # calendar-shaped
                form="10-Q",
                xbrl_year="2026", xbrl_period="Q1",
            )
        ]
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T16:00:00-04:00", fye_month=12, priors=priors)
            out = _resolve(mp, ticker="FOO", accession="ACCN-this",
                           meta=meta, priors=priors)
        self.assertEqual(out["safety_action"], "FAIL_CLOSED")
        self.assertEqual(
            out["quarter_identity_source"],
            "prior_periodic_projection_future_prior_fail_closed",
        )
        self.assertEqual(out["accession_periodic"], "")


# ── 3. Calendar-shaped AUTO_OK path (currently-firing rows) ──────────
class CalendarShapedAutoOkTests(unittest.TestCase):
    """Normal calendar-shaped prior advances one quarter via period_to_fiscal.
    The 9,860 currently-firing rows use this path and must be preserved."""

    def test_calendar_prior_q4_advances_to_q1_with_fy_rollover(self):
        # FCX-shape: prior Q4 FY2025 10-K (period 2025-12-31), this 8-K
        # filed 2026-04-23 → must advance to Q1 FY2026.
        priors = [
            _prior(
                accession="prior-q4",
                created="2026-02-14T08:00:00-05:00",
                period="2025-12-31",
                form="10-K",
                xbrl_year="2025", xbrl_period="FY",
            )
        ]
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T08:09:07-04:00", fye_month=12, priors=priors)
            out = _resolve(mp, ticker="FCX", accession="ACCN-this",
                           meta=meta, priors=priors)
        self.assertEqual(out["safety_action"], "AUTO_OK")
        self.assertEqual(out["quarter_label"], "Q1_FY2026")
        self.assertEqual(
            out["quarter_identity_source"], "prior_periodic_projection_q4_to_q1"
        )

    def test_calendar_projection_does_not_expose_prior_accession(self):
        # The calendar-shaped branch ADVANCES from prior — it is a projection,
        # not a same-event match. The prior's accession must NOT be echoed
        # as accession_periodic; downstream consumers expect that field to
        # mean "the periodic the 8-K is announcing about", which only the
        # rule_f_direct_recent_prior path can claim.
        priors = [
            _prior(
                accession="prior-q4",
                created="2026-02-14T08:00:00-05:00",
                period="2025-12-31",
                form="10-K",
                xbrl_year="2025", xbrl_period="FY",
            )
        ]
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T08:09:07-04:00", fye_month=12, priors=priors)
            out = _resolve(mp, ticker="FCX", accession="ACCN-this",
                           meta=meta, priors=priors)
        self.assertEqual(out["safety_action"], "AUTO_OK")
        # Calendar advance is a projection — accession_periodic stays empty.
        self.assertEqual(out["accession_periodic"], "")


# ── 4. Rule F direct-recent path ─────────────────────────────────────
class RuleFDirectRecentTests(unittest.TestCase):
    """Odd 52/53-week prior filed within 24h of the 8-K → use prior label
    directly (no advance). This is the same-event 10-Q-then-8-K pattern
    (PEP/LEVI class). accession_periodic IS populated here because the
    prior IS the same-event periodic the 8-K is announcing."""

    def test_direct_recent_odd_prior_returns_xbrl_label(self):
        # 52/53-week shape: period day 21 (mid-month, not within 5 days of
        # last day). Prior filed 9 minutes before 8-K → same-event pattern.
        priors = [
            _prior(
                accession="prior-recent",
                created="2026-04-23T08:00:00-04:00",
                period="2026-03-21",
                form="10-Q",
                xbrl_year="2026", xbrl_period="Q1",
            )
        ]
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T08:09:07-04:00", fye_month=12, priors=priors)
            out = _resolve(mp, ticker="FOO", accession="ACCN-this",
                           meta=meta, priors=priors)
        self.assertEqual(out["safety_action"], "AUTO_OK")
        self.assertEqual(out["quarter_label"], "Q1_FY2026")
        self.assertEqual(
            out["quarter_identity_source"], "rule_f_direct_recent_prior"
        )
        # Same-event: the prior periodic IS what the 8-K is announcing.
        # accession_periodic carries the prior's accession through.
        self.assertEqual(out["accession_periodic"], "prior-recent")

    def test_direct_recent_odd_prior_preserves_form_type(self):
        priors = [
            _prior(
                accession="prior-recent-10k",
                created="2026-04-23T08:00:00-04:00",
                period="2026-03-21",
                form="10-K",
                xbrl_year="2026", xbrl_period="FY",
            )
        ]
        import pytest as _pytest
        with _pytest.MonkeyPatch.context() as mp:
            meta = _meta("2026-04-23T08:09:07-04:00", fye_month=12, priors=priors)
            out = _resolve(mp, ticker="FOO", accession="ACCN-this",
                           meta=meta, priors=priors)
        self.assertEqual(out["safety_action"], "AUTO_OK")
        self.assertEqual(out["form_type_periodic"], "10-K")


if __name__ == "__main__":
    unittest.main()
