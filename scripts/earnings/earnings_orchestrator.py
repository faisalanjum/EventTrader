#!/usr/bin/env python3
"""Earnings Orchestrator — minimal bundle assembly and rendering.

Usage:
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383 --pit 2025-02-26T17:00:00-05:00
    python scripts/earnings/earnings_orchestrator.py CRM --quarter-info-json /tmp/quarter_info.json
    python scripts/earnings/earnings_orchestrator.py CRM 0001628280-25-004383 --save
"""
from __future__ import annotations

import asyncio
import argparse
import json
import logging
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))
sys.path.insert(0, str(_PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts"))

from builder_adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)
from config.llm_models import LEARNER, PREDICTOR
from quarter_identity import resolve_quarter_info
from scripts.earnings.utils import neo4j_session

from dotenv import load_dotenv
load_dotenv(str(_PROJECT_ROOT / ".env"), override=True)



def load_quarter_info_json(path: str) -> dict[str, Any]:
    """Load quarter_info from a JSON file."""
    with open(path, encoding="utf-8") as f:
        quarter_info = json.load(f)
    if not isinstance(quarter_info, dict):
        raise ValueError(f"quarter_info JSON must be an object: {path}")
    return quarter_info


def validate_quarter_info(quarter_info: dict[str, Any]) -> None:
    """Validate the common quarter_info shape expected by adapters."""
    required = [
        "accession_8k",
        "filed_8k",
        "market_session",
        "period_of_report",
        "prev_8k_ts",
        "quarter_label",
    ]
    missing = [key for key in required if key not in quarter_info]
    if missing:
        raise ValueError(f"quarter_info missing keys: {', '.join(missing)}")
    if not quarter_info.get("period_of_report"):
        raise ValueError(
            f"period_of_report is None — quarter identity could not be resolved. "
            f"Gaps: {quarter_info.get('gaps', 'unknown')}"
        )
    if not quarter_info.get("quarter_label"):
        raise ValueError(
            f"quarter_label is None — fiscal identity could not be derived. "
            f"Gaps: {quarter_info.get('gaps', 'unknown')}"
        )


# ── Bundle assembly ──────────────────────────────────────────────────

# The 7 parallel builders — each hits Neo4j/APIs and runs in ThreadPoolExecutor.
# learning_context is the logical 8th bundle field but is NOT a parallel builder:
# it's a lightweight local file read added after builder execution (see build_prediction_bundle).
BUNDLE_ITEM_ORDER = [
    "8k_packet",
    "guidance_history",
    "inter_quarter_context",
    "peer_earnings_snapshot",
    "macro_snapshot",
    "consensus",
    "prior_financials",
]

BUILDERS = {
    "8k_packet":                 build_8k_packet,
    "guidance_history":          build_guidance_history,
    "inter_quarter_context":     build_inter_quarter_context,
    "peer_earnings_snapshot":    build_peer_earnings_snapshot,
    "macro_snapshot":            build_macro_snapshot,
    "consensus":                 build_consensus,
    "prior_financials":          build_prior_financials,
}


_TRANSIENT_MARKERS = ("defunct connection", "serviceunavailable", "connection refused",
                      "connection reset", "broken pipe", "timed out", "pool")
_COMPANY_SECTOR_QUERY = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
RETURN coalesce(c.sector, sec.name) AS sector
"""


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


# Anti-poisoning cache (amendment 2026-04-17): we use a manual dict that caches
# ONLY successful lookups. Failed lookups (Neo4j down, ticker absent, empty
# string) are re-queried on every call so a single transient Neo4j hiccup does
# NOT poison the cache for the lifetime of the process.
_SECTOR_CACHE: dict[str, str] = {}


def _lookup_company_sector(ticker: str) -> str | None:
    """Best-effort sector lookup for learning-context filtering and source_sector
    stamping. Only successful results are cached; None results are re-queried
    on every call to prevent transient-Neo4j-failure cache poisoning.
    """
    symbol = str(ticker or "").upper().strip()
    if not symbol:
        return None
    if symbol in _SECTOR_CACHE:
        return _SECTOR_CACHE[symbol]

    try:
        with neo4j_session() as (session, err):
            if err or session is None:
                log.warning("Sector lookup unavailable for %s: %s", symbol, err)
                return None  # intentionally NOT cached
            row = session.run(_COMPANY_SECTOR_QUERY, ticker=symbol).single()
    except Exception as e:
        log.warning("Sector lookup failed for %s: %s", symbol, e)
        return None  # intentionally NOT cached

    if not row:
        log.warning("Sector lookup returned no row for %s (ticker may be out-of-universe)", symbol)
        return None

    sector = row.data().get("sector")
    if sector is None:
        log.warning("source_sector is None for %s (ticker may be out-of-universe)", symbol)
        return None
    sector_text = str(sector).strip()
    if not sector_text:
        return None
    _SECTOR_CACHE[symbol] = sector_text  # success only
    return sector_text


def _normalize_sector(sector: str | None) -> str | None:
    if sector is None:
        return None
    normalized = " ".join(str(sector).split()).casefold()
    return normalized or None


def _run_builder(fn, ticker, quarter_info, pit_cutoff, out_path,
                 retries: int = 2, backoff: float = 2.0):
    """Run a single builder with retry on transient (connection) errors."""
    for attempt in range(retries + 1):
        try:
            return fn(ticker, quarter_info, pit_cutoff, out_path)
        except Exception as e:
            if attempt < retries and _is_transient(e):
                wait = backoff * (attempt + 1)
                log.warning("Builder %s attempt %d failed (transient): %s — retrying in %.1fs",
                            fn.__name__, attempt + 1, e, wait)
                time.sleep(wait)
                continue
            raise


def build_prediction_bundle(ticker: str, quarter_info: dict,
                            pit_cutoff: str | None = None,
                            out_dir: str | None = None) -> dict:
    """Run all 7 standardized builders in parallel, return merged bundle dict."""
    validate_quarter_info(quarter_info)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = Path(out_dir) if out_dir else Path("/tmp/earnings") / run_id

    def out(name: str) -> str:
        return str(base / f"{name}.json")

    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=len(BUNDLE_ITEM_ORDER)) as pool:
        futures = {
            pool.submit(_run_builder, BUILDERS[name], ticker, quarter_info,
                        pit_cutoff, out(name)): name
            for name in BUNDLE_ITEM_ORDER
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                errors[name] = str(e)

    if "8k_packet" in errors:
        raise RuntimeError(f"HARD FAIL — 8k_packet builder failed: {errors['8k_packet']}")

    bundle = {
        "schema_version": "prediction_bundle.v1",
        "ticker": ticker,
        "quarter_info": quarter_info,
        "pit_cutoff": pit_cutoff,
        "assembled_at": datetime.now(timezone.utc).isoformat(),
        "builder_errors": errors if errors else None,
    }
    for name in BUNDLE_ITEM_ORDER:
        bundle[name] = results.get(name)

    # learning_context is the logical 8th bundle field. It remains outside
    # BUNDLE_ITEM_ORDER because the main work is local lesson-file loading;
    # sector-aware filtering may do a cached company-metadata lookup when needed.
    # T1.5b: pit_cutoff flows in from the bundle caller so historical reruns
    # filter out lessons stamped after the predictor's cutoff. Live mode
    # (pit_cutoff=None) bypasses the filter entirely.
    try:
        sector = (results.get("8k_packet") or {}).get("sector") or _lookup_company_sector(ticker)
        bundle["learning_context"] = build_learning_context(
            ticker, sector=sector, pit_cutoff=pit_cutoff,
        )
    except Exception as e:
        log.warning("learning_context builder failed (non-fatal): %s", e)
        bundle["learning_context"] = {"ticker_lessons": [], "global_lessons": [],
                                       "ticker_ref": None, "global_ref": None}

    return bundle


# ── Bundle rendering ─────────────────────────────────────────────────

SECTION_TITLES = {
    "8k_packet":                 "8-K Earnings Results (Current Quarter)",
    "guidance_history":          "Company Guidance History",
    "inter_quarter_context":     "Inter-Quarter Events (News, Filings, Analyst Actions)",
    "peer_earnings_snapshot":    "Sector Peer Earnings & Reactions",
    "macro_snapshot":            "Macro Environment",
    "consensus":                 "Analyst Consensus (EPS & Revenue Expectations)",
    "prior_financials":          "Multi-Quarter Financial Trends",
}


def _render_header(bundle: dict) -> str:
    """Section 1: Header — ticker, quarter, filing context, mode."""
    qi = bundle.get("quarter_info", {})
    ticker = str(bundle.get("ticker") or "UNKNOWN").upper()
    quarter = str(qi.get("quarter_label") or "UNKNOWN")
    filed = str(qi.get("filed_8k") or "UNKNOWN")
    session = str(qi.get("market_session") or "UNKNOWN")
    period = str(qi.get("period_of_report") or "UNKNOWN")
    pit = bundle.get("pit_cutoff")
    mode = "historical" if pit else "live"

    lines = [
        f"# {ticker} {quarter}",
        f"Filed: {filed} | Session: {session} | Period ending: {period}",
    ]
    if pit:
        lines.append(f"Mode: {mode} | PIT cutoff: {pit}")
    else:
        lines.append(f"Mode: {mode}")
    return "\n".join(lines)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Render a column-aligned markdown table."""
    all_rows = [headers] + rows
    widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]
    hdr = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    body = ["| " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)) + " |" for row in rows]
    return "\n".join([hdr, sep] + body)


def _fmt_num(val, prefix="", suffix="") -> str:
    """Format a number with optional prefix/suffix, smart magnitude scaling."""
    if val is None:
        return "—"
    v = float(val)
    if not math.isfinite(v):
        return "—"
    abs_v = abs(v)
    sign = "-" if v < 0 else ""
    abs_v_use = abs_v
    if abs_v_use >= 1e9:
        scaled = abs_v_use / 1e9
        s = f"{scaled:.0f}B" if scaled == int(scaled) else f"{scaled:.2f}B"
    elif abs_v_use >= 1e6:
        scaled = abs_v_use / 1e6
        s = f"{scaled:.0f}M" if scaled == int(scaled) else f"{scaled:.1f}M"
    elif abs_v_use >= 1e3:
        scaled = abs_v_use / 1e3
        s = f"{scaled:.0f}K" if scaled == int(scaled) else f"{scaled:.1f}K"
    elif abs_v_use == int(abs_v_use):
        s = str(int(abs_v_use))
    else:
        s = f"{abs_v_use:.2f}"
    return f"{sign}{prefix}{s}{suffix}"


def _fmt_money(val) -> str:
    """Format a monetary value for display."""
    return _fmt_num(val, prefix="$")


def _fmt_pct(val) -> str:
    """Format a percentage for display."""
    if val is None:
        return "—"
    v = float(val)
    if not math.isfinite(v):
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def _fmt_guidance_value(update: dict, resolved_unit: str) -> str:
    """Format a guidance update value: numeric range + qualitative if both present."""
    low = update.get("low")
    mid = update.get("mid")
    high = update.get("high")
    qual = (update.get("qualitative") or "").replace("\n", " ").strip() or None
    conditions = (update.get("conditions") or "").replace("\n", " ").strip() or None

    # Numeric formatting based on unit
    numeric = None
    has_numeric = low is not None or high is not None or mid is not None

    if has_numeric:
        is_money = resolved_unit in ("m_usd", "usd", "k_usd")
        _PCT_SUFFIX = {
            "percent": "%", "percent_yoy": "% YoY",
            "percent_points": "pp", "basis_points": "bps",
        }
        pct_suffix = _PCT_SUFFIX.get(resolved_unit)

        def _fv(v):
            if v is None:
                return "—"
            if is_money:
                if resolved_unit == "m_usd":
                    return _fmt_money(v * 1e6)
                elif resolved_unit == "k_usd":
                    return _fmt_money(v * 1e3)
                return _fmt_money(v)
            if pct_suffix:
                pv = float(v)
                if not math.isfinite(pv):
                    return "—"
                return f"{pv:.0f}{pct_suffix}" if pv == int(pv) else f"{pv:.1f}{pct_suffix}"
            if resolved_unit == "x":
                xv = float(v)
                if not math.isfinite(xv):
                    return "—"
                return f"{xv:g}x"
            # count, unknown — compact scaling for large values, comma format for smaller
            fv = float(v)
            if not math.isfinite(fv):
                return "—"
            abs_fv = abs(fv)
            if abs_fv >= 1e9:
                return _fmt_num(v)
            elif abs_fv >= 1e6:
                return _fmt_num(v)
            elif fv == int(fv):
                return f"{int(fv):,}"
            return f"{fv:g}"

        if low is not None and high is not None:
            if low == high:
                numeric = f"~{_fv(low)}"
            else:
                numeric = f"{_fv(low)}-{_fv(high)}"
        elif low is not None and high is None:
            numeric = f"≥{_fv(low)}"
        elif low is None and high is not None:
            numeric = f"≤{_fv(high)}"
        elif mid is not None:
            numeric = f"~{_fv(mid)}"

    # Combine numeric + qualitative
    parts = []
    if numeric:
        parts.append(numeric)
    if qual:
        parts.append(f'"{qual}"')
    if not parts:
        parts.append("—")

    result = " ".join(parts)

    # Inline conditions (truncated)
    if conditions:
        cond = conditions[:200] + ("..." if len(conditions) > 200 else "")
        result += f" ({cond})"

    return result


def _compute_change(current: dict, prior: dict | None) -> str:
    """Compute change label between current and prior guidance update."""
    if prior is None:
        return "new"

    c_low, c_mid, c_high = current.get("low"), current.get("mid"), current.get("high")
    p_low, p_mid, p_high = prior.get("low"), prior.get("mid"), prior.get("high")
    c_qual = (current.get("qualitative") or "").strip().lower()
    p_qual = (prior.get("qualitative") or "").strip().lower()

    def _bounds(low, mid, high):
        return (
            low if low is not None else mid,
            high if high is not None else mid,
        )

    c_has_numeric = any(v is not None for v in (c_low, c_mid, c_high))
    p_has_numeric = any(v is not None for v in (p_low, p_mid, p_high))

    if c_has_numeric and p_has_numeric:
        c_lo, c_hi = _bounds(c_low, c_mid, c_high)
        p_lo, p_hi = _bounds(p_low, p_mid, p_high)
        if c_lo == p_lo and c_hi == p_hi:
            return "maintained" if c_qual == p_qual else "revised"

        lo_cmp = None if c_lo is None or p_lo is None else ((c_lo > p_lo) - (c_lo < p_lo))
        hi_cmp = None if c_hi is None or p_hi is None else ((c_hi > p_hi) - (c_hi < p_hi))
        comps = [c for c in (lo_cmp, hi_cmp) if c is not None]
        if comps and all(c >= 0 for c in comps) and any(c > 0 for c in comps):
            return "raised"
        if comps and all(c <= 0 for c in comps) and any(c < 0 for c in comps):
            return "lowered"
        return "revised"

    # Qualitative only comparison
    if c_qual and p_qual:
        return "maintained" if c_qual == p_qual else "revised"

    return "revised"


