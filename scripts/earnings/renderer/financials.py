"""Section 5 — Prior Financial Trends + revenue splits + financial-cell formatters.

Extracted from earnings_orchestrator.py (commit 11/20) — bodies copied verbatim
from the pre-renderer-extract baseline at lines 730, 769, 790, 796, 823 (per
Appendix A.5).
"""
from __future__ import annotations

from ._formatters import (
    _md_table, _fmt_num, _fmt_money,
    # PERMANENT back-compat re-export — _fmt_financial_cell was relocated
    # to _formatters.py (stage 2 of the _fmt_financial_cell move). This
    # preserves `from scripts.earnings.renderer.financials import
    # _fmt_financial_cell` for any unaudited caller. Do not remove.
    _fmt_financial_cell,  # noqa: F401
)


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


def _render_derivation_notes(quarters: list) -> list[str]:
    """U12: per-quarter "Derivation notes" block surfacing derived_metrics
    method + input accessions so the predictor can distinguish exact-extract
    from arithmetic-derived numbers.

    Source of truth: `quarters[].derived_metrics` (NOT `_provenance` —
    `_provenance` carries entries for direct extracts too, which would
    produce noisy non-derivation notes).

    Quarters with no derivations are omitted; if no quarter has derivations,
    the entire section is omitted.
    """
    blocks = []
    for q in quarters:
        derived = q.get("derived_metrics") or []
        if not derived:
            continue
        block_lines = [f"\n**{q.get('fiscal_label', '?')}**:"]
        for d in derived:
            metric = d.get("metric", "?")
            method = d.get("method", "?")
            inputs = d.get("inputs") or []
            input_strs = []
            for inp in inputs:
                role = inp.get("role", "?")
                acc = inp.get("accession") or "?"
                form = inp.get("form") or "?"
                input_strs.append(f"{role} from {acc} ({form})")
            inputs_part = ", ".join(input_strs) if input_strs else "(no inputs)"
            block_lines.append(f"- {metric}: derived via {method}, inputs: {inputs_part}")
        blocks.append("\n".join(block_lines))
    if not blocks:
        return []
    return ["\n### Derivation notes"] + blocks


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
    parts.extend(_render_derivation_notes(quarters))

    if gaps:
        parts.append(f"\nData notes: {len(gaps)} gaps in packet")

    return "\n".join(parts)
