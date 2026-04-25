"""Section 3 — Forward Guidance + supporting formatters/comparators.

Extracted from earnings_orchestrator.py (commit 10/20) — bodies copied verbatim
from the pre-renderer-extract baseline at lines 338, 421, 462, 482, 492, 514, 519
(per Appendix A.5). Imports `_fmt_money`, `_fmt_num` from the sibling
_formatters module.
"""
from __future__ import annotations

import math
from typing import Any

from ._formatters import _fmt_money, _fmt_num


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
