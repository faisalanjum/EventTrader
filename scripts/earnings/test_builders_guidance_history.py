"""Mocked unit tests for guidance_history (Stage 2.1)."""
from __future__ import annotations
import json
import os
from unittest.mock import MagicMock, patch
import pytest

from scripts.earnings.builders import guidance_history as gh

pytestmark = pytest.mark.builders


def _mock_manager(rows_by_query):
    """Mock Neo4j manager that routes queries by EXACT identity match against the
    canonical query-constant strings imported from `guidance_history`."""
    m = MagicMock()
    def execute(query, params):
        if query == gh.QUERY_GUIDANCE_HISTORY:
            return rows_by_query.get("LIVE", [])
        if query == gh.QUERY_GUIDANCE_HISTORY_PIT:
            return rows_by_query.get("PIT", [])
        raise AssertionError(f"unexpected query: {query[:120]}")
    m.execute_cypher_query_all.side_effect = execute
    m.close = MagicMock()
    return m


def _row(**kw):
    """Helper: return a guidance-row dict with all required keys, overridable."""
    base = {
        'metric': 'Revenue', 'metric_id': 'revenue',
        'basis_norm': 'gaap', 'segment': 'Total', 'segment_slug': 'total',
        'period_scope': 'quarter', 'canonical_unit': 'm_usd', 'time_type': 'duration',
        'fiscal_year': 2024, 'fiscal_quarter': 3,
        'given_date': '2024-09-15T16:00:00-04:00',
        'low': 100, 'mid': 110, 'high': 120,
        'source_type': '8k', 'derivation': 'explicit',
        'qualitative': None, 'conditions': None,
        'evhash16': 'aaaa1111aaaa1111',
        'period_start': '2024-07-01', 'period_end': '2024-09-30',
        'xbrl_qname': 'us-gaap:Revenues', 'member_qnames': [],
    }
    base.update(kw)
    return base


# ── empty-packet path ───────────────────────────────────────────────────

def test_empty_guidance_returns_empty_packet(tmp_path):
    mgr = _mock_manager({"LIVE": []})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    assert packet["schema_version"] == "guidance_history.v1"
    assert packet["ticker"] == "FAKE"
    assert packet["pit"] is None
    assert packet["series"] == []
    assert packet["summary"]["total_series"] == 0
    assert packet["summary"]["total_updates_raw"] == 0
    mgr.close.assert_called_once()


# ── PIT vs live query selection ─────────────────────────────────────────

def test_pit_query_selected_when_pit_set(tmp_path):
    """When pit is set, build_guidance_history must call manager with QUERY_GUIDANCE_HISTORY_PIT
    AND pass the pit value as a param. The mock raises if the wrong query string is used."""
    mgr = _mock_manager({"PIT": []})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        gh.build_guidance_history("FAKE", pit="2024-09-15T16:00:00-04:00", out_path=out)
    # The mock returns from PIT bucket → if LIVE query was used, it'd return [] from LIVE
    # bucket too, which we don't populate; assertion is the lack of AssertionError from
    # the side_effect dispatcher (which raises on unexpected query).
    args_used = [c.args[0] for c in mgr.execute_cypher_query_all.call_args_list]
    assert gh.QUERY_GUIDANCE_HISTORY_PIT in args_used
    assert gh.QUERY_GUIDANCE_HISTORY not in args_used
    params_used = [c.args[1] for c in mgr.execute_cypher_query_all.call_args_list]
    assert params_used[0]["pit"] == "2024-09-15T16:00:00-04:00"


def test_live_query_selected_when_pit_none(tmp_path):
    mgr = _mock_manager({"LIVE": []})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        gh.build_guidance_history("FAKE", pit=None, out_path=out)
    args_used = [c.args[0] for c in mgr.execute_cypher_query_all.call_args_list]
    assert gh.QUERY_GUIDANCE_HISTORY in args_used
    assert gh.QUERY_GUIDANCE_HISTORY_PIT not in args_used


# ── resolve_unit_groups ─────────────────────────────────────────────────