def _fmt_metric_label(series: dict) -> str:
    """Format metric label with basis and segment annotations."""
    metric = series.get("metric", "Unknown")
    basis = series.get("basis_norm", "unknown")
    segment = series.get("segment", "Total")
    segment_slug = series.get("segment_slug", "total")

    label = metric
    if basis and basis not in ("unknown", ""):
        basis_label = {
            "gaap": "GAAP",
            "non_gaap": "Non-GAAP",
            "constant_currency": "Constant Currency",
        }.get(basis, basis.replace("_", " ").title())
        label += f" ({basis_label})"
    if segment_slug and segment_slug != "total":
        label += f" — {segment}"
    return label


def _guidance_target_key(update: dict) -> tuple[Any, Any, Any, Any]:
    """Stable target-period key within a canonical guidance series."""
    return (
        update.get("period_start"),
        update.get("period_end"),
        update.get("fiscal_year"),
        update.get("fiscal_quarter"),
    )


def _guidance_target_label(scope: str, fy: int | None, fq: int | None,
                           period_start: str | None, period_end: str | None) -> str:
    """Human-readable label for a guidance target period/horizon."""
    if scope == "quarter" and fy and fq:
        return f"Q{fq} FY{fy}"
    if scope == "annual" and fy:
        return f"FY{fy}"
    if scope == "half" and fy and period_start and period_end:
        return f"FY{fy} ({period_start} to {period_end})"
    if scope in ("long_term", "long_range", "medium_term", "short_term", "undefined"):
        if period_start and period_end:
            return f"{scope.replace('_', ' ').title()} ({period_start} to {period_end})"
        return scope.replace("_", " ").title()
    if fy and fq:
        return f"Q{fq} FY{fy}"
    if fy:
        return f"FY{fy}"
    if period_start and period_end:
        return f"{period_start} to {period_end}"
    return scope.replace("_", " ").title() if scope else "Unspecified"


def _is_segmented_label(label: str) -> bool:
    """Detect rows with explicit segment annotation for sorting."""
    return " — " in label


def _render_forward_guidance(bundle: dict) -> str:
    """Section 3: Forward Guidance — structured tables from guidance_history."""
    errors = bundle.get("builder_errors") or {}
    gh = bundle.get("guidance_history")

    if "guidance_history" in errors:
        return f"## 3. Forward Guidance\n[BUILDER ERROR: {errors['guidance_history']}]"
    if not gh or not isinstance(gh, dict):
        return "## 3. Forward Guidance\n[NO DATA]"

    series_list = gh.get("series", [])
    if not series_list:
        summary = gh.get("summary", {})
        return f"## 3. Forward Guidance\n[NO DATA — {summary.get('total_series', 0)} series]"

    summary = gh.get("summary", {})
    parts = [
        f"## 3. Forward Guidance",
        f"Guidance packet: {summary.get('total_series', '?')} series | "
        f"{summary.get('total_updates_collapsed', '?')} updates | "
        f"{summary.get('earliest_date', '?')} to {summary.get('latest_date', '?')}",
    ]

    # Parse current quarter from bundle to classify target periods
    qi = bundle.get("quarter_info", {})
    ql = qi.get("quarter_label", "")  # e.g. "Q1_FY2024"
    current_q, current_fy = None, None
    if "_FY" in ql:
        try:
            q_part, fy_part = ql.split("_FY")
            current_q = int(q_part.replace("Q", ""))
            current_fy = int(fy_part)
        except (ValueError, IndexError):
            pass

    # Bucket each series by section: quarterly / annual / other
    quarterly = {}   # key = (fy, fq) → list of row dicts
    annual = {}      # key = fy → list of row dicts
    other = []       # list of row dicts
    history_extras = []  # (series_label, target_label, list of middle_updates)

    for s in series_list:
        scope = s.get("period_scope", "")
        unit = s.get("resolved_unit", "unknown")
        label = _fmt_metric_label(s)
        updates = s.get("updates", [])

        # Group updates by target period. Include period dates so half-year and
        # long-range targets do not collide inside the same canonical series.
        by_target = {}
        for u in updates:
            key = _guidance_target_key(u)
            by_target.setdefault(key, []).append(u)

        for (period_start, period_end, fy, fq), target_updates in by_target.items():
            # Sort by given_day (already sorted, but be safe)
            target_updates.sort(key=lambda x: x.get("given_day", ""))
            current_u = target_updates[-1]
            prior_u = target_updates[-2] if len(target_updates) >= 2 else None
            change = _compute_change(current_u, prior_u)
            val_current = _fmt_guidance_value(current_u, unit)
            val_prior = _fmt_guidance_value(prior_u, unit) if prior_u else "—"
            row = {
                "label": label,
                "current": val_current,
                "prior": val_prior,
                "change": change,
                "segmented": _is_segmented_label(label),
            }

            # Quarterly: only FORWARD quarters (after the filing quarter)
            is_forward_quarter = False
            if scope == "quarter" and fy is not None and fq is not None and current_fy and current_q:
                if fy > current_fy or (fy == current_fy and fq > current_q):
                    is_forward_quarter = True

            if is_forward_quarter:
                quarterly.setdefault((fy, fq), []).append(row)
            elif scope == "annual" and fy is not None:
                annual.setdefault(fy, []).append(row)
            else:
                row["horizon"] = _guidance_target_label(scope, fy, fq, period_start, period_end)
                other.append(row)

            # Track history extras (3+ updates for same target)
            if len(target_updates) >= 3:
                middle = target_updates[:-2]  # everything except current and prior
                target_label = _guidance_target_label(scope, fy, fq, period_start, period_end)
                history_extras.append((label, target_label, middle, unit))

    # ── Render Quarterly Guidance ──
    # Note: guidance tables use simple pipes (not _md_table) because conditions
    # text creates extreme column widths that hurt readability when padded.
    if quarterly:
        parts.append("\n### Quarterly Guidance")
        for (fy, fq) in sorted(quarterly.keys()):
            parts.append(f"\n#### Q{fq} FY{fy}")
            parts.append("| Metric | Current | Prior | Change |")
            parts.append("|--------|---------|-------|--------|")
            rows = sorted(quarterly[(fy, fq)], key=lambda r: (r["segmented"], r["label"]))
            for row in rows:
                parts.append(f"| {row['label']} | {row['current']} | {row['prior']} | {row['change']} |")

    # ── Render Full Year Guidance ──
    if annual:
        parts.append("\n### Full Year Guidance")
        for fy in sorted(annual.keys()):
            parts.append(f"\n#### FY{fy}")
            parts.append("| Metric | Current | Prior | Change |")
            parts.append("|--------|---------|-------|--------|")
            rows = sorted(annual[fy], key=lambda r: (r["segmented"], r["label"]))
            for row in rows:
                parts.append(f"| {row['label']} | {row['current']} | {row['prior']} | {row['change']} |")

    # ── Render Other Horizons ──
    if other:
        parts.append("\n### Other Horizons")
        parts.append("| Metric | Horizon | Current | Prior | Change |")
        parts.append("|--------|---------|---------|-------|--------|")
        other.sort(key=lambda r: (r["horizon"], r["segmented"], r["label"]))
        for row in other:
            parts.append(f"| {row['label']} | {row['horizon']} | {row['current']} | {row['prior']} | {row['change']} |")

    # ── Render History Appendix (only when 3+ updates exist) ──
    if history_extras:
        parts.append("\n### Guidance History (earlier updates)")
        parts.append("| Metric | Period | Date | Value |")
        parts.append("|--------|--------|------|-------|")
        for label, target_label, middle_updates, unit in history_extras:
            for u in middle_updates:
                val = _fmt_guidance_value(u, unit)
                day = u.get("given_day", "?")
                parts.append(f"| {label} | {target_label} | {day} | {val} |")

    return "\n".join(parts)


def _render_consensus_history(bundle: dict) -> str:
    """Section 4: Consensus History — beat/miss pattern, revision momentum."""
    errors = bundle.get("builder_errors") or {}
    consensus = bundle.get("consensus")

    if "consensus" in errors:
        return f"## 4. Consensus History\n[BUILDER ERROR: {errors['consensus']}]"
    if not consensus or not isinstance(consensus, dict):
        return "## 4. Consensus History\n[NO DATA]"

    qrows = consensus.get("quarterly_rows", [])
    summary = consensus.get("summary", {})
    forward = consensus.get("forward_estimates", [])
    gaps = consensus.get("gaps", [])

    parts = ["## 4. Consensus History"]

    # ── Summary line ──
    streak = summary.get("eps_beat_streak", 0)
    avg_eps = summary.get("avg_eps_surprise_pct_last4")
    avg_rev = summary.get("avg_revenue_surprise_pct_last4")
    n_quarters = summary.get("quarterly_row_count", len(qrows))

    summary_parts = []
    if streak and streak > 0:
        summary_parts.append(f"{streak} EPS beats in last {min(streak, n_quarters)} quarters")
    if avg_eps is not None:
        summary_parts.append(f"Avg EPS surprise {'+' if avg_eps > 0 else ''}{avg_eps:.1f}%")
    if avg_rev is not None:
        summary_parts.append(f"Avg Rev surprise {'+' if avg_rev > 0 else ''}{avg_rev:.1f}%")
    if summary_parts:
        parts.append(f"Summary: {' | '.join(summary_parts)}")

    # ── Beat/Miss History table (exclude current quarter — already in Section 2) ──
    prior_rows = [r for r in qrows if not r.get("is_current_quarter")]
    if prior_rows:
        parts.append("\n### Beat/Miss History")
        headers = ["Quarter", "EPS Est", "EPS Act", "EPS Surprise", "Rev Est", "Rev Act", "Rev Surprise"]
        tbl_rows = []
        for r in prior_rows:
            fy_end = r.get("fiscalDateEnding", "?")
            eps_est = _fmt_financial_cell(r.get("estimatedEPS"), "usd")
            eps_act = _fmt_financial_cell(r.get("reportedEPS"), "usd")
            eps_surp = _fmt_pct(r.get("epsSurprisePct")) if r.get("epsSurprisePct") is not None else "—"
            rev_est = _fmt_money(r["revenueEstimate"]) if r.get("revenueEstimate") is not None else "—"
            rev_act = _fmt_money(r["revenueActual"]) if r.get("revenueActual") is not None else "—"
            rev_surp = _fmt_pct(r.get("revenueSurprisePct")) if r.get("revenueSurprisePct") is not None else "—"
            tbl_rows.append([fy_end, eps_est, eps_act, eps_surp, rev_est, rev_act, rev_surp])
        parts.append(_md_table(headers, tbl_rows))

    # ── Forward Estimates (live mode only) ──
    if forward:
        parts.append("\n### Forward Estimates (revision momentum)")
        parts.append("| Period | EPS Current | 7d ago | 30d ago | 90d ago | Rev Current |")
        parts.append("|--------|-------------|--------|---------|---------|-------------|")
        for f_row in forward:
            period = f_row.get("period", "?")
            eps_cur = f"${f_row['eps_estimate_current']}" if f_row.get("eps_estimate_current") is not None else "—"
            eps_7d = f"${f_row['eps_estimate_7d_ago']}" if f_row.get("eps_estimate_7d_ago") is not None else "—"
            eps_30d = f"${f_row['eps_estimate_30d_ago']}" if f_row.get("eps_estimate_30d_ago") is not None else "—"
            eps_90d = f"${f_row['eps_estimate_90d_ago']}" if f_row.get("eps_estimate_90d_ago") is not None else "—"
            rev_cur = _fmt_money(f_row.get("revenue_estimate_current")) if f_row.get("revenue_estimate_current") is not None else "—"
            parts.append(f"| {period} | {eps_cur} | {eps_7d} | {eps_30d} | {eps_90d} | {rev_cur} |")

    # ── Gaps ──
    if gaps:
        gap_notes = [g.get("reason") or g.get("type", "unknown") for g in gaps]
        parts.append(f"\nData notes: {'; '.join(gap_notes)}")

    return "\n".join(parts)


# ── Section 5: Prior Financial Trends ────────────────────────────────

_FINANCIAL_SECTIONS = [
    ("Income Statement Trend", [
        ("revenue", "Revenue", "money"),
        ("cost_of_revenue", "Cost of Revenue", "money"),
        ("gross_profit", "Gross Profit", "money"),
        ("sga", "SG&A", "money"),
        ("rd_expense", "R&D", "money"),
        ("depreciation_amortization", "D&A", "money"),
        ("interest_expense", "Interest Expense", "money"),
        ("income_tax", "Income Tax", "money"),
        ("operating_income", "Operating Income", "money"),
        ("net_income", "Net Income", "money"),
        ("eps_diluted", "EPS Diluted", "usd"),
    ]),
    ("Margins and Efficiency", [
        ("gross_margin_pct", "Gross Margin %", "pct"),
        ("operating_margin_pct", "Operating Margin %", "pct"),
        ("net_margin_pct", "Net Margin %", "pct"),
        ("rd_pct_revenue", "R&D % Revenue", "pct"),
        ("effective_tax_rate", "Effective Tax Rate", "pct"),
        ("diluted_shares", "Diluted Shares", "count"),
    ]),
    ("Cash Flow and Capital", [
        ("operating_cash_flow", "Operating Cash Flow", "money"),
        ("capex", "Capex", "money"),
        ("free_cash_flow", "Free Cash Flow", "money"),
        ("buybacks", "Buybacks", "money"),
        ("dividends_per_share", "Dividends / Share", "usd"),
    ]),
    ("Balance Sheet", [
        ("cash_and_equivalents", "Cash & Equivalents", "money"),
        ("total_assets", "Total Assets", "money"),
        ("stockholders_equity", "Stockholders' Equity", "money"),
        ("long_term_debt", "Long-Term Debt", "money"),
        ("debt_to_equity", "Debt / Equity", "ratio"),
    ]),
]


def _fmt_financial_cell(value, fmt_type: str) -> str:
    """Format a single financial metric cell."""
    if value is None:
        return "—"
    v = float(value)
    if not math.isfinite(v):
        return "—"
    if fmt_type == "money":
        return _fmt_money(v)
    if fmt_type == "usd":
        sign = "-" if v < 0 else ""
        return f"{sign}${abs(v):.2f}"
    if fmt_type == "pct":
        return f"{v:.1f}%"
    if fmt_type == "count":
        return _fmt_num(v)
    if fmt_type == "ratio":
        return f"{v:.2f}"
    return str(value)


def _render_prior_financials(bundle: dict) -> str:
    """Section 5: Prior Financial Trends — multi-quarter trend tables."""
    errors = bundle.get("builder_errors") or {}
    pf = bundle.get("prior_financials")

    if "prior_financials" in errors:
        return f"## 5. Prior Financial Trends\n[BUILDER ERROR: {errors['prior_financials']}]"
    if not pf or not isinstance(pf, dict):
        return "## 5. Prior Financial Trends\n[NO DATA]"

    quarters = pf.get("quarters", [])
    if not quarters:
        return "## 5. Prior Financial Trends\n[NO DATA — 0 quarters]"

    summary = pf.get("summary", {})
    gaps = pf.get("gaps", [])

    parts = ["## 5. Prior Financial Trends"]

    # Coverage line
    src = summary.get("primary_source_breakdown", {})
    src_parts = [f"{k}={v}" for k, v in src.items() if v]
    parts.append(
        f"Coverage: {summary.get('quarter_count', len(quarters))} quarters"
        f" | Sources: {', '.join(src_parts) if src_parts else '?'}"
    )

    # Quarter column headers
    q_labels = [q.get("fiscal_label", "?") for q in quarters]

    # Render each metric family as a sub-table
    for section_name, metrics in _FINANCIAL_SECTIONS:
        tbl_rows = []
        for key, label, fmt_type in metrics:
            values = []
            has_any = False
            for q in quarters:
                val = q.get(key)
                if val is not None:
                    has_any = True
                values.append(_fmt_financial_cell(val, fmt_type))
            if has_any:
                tbl_rows.append([label] + values)

        if not tbl_rows:
            continue

        parts.append(f"\n### {section_name}")
        parts.append(_md_table(["Metric"] + q_labels, tbl_rows))

    if gaps:
        parts.append(f"\nData notes: {len(gaps)} gaps in packet")

    return "\n".join(parts)


