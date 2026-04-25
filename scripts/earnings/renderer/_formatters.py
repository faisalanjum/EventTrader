"""Generic formatters shared by every renderer section.

Extracted from earnings_orchestrator.py (commit 8/20) — bodies copied verbatim
from the pre-renderer-extract baseline at lines 286-335.
"""
from __future__ import annotations

import math


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
