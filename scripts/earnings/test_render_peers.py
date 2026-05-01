"""U22 renderer tests for §7 Sector Peer Earnings (Option D per-peer block).

Tests the structural contract of `_render_peer_earnings`:
- section header + Data notes line
- per-peer block (header decorations, 3×3 matrix, headlines)
- defensive `_signed_pct` and `_sub` helpers
- existing guards ([BUILDER ERROR: ...] and [NO PEER EARNINGS IN WINDOW])

Per-fixture golden byte-equality is NOT duplicated here — already covered by
the existing parametrized `test_section_byte_equality` in
`test_renderer_golden_sections.py:54-56` over (9 sections × 4 fixtures).
"""
from __future__ import annotations

import math

import pytest

from scripts.earnings.renderer.peers import (
    _render_peer_earnings,
    _signed_pct,
    _sub,
    _month_abbr,
)

pytestmark = pytest.mark.builders


# ─── Fixtures ─────────────────────────────────────────────────────────


def _peer(**overrides):
    """Default peer dict shape (all 9 cells + new fields populated)."""
    base = {
        'ticker': 'NVDA',
        'name': 'NVIDIA CORP',
        'mkt_cap': '3,179,780,000,000',
        'filed': '2023-11-21T16:22:00-05:00',
        'accession': '0001045810-23-000225',
        'period_of_report': '2023-11-21',
        'market_session': 'post_market',
        'fy_end_month': '1',
        'is_amendment': False,
        'accession_periodic': None,
        'form_type_periodic': None,
        'daily_stock_pct': -2.46,
        'session_stock_pct': 3.99,
        'hourly_stock_pct': 3.18,
        'daily_sector_pct': 0.45,
        'session_sector_pct': 1.68,
        'hourly_sector_pct': 0.48,
        'daily_macro_pct': 0.38,
        'session_macro_pct': 0.74,
        'hourly_macro_pct': 0.16,
        'best_sector_pct': 2.70,
        'best_macro_pct': 3.25,
        'context_horizon': 'daily',
        'headlines': [],
        'headline_coverage': 'none',
    }
    base.update(overrides)
    return base


def _bundle(peers=None, gaps=None, target_fye=10, builder_error=None):
    """Build a minimal bundle for rendering."""
    summary = {'total_peers': len(peers or []), 'total_filings': len(peers or [])}
    if gaps:
        summary['gaps'] = gaps
    pkt = {
        'peers': peers or [],
        'industry': 'Semiconductors',
        'window_start': '2023-10-23',
        'effective_cutoff_ts': '2023-12-07T16:18:51-05:00',
        'summary': summary,
    }
    bundle = {
        'peer_earnings_snapshot': pkt,
        'quarter_info': {'fye_month': target_fye},
        'builder_errors': {'peer_earnings_snapshot': builder_error} if builder_error else {},
    }
    return bundle


# ─── _signed_pct helper ───────────────────────────────────────────────


def test_signed_percent_formatter_for_positive():
    assert _signed_pct(2.46) == "+2.46%"


def test_signed_percent_formatter_for_negative():
    assert _signed_pct(-2.46) == "-2.46%"


def test_signed_percent_formatter_for_zero():
    assert _signed_pct(0.0) == "+0.00%"


def test_signed_percent_formatter_for_none():
    assert _signed_pct(None) == "—"


def test_signed_percent_formatter_for_string_returns_dash():
    """Defensive: stray string should not crash render."""
    assert _signed_pct("not-a-number") == "—"


def test_signed_percent_formatter_for_nan_returns_dash():
    assert _signed_pct(float("nan")) == "—"


def test_signed_percent_formatter_for_dict_returns_dash():
    assert _signed_pct({"some": "dict"}) == "—"


def test_signed_percent_formatter_for_int_works():
    """Integer should also round-trip cleanly."""
    assert _signed_pct(5) == "+5.00%"


# ─── _sub helper ──────────────────────────────────────────────────────


def test_sub_subtracts_correctly():
    assert math.isclose(_sub(-2.46, 0.38), -2.84, abs_tol=0.001)


