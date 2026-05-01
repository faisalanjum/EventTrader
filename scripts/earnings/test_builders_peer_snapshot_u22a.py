"""U22a builder backfill tests.

Covers the additions in `scripts/earnings/builders/peer_earnings_snapshot.py`:
- new fields in peer dict (session_sector_pct, session_macro_pct, is_amendment,
  accession_periodic, form_type_periodic) + bz_id per headline
- per-horizon and whole-schedule fail-CLOSED PIT-nulling
- defensive `_parse_pit_safe` for malformed timestamps
- math-max best_*_pct from ADJ values (not raw)
- no-leak invariant: `matched_accession_periodic` not exposed in peer dict
- `summary.gaps` emission on whole-schedule failure

All mocked at the `get_manager` boundary — no live Neo4j.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from scripts.earnings.builders import peer_earnings_snapshot as ps

pytestmark = pytest.mark.builders


# ─── Fixtures ─────────────────────────────────────────────────────────


def _row(**overrides):
    """Build a mock Cypher row with sane defaults for one peer."""
    base = {
        'industry': 'Semiconductors',
        'ticker': 'NVDA',
        'name': 'NVIDIA CORP',
        'mkt_cap': '3,179,780,000,000',
        'filed': '2023-11-21T16:22:00-05:00',
        'session': 'post_market',
        'accession': '0001045810-23-000225',
        'period_of_report': '2023-11-21',
        'returns_schedule': json.dumps({
            'hourly': '2023-11-21T17:30:00-05:00',
            'session': '2023-11-22T09:30:00-05:00',
            'daily': '2023-11-22T16:00:00-05:00',
        }),
        'fy_end_month': '1',
        'daily_stock': -2.46,
        'hourly_stock': 3.18,
        'session_stock': 3.99,
        'daily_sector': 0.45,
        'daily_macro': 0.38,
        'hourly_sector': 0.48,
        'hourly_macro': 0.16,
        'session_sector': 1.68,
        'session_macro': 0.74,
        'is_amendment': False,
        'accession_periodic': None,
        'form_type_periodic': None,
        'raw_headlines': [],
    }
    base.update(overrides)
    return base


def _build(rows, *, pit='2023-12-07T16:18:51-05:00'):
    """Run the builder with mocked manager returning `rows`."""
    mock_manager = MagicMock()
    mock_manager.execute_cypher_query_all.return_value = rows
    with patch.object(ps, 'get_manager', return_value=mock_manager):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            out_path = f.name
        try:
            return ps.build_peer_earnings_snapshot(
                ticker='AVGO', pit_cutoff=pit, out_path=out_path
            )
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)


# ─── New cohort fields surface in peer dict ────────────────────────────


def test_returns_session_sector_in_peer_dict():
    pkt = _build([_row(session_sector=1.68)])
    assert pkt['peers'][0]['session_sector_pct'] == 1.68


def test_returns_session_macro_in_peer_dict():
    pkt = _build([_row(session_macro=0.74)])
    assert pkt['peers'][0]['session_macro_pct'] == 0.74


def test_returns_is_amendment_passthrough_true():
    pkt = _build([_row(is_amendment=True)])
    assert pkt['peers'][0]['is_amendment'] is True


def test_returns_is_amendment_passthrough_false():
    pkt = _build([_row(is_amendment=False)])
    assert pkt['peers'][0]['is_amendment'] is False


def test_returns_per_peer_accession_periodic_when_visible():
    pkt = _build([_row(accession_periodic='0001045810-23-000245',
                       form_type_periodic='10-Q')])
    p = pkt['peers'][0]
    assert p['accession_periodic'] == '0001045810-23-000245'
    assert p['form_type_periodic'] == '10-Q'


def test_returns_per_peer_accession_periodic_none_when_post_pit():
    """Cypher CASE WHEN returns null when q.created > pit_cutoff."""
    pkt = _build([_row(accession_periodic=None, form_type_periodic=None)])
    p = pkt['peers'][0]
    assert p['accession_periodic'] is None
    assert p['form_type_periodic'] is None


def test_returns_per_peer_accession_periodic_none_for_new_ipo():
    """New IPO: OPTIONAL CALL returns no rows → both fields are None."""
    pkt = _build([_row(accession_periodic=None, form_type_periodic=None)])
    assert pkt['peers'][0]['accession_periodic'] is None


def test_form_type_periodic_is_null_when_accession_periodic_is_null():
    """Pass-2 release-blocker: PIT symmetry between accession + form_type gates."""
    pkt = _build([_row(accession_periodic=None, form_type_periodic=None)])
    p = pkt['peers'][0]
    # Both must be None; if accession is masked, form_type is too
    assert p['accession_periodic'] is None
    assert p['form_type_periodic'] is None


def test_does_not_expose_matched_accession_periodic_in_peer_dict():
    """U22a contract: peer bundle must NOT expose raw matched accession.

    Differs from U64 target ticker, where raw matched_accession_periodic IS
    exposed for internal denylist/XBRL logic. Peers have no equivalent need.
    """
    pkt = _build([_row()])
    assert 'matched_accession_periodic' not in pkt['peers'][0]


# ─── Per-horizon fail-CLOSED PIT-nulling ──────────────────────────────


def _row_with_schedule(**sched):
    """Helper: row with custom returns_schedule values."""
    return _row(returns_schedule=json.dumps(sched))


def test_pit_nulls_session_sector_macro_when_session_window_post_pit():
    # session_end is AFTER pit_cutoff; session_stock + session_sector + session_macro all nulled
    rs = {
        'hourly': '2023-11-21T17:30:00-05:00',
        'session': '2023-12-08T09:30:00-05:00',  # post-PIT
        'daily': '2023-11-22T16:00:00-05:00',
    }
    pkt = _build([_row(returns_schedule=json.dumps(rs), session_stock=3.99,
                       session_sector=1.68, session_macro=0.74)])
    p = pkt['peers'][0]
    assert p['session_stock_pct'] is None
    assert p['session_sector_pct'] is None
    assert p['session_macro_pct'] is None
    # daily/hourly preserved
    assert p['daily_stock_pct'] == -2.46
    assert p['hourly_stock_pct'] == 3.18


def test_pit_nulls_only_session_when_only_session_post_pit():
    rs = {
        'hourly': '2023-11-21T17:30:00-05:00',
        'session': '2023-12-08T09:30:00-05:00',  # post-PIT
        'daily': '2023-11-22T16:00:00-05:00',
    }
    pkt = _build([_row(returns_schedule=json.dumps(rs))])
    p = pkt['peers'][0]
    assert p['session_stock_pct'] is None
    assert p['hourly_stock_pct'] is not None
    assert p['daily_stock_pct'] is not None


def test_per_horizon_fail_closed_when_rs_daily_missing():
    """rs has hourly+session but daily key missing → daily fail-CLOSED."""
    rs = {
        'hourly': '2023-11-21T17:30:00-05:00',
        'session': '2023-11-22T09:30:00-05:00',
        # 'daily' key absent
    }
    pkt = _build([_row(returns_schedule=json.dumps(rs))])
    p = pkt['peers'][0]
    assert p['daily_stock_pct'] is None
    assert p['daily_sector_pct'] is None
    assert p['daily_macro_pct'] is None
    # hourly/session preserved
    assert p['hourly_stock_pct'] is not None
    assert p['session_stock_pct'] is not None


def test_per_horizon_fail_closed_when_rs_session_malformed():
    """Malformed session string → _parse_pit_safe returns None → session fail-CLOSED."""
    rs = {
        'hourly': '2023-11-21T17:30:00-05:00',
        'session': 'TBD',  # malformed
        'daily': '2023-11-22T16:00:00-05:00',
    }
    pkt = _build([_row(returns_schedule=json.dumps(rs))])
    p = pkt['peers'][0]
    assert p['session_stock_pct'] is None
    assert p['session_sector_pct'] is None
    assert p['session_macro_pct'] is None
    # other horizons untouched
    assert p['daily_stock_pct'] is not None
    assert p['hourly_stock_pct'] is not None


def test_per_horizon_fail_closed_when_rs_hourly_empty_string():
    rs = {
        'hourly': '',  # empty string falsy
        'session': '2023-11-22T09:30:00-05:00',
        'daily': '2023-11-22T16:00:00-05:00',
    }
    pkt = _build([_row(returns_schedule=json.dumps(rs))])
    p = pkt['peers'][0]
    assert p['hourly_stock_pct'] is None
    assert p['hourly_sector_pct'] is None
    assert p['hourly_macro_pct'] is None


# ─── Whole-schedule fail-CLOSED ───────────────────────────────────────


def test_fail_closed_when_returns_schedule_missing_nulls_all_horizons():
    pkt = _build([_row(returns_schedule=None)])
    p = pkt['peers'][0]
    for k in ('daily_stock_pct', 'session_stock_pct', 'hourly_stock_pct',
              'daily_sector_pct', 'session_sector_pct', 'hourly_sector_pct',
              'daily_macro_pct', 'session_macro_pct', 'hourly_macro_pct'):
        assert p[k] is None, f'{k} should be None under fail-CLOSED'


def test_fail_closed_when_returns_schedule_malformed_nulls_all_horizons():
    pkt = _build([_row(returns_schedule='not-json{{{')])
    p = pkt['peers'][0]
    assert p['daily_stock_pct'] is None
    assert p['session_stock_pct'] is None
    assert p['hourly_stock_pct'] is None


def test_fail_closed_emits_summary_gaps_entry():
    pkt = _build([_row(returns_schedule=None, ticker='ZZZZ',
                       accession='0000000000-99-999999')])
    gaps = pkt['summary'].get('gaps') or []
    assert len(gaps) == 1
    assert gaps[0]['type'] == 'missing_returns_schedule'
    assert gaps[0]['peer_ticker'] == 'ZZZZ'
    assert gaps[0]['peer_accession'] == '0000000000-99-999999'


def test_fail_closed_keeps_peer_in_list_for_visibility():
    pkt = _build([_row(returns_schedule=None)])
    assert len(pkt['peers']) == 1
    assert pkt['peers'][0]['ticker'] == 'NVDA'


def test_summary_gaps_absent_when_all_peers_have_schedule():
    pkt = _build([_row()])
    assert 'gaps' not in pkt['summary']


# ─── Defensive _parse_pit_safe ────────────────────────────────────────


def test_parse_pit_safe_returns_none_for_invalid_string():
    assert ps._parse_pit_safe('not-a-timestamp') is None


def test_parse_pit_safe_returns_none_for_empty_string():
    assert ps._parse_pit_safe('') is None


def test_parse_pit_safe_returns_none_for_none_input():
    assert ps._parse_pit_safe(None) is None


def test_parse_pit_safe_handles_valid_timestamp():
    dt = ps._parse_pit_safe('2023-12-07T16:18:51-05:00')
    assert dt is not None


# ─── _extract_bz_id helper ────────────────────────────────────────────


def test_extract_bz_id_from_bzNews_prefix():
    assert ps._extract_bz_id('bzNews_35906540') == '35906540'


def test_extract_bz_id_returns_none_for_non_bz_format():
    assert ps._extract_bz_id('reuters-12345') is None


def test_extract_bz_id_returns_none_for_empty():
    assert ps._extract_bz_id('') is None


def test_extract_bz_id_returns_none_for_none():
    assert ps._extract_bz_id(None) is None


def test_extract_bz_id_returns_none_for_non_digit_suffix():
    assert ps._extract_bz_id('bzNews_abc') is None


def test_extract_bz_id_returns_none_for_bare_prefix():
    assert ps._extract_bz_id('bzNews_') is None


# ─── bz_id injected per headline in peer dict ─────────────────────────


def test_bz_id_injected_per_headline_when_news_id_recognized():
    headlines = [
        {'date': '2023-11-21T16:30:00', 'title': 'NVIDIA Q3 EPS $4.02 Beats',
         'news_id': 'bzNews_35906540',
         'channels': ['Earnings', 'Earnings Beats']},
    ]
    pkt = _build([_row(raw_headlines=headlines)])
    p = pkt['peers'][0]
    assert len(p['headlines']) == 1
    assert p['headlines'][0]['bz_id'] == '35906540'


def test_bz_id_is_none_for_unrecognized_news_id():
    headlines = [
        {'date': '2023-11-21T16:30:00', 'title': 'Some Headline',
         'news_id': 'reuters-12345', 'channels': ['Earnings']},
    ]
    pkt = _build([_row(raw_headlines=headlines)])
    assert pkt['peers'][0]['headlines'][0]['bz_id'] is None


# ─── best_*_pct: math max from ADJ values (U23) ───────────────────────


def test_best_pct_uses_math_max_across_three_horizons():
    """Bundle stores raw; best_* is computed from stock-minus-benchmark ADJ."""
    pkt = _build([_row(
        daily_stock=-2.46, daily_sector=0.45, daily_macro=0.38,
        session_stock=3.99, session_sector=1.68, session_macro=0.74,
        hourly_stock=3.18, hourly_sector=0.48, hourly_macro=0.16,
    )])
    p = pkt['peers'][0]
    # ADJ values:
    # daily_sec_adj = -2.46 - 0.45 = -2.91
    # session_sec_adj = 3.99 - 1.68 = 2.31
    # hourly_sec_adj = 3.18 - 0.48 = 2.70
    # max = 2.70 (hourly)
    assert math.isclose(p['best_sector_pct'], 2.70, abs_tol=0.001)
    # daily_mac_adj = -2.46 - 0.38 = -2.84
    # session_mac_adj = 3.99 - 0.74 = 3.25
    # hourly_mac_adj = 3.18 - 0.16 = 3.02
    # max = 3.25 (session)
    assert math.isclose(p['best_macro_pct'], 3.25, abs_tol=0.001)


def test_best_pct_computed_from_adjusted_values_not_raw():
    """Anti-regression: confirms we're not just taking max of raw benchmark returns."""
    # Stock down 5%, all sector indexes up; max ADJ = least negative
    pkt = _build([_row(
        daily_stock=-5.0, daily_sector=1.0, daily_macro=1.0,
        session_stock=-5.0, session_sector=2.0, session_macro=2.0,
        hourly_stock=-5.0, hourly_sector=3.0, hourly_macro=3.0,
    )])
    p = pkt['peers'][0]
    # If raw: max(1, 2, 3) = 3; if ADJ: max(-5-1, -5-2, -5-3) = max(-6, -7, -8) = -6
    assert math.isclose(p['best_sector_pct'], -6.0, abs_tol=0.001)
    assert math.isclose(p['best_macro_pct'], -6.0, abs_tol=0.001)


