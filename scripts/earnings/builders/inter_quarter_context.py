#!/usr/bin/env python3
"""Inter-quarter context builder — orchestration side.

Owns:
  - QUERY_IQ_* (6 Cypher queries)
  - JSON / number / time helpers
  - _parse_dt_for_pit (DIFFERENT FUNCTION from peer_earnings_snapshot._parse_dt_for_pit;
    same name, intentionally distinct — see test_parse_dt_for_pit_disambiguation)
  - PIT safety gates (_is_price_pit_safe, _build_forward_returns, _cutoff_boundary_price_role)
  - Render helpers (_best_safe_horizon, _report_summary, _render_*)
  - render_inter_quarter_text(packet) -> str
  - build_inter_quarter_context(ticker, prev_8k_ts, context_cutoff_ts,
                                out_path=None, context_cutoff_reason=None) -> packet dict

Re-exported from scripts.earnings.builders.warmup_cache for back-compat.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from ._paths import ensure_legacy_paths
ensure_legacy_paths()

from neograph.Neo4jConnection import get_manager


# --- Inter-quarter query constants ---

QUERY_IQ_PRICES = """
MATCH (d:Date)-[hp:HAS_PRICE]->(c:Company {ticker: $ticker})
WHERE d.date >= $prev_day AND d.date <= $cutoff_day
OPTIONAL MATCH (d)-[spy:HAS_PRICE]->(idx:MarketIndex {ticker: 'SPY'})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)-[:BELONGS_TO]->(sec:Sector)
OPTIONAL MATCH (d)-[sec_hp:HAS_PRICE]->(sec)
OPTIONAL MATCH (d)-[ind_hp:HAS_PRICE]->(ind)
RETURN d.date AS date,
       hp.open AS open,
       hp.high AS high,
       hp.low AS low,
       hp.close AS close,
       hp.daily_return AS daily_return,
       hp.volume AS volume,
       hp.vwap AS vwap,
       hp.transactions AS transactions,
       hp.timestamp AS price_timestamp,
       spy.daily_return AS spy_return,
       sec_hp.daily_return AS sector_return,
       sec.name AS sector_name,
       ind_hp.daily_return AS industry_return,
       ind.name AS industry_name
ORDER BY d.date
"""

QUERY_IQ_NEWS = """
MATCH (n:News)-[rel:INFLUENCES]->(c:Company {ticker: $ticker})
WHERE datetime(n.created) > datetime($prev_8k_ts)
  AND datetime(n.created) < datetime($context_cutoff_ts)
RETURN n.created AS created,
       n.market_session AS market_session,
       n.id AS news_id,
       n.title AS title,
       n.channels AS channels,
       n.authors AS authors,
       n.tags AS tags,
       n.url AS url,
       n.updated AS updated,
       n.returns_schedule AS returns_schedule,
       rel.hourly_stock AS hourly_stock,
       rel.session_stock AS session_stock,
       rel.daily_stock AS daily_stock,
       rel.hourly_sector AS hourly_sector,
       rel.session_sector AS session_sector,
       rel.daily_sector AS daily_sector,
       rel.hourly_industry AS hourly_industry,
       rel.session_industry AS session_industry,
       rel.daily_industry AS daily_industry,
       rel.hourly_macro AS hourly_macro,
       rel.session_macro AS session_macro,
       rel.daily_macro AS daily_macro
