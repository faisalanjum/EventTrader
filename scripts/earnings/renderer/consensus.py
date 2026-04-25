"""Section 4 — Consensus History (beat/miss + revision momentum).

Extracted from earnings_orchestrator.py (commit 12/20) — body copied verbatim
from the pre-renderer-extract baseline at line 656.

Imports `_fmt_financial_cell` from the sibling `financials` module
(used at line 697 for EPS estimate/actual cells); `_md_table`, `_fmt_money`,
`_fmt_pct` from `_formatters`.
"""
from __future__ import annotations

from ._formatters import _md_table, _fmt_money, _fmt_pct
from .financials import _fmt_financial_cell


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
