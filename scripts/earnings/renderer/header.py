"""Section 1 — Header.

Extracted from earnings_orchestrator.py (commit 9/20) — body copied verbatim
from the pre-renderer-extract baseline at lines 264-283. Pure: no external
dependencies, no I/O.
"""
from __future__ import annotations


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