ORDER BY datetime(n.created)
"""

QUERY_IQ_FILINGS = """
MATCH (r:Report)-[pf:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE datetime(r.created) > datetime($prev_8k_ts)
  AND datetime(r.created) < datetime($context_cutoff_ts)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(sec:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_FILING_TEXT]->(ft:FilingTextContent)
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
RETURN r.created AS created,
       r.market_session AS market_session,
       r.formType AS form_type,
       r.accessionNo AS accession,
       r.id AS report_id,
       r.description AS description,
       r.items AS items,
       r.exhibits AS exhibits,
       r.periodOfReport AS period_of_report,
       r.isAmendment AS is_amendment,
       r.xbrl_status AS xbrl_status,
       r.primaryDocumentUrl AS primary_doc_url,
       r.linkToTxt AS link_to_txt,
       r.linkToHtml AS link_to_html,
       r.linkToFilingDetails AS link_to_filing_details,
       r.returns_schedule AS returns_schedule,
       collect(DISTINCT sec.section_name) AS section_names,
       count(DISTINCT ft) > 0 AS has_filing_text,
       count(DISTINCT fs) AS financial_statement_count,
       pf.hourly_stock AS hourly_stock,
       pf.session_stock AS session_stock,
       pf.daily_stock AS daily_stock,
       pf.hourly_sector AS hourly_sector,
       pf.session_sector AS session_sector,
       pf.daily_sector AS daily_sector,
       pf.hourly_industry AS hourly_industry,
       pf.session_industry AS session_industry,
       pf.daily_industry AS daily_industry,
       pf.hourly_macro AS hourly_macro,
       pf.session_macro AS session_macro,
       pf.daily_macro AS daily_macro
ORDER BY datetime(r.created)
"""

QUERY_IQ_DIVIDENDS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_DIVIDEND]->(div:Dividend)
WHERE div.declaration_date > $prev_day
  AND div.declaration_date < $cutoff_day
RETURN div.id AS dividend_id,
       div.declaration_date AS declaration_date,
       div.ex_dividend_date AS ex_dividend_date,
       div.cash_amount AS cash_amount,
       div.currency AS currency,
       div.frequency AS frequency,
       div.dividend_type AS dividend_type,
       div.pay_date AS pay_date,
       div.record_date AS record_date
ORDER BY div.declaration_date
"""

QUERY_IQ_SPLITS = """
MATCH (c:Company {ticker: $ticker})-[:DECLARED_SPLIT]->(sp:Split)
WHERE sp.execution_date > $prev_day
  AND sp.execution_date < $cutoff_day
RETURN sp.id AS split_id,
       sp.execution_date AS execution_date,
       sp.split_from AS split_from,
       sp.split_to AS split_to
ORDER BY sp.execution_date
"""

QUERY_IQ_COMPANY_CONTEXT = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(ind:Industry)
OPTIONAL MATCH (ind)-[:BELONGS_TO]->(sec:Sector)
RETURN ind.name AS industry_name,
       sec.name AS sector_name
"""

# --- Inter-quarter helper functions ---


import re as _re_iqc


# ── U7: related-filings sidecar helpers ─────────────────────────────────────
# Parse SEC 8-K item codes from "Item N.NN[: <label>]" → "N.NN".

_ITEM_CODE_RE = _re_iqc.compile(r"^\s*Item\s+(\d+\.\d+)", _re_iqc.IGNORECASE)


def _parse_item_code(item_str):
    """Return the numeric item code (e.g. '9.01') or None if unparseable."""
    if not item_str or not isinstance(item_str, str):
        return None
    m = _ITEM_CODE_RE.match(item_str.strip())
    return m.group(1) if m else None


def _should_emit_sidecar(form_type, items_codes, exhibits_dict):
    """Return True if this filing should receive a related-filing sidecar.

    Rule:
      - 8-K/A: always include (amendments often carry restated content).
      - 8-K: include UNLESS items == {9.01} AND no exhibits (boilerplate-only).
      - All other forms (10-Q, 10-K, Form 4, SCHEDULE 13D, etc.): skip.
      - Missing/unparseable items on an 8-K: include (don't silently drop).

    `items_codes` is a set of parsed item codes (e.g. {'2.01', '9.01'}).
    `exhibits_dict` is the parsed exhibits map (typically {EX-99.1: url, ...}).
    """
    ft = (form_type or "").strip().upper()
    if ft == "8-K/A":
        return True
    if ft == "8-K":
        if items_codes == {"9.01"} and not exhibits_dict:
            return False
        return True
    return False


# Cypher: fetch sections + ALL exhibits + filing-text fallback for ONE accession.
# Mirrors eight_k_packet's QUERY_4J/4K patterns; broadens to ALL exhibits (not
# just EX-99) per Item 1.01 / 5.02 cases where EX-10 contracts/comp matter.
QUERY_RF_SECTIONS = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_SECTION]->(s:ExtractedSectionContent)
WHERE s.content IS NOT NULL AND s.content <> ''
RETURN s.section_name AS section_name, s.content AS content
ORDER BY s.section_name
"""

QUERY_RF_EXHIBITS = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.content IS NOT NULL AND e.content <> ''
RETURN e.exhibit_number AS exhibit_number, e.content AS content
ORDER BY e.exhibit_number
"""

QUERY_RF_FILING_TEXT = """
MATCH (r:Report {accessionNo: $accession})-[:HAS_FILING_TEXT]->(f:FilingTextContent)
RETURN f.content AS content
"""


def _fetch_related_filing_content(manager, accession):
    """Fetch (sections, exhibits, filing_text) for one accession from Neo4j."""
    sections = manager.execute_cypher_query_all(QUERY_RF_SECTIONS, {"accession": accession}) or []
    exhibits = manager.execute_cypher_query_all(QUERY_RF_EXHIBITS, {"accession": accession}) or []
    ft_rows = manager.execute_cypher_query_all(QUERY_RF_FILING_TEXT, {"accession": accession}) or []
    filing_text = ft_rows[0]["content"] if ft_rows else None
    return sections, exhibits, filing_text


def _render_sidecar_md(meta, sections, exhibits, filing_text):
    """Render a related filing's content as markdown.

    `meta` carries accession/form_type/created/items/etc. for the filing.
    Returns markdown string. Empty result signals 'no useful content' and the
    caller skips writing to disk.
    """
    has_any = bool(sections) or bool(exhibits) or bool(filing_text)
    if not has_any:
        return ""
    lines = []
    items_str = " || ".join(meta.get("items") or []) or "—"
    lines.append(f"# {meta.get('form_type', '?')} — {items_str}")
    lines.append("")
    lines.append(f"**Accession**: {meta.get('accession', '?')}")
    lines.append(f"**Filed**: {meta.get('created', '?')} ({meta.get('market_session') or '—'})")
    lines.append(f"**Period of Report**: {meta.get('period_of_report') or '—'}")
    if meta.get("is_amendment"):
        lines.append("**Amendment**: yes")
    if sections:
        lines.append("\n## Sections\n")
        for s in sections:
            lines.append(f"### {s.get('section_name', '—')}")
            lines.append((s.get("content") or "").strip())
            lines.append("")
    if exhibits:
        lines.append("\n## Exhibits\n")
        for e in exhibits:
            lines.append(f"### {e.get('exhibit_number', '—')}")
            lines.append((e.get("content") or "").strip())
            lines.append("")
    if filing_text and not sections and not exhibits:
        lines.append("\n## Filing Text (fallback)\n")
        lines.append(filing_text.strip())
    return "\n".join(lines).strip() + "\n"


def _atomic_write_text(path, content):
    """Atomic tmp + rename. Caller ensures parent dir exists."""
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, str(path))


def _iq_parse_json_field(raw, fallback=None):
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _norm_ret(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return round(f, 2)


def _fmt_vol(v):
    if v is None:
        return '?'
    if v == int(v):
        return f'{int(v):,}'
    return f'{v:,.2f}'


def _fmt_txn(v):
    if v is None:
        return '?'
    return f'{int(v):,}'


def _safe_adj(a, b):
    if a is None or b is None:
        return None
    return round(a - b, 2)


def _event_ref(event_type, native_id):
    return f'{event_type}:{native_id}'


def _day_from_ts(ts):
    return str(ts)[:10] if ts else None


def _parse_dt_for_pit(ts_str):
    """Parse ISO timestamp to timezone-aware datetime for PIT comparison.

    CRITICAL: Never compare timestamps as strings — timezone offsets (-04:00 vs -05:00)
    make lexicographic comparison unreliable across DST boundaries.

    Handles both standard (-04:00) and compact (-0400) timezone offsets,
    as well as space-separated datetime formats from Polygon price bars.
    """
    s = str(ts_str).strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    # Normalize compact timezone offset: -0400 → -04:00, +0530 → +05:30
    if len(s) >= 5 and s[-5] in ('+', '-') and s[-4:].isdigit():
        s = s[:-2] + ':' + s[-2:]
    return datetime.fromisoformat(s)


def _is_price_pit_safe(price_ts, cutoff_ts):
    """Check if a daily price bar settled before the PIT cutoff.

    Returns True if the bar is PIT-safe (settled at or before cutoff).
    Returns False (fail-closed) if timestamp is missing, unparseable, or post-cutoff.
    """
    if not price_ts:
        return False
    try:
        return _parse_dt_for_pit(price_ts) <= _parse_dt_for_pit(cutoff_ts)
    except (ValueError, TypeError):
        return False


def _build_forward_returns(created, market_session_val, returns_schedule_raw, metrics,
                           session_helper, context_cutoff_ts):
    """Build forward returns for a news or filing event.

    Returns are nulled for any horizon whose window end extends past context_cutoff_ts.
    This is the PIT safety gate — it prevents return values from capturing the
    current earnings reaction even when the event itself is legitimately pre-cutoff.
    """
    schedule = _iq_parse_json_field(returns_schedule_raw, {}) or {}

    hourly_start = session_helper.get_interval_start_time(created)
    hourly_end = schedule.get('hourly') or session_helper.get_interval_end_time(
        created, 60, respect_session_boundary=False
    ).isoformat()

    session_start = session_helper.get_start_time(created)
    session_end = schedule.get('session') or session_helper.get_end_time(created).isoformat()

    daily_start, daily_end_fallback = session_helper.get_1d_impact_times(created)
    daily_end = schedule.get('daily') or daily_end_fallback.isoformat()

    def pack(prefix, start_ts, end_ts):
        stock = _norm_ret(metrics.get(f'{prefix}_stock'))
        sector = _norm_ret(metrics.get(f'{prefix}_sector'))
        industry = _norm_ret(metrics.get(f'{prefix}_industry'))
        macro = _norm_ret(metrics.get(f'{prefix}_macro'))
        return {
            'start_ts': str(start_ts),
            'end_ts': str(end_ts),
            'stock': stock,
            'sector': sector,
            'industry': industry,
            'macro': macro,
            'adj_macro': _safe_adj(stock, macro),
            'adj_sector': _safe_adj(stock, sector),
            'adj_industry': _safe_adj(stock, industry),
        }

    result = {}
    for horizon, prefix, start_ts, end_ts in [
        ('hourly', 'hourly', hourly_start.isoformat(), hourly_end),
        ('session', 'session', session_start.isoformat(), session_end),
        ('daily', 'daily', daily_start.isoformat(), daily_end),
    ]:
        # PIT safety: null the entire horizon if its window extends past the cutoff
        if _parse_dt_for_pit(end_ts) > _parse_dt_for_pit(context_cutoff_ts):
            result[horizon] = None
        else:
            result[horizon] = pack(prefix, start_ts, end_ts)

    return result


def _cutoff_boundary_price_role(context_cutoff_ts):
    """Determine if the cutoff boundary day's close-to-close price is within-window.

    Rule: ordinary if cutoff time >= 16:00 (market close), reference_only otherwise.
    No MarketSessionClassifier needed — pure timestamp check.
    """
    hour = int(context_cutoff_ts[11:13])
    return 'ordinary' if hour >= 16 else 'reference_only'


def _best_safe_horizon(forward_returns):
    """Return the best safe horizon dict for compact news rendering.

    Priority: daily (most informative) -> session -> hourly.
    Returns (horizon_name, horizon_dict) or (None, None) if all null.
    """
    if forward_returns is None:
        return None, None
    for name in ('daily', 'session', 'hourly'):
        h = forward_returns.get(name)
        if h is not None and h.get('stock') is not None:
            return name, h
    return None, None


def _report_summary(form_type, items, description, accession):
    """Render label for report event. Always prepend [form_type]."""
    text = None
    if items:
        text = items[0]
    if not text and description:
        text = description
    if not text:
        text = accession
    return f'[{form_type}] {text}'


# --- Rendered text helpers ---


def _render_window_label_news(start_ts, end_ts):
    """Compact HH:MM->HH:MM for news react lines (no date prefix)."""
    s_time = str(start_ts)[11:16]
    e_time = str(end_ts)[11:16]
    return f'({s_time}->{e_time})'


def _render_window_label_filing(start_ts, end_ts, event_date, horizon):
    """Detailed window label for filing horizon lines.

    - Daily: MM/DD close->MM/DD close
    - Hourly/session: HH:MM or MM/DD HH:MM when cross-day
    """
    s_day = str(start_ts)[:10]
    e_day = str(end_ts)[:10]
    s_time = str(start_ts)[11:16]
    e_time = str(end_ts)[11:16]

    if horizon == 'daily':
        s_label = f'{s_day[5:7]}/{s_day[8:10]} close'
        e_label = f'{e_day[5:7]}/{e_day[8:10]} close'
        return f'({s_label}->{e_label})'

    # For hourly/session: add date prefix when cross-day
    if s_day != event_date:
        s_label = f'{s_day[5:7]}/{s_day[8:10]} {s_time}'
    else:
        s_label = s_time
    if e_day != s_day:
        e_label = f'{e_day[5:7]}/{e_day[8:10]} {e_time}'
    else:
        e_label = e_time
    return f'({s_label}->{e_label})'


def _render_horizon_line_filing(horizon_name, h, event_date):
    """Render one filing horizon line: stock, sector, industry, SPY, adj_macro, window."""
    if h is None:
        return f'  {horizon_name:7s} (nulled -- window extends past cutoff)'
    if h.get('stock') is None:
        return None  # skip this horizon
    parts = [f'{horizon_name:7s} stock {h["stock"]:+.2f}%']
    if h.get('sector') is not None:
        parts.append(f'sector {h["sector"]:+.2f}%')
    if h.get('industry') is not None:
        parts.append(f'industry {h["industry"]:+.2f}%')
    if h.get('macro') is not None:
        parts.append(f'SPY {h["macro"]:+.2f}%')
    if h.get('adj_macro') is not None:
        parts.append(f'adj_macro {h["adj_macro"]:+.2f}%')
    wl = _render_window_label_filing(h['start_ts'], h['end_ts'], event_date, horizon_name)
    parts.append(wl)
    return '  ' + ' | '.join(parts)


def _render_news_react_line(forward_returns):
    """Render one compact react: line for news using best safe horizon."""
    h_name, h = _best_safe_horizon(forward_returns)
    if h_name is None:
        return None
    parts = [f'{h_name} stock {h["stock"]:+.2f}%']
    if h.get('macro') is not None:
        parts.append(f'SPY {h["macro"]:+.2f}%')
    if h.get('adj_macro') is not None:
        parts.append(f'adj_macro {h["adj_macro"]:+.2f}%')
    wl = _render_window_label_news(h['start_ts'], h['end_ts'])
    parts.append(wl)
    return '  react: ' + ' | '.join(parts)


def render_inter_quarter_text(packet):
    """Render canonical JSON into compact text timeline for LLM prompt."""
    ticker = packet['ticker']
    s = packet['summary']
    lines = []

    # Header
    lines.append(f'=== INTER-QUARTER TIMELINE: {ticker} ===')
    lines.append(f'Industry: {packet.get("industry") or "?"} | Sector: {packet.get("sector") or "?"}')
    lines.append(
        f'{s["trading_days_ordinary"]} ordinary trading days | '
        f'{s["boundary_days_rendered"]} boundary days | '
        f'{s["total_news"]} news | {s["total_filings"]} filings | '
        f'{s["total_dividends"]} dividends | {s["total_splits"]} splits'
    )
    lines.append(f'{s["significant_move_days"]} significant move days | {s["gap_days"]} gap days')
    lines.append('')
    lines.append('Legend:')
    lines.append('pre_market  = session -> 09:35, daily = prior close -> same-day close')
    lines.append('in_market   = session -> same-day close, daily = prior close -> same-day close')
    lines.append('post_market = session -> next-day 09:35, daily = same-day close -> next-day close')
    lines.append('market_closed = exact windows shown explicitly when they differ')

    for day in packet['days']:
        lines.append('')
        d = day['date']
        br = day.get('boundary_role')
        pr = day.get('price_role', 'ordinary')
        is_td = day.get('is_trading_day', False)
        price = day.get('price')

        # --- Day header ---
        if br == 'prev_boundary':
            lines.append(f'{d} | boundary day after previous earnings')
            prev_time = packet['prev_8k_ts'][11:19]
            lines.append(f'  previous 8-K filed at {prev_time}; only later timestamped events are included')
            if price:
                dr = price.get('daily_return')
                sr = day.get('spy_return')
                dr_s = f'{dr:+.2f}%' if dr is not None else '?'
                sr_s = f'{sr:+.2f}%' if sr is not None else '?'
                lines.append(f'  same-day close-to-close ({dr_s} vs SPY {sr_s}) is reference only')

        elif br == 'cutoff_boundary':
            cutoff_time = packet['context_cutoff_ts'][11:19]
            lines.append(f'{d} | cutoff boundary (context cutoff at {cutoff_time})')
            lines.append(f'  only events before cutoff are included')
            if pr == 'ordinary':
                lines.append(f'  same-day close-to-close is fully pre-cutoff and therefore within-window')
                if price:
                    dr = price.get('daily_return')
                    sr = day.get('spy_return')
                    adj = day.get('adj_return')
                    dr_s = f'{dr:+.2f}%' if dr is not None else '?'
                    sr_s = f'{sr:+.2f}%' if sr is not None else '?'
                    adj_s = f'{adj:+.2f}%' if adj is not None else '?'
                    lines.append(f'  {ticker} {dr_s} vs SPY {sr_s} | adj {adj_s}')
            else:
                lines.append(f'  same-day close-to-close extends past cutoff and is reference only')

        elif not is_td:
            lines.append(f'{d} | non-trading event day')

        else:
            # Ordinary trading day
            dr = price.get('daily_return') if price else None
            sr = day.get('spy_return')
            adj = day.get('adj_return')
            dr_s = f'{dr:+.2f}%' if dr is not None else '?'
            sr_s = f'{sr:+.2f}%' if sr is not None else '?'
            adj_s = f'{adj:+.2f}%' if adj is not None else '?'
            header = f'{d} | {ticker} {dr_s} vs SPY {sr_s} | adj {adj_s}'
            if day.get('is_significant'):
                header += '  ***'
            if day.get('is_gap_day'):
                header += '  GAP'
            lines.append(header)
            if price:
                lines.append(f'  open={price["open"]}  high={price["high"]}  low={price["low"]}  close={price["close"]}')
                lines.append(f'  vol={_fmt_vol(price.get("volume"))}  vwap={price.get("vwap")}  txns={_fmt_txn(price.get("transactions"))}')
                sec_ret = day.get('sector_return')
                ind_ret = day.get('industry_return')
                bench_parts = []
                if sec_ret is not None:
                    bench_parts.append(f'Sector {sec_ret:+.2f}%')
                if ind_ret is not None:
                    bench_parts.append(f'Industry {ind_ret:+.2f}%')
                if bench_parts:
                    lines.append(f'  {" | ".join(bench_parts)}')

        # --- Events ---
        events = day.get('events', [])
        if not events and is_td and br is None and day.get('is_gap_day'):
            lines.append('')
            lines.append('  (no news, no filings)')
        for ev in events:
            lines.append('')
            etype = ev['type']
            if etype == 'news':
                ts_time = str(ev['created'])[11:16]
                ms = ev.get('market_session', '')
                ref = ev['event_ref']
                title = ev.get('title', '')
                header = f'  {ts_time} {ms} | {ref} | {title}'
                channels = ev.get('channels', [])
                if channels:
                    header += f' [{", ".join(channels)}]'
                lines.append(header)
                react = _render_news_react_line(ev.get('forward_returns'))
                if react:
                    lines.append(f'  {react.strip()}')

            elif etype == 'filing':
                ts_time = str(ev['created'])[11:16]
                ms = ev.get('market_session', '')
                ref = ev['event_ref']
                summary = _report_summary(
                    ev.get('form_type', '?'),
                    ev.get('items', []),
                    ev.get('description'),
                    ev.get('accession', '?')
                )
                lines.append(f'  {ts_time} {ms} | {ref} | {summary}')
                # Detail line 1: accession + period + amendment
                det1 = f'    accession: {ev.get("accession", "?")}'
                if ev.get('period_of_report'):
                    det1 += f' | period: {ev["period_of_report"]}'
                if ev.get('is_amendment'):
                    det1 += ' | amendment'
                lines.append(det1)
                # Detail line 2: sections + exhibits
                sn = ev.get('section_names', [])
                ek = ev.get('exhibit_keys', [])
                det2 = f'    sections: {len(sn)}'
                if ek:
                    det2 += f' | exhibits: {", ".join(ek)}'
                else:
                    det2 += ' | exhibits: none'
                lines.append(det2)
                # Horizon lines (all 3 for filings)
                ev_date = str(ev['created'])[:10]
                fr = ev.get('forward_returns') or {}
                for h_name in ('hourly', 'session', 'daily'):
                    h = fr.get(h_name)
                    if h is None and h_name in fr:
                        # Horizon was explicitly nulled by PIT safety
                        lines.append(f'    {h_name:7s} (nulled -- window extends past cutoff)')
                    elif h is None:
                        continue  # horizon not present at all
                    else:
                        hl = _render_horizon_line_filing(h_name, h, ev_date)
                        if hl:
                            lines.append(f'  {hl.strip()}')

            elif etype == 'dividend':
                ref = ev['event_ref']
                amt = ev.get('cash_amount', '?')
                cur = ev.get('currency', '')
                freq = ev.get('frequency', '')
                lines.append(f'  date-only | {ref} | Dividend declared: ${amt} {cur} {freq}'.rstrip())
                ex_d = ev.get('ex_dividend_date', '?')
                pay_d = ev.get('pay_date', '?')
                dtype = ev.get('dividend_type', '?')
                lines.append(f'    ex-date {ex_d} | pay-date {pay_d} | type {dtype}')

            elif etype == 'split':
                ref = ev['event_ref']
                ratio = ev.get('ratio_text', '?')
                lines.append(f'  date-only | {ref} | Split effective: {ratio}')

    return '\n'.join(lines)


def build_inter_quarter_context(ticker, prev_8k_ts, context_cutoff_ts,
                                out_path=None, context_cutoff_reason=None,
                                exclude_accessions=None,
                                related_filings_dir=None):
    """Build inter-quarter context timeline artifact (inter_quarter_context.v1).

    Returns: packet dict (inter_quarter_context.v1).

    Args:
        ticker: Company ticker (e.g. 'CRM')
        prev_8k_ts: ISO8601 timestamp of previous earnings 8-K
        context_cutoff_ts: Upper bound for event inclusion (exclusive)
        out_path: Output file path (default: /tmp/earnings_inter_quarter_{ticker}.json)
        context_cutoff_reason: Optional metadata label (e.g. 'historical_release_session_floor')
        exclude_accessions: Optional set of accession numbers to drop from the
            filings timeline (e.g. the target 8-K). Defends against
            `--pit > filed_8k` reruns where the target would otherwise leak.
        related_filings_dir: Optional path to write per-accession sidecar
            markdown files for selected related 8-Ks. If None, no sidecars are
            written and `_allowed_related_filing_paths` will be empty
            (idempotent: dry inspection produces no on-disk side effects).
    """
    exclude_accessions = set(exclude_accessions or ())
    from utils.market_session import MarketSessionClassifier

    # 1. Parse inputs
    prev_day = prev_8k_ts[:10]
    cutoff_day = context_cutoff_ts[:10]
    if out_path is None:
        out_path = f'/tmp/earnings_inter_quarter_{ticker}.json'

    # 2. Initialize helpers
    session_helper = MarketSessionClassifier()

    manager = get_manager()
    try:
        # 3. Query
        price_rows = manager.execute_cypher_query_all(QUERY_IQ_PRICES, {
            'ticker': ticker, 'prev_day': prev_day, 'cutoff_day': cutoff_day
        })

        news_rows = manager.execute_cypher_query_all(QUERY_IQ_NEWS, {
            'ticker': ticker, 'prev_8k_ts': prev_8k_ts, 'context_cutoff_ts': context_cutoff_ts
        })

        filing_rows = manager.execute_cypher_query_all(QUERY_IQ_FILINGS, {
            'ticker': ticker, 'prev_8k_ts': prev_8k_ts, 'context_cutoff_ts': context_cutoff_ts
        })

        div_rows = manager.execute_cypher_query_all(QUERY_IQ_DIVIDENDS, {
            'ticker': ticker, 'prev_day': prev_day, 'cutoff_day': cutoff_day
        })

        split_rows = manager.execute_cypher_query_all(QUERY_IQ_SPLITS, {
            'ticker': ticker, 'prev_day': prev_day, 'cutoff_day': cutoff_day
        })

        # 4. Build base day_map from price rows
        day_map = {}
        top_sector = None
        top_industry = None

        for row in price_rows:
            d = str(row['date'])
            dr = row.get('daily_return')
            sr = row.get('spy_return')
            day_map[d] = {
                'date': d,
                'is_trading_day': True,
                'boundary_role': None,
                'price_role': 'ordinary',
                'price': {
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'daily_return': dr,
                    'volume': row.get('volume'),
                    'vwap': row.get('vwap'),
                    'transactions': row.get('transactions'),
                    'timestamp': row.get('price_timestamp'),
                },
                'spy_return': sr,
                'sector_return': row.get('sector_return'),
                'industry_return': row.get('industry_return'),
                'adj_return': _safe_adj(dr, sr),
                'is_significant': None,
                'is_gap_day': None,
                'events': [],
            }
            if top_sector is None and row.get('sector_name'):
                top_sector = row['sector_name']
            if top_industry is None and row.get('industry_name'):
                top_industry = row['industry_name']

        # Company context fallback
        if top_sector is None or top_industry is None:
            ctx_rows = manager.execute_cypher_query_all(QUERY_IQ_COMPANY_CONTEXT, {'ticker': ticker})
            if ctx_rows:
                if top_industry is None:
                    top_industry = ctx_rows[0].get('industry_name')
                if top_sector is None:
                    top_sector = ctx_rows[0].get('sector_name')

        # 5. Ensure boundary day entries exist
        for bd in [prev_day, cutoff_day]:
            if bd not in day_map:
                day_map[bd] = {
                    'date': bd,
                    'is_trading_day': False,
                    'boundary_role': None,
                    'price_role': 'ordinary',
                    'price': None,
                    'spy_return': None,
                    'sector_return': None,
                    'industry_return': None,
                    'adj_return': None,
                    'is_significant': None,
                    'is_gap_day': None,
                    'events': [],
                }

        # 6. Mark boundary roles
        day_map[prev_day]['boundary_role'] = 'prev_boundary'
        day_map[cutoff_day]['boundary_role'] = 'cutoff_boundary'

        # 7. Set price roles
        if day_map[prev_day]['is_trading_day']:
            day_map[prev_day]['price_role'] = 'reference_only'
        cutoff_pr = _cutoff_boundary_price_role(context_cutoff_ts)
        if day_map[cutoff_day]['is_trading_day']:
            day_map[cutoff_day]['price_role'] = cutoff_pr

        # 7b. PIT safety — null cutoff day price data if bar settles after cutoff
        #     Uses actual bar settlement timestamp (hp.timestamp), not hour heuristic.
        #     Matches the same principled approach _build_forward_returns uses for events.
        #     Fail-closed: if timestamp missing/unparseable, data is nulled.
        cutoff_entry = day_map[cutoff_day]
        if (cutoff_entry['is_trading_day']
                and cutoff_entry.get('price')
                and not _is_price_pit_safe(
                    cutoff_entry['price'].get('timestamp'), context_cutoff_ts)):
            cutoff_entry['price'] = None
            cutoff_entry['spy_return'] = None
            cutoff_entry['sector_return'] = None
            cutoff_entry['industry_return'] = None
            cutoff_entry['adj_return'] = None
            cutoff_entry['price_role'] = 'reference_only'
        elif cutoff_entry['is_trading_day'] and cutoff_entry.get('price'):
            # Bar is PIT-safe — ensure price_role reflects this (fixes
            # early-close days where hour heuristic wrongly sets reference_only)
            cutoff_entry['price_role'] = 'ordinary'

        # 8. Merge news events
        for row in news_rows:
            created = str(row['created'])
            day_key = created[:10]
            channels = _iq_parse_json_field(row.get('channels'), [])
            authors = _iq_parse_json_field(row.get('authors'), [])
            tags = _iq_parse_json_field(row.get('tags'), [])
            rs_raw = row.get('returns_schedule')
            metrics = {k: row.get(k) for k in [
                'hourly_stock', 'session_stock', 'daily_stock',
                'hourly_sector', 'session_sector', 'daily_sector',
                'hourly_industry', 'session_industry', 'daily_industry',
                'hourly_macro', 'session_macro', 'daily_macro',
            ]}
            fr = _build_forward_returns(created, row.get('market_session'), rs_raw,
                                        metrics, session_helper, context_cutoff_ts)
            ev = {
                'event_ref': _event_ref('news', row['news_id']),
                'type': 'news',
                'available_precision': 'timestamp',
                'created': created,
                'market_session': row.get('market_session'),
                'title': row.get('title'),
                'channels': channels,
                'forward_returns': fr,
                # JSON-only fields
                'id': row.get('news_id'),
                'url': row.get('url'),
                'authors': authors,
                'tags': tags,
                'updated': row.get('updated'),
                'returns_schedule_raw': rs_raw,
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 9. Merge filing events
        # Set up sidecar directory once (only when caller opted in via
        # related_filings_dir — dry inspections pass None to avoid side effects).
        if related_filings_dir:
            os.makedirs(related_filings_dir, exist_ok=True)
        for row in filing_rows:
            # U7: defensive target-accession exclusion (covers --pit > filed_8k).
            if row.get('accession') in exclude_accessions:
                continue
            created = str(row['created'])
            day_key = created[:10]
            items = _iq_parse_json_field(row.get('items'), [])
            exhibits_parsed = _iq_parse_json_field(row.get('exhibits'), {})
            exhibit_keys = sorted(exhibits_parsed.keys()) if isinstance(exhibits_parsed, dict) else []
            rs_raw = row.get('returns_schedule')
            section_names = sorted([s for s in (row.get('section_names') or []) if s])
            metrics = {k: row.get(k) for k in [
                'hourly_stock', 'session_stock', 'daily_stock',
                'hourly_sector', 'session_sector', 'daily_sector',
                'hourly_industry', 'session_industry', 'daily_industry',
                'hourly_macro', 'session_macro', 'daily_macro',
            ]}
            fr = _build_forward_returns(created, row.get('market_session'), rs_raw,
                                        metrics, session_helper, context_cutoff_ts)
            ev = {
                'event_ref': _event_ref('report', row['accession']),
                'type': 'filing',
                'available_precision': 'timestamp',
                'created': created,
                'market_session': row.get('market_session'),
                'form_type': row.get('form_type'),
                'accession': row.get('accession'),
                'period_of_report': row.get('period_of_report'),
                'is_amendment': row.get('is_amendment'),
                'description': row.get('description'),
                'items': items,
                'exhibit_keys': exhibit_keys,
                'forward_returns': fr,
                # JSON-only fields
                'report_id': row.get('report_id'),
                'filing_links': {
                    'primary_doc_url': row.get('primary_doc_url'),
                    'link_to_txt': row.get('link_to_txt'),
                    'link_to_html': row.get('link_to_html'),
                    'link_to_filing_details': row.get('link_to_filing_details'),
                },
                'section_names': section_names,
                'has_filing_text': row.get('has_filing_text'),
                'xbrl_status': row.get('xbrl_status'),
                'financial_statement_count': row.get('financial_statement_count'),
                'returns_schedule_raw': rs_raw,
                'related_content_path': None,
            }
            # U7: emit sidecar for selected 8-K / 8-K/A only when caller opted in.
            if related_filings_dir:
                items_codes = {c for c in (_parse_item_code(i) for i in items) if c}
                if _should_emit_sidecar(row.get('form_type'), items_codes,
                                        exhibits_parsed if isinstance(exhibits_parsed, dict) else {}):
                    sections, exhibits, filing_text = _fetch_related_filing_content(
                        manager, row.get('accession'))
                    md = _render_sidecar_md(ev, sections, exhibits, filing_text)
                    if md.strip():
                        sidecar_path = os.path.join(related_filings_dir,
                                                    f"{row.get('accession')}.md")
                        try:
                            _atomic_write_text(sidecar_path, md)
                            if os.path.isfile(sidecar_path):
                                # Repo-relative path for the bundle / allowlist.
                                ev['related_content_path'] = os.path.relpath(
                                    sidecar_path, str(Path.cwd()))
                        except OSError:
                            pass  # leave related_content_path = None
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 10. Merge dividends
        for row in div_rows:
            day_key = str(row['declaration_date'])
            ev = {
                'event_ref': _event_ref('dividend', row['dividend_id']),
                'type': 'dividend',
                'available_precision': 'date',
                'event_day': day_key,
                'declaration_date': day_key,
                'ex_dividend_date': row.get('ex_dividend_date'),
                'cash_amount': row.get('cash_amount'),
                'currency': row.get('currency'),
                'frequency': row.get('frequency'),
                'dividend_type': row.get('dividend_type'),
                'forward_returns': None,
                # JSON-only
                'id': row.get('dividend_id'),
                'pay_date': row.get('pay_date'),
                'record_date': row.get('record_date'),
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 11. Merge splits
        for row in split_rows:
            day_key = str(row['execution_date'])
            sf = row.get('split_from')
            st = row.get('split_to')
            ev = {
                'event_ref': _event_ref('split', row['split_id']),
                'type': 'split',
                'available_precision': 'date',
                'event_day': day_key,
                'execution_date': day_key,
                'split_from': sf,
                'split_to': st,
                'ratio_text': f'{sf}:{st}',
                'forward_returns': None,
                # JSON-only
                'id': row.get('split_id'),
            }
            if day_key not in day_map:
                day_map[day_key] = {
                    'date': day_key, 'is_trading_day': False, 'boundary_role': None,
                    'price_role': 'ordinary', 'price': None, 'spy_return': None,
                    'sector_return': None, 'industry_return': None, 'adj_return': None,
                    'is_significant': None, 'is_gap_day': None, 'events': [],
                }
            day_map[day_key]['events'].append(ev)

        # 12. Remove empty non-trading non-boundary days (synthetic entries with no events)
        # (Steps 8-11 already created synthetic entries only when events exist)

        # 13. Sort events within each day
        type_order = {'filing': 0, 'news': 1, 'dividend': 2, 'split': 3}
        for day in day_map.values():
            day['events'].sort(key=lambda e: (
                0 if e.get('available_precision') == 'timestamp' else 1,
                str(e.get('created', 'zzzz')),
                type_order.get(e['type'], 9),
            ))

        # 14. Compute ordinary-day significance markers
        for day in day_map.values():
            br = day['boundary_role']
            pr = day['price_role']
            if day['is_trading_day'] and (
                (br is None and pr == 'ordinary') or
                (br == 'cutoff_boundary' and pr == 'ordinary')
            ):
                adj = day['adj_return']
                if adj is not None:
                    day['is_significant'] = abs(adj) >= 2.0
                    news_count = sum(1 for e in day['events'] if e['type'] == 'news')
                    filing_count = sum(1 for e in day['events'] if e['type'] == 'filing')
                    day['is_gap_day'] = day['is_significant'] and news_count == 0 and filing_count == 0
                else:
                    day['is_significant'] = False
                    day['is_gap_day'] = False

        # Build sorted day list and remove days with no events and no price (non-boundary)
        sorted_days = []
        for d in sorted(day_map.keys()):
            day = day_map[d]
            # Keep if: has events, has price, or is a boundary day
            if day['events'] or day['price'] is not None or day['boundary_role'] is not None:
                sorted_days.append(day)

        # 15. Build summary counts
        total_news = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'news')
        total_filings = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'filing')
        total_dividends = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'dividend')
        total_splits = sum(1 for day in sorted_days for e in day['events'] if e['type'] == 'split')
        trading_ordinary = sum(1 for day in sorted_days if day['is_trading_day'] and day['boundary_role'] is None)
        boundary_rendered = sum(1 for day in sorted_days if day['boundary_role'] is not None)
        non_trading_event = sum(1 for day in sorted_days if not day['is_trading_day'])
        sig_days = sum(1 for day in sorted_days if day.get('is_significant') is True)
        gap_days = sum(1 for day in sorted_days if day.get('is_gap_day') is True)

        summary = {
            'total_day_blocks': len(sorted_days),
            'trading_days_ordinary': trading_ordinary,
            'boundary_days_rendered': boundary_rendered,
            'non_trading_event_days': non_trading_event,
            'significant_move_days': sig_days,
            'gap_days': gap_days,
            'total_news': total_news,
            'total_filings': total_filings,
            'total_dividends': total_dividends,
            'total_splits': total_splits,
        }

        # 15b. U7: build allowlist of related-filing sidecar paths.
        # Order matches event render order; no duplicates by construction
        # (each accession is unique). Local invariant: allowlist set equals
        # the set of non-null related_content_path values across filing events.
        allowed_related_paths = []
        seen_paths = set()
        for day in sorted_days:
            for ev in day.get('events', []):
                if ev.get('type') != 'filing':
                    continue
                p = ev.get('related_content_path')
                if p and p not in seen_paths:
                    allowed_related_paths.append(p)
                    seen_paths.add(p)
        # Local invariant (non-blocking belt-and-suspenders):
        event_paths_set = {ev.get('related_content_path')
                           for day in sorted_days for ev in day.get('events', [])
                           if ev.get('type') == 'filing' and ev.get('related_content_path')}
        if set(allowed_related_paths) != event_paths_set:
            raise AssertionError(
                "_allowed_related_filing_paths invariant violated: "
                f"allowlist={set(allowed_related_paths)!r} "
                f"event_paths={event_paths_set!r}"
            )

        # 16. Assemble and write canonical JSON
        packet = {
            'schema_version': 'inter_quarter_context.v1',
            'ticker': ticker,
            'prev_8k_ts': prev_8k_ts,
            'context_cutoff_ts': context_cutoff_ts,
            'context_cutoff_reason': context_cutoff_reason,
            'prev_day': prev_day,
            'cutoff_day': cutoff_day,
            'industry': top_industry,
            'sector': top_sector,
            'days': sorted_days,
            'summary': summary,
            '_allowed_related_filing_paths': allowed_related_paths,
            'assembled_at': datetime.now(timezone.utc).isoformat(),
        }

        out_dir = os.path.dirname(out_path) or '.'
        os.makedirs(out_dir, exist_ok=True)
        tmp_path = out_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(packet, f, default=str, indent=2)
        os.replace(tmp_path, out_path)

        return packet

    finally:
        manager.close()
