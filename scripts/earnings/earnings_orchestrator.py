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
from quarter_identity import resolve_quarter_info

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


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


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
        f"{summary.get('total_series', '?')} series | "
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
    if quarterly:
        parts.append("\n### Quarterly Guidance")
        for (fy, fq) in sorted(quarterly.keys()):
            parts.append(f"\n#### Q{fq} FY{fy}")
            parts.append("| Metric | Current | Prior | Change |")
            parts.append("|--------|---------|-------|--------|")
            # Sort: Total first (no segment marker), then alphabetical
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


def render_bundle_text(bundle: dict) -> str:
    """Render the 7-item bundle as decision-ordered text for the predictor."""
    sections = []

    # 1. Header
    sections.append(_render_header(bundle))

    # 2. Results & Expectations (consensus bar + EX-99.1)
    sections.append(_render_results_and_expectations(bundle))

    # 3. Forward Guidance
    sections.append(_render_forward_guidance(bundle))

    # 4-8: TODO — remaining builder sections render as raw JSON until replaced
    remaining = [n for n in BUNDLE_ITEM_ORDER
                 if n not in ("8k_packet", "consensus", "guidance_history")]
    for i, name in enumerate(remaining, 4):
        title = SECTION_TITLES[name]
        sections.append(f"## {i}. {title}")

        if name in (bundle.get("builder_errors") or {}):
            sections.append(f"[BUILDER ERROR: {bundle['builder_errors'][name]}]")
            continue

        item = bundle.get(name)
        if item is None:
            sections.append("[NO DATA]")
            continue

        sections.append(json.dumps(item, indent=2, default=str, ensure_ascii=False))

    # 9. Reference — other exhibits, 8-K sections, lower-signal content
    sections.append(_render_reference(bundle))

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


def get_prediction_paths(ticker: str, quarter_info: dict,
                         save_dir: str | None = None) -> dict[str, Path]:
    """Return canonical paths for predictor bundle + result artifacts."""
    base_dir = get_prediction_dir(ticker, quarter_info, save_dir)
    return {
        "base_dir": base_dir,
        "bundle_path": base_dir / "context_bundle.json",
        "rendered_path": base_dir / "context_bundle_rendered.txt",
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


async def _run_predictor_via_sdk(bundle_path: Path,
                                 rendered_path: Path,
                                 result_path: Path) -> str | None:
    """Invoke the predictor skill once via Claude Agent SDK."""
    from claude_agent_sdk import query, ClaudeAgentOptions

    prompt = (
        "Run /earnings-prediction with these exact paths:\n"
        f"BUNDLE_PATH={bundle_path}\n"
        f"RENDERED_BUNDLE_PATH={rendered_path}\n"
        f"RESULT_PATH={result_path}\n"
        "Read the bundle, write RESULT_PATH as JSON, and stop."
    )

    final_result = None
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=20,
        ),
    ):
        if hasattr(msg, "result"):
            final_result = str(msg.result)
    return final_result


def run_predictor_via_sdk(bundle_path: Path,
                          rendered_path: Path,
                          result_path: Path) -> str | None:
    """Sync wrapper for the one-turn predictor SDK call."""
    try:
        return asyncio.run(_run_predictor_via_sdk(bundle_path, rendered_path, result_path))
    except ImportError as e:
        raise RuntimeError(
            "claude_agent_sdk is not available; cannot run --predict"
        ) from e


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Earnings prediction bundle assembly")
    parser.add_argument("ticker", help="Company ticker")
    parser.add_argument("accession", nargs="?", help="8-K accession number")
    parser.add_argument("--quarter-info-json", default=None,
                        help="Path to a quarter_info JSON file (alternative to accession)")
    parser.add_argument("--pit", default=None, help="PIT cutoff (ISO8601) for historical mode")
    parser.add_argument("--save", action="store_true", help="Write bundle artifacts to disk")
    parser.add_argument("--predict", action="store_true",
                        help="Save bundle artifacts and run one predictor SDK call")
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

    print(f"Building prediction bundle ({len(BUILDERS)} builders in parallel) ...", flush=True)
    t0 = datetime.now()
    bundle, rendered = run_core_flow(
        ticker=args.ticker,
        quarter_info=quarter_info,
        pit_cutoff=args.pit,
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
        run_predictor_via_sdk(paths["bundle_path"], paths["rendered_path"], paths["result_path"])
        pred_elapsed = (datetime.now() - t1).total_seconds()

        if not paths["result_path"].exists():
            raise RuntimeError("Predictor finished without writing prediction/result.json")

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


if __name__ == "__main__":
    main()
