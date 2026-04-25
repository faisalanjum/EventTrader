"""Section 5 — Prior Financial Trends + revenue splits + financial-cell formatters.

Extracted from earnings_orchestrator.py (commit 11/20) — bodies copied verbatim
from the pre-renderer-extract baseline at lines 730, 769, 790, 796, 823 (per
Appendix A.5).
"""
from __future__ import annotations

import math
from typing import Any

from ._formatters import _md_table, _fmt_num, _fmt_money


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


def _fmt_split_pct(value) -> str:
    if value is None:
        return "—"
    return f"{float(value):.1f}%"


def _render_revenue_splits(pf: dict) -> list[str]:
    rs = pf.get("revenue_splits")
    if not rs or not isinstance(rs, dict):
        return []

    quarter_headers = [q.get("fiscal_label", q.get("period", "?")) for q in rs.get("quarters", [])]
    if not quarter_headers:
        return []

    parts: list[str] = []
    for key, heading in (
        ("business_segment", "Revenue Mix — Business Segments"),
        ("geography", "Revenue Mix — Geography"),
        ("product_service", "Revenue Mix — Product / Service"),
    ):
        rows = rs.get(key) or []
        if not rows:
            continue
        tbl_rows = []
        for row in rows:
            tbl_rows.append([row.get("label") or row.get("member") or "—"] +
                            [_fmt_split_pct(v) for v in row.get("pct", [])])
        parts.append(f"\n### {heading}")
        parts.append(_md_table(["Row"] + quarter_headers, tbl_rows))
    return parts


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

    parts.extend(_render_revenue_splits(pf))

    if gaps:
        parts.append(f"\nData notes: {len(gaps)} gaps in packet")

    return "\n".join(parts)
