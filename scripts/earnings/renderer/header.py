"""Section 1 — Header.

Extracted from earnings_orchestrator.py (commit 9/20). Pure: no external
dependencies, no I/O.
"""
from __future__ import annotations
from datetime import datetime, timezone


def _calendar_days_between(later_iso: str, earlier_iso: str) -> int | None:
    # Calendar-date delta (NOT timedelta.days) so DST/time-of-day
    # under-shoot does not turn 98 into 97.
    try:
        later = datetime.fromisoformat(later_iso)
        earlier = datetime.fromisoformat(earlier_iso)
        return (later.date() - earlier.date()).days
    except (TypeError, ValueError):
        return None


def _format_assembled_at(ts) -> str | None:
    """Normalize a UTC-aware ISO timestamp to seconds + 'Z'. None on missing/malformed.

    U61: surfaces bundle.assembled_at in §1.0 as a freshness signal (live mode)
    and provenance anchor (learner). Defensive against:
    - missing / None / non-string / empty (returns None → segment omitted)
    - unparseable strings (returns None)
    - naive datetimes (REJECTED — returns None. Naive input would force us
      to invent timezone provenance; orchestrator always emits tz-aware UTC,
      so naive = malformed by contract.)
    - 'Z' suffix variants (handled via .replace("Z", "+00:00") shim so the
      same helper works whether upstream emits +00:00 or Z form)
    - non-UTC offsets (converted to UTC before formatting)
    """
    if not isinstance(ts, str) or not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


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

    # U61: append optional Assembled segment to the Mode line. Uniform
    # mode_parts construction collapses the prior if/else and lets the
    # defensive helper decide whether to surface the bundle's assembled_at.
    mode_parts = [f"Mode: {mode}"]
    if pit:
        mode_parts.append(f"PIT cutoff: {pit}")
    asm = _format_assembled_at(bundle.get("assembled_at"))
    if asm:
        mode_parts.append(f"Assembled: {asm}")
    lines.append(" | ".join(mode_parts))
    return "\n".join(lines)
