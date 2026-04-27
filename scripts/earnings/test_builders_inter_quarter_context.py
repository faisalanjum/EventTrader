"""Mocked unit tests for inter_quarter_context (Stage 3.1)."""
from __future__ import annotations
import json
import math
from unittest.mock import MagicMock, patch
import pytest

from scripts.earnings.builders import inter_quarter_context as iq

pytestmark = pytest.mark.builders


# ── Mock helpers ─────────────────────────────────────────────────────────

def _mock_manager(rows_by_query):
    """Mock Neo4j manager that routes queries by EXACT identity match against the
    canonical query-constant strings imported from `inter_quarter_context`."""
    m = MagicMock()
    def execute(query, params):
        if query == iq.QUERY_IQ_PRICES:
            return rows_by_query.get("PRICES", [])
        if query == iq.QUERY_IQ_NEWS:
            return rows_by_query.get("NEWS", [])
        if query == iq.QUERY_IQ_FILINGS:
            return rows_by_query.get("FILINGS", [])
        if query == iq.QUERY_IQ_DIVIDENDS:
            return rows_by_query.get("DIVIDENDS", [])
        if query == iq.QUERY_IQ_SPLITS:
            return rows_by_query.get("SPLITS", [])
        if query == iq.QUERY_IQ_COMPANY_CONTEXT:
            return rows_by_query.get("COMPANY_CONTEXT", [])
        raise AssertionError(f"unexpected query: {query[:120]}")
    m.execute_cypher_query_all.side_effect = execute
    m.close = MagicMock()
    return m


def _mock_session_helper():
    """Mock MarketSessionClassifier.

    Returns predictable times so PIT-safety logic can be exercised:
      - get_interval_start_time → fixed start (event_ts)
      - get_interval_end_time → event + 1h
      - get_start_time → event_ts (session start)
      - get_end_time → event + 4h (session end)
      - get_1d_impact_times → (prev close, next close)
    """
    h = MagicMock()
    from datetime import datetime as _dt, timedelta as _td

    def _parse(ts_str):
        return iq._parse_dt_for_pit(ts_str)

    h.get_interval_start_time = lambda ts: _parse(ts)
    h.get_interval_end_time = lambda ts, mins, respect_session_boundary=True: \
        _parse(ts) + _td(minutes=mins)
    h.get_start_time = lambda ts: _parse(ts)
    h.get_end_time = lambda ts: _parse(ts) + _td(hours=4)
    h.get_1d_impact_times = lambda ts: (_parse(ts) - _td(hours=1),
                                        _parse(ts) + _td(hours=24))
    return h


# ── _iq_parse_json_field ─────────────────────────────────────────────────

def test_iq_parse_json_field_none_returns_fallback():
    assert iq._iq_parse_json_field(None, []) == []
    assert iq._iq_parse_json_field(None, {}) == {}


def test_iq_parse_json_field_passthrough_for_list_dict():
    assert iq._iq_parse_json_field([1, 2, 3], None) == [1, 2, 3]
    assert iq._iq_parse_json_field({"a": 1}, None) == {"a": 1}


def test_iq_parse_json_field_bad_string_returns_fallback():
    assert iq._iq_parse_json_field("not-json", "fallback") == "fallback"
    assert iq._iq_parse_json_field("{not valid", []) == []


def test_iq_parse_json_field_valid_string_parses():
    assert iq._iq_parse_json_field('[1, 2, 3]', None) == [1, 2, 3]


# ── _norm_ret ────────────────────────────────────────────────────────────

def test_norm_ret_nan_returns_none():
    assert iq._norm_ret(float('nan')) is None


def test_norm_ret_none_returns_none():
    assert iq._norm_ret(None) is None


def test_norm_ret_string_non_numeric_returns_none():
    assert iq._norm_ret("abc") is None


def test_norm_ret_zero_returns_zero():
    assert iq._norm_ret(0.0) == 0.0


def test_norm_ret_large_negative_rounds_to_2dp():
    assert iq._norm_ret(-12345.6789) == -12345.68


def test_norm_ret_list_takes_first():
    assert iq._norm_ret([3.14159, 2.71828]) == 3.14


