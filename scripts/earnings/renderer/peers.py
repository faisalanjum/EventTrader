"""Section 7 — Sector Peer Earnings & Reactions.

Extracted from earnings_orchestrator.py (commit 15/20) — body copied verbatim
from the pre-renderer-extract baseline at line 1268. Re-uses _iq_val, _iq_cell,
_iq_join from the sibling inter_quarter module.
"""
from __future__ import annotations

from .inter_quarter import _iq_val, _iq_cell, _iq_join


def _render_peer_earnings(bundle: dict) -> str:
    """Section 7: Sector Peer Earnings & Reactions — compact table."""
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

    if not peers:
        parts.append("\n[NO PEER EARNINGS IN WINDOW]")
        return "\n".join(parts)

    # Peer table: one row per peer with key reaction metrics
    # Adjusted returns = stock − macro. Session macro not in packet, so SessStk% is raw.
    headers = [
        "Ticker", "Name", "MktCap", "Filed", "Accession", "Period",
        "Sess", "DayStk%", "AdjH%", "SessStk%", "AdjD%", "Horizon",
    ]
    rows = []
    for p in peers:
        h_stk = p.get("hourly_stock_pct")
        h_mac = p.get("hourly_macro_pct")
        d_stk = p.get("daily_stock_pct")
        d_mac = p.get("daily_macro_pct")
        adj_h = _iq_val(round(h_stk - h_mac, 2)) if h_stk is not None and h_mac is not None else "—"
        adj_d = _iq_val(round(d_stk - d_mac, 2)) if d_stk is not None and d_mac is not None else "—"
        rows.append([
            _iq_val(p.get("ticker")),
            _iq_cell((p.get("name") or "—").replace("\n", " ").strip()),
            _iq_val(p.get("mkt_cap")),
            _iq_val((p.get("filed") or "—")[:10]),
            _iq_val(p.get("accession")),
            _iq_val(p.get("period_of_report")),
            _iq_val(p.get("market_session")),
            _iq_val(d_stk),
            adj_h,
            _iq_val(p.get("session_stock_pct")),
            adj_d,
            _iq_val(p.get("context_horizon")),
        ])

    parts.append("")
    parts.append("| " + " | ".join(headers) + " |")
    parts.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        parts.append("| " + " | ".join(row) + " |")

    # Headlines sub-section: one line per headline, grouped by peer
    has_headlines = any(p.get("headlines") for p in peers)
    if has_headlines:
        parts.append("")
        parts.append("### Peer Headlines")
        hl_headers = ["Peer", "Time", "Title", "Channels"]
        hl_rows = []
        for p in peers:
            ticker = p.get("ticker", "—")
            for h in (p.get("headlines") or []):
                hl_rows.append([
                    ticker,
                    _iq_val(h.get("date")),
                    _iq_cell((h.get("title") or "—").replace("\n", " ").strip()),
                    _iq_join(h.get("channels")),
                ])
        if hl_rows:
            parts.append("")
            parts.append("| " + " | ".join(hl_headers) + " |")
            parts.append("|" + "|".join("---" for _ in hl_headers) + "|")
            for row in hl_rows:
                parts.append("| " + " | ".join(row) + " |")

    return "\n".join(parts)
