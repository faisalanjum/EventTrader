"""Section 8 — Macro Environment.

Extracted from earnings_orchestrator.py (commit 16/20) — body copied verbatim
from the pre-renderer-extract baseline at line 1361. Re-uses _iq_val, _iq_cell,
_iq_join from the sibling inter_quarter module.
"""
from __future__ import annotations

from .inter_quarter import _iq_val, _iq_cell, _iq_join


def _render_macro(bundle: dict) -> str:
    """Section 8: Macro Environment — SPY, VIX, cross-asset indicators, catalysts."""
    name = "macro_snapshot"
    errors = bundle.get("builder_errors") or {}
    if name in errors:
        return f"## 8. Macro Environment\n\n[BUILDER ERROR: {errors[name]}]"

    packet = bundle.get(name)
    if not packet or not isinstance(packet, dict):
        return "## 8. Macro Environment\n\n[NO DATA]"

    market = packet.get("market_now") or {}
    spy = market.get("spy") or {}
    sector = market.get("sector") or {}
    indicators = market.get("indicators") or {}
    catalysts = packet.get("catalysts") or {}

    parts = [
        "## 8. Macro Environment",
        "",
        f"Session: {packet.get('market_session', '—')} | "
        f"Source: {packet.get('source', '—')} | "
        f"PIT: {packet.get('pit_date', '—')}",
        f"SPY {_iq_val(spy.get('level_at_pit'))} | "
        f"VIX {_iq_val(market.get('vix_close'))} ({market.get('vix_label', '—')})",
        # U35: SPY-specific provenance — last_settled_date is sourced from
        # _compute_spy_now and reflects SPY's bar coverage only.
        f"Bars: SPY minute≤PIT−60s, SPY daily settled through {spy.get('last_settled_date') or '—'}",
    ]

    # ── SPY Trend ──
    spy_headers = [
        "Level", "Open→PIT", "Last60m", "Gap", "Today",
        "Yest", "5D", "20D", "YTD",
        "MA50", "MA200", "Vs50D", "Vs200D", "VolRatio",
    ]
    spy_row = [
        _iq_val(spy.get("level_at_pit")),
        _iq_val(spy.get("open_to_pit")),
        _iq_val(spy.get("last_60m")),
        _iq_val(spy.get("overnight_gap")),
        _iq_val(spy.get("today_return")),
        _iq_val(spy.get("yesterday")),
        _iq_val(spy.get("change_5d")),
        _iq_val(spy.get("change_20d")),
        _iq_val(spy.get("change_ytd")),
        _iq_val(spy.get("ma_50")),
        _iq_val(spy.get("ma_200")),
        _iq_val(spy.get("vs_50d")),
        _iq_val(spy.get("vs_200d")),
        _iq_val(spy.get("volume_ratio")),
    ]
    parts.append("")
    parts.append("### SPY Trend")
    parts.append("")
    parts.append("| " + " | ".join(spy_headers) + " |")
    parts.append("|" + "|".join("---" for _ in spy_headers) + "|")
    parts.append("| " + " | ".join(spy_row) + " |")

    # ── Sector Context ──
    if sector:
        sec_headers = ["Sector", "ETF", "LastRet", "Label", "Open→PIT", "5D", "VsSPY5D"]
        sec_row = [
            _iq_val(sector.get("name")),
            _iq_val(sector.get("etf")),
            _iq_val(sector.get("last_return")),
            _iq_val(sector.get("return_label")),
            _iq_val(sector.get("open_to_pit")),
            _iq_val(sector.get("change_5d")),
            _iq_val(sector.get("vs_spy_5d")),
        ]
        parts.append("")
        parts.append("### Sector Context")
        parts.append("")
        parts.append("| " + " | ".join(sec_headers) + " |")
        parts.append("|" + "|".join("---" for _ in sec_headers) + "|")
        parts.append("| " + " | ".join(sec_row) + " |")

    # ── Cross-Asset Indicators ──
    if indicators:
        ind_headers = ["Indicator", "Level", "LastRet", "Label", "5D", "YTD"]
        ind_rows = []
        for ind_name, ind_data in indicators.items():
            if not isinstance(ind_data, dict):
                continue
            ind_rows.append([
                _iq_cell(ind_name),
                _iq_val(ind_data.get("level")),
                _iq_val(ind_data.get("last_return")),
                _iq_val(ind_data.get("return_label")),
                _iq_val(ind_data.get("change_5d")),
                _iq_val(ind_data.get("change_ytd")),
            ])
        if ind_rows:
            parts.append("")
            parts.append("### Cross-Asset Indicators")
            parts.append("")
            parts.append("| " + " | ".join(ind_headers) + " |")
            parts.append("|" + "|".join("---" for _ in ind_headers) + "|")
            for row in ind_rows:
                parts.append("| " + " | ".join(row) + " |")

    # ── Macro Catalysts ──
    cat_rows = []
    for bucket_name, bucket_key in [("Today", "today"), ("Yesterday", "yesterday")]:
        bucket = catalysts.get(bucket_key)
        if not bucket or not isinstance(bucket, dict):
            continue
        date = bucket.get("date", "—")
        for h in bucket.get("headlines", []):
            cat_rows.append([
                bucket_name,
                date,
                _iq_val(h.get("time")),
                _iq_cell((h.get("title") or "—").replace("\n", " ").strip()),
                _iq_join(h.get("channels")),
            ])
    # Earlier is a list of [date, headline] pairs
    earlier = catalysts.get("earlier", [])
    if isinstance(earlier, list):
        for item in earlier:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                date, h = item[0], item[1]
                if isinstance(h, dict):
                    cat_rows.append([
                        "Earlier",
                        str(date),
                        _iq_val(h.get("time")),
                        _iq_cell((h.get("title") or "—").replace("\n", " ").strip()),
                        _iq_join(h.get("channels")),
                    ])

    if cat_rows:
        cat_headers = ["Bucket", "Date", "Time", "Title", "Channels"]
        parts.append("")
        parts.append("### Macro Catalysts")
        parts.append("")
        parts.append("| " + " | ".join(cat_headers) + " |")
        parts.append("|" + "|".join("---" for _ in cat_headers) + "|")
        for row in cat_rows:
            parts.append("| " + " | ".join(row) + " |")

    return "\n".join(parts)