def test_best_pct_returns_none_when_all_horizons_null():
    """U23 invariant: never 0-artifact when all data missing."""
    pkt = _build([_row(returns_schedule=None)])
    p = pkt['peers'][0]
    assert p['best_sector_pct'] is None
    assert p['best_macro_pct'] is None


def test_best_pct_zero_artifact_eliminated_with_partial_nulls():
    pkt = _build([_row(
        daily_stock=None, daily_sector=None, daily_macro=None,
        session_stock=None, session_sector=None, session_macro=None,
        hourly_stock=2.0, hourly_sector=0.5, hourly_macro=0.3,
    )])
    p = pkt['peers'][0]
    # only hourly is non-null; best = hourly_adj
    assert math.isclose(p['best_sector_pct'], 1.5, abs_tol=0.001)
    assert math.isclose(p['best_macro_pct'], 1.7, abs_tol=0.001)


# ─── _adj helper ──────────────────────────────────────────────────────


def test_adj_helper_subtracts_correctly():
    assert math.isclose(ps._adj(-2.46, 0.38), -2.84, abs_tol=0.001)


def test_adj_helper_returns_none_when_stock_is_none():
    assert ps._adj(None, 0.38) is None


def test_adj_helper_returns_none_when_index_is_none():
    assert ps._adj(-2.46, None) is None