def test_norm_ret_empty_list_returns_none():
    assert iq._norm_ret([]) is None


# ── _parse_dt_for_pit format coverage ────────────────────────────────────

def test_parse_dt_for_pit_z_suffix():
    """Z suffix becomes +00:00 — UTC."""
    dt = iq._parse_dt_for_pit("2024-09-15T16:00:00Z")
    assert dt.tzinfo is not None


def test_parse_dt_for_pit_standard_offset():
    dt = iq._parse_dt_for_pit("2024-09-15T16:00:00-04:00")
    assert dt.tzinfo is not None


def test_parse_dt_for_pit_compact_offset():
    """Compact offset -0400 normalized to -04:00."""
    dt = iq._parse_dt_for_pit("2024-09-15T16:00:00-0400")
    assert dt.tzinfo is not None


def test_parse_dt_for_pit_distinct_from_peer():
    """Mirror of the existing test_builders_imports.py shadow guard, scoped
    to the new canonical home. Stage 3.1 contract: inter_quarter_context's
    _parse_dt_for_pit is a DIFFERENT object from peer_earnings_snapshot's."""
    from scripts.earnings.builders.inter_quarter_context import _parse_dt_for_pit as iq_fn
    from scripts.earnings.builders.peer_earnings_snapshot import _parse_dt_for_pit as peer_fn
    assert iq_fn is not peer_fn, "shadow violation: same object across modules"


# ── _is_price_pit_safe ───────────────────────────────────────────────────

def test_is_price_pit_safe_post_cutoff_returns_false():
    assert iq._is_price_pit_safe("2024-09-15T20:00:00-04:00",
                                  "2024-09-15T16:00:00-04:00") is False


def test_is_price_pit_safe_pre_cutoff_returns_true():
    assert iq._is_price_pit_safe("2024-09-15T13:00:00-04:00",
                                  "2024-09-15T16:00:00-04:00") is True


def test_is_price_pit_safe_missing_returns_false():
    assert iq._is_price_pit_safe(None, "2024-09-15T16:00:00-04:00") is False


def test_is_price_pit_safe_unparseable_returns_false():
    assert iq._is_price_pit_safe("not-a-timestamp",
                                  "2024-09-15T16:00:00-04:00") is False


# ── _cutoff_boundary_price_role ──────────────────────────────────────────

def test_cutoff_boundary_role_late_is_ordinary():
    assert iq._cutoff_boundary_price_role("2024-09-15T16:00:00-04:00") == "ordinary"
    assert iq._cutoff_boundary_price_role("2024-09-15T20:00:00-04:00") == "ordinary"


def test_cutoff_boundary_role_early_is_reference_only():
    assert iq._cutoff_boundary_price_role("2024-09-15T13:00:00-04:00") == "reference_only"


# ── _safe_adj ────────────────────────────────────────────────────────────

def test_safe_adj_returns_rounded_diff():
    assert iq._safe_adj(2.567, 1.234) == 1.33


def test_safe_adj_none_returns_none():
    assert iq._safe_adj(None, 1.0) is None
    assert iq._safe_adj(1.0, None) is None


# ── boundary day creation ────────────────────────────────────────────────

def test_boundary_days_synthesized_when_no_price_rows(tmp_path):
    """When PRICES returns empty, prev_boundary and cutoff_boundary days are still created."""
    mgr = _mock_manager({})
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T16:00:00-04:00",
                out_path=out
            )
    days_by_role = {d.get('boundary_role'): d for d in packet["days"] if d.get('boundary_role')}
    assert "prev_boundary" in days_by_role
    assert "cutoff_boundary" in days_by_role


# ── prev_boundary always reference_only ──────────────────────────────────

def test_prev_boundary_marked_reference_only_even_when_pit_safe(tmp_path):
    """Critical: prev boundary day's price is reference_only by design — its return
    measures the PRIOR quarter's reaction, not this one."""
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-06-01", "open": 100, "high": 101, "low": 99, "close": 100.5,
            "daily_return": 0.5, "volume": 1000000, "vwap": 100.2, "transactions": 1000,
            "price_timestamp": "2024-06-01T20:00:00-04:00",  # post-close, PIT-safe vs cutoff
            "spy_return": 0.3, "sector_return": 0.4,
            "sector_name": "Tech", "industry_return": 0.45, "industry_name": "Software",
        }],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T16:00:00-04:00",
                out_path=out
            )
    prev = next(d for d in packet["days"] if d.get('boundary_role') == 'prev_boundary')
    assert prev['price_role'] == 'reference_only'


