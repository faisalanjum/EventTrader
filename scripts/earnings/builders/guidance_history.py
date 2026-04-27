#!/usr/bin/env python3
"""Guidance history builder — orchestration side.

Owns:
  - QUERY_GUIDANCE_HISTORY, QUERY_GUIDANCE_HISTORY_PIT
  - _SOURCE_PRIORITY (8k > transcript > 10q > 10k > news)
  - _extract_given_day, _normalize_qualitative, resolve_unit_groups
  - _format_value (numeric/qualitative formatter)
  - render_guidance_text(packet) -> str
  - build_guidance_history(ticker, pit=None, out_path=None) -> packet dict
  - _run_v2_regression_tests() -> bool   (CLI --test target, exercises
    _format_value + resolve_unit_groups)

Re-exported from scripts.earnings.builders.warmup_cache for back-compat.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from ._paths import ensure_legacy_paths
ensure_legacy_paths()

from neograph.Neo4jConnection import get_manager


# ---------------------------------------------------------------------------
# Guidance History — all GuidanceUpdate nodes for a ticker
# Two variants: full history and PIT-filtered
# NOTE: explicit AS aliases required — Neo4j Python driver returns
# 'gu.basis_norm' not 'basis_norm' for unaliased dotted property access.
# ---------------------------------------------------------------------------
QUERY_GUIDANCE_HISTORY = """
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(concept:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(member:Member)
RETURN g.label AS metric, g.id AS metric_id,
       gu.basis_norm AS basis_norm, gu.segment AS segment,
       gu.segment_slug AS segment_slug,
       gu.period_scope AS period_scope,
       gu.canonical_unit AS canonical_unit, gu.time_type AS time_type,
       gu.fiscal_year AS fiscal_year, gu.fiscal_quarter AS fiscal_quarter,
       gu.given_date AS given_date, gu.low AS low, gu.mid AS mid,
       gu.high AS high,
       gu.source_type AS source_type, gu.derivation AS derivation,
       gu.qualitative AS qualitative, gu.conditions AS conditions,
       gu.evhash16 AS evhash16,
       gp.start_date AS period_start, gp.end_date AS period_end,
       concept.qname AS xbrl_qname,
       collect(DISTINCT member.qname) AS member_qnames
ORDER BY g.label, gu.basis_norm, gu.segment_slug, gu.period_scope,
         gu.canonical_unit, gu.time_type, gu.given_date
"""

QUERY_GUIDANCE_HISTORY_PIT = """
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE datetime(gu.given_date) <= datetime($pit)
MATCH (gu)-[:UPDATES]->(g:Guidance)
MATCH (gu)-[:HAS_PERIOD]->(gp:GuidancePeriod)
OPTIONAL MATCH (gu)-[:MAPS_TO_CONCEPT]->(concept:Concept)
OPTIONAL MATCH (gu)-[:MAPS_TO_MEMBER]->(member:Member)
RETURN g.label AS metric, g.id AS metric_id,
       gu.basis_norm AS basis_norm, gu.segment AS segment,
       gu.segment_slug AS segment_slug,
       gu.period_scope AS period_scope,
       gu.canonical_unit AS canonical_unit, gu.time_type AS time_type,
       gu.fiscal_year AS fiscal_year, gu.fiscal_quarter AS fiscal_quarter,
       gu.given_date AS given_date, gu.low AS low, gu.mid AS mid,
       gu.high AS high,
       gu.source_type AS source_type, gu.derivation AS derivation,
       gu.qualitative AS qualitative, gu.conditions AS conditions,
       gu.evhash16 AS evhash16,
       gp.start_date AS period_start, gp.end_date AS period_end,
       concept.qname AS xbrl_qname,
       collect(DISTINCT member.qname) AS member_qnames
ORDER BY g.label, gu.basis_norm, gu.segment_slug, gu.period_scope,
         gu.canonical_unit, gu.time_type, gu.given_date
"""

# Source priority for deterministic merge ordering: 8k > transcript > 10q > 10k > news
_SOURCE_PRIORITY = {'8k': 0, 'transcript': 1, '10q': 2, '10k': 3, 'news': 4}


def _extract_given_day(ts):
    """Extract calendar date string from ISO timestamp."""
    return str(ts)[:10] if ts else None


def _normalize_qualitative(q):
    """Normalize qualitative string for collapse comparison.

    Handles verified real-world variants: 'low single-digit' vs 'low-single-digits',
    'flat to 3%' vs 'Flat to 3%'. Null treated as empty string.
    """
    s = (q or "").lower().strip()
    s = s.replace('-', ' ')
    words = s.split()  # also collapses multiple spaces
    if words and len(words[-1]) > 1 and words[-1].endswith('s'):
        words[-1] = words[-1][:-1]
    return ' '.join(words)


def resolve_unit_groups(rows):
    """For each base series (5D key without unit), if exactly one non-unknown
    canonical_unit exists, remap all 'unknown' entries to that unit.
    Prevents false series splits from extraction quality gaps."""

    base_units = {}  # (metric_id, basis, seg_slug, scope, tt) → set of non-unknown units
    for r in rows:
        base = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                r['period_scope'], r['time_type'])
        if r['canonical_unit'] != 'unknown':
            base_units.setdefault(base, set()).add(r['canonical_unit'])

    for r in rows:
        if r['canonical_unit'] == 'unknown':
            base = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                    r['period_scope'], r['time_type'])
            real_units = base_units.get(base, set())
            if len(real_units) == 1:
                r['resolved_unit'] = next(iter(real_units))
            else:
                r['resolved_unit'] = 'unknown'
        else:
            r['resolved_unit'] = r['canonical_unit']

    return rows


def _format_value(low, mid, high, unit, qualitative, derivation):
    """Format numeric/qualitative guidance value for rendered text."""
    is_numeric = (low is not None or mid is not None or high is not None)
    if not is_numeric:
        return qualitative or '(qualitative missing)'

    def _fmt_num(v, u):
        if v is None:
            return '?'
        if u == 'm_usd':
            if abs(v) >= 1000:
                return f'${v / 1000:g}B'
            return f'${v:g}M'
        elif u == 'usd':
            return f'${v:g}'
        elif u == 'percent':
            return f'{v:g}%'
        elif u == 'basis_points':
            return f'{v:+g} bps' if v != 0 else '0 bps'
        elif u == 'percent_yoy':
            return f'{v:g}% YoY'
        elif u == 'percent_points':
            return f'{v:g} pp'
        elif u == 'x':
            return f'{v:g}x'
        else:
            return f'{v:g}'

    # Point: all three equal or only mid
    if low == mid == high and mid is not None:
        return _fmt_num(mid, unit)
    if low is None and high is None and mid is not None:
        return f'~{_fmt_num(mid, unit)}'

    # Range — suffix only on high value
    if low is not None and high is not None:
        hi_s = _fmt_num(high, unit)
        # Strip unit suffix from lo for clean ranges (e.g., "$345-$355M" not "$345M-$355M")
        if unit == 'm_usd':
            lo_b, hi_b = abs(low) >= 1000, abs(high) >= 1000
            if lo_b and hi_b:
                lo_s = f'${low / 1000:g}'
            elif not lo_b and not hi_b:
                lo_s = f'${low:g}'
            else:
                lo_s = _fmt_num(low, unit)  # mixed scales — keep both suffixes
        elif unit == 'usd':
            lo_s = f'${low:g}'
        elif unit in ('percent', 'percent_yoy', 'percent_points'):
            lo_s = f'{low:g}'
        elif unit == 'basis_points':
            lo_s = f'{low:+g}' if low != 0 else '0'
        elif unit == 'x':
            lo_s = f'{low:g}'
        else:
            lo_s = f'{low:g}'
        # Use "to" when either value is negative or basis_points
        if low < 0 or high < 0 or unit == 'basis_points':
            return f'{lo_s} to {hi_s}'
        return f'{lo_s}-{hi_s}'

    # Floor/ceiling (only one bound)
    if low is not None:
        return f'>={_fmt_num(low, unit)}'
    if high is not None:
        return f'<={_fmt_num(high, unit)}'
    return f'~{_fmt_num(mid, unit)}'


def render_guidance_text(packet):
    """Render guidance_history.v1 packet to planner-readable text."""
    ticker = packet['ticker']
    series = packet['series']
    summary = packet['summary']

    if not series:
        return f'=== GUIDANCE HISTORY: {ticker} ===\n(no guidance data available)'

    pit_str = packet.get('pit')
    header_parts = [f'{summary["total_series"]} series',
                    f'{summary["total_updates_collapsed"]} events']
    if pit_str:
        pit_day = _extract_given_day(pit_str)
        header_parts.append(f'cutoff {pit_day}')
    header = f'=== GUIDANCE HISTORY: {ticker} ({", ".join(header_parts)}) ==='

    lines = [header, '']
    for s in series:
        # Series header with simplification rules
        parts = [s['period_scope']]
        if s['resolved_unit'] and s['resolved_unit'] != 'unknown':
            parts.append(s['resolved_unit'])
        if s['basis_norm'] and s['basis_norm'] != 'unknown':
            parts.append(f'{s["basis_norm"]} basis')
        if s['segment'] and s['segment'] != 'Total':
            parts.append(f'{s["segment"]} segment')
        if s['time_type'] and s['time_type'] != 'duration':
            parts.append(s['time_type'])
        lines.append(f'{s["metric"]} ({", ".join(parts)}):')

        for u in s['updates']:
            # Period label
            fy = u.get('fiscal_year')
            fq = u.get('fiscal_quarter')
            if fq:
                period = f'FY{fy}-Q{fq}'
            else:
                period = f'FY{fy}'

            # Value
            val = _format_value(u.get('low'), u.get('mid'), u.get('high'),
                                s['resolved_unit'], u.get('qualitative'),
                                u.get('derivation'))

            # Sources
            src_str = '+'.join(u.get('sources', []))

            # Build update line
            parts = [f'{u["given_day"]}', f'sources: {src_str}']
            if u.get('derivation'):
                parts.append(u['derivation'])
            cond = u.get('conditions')
            if cond:
                cond_trunc = cond[:100] + '...' if len(cond) > 100 else cond
                parts.append(cond_trunc)
            lines.append(f'  {period}: {val} ({", ".join(parts)})')

        lines.append('')

    return '\n'.join(lines).rstrip()


def build_guidance_history(ticker, pit=None, out_path=None):
    """Assemble canonical guidance_history.v1 for earnings orchestration.

    Steps: query → resolve units → 6D grouping → collapse duplicates → sort → JSON → atomic write.
    Returns: packet dict (guidance_history.v1).
    """
    if out_path is None:
        out_path = f'/tmp/earnings_guidance_{ticker}.json'

    manager = get_manager()
    try:
        # 1. Query
        query = QUERY_GUIDANCE_HISTORY_PIT if pit else QUERY_GUIDANCE_HISTORY
        params = {'ticker': ticker, 'pit': pit} if pit else {'ticker': ticker}
        rows = manager.execute_cypher_query_all(query, params)
        total_raw = len(rows)

        if not rows:
            packet = {
                'schema_version': 'guidance_history.v1',
                'ticker': ticker,
                'pit': pit,
                'series': [],
                'summary': {
                    'total_series': 0,
                    'total_updates_raw': 0,
                    'total_updates_collapsed': 0,
                    'earliest_date': None,
                    'latest_date': None,
                },
                'assembled_at': datetime.now(timezone.utc).isoformat(),
            }
            out_dir = os.path.dirname(out_path) or '.'
            os.makedirs(out_dir, exist_ok=True)
            tmp_path = out_path + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(packet, f, default=str)
            os.replace(tmp_path, out_path)
            return packet

        # 2. Resolve unit groups
        rows = resolve_unit_groups(rows)

        # 3. Group by 6D key
        series_map = defaultdict(list)
        for r in rows:
            key = (r['metric_id'], r['basis_norm'], r['segment_slug'],
                   r['period_scope'], r['resolved_unit'], r['time_type'])
            series_map[key].append(r)

        # 4. For each series: select display segment, collapse duplicates
        all_series = []
        for key, updates in series_map.items():
            metric_id, basis_norm, segment_slug, period_scope, resolved_unit, time_type = key

            # Display segment: most frequent non-null label, tie-break lexicographic
            seg_counter = Counter()
            for u in updates:
                seg = u.get('segment')
                if seg is not None:
                    seg_counter[seg] += 1
            if seg_counter:
                display_segment = sorted(seg_counter.items(),
                                         key=lambda x: (-x[1], x[0]))[0][0]
            else:
                display_segment = segment_slug or 'Total'

            # raw_unit_variants: sorted distinct canonical_unit values
            raw_units = sorted(set(u['canonical_unit'] for u in updates
                                   if u.get('canonical_unit')))

            metric_label = updates[0]['metric']

            # Collapse same-day cross-source duplicates
            collapse_groups = defaultdict(list)
            for u in updates:
                given_day = _extract_given_day(u.get('given_date'))
                fy = u.get('fiscal_year')
                fq = u.get('fiscal_quarter')
                low, mid, high = u.get('low'), u.get('mid'), u.get('high')
                is_numeric = (low is not None or mid is not None or high is not None)

                if is_numeric:
                    ckey = (fy, fq, given_day, low, mid, high)
                else:
                    norm_q = _normalize_qualitative(u.get('qualitative'))
                    ckey = ('qual', fy, fq, given_day, norm_q)
                collapse_groups[ckey].append(u)

            collapsed_updates = []
            for ckey, group in collapse_groups.items():
                # Sort by source priority for deterministic primary selection
                group.sort(key=lambda u: _SOURCE_PRIORITY.get(
                    u.get('source_type', ''), 99))

                # Merge sources (sorted by priority)
                sources = sorted(
                    {u['source_type'] for u in group if u.get('source_type')},
                    key=lambda s: _SOURCE_PRIORITY.get(s, 99))

                # Conditions: keep richest (longest non-null)
                conditions = None
                for u in group:
                    c = u.get('conditions')
                    if c and (conditions is None or len(c) > len(conditions)):
                        conditions = c

                # Qualitative: keep richest (longest non-null)
                qualitative = None
                for u in group:
                    q = u.get('qualitative')
                    if q and (qualitative is None or len(q) > len(qualitative)):
                        qualitative = q

                # Derivation from primary source (first by priority)
                derivation = group[0].get('derivation')

                # xbrl_qname: first non-null
                xbrl_qname = None
                for u in group:
                    if u.get('xbrl_qname'):
                        xbrl_qname = u['xbrl_qname']
                        break

                # member_qnames: union all, sorted alphabetically
                all_members = set()
                for u in group:
                    for m in (u.get('member_qnames') or []):
                        if m:
                            all_members.add(m)

                # evhash16: first
                evhash16 = group[0].get('evhash16')

                # given_date_ts: earliest
                timestamps = [str(u['given_date']) for u in group
                              if u.get('given_date')]
                given_date_ts = min(timestamps) if timestamps else None
                given_day = _extract_given_day(given_date_ts)

                # Period dates from primary source
                period_start = str(group[0]['period_start']) if group[0].get('period_start') else None
                period_end = str(group[0]['period_end']) if group[0].get('period_end') else None

                collapsed_updates.append({
                    'fiscal_year': group[0].get('fiscal_year'),
                    'fiscal_quarter': group[0].get('fiscal_quarter'),
                    'given_date_ts': given_date_ts,
                    'given_day': given_day,
                    'low': group[0].get('low'),
                    'mid': group[0].get('mid'),
                    'high': group[0].get('high'),
                    'sources': sources,
                    'derivation': derivation,
                    'qualitative': qualitative,
                    'conditions': conditions,
                    'evhash16': evhash16,
                    'period_start': period_start,
                    'period_end': period_end,
                    'xbrl_qname': xbrl_qname,
                    'member_qnames': sorted(all_members),
                })

            # Sort updates: given_day, fiscal_year, fiscal_quarter
            collapsed_updates.sort(key=lambda u: (
                u.get('given_day') or '',
                u.get('fiscal_year') or 0,
                u.get('fiscal_quarter') or 0,
            ))

            all_series.append({
                'metric': metric_label,
                'metric_id': metric_id,
                'basis_norm': basis_norm,
                'segment': display_segment,
                'segment_slug': segment_slug,
                'period_scope': period_scope,
                'raw_unit_variants': raw_units,
                'resolved_unit': resolved_unit,
                'time_type': time_type,
                'updates': collapsed_updates,
            })

        # 5. Sort series: alphabetical by metric, Total first within same metric_id
        all_series.sort(key=lambda s: (
            s['metric'],
            0 if s['segment_slug'] == 'total' else 1,
            s['segment_slug'],
        ))

        # Compute summary
        all_days = []
        total_collapsed = 0
        for s in all_series:
            total_collapsed += len(s['updates'])
            for u in s['updates']:
                if u.get('given_day'):
                    all_days.append(u['given_day'])

        packet = {
            'schema_version': 'guidance_history.v1',
            'ticker': ticker,
            'pit': pit,
            'series': all_series,
            'summary': {
                'total_series': len(all_series),
                'total_updates_raw': total_raw,
                'total_updates_collapsed': total_collapsed,
                'earliest_date': min(all_days) if all_days else None,
                'latest_date': max(all_days) if all_days else None,
            },
            'assembled_at': datetime.now(timezone.utc).isoformat(),
        }

        # 6-7. Atomic write
        out_dir = os.path.dirname(out_path) or '.'
        os.makedirs(out_dir, exist_ok=True)
        tmp_path = out_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(packet, f, default=str)
        os.replace(tmp_path, out_path)

        return packet
    finally:
        manager.close()


def _run_v2_regression_tests():
    """V2 regression tests for formatting/grouping with corrected canonical_unit values.
    Verifies downstream behavior once V2 resolver produces correct units.
    Run: python3 warmup_cache.py --test"""

    passed = failed = 0
    def check(name, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {name}: expected {expected!r}, got {actual!r}")

    # _format_value: corrected usd metrics (was m_usd in V1)
    check("fmt_asp_usd_point", _format_value(490000, 490000, 490000, 'usd', None, 'point'), '$490000')
    check("fmt_dps_usd_point", _format_value(0.32, 0.32, 0.32, 'usd', None, 'point'), '$0.32')
    check("fmt_eps_usd_range", _format_value(3.2, None, 3.4, 'usd', None, 'explicit'), '$3.2-$3.4')

    # _format_value: corrected count metrics (was m_usd in V1)
    check("fmt_count_point", _format_value(300e6, 300e6, 300e6, 'count', None, 'point'), '3e+08')

    # _format_value: m_usd unchanged
    check("fmt_musd_range", _format_value(94000, None, 98000, 'm_usd', None, 'explicit'), '$94-$98B')
    check("fmt_musd_point", _format_value(2000, 2000, 2000, 'm_usd', None, 'point'), '$2B')

    # _format_value: ratio metrics
    check("fmt_pct", _format_value(42, 42, 42, 'percent', None, 'point'), '42%')
    check("fmt_pct_yoy_range", _format_value(5, None, 7, 'percent_yoy', None, 'explicit'), '5-7% YoY')
    check("fmt_bps", _format_value(50, 50, 50, 'basis_points', None, 'point'), '+50 bps')
    check("fmt_pp", _format_value(1.5, 1.5, 1.5, 'percent_points', None, 'point'), '1.5 pp')
    check("fmt_x", _format_value(2.5, 2.5, 2.5, 'x', None, 'point'), '2.5x')

    # resolve_unit_groups: unknown remap via resolved_unit
    rows = [
        {'metric_id': 'revenue', 'basis_norm': 'gaap', 'segment_slug': 'total',
         'period_scope': 'quarter', 'time_type': 'duration', 'canonical_unit': 'm_usd'},
        {'metric_id': 'revenue', 'basis_norm': 'gaap', 'segment_slug': 'total',
         'period_scope': 'quarter', 'time_type': 'duration', 'canonical_unit': 'unknown'},
    ]
    resolve_unit_groups(rows)
    check("remap_resolved_unit", rows[1]['resolved_unit'], 'm_usd')
    check("remap_known_passthrough", rows[0]['resolved_unit'], 'm_usd')

    # No remap when mixed non-unknown units
    rows2 = [
        {'metric_id': 'mixed', 'basis_norm': 'gaap', 'segment_slug': 'total',
         'period_scope': 'quarter', 'time_type': 'duration', 'canonical_unit': 'm_usd'},
        {'metric_id': 'mixed', 'basis_norm': 'gaap', 'segment_slug': 'total',
         'period_scope': 'quarter', 'time_type': 'duration', 'canonical_unit': 'usd'},
        {'metric_id': 'mixed', 'basis_norm': 'gaap', 'segment_slug': 'total',
         'period_scope': 'quarter', 'time_type': 'duration', 'canonical_unit': 'unknown'},
    ]
    resolve_unit_groups(rows2)
    check("no_remap_mixed", rows2[2]['resolved_unit'], 'unknown')

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    return failed == 0
