"""Section 6 — Inter-Quarter Events.

12 functions extracted from earnings_orchestrator.py (commit 14/20):
  _iq_cell, _iq_val, _iq_bool, _iq_join (cell-level helpers)
  _iq_header, _iq_days_table (block helpers)
  _iq_adj_returns (extracts adjusted-return triples)
  _iq_news_table, _iq_filings_table, _iq_dividends_table, _iq_splits_table
  _render_inter_quarter (top-level orchestrator)

All bodies copied verbatim from the pre-renderer-extract baseline at lines
996, 1001, 1008, 1017, 1025, 1058, 1092, 1107, 1139, 1178, 1207, 1235.

Pure: no external dependencies (the helpers are leaves; peers/macro re-use
some of them).

NOTE: _IQ_ANALYST_CHANNELS (a dead constant from the original baseline at
line 990) intentionally stays in earnings_orchestrator.py — its removal is
deferred to a follow-up PR per the migration plan §2.2.
"""
from __future__ import annotations


def _iq_cell(s: str) -> str:
    """Escape a string for safe use inside a markdown table cell."""
    return s.replace("\n", " ").replace("|", "\\|")


def _iq_val(v) -> str:
    """Render a value for inter-quarter tables. None → '—', else pipe-safe str."""
    if v is None:
        return "—"
    return _iq_cell(str(v))


def _iq_bool(v) -> str:
    """Three-state boolean: True→Y, False→N, None→—."""
    if v is True:
        return "Y"
    if v is False:
        return "N"
    return "—"


def _iq_join(arr, sep=" ; ") -> str:
    """Join an array with separator. Empty/None → '—'. Pipe-safe."""
    if not arr:
        return "—"
    items = [_iq_cell(str(x)) for x in arr if x]
    return sep.join(items) if items else "—"


def _iq_header(packet: dict) -> str:
    """Block 1: Period metadata + summary counts."""
    summary = packet.get("summary", {})
    lines = [
        "## 6. Inter-Quarter Events",
        "",
        f"Ticker: {packet.get('ticker', '—')} | "
        f"Sector: {packet.get('sector', '—')} | "
        f"Industry: {packet.get('industry', '—')}",

        f"Window: {packet.get('prev_8k_ts', '—')} → "
        f"{packet.get('context_cutoff_ts', '—')} "
        f"({packet.get('context_cutoff_reason', '—')})",

        f"Dates: {packet.get('prev_day', '—')} → "
        f"{packet.get('cutoff_day', '—')} | "
        f"PIT: {packet.get('pit_cutoff') or 'N/A'} | "
        f"Mode: {packet.get('source_mode', '—')}",

        f"Schema: {packet.get('schema_version', '—')} | "
        f"Assembled: {packet.get('assembled_at', '—')}",

        f"Summary: {summary.get('trading_days_ordinary', 0)} trading days, "
        f"{summary.get('significant_move_days', 0)} significant, "
        f"{summary.get('gap_days', 0)} gap | "
        f"{summary.get('total_news', 0)} news, "
        f"{summary.get('total_filings', 0)} filings, "
        f"{summary.get('total_dividends', 0)} dividends, "
        f"{summary.get('total_splits', 0)} splits",
    ]
    return "\n".join(lines)