# ── cutoff-day price NULLED when post-cutoff timestamp ───────────────────

def test_cutoff_price_nulled_when_post_cutoff_timestamp(tmp_path):
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-09-15", "open": 100, "high": 101, "low": 99, "close": 100.5,
            "daily_return": 0.5, "volume": 1000000, "vwap": 100.2, "transactions": 1000,
            "price_timestamp": "2024-09-15T20:00:00-04:00",  # POST cutoff (16:00)
            "spy_return": 0.3, "sector_return": 0.4,
            "sector_name": "Tech", "industry_return": 0.45, "industry_name": "Software",
        }],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T16:00:00-04:00",
                out_path=out
            )
    cutoff_day = next(d for d in packet["days"] if d.get('boundary_role') == 'cutoff_boundary')
    assert cutoff_day['price'] is None
    assert cutoff_day['price_role'] == 'reference_only'


def test_cutoff_price_kept_when_pit_safe(tmp_path):
    """Cutoff day price KEPT when bar timestamp is at or before cutoff
    (e.g., early-close session). price_role must be 'ordinary'."""
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-09-15", "open": 100, "high": 101, "low": 99, "close": 100.5,
            "daily_return": 0.5, "volume": 1000000, "vwap": 100.2, "transactions": 1000,
            "price_timestamp": "2024-09-15T13:00:00-04:00",  # 1pm early-close, PIT-safe
            "spy_return": 0.3, "sector_return": 0.4,
            "sector_name": "Tech", "industry_return": 0.45, "industry_name": "Software",
        }],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                # Cutoff at 16:00 — bar at 13:00 is PIT-safe
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T16:00:00-04:00",
                out_path=out
            )
    cutoff_day = next(d for d in packet["days"] if d.get('boundary_role') == 'cutoff_boundary')
    assert cutoff_day['price'] is not None
    assert cutoff_day['price_role'] == 'ordinary'


# ── company-context fallback ─────────────────────────────────────────────

def test_company_context_fallback_when_price_rows_lack_sector(tmp_path):
    """When price rows have no sector_name/industry_name, falls back to
    QUERY_IQ_COMPANY_CONTEXT."""
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-09-15", "open": 100, "high": 101, "low": 99, "close": 100.5,
            "daily_return": 0.5, "volume": 1000000, "vwap": 100.2, "transactions": 1000,
            "price_timestamp": "2024-09-15T13:00:00-04:00",
            "spy_return": 0.3, "sector_return": None, "sector_name": None,
            "industry_return": None, "industry_name": None,
        }],
        "COMPANY_CONTEXT": [{"industry_name": "Fallback-Industry", "sector_name": "Fallback-Sector"}],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T16:00:00-04:00",
                out_path=out
            )
    assert packet["industry"] == "Fallback-Industry"
    assert packet["sector"] == "Fallback-Sector"


# ── synthetic non-trading-day for events ─────────────────────────────────