def test_sub_returns_none_for_string_inputs():
    assert _sub("not-a-number", 0.38) is None


def test_sub_returns_none_for_either_none():
    assert _sub(None, 0.38) is None
    assert _sub(-2.46, None) is None


# ─── _month_abbr helper ───────────────────────────────────────────────


def test_month_abbr_for_valid_int():
    assert _month_abbr(10) == "Oct"


def test_month_abbr_for_string_int():
    assert _month_abbr("1") == "Jan"


def test_month_abbr_for_none():
    assert _month_abbr(None) is None


def test_month_abbr_for_invalid():
    assert _month_abbr("Oct") is None  # full month name not accepted


def test_month_abbr_for_out_of_range():
    assert _month_abbr(13) is None
    assert _month_abbr(0) is None


# ─── Section header + Data notes line ─────────────────────────────────


def test_section_header_format():
    out = _render_peer_earnings(_bundle())
    assert out.startswith("## 7. Sector Peer Earnings & Reactions")
    assert "Industry: Semiconductors" in out
    assert "Window: 2023-10-23 → 2023-12-07" in out
    assert "Peers: 0" in out


def test_data_notes_line_when_summary_gaps_present():
    gaps = [{'type': 'missing_returns_schedule', 'peer_ticker': 'TXN',
             'peer_accession': '0000097476-23-000039'}]
    out = _render_peer_earnings(_bundle(peers=[_peer()], gaps=gaps))
    assert "Data notes: 1 peer(s) with missing returns_schedule: TXN" in out


def test_data_notes_line_omitted_when_no_gaps():
    out = _render_peer_earnings(_bundle(peers=[_peer()]))
    assert "Data notes:" not in out


# ─── Per-peer block header ────────────────────────────────────────────


def test_per_peer_block_header_format():
    out = _render_peer_earnings(_bundle(peers=[_peer()]))
    assert "### NVDA — filed 2023-11-21 (post_market), accession 0001045810-23-000225" in out


def test_per_peer_block_header_with_fy_mismatch_tag():
    """Peer fye=1 (Jan) vs target fye=10 (Oct) → tag rendered."""
    out = _render_peer_earnings(_bundle(peers=[_peer(fy_end_month='1')]))
    assert "(FY ends Jan)" in out


def test_per_peer_block_header_no_fy_tag_when_match():
    """Peer fye=10 (Oct) vs target fye=10 (Oct) → no tag."""
    out = _render_peer_earnings(_bundle(peers=[_peer(fy_end_month='10')]))
    assert "(FY ends" not in out


def test_per_peer_block_header_no_fy_tag_when_target_fye_none():
    """Defensive: target_fye missing → omit tag entirely."""
    out = _render_peer_earnings(_bundle(peers=[_peer(fy_end_month='1')], target_fye=None))
    assert "(FY ends" not in out


def test_per_peer_block_header_no_fy_tag_when_peer_fye_none():
    """Defensive: peer fye missing → omit tag."""
    out = _render_peer_earnings(_bundle(peers=[_peer(fy_end_month=None)]))
    assert "(FY ends" not in out


def test_per_peer_block_header_no_fy_tag_for_unparseable_peer_fye():
    """Defensive: peer fye='Oct' (unparseable as int) → omit tag, don't crash."""
    out = _render_peer_earnings(_bundle(peers=[_peer(fy_end_month='Oct')]))
    assert "(FY ends" not in out


# ─── Periodic line ────────────────────────────────────────────────────


def test_periodic_line_when_accession_periodic_present():
    p = _peer(accession_periodic='0001045810-23-000245', form_type_periodic='10-Q')
    out = _render_peer_earnings(_bundle(peers=[p]))
    assert "Periodic: 0001045810-23-000245 (10-Q)" in out


def test_periodic_line_omitted_when_accession_periodic_null():
    out = _render_peer_earnings(_bundle(peers=[_peer(accession_periodic=None)]))
    assert "Periodic:" not in out