def test_resolve_unit_groups_unknown_remap_one_real():
    rows = [
        _row(canonical_unit='m_usd'),
        _row(canonical_unit='unknown'),
    ]
    gh.resolve_unit_groups(rows)
    assert rows[0]['resolved_unit'] == 'm_usd'
    assert rows[1]['resolved_unit'] == 'm_usd'  # remapped


def test_resolve_unit_groups_no_remap_mixed():
    rows = [
        _row(canonical_unit='m_usd'),
        _row(canonical_unit='usd'),
        _row(canonical_unit='unknown'),
    ]
    gh.resolve_unit_groups(rows)
    assert rows[2]['resolved_unit'] == 'unknown'


# ── numeric duplicate collapse ──────────────────────────────────────────

def test_numeric_duplicate_collapse(tmp_path):
    """Two rows with same (fy, fq, day, low, mid, high) collapse into one update."""
    rows = [
        _row(source_type='8k', given_date='2024-09-15T16:00:00-04:00'),
        _row(source_type='transcript', given_date='2024-09-15T17:00:00-04:00'),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    assert packet["summary"]["total_updates_raw"] == 2
    assert packet["summary"]["total_updates_collapsed"] == 1


# ── qualitative duplicate collapse ──────────────────────────────────────

def test_qualitative_duplicate_collapse_after_normalize(tmp_path):
    """Same-day qualitative rows with normalized-equal text collapse to one."""
    rows = [
        _row(low=None, mid=None, high=None, qualitative='Low single-digit',
             source_type='8k', given_date='2024-09-15T16:00:00-04:00'),
        _row(low=None, mid=None, high=None, qualitative='low-single-digits',
             source_type='transcript', given_date='2024-09-15T17:00:00-04:00'),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    assert packet["summary"]["total_updates_collapsed"] == 1


# ── source priority ordering ────────────────────────────────────────────

def test_sources_sorted_by_priority(tmp_path):
    """Merged sources list orders by 8k > transcript > 10q > 10k > news."""
    rows = [
        _row(source_type='news', given_date='2024-09-15T15:00:00-04:00'),
        _row(source_type='8k', given_date='2024-09-15T16:00:00-04:00'),
        _row(source_type='transcript', given_date='2024-09-15T17:00:00-04:00'),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    sources = packet["series"][0]["updates"][0]["sources"]
    assert sources == ['8k', 'transcript', 'news']


# ── richest conditions selection (cross-source) ─────────────────────────

def test_richest_conditions_cross_source(tmp_path):
    """Across 8-K + transcript + 10-Q rows in the same collapse group, longest
    non-null conditions value wins."""
    rows = [
        _row(source_type='8k', conditions='short'),
        _row(source_type='transcript', conditions='this is a much longer conditions string'),
        _row(source_type='10q', conditions='medium-len'),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    upd = packet["series"][0]["updates"][0]
    assert upd["conditions"] == 'this is a much longer conditions string'


# ── richest qualitative selection (cross-source) ────────────────────────

def test_richest_qualitative_cross_source(tmp_path):
    """Across multiple sources, longest non-null qualitative wins (numeric path active)."""
    rows = [
        _row(source_type='8k', qualitative='ok'),
        _row(source_type='transcript', qualitative='this is the longest one of three'),
        _row(source_type='10q', qualitative='medium answer'),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    upd = packet["series"][0]["updates"][0]
    assert upd["qualitative"] == 'this is the longest one of three'


# ── member_qnames union + sort (cross-source) ──────────────────────────

def test_member_qnames_union_and_sorted_cross_source(tmp_path):
    rows = [
        _row(source_type='8k', member_qnames=['us-gaap:NorthAmerica', 'us-gaap:Total']),
        _row(source_type='transcript', member_qnames=['us-gaap:Europe']),
        _row(source_type='10q', member_qnames=['us-gaap:Asia']),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    members = packet["series"][0]["updates"][0]["member_qnames"]
    assert members == sorted({'us-gaap:NorthAmerica', 'us-gaap:Total',
                              'us-gaap:Europe', 'us-gaap:Asia'})


# ── series sort ─────────────────────────────────────────────────────────

def test_series_sort_alphabetical_with_total_first(tmp_path):
    """Series sorted alphabetical by metric, then 'total' before other segment_slug."""
    rows = [
        _row(metric='Revenue', metric_id='revenue', segment_slug='north_america',
             segment='North America'),
        _row(metric='EPS', metric_id='eps', segment_slug='total', segment='Total'),
        _row(metric='Revenue', metric_id='revenue', segment_slug='total', segment='Total'),
    ]
    mgr = _mock_manager({"LIVE": rows})
    with patch("scripts.earnings.builders.guidance_history.get_manager", return_value=mgr):
        out = str(tmp_path / "g.json")
        packet = gh.build_guidance_history("FAKE", pit=None, out_path=out)
    metrics = [(s["metric"], s["segment_slug"]) for s in packet["series"]]
    assert metrics == [
        ('EPS', 'total'),
        ('Revenue', 'total'),            # total first within same metric
        ('Revenue', 'north_america'),
    ]


# ── _format_value edge cases ────────────────────────────────────────────

def test_format_value_negative_range_uses_to():
    assert gh._format_value(-3, None, 5, 'percent', None, 'explicit') == '-3 to 5%'


def test_format_value_basis_points_uses_to():
    assert gh._format_value(50, None, 100, 'basis_points', None, 'explicit') == '+50 to +100 bps'


def test_format_value_m_usd_unit_suffix_stripped_in_range():
    """Range "$345-$355M" not "$345M-$355M" — low's unit suffix stripped when same scale."""
    assert gh._format_value(345, None, 355, 'm_usd', None, 'explicit') == '$345-$355M'


# ── render_guidance_text — header with cutoff ───────────────────────────

def test_render_header_with_cutoff_when_pit_set():
    packet = {
        'ticker': 'FAKE',
        'pit': '2024-09-15T16:00:00-04:00',
        'series': [],
        'summary': {'total_series': 0, 'total_updates_collapsed': 0},
    }
    text = gh.render_guidance_text(packet)
    # Empty path bypasses the header builder; force a series in
    packet['series'] = [{
        'metric': 'Revenue', 'metric_id': 'revenue',
        'basis_norm': 'gaap', 'segment': 'Total', 'segment_slug': 'total',
        'period_scope': 'quarter', 'resolved_unit': 'm_usd',
        'time_type': 'duration', 'updates': [],
    }]
    packet['summary'] = {'total_series': 1, 'total_updates_collapsed': 0}
    text = gh.render_guidance_text(packet)
    assert 'cutoff 2024-09-15' in text


# ── render_guidance_text — conditions truncation ────────────────────────

def test_render_conditions_truncation_above_100_chars():
    long_cond = 'x' * 150
    packet = {
        'ticker': 'FAKE',
        'pit': None,
        'series': [{
            'metric': 'Revenue', 'metric_id': 'revenue',
            'basis_norm': 'gaap', 'segment': 'Total', 'segment_slug': 'total',
            'period_scope': 'quarter', 'resolved_unit': 'm_usd',
            'time_type': 'duration',
            'updates': [{
                'fiscal_year': 2024, 'fiscal_quarter': 3,
                'given_day': '2024-09-15',
                'low': 100, 'mid': 110, 'high': 120,
                'sources': ['8k'],
                'derivation': 'explicit',
                'qualitative': None,
                'conditions': long_cond,
            }],
        }],
        'summary': {'total_series': 1, 'total_updates_collapsed': 1},
    }
    text = gh.render_guidance_text(packet)
    # The truncated conditions piece is exactly 100 chars + '...' (per cond[:100] + '...' rule)
    assert ('x' * 100 + '...') in text
    # And the full 150-char untruncated string must NOT appear in the rendered text
    assert ('x' * 150) not in text


# ── _run_v2_regression_tests in isolation ───────────────────────────────

def test_inline_regression_tests_pass_in_new_module():
    """Stage 2.1 CRITICAL: the inline 14-check suite must still return True
    when invoked from the new guidance_history module — proves _format_value
    and resolve_unit_groups references resolve in the new namespace per §10.4."""
    assert gh._run_v2_regression_tests() is True