def test_news_on_non_trading_day_creates_synthetic_block(tmp_path):
    """News on a date not in PRICES creates a synthetic non-trading-day block."""
    mgr = _mock_manager({
        "NEWS": [{
            "created": "2024-07-04T10:00:00-04:00",  # holiday, no price row
            "market_session": "in_market",
            "news_id": "n1", "title": "Holiday news", "channels": '["X"]',
            "authors": "[]", "tags": "[]", "url": "http://x", "updated": None,
            "returns_schedule": None,
            "hourly_stock": 0.5, "session_stock": 0.6, "daily_stock": 0.8,
            "hourly_sector": None, "session_sector": None, "daily_sector": None,
            "hourly_industry": None, "session_industry": None, "daily_industry": None,
            "hourly_macro": None, "session_macro": None, "daily_macro": None,
        }],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T16:00:00-04:00",
                out_path=out
            )
    july_day = next(d for d in packet["days"] if d['date'] == '2024-07-04')
    assert july_day['is_trading_day'] is False
    assert len(july_day['events']) == 1
    assert july_day['events'][0]['type'] == 'news'


# ── forward returns nulled past cutoff ───────────────────────────────────

def test_forward_returns_nulled_when_horizon_past_cutoff():
    """Per _build_forward_returns: any horizon whose end_ts > context_cutoff_ts → null."""
    helper = _mock_session_helper()
    metrics = {
        'hourly_stock': 0.5, 'session_stock': 0.6, 'daily_stock': 0.8,
        'hourly_sector': None, 'session_sector': None, 'daily_sector': None,
        'hourly_industry': None, 'session_industry': None, 'daily_industry': None,
        'hourly_macro': None, 'session_macro': None, 'daily_macro': None,
    }
    # Event at 15:00, cutoff at 16:00 — only hourly window (event+1h=16:00) is PIT-safe.
    # session window (event+4h=19:00) > cutoff → null
    # daily window (event+24h=next day 15:00) > cutoff → null
    fr = iq._build_forward_returns(
        "2024-09-15T15:00:00-04:00", "in_market", None, metrics, helper,
        "2024-09-15T16:00:00-04:00"
    )
    assert fr['hourly'] is not None
    assert fr['session'] is None
    assert fr['daily'] is None


# ── event sort order: timestamp before date-only, then type order ───────

def test_event_sort_order(tmp_path):
    """Within a day, events sorted: timestamp before date-only, then by created
    timestamp, then by type (filing→news→dividend→split)."""
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-07-01",
            "open": 100, "high": 101, "low": 99, "close": 100.5,
            "daily_return": 0.5, "volume": 1000000, "vwap": 100.2, "transactions": 1000,
            "price_timestamp": "2024-07-01T16:00:00-04:00",
            "spy_return": 0.3, "sector_return": 0.4,
            "sector_name": "Tech", "industry_return": 0.45, "industry_name": "Software",
        }],
        "NEWS": [{
            "created": "2024-07-01T11:00:00-04:00",
            "market_session": "in_market",
            "news_id": "n1", "title": "News", "channels": "[]",
            "authors": "[]", "tags": "[]", "url": "http://x", "updated": None,
            "returns_schedule": None,
            "hourly_stock": 0.1, "session_stock": 0.2, "daily_stock": 0.3,
            "hourly_sector": None, "session_sector": None, "daily_sector": None,
            "hourly_industry": None, "session_industry": None, "daily_industry": None,
            "hourly_macro": None, "session_macro": None, "daily_macro": None,
        }],
        "FILINGS": [{
            "created": "2024-07-01T10:00:00-04:00",
            "market_session": "in_market", "form_type": "10-Q",
            "accession": "0001234567-24-000001", "report_id": "r1",
            "description": "Quarterly Report", "items": "[]", "exhibits": "{}",
            "period_of_report": "2024-06-30", "is_amendment": False,
            "xbrl_status": "complete", "primary_doc_url": None, "link_to_txt": None,
            "link_to_html": None, "link_to_filing_details": None,
            "returns_schedule": None,
            "section_names": [], "has_filing_text": False, "financial_statement_count": 0,
            "hourly_stock": 0.1, "session_stock": 0.2, "daily_stock": 0.3,
            "hourly_sector": None, "session_sector": None, "daily_sector": None,
            "hourly_industry": None, "session_industry": None, "daily_industry": None,
            "hourly_macro": None, "session_macro": None, "daily_macro": None,
        }],
        "DIVIDENDS": [{
            "dividend_id": "d1", "declaration_date": "2024-07-01",
            "ex_dividend_date": "2024-07-15", "cash_amount": 0.5,
            "currency": "USD", "frequency": "quarterly", "dividend_type": "regular",
            "pay_date": "2024-08-01", "record_date": "2024-07-22",
        }],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T18:00:00-04:00",
                out_path=out
            )
    july_1 = next(d for d in packet["days"] if d['date'] == '2024-07-01')
    types_order = [e['type'] for e in july_1['events']]
    # Filing (10:00) → News (11:00) → Dividend (date-only, last)
    assert types_order == ['filing', 'news', 'dividend']