def _render_results_and_expectations(bundle: dict) -> str:
    """Section 2: Consensus bar (estimates only) + EX-99.1 reported results."""
    parts = ["## 2. Results & Expectations"]
    errors = bundle.get("builder_errors") or {}

    # ── Subsection A: Consensus Bar (estimates only — standardized for live + historical) ──
    consensus = bundle.get("consensus")

    if "consensus" in errors:
        parts.append(f"\n### Consensus Bar\n[BUILDER ERROR: {errors['consensus']}]")
    elif not consensus:
        parts.append("\n### Consensus Bar\n[NO DATA]")
    else:
        rows = consensus.get("quarterly_rows", [])
        current = next((r for r in rows if r.get("is_current_quarter")), None)

        if current:
            parts.append("\n### Consensus Bar")
            parts.append("")
            parts.append("| Metric | Estimate |")
            parts.append("|--------|----------|")

            est_eps = current.get("estimatedEPS")
            parts.append(f"| EPS | {f'${est_eps}' if est_eps is not None else '—'} |")

            est_rev = current.get("revenueEstimate")
            parts.append(f"| Revenue | {_fmt_money(est_rev)} |")
        else:
            parts.append("\n### Consensus Bar\n[No current-quarter row found]")

    # ── Subsection B: Reported Results (EX-99.1 only — other exhibits go to Reference) ──
    packet = bundle.get("8k_packet")

    if "8k_packet" in errors:
        parts.append(f"\n### Reported Results\n[BUILDER ERROR: {errors['8k_packet']}]")
    elif not packet:
        parts.append("\n### Reported Results\n[NO DATA]")
    else:
        exhibits = packet.get("exhibits_99", [])
        ex991 = next((e for e in exhibits if e.get("exhibit_number") == "EX-99.1"), None)

        if ex991:
            parts.append("\n### Reported Results (EX-99.1)")
            parts.append("")
            parts.append(ex991.get("content", "[NO CONTENT]").strip())
        else:
            parts.append("\n### Reported Results\n[No EX-99.1 found]")

    return "\n".join(parts)


def _render_reference(bundle: dict) -> str:
    """Section 9: Reference — filing metadata, other exhibits, 8-K section text."""
    parts = ["## 9. Reference"]
    packet = bundle.get("8k_packet")
    if not packet or not isinstance(packet, dict):
        parts.append("\n[NO 8-K DATA]")
        return "\n".join(parts)

    # Filing metadata
    items = packet.get("items", [])
    items_short = ", ".join(
        i.split(":")[0].replace("Item ", "") if ":" in i else i
        for i in items
    ) if items else "—"
    accession = packet.get("accession_8k", "—")
    form = packet.get("form_type", "—")
    inv = packet.get("content_inventory", {})
    parts.append(f"\n### Filing Metadata")
    parts.append(f"Accession: {accession} | Form: {form} | Items: {items_short}")
    parts.append(f"Sections: {len(inv.get('section_names', []))} | Exhibits: {', '.join(inv.get('exhibit_numbers', [])) or '—'}")

    # Other EX-99.x exhibits (not EX-99.1)
    exhibits = packet.get("exhibits_99", [])
    other_ex99 = [e for e in exhibits if e.get("exhibit_number") != "EX-99.1"]
    for ex in other_ex99:
        parts.append(f"\n### {ex.get('exhibit_number', 'Exhibit')}")
        parts.append(ex.get("content", "[NO CONTENT]").strip())

    # Non-99 exhibits (previews)
    for ex in packet.get("exhibits_other", []):
        num = ex.get("exhibit_number", "Exhibit")
        preview = ex.get("content_preview", "").strip()
        full_size = ex.get("full_size", 0)
        if preview:
            parts.append(f"\n### {num} (preview, {full_size} chars full)")
            parts.append(preview)

    # 8-K section text
    sections = packet.get("sections", [])
    if sections:
        parts.append("\n### 8-K Section Text")
        for sec in sections:
            name = sec.get("section_name", "")
            content = sec.get("content", "").strip()
            if content:
                parts.append(f"\n**{name}**\n{content}")

    # Filing text fallback
    ft = packet.get("filing_text")
    if ft:
        parts.append("\n### Filing Text (fallback)")
        parts.append(ft.strip())

    return "\n".join(parts)


# ── Section 6: Inter-Quarter Events renderer ────────────────────────

_IQ_ANALYST_CHANNELS = frozenset({
    "Analyst Ratings", "Upgrades", "Downgrades", "Reiteration",
    "Initiation", "Price Target",
})


def _iq_cell(s: str) -> str:
    """Escape a string for safe use inside a markdown table cell."""
    return s.replace("\n", " ").replace("|", "\\|")


def _iq_val(v) -> str:
    """Render a value for inter-quarter tables. None → '—', else pipe-safe str."""
    if v is None:
        return "—"
    return _iq_cell(str(v))


def _iq_bool(v) -> str:
    """Three-state boolean: True→Y, False→N, None→—."""
    if v is True:
        return "Y"
    if v is False:
        return "N"
    return "—"


def _iq_join(arr, sep=" ; ") -> str:
    """Join an array with separator. Empty/None → '—'. Pipe-safe."""
    if not arr:
        return "—"
    items = [_iq_cell(str(x)) for x in arr if x]
    return sep.join(items) if items else "—"


def _iq_header(packet: dict) -> str:
    """Block 1: Period metadata + summary counts."""
    summary = packet.get("summary", {})
    lines = [
        "## 6. Inter-Quarter Events",
        "",
        f"Ticker: {packet.get('ticker', '—')} | "
        f"Sector: {packet.get('sector', '—')} | "
        f"Industry: {packet.get('industry', '—')}",

        f"Window: {packet.get('prev_8k_ts', '—')} → "
        f"{packet.get('context_cutoff_ts', '—')} "
        f"({packet.get('context_cutoff_reason', '—')})",

        f"Dates: {packet.get('prev_day', '—')} → "
        f"{packet.get('cutoff_day', '—')} | "
        f"PIT: {packet.get('pit_cutoff') or 'N/A'} | "
        f"Mode: {packet.get('source_mode', '—')}",

        f"Schema: {packet.get('schema_version', '—')} | "
        f"Assembled: {packet.get('assembled_at', '—')}",

        f"Summary: {summary.get('trading_days_ordinary', 0)} trading days, "
        f"{summary.get('significant_move_days', 0)} significant, "
        f"{summary.get('gap_days', 0)} gap | "
        f"{summary.get('total_news', 0)} news, "
        f"{summary.get('total_filings', 0)} filings, "
        f"{summary.get('total_dividends', 0)} dividends, "
        f"{summary.get('total_splits', 0)} splits",
    ]
    return "\n".join(lines)


