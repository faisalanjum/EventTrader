"""Section 1 — Header.

Extracted from earnings_orchestrator.py (commit 9/20). Pure: no external
dependencies, no I/O.
"""
from __future__ import annotations
from datetime import datetime


def _calendar_days_between(later_iso: str, earlier_iso: str) -> int | None:
    # Calendar-date delta (NOT timedelta.days) so DST/time-of-day
    # under-shoot does not turn 98 into 97.
    try:
        later = datetime.fromisoformat(later_iso)
        earlier = datetime.fromisoformat(earlier_iso)
        return (later.date() - earlier.date()).days
    except (TypeError, ValueError):
        return None


def _render_header(bundle: dict) -> str:
    """Section 1: Header — ticker, quarter, filing context, mode."""
    qi = bundle.get("quarter_info", {})
    ticker = str(bundle.get("ticker") or "UNKNOWN").upper()
    quarter = str(qi.get("quarter_label") or "UNKNOWN")
    filed = str(qi.get("filed_8k") or "UNKNOWN")
    session = str(qi.get("market_session") or "UNKNOWN")
    period = str(qi.get("period_of_report") or "UNKNOWN")
    accession = qi.get("accession_8k")
    prev_8k = qi.get("prev_8k_ts")
    pit = bundle.get("pit_cutoff")
    mode = "historical" if pit else "live"

    lines = [
        f"# {ticker} {quarter}",
        f"Filed: {filed} | Session: {session} | Period ending: {period}",
    ]

    provenance: list[str] = []
    if accession:
        provenance.append(f"Accession: {accession}")
    if prev_8k:
        days = _calendar_days_between(filed, prev_8k) if filed != "UNKNOWN" else None
        if days is not None:
            provenance.append(f"Prior 8-K: {prev_8k} ({days} days ago)")
        else:
            provenance.append(f"Prior 8-K: {prev_8k}")
    if provenance:
        lines.append(" | ".join(provenance))

    if pit:
        lines.append(f"Mode: {mode} | PIT cutoff: {pit}")
    else:
        lines.append(f"Mode: {mode}")
    return "\n".join(lines)