def test_periodic_line_omits_form_tag_when_form_type_null():
    """If accession_periodic is set but form_type_periodic is None, drop the tag."""
    p = _peer(accession_periodic='0001045810-23-000245', form_type_periodic=None)
    out = _render_peer_earnings(_bundle(peers=[p]))
    assert "Periodic: 0001045810-23-000245" in out
    # Check there's no parenthetical form tag immediately after
    assert "0001045810-23-000245 (" not in out


# ─── Amendment marker ─────────────────────────────────────────────────


def test_amendment_marker_when_is_amendment_true():
    out = _render_peer_earnings(_bundle(peers=[_peer(is_amendment=True)]))
    assert "[8-K/A amendment]" in out


def test_amendment_marker_omitted_when_is_amendment_false():
    out = _render_peer_earnings(_bundle(peers=[_peer(is_amendment=False)]))
    assert "[8-K/A amendment]" not in out


def test_amendment_marker_omitted_when_is_amendment_none():
    out = _render_peer_earnings(_bundle(peers=[_peer(is_amendment=None)]))
    assert "[8-K/A amendment]" not in out


# ─── 3×3 matrix ───────────────────────────────────────────────────────


def test_3x3_matrix_three_lines_with_correct_labels():
    out = _render_peer_earnings(_bundle(peers=[_peer()]))
    assert "Stock move:" in out
    assert "Sector-adj:" in out
    assert "Macro-adj:" in out


def test_stock_raw_line_has_no_best_cell():
    """Best cell only on adjusted lines."""
    out = _render_peer_earnings(_bundle(peers=[_peer()]))
    # Find the Stock move line and assert no "Best" on it
    stock_line = next(line for line in out.splitlines() if line.startswith("Stock move:"))
    assert "Best" not in stock_line


def test_sector_adj_line_has_best_cell():
    out = _render_peer_earnings(_bundle(peers=[_peer()]))
    sector_line = next(line for line in out.splitlines() if line.startswith("Sector-adj:"))
    assert "Best" in sector_line


def test_macro_adj_line_has_best_cell():
    out = _render_peer_earnings(_bundle(peers=[_peer()]))
    macro_line = next(line for line in out.splitlines() if line.startswith("Macro-adj:"))
    assert "Best" in macro_line


def test_sector_adj_cell_subtracts_stock_minus_sector():
    """CRITICAL math test: bundle stores RAW; renderer must subtract."""
    p = _peer(daily_stock_pct=-2.46, daily_sector_pct=0.45)
    out = _render_peer_earnings(_bundle(peers=[p]))
    sector_line = next(line for line in out.splitlines() if line.startswith("Sector-adj:"))
    # -2.46 - 0.45 = -2.91
    assert "-2.91%" in sector_line


def test_macro_adj_cell_subtracts_stock_minus_macro():
    """CRITICAL math test: bundle stores RAW SPY; renderer must subtract."""
    p = _peer(daily_stock_pct=-2.46, daily_macro_pct=0.38)
    out = _render_peer_earnings(_bundle(peers=[p]))
    macro_line = next(line for line in out.splitlines() if line.startswith("Macro-adj:"))
    # -2.46 - 0.38 = -2.84
    assert "-2.84%" in macro_line


def test_dash_for_none_stock_cell():
    """When stock cell is None → render '—' for that cell + downstream adj cells."""
    p = _peer(daily_stock_pct=None, daily_sector_pct=0.45, daily_macro_pct=0.38)
    out = _render_peer_earnings(_bundle(peers=[p]))
    stock_line = next(line for line in out.splitlines() if line.startswith("Stock move:"))
    assert "Day —" in stock_line
    # Sector-adj and Macro-adj day cells should also be '—' (None - X = None)
    sector_line = next(line for line in out.splitlines() if line.startswith("Sector-adj:"))
    macro_line = next(line for line in out.splitlines() if line.startswith("Macro-adj:"))
    assert "Day —" in sector_line
    assert "Day —" in macro_line