def test_adj_helper_handles_string_input():
    """Defensive: stray string in bundle should produce None, not crash."""
    assert ps._adj('not-a-number', 0.38) is None


# ─── _max_or_none helper ──────────────────────────────────────────────


def test_max_or_none_returns_max_of_non_null():
    assert ps._max_or_none(1.0, 2.0, 3.0) == 3.0


def test_max_or_none_filters_none_values():
    assert ps._max_or_none(None, 2.0, None) == 2.0


def test_max_or_none_returns_none_when_all_none():
    assert ps._max_or_none(None, None, None) is None


def test_max_or_none_keeps_zero_as_valid_value():
    """Anti-bug: filter(None, [0]) would drop zero; we must keep it."""
    assert ps._max_or_none(0.0, -1.0, -2.0) == 0.0


# ─── context_horizon: keep original prefer-daily-fallback semantic ───────


def test_context_horizon_preserves_prefer_daily_fallback_semantic():
    """Pass-8 decision: keep original semantic; not redefined to max-ADJ."""
    pkt = _build([_row(daily_sector=0.45, hourly_sector=0.48)])
    # daily_sector is non-None → context_horizon = 'daily'
    assert pkt['peers'][0]['context_horizon'] == 'daily'


def test_context_horizon_falls_back_to_hourly_when_no_daily():
    pkt = _build([_row(daily_sector=None, hourly_sector=0.48,
                       returns_schedule=json.dumps({
                           'hourly': '2023-11-21T17:30:00-05:00',
                           'session': '2023-11-22T09:30:00-05:00',
                           'daily': '2023-12-08T16:00:00-05:00',  # post-PIT, daily nulled
                       }))])
    assert pkt['peers'][0]['context_horizon'] == 'hourly'


def test_context_horizon_none_when_all_sector_null():
    pkt = _build([_row(returns_schedule=None)])
    assert pkt['peers'][0]['context_horizon'] is None