# ── significance + gap day ───────────────────────────────────────────────

def test_significant_move_marks_day(tmp_path):
    """abs(adj_return) >= 2.0 → is_significant=True. No news/filings → is_gap_day=True."""
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-07-15",
            "open": 100, "high": 105, "low": 95, "close": 105,
            "daily_return": 5.0, "volume": 5000000, "vwap": 102, "transactions": 5000,
            "price_timestamp": "2024-07-15T16:00:00-04:00",
            "spy_return": 0.5, "sector_return": 1.0,
            "sector_name": "Tech", "industry_return": 1.5, "industry_name": "Software",
        }],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T18:00:00-04:00",
                out_path=out
            )
    july_15 = next(d for d in packet["days"] if d['date'] == '2024-07-15')
    assert july_15['is_significant'] is True
    assert july_15['is_gap_day'] is True  # no news/filings → gap day


# ── summary count correctness ────────────────────────────────────────────

def test_summary_counts_correct(tmp_path):
    mgr = _mock_manager({
        "PRICES": [{
            "date": "2024-07-01",
            "open": 100, "high": 101, "low": 99, "close": 100.5,
            "daily_return": 0.5, "volume": 1000000, "vwap": 100.2, "transactions": 1000,
            "price_timestamp": "2024-07-01T16:00:00-04:00",
            "spy_return": 0.3, "sector_return": 0.4,
            "sector_name": "Tech", "industry_return": 0.45, "industry_name": "Software",
        }],
        "NEWS": [
            {"created": "2024-07-01T10:00:00-04:00", "market_session": "in_market",
             "news_id": "n1", "title": "T1", "channels": "[]", "authors": "[]",
             "tags": "[]", "url": None, "updated": None, "returns_schedule": None,
             "hourly_stock": None, "session_stock": None, "daily_stock": None,
             "hourly_sector": None, "session_sector": None, "daily_sector": None,
             "hourly_industry": None, "session_industry": None, "daily_industry": None,
             "hourly_macro": None, "session_macro": None, "daily_macro": None},
            {"created": "2024-07-02T10:00:00-04:00", "market_session": "in_market",
             "news_id": "n2", "title": "T2", "channels": "[]", "authors": "[]",
             "tags": "[]", "url": None, "updated": None, "returns_schedule": None,
             "hourly_stock": None, "session_stock": None, "daily_stock": None,
             "hourly_sector": None, "session_sector": None, "daily_sector": None,
             "hourly_industry": None, "session_industry": None, "daily_industry": None,
             "hourly_macro": None, "session_macro": None, "daily_macro": None},
        ],
    })
    with patch("scripts.earnings.builders.inter_quarter_context.get_manager", return_value=mgr):
        with patch("utils.market_session.MarketSessionClassifier", return_value=_mock_session_helper()):
            out = str(tmp_path / "iq.json")
            packet = iq.build_inter_quarter_context(
                "FAKE", "2024-06-01T16:00:00-04:00", "2024-09-15T18:00:00-04:00",
                out_path=out
            )
    s = packet["summary"]
    assert s["total_news"] == 2
    assert s["total_filings"] == 0


# ── render_inter_quarter_text branch coverage ────────────────────────────

def _minimal_packet(days, **kw):
    p = {
        "ticker": "FAKE", "industry": "Software", "sector": "Tech",
        "prev_8k_ts": "2024-06-01T16:00:00-04:00",
        "context_cutoff_ts": "2024-09-15T16:00:00-04:00",
        "days": days,
        "summary": {
            "trading_days_ordinary": kw.get("td_ord", 0),
            "boundary_days_rendered": kw.get("bd_rendered", 0),
            "total_news": kw.get("news", 0),
            "total_filings": kw.get("filings", 0),
            "total_dividends": kw.get("dividends", 0),
            "total_splits": kw.get("splits", 0),
            "significant_move_days": kw.get("sig", 0),
            "gap_days": kw.get("gap", 0),
        },
    }
    return p