def test_all_horizons_none_renders_three_dashes_each_line():
    p = _peer(
        daily_stock_pct=None, session_stock_pct=None, hourly_stock_pct=None,
        daily_sector_pct=None, session_sector_pct=None, hourly_sector_pct=None,
        daily_macro_pct=None, session_macro_pct=None, hourly_macro_pct=None,
        best_sector_pct=None, best_macro_pct=None,
    )
    out = _render_peer_earnings(_bundle(peers=[p]))
    # Each of the 3 lines should have 3 dashes ("Day —" + "Sess —" + "Hour —")
    for label in ("Stock move:", "Sector-adj:", "Macro-adj:"):
        line = next(l for l in out.splitlines() if l.startswith(label))
        assert line.count("—") >= 3


# ─── Headlines section ────────────────────────────────────────────────


def test_headline_format_with_bz_id():
    p = _peer(headlines=[
        {'date': '2023-11-21T16:30:00', 'title': 'NVIDIA Q3 EPS Beats',
         'bz_id': '35906540', 'channels': ['Earnings Beats']},
    ])
    out = _render_peer_earnings(_bundle(peers=[p]))
    assert "Headlines:" in out
    assert "- [bz:35906540] 2023-11-21 NVIDIA Q3 EPS Beats" in out


def test_headline_format_without_bz_id_omits_bz_token():
    p = _peer(headlines=[
        {'date': '2023-11-21T16:30:00', 'title': 'Some Headline',
         'bz_id': None, 'channels': []},
    ])
    out = _render_peer_earnings(_bundle(peers=[p]))
    assert "Headlines:" in out
    # No "[bz:" tag should appear in the headline line
    headline_line = next(l for l in out.splitlines() if "Some Headline" in l)
    assert "[bz:" not in headline_line


def test_headlines_section_omitted_when_zero_valid_headlines():
    out = _render_peer_earnings(_bundle(peers=[_peer(headlines=[])]))
    assert "Headlines:" not in out


def test_headlines_section_omitted_when_all_titles_missing():
    p = _peer(headlines=[{'date': '...', 'title': None, 'bz_id': None}])
    out = _render_peer_earnings(_bundle(peers=[p]))
    assert "Headlines:" not in out


def test_headline_with_pipe_in_title_escaped():
    """_iq_cell escapes pipe characters for markdown safety."""
    p = _peer(headlines=[
        {'date': '2023-11-21T00:00:00', 'title': 'Q3 EPS | Beat | Sales',
         'bz_id': '12345'},
    ])
    out = _render_peer_earnings(_bundle(peers=[p]))
    assert "\\|" in out  # pipe escaped


# ─── Guards (preserved) ───────────────────────────────────────────────


def test_no_peers_renders_no_peer_earnings_in_window():
    out = _render_peer_earnings(_bundle(peers=[]))
    assert "[NO PEER EARNINGS IN WINDOW]" in out


def test_builder_error_guard_preserved():
    out = _render_peer_earnings(_bundle(builder_error="Cypher syntax error"))
    assert "[BUILDER ERROR: Cypher syntax error]" in out
    # Should NOT continue to render peer blocks
    assert "Stock move:" not in out


def test_no_data_guard_when_packet_missing():
    bundle = {'peer_earnings_snapshot': None, 'quarter_info': {}, 'builder_errors': {}}
    out = _render_peer_earnings(bundle)
    assert "[NO DATA]" in out


# ─── Peer ordering preserved ──────────────────────────────────────────


def test_peer_iteration_order_preserved():
    """Renderer iterates peers in list order (catalog must match)."""
    peers = [
        _peer(ticker='NVDA'),
        _peer(ticker='QCOM'),
        _peer(ticker='AMD'),
    ]
    out = _render_peer_earnings(_bundle(peers=peers))
    # Find positions of each ticker's H3 header
    pos_nvda = out.find("### NVDA")
    pos_qcom = out.find("### QCOM")
    pos_amd = out.find("### AMD")
    assert pos_nvda < pos_qcom < pos_amd, "peer order broken"
