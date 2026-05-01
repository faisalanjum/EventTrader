"""Section 7 — Sector Peer Earnings & Reactions (Option D per-peer block).

U22 rewrite: replaces the wide-table format with per-peer blocks. Each peer
gets a 3×3 reaction matrix (Day/Sess/Hour × Stock-raw/Sector-adj/Macro-adj)
plus optional decorations (FY-mismatch tag, Periodic line, amendment marker)
and a headlines list with [bz:...] tags.

Math semantics (verified 2026-05-01 via Cypher probe of pf.* on PRIMARY_FILER):
- Bundle stores RAW returns: pf.daily_macro = SPY's same-window return,
  pf.daily_sector = sector index's same-window return, etc.
- There is NO `*_adj` property on the relationship.
- Renderer computes Sector-adj / Macro-adj cells as `stock − benchmark` per
  horizon at render time. Best cells come pre-computed from the bundle
  (builder takes math-max across the 3 ADJ horizons per U23).
"""
from __future__ import annotations

from .inter_quarter import _iq_cell

_MONTH_ABBR = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
               7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}


def _signed_pct(v) -> str:
    """Defensive: None / non-numeric / NaN → '—'; otherwise signed-2dp percent.

    A stray string in the bundle JSON would otherwise crash render. Bundle
    fields SHOULD be float|None per builder contract, but renderers should
    never trust upstream — old fixtures, partial backfills, and adapter bugs
    can all leak strings or other types.
    """
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f != f:  # NaN
        return "—"
    return f"{f:+.2f}%"


def _sub(stk, idx):
    """Defensive subtraction: None on either side OR non-numeric → None.

    Module-level (not nested in the per-peer loop) so it's testable in
    isolation and not redefined per iteration.
    """
    if stk is None or idx is None:
        return None
    try:
        return float(stk) - float(idx)
    except (TypeError, ValueError):
        return None


def _month_abbr(m):
    """Integer fye_month → 'Jan'/'Feb'/...; None / unparseable → None."""
    if m is None:
        return None
    try:
        return _MONTH_ABBR.get(int(m))
    except (ValueError, TypeError):
        return None


def _render_peer_earnings(bundle: dict) -> str:
    """Section 7: Sector Peer Earnings & Reactions — per-peer Option D format."""
    name = "peer_earnings_snapshot"
    errors = bundle.get("builder_errors") or {}
    if name in errors:
        return f"## 7. Sector Peer Earnings & Reactions\n\n[BUILDER ERROR: {errors[name]}]"

    packet = bundle.get(name)
    if not packet or not isinstance(packet, dict):
        return "## 7. Sector Peer Earnings & Reactions\n\n[NO DATA]"

    peers = packet.get("peers", [])
    industry = packet.get("industry") or "—"
    window_start = packet.get("window_start") or "—"
    cutoff = (packet.get("effective_cutoff_ts") or "—")[:10]
    summary = packet.get("summary", {})

    parts = [
        "## 7. Sector Peer Earnings & Reactions",
        "",
        f"Industry: {industry} | "
        f"Window: {window_start} → {cutoff} | "
        f"Peers: {summary.get('total_peers', 0)}",
    ]

    # Data notes line — only when fail-CLOSED gaps exist
    gaps = summary.get("gaps") or []
    if gaps:
        excluded = ", ".join(g.get("peer_ticker", "?") for g in gaps)
        parts.append(
            f"Data notes: {len(gaps)} peer(s) with missing returns_schedule: {excluded}"
        )

    if not peers:
        parts.append("")
        parts.append("[NO PEER EARNINGS IN WINDOW]")
        return "\n".join(parts)

    target_fye = (bundle.get("quarter_info") or {}).get("fye_month")

    for p in peers:
        ticker = p.get("ticker") or "—"
        filed_short = (p.get("filed") or "—")[:10]
        session = p.get("market_session") or "—"
        accession = p.get("accession") or "—"

        # FY-mismatch tag — only when peer's fye differs from target's
        peer_fye = p.get("fy_end_month")
        fy_tag = ""
        try:
            if peer_fye is not None and target_fye is not None and int(peer_fye) != int(target_fye):
                ab = _month_abbr(peer_fye)
                if ab:
                    fy_tag = f" (FY ends {ab})"
        except (ValueError, TypeError):
            pass

        parts.append("")
        parts.append(
            f"### {ticker} — filed {filed_short} ({session}), "
            f"accession {accession}{fy_tag}"
        )

        # Periodic line — only when accession_periodic is non-null (PIT-visible)
        ap = p.get("accession_periodic")
        ftp = p.get("form_type_periodic")
        if ap:
            tag = f" ({ftp})" if ftp else ""
            parts.append(f"Periodic: {ap}{tag}")

        # Amendment marker — only when peer's 8-K is amended (8-K/A, not 10-K/A)
        if p.get("is_amendment"):
            parts.append("[8-K/A amendment]")

        # 3×3 matrix
        d_stk = p.get("daily_stock_pct")
        s_stk = p.get("session_stock_pct")
        h_stk = p.get("hourly_stock_pct")
        d_sec = p.get("daily_sector_pct")
        s_sec = p.get("session_sector_pct")
        h_sec = p.get("hourly_sector_pct")
        d_mac = p.get("daily_macro_pct")
        s_mac = p.get("session_macro_pct")
        h_mac = p.get("hourly_macro_pct")
        b_sec = p.get("best_sector_pct")
        b_mac = p.get("best_macro_pct")

        parts.append("")
        parts.append(
            f"Stock move:    Day {_signed_pct(d_stk)}   "
            f"Sess {_signed_pct(s_stk)}   "
            f"Hour {_signed_pct(h_stk)}"
        )
        parts.append(
            f"Sector-adj:    Day {_signed_pct(_sub(d_stk, d_sec))}   "
            f"Sess {_signed_pct(_sub(s_stk, s_sec))}   "
            f"Hour {_signed_pct(_sub(h_stk, h_sec))}   "
            f"Best {_signed_pct(b_sec)}"
        )
        parts.append(
            f"Macro-adj:     Day {_signed_pct(_sub(d_stk, d_mac))}   "
            f"Sess {_signed_pct(_sub(s_stk, s_mac))}   "
            f"Hour {_signed_pct(_sub(h_stk, h_mac))}   "
            f"Best {_signed_pct(b_mac)}"
        )

        # Headlines — only when at least one valid title
        valid_hl = [h for h in (p.get("headlines") or []) if h.get("title")]
        if valid_hl:
            parts.append("Headlines:")
            for h in valid_hl:
                bz = h.get("bz_id")
                date_short = (h.get("date") or "")[:10]
                title = _iq_cell((h.get("title") or "—").replace("\n", " ").strip())
                tag = f"[bz:{bz}] " if bz else ""
                line = f"- {tag}{date_short} {title}".rstrip()
                parts.append(line)

    return "\n".join(parts)