def _ord_day(date, **kw):
    return {
        'date': date, 'is_trading_day': True, 'boundary_role': None,
        'price_role': 'ordinary',
        'price': kw.get('price', {'open': 100, 'high': 101, 'low': 99, 'close': 100.5,
                                    'daily_return': 0.5, 'volume': 1000000, 'vwap': 100.2,
                                    'transactions': 1000, 'timestamp': None}),
        'spy_return': kw.get('spy_return', 0.3),
        'sector_return': kw.get('sector_return', 0.4),
        'industry_return': kw.get('industry_return', 0.5),
        'adj_return': kw.get('adj_return', 0.2),
        'is_significant': kw.get('is_sig', False),
        'is_gap_day': kw.get('is_gap', False),
        'events': kw.get('events', []),
    }


def test_render_boundary_branch():
    days = [
        {**_ord_day('2024-06-01'), 'boundary_role': 'prev_boundary',
         'price_role': 'reference_only'},
        {**_ord_day('2024-09-15'), 'boundary_role': 'cutoff_boundary'},
    ]
    text = iq.render_inter_quarter_text(_minimal_packet(days, bd_rendered=2))
    assert 'boundary day after previous earnings' in text
    assert 'cutoff boundary' in text


def test_render_ordinary_branch():
    days = [_ord_day('2024-07-01')]
    text = iq.render_inter_quarter_text(_minimal_packet(days, td_ord=1))
    assert '2024-07-01' in text
    assert 'open=100' in text


def test_render_gap_branch():
    days = [_ord_day('2024-07-15', is_sig=True, is_gap=True, adj_return=2.5)]
    text = iq.render_inter_quarter_text(_minimal_packet(days, sig=1, gap=1, td_ord=1))
    assert '***' in text
    assert 'GAP' in text
    assert '(no news, no filings)' in text


def test_render_news_event_branch():
    news_ev = {
        'event_ref': 'news:n1', 'type': 'news', 'available_precision': 'timestamp',
        'created': '2024-07-01T11:00:00-04:00', 'market_session': 'in_market',
        'title': 'Big news', 'channels': ['X'],
        'forward_returns': None,
    }
    days = [_ord_day('2024-07-01', events=[news_ev])]
    text = iq.render_inter_quarter_text(_minimal_packet(days, news=1, td_ord=1))
    assert 'news:n1' in text
    assert 'Big news' in text


def test_render_filing_event_branch():
    fil_ev = {
        'event_ref': 'report:0001-01', 'type': 'filing',
        'available_precision': 'timestamp',
        'created': '2024-07-01T10:00:00-04:00', 'market_session': 'in_market',
        'form_type': '10-Q', 'accession': '0001-01',
        'period_of_report': '2024-06-30', 'is_amendment': False,
        'description': 'Quarterly', 'items': [], 'exhibit_keys': ['EX-99.1'],
        'section_names': ['Section A'],
        'forward_returns': {},
    }
    days = [_ord_day('2024-07-01', events=[fil_ev])]
    text = iq.render_inter_quarter_text(_minimal_packet(days, filings=1, td_ord=1))
    assert 'report:0001-01' in text
    assert '[10-Q]' in text
    assert 'accession: 0001-01' in text


def test_render_dividend_event_branch():
    div_ev = {
        'event_ref': 'dividend:d1', 'type': 'dividend',
        'available_precision': 'date',
        'cash_amount': 0.5, 'currency': 'USD', 'frequency': 'quarterly',
        'ex_dividend_date': '2024-07-15', 'pay_date': '2024-08-01',
        'dividend_type': 'regular',
    }
    days = [_ord_day('2024-07-01', events=[div_ev])]
    text = iq.render_inter_quarter_text(_minimal_packet(days, dividends=1, td_ord=1))
    assert 'dividend:d1' in text
    assert 'Dividend declared' in text


def test_render_split_event_branch():
    sp_ev = {
        'event_ref': 'split:s1', 'type': 'split',
        'available_precision': 'date', 'ratio_text': '2:1',
    }
    days = [_ord_day('2024-07-01', events=[sp_ev])]
    text = iq.render_inter_quarter_text(_minimal_packet(days, splits=1, td_ord=1))
    assert 'split:s1' in text
    assert 'Split effective: 2:1' in text
