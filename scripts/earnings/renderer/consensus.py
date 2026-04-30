"""Section 4 — Consensus History (beat/miss + revision momentum).

Extracted from earnings_orchestrator.py (commit 12/20) — body copied verbatim
from the pre-renderer-extract baseline at line 656.

All formatter imports come from `_formatters` (single canonical source).
"""
from __future__ import annotations

from ._formatters import _md_table, _fmt_money, _fmt_pct, _fmt_financial_cell, _fmt_eps, _fmt_eps_delta


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
    # U8: keys aligned to builder schema (epsEstimateAverage, epsRevisionXdAgo,
    # epsRevisionDeltaXd, revenueEstimateAverage, ...). 60d column added; deltas
    # surfaced as primary signal; both EPS and Rev analyst counts shown.
    if forward:
        parts.append("\n### Forward Estimates (revision momentum)")
        parts.append("| Period | EPS Cur | 7d | 30d | 60d | 90d | Δ30d | Δ90d | Revenue Est | EPS Analysts | Rev Analysts |")
        parts.append("|--------|---------|------|------|------|------|------|------|-------------|--------------|--------------|")
        for f_row in forward:
            fde = f_row.get("fiscalDateEnding") or "?"
            horizon = (f_row.get("horizon") or "").lower()
            tag = "FY" if "year" in horizon else ("Q" if "quarter" in horizon else "")
            period = f"{fde} ({tag})" if tag else fde
            eps_cur = _fmt_eps(f_row.get("epsEstimateAverage"))
            eps_7d  = _fmt_eps(f_row.get("epsRevision7dAgo"))
            eps_30d = _fmt_eps(f_row.get("epsRevision30dAgo"))
            eps_60d = _fmt_eps(f_row.get("epsRevision60dAgo"))
            eps_90d = _fmt_eps(f_row.get("epsRevision90dAgo"))
            d30 = _fmt_eps_delta(f_row.get("epsRevisionDelta30d"))
            d90 = _fmt_eps_delta(f_row.get("epsRevisionDelta90d"))
            rev_est = _fmt_money(f_row.get("revenueEstimateAverage"))
            # Analyst counts: explicit None check so 0 is preserved (defensive).
            eps_n_raw = f_row.get("epsAnalystCount")
            eps_n = eps_n_raw if eps_n_raw is not None else "—"
            rev_n_raw = f_row.get("revenueAnalystCount")
            rev_n = rev_n_raw if rev_n_raw is not None else "—"
            parts.append(f"| {period} | {eps_cur} | {eps_7d} | {eps_30d} | {eps_60d} | {eps_90d} | {d30} | {d90} | {rev_est} | {eps_n} | {rev_n} |")

    # ── Gaps ──
    if gaps:
        gap_notes = [g.get("reason") or g.get("type", "unknown") for g in gaps]
        parts.append(f"\nData notes: {'; '.join(gap_notes)}")

    return "\n".join(parts)