def _iq_days_table(days: list) -> str:
    """Block 2: Trading Days table — one row per day in the packet."""
    if not days:
        return "### Trading Days\n\n[NO TRADING DAYS]"
    headers = [
        "Date", "Trd", "Bnd", "Close", "Ret%", "SPY%", "Sect%",
        "Adj%", "Sig", "Gap",
    ]
    rows = []
    for day in days:
        p = day.get("price") or {}
        bnd = day.get("boundary_role")
        bnd_short = "prev" if bnd == "prev_boundary" else (
            "cutoff" if bnd == "cutoff_boundary" else "—")
        rows.append([
            day.get("date", "—"),
            "Y" if day.get("is_trading_day") else "N",
            bnd_short,
            _iq_val(p.get("close")),
            _iq_val(p.get("daily_return")),
            _iq_val(day.get("spy_return")),
            _iq_val(day.get("sector_return")),
            _iq_val(day.get("adj_return")),
            _iq_bool(day.get("is_significant")),
            _iq_bool(day.get("is_gap_day")),
        ])
    lines = ["### Trading Days", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_adj_returns(ev: dict) -> tuple[str, str, str]:
    """Extract adjusted returns (stock - macro) for hourly, session, daily windows."""
    fr = ev.get("forward_returns")
    if not fr or not isinstance(fr, dict):
        return ("—", "—", "—")
    vals = []
    for win_key in ("hourly", "session", "daily"):
        win = fr.get(win_key)
        if win and win.get("adj_macro") is not None:
            vals.append(_iq_val(win["adj_macro"]))
        else:
            vals.append("—")
    return (vals[0], vals[1], vals[2])


def _iq_news_table(days: list) -> str:
    """Block 3: News Events table — one row per news event, with inline adjusted returns."""
    news = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "news":
                news.append((day["date"], ev))
    if not news:
        return ""

    headers = ["Ref", "Date", "Sess", "Title", "Channels",
               "AdjH%", "AdjS%", "AdjD%"]
    rows = []
    for i, (date, ev) in enumerate(news, 1):
        adj_h, adj_s, adj_d = _iq_adj_returns(ev)
        # U17: surface clean Benzinga id alongside synthetic N{i} when builder supplies bz_id;
        # falls back to bare N{i} for events without bz_id (None/missing). Render-additive only —
        # catalog still emits #S6.news.N{i} aliases (no #S6.news.bz: forms; see U17 plan).
        bz = ev.get("bz_id")
        ref_cell = f"N{i} [bz:{bz}]" if bz else f"N{i}"
        rows.append([
            ref_cell,
            date,
            _iq_val(ev.get("market_session")),
            _iq_cell((ev.get("title") or "").replace("\n", " ").strip()) or "—",
            _iq_join(ev.get("channels")),
            adj_h, adj_s, adj_d,
        ])
    lines = [f"### News Events ({len(news)})", "",
             "Adjusted returns = stock − macro for each window (hourly / session / daily)", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_filings_table(days: list) -> str:
    """Block 4: Filing Events table — one row per filing event, with inline adjusted returns."""
    filings = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "filing":
                filings.append((day["date"], ev))
    if not filings:
        return ""

    headers = [
        "Ref", "Date", "Sess", "Form", "Accession",
        "Items", "Exhibits", "Period", "Amend", "Content",
        "AdjH%", "AdjS%", "AdjD%",
    ]
    rows = []
    for i, (date, ev) in enumerate(filings, 1):
        adj_h, adj_s, adj_d = _iq_adj_returns(ev)
        rows.append([
            f"F{i}",
            date,
            _iq_val(ev.get("market_session")),
            _iq_val(ev.get("form_type")),
            _iq_val(ev.get("accession")),
            _iq_join(ev.get("items"), sep=" || "),
            _iq_join(ev.get("exhibit_keys")),
            _iq_val(ev.get("period_of_report")),
            _iq_bool(ev.get("is_amendment")),
            _iq_val(ev.get("related_content_path")),
            adj_h, adj_s, adj_d,
        ])
    lines = [f"### Filing Events ({len(filings)})", "",
             "Adjusted returns = stock − macro for each window (hourly / session / daily)", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_dividends_table(days: list) -> str:
    """Block 5: Dividends table."""
    divs = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "dividend":
                divs.append(ev)
    if not divs:
        return ""

    headers = ["Ref", "DeclDate", "ExDiv", "Amount", "Freq", "Type"]
    rows = []
    for i, ev in enumerate(divs, 1):
        rows.append([
            f"D{i}",
            _iq_val(ev.get("declaration_date")),
            _iq_val(ev.get("ex_dividend_date")),
            _iq_val(ev.get("cash_amount")),
            _iq_val(ev.get("frequency")),
            _iq_val(ev.get("dividend_type")),
        ])
    lines = [f"### Dividends ({len(divs)})", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _iq_splits_table(days: list) -> str:
    """Block 6: Splits table."""
    splits = []
    for day in days:
        for ev in day["events"]:
            if ev.get("type") == "split":
                splits.append(ev)
    if not splits:
        return ""

    headers = ["Ref", "ExecDate", "Ratio"]
    rows = []
    for i, ev in enumerate(splits, 1):
        rows.append([
            f"S{i}",
            _iq_val(ev.get("execution_date")),
            _iq_val(ev.get("ratio_text")),
        ])
    lines = [f"### Splits ({len(splits)})", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)




def _render_inter_quarter(bundle: dict) -> str:
    """Section 6: Inter-Quarter Events — full tabular rendering."""
    name = "inter_quarter_context"
    errors = bundle.get("builder_errors") or {}
    if name in errors:
        return f"## 6. Inter-Quarter Events\n\n[BUILDER ERROR: {errors[name]}]"

    packet = bundle.get(name)
    if not packet or not isinstance(packet, dict):
        return "## 6. Inter-Quarter Events\n\n[NO DATA]"

    days = packet.get("days", [])

    blocks = [_iq_header(packet)]
    blocks.append(_iq_days_table(days))

    # Event tables — only included if non-empty
    for table_fn in [
        _iq_news_table,
        _iq_filings_table,
        _iq_dividends_table,
        _iq_splits_table,
    ]:
        block = table_fn(days)
        if block:
            blocks.append(block)

    # U7: surface allowlisted related-filing sidecars for the predictor.
    allowed = packet.get("_allowed_related_filing_paths") or []
    if allowed:
        rf_block = ["### Allowed related filing files for this prediction", ""]
        for p in allowed:
            rf_block.append(f"- {p}")
        blocks.append("\n".join(rf_block))

    return "\n\n".join(blocks)