def _iq_days_table(days: list) -> str:
    """Block 2: Trading Days table — one row per day in the packet."""
    if not days:
        return "### Trading Days\n\n[NO TRADING DAYS]"
    headers = [
        "Date", "Trd", "Bnd", "Close", "Ret%", "SPY%", "Sect%",
        "Adj%", "Sig", "Gap",
    ]
    rows = []
    for day in days:
        p = day.get("price") or {}
        bnd = day.get("boundary_role")
        bnd_short = "prev" if bnd == "prev_boundary" else (
            "cutoff" if bnd == "cutoff_boundary" else "—")
        rows.append([
            day.get("date", "—"),
            "Y" if day.get("is_trading_day") else "N",
            bnd_short,
            _iq_val(p.get("close")),
            _iq_val(p.get("daily_return")),
            _iq_val(day.get("spy_return")),
            _iq_val(day.get("sector_return")),
            _iq_val(day.get("adj_return")),
            _iq_bool(day.get("is_significant")),
            _iq_bool(day.get("is_gap_day")),
        ])
    lines = ["### Trading Days", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_adj_returns(ev: dict) -> tuple[str, str, str]:
    """Extract adjusted returns (stock - macro) for hourly, session, daily windows."""
    fr = ev.get("forward_returns")
    if not fr or not isinstance(fr, dict):
        return ("—", "—", "—")
    vals = []
    for win_key in ("hourly", "session", "daily"):
        win = fr.get(win_key)
        if win and win.get("adj_macro") is not None:
            vals.append(_iq_val(win["adj_macro"]))
        else:
            vals.append("—")
    return (vals[0], vals[1], vals[2])


def _iq_news_table(days: list) -> str:
    """Block 3: News Events table — one row per news event, with inline adjusted returns."""
    news = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "news":
                news.append((day["date"], ev))
    if not news:
        return ""

    headers = ["Ref", "Date", "Sess", "Title", "Channels",
               "AdjH%", "AdjS%", "AdjD%"]
    rows = []
    for i, (date, ev) in enumerate(news, 1):
        adj_h, adj_s, adj_d = _iq_adj_returns(ev)
        rows.append([
            f"N{i}",
            date,
            _iq_val(ev.get("market_session")),
            _iq_cell((ev.get("title") or "").replace("\n", " ").strip()) or "—",
            _iq_join(ev.get("channels")),
            adj_h, adj_s, adj_d,
        ])
    lines = [f"### News Events ({len(news)})", "",
             "Adjusted returns = stock − macro for each window (hourly / session / daily)", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_filings_table(days: list) -> str:
    """Block 4: Filing Events table — one row per filing event, with inline adjusted returns."""
    filings = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "filing":
                filings.append((day["date"], ev))
    if not filings:
        return ""

    headers = [
        "Ref", "Date", "Sess", "Form", "Accession",
        "Items", "Exhibits", "Period", "Amend",
        "AdjH%", "AdjS%", "AdjD%",
    ]
    rows = []
    for i, (date, ev) in enumerate(filings, 1):
        adj_h, adj_s, adj_d = _iq_adj_returns(ev)
        rows.append([
            f"F{i}",
            date,
            _iq_val(ev.get("market_session")),
            _iq_val(ev.get("form_type")),
            _iq_val(ev.get("accession")),
            _iq_join(ev.get("items"), sep=" || "),
            _iq_join(ev.get("exhibit_keys")),
            _iq_val(ev.get("period_of_report")),
            _iq_bool(ev.get("is_amendment")),
            adj_h, adj_s, adj_d,
        ])
    lines = [f"### Filing Events ({len(filings)})", "",
             "Adjusted returns = stock − macro for each window (hourly / session / daily)", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_dividends_table(days: list) -> str:
    """Block 5: Dividends table."""
    divs = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "dividend":
                divs.append(ev)
    if not divs:
        return ""

    headers = ["Ref", "DeclDate", "ExDiv", "Amount", "Freq", "Type"]
    rows = []
    for i, ev in enumerate(divs, 1):
        rows.append([
            f"D{i}",
            _iq_val(ev.get("declaration_date")),
            _iq_val(ev.get("ex_dividend_date")),
            _iq_val(ev.get("cash_amount")),
            _iq_val(ev.get("frequency")),
            _iq_val(ev.get("dividend_type")),
        ])
    lines = [f"### Dividends ({len(divs)})", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_splits_table(days: list) -> str:
    """Block 6: Splits table."""
    splits = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "split":
                splits.append(ev)
    if not splits:
        return ""

    headers = ["Ref", "ExecDate", "Ratio"]
    rows = []
    for i, ev in enumerate(splits, 1):
        rows.append([
            f"S{i}",
            _iq_val(ev.get("execution_date")),
            _iq_val(ev.get("ratio_text")),
        ])
    lines = [f"### Splits ({len(splits)})", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)




def _render_inter_quarter(bundle: dict) -> str:
    """Section 6: Inter-Quarter Events — full tabular rendering."""
    name = "inter_quarter_context"
    errors = bundle.get("builder_errors") or {}
    if name in errors:
        return f"## 6. Inter-Quarter Events\n\n[BUILDER ERROR: {errors[name]}]"

    packet = bundle.get(name)
    if not packet or not isinstance(packet, dict):
        return "## 6. Inter-Quarter Events\n\n[NO DATA]"

    days = packet.get("days", [])

    blocks = [_iq_header(packet)]
    blocks.append(_iq_days_table(days))

    # Event tables — only included if non-empty
    for table_fn in [
        _iq_news_table,
        _iq_filings_table,
        _iq_dividends_table,
        _iq_splits_table,
    ]:
        block = table_fn(days)
        if block:
            blocks.append(block)

    return "\n\n".join(blocks)


# ── Section 7: Peer Earnings renderer ────────────────────────────────


def _render_peer_earnings(bundle: dict) -> str:
    """Section 7: Sector Peer Earnings & Reactions — compact table."""
    name = "peer_earnings_snapshot"
    errors = bundle.get("builder_errors") or {}
    if name in errors:
        return f"## 7. Sector Peer Earnings & Reactions\n\n[BUILDER ERROR: {errors[name]}]"

    packet = bundle.get(name)
    if not packet or not isinstance(packet, dict):
        return "## 7. Sector Peer Earnings & Reactions\n\n[NO DATA]"

    peers = packet.get("peers", [])
    industry = packet.get("industry") or "—"
    window_start = packet.get("window_start") or "—"
    cutoff = (packet.get("effective_cutoff_ts") or "—")[:10]
    summary = packet.get("summary", {})

    parts = [
        "## 7. Sector Peer Earnings & Reactions",
        "",
        f"Industry: {industry} | "
        f"Window: {window_start} → {cutoff} | "
        f"Peers: {summary.get('total_peers', 0)}",
    ]

    if not peers:
        parts.append("\n[NO PEER EARNINGS IN WINDOW]")
        return "\n".join(parts)

    # Peer table: one row per peer with key reaction metrics
    # Adjusted returns = stock − macro. Session macro not in packet, so SessStk% is raw.
    headers = [
        "Ticker", "Name", "MktCap", "Filed", "Accession", "Period",
        "Sess", "DayStk%", "AdjH%", "SessStk%", "AdjD%", "Horizon",
    ]
    rows = []
    for p in peers:
        h_stk = p.get("hourly_stock_pct")
        h_mac = p.get("hourly_macro_pct")
        d_stk = p.get("daily_stock_pct")
        d_mac = p.get("daily_macro_pct")
        adj_h = _iq_val(round(h_stk - h_mac, 2)) if h_stk is not None and h_mac is not None else "—"
        adj_d = _iq_val(round(d_stk - d_mac, 2)) if d_stk is not None and d_mac is not None else "—"
        rows.append([
            _iq_val(p.get("ticker")),
            _iq_cell((p.get("name") or "—").replace("\n", " ").strip()),
            _iq_val(p.get("mkt_cap")),
            _iq_val((p.get("filed") or "—")[:10]),
            _iq_val(p.get("accession")),
            _iq_val(p.get("period_of_report")),
            _iq_val(p.get("market_session")),
            _iq_val(d_stk),
            adj_h,
            _iq_val(p.get("session_stock_pct")),
            adj_d,
            _iq_val(p.get("context_horizon")),
        ])

    parts.append("")
    parts.append("| " + " | ".join(headers) + " |")
    parts.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        parts.append("| " + " | ".join(row) + " |")

    # Headlines sub-section: one line per headline, grouped by peer
    has_headlines = any(p.get("headlines") for p in peers)
    if has_headlines:
        parts.append("")
        parts.append("### Peer Headlines")
        hl_headers = ["Peer", "Time", "Title", "Channels"]
        hl_rows = []
        for p in peers:
            ticker = p.get("ticker", "—")
            for h in (p.get("headlines") or []):
                hl_rows.append([
                    ticker,
                    _iq_val(h.get("date")),
                    _iq_cell((h.get("title") or "—").replace("\n", " ").strip()),
                    _iq_join(h.get("channels")),
                ])
        if hl_rows:
            parts.append("")
            parts.append("| " + " | ".join(hl_headers) + " |")
            parts.append("|" + "|".join("---" for _ in hl_headers) + "|")
            for row in hl_rows:
                parts.append("| " + " | ".join(row) + " |")

    return "\n".join(parts)


# ── Section 8: Macro Snapshot renderer ────────────────────────────────


def _render_macro(bundle: dict) -> str:
    """Section 8: Macro Environment — SPY, VIX, cross-asset indicators, catalysts."""
    name = "macro_snapshot"
    errors = bundle.get("builder_errors") or {}
    if name in errors:
        return f"## 8. Macro Environment\n\n[BUILDER ERROR: {errors[name]}]"

    packet = bundle.get(name)
    if not packet or not isinstance(packet, dict):
        return "## 8. Macro Environment\n\n[NO DATA]"

    market = packet.get("market_now") or {}
    spy = market.get("spy") or {}
    sector = market.get("sector") or {}
    indicators = market.get("indicators") or {}
    catalysts = packet.get("catalysts") or {}

    parts = [
        "## 8. Macro Environment",
        "",
        f"Session: {packet.get('market_session', '—')} | "
        f"Source: {packet.get('source', '—')} | "
        f"PIT: {packet.get('pit_date', '—')}",
        f"SPY {_iq_val(spy.get('level_at_pit'))} | "
        f"VIX {_iq_val(market.get('vix_close'))} ({market.get('vix_label', '—')})",
    ]

    # ── SPY Trend ──
    spy_headers = [
        "Level", "Open→PIT", "Last60m", "Gap", "Today",
        "Yest", "5D", "20D", "YTD",
        "MA50", "MA200", "Vs50D", "Vs200D", "VolRatio",
    ]
    spy_row = [
        _iq_val(spy.get("level_at_pit")),
        _iq_val(spy.get("open_to_pit")),
        _iq_val(spy.get("last_60m")),
        _iq_val(spy.get("overnight_gap")),
        _iq_val(spy.get("today_return")),
        _iq_val(spy.get("yesterday")),
        _iq_val(spy.get("change_5d")),
        _iq_val(spy.get("change_20d")),
        _iq_val(spy.get("change_ytd")),
        _iq_val(spy.get("ma_50")),
        _iq_val(spy.get("ma_200")),
        _iq_val(spy.get("vs_50d")),
        _iq_val(spy.get("vs_200d")),
        _iq_val(spy.get("volume_ratio")),
    ]
    parts.append("")
    parts.append("### SPY Trend")
    parts.append("")
    parts.append("| " + " | ".join(spy_headers) + " |")
    parts.append("|" + "|".join("---" for _ in spy_headers) + "|")
    parts.append("| " + " | ".join(spy_row) + " |")

    # ── Sector Context ──
    if sector:
        sec_headers = ["Sector", "ETF", "LastRet", "Label", "Open→PIT", "5D", "VsSPY5D"]
        sec_row = [
            _iq_val(sector.get("name")),
            _iq_val(sector.get("etf")),
            _iq_val(sector.get("last_return")),
            _iq_val(sector.get("return_label")),
            _iq_val(sector.get("open_to_pit")),
            _iq_val(sector.get("change_5d")),
            _iq_val(sector.get("vs_spy_5d")),
        ]
        parts.append("")
        parts.append("### Sector Context")
        parts.append("")
        parts.append("| " + " | ".join(sec_headers) + " |")
        parts.append("|" + "|".join("---" for _ in sec_headers) + "|")
        parts.append("| " + " | ".join(sec_row) + " |")

    # ── Cross-Asset Indicators ──
    if indicators:
        ind_headers = ["Indicator", "Level", "LastRet", "Label", "5D", "YTD"]
        ind_rows = []
        for ind_name, ind_data in indicators.items():
            if not isinstance(ind_data, dict):
                continue
            ind_rows.append([
                _iq_cell(ind_name),
                _iq_val(ind_data.get("level")),
                _iq_val(ind_data.get("last_return")),
                _iq_val(ind_data.get("return_label")),
                _iq_val(ind_data.get("change_5d")),
                _iq_val(ind_data.get("change_ytd")),
            ])
        if ind_rows:
            parts.append("")
            parts.append("### Cross-Asset Indicators")
            parts.append("")
            parts.append("| " + " | ".join(ind_headers) + " |")
            parts.append("|" + "|".join("---" for _ in ind_headers) + "|")
            for row in ind_rows:
                parts.append("| " + " | ".join(row) + " |")

    # ── Macro Catalysts ──
    cat_rows = []
    for bucket_name, bucket_key in [("Today", "today"), ("Yesterday", "yesterday")]:
        bucket = catalysts.get(bucket_key)
        if not bucket or not isinstance(bucket, dict):
            continue
        date = bucket.get("date", "—")
        for h in bucket.get("headlines", []):
            cat_rows.append([
                bucket_name,
                date,
                _iq_val(h.get("time")),
                _iq_cell((h.get("title") or "—").replace("\n", " ").strip()),
                _iq_join(h.get("channels")),
            ])
    # Earlier is a list of [date, headline] pairs
    earlier = catalysts.get("earlier", [])
    if isinstance(earlier, list):
        for item in earlier:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                date, h = item[0], item[1]
                if isinstance(h, dict):
                    cat_rows.append([
                        "Earlier",
                        str(date),
                        _iq_val(h.get("time")),
                        _iq_cell((h.get("title") or "—").replace("\n", " ").strip()),
                        _iq_join(h.get("channels")),
                    ])

    if cat_rows:
        cat_headers = ["Bucket", "Date", "Time", "Title", "Channels"]
        parts.append("")
        parts.append("### Macro Catalysts")
        parts.append("")
        parts.append("| " + " | ".join(cat_headers) + " |")
        parts.append("|" + "|".join("---" for _ in cat_headers) + "|")
        for row in cat_rows:
            parts.append("| " + " | ".join(row) + " |")

    return "\n".join(parts)


def render_bundle_text(bundle: dict) -> str:
    """Render the 7-item bundle as decision-ordered text for the predictor."""
    sections = []

    # 1. Header
    sections.append(_render_header(bundle))

    # 2. Results & Expectations (consensus bar + EX-99.1)
    sections.append(_render_results_and_expectations(bundle))

    # 3. Forward Guidance
    sections.append(_render_forward_guidance(bundle))

    # 4. Consensus History
    sections.append(_render_consensus_history(bundle))

    # 5. Prior Financial Trends
    sections.append(_render_prior_financials(bundle))

    # 6. Inter-Quarter Events
    sections.append(_render_inter_quarter(bundle))

    # 7. Peer Earnings
    sections.append(_render_peer_earnings(bundle))

    # 8. Macro Environment
    sections.append(_render_macro(bundle))

    # 9. Reference — other exhibits, 8-K sections, lower-signal content
    sections.append(_render_reference(bundle))

    # 10. Prior Lessons (from learner — if available)
    learning_ctx = bundle.get("learning_context")
    if learning_ctx and (learning_ctx.get("ticker_lessons") or learning_ctx.get("global_lessons")):
        sections.append(_render_learning_context(learning_ctx))

    return "\n\n".join(sections)


def run_core_flow(ticker: str, quarter_info: dict,
                  pit_cutoff: str | None = None,
                  out_dir: str | None = None) -> tuple[dict, str]:
    """Build the bundle and render it as sectioned text."""
    bundle = build_prediction_bundle(
        ticker=ticker,
        quarter_info=quarter_info,
        pit_cutoff=pit_cutoff,
        out_dir=out_dir,
    )
    rendered = render_bundle_text(bundle)
    return bundle, rendered


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with parent directory creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str, ensure_ascii=False)


def write_text(path: Path, content: str) -> None:
    """Write text with parent directory creation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def get_prediction_dir(ticker: str, quarter_info: dict, save_dir: str | None = None) -> Path:
    """Return the prediction artifact directory for this event."""
    if save_dir:
        return Path(save_dir)
    quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
    return Path("earnings-analysis/Companies") / ticker.upper() / "events" / quarter_dir / "prediction"


def get_quarter_dir(ticker: str, quarter_info: dict, save_dir: str | None = None) -> Path:
    """Return the top-level quarter directory (parent of prediction/, learning/, experiments/).

    Added 2026-04-17 per obsidian_thinking.md: context_bundle.{json,txt} are
    PROMOTED from events/{Q}/prediction/ up to events/{Q}/ (quarter root) so
    they are shared by predictor + learner + future readers.
    """
    if save_dir:
        return Path(save_dir).parent
    quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
    return Path("earnings-analysis/Companies") / ticker.upper() / "events" / quarter_dir


def get_prediction_paths(ticker: str, quarter_info: dict,
                         save_dir: str | None = None) -> dict[str, Path]:
    """Return canonical paths for predictor bundle + result artifacts.

    As of obsidian_thinking.md (2026-04-17), ``context_bundle.{json,txt}``
    live at the QUARTER ROOT (``events/{Q}/``), not under ``prediction/``.
    ``result.json`` stays under ``prediction/``.
    """
    base_dir = get_prediction_dir(ticker, quarter_info, save_dir)
    q_dir = get_quarter_dir(ticker, quarter_info, save_dir)
    return {
        "base_dir": base_dir,
        "bundle_path": q_dir / "context_bundle.json",
        "rendered_path": q_dir / "context_bundle_rendered.txt",
        "result_path": base_dir / "result.json",
    }


def validate_prediction_result(payload: dict[str, Any],
                               expected_ticker: str,
                               expected_quarter: str) -> None:
    """Light validation for the first predictor MVP output."""
    required = [
        "schema_version",
        "ticker",
        "quarter_label",
        "direction",
        "confidence_score",
        "confidence_bucket",
        "expected_move_range_pct",
        "magnitude_bucket",
        "key_drivers",
        "data_gaps",
        "evidence_ledger",
        "analysis",
        "predicted_at",
        "model_version",
        "prompt_version",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"prediction/result.json missing keys: {', '.join(missing)}")

    if payload["schema_version"] != "prediction_result.v1":
        raise ValueError(f"unexpected schema_version: {payload['schema_version']}")

    if str(payload["ticker"]).upper() != expected_ticker.upper():
        raise ValueError(
            f"ticker mismatch in prediction/result.json: {payload['ticker']} != {expected_ticker}"
        )

    if payload["quarter_label"] != expected_quarter:
        raise ValueError(
            "quarter_label mismatch in prediction/result.json: "
            f"{payload['quarter_label']} != {expected_quarter}"
        )

    if payload["direction"] not in {"long", "short", "no_call"}:
        raise ValueError(f"invalid direction: {payload['direction']}")

    if payload["confidence_bucket"] not in {"high", "moderate", "low", "no_call"}:
        raise ValueError(f"invalid confidence_bucket: {payload['confidence_bucket']}")

    if payload["magnitude_bucket"] not in {"large", "medium", "small", "none"}:
        raise ValueError(f"invalid magnitude_bucket: {payload['magnitude_bucket']}")

    score = payload["confidence_score"]
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError(f"invalid confidence_score: {score}")

    move_range = payload["expected_move_range_pct"]
    if (
        not isinstance(move_range, list)
        or len(move_range) != 2
        or not all(isinstance(x, (int, float)) for x in move_range)
    ):
        raise ValueError("expected_move_range_pct must be a 2-number array")

    for key in ("key_drivers", "data_gaps", "evidence_ledger"):
        if not isinstance(payload[key], list):
            raise ValueError(f"{key} must be a list")

    if not isinstance(payload["analysis"], str) or not payload["analysis"].strip():
        raise ValueError("analysis must be a non-empty string")


# ── Attribution / Learner Helpers ────────────────────────────────────


COMPANIES_DIR = Path("earnings-analysis/Companies")
LEARNINGS_DIR = Path("earnings-analysis/learnings")


def get_learning_dir(ticker: str, quarter_info: dict,
                     save_dir: str | None = None) -> Path:
    """Return the learning artifact directory for this event.

    Renamed from ``get_attribution_dir`` per obsidian_thinking.md
    (2026-04-17). The folder name changed from ``attribution/`` to
    ``learning/``; the schema name ``attribution_result.v2`` is preserved
    (schema versions are not renamed per plan).
    """
    if save_dir:
        return Path(save_dir)
    quarter_dir = quarter_info.get("quarter_label") or quarter_info["accession_8k"]
    return COMPANIES_DIR / ticker.upper() / "events" / quarter_dir / "learning"


# Thin alias for 1-release backward compat. Existing callers using the
# old name continue to work transparently. Remove after callers migrate.
def get_attribution_dir(ticker: str, quarter_info: dict,
                        save_dir: str | None = None) -> Path:
    """DEPRECATED alias for get_learning_dir (1-release backward compat)."""
    return get_learning_dir(ticker, quarter_info, save_dir)


def get_learning_paths(ticker: str, quarter_info: dict,
                       save_dir: str | None = None) -> dict[str, Path]:
    """Return canonical paths for learner result + lesson artifacts.

    As of obsidian_thinking.md (2026-04-17):
      - ``base_dir`` is ``events/{Q}/learning/`` (renamed from attribution/)
      - ``context_bundle_path`` is at the QUARTER ROOT (promoted from
        prediction/)
    """
    learn_dir = get_learning_dir(ticker, quarter_info, save_dir)
    q_dir = learn_dir.parent
    pred_dir = q_dir / "prediction"
    return {
        "base_dir": learn_dir,
        "result_path": learn_dir / "result.json",
        "prediction_result_path": pred_dir / "result.json",
        "context_bundle_path": q_dir / "context_bundle.json",
    }


# Thin alias — preserves "get_attribution_paths" import for 1 release.
# Remove once all callers migrate.
def get_attribution_paths(ticker: str, quarter_info: dict,
                          save_dir: str | None = None) -> dict[str, Path]:
    """DEPRECATED alias for get_learning_paths (1-release backward compat)."""
    return get_learning_paths(ticker, quarter_info, save_dir)


def get_learnings_paths(ticker: str) -> dict[str, Path]:
    """Return canonical paths for ticker + global lesson files."""
    return {
        "ticker_lessons_path": LEARNINGS_DIR / "ticker" / f"{ticker.upper()}.json",
        "global_lessons_path": LEARNINGS_DIR / "global.json",
    }


# ── Attribution Result Validator (re-exported from standalone module) ─

from validate_attribution import validate_attribution_result  # noqa: F401 — stdlib-only, hook-safe


# ── PIT Cutoff Derivation (three-tier rule per learner.md §3) ──


def derive_learner_pit(events: list[dict], current_index: int,
                       live_state_path: Path | None = None
                       ) -> tuple[str | None, str]:
    """Derive the PIT cutoff for the learner at position current_index.

    Three-tier rule:
      1. Q(n+1) exists in events → use Q(n+1)'s filed_8k
      2. No Q(n+1), but a live cycle exists → use live quarter's filed_8k
      3. No Q(n+1) and no live cycle → use current invocation time

    Returns (pit_cutoff, pit_boundary_source).
    For live mode (caller decides), returns (None, "").
    ⚠️ HUMAN REVIEW GATE — verify correctness across all tickers.
    """
    # Tier 1: next quarter in the events list
    if current_index + 1 < len(events):
        next_event = events[current_index + 1]
        next_filed = next_event.get("filed_8k")
        if next_filed:
            return next_filed, "next_quarter"

    # Tier 2: live cycle exists (live_state.json has a filed_8k for a quarter
    # that's not yet in the events list)
    if live_state_path and live_state_path.exists():
        try:
            ls = json.loads(live_state_path.read_text(encoding="utf-8"))
            live_filed = ls.get("filed_8k")
            if live_filed:
                return live_filed, "live_cycle"
        except (json.JSONDecodeError, OSError):
            pass

    # Tier 3: fallback to current invocation time
    return datetime.now(timezone.utc).isoformat(), "invocation_time"


# ── actual_return Normalization (Neo4j PUBLISHED_AS → normalized packet) ─


_RETURN_FIELD_MAP = {
    "daily_stock": "daily_stock_pct",
    "hourly_stock": "hourly_stock_pct",
    "session_stock": "session_stock_pct",
    "daily_macro": "daily_macro_pct",
    "daily_sector": "daily_sector_pct",
    "daily_industry": "daily_industry_pct",
}


def normalize_actual_return(neo4j_record: dict) -> dict:
    """Normalize Neo4j PUBLISHED_AS relationship fields to the learner contract.

    Input: dict with raw Neo4j field names (daily_stock, hourly_stock, etc.)
    Output: dict with normalized names (daily_stock_pct, hourly_stock_pct, etc.)
    """
    result: dict[str, Any] = {}
    for neo4j_name, normalized_name in _RETURN_FIELD_MAP.items():
        val = neo4j_record.get(neo4j_name)
        result[normalized_name] = float(val) if val is not None else None
    result["market_session"] = neo4j_record.get("market_session") or neo4j_record.get("market_session_8k")
    return result


def fetch_actual_return(ticker: str, accession: str) -> dict | None:
    """Fetch actual return data from Neo4j for a given 8-K accession.

    Queries the PRIMARY_FILER relationship on the 8-K report.
    Returns normalized actual_return dict, or None if not found or daily_stock missing.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        log.error("neo4j driver not available — cannot fetch actual_return")
        return None

    uri = os.environ.get("NEO4J_URI", "bolt://minisforum3:30687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")

    query_str = """
    MATCH (r:Report {accessionNo: $accession})-[p:PRIMARY_FILER]->(c:Company {ticker: $ticker})
    RETURN p.daily_stock AS daily_stock,
           p.hourly_stock AS hourly_stock,
           p.session_stock AS session_stock,
           p.daily_macro AS daily_macro,
           p.daily_sector AS daily_sector,
           p.daily_industry AS daily_industry,
           r.market_session AS market_session
    LIMIT 1
    """
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run(query_str, accession=accession, ticker=ticker.upper())
            record = result.single()
        driver.close()
    except Exception as e:
        log.error("Neo4j query failed for actual_return: %s", e)
        return None

    if not record:
        log.warning("No PUBLISHED_AS relationship found for %s / %s", ticker, accession)
        return None

    raw = dict(record)
    if raw.get("daily_stock") is None:
        log.warning("daily_stock is NULL for %s / %s — hard gate not met", ticker, accession)
        return None

    return normalize_actual_return(raw)


# ── Learner Orchestration (post-prediction sequential flow) ─────────


def run_learner_for_quarter(
    ticker: str,
    quarter_info: dict,
    events: list[dict],
    current_index: int,
    pit_mode: str = "historical",
    live_state_path: Path | None = None,
) -> dict | None:
    """Run the full learner pipeline for one quarter.

    1. Check hard gates (prediction/result.json + daily_stock)
    2. Derive PIT cutoff
    3. Fetch actual_return from Neo4j
    4. Invoke learner via SDK
    5. Validate attribution/result.json (post-return)
    6. Append ticker + global lessons

    Returns the validated attribution result dict, or None on failure.
    """
    ticker = ticker.upper()
    attr_paths = get_learning_paths(ticker, quarter_info)
    learn_paths = get_learnings_paths(ticker)
    accession = quarter_info.get("accession_8k", "")

    # ── Hard gate 1: prediction must exist ──
    if not attr_paths["prediction_result_path"].exists():
        log.warning("Learner skip %s %s: prediction/result.json does not exist",
                     ticker, quarter_info.get("quarter_label"))
        return None

    # ── If attribution already exists, run derived-write recovery FIRST ──
    # Runs before fetch_actual_return() so recovery works even if Neo4j is down.
    # A prior run may have written result.json but crashed before ticker/global appends.
    # Completion requires all 3 artifacts (plan §10 completion semantics).
    if attr_paths["result_path"].exists():
        log.info("Learner %s %s: attribution/result.json exists, running derived-write recovery",
                  ticker, quarter_info.get("quarter_label"))
        try:
            existing = json.loads(attr_paths["result_path"].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.error("Existing result.json unreadable for %s %s: %s — deleting and re-running",
                       ticker, quarter_info.get("quarter_label"), e)
            attr_paths["result_path"].unlink(missing_ok=True)
            existing = None
        if existing is not None:
            errors = validate_attribution_result(existing, ticker, quarter_info.get("quarter_label", ""))
            if errors:
                log.error("Existing result.json invalid for %s %s: %s — deleting and re-running",
                           ticker, quarter_info.get("quarter_label"), "; ".join(errors[:3]))
                attr_paths["result_path"].unlink(missing_ok=True)
            else:
                # Valid result exists — ensure derived writes are complete
                try:
                    append_ticker_lesson(ticker, existing)
                    append_global_lessons(existing)
                    log.info("Derived-write recovery complete for %s %s", ticker, quarter_info.get("quarter_label"))
                except Exception as e:
                    log.error("Derived-write recovery failed for %s %s: %s", ticker, quarter_info.get("quarter_label"), e)
                    return None
                return existing

    # ── Hard gate 2: actual returns (daily_stock must exist) ──
    actual_return = fetch_actual_return(ticker, accession)
    if actual_return is None:
        log.warning("Learner skip %s %s: daily_stock not available (hard gate)",
                     ticker, quarter_info.get("quarter_label"))
        return None

    # ── PIT cutoff derivation ──
    if pit_mode == "historical":
        pit_cutoff, pit_boundary_source = derive_learner_pit(
            events, current_index, live_state_path
        )
    else:
        pit_cutoff, pit_boundary_source = None, "invocation_time"

    # ── Invoke learner via SDK ──
    log.info("Running learner for %s %s (PIT=%s, source=%s)",
             ticker, quarter_info.get("quarter_label"), pit_cutoff, pit_boundary_source)

    result_path = attr_paths["result_path"]
    result_path.parent.mkdir(parents=True, exist_ok=True)

    _sdk_result, learner_session_id = run_learner_via_sdk(
        ticker=ticker,
        quarter_info=quarter_info,
        actual_return=actual_return,
        pit_mode=pit_mode,
        pit_cutoff=pit_cutoff,
        pit_boundary_source=pit_boundary_source,
        result_path=result_path,
        prediction_result_path=attr_paths["prediction_result_path"],
        context_bundle_path=attr_paths["context_bundle_path"],
        prior_lessons_path=learn_paths["ticker_lessons_path"],
    )

    # ── Post-return validation ──
    if not result_path.exists():
        log.error("Learner failed %s %s: attribution/result.json not written",
                   ticker, quarter_info.get("quarter_label"))
        return None

    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        log.error("Learner failed %s %s: result.json not valid JSON: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None

    errors = validate_attribution_result(
        payload, ticker, quarter_info.get("quarter_label", "")
    )
    if errors:
        log.error("Learner failed %s %s: validation errors: %s",
                   ticker, quarter_info.get("quarter_label"), "; ".join(errors[:3]))
        # Retry once: delete bad file, re-invoke WITH validation errors fed
        # back into the prompt (H2 informed retry, amendment 2026-04-17 per
        # .claude/plans/learner-edits.md §6.6).
        result_path.unlink(missing_ok=True)
        log.info(
            "Retrying learner for %s %s (1 retry, feeding %d validation errors back)",
            ticker, quarter_info.get("quarter_label"), len(errors),
        )
        _sdk_retry_result, learner_session_id = run_learner_via_sdk(
            ticker=ticker,
            quarter_info=quarter_info,
            actual_return=actual_return,
            pit_mode=pit_mode,
            pit_cutoff=pit_cutoff,
            pit_boundary_source=pit_boundary_source,
            result_path=result_path,
            prediction_result_path=attr_paths["prediction_result_path"],
            context_bundle_path=attr_paths["context_bundle_path"],
            prior_lessons_path=learn_paths["ticker_lessons_path"],
            prior_validation_errors=errors,
        )
        if not result_path.exists():
            log.error("Learner retry failed %s %s: no result.json after retry",
                       ticker, quarter_info.get("quarter_label"))
            return None
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.error("Learner retry failed %s %s: result.json still invalid JSON",
                       ticker, quarter_info.get("quarter_label"))
            return None
        errors = validate_attribution_result(
            payload, ticker, quarter_info.get("quarter_label", "")
        )
        if errors:
            log.error("Learner retry failed %s %s: still invalid after retry: %s",
                       ticker, quarter_info.get("quarter_label"), "; ".join(errors[:3]))
            return None

    # Stamp authoritative model_version + sdk_session_id; side-effect render + harvest.
    payload = finalize_learning_result(
        result_path=result_path,
        model=LEARNER.model,
        sdk_session_id=learner_session_id,
        ticker=ticker,
        quarter_label=quarter_info.get("quarter_label"),
    )

    # ── Derived writes: ticker.json + global.json ──
    try:
        append_ticker_lesson(ticker, payload)
        log.info("Appended ticker lesson for %s %s", ticker, quarter_info.get("quarter_label"))
    except Exception as e:
        log.error("Ticker lesson append failed for %s %s: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None

    try:
        append_global_lessons(payload)
        log.info("Appended global lessons for %s %s", ticker, quarter_info.get("quarter_label"))
    except Exception as e:
        log.error("Global lesson append failed for %s %s: %s",
                   ticker, quarter_info.get("quarter_label"), e)
        return None

    log.info("Learner complete for %s %s", ticker, quarter_info.get("quarter_label"))
    return payload


# ── Lesson File Operations (Python owns all derived writes) ─────────

import fcntl
import tempfile


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically: temp file + os.replace. Creates parents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        dir=path.parent, suffix=".tmp", mode="w", encoding="utf-8", delete=False
    )
    try:
        json.dump(data, tmp, indent=2, default=str, ensure_ascii=False)
        tmp.close()
        os.replace(tmp.name, path)
    except BaseException:
        tmp.close()
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


def append_ticker_lesson(ticker: str, attribution_result: dict) -> Path:
    """Extract feedback from attribution result and append to ticker lessons file.

    Atomic write. No locking needed (single-ticker sequential processing).
    Returns the path written.
    """
    paths = get_learnings_paths(ticker)
    path = paths["ticker_lessons_path"]

    # Read existing or create skeleton
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {
            "schema_version": "ticker_lessons.v1",
            "ticker": ticker.upper(),
            "updated_at": None,
            "lessons": [],
        }

    # Extract compact lesson entry from attribution result
    fb = attribution_result.get("feedback", {})
    pc = fb.get("prediction_comparison", {})
    entry = {
        "quarter_label": attribution_result.get("quarter_label"),
        "attributed_at": attribution_result.get("attributed_at"),
        # T1.5b: stamp source event's PIT metadata for read-side filtering.
        # Copied verbatim from attribution_result.v2 top-level fields.
        "source_filed_8k": attribution_result.get("filed_8k"),
        "source_pit_cutoff": attribution_result.get("pit_cutoff"),
        "direction_correct": pc.get("direction_correct"),
        "actual_daily_pct": (attribution_result.get("actual_return") or {}).get("daily_stock_pct"),
        "predicted_direction": pc.get("predicted_direction"),
        "predicted_confidence_score": pc.get("predicted_confidence_score"),
        "primary_driver_summary": (attribution_result.get("primary_driver") or {}).get("summary"),
        "primary_driver_category": (attribution_result.get("primary_driver") or {}).get("category"),
        "what_worked": fb.get("what_worked", []),
        "what_failed": fb.get("what_failed", []),
        "predictor_lessons": fb.get("predictor_lessons", []),
        "data_lessons": fb.get("data_lessons", []),
        "why": fb.get("why"),
    }

    # Idempotent upsert-by-quarter_label (amendment 2026-04-17): remove any
    # prior entry for this quarter before appending, so derived-write recovery
    # or a re-run replaces rather than duplicates.
    target_ql = entry["quarter_label"]
    data["lessons"] = [l for l in data["lessons"] if l.get("quarter_label") != target_ql]
    data["lessons"].append(entry)
    data["updated_at"] = attribution_result.get("attributed_at")
    _atomic_write_json(path, data)
    return path


def append_global_lessons(attribution_result: dict) -> Path | None:
    """Upsert global_observations into learnings/global.json for this quarter.

    Amendment 2026-04-17 (per .claude/plans/learner-edits.md §6.2):

      - **Always returns the path** on success (was: returned None when
        observations were empty). Docstring change is intentional — the
        function now runs the flock-protected upsert UNCONDITIONALLY so that a
        re-run producing zero global_observations still purges stale prior
        entries for (source_ticker, quarter_label).
      - **Upsert-by-source-key** (source_ticker, quarter_label): prior entries
        for the same key are removed before the new ones are appended.
        Idempotent under derived-write recovery or any re-run.
      - Enrichment dict passes through structured routing fields
        (related_tickers, target_sector) and stamps source_sector via
        _lookup_company_sector. `scope_key` is NOT passed through (removed
        from schema; validator rejects it on writes).

    Uses fcntl.flock for concurrent-ticker safety. Return type annotation
    stays Path | None — the function can still return None if an exception
    propagates after the lock releases, even though the contract on success
    is "always returns path".
    """
    observations = attribution_result.get("global_observations", [])
    # Normalize src_ticker to UPPER for consistent upsert-key integrity.
    # Mixed-case tickers (e.g., "AAPL" from one call, "aapl" from another) would
    # otherwise produce distinct upsert keys and leave duplicate entries.
    src_ticker = (attribution_result.get("ticker") or "").upper().strip()
    src_quarter = attribution_result.get("quarter_label")

    # Enrich each observation with structured routing + audit fields.
    # NOTE: scope_key is DROPPED here — never passed through to global.json.
    # Routing fields (related_tickers, target_sector) are passed through by
    # key-presence only, so stored entries don't get null-padded on their
    # non-owning scopes. The upstream validator + PreToolUse hook guarantee
    # each routing field appears only on its owning scope before this writer
    # runs; we simply mirror that contract into storage.
    # T1.5b: stamp source event's PIT metadata from attribution_result top-level
    # fields. These are storage metadata used by build_learning_context's
    # read-side filter; they are NOT new learner-output contract fields.
    src_filed_8k = attribution_result.get("filed_8k")
    src_pit_cutoff = attribution_result.get("pit_cutoff")

    enriched = []
    for obs in observations:
        entry = {
            "scope":            obs.get("scope"),
            "source_ticker":    src_ticker,
            "source_sector":    _lookup_company_sector(src_ticker),  # audit-only, NOT routing
            "quarter_label":    src_quarter,
            "attributed_at":    attribution_result.get("attributed_at"),
            "source_filed_8k":  src_filed_8k,
            "source_pit_cutoff": src_pit_cutoff,
            "lesson":           obs.get("lesson"),
        }
        if "related_tickers" in obs:
            entry["related_tickers"] = obs["related_tickers"]
        if "target_sector" in obs:
            entry["target_sector"] = obs["target_sector"]
        enriched.append(entry)

    path = LEARNINGS_DIR / "global.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Locked read-modify-write for concurrency safety.
    # Upsert step — always runs, even when enriched == [] (purges stale entries).
    lock_path = path.with_suffix(".lock")
    with open(lock_path, "w") as lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                data = {
                    "schema_version": "global_lessons.v1",
                    "updated_at": None,
                    "entries": [],
                }
            # Remove any prior entries for this (source_ticker, quarter_label)
            # before extending — deterministic upsert-by-source-key.
            key = (src_ticker, src_quarter)
            data["entries"] = [
                e for e in data["entries"]
                if (e.get("source_ticker"), e.get("quarter_label")) != key
            ]
            data["entries"].extend(enriched)
            data["updated_at"] = attribution_result.get("attributed_at")
            _atomic_write_json(path, data)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)

    return path


# ── Learning Context Builder (read-time filtering for predictor) ─────


def build_learning_context(ticker: str, sector: str | None = None,
                           base_dir: Path | None = None,
                           pit_cutoff: str | None = None) -> dict:
    """Build learning context for predictor consumption.

    Amendment 2026-04-17 (per .claude/plans/learner-edits.md §4.3 / §6.3):
      - Structured-field routing: cross_ticker by ``related_tickers`` list
        membership; sector by ``target_sector`` enum (normalized compare); macro
        always included. No regex. No per-entry Neo4j calls.
      - ``sector_lookup`` parameter DROPPED (was codex-era threading).
      - Six named exclusion counters; observability log ALWAYS fires (even when
        global.json is absent).
      - ``except JSONDecodeError / OSError`` now log ``log.error`` (was silent).

    Amendment 2026-04-17 T1.5b (per .claude/plans/learner.md §🔥):
      - New ``pit_cutoff`` parameter. When not None, filter lessons whose
        ``source_pit_cutoff`` is strictly after ``pit_cutoff`` across ALL four
        scopes (ticker, sector, macro, cross_ticker). Legacy entries without
        ``source_pit_cutoff`` are treated as post-cutoff in historical mode
        (excluded) and passed through in live mode.
      - When pit_cutoff is None (production real-time path), NO filter is
        applied — preserves pre-T1.5b behavior exactly.
      - Two new observability counters: ``ticker_post_cutoff``,
        ``global_post_cutoff``.
    """
    # Normalize ticker case at function entry. Stored related_tickers are
    # validator-enforced UPPERCASE, and the ticker-lessons filename is UPPERCASE.
    # Without this normalization, a caller passing "aapl" would silently drop
    # every ["AAPL"] cross_ticker lesson and miss its own ticker.json.
    ticker = (ticker or "").upper().strip()
    learnings_dir = base_dir or LEARNINGS_DIR
    ticker_path = learnings_dir / "ticker" / f"{ticker}.json"
    global_path = learnings_dir / "global.json"

    result: dict[str, Any] = {
        "ticker_lessons": [],
        "global_lessons": [],
        "ticker_ref": str(ticker_path) if ticker_path.exists() else None,
        "global_ref": str(global_path) if global_path.exists() else None,
    }

    # T1.5b PIT filter helper. Returns True iff the entry passes the cutoff.
    # Live mode (pit_cutoff is None) → always True (no filter).
    # Historical mode → entry must have source_pit_cutoff AND it must be
    # chronologically <= pit_cutoff.
    #
    # IMPORTANT: naive string comparison is UNSAFE across different UTC
    # offsets (e.g., "...-04:00" vs "...+00:00") — lexical order diverges
    # from chronological order when timestamps are close in real time but
    # differ in offset. Reported by external review 2026-04-17 with this
    # repro: src=2024-06-12T16:19:05-04:00 (20:19:05 UTC) and
    # pit=2024-06-12T20:18:00+00:00 (20:18:00 UTC) — src is chronologically
    # 65s LATER but lexically appears earlier ('16' < '20'). Must parse to
    # tz-aware datetime before comparing. This mirrors the existing PIT
    # pattern in peer_earnings_snapshot._parse_dt_for_pit().
    def _passes_pit(entry: dict) -> bool:
        if pit_cutoff is None:
            return True
        src_pit_raw = entry.get("source_pit_cutoff")
        if src_pit_raw is None:
            return False  # legacy: no bound → cannot be trusted in historical mode
        try:
            # "Z" suffix → "+00:00" for portability across Python versions.
            src_dt = datetime.fromisoformat(str(src_pit_raw).replace("Z", "+00:00"))
            cut_dt = datetime.fromisoformat(str(pit_cutoff).replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            return False  # malformed → defensive exclude in historical mode
        # Both must be tz-aware — comparing naive + aware raises TypeError
        # and would hide the bug silently.
        if src_dt.tzinfo is None or cut_dt.tzinfo is None:
            return False
        return src_dt <= cut_dt

    ticker_post_cutoff = 0
    global_post_cutoff = 0

    # ── Ticker lessons: most recent 8 ──
    if ticker_path.exists():
        try:
            data = json.loads(ticker_path.read_text(encoding="utf-8"))
            lessons = data.get("lessons", [])
            # Sort by attributed_at descending, dedupe by quarter_label (keep most recent),
            # then take most recent 8. Dedup handles re-bootstrap/retry reruns.
            lessons.sort(key=lambda x: x.get("attributed_at", ""), reverse=True)
            seen_quarters: set[str] = set()
            deduped: list[dict] = []
            for lesson in lessons:
                ql = lesson.get("quarter_label", "")
                if ql not in seen_quarters:
                    seen_quarters.add(ql)
                    deduped.append(lesson)
            # T1.5b: apply PIT filter; count exclusions.
            filtered: list[dict] = []
            for lesson in deduped:
                if _passes_pit(lesson):
                    filtered.append(lesson)
                else:
                    ticker_post_cutoff += 1
            result["ticker_lessons"] = filtered[:8]
        except json.JSONDecodeError as e:
            log.error("ticker.json malformed — no ticker lessons loaded for %s: %s", ticker, e)
        except OSError as e:
            log.error("ticker.json read failed — no ticker lessons loaded for %s: %s", ticker, e)

    # ── Global lessons: structured-field routing, per-scope caps ──
    # Counters initialized to zero BEFORE the file-exists check so the
    # observability log at the end always fires with a full, consistent shape
    # — even if global.json is absent (first-ever run / post-wipe state).
    sector_entries: list[dict] = []
    macro_entries: list[dict] = []
    cross_entries: list[dict] = []
    excluded = {
        "sector_mismatch": 0,
        "current_sector_unknown": 0,
        "cross_ticker_not_listed": 0,
        "cross_ticker_missing_related": 0,
        "unknown_scope": 0,
        "legacy_schema": 0,
    }
    normalized_current_sector = _normalize_sector(sector)

    if global_path.exists():
        try:
            data = json.loads(global_path.read_text(encoding="utf-8"))
            entries = data.get("entries", [])

            for e in entries:
                # T1.5b: PIT filter fires BEFORE scope routing for all scopes,
                # so global_post_cutoff is disjoint from scope-specific counters.
                if not _passes_pit(e):
                    global_post_cutoff += 1
                    continue

                scope = e.get("scope")

                if scope == "sector":
                    ts = e.get("target_sector")
                    if ts is None:
                        # Legacy/old-schema entry (pre-fix) — transparently excluded
                        excluded["legacy_schema"] += 1
                        continue
                    if not normalized_current_sector:
                        # CURRENT ticker's sector unknown — cannot route sector-scope.
                        # (Distinct from legacy_schema, which is about the ENTRY.)
                        excluded["current_sector_unknown"] += 1
                        continue
                    if _normalize_sector(ts) == normalized_current_sector:
                        sector_entries.append(e)
                    else:
                        excluded["sector_mismatch"] += 1

                elif scope == "macro":
                    macro_entries.append(e)

                elif scope == "cross_ticker":
                    rt = e.get("related_tickers")
                    if not rt:
                        # Legacy/old-schema entry OR learner error past validator
                        excluded["cross_ticker_missing_related"] += 1
                        continue
                    if ticker in rt:
                        cross_entries.append(e)
                    else:
                        excluded["cross_ticker_not_listed"] += 1

                else:
                    excluded["unknown_scope"] += 1

            # Sort each bucket by recency, apply per-scope caps
            for bucket in (sector_entries, macro_entries, cross_entries):
                bucket.sort(key=lambda x: x.get("attributed_at", ""), reverse=True)

            # Dedupe within each scope: exact text match after normalization
            def _dedupe(entries: list[dict]) -> list[dict]:
                seen: set[str] = set()
                out = []
                for e in entries:
                    k = (e.get("lesson") or "").strip().lower()
                    if k and k not in seen:
                        seen.add(k)
                        out.append(e)
                return out

            sector_entries = _dedupe(sector_entries)[:4]
            macro_entries = _dedupe(macro_entries)[:4]
            cross_entries = _dedupe(cross_entries)[:2]

            result["global_lessons"] = sector_entries + macro_entries + cross_entries
        except json.JSONDecodeError as e:
            log.error("global.json malformed — no global lessons loaded for %s: %s", ticker, e)
        except OSError as e:
            log.error("global.json read failed — no global lessons loaded for %s: %s", ticker, e)

    # Observability log — fires ALWAYS, even if global_path didn't exist.
    # Names must match §4.5 contract exactly. Six exclusion counters so any
    # future silent-drop regression appears immediately as an anomalous count.
    # T1.5b adds two more: ticker_post_cutoff, global_post_cutoff.
    log.info(
        "learning_context %s(sector=%s, pit=%s): "
        "included[sector=%d macro=%d cross=%d] "
        "excluded[sector_mismatch=%d current_sector_unknown=%d "
        "cross_ticker_not_listed=%d cross_ticker_missing_related=%d "
        "unknown_scope=%d legacy_schema=%d "
        "ticker_post_cutoff=%d global_post_cutoff=%d]",
        ticker, sector, pit_cutoff,
        len(sector_entries), len(macro_entries), len(cross_entries),
        excluded["sector_mismatch"],
        excluded["current_sector_unknown"],
        excluded["cross_ticker_not_listed"],
        excluded["cross_ticker_missing_related"],
        excluded["unknown_scope"],
        excluded["legacy_schema"],
        ticker_post_cutoff,
        global_post_cutoff,
    )

    return result


# ── Learning Context Renderer (for prediction bundle text) ──────────


def _render_learning_context(learning_ctx: dict) -> str:
    """Render learning context into a readable section for the prediction bundle."""
    parts: list[str] = []
    parts.append("## Prior Lessons (from learner)")

    ticker_lessons = learning_ctx.get("ticker_lessons", [])
    global_lessons = learning_ctx.get("global_lessons", [])

    if not ticker_lessons and not global_lessons:
        parts.append("\nNo prior lessons available (first prediction for this ticker).")
        return "\n".join(parts)

    # ── Ticker-specific lessons ──
    if ticker_lessons:
        parts.append(f"\n### Ticker Lessons ({len(ticker_lessons)} most recent quarters)\n")
        for lesson in ticker_lessons:
            ql = lesson.get("quarter_label", "?")
            correct = lesson.get("direction_correct")
            actual = lesson.get("actual_daily_pct")
            pred_dir = lesson.get("predicted_direction", "?")
            cat = lesson.get("primary_driver_category", "?")
            icon = "correct" if correct else "wrong"
            parts.append(f"**{ql}** — prediction {icon} ({pred_dir}), actual {actual:+.2f}%, driver: {cat}")
            for pl in lesson.get("predictor_lessons", []):
                parts.append(f"  - Predictor: {pl}")
            for dl in lesson.get("data_lessons", []):
                parts.append(f"  - Data: {dl}")
            why = lesson.get("why")
            if why:
                parts.append(f"  - Why: {why}")
            parts.append("")

    # ── Global lessons — split into three sub-sections by scope (amendment
    # 2026-04-17): heading was previously "Cross-Ticker Insights" for all three
    # scopes which was misleading. scope_key removed from display — rendering
    # uses routing fields (target_sector, related_tickers) only.
    if global_lessons:
        by_scope: dict[str, list[dict]] = {"sector": [], "macro": [], "cross_ticker": []}
        for entry in global_lessons:
            by_scope.setdefault(entry.get("scope"), []).append(entry)

        if by_scope["sector"]:
            parts.append(f"\n### Sector Lessons ({len(by_scope['sector'])} entries)\n")
            for entry in by_scope["sector"]:
                ts = entry.get("target_sector") or "?"
                src = entry.get("source_ticker") or "?"
                parts.append(f"- [sector:{ts}] ({src}) {entry.get('lesson', '')}")

        if by_scope["macro"]:
            parts.append(f"\n### Macro Lessons ({len(by_scope['macro'])} entries)\n")
            for entry in by_scope["macro"]:
                src = entry.get("source_ticker") or "?"
                parts.append(f"- [macro] ({src}) {entry.get('lesson', '')}")

        if by_scope["cross_ticker"]:
            parts.append(f"\n### Cross-Ticker Lessons ({len(by_scope['cross_ticker'])} entries)\n")
            for entry in by_scope["cross_ticker"]:
                rt = entry.get("related_tickers") or []
                src = entry.get("source_ticker") or "?"
                parts.append(f"- [cross:{','.join(rt)}] ({src}) {entry.get('lesson', '')}")
        parts.append("")

    return "\n".join(parts)


# ── Learner SDK Invocation ───────────────────────────────────────────

_LEARNER_SKILL_PATH = Path(".claude/skills/earnings-learner/SKILL.md")


def _load_learner_skill_content() -> str:
    """Load SKILL.md content, stripping YAML frontmatter."""
    raw = _LEARNER_SKILL_PATH.read_text(encoding="utf-8")
    # Strip frontmatter (--- ... ---)
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            raw = raw[end + 3:].lstrip("\n")
    return raw


def _build_learner_prompt(
    skill_content: str,
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,
) -> str:
    """Assemble the full learner prompt: SKILL.md instructions + runtime INPUTS.

    ``prior_validation_errors`` (amendment 2026-04-17, H2 informed retry per
    .claude/plans/learner-edits.md §6.6): when non-empty, appended as a
    dedicated "YOUR PRIOR OUTPUT WAS REJECTED" block so the 1-retry path is
    informed rather than blind. Default None for first-attempt calls.
    """
    actual_return_json = json.dumps(actual_return, indent=2, default=str)
    inputs_section = f"""--- INPUTS ---
TICKER: {ticker}
QUARTER: {quarter_info.get('quarter_label', 'UNKNOWN')}
FILED_8K: {quarter_info.get('filed_8k', 'UNKNOWN')}
ACCESSION: {quarter_info.get('accession_8k', 'UNKNOWN')}
PIT_MODE: {pit_mode}
PIT_CUTOFF: {pit_cutoff or 'null'}
PIT_BOUNDARY_SOURCE: {pit_boundary_source}
RESULT_PATH: {result_path}
PREDICTION_RESULT: {prediction_result_path}
CONTEXT_BUNDLE: {context_bundle_path}
ACTUAL_RETURN: {actual_return_json}
PRIOR_LESSONS: {prior_lessons_path}
"""
    if prior_validation_errors:
        numbered = "\n".join(
            f"  {i + 1}. {e}" for i, e in enumerate(prior_validation_errors)
        )
        retry_block = (
            "\n--- YOUR PRIOR OUTPUT WAS REJECTED ---\n"
            "The previous attempt failed schema validation with these errors:\n"
            f"{numbered}\n\n"
            "Fix these EXACT errors and re-emit attribution/result.json. "
            "Do not change other fields; only correct the listed shape issues.\n"
        )
        return f"{skill_content}\n\n{inputs_section}{retry_block}"
    return f"{skill_content}\n\n{inputs_section}"


async def _run_learner_via_sdk(
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,
) -> tuple[str | None, str | None]:
    """Invoke the learner via SDK embed (main session, full tool access).

    Loads SKILL.md content as prompt text — NOT via /earnings-learner fork.
    This gives the session Agent tool access for all 14 Data SubAgents.

    ``prior_validation_errors`` threads through to ``_build_learner_prompt`` so
    the retry path in ``run_learner_for_quarter`` can feed the previous
    attempt's validation errors back into the prompt (H2, informed retry).

    Returns:
        Tuple of ``(final_result, session_id)``. ``session_id`` is captured
        using the hybrid approach (per obsidian_thinking.md locked decision §6):
        primary path is ``getattr(msg, "session_id", None)`` which works
        against SDK v0.1.61 where every message class exposes it; fallback to
        the older ``SystemMessage(subtype="init").data.get("session_id")``
        shape for SDK-version resilience.
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    cli_path, creds_path = _assert_claude_code_oauth_ready()
    log.info("Learner SDK auth mode: Claude Code OAuth via %s (creds %s)", cli_path, creds_path)

    skill_content = _load_learner_skill_content()
    prompt = _build_learner_prompt(
        skill_content=skill_content,
        ticker=ticker,
        quarter_info=quarter_info,
        actual_return=actual_return,
        pit_mode=pit_mode,
        pit_cutoff=pit_cutoff,
        pit_boundary_source=pit_boundary_source,
        result_path=result_path,
        prediction_result_path=prediction_result_path,
        context_bundle_path=context_bundle_path,
        prior_lessons_path=prior_lessons_path,
        prior_validation_errors=prior_validation_errors,
    )

    # Drain stderr via callback — without this, a chatty subprocess stderr
    # pipe fills and the child dies with "Command failed with exit code 1".
    def _stderr_sink(line: str) -> None:
        log.info("learner stderr: %s", line.rstrip())

    final_result: str | None = None
    session_id: str | None = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            **LEARNER.as_sdk_kwargs(),
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            stderr=_stderr_sink,
            cli_path=cli_path,
            env=_sdk_subprocess_env(),
        ),
    ):
        # Hybrid session_id capture — primary path (SDK v0.1.61+) + fallback.
        if session_id is None:
            session_id = getattr(msg, "session_id", None) or getattr(msg, "sessionId", None)
        if session_id is None and getattr(msg, "subtype", "") == "init":
            data = getattr(msg, "data", {}) or {}
            session_id = data.get("session_id") or data.get("sessionId")
        if hasattr(msg, "result"):
            final_result = str(msg.result)
    return final_result, session_id


def run_learner_via_sdk(
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,
) -> tuple[str | None, str | None]:
    """Sync wrapper for the learner SDK call.

    ``prior_validation_errors`` threads through to ``_run_learner_via_sdk`` for
    the H2 informed-retry path. Default None for first-attempt calls.

    Returns ``(final_result, session_id)`` tuple — see ``_run_learner_via_sdk``.
    """
    try:
        return asyncio.run(_run_learner_via_sdk(
            ticker=ticker,
            quarter_info=quarter_info,
            actual_return=actual_return,
            pit_mode=pit_mode,
            pit_cutoff=pit_cutoff,
            pit_boundary_source=pit_boundary_source,
            result_path=result_path,
            prediction_result_path=prediction_result_path,
            context_bundle_path=context_bundle_path,
            prior_lessons_path=prior_lessons_path,
            prior_validation_errors=prior_validation_errors,
        ))
    except ImportError as e:
        raise RuntimeError(
            "claude_agent_sdk is not available; cannot run learner"
        ) from e


# ── Predictor Canonicalization Layer (Option A) ─────────────────────
# SKILL.md is UNCHANGED. LLM writes the 7 analytic fields. Python adds
# 8 metadata/derived fields after SDK write, before validation.
# Thresholds from .claude/plans/predictor-revamp.md §389-390 (canonical).

import hashlib
import shutil

# Backward-compat alias for existing callers — authoritative source is
# config.llm_models.PREDICTOR.model
PREDICTOR_MODEL_ID = PREDICTOR.model
_PREDICTOR_SKILL_PATH = Path(".claude/skills/earnings-prediction/SKILL.md")
_CLAUDE_CREDS_PATH = Path.home() / ".claude" / ".credentials.json"
_SYSTEM_CLAUDE_CANDIDATES = [
    Path.home() / ".local" / "bin" / "claude",
    Path(shutil.which("claude")) if shutil.which("claude") else None,
]

# System CLI path — use the user's installed Claude Code CLI with local OAuth
# credentials, not the SDK's bundled fallback.
_SYSTEM_CLAUDE_CLI = next(
    (str(path) for path in _SYSTEM_CLAUDE_CANDIDATES if path and path.exists()),
    None,
)


def _sdk_cli_path() -> str | None:
    """Return the claude CLI path for SDK invocation (system CLI if available)."""
    return _SYSTEM_CLAUDE_CLI


def _sdk_subprocess_env() -> dict[str, str]:
    """Strip Anthropic API-key auth from the Claude Code subprocess environment.

    The earnings predictor/learner must run through local Claude Code OAuth
    credentials, not direct Anthropic API-key auth.
    """
    return {
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_AUTH_TOKEN": "",
    }


def _strip_anthropic_api_auth_env() -> list[str]:
    """Remove direct Anthropic API auth from the current process environment."""
    stripped: list[str] = []
    for env_key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if os.environ.pop(env_key, None):
            stripped.append(env_key)
    return stripped


def _assert_claude_code_oauth_ready() -> tuple[str, str]:
    """Fail closed unless Claude Code OAuth credentials are available.

    Returns:
        tuple[str, str]: (cli_path, credentials_path)
    """
    stripped = _strip_anthropic_api_auth_env()
    if stripped:
        log.warning(
            "Stripped direct Anthropic API auth from orchestrator process before "
            "Claude Code SDK invocation: %s",
            ", ".join(stripped),
        )

    cli_path = _sdk_cli_path()
    if not cli_path:
        raise RuntimeError(
            "Claude Code CLI not found. Expected ~/.local/bin/claude or a "
            "'claude' binary on PATH for OAuth-backed execution."
        )

    if not _CLAUDE_CREDS_PATH.exists():
        raise RuntimeError(
            f"Claude Code OAuth credentials not found: {_CLAUDE_CREDS_PATH}"
        )

    try:
        creds = json.loads(_CLAUDE_CREDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(
            f"Could not read Claude Code credentials at {_CLAUDE_CREDS_PATH}"
        ) from e

    oauth = creds.get("claudeAiOauth") or {}
    if not oauth.get("accessToken"):
        raise RuntimeError(
            "Claude Code OAuth credentials are missing claudeAiOauth.accessToken; "
            "predictor/learner will not run in API-key mode."
        )

    return cli_path, str(_CLAUDE_CREDS_PATH)


def _derive_confidence_bucket(direction: str, score: int | float) -> str:
    """Per predictor-revamp.md: 70-100=high, 40-69=moderate, 0-39=low, no_call=no_call."""
    if direction == "no_call":
        return "no_call"
    if score >= 70:
        return "high"
    if score >= 40:
        return "moderate"
    return "low"


def _derive_magnitude_bucket(direction: str, move_range: list) -> str:
    """Per predictor-revamp.md: <2%=small, 2-4%=medium, >=4%=large, no_call=none.
    Midpoint of expected_move_range_pct used as the magnitude."""
    if direction == "no_call":
        return "none"
    try:
        midpoint = (float(move_range[0]) + float(move_range[1])) / 2.0
    except (TypeError, ValueError, IndexError):
        return "none"
    if midpoint >= 4.0:
        return "large"
    if midpoint >= 2.0:
        return "medium"
    return "small"


def _hash_prompt_version(skill_path: Path = _PREDICTOR_SKILL_PATH) -> str:
    """Deterministic prompt_version: short sha256 hash of SKILL.md content.
    Auto-invalidates when SKILL.md changes. Fallback to 'v1' if unreadable."""
    try:
        content = skill_path.read_bytes()
        return "v1-" + hashlib.sha256(content).hexdigest()[:12]
    except OSError:
        return "v1"


def finalize_learning_result(
    *,
    result_path: Path,
    model: str,
    sdk_session_id: str | None = None,
    ticker: str | None = None,
    quarter_label: str | None = None,
    experiment_name: str | None = None,
) -> dict:
    """Stamp authoritative metadata onto learning/result.json + side-effects.

    Mirrors the predictor's finalize_prediction_result() in principle but
    intentionally narrow: ONLY overwrites ``model_version`` + adds
    ``sdk_session_id`` flat top-level field. Does NOT rewrite any other
    learner-authored field. The learner's prompt controls everything else;
    Python is only the source of truth for which model actually ran + the
    SDK session id for thinking harvest linkage.

    Side-effects (best-effort, try/except so neither blocks the JSON write):
      - Generates ``result.md`` sidecar via result_md_renderer
      - Calls thinking_harvester.harvest() to produce ``thinking.md`` +
        ``subagents/`` under ``events/{Q}/learning/``

    Added 2026-04-17 per obsidian_thinking.md. Old name
    ``finalize_attribution_result`` is kept as a thin alias for 1 release.
    """
    if not result_path.exists():
        raise RuntimeError(f"Learner did not write {result_path}")
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["model_version"] = model
    # sdk_session_id: never overwrite an existing non-null value with None
    # (protects resume paths where the caller doesn't re-capture a session id).
    # Rule: stamp when caller provides a real value OR when the key is missing;
    # otherwise preserve whatever is already there.
    existing_sid = payload.get("sdk_session_id")
    if sdk_session_id is not None:
        payload["sdk_session_id"] = sdk_session_id
    elif "sdk_session_id" not in payload:
        payload["sdk_session_id"] = None
    # else: payload already has a value (None or real); keep it unchanged.
    effective_sid = payload.get("sdk_session_id")
    result_path.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    _render_and_harvest_best_effort(
        component="learning",
        result_path=result_path,
        ticker=ticker or payload.get("ticker"),
        quarter_label=quarter_label or payload.get("quarter_label"),
        sdk_session_id=effective_sid,
        experiment_name=experiment_name,
    )
    return payload


# Thin alias — 1-release backward-compat for any caller still using the old name.
def finalize_attribution_result(
    *,
    result_path: Path,
    model: str,
    sdk_session_id: str | None = None,
    ticker: str | None = None,
    quarter_label: str | None = None,
    experiment_name: str | None = None,
) -> dict:
    """DEPRECATED alias for finalize_learning_result (1-release compat)."""
    return finalize_learning_result(
        result_path=result_path,
        model=model,
        sdk_session_id=sdk_session_id,
        ticker=ticker,
        quarter_label=quarter_label,
        experiment_name=experiment_name,
    )


def finalize_prediction_result(
    result_path: Path,
    ticker: str,
    quarter_info: dict,
    model: str = PREDICTOR_MODEL_ID,
    sdk_session_id: str | None = None,
    experiment_name: str | None = None,
) -> None:
    """Enrich LLM-written prediction with deterministic metadata.

    LLM writes 7 analytic fields per SKILL.md; Python adds 8 fields here
    plus ``sdk_session_id`` (flat top-level; nullable).
    Runs AFTER SDK write, BEFORE validator. Does not change /earnings-prediction.

    Side-effects (best-effort, try/except so neither blocks the JSON write):
      - Generates ``result.md`` sidecar via result_md_renderer
      - Calls thinking_harvester.harvest() to produce ``thinking.md`` under
        ``events/{Q}/prediction/`` (or under ``experiments/{experiment_name}/``
        when ``experiment_name`` is provided — used by A/B baseline callsites).
    """
    if not result_path.exists():
        raise RuntimeError(f"Predictor did not write {result_path}")

    payload = json.loads(result_path.read_text(encoding="utf-8"))

    # Required LLM-written fields (must be present — predictor's job)
    for required in ("direction", "confidence_score", "expected_move_range_pct"):
        if required not in payload:
            raise ValueError(
                f"LLM output missing required analytic field '{required}' — predictor SKILL.md contract violation"
            )

    # Python-owned metadata
    payload["schema_version"] = "prediction_result.v1"
    payload["ticker"] = ticker.upper()
    payload["quarter_label"] = quarter_info["quarter_label"]
    payload["predicted_at"] = datetime.now(timezone.utc).isoformat()
    payload["model_version"] = model
    payload["prompt_version"] = _hash_prompt_version()
    # sdk_session_id: never overwrite an existing non-null value with None.
    # Protects resume paths (e.g., run_ab_baseline.py) where caller passes
    # None because the SDK wasn't re-invoked.
    if sdk_session_id is not None:
        payload["sdk_session_id"] = sdk_session_id
    elif "sdk_session_id" not in payload:
        payload["sdk_session_id"] = None
    # else: existing value (None or real) preserved.
    effective_sid = payload.get("sdk_session_id")

    # Deterministic derivations from LLM output
    payload["confidence_bucket"] = _derive_confidence_bucket(
        payload["direction"], payload["confidence_score"]
    )
    payload["magnitude_bucket"] = _derive_magnitude_bucket(
        payload["direction"], payload["expected_move_range_pct"]
    )

    # Atomic write back (temp file + os.replace)
    _atomic_write_json(result_path, payload)

    _render_and_harvest_best_effort(
        component="prediction" if experiment_name is None else "prediction_no_lessons",
        result_path=result_path,
        ticker=ticker,
        quarter_label=quarter_info["quarter_label"],
        sdk_session_id=effective_sid,
        experiment_name=experiment_name,
    )


def _render_and_harvest_best_effort(
    *,
    component: str,
    result_path: Path,
    ticker: str | None,
    quarter_label: str | None,
    sdk_session_id: str | None,
    experiment_name: str | None,
) -> None:
    """Run result_md render + thinking_harvester in try/except.

    Neither failure blocks the result.json write (per locked decision:
    "Silent-fail semantics on harvest").
    """
    # result.md sidecar
    try:
        from result_md_renderer import render as _render
        md_path = result_path.with_name("result.md")
        _render(component, result_path, md_path)
    except Exception as e:
        log.warning("result.md render failed for %s: %s", result_path, e)

    # thinking.md harvest — requires ticker + quarter + session_id
    if not (ticker and quarter_label):
        log.info("Skipping thinking harvest (missing ticker/quarter): %s", result_path)
        return
    try:
        from thinking_harvester import harvest as _harvest
        # Map renderer component name to harvester thinking_type
        if component == "prediction_no_lessons":
            harv_type = "prediction"
            harv_exp = experiment_name or "prediction_no_lessons"
        elif component in ("prediction", "learning", "guidance"):
            harv_type = component
            harv_exp = experiment_name
        else:
            log.info("Unknown component for harvest: %s", component)
            return
        _harvest(
            thinking_type=harv_type,
            ticker=ticker,
            quarter=quarter_label,
            session_id=sdk_session_id,
            experiment_name=harv_exp,
        )
    except Exception as e:
        log.warning(
            "thinking_harvester failed for %s %s (session=%s): %s",
            ticker, quarter_label, sdk_session_id, e,
        )


async def _run_predictor_via_sdk(bundle_path: Path,
                                 rendered_path: Path,
                                 result_path: Path) -> tuple[str | None, str | None]:
    """Invoke the predictor skill once via Claude Agent SDK.

    Returns ``(final_result, session_id)`` — session_id is captured via the
    hybrid approach (per obsidian_thinking.md locked decision §6).
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    cli_path, creds_path = _assert_claude_code_oauth_ready()
    log.info("Predictor SDK auth mode: Claude Code OAuth via %s (creds %s)", cli_path, creds_path)

    prompt = (
        "Run /earnings-prediction with these exact paths:\n"
        f"BUNDLE_PATH={bundle_path}\n"
        f"RENDERED_BUNDLE_PATH={rendered_path}\n"
        f"RESULT_PATH={result_path}\n"
        "Read the bundle, write RESULT_PATH as JSON, and stop."
    )

    # Drain stderr via callback — without this, a chatty subprocess stderr
    # pipe fills and the child dies with "Command failed with exit code 1".
    def _stderr_sink(line: str) -> None:
        log.debug("predictor stderr: %s", line.rstrip())

    final_result: str | None = None
    session_id: str | None = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            **PREDICTOR.as_sdk_kwargs(),
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            stderr=_stderr_sink,
            cli_path=cli_path,
            env=_sdk_subprocess_env(),
        ),
    ):
        # Hybrid session_id capture — primary path (SDK v0.1.61+) + fallback.
        if session_id is None:
            session_id = getattr(msg, "session_id", None) or getattr(msg, "sessionId", None)
        if session_id is None and getattr(msg, "subtype", "") == "init":
            data = getattr(msg, "data", {}) or {}
            session_id = data.get("session_id") or data.get("sessionId")
        if hasattr(msg, "result"):
            final_result = str(msg.result)
    return final_result, session_id


def run_predictor_via_sdk(bundle_path: Path,
                          rendered_path: Path,
                          result_path: Path) -> tuple[str | None, str | None]:
    """Sync wrapper for the one-turn predictor SDK call.

    Returns ``(final_result, session_id)`` tuple.
    """
    try:
        return asyncio.run(_run_predictor_via_sdk(bundle_path, rendered_path, result_path))
    except ImportError as e:
        raise RuntimeError(
            "claude_agent_sdk is not available; cannot run --predict"
        ) from e


# ── CLI ──────────────────────────────────────────────────────────────

def _resolve_pit_mode(args, quarter_info):
    """Resolve ``(pit_cutoff, mode_label)`` from CLI args + quarter_info.

    Implements T1.5a per ``.claude/plans/learner.md`` §🔥. Rules:

    - ``--live`` and ``--pit`` are mutually exclusive → ``ValueError``.
    - ``--live`` → ``(None, "live")`` regardless of other flags.
    - ``--pit X`` → ``(X, "historical")`` regardless of other flags.
    - No ``--pit`` / ``--live`` with ``--predict`` or ``--learn``
      → ``(quarter_info["filed_8k"], "historical")``.  This is the default
      that closes the T1.5a bug: manual CLI runs against historical
      accessions no longer silently fall into live mode.
    - No ``--pit`` / ``--live`` / ``--predict`` / ``--learn``
      → ``(None, "live")``.  Preserves bundle-inspection mode (``--save``
      alone) where the caller explicitly didn't ask for a prediction.

    Raises ``ValueError`` if the default branch would fire but
    ``quarter_info`` is missing ``filed_8k`` — the caller must then pass
    ``--pit`` or ``--live`` explicitly.
    """
    if args.live and args.pit:
        raise ValueError(
            "--live and --pit are mutually exclusive. Pass exactly one."
        )
    if args.live:
        return None, "live"
    if args.pit:
        return args.pit, "historical"
    if args.predict or args.learn:
        filed_8k = (quarter_info or {}).get("filed_8k")
        if not filed_8k:
            raise ValueError(
                "Cannot default pit_cutoff to filed_8k: quarter_info is "
                "missing filed_8k. Pass --pit explicitly or --live."
            )
        return filed_8k, "historical"
    return None, "live"


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Earnings prediction bundle assembly")
    parser.add_argument("ticker", help="Company ticker")
    parser.add_argument("accession", nargs="?", help="8-K accession number")
    parser.add_argument("--quarter-info-json", default=None,
                        help="Path to a quarter_info JSON file (alternative to accession)")
    parser.add_argument("--pit", default=None, help="PIT cutoff (ISO8601) for historical mode")
    parser.add_argument("--live", action="store_true",
                        help="Force live mode (pit_cutoff=None). Mutually exclusive with --pit. "
                             "Required to preserve old accidental-live behavior on historical accessions.")
    parser.add_argument("--save", action="store_true", help="Write bundle artifacts to disk")
    parser.add_argument("--predict", action="store_true",
                        help="Save bundle artifacts and run one predictor SDK call")
    parser.add_argument("--learn", action="store_true",
                        help="Run learner/attribution after prediction for this quarter")
    parser.add_argument("--save-dir", default=None,
                        help="Optional output directory for saved bundle artifacts")
    args = parser.parse_args()

    if bool(args.accession) == bool(args.quarter_info_json):
        parser.error("Provide exactly one of ACCESSION or --quarter-info-json")

    if args.quarter_info_json:
        print(f"Loading quarter info for {args.ticker} from {args.quarter_info_json} ...", flush=True)
        quarter_info = load_quarter_info_json(args.quarter_info_json)
    else:
        print(f"Resolving quarter identity for {args.ticker} / {args.accession} ...", flush=True)
        quarter_info = resolve_quarter_info(args.ticker, args.accession)

    validate_quarter_info(quarter_info)
    print(f"  filed_8k:    {quarter_info['filed_8k']}")
    print(f"  period:      {quarter_info['period_of_report']}")
    print(f"  session:     {quarter_info['market_session']}")
    print(f"  prev_8k_ts:  {quarter_info['prev_8k_ts']}")
    print(f"  quarter:     {quarter_info['quarter_label']}")
    print(f"  source:      {quarter_info.get('quarter_identity_source', 'n/a')}")
    if quarter_info.get("gaps"):
        for g in quarter_info["gaps"]:
            print(f"  GAP: {g['type']}: {g['reason']}")
    print()

    # T1.5a: resolve PIT mode (default=filed_8k for --predict/--learn; --live opt-in;
    # --pit CLI wins). Historical calibration is now PIT-safe by construction.
    try:
        pit_cutoff, pit_mode = _resolve_pit_mode(args, quarter_info)
    except ValueError as e:
        parser.error(str(e))
    log.info("PIT mode resolved: mode=%s cutoff=%s (cli_pit=%s cli_live=%s)",
             pit_mode, pit_cutoff, args.pit, args.live)
    print(f"  pit_mode:    {pit_mode}")
    print(f"  pit_cutoff:  {pit_cutoff}")
    print()

    print(f"Building prediction bundle ({len(BUILDERS)} builders in parallel) ...", flush=True)
    t0 = datetime.now()
    bundle, rendered = run_core_flow(
        ticker=args.ticker,
        quarter_info=quarter_info,
        pit_cutoff=pit_cutoff,
        out_dir=args.save_dir,
    )
    elapsed = (datetime.now() - t0).total_seconds()

    ok = [k for k in BUNDLE_ITEM_ORDER if k not in (bundle.get("builder_errors") or {})]
    fail = list((bundle.get("builder_errors") or {}).keys())
    print(f"  Done in {elapsed:.1f}s — {len(ok)} ok, {len(fail)} failed")
    if fail:
        for name in fail:
            print(f"  FAIL: {name}: {bundle['builder_errors'][name]}")
    print()

    print(f"Rendered bundle: {len(rendered)} chars, {rendered.count(chr(10))} lines")

    paths = get_prediction_paths(args.ticker, quarter_info, args.save_dir)
    if args.save or args.predict:
        write_json(paths["bundle_path"], bundle)
        write_text(paths["rendered_path"], rendered)
        print(f"Saved: {paths['bundle_path']}")
        print(f"Saved: {paths['rendered_path']}")

    if args.predict:
        if paths["result_path"].exists():
            paths["result_path"].unlink()

        print("Running predictor via SDK ...", flush=True)
        t1 = datetime.now()
        _pred_result, predictor_session_id = run_predictor_via_sdk(
            paths["bundle_path"], paths["rendered_path"], paths["result_path"]
        )
        pred_elapsed = (datetime.now() - t1).total_seconds()

        if not paths["result_path"].exists():
            raise RuntimeError("Predictor finished without writing prediction/result.json")

        # Canonicalize: LLM wrote 7 analytic fields; Python adds 8 metadata/derived + sdk_session_id.
        # Side-effects (best-effort): result.md sidecar + thinking.md harvest.
        finalize_prediction_result(
            result_path=paths["result_path"],
            ticker=args.ticker,
            quarter_info=quarter_info,
            model=PREDICTOR_MODEL_ID,
            sdk_session_id=predictor_session_id,
        )

        with open(paths["result_path"], encoding="utf-8") as f:
            prediction = json.load(f)

        validate_prediction_result(
            prediction,
            expected_ticker=args.ticker,
            expected_quarter=quarter_info["quarter_label"],
        )

        print(f"Prediction written in {pred_elapsed:.1f}s: {paths['result_path']}")
        print(
            f"  direction: {prediction['direction']} | "
            f"confidence: {prediction['confidence_score']} ({prediction['confidence_bucket']}) | "
            f"magnitude: {prediction['magnitude_bucket']}"
        )

    if args.learn:
        # Load event.json for PIT derivation (needs chronological quarter list)
        event_json_path = COMPANIES_DIR / args.ticker.upper() / "events" / "event.json"
        if not event_json_path.exists():
            raise RuntimeError(f"event.json not found at {event_json_path} — run get_quarterly_filings first")
        event_data = json.loads(event_json_path.read_text(encoding="utf-8"))
        events = event_data.get("events", [])

        # Find current quarter's index in the chronological events list
        target_ql = quarter_info["quarter_label"]
        target_acc = quarter_info["accession_8k"]
        current_index = None
        for i, e in enumerate(events):
            if e.get("quarter_label") == target_ql or e.get("accession_8k") == target_acc:
                current_index = i
                break
        if current_index is None:
            raise RuntimeError(
                f"Quarter {target_ql} ({target_acc}) not found in event.json — "
                f"rebuild with get_quarterly_filings"
            )

        live_state_path = COMPANIES_DIR / args.ticker.upper() / "events" / "live_state.json"

        print(f"\nRunning learner for {args.ticker} {target_ql} ...", flush=True)
        t2 = datetime.now()
        attribution = run_learner_for_quarter(
            ticker=args.ticker,
            quarter_info=quarter_info,
            events=events,
            current_index=current_index,
            pit_mode="historical",
            live_state_path=live_state_path,
        )
        learn_elapsed = (datetime.now() - t2).total_seconds()

        if attribution:
            print(f"Learner complete in {learn_elapsed:.1f}s")
            pd = attribution.get("primary_driver", {})
            fb = attribution.get("feedback", {})
            pc = fb.get("prediction_comparison", {})
            print(f"  primary_driver: {pd.get('category', '?')} — {pd.get('summary', '?')[:80]}")
            print(f"  direction_correct: {pc.get('direction_correct')}")
            print(f"  predictor_lessons: {len(fb.get('predictor_lessons', []))}")
        else:
            print(f"Learner failed or skipped for {args.ticker} {target_ql} after {learn_elapsed:.1f}s")


def _run_v2_regression_tests():
    """V2 regression tests for _fmt_guidance_value with corrected canonical_unit values.
    Verifies renderer behavior once V2 resolver produces correct units.
    Run with full env: python3 scripts/earnings/earnings_orchestrator.py --test"""

    passed = failed = 0
    def check(name, actual, expected_substr):
        nonlocal passed, failed
        if expected_substr in actual:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL {name}: expected '{expected_substr}' in {actual!r}")

    # Corrected usd: face-value dollar formatting (was m_usd → billions in V1)
    check("fmt_eps_usd", _fmt_guidance_value({'low': 3.2, 'high': 3.4}, 'usd'), '$3.20-$3.40')
    check("fmt_dps_usd", _fmt_guidance_value({'low': 0.32, 'high': 0.32}, 'usd'), '$0.32')

    # Corrected count: absolute quantity (was m_usd → $300M in V1)
    r_count = _fmt_guidance_value({'low': 300e6, 'high': 300e6}, 'count')
    check("fmt_count_300m", r_count, '300')

    # m_usd unchanged: aggregate money still formatted in B/M
    check("fmt_rev_musd", _fmt_guidance_value({'low': 94000, 'high': 98000}, 'm_usd'), 'B')

    # Ratios
    check("fmt_pct", _fmt_guidance_value({'low': 42, 'high': 42}, 'percent'), '42%')
    check("fmt_pct_yoy", _fmt_guidance_value({'low': 5, 'high': 7}, 'percent_yoy'), 'YoY')
    check("fmt_bps", _fmt_guidance_value({'low': 50, 'high': 50}, 'basis_points'), 'bps')
    check("fmt_x", _fmt_guidance_value({'low': 2.5, 'high': 2.5}, 'x'), '2.5x')

    # Qualitative-only
    check("fmt_qual", _fmt_guidance_value({'qualitative': 'strong growth expected'}, 'unknown'), 'strong growth')

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    return failed == 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        sys.exit(0 if _run_v2_regression_tests() else 1)
    main()
