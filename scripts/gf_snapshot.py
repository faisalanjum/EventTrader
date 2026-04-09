#!/usr/bin/env python3
"""
US Market Snapshot — comprehensive macro state in one shot.

Combines Google Finance (movers, earnings, news + article text)
with Yahoo Finance (sectors, rates, commodities, FX, crypto, global).

Usage:
  python3 scripts/market_snapshot.py               # full snapshot
  python3 scripts/market_snapshot.py --json         # JSON for bots
  python3 scripts/market_snapshot.py --lite         # Google Finance only (fast)
  python3 scripts/market_snapshot.py --no-articles  # skip article text
  python3 scripts/market_snapshot.py --articles 5   # fewer articles
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

# Import Google Finance parsing from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gf_scraper import (
    fetch_url, extract_callbacks, identify_callbacks,
    parse_indices, parse_movers, parse_most_followed,
    parse_earnings_calendar, parse_news, extract_article_text,
    GOOGLE_FINANCE_URL, HAS_TRAFILATURA,
    fmt_change, fmt_price,
)

# ---------------------------------------------------------------------------
# Yahoo Finance — batch macro data
# ---------------------------------------------------------------------------

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

ET = timezone(timedelta(hours=-4))

STOCK_QUOTE_URL = "https://www.google.com/finance/quote/{ticker}:{exchange}?hl=en&gl=us"
EXCHANGES_TO_TRY = ["NASDAQ", "NYSE", "NYSEARCA"]

SESSION_NAMES = {1: "Regular", 2: "Pre-market", 3: "After-hours"}

# Ticker groups with short labels
SECTOR_TICKERS = {
    "XLK": "Tech", "XLF": "Financials", "XLE": "Energy", "XLV": "Healthcare",
    "XLU": "Utilities", "XLC": "Comm Svcs", "XLI": "Industrials",
    "XLY": "Cons Disc", "XLP": "Cons Staples", "XLB": "Materials", "XLRE": "Real Estate",
}
RATE_TICKERS = {"^FVX": "5Y", "^TNX": "10Y", "^TYX": "30Y"}
BOND_TICKERS = {"TLT": "TLT", "HYG": "HYG", "LQD": "LQD"}
COMMODITY_TICKERS = {"GC=F": "Gold", "CL=F": "Oil", "NG=F": "NatGas", "HG=F": "Copper"}
FX_TICKERS = {"DX-Y.NYB": "DXY", "EURUSD=X": "EUR", "USDJPY=X": "JPY", "GBPUSD=X": "GBP"}
CRYPTO_TICKERS = {"BTC-USD": "BTC", "ETH-USD": "ETH"}
GLOBAL_TICKERS = {"^N225": "Nikkei", "^GDAXI": "DAX", "^FTSE": "FTSE"}

ALL_YAHOO = {
    **SECTOR_TICKERS, **RATE_TICKERS, **BOND_TICKERS,
    **COMMODITY_TICKERS, **FX_TICKERS, **CRYPTO_TICKERS, **GLOBAL_TICKERS,
}


def fetch_yahoo_quotes() -> dict[str, dict]:
    """Batch-fetch all Yahoo tickers. Returns {ticker: {price, prev, change, pct}}."""
    if not HAS_YFINANCE:
        return {}

    results = {}
    syms = list(ALL_YAHOO.keys())

    def _get_one(sym):
        try:
            t = yf.Ticker(sym)
            fi = t.fast_info
            price = fi.last_price
            prev = fi.previous_close
            if price is None or prev is None or prev == 0:
                return sym, None
            change = price - prev
            pct = (change / prev) * 100
            return sym, {"price": price, "prev": prev, "change": change, "pct": pct}
        except Exception:
            return sym, None

    with ThreadPoolExecutor(max_workers=12) as pool:
        for sym, data in pool.map(lambda s: _get_one(s), syms):
            if data:
                results[sym] = data

    return results


# ---------------------------------------------------------------------------
# Ticker deep-dive (individual stock page)
# ---------------------------------------------------------------------------

def resolve_exchange(ticker: str) -> tuple[str, str] | None:
    """Try common exchanges to find the correct one for a ticker.
    Returns (html, exchange) or None."""
    ticker = ticker.upper()
    if ":" in ticker:
        sym, exch = ticker.split(":", 1)
        html = fetch_url(STOCK_QUOTE_URL.format(ticker=sym, exchange=exch))
        return html, exch
    for exch in EXCHANGES_TO_TRY:
        try:
            html = fetch_url(STOCK_QUOTE_URL.format(ticker=ticker, exchange=exch), retries=1, timeout=10)
            # Correct exchange → title has full company name + "Stock Price & News"
            # Wrong exchange → title is just "TICKER - Google Finance"
            m = re.search(r'<title>([^<]+)</title>', html)
            if m and "Stock Price" in m.group(1):
                return html, exch
        except Exception:
            continue
    return None


def parse_ticker_page(html: str) -> dict:
    """Parse a Google Finance stock page into structured data."""
    result = {
        "title": None, "sessions": [], "financials": [],
        "key_events": [], "news": [], "profile": None,
    }

    # Title / company name
    m = re.search(r'<title>([^<]+)</title>', html)
    if m:
        result["title"] = re.sub(r'\s*-\s*Google Finance$', '', m.group(1).replace("&amp;", "&"))

    callbacks = extract_callbacks(html)

    # Extract ticker symbol from the title for filtering
    ticker_sym = None
    if result["title"]:
        m2 = re.search(r'\(([A-Z.]+)\)', result["title"])
        if m2:
            ticker_sym = m2.group(1)

    for key, data in callbacks.items():
        flat = json.dumps(data, ensure_ascii=False)

        # --- Intraday sessions (minute bars) ---
        # ds:10: starts with [[[["TICKER","EXCHANGE"], freebase_id, "USD", [sessions...]]
        # Has minute-level timestamps and UTC offset [-14400] etc
        if (len(flat) > 5000
                and re.search(r'\[\[\["[A-Z.]+"', flat[:50])
                and re.search(r'\[-\d{4,5}\]', flat[:500])):
            try:
                _parse_sessions(data, result)
            except Exception:
                pass

        # --- Quarterly financials ---
        # Revenue can be 9+ digits (>$100M) for small caps, or 12+ for mega caps
        if len(flat) > 20000 and re.search(r'\[\d{4},\s*[1-4],\s*\[-?\d{8,}', flat[:500]):
            try:
                _parse_financials(flat, result)
            except Exception:
                pass

        # --- Key events / news ---
        # Only from small callbacks (<10KB) that contain article URLs
        # Must mention the ticker or be from the stock-specific news callbacks (ds:3, ds:4)
        if ('"https://' in flat and len(flat) < 10000):
            # Filter: must mention this ticker OR be a clearly stock-specific section
            is_ticker_specific = (ticker_sym and f'"{ticker_sym}"' in flat)
            has_key_event_structure = bool(re.search(r'\[\d+,\s*\[\["https://', flat[:100]))
            if is_ticker_specific or has_key_event_structure:
                _parse_stock_news(flat, result)

        # --- Company profile ---
        if "Headquartered in" in flat or "headquartered in" in flat:
            m2 = re.search(r'"((?:Headquartered|headquartered) in [^"]+)"', flat)
            if m2:
                result["profile"] = m2.group(1)

    return result


def _parse_sessions(data, result: dict):
    """Extract price sessions (pre-market, regular, after-hours) from ds:10-like data."""
    # Navigate: data[0][0][3] = list of sessions
    root = data
    if isinstance(root, list) and root:
        if isinstance(root[0], list) and root[0]:
            if isinstance(root[0][0], list) and len(root[0][0]) > 3:
                sessions_raw = root[0][0][3]
                if not isinstance(sessions_raw, list):
                    return
                for sess in sessions_raw:
                    if not isinstance(sess, list) or len(sess) < 2:
                        continue
                    header = sess[0]
                    bars_raw = sess[1]
                    if not isinstance(header, list) or not isinstance(bars_raw, list):
                        continue

                    session_type = header[0] if header else None
                    session_name = SESSION_NAMES.get(session_type, f"Type-{session_type}")

                    # Parse start/end times
                    start_t = header[1] if len(header) > 1 else None
                    end_t = header[2] if len(header) > 2 else None

                    bars = []
                    for bar in bars_raw:
                        if not isinstance(bar, list) or len(bar) < 2:
                            continue
                        ts = bar[0]  # [year, month, day, hour, min, ...]
                        price_arr = bar[1]  # [price, change, pct_change, ...]
                        vol = bar[2] if len(bar) > 2 else None

                        if not isinstance(ts, list) or len(ts) < 4:
                            continue
                        hour = ts[3]
                        minute = ts[4] if len(ts) > 4 and ts[4] is not None else 0
                        price = price_arr[0] if isinstance(price_arr, list) and price_arr else None
                        change = price_arr[1] if isinstance(price_arr, list) and len(price_arr) > 1 else None
                        pct = price_arr[2] if isinstance(price_arr, list) and len(price_arr) > 2 else None

                        bars.append({
                            "time": f"{hour:02d}:{minute:02d}",
                            "price": price,
                            "change": change,
                            "pct": pct,
                            "volume": vol,
                        })

                    if bars:
                        # Skip daily-level sessions (few bars, all at same time like 16:00)
                        unique_times = set(b["time"] for b in bars)
                        if len(unique_times) < 3 and len(bars) > 5:
                            continue  # daily bars, not intraday

                        result["sessions"].append({
                            "name": session_name,
                            "type": session_type,
                            "bars": bars,
                            "open": bars[0]["price"],
                            "close": bars[-1]["price"],
                            "high": max(b["price"] for b in bars if b["price"]),
                            "low": min(b["price"] for b in bars if b["price"]),
                            "start": bars[0]["time"],
                            "end": bars[-1]["time"],
                            "count": len(bars),
                        })


def _parse_financials(flat: str, result: dict):
    """Extract quarterly financials from ds:13-like data."""
    # Pattern: [year, quarter, [revenue, net_income, eps, pe, op_income, interest, null, gross_profit, ...]]
    # Revenue can be 7+ digits for micro-caps ($10M+)
    quarters = re.findall(
        r'\[(\d{4}),\s*(\d),\s*\[(-?\d{7,15}),\s*(-?\d{7,15}),\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?\d{7,15}),\s*(-?\d{7,15}),\s*null,\s*(-?\d{7,15})',
        flat
    )
    seen = set()
    for year, q, rev, ni, eps, pe, op_inc, interest, gross in quarters:
        key = f"{year}Q{q}"
        if key in seen:
            continue
        seen.add(key)
        result["financials"].append({
            "period": f"FY{year} Q{q}",
            "revenue": int(rev),
            "net_income": int(ni),
            "eps": float(eps),
            "pe": float(pe),
            "op_income": int(op_inc),
            "gross_profit": int(gross),
        })


def _parse_stock_news(flat: str, result: dict):
    """Extract news articles from stock page."""
    articles = re.findall(
        r'"(https?://(?!encrypted-tbn|www\.gstatic)[^"]+)",\s*"([^"]{10,200})",\s*"([^"]{2,50})"',
        flat
    )
    seen = set()
    for url, headline, source in articles:
        if url in seen or "google.com" in url:
            continue
        seen.add(url)
        # Deduplicate with existing
        if not any(e["url"] == url for e in result["key_events"]):
            result["key_events"].append({"url": url, "headline": headline, "source": source})


# ---------------------------------------------------------------------------
# Ticker display
# ---------------------------------------------------------------------------

def print_ticker_report(ticker: str, tdata: dict, args):
    """Print the per-ticker deep dive."""
    now_et = datetime.now(ET).strftime("%Y-%m-%d %I:%M %p ET")
    print(f"\n\033[1;36m{'═' * W}\033[0m")
    print(f"\033[1;37m  {tdata['title'] or ticker}  •  {now_et}\033[0m")
    print(f"\033[1;36m{'═' * W}\033[0m")

    if tdata.get("profile"):
        print(f"\n  \033[2m{tdata['profile']}\033[0m")

    # Sessions (pre-market, regular, after-hours)
    if tdata["sessions"]:
        _section("PRICE SESSIONS (1-min bars)", SRC_GOOGLE)
        for sess in tdata["sessions"]:
            name = sess["name"]
            bars = sess["bars"]
            o, c, h, l = sess["open"], sess["close"], sess["high"], sess["low"]
            chg = c - o if o and c else 0
            pct = (chg / o * 100) if o else 0
            color = "\033[32m" if chg >= 0 else "\033[31m"

            print(f"\n  \033[1m{name}\033[0m  {sess['start']}–{sess['end']}  ({sess['count']} bars)")
            print(f"    Open {o:>10.2f}    Close {color}{c:>10.2f}\033[0m    {color}{'+' if chg>=0 else ''}{chg:.2f} ({'+' if pct>=0 else ''}{pct:.2f}%)\033[0m")
            print(f"    High {h:>10.2f}    Low   {l:>10.2f}    Range {h-l:.2f}")

            # Show last 5 bars (most recent price action)
            print(f"    \033[2mLast 5 bars:\033[0m")
            for b in bars[-5:]:
                vol_str = f"  vol {b['volume']:>8,}" if b["volume"] else ""
                bc = "\033[32m" if (b.get("change") or 0) >= 0 else "\033[31m"
                print(f"      {b['time']}  {bc}${b['price']:.2f}\033[0m{vol_str}")

    # Financials
    if tdata["financials"]:
        _section("QUARTERLY FINANCIALS", SRC_GOOGLE)
        print(f"    {'Period':<11} {'Revenue':>10} {'Net Inc':>10} {'EPS':>7} {'P/E':>6} {'Gross':>10} {'Op Inc':>10}")
        print(f"    {'─'*66}")
        for f in tdata["financials"][:8]:
            rev = f"${f['revenue']/1e9:.1f}B"
            ni = f"${f['net_income']/1e9:.1f}B"
            gross = f"${f['gross_profit']/1e9:.1f}B"
            op = f"${f['op_income']/1e9:.1f}B"
            print(f"    {f['period']:<11} {rev:>10} {ni:>10} {f['eps']:>7.2f} {f['pe']:>6.1f} {gross:>10} {op:>10}")

    # Key events / news
    if tdata["key_events"]:
        n = args.articles
        events = tdata["key_events"][:n]
        _section(f"KEY EVENTS ({len(events)})", SRC_GOOGLE)

        # Fetch article text if requested
        article_texts = None
        if not args.no_articles and HAS_TRAFILATURA and events:
            urls = [e["url"] for e in events]
            print(f"  \033[2mFetching {len(urls)} articles…\033[0m", file=sys.stderr)
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(extract_article_text, url): url for url in urls}
                article_texts = {}
                for future in as_completed(futures):
                    r = future.result()
                    article_texts[r["url"]] = r

        for i, ev in enumerate(events):
            print(f"\n  \033[1m[{i+1}]\033[0m [{ev['source']}] {ev['headline']}")
            print(f"      \033[4m{ev['url']}\033[0m")
            if article_texts and ev["url"] in article_texts:
                t = article_texts[ev["url"]]
                if t.get("error"):
                    print(f"      \033[33m⚠ {t['error']}\033[0m")
                elif t.get("text"):
                    text = t["text"]
                    if len(text) > 1500:
                        text = text[:1500] + "…"
                    for line in text.split("\n"):
                        line = line.strip()
                        if line:
                            print(f"      {line}")


def build_ticker_json(ticker: str, tdata: dict) -> dict:
    """Build JSON for ticker mode."""
    out = {
        "ticker": ticker,
        "title": tdata["title"],
        "profile": tdata["profile"],
        "source": "google_finance",
        "timestamp": datetime.now(ET).isoformat(),
        "sessions": [],
        "financials": tdata["financials"],
        "key_events": tdata["key_events"],
    }
    for sess in tdata["sessions"]:
        out["sessions"].append({
            "name": sess["name"],
            "type": sess["type"],
            "start": sess["start"],
            "end": sess["end"],
            "open": sess["open"],
            "close": sess["close"],
            "high": sess["high"],
            "low": sess["low"],
            "bar_count": sess["count"],
            "bars": sess["bars"],
        })
    return out


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

W = 72  # terminal width
SRC_GOOGLE = "\033[2m[Google Finance]\033[0m"
SRC_YAHOO = "\033[2m[Yahoo Finance]\033[0m"
SRC_MIXED = "\033[2m[Google Finance + trafilatura]\033[0m"


def _section(title: str, source: str):
    print(f"\n\033[1;36m{'─' * W}\033[0m")
    pad = W - len(title) - 4
    print(f"\033[1;37m  {title}\033[0m{' ' * max(1, pad - len(source) + 14)}{source}")


def _pct_color(pct: float) -> str:
    if pct >= 0:
        return f"\033[32m+{pct:.2f}%\033[0m"
    return f"\033[31m{pct:.2f}%\033[0m"


def _pct_bar(pct: float, scale: float = 4.0) -> str:
    width = min(int(abs(pct) / scale * 8), 16)
    if pct >= 0:
        return f"\033[32m{'█' * width}\033[0m"
    return f"\033[31m{'█' * width}\033[0m"


def print_indices(indices: list):
    _section("INDICES", SRC_GOOGLE)
    if not indices:
        print("    (unavailable)")
        return
    # Compact 2-column layout
    for q in indices:
        sym = q["symbol"].replace(".", "")
        name_map = {
            "INX": "SPX", "DJI": "DJI", "IXIC": "NDX",
            "RUT": "RUT", "VIX": "VIX", "RUI": "R1K", "NDX": "NDX",
        }
        label = name_map.get(sym, sym)
        price = fmt_price(q["price"])
        pct = _pct_color(q["pct_change"]) if q["pct_change"] is not None else "N/A"
        print(f"    {label:<5} {price:>11}  {pct}")


def print_sectors(ydata: dict):
    _section("SECTORS", SRC_YAHOO)
    items = []
    for sym, label in SECTOR_TICKERS.items():
        d = ydata.get(sym)
        if d:
            items.append((sym, label, d["pct"]))
    items.sort(key=lambda x: x[2], reverse=True)
    for sym, label, pct in items:
        bar = _pct_bar(pct, scale=2.0)
        print(f"    {sym:<5} {_pct_color(pct):>18}  {label:<12} {bar}")


def print_rates(ydata: dict):
    _section("RATES & BONDS", SRC_YAHOO)
    # Yields
    parts = []
    for sym, label in RATE_TICKERS.items():
        d = ydata.get(sym)
        if d:
            chg_bp = d["change"] * 100  # convert to basis points
            sign = "+" if chg_bp >= 0 else ""
            parts.append(f"{label} {d['price']:.2f}% {sign}{chg_bp:.0f}bp")
    if parts:
        print(f"    {'    '.join(parts)}")

    # Bond ETFs
    parts = []
    for sym, label in BOND_TICKERS.items():
        d = ydata.get(sym)
        if d:
            parts.append(f"{label} ${d['price']:.2f} {_pct_color(d['pct'])}")
    if parts:
        print(f"    {'    '.join(parts)}")


def print_commodities(ydata: dict):
    _section("COMMODITIES", SRC_YAHOO)
    parts = []
    for sym, label in COMMODITY_TICKERS.items():
        d = ydata.get(sym)
        if d:
            if d["price"] > 100:
                parts.append(f"{label} ${d['price']:,.0f} {_pct_color(d['pct'])}")
            else:
                parts.append(f"{label} ${d['price']:.2f} {_pct_color(d['pct'])}")
    if parts:
        print(f"    {'    '.join(parts)}")


def print_fx_crypto(ydata: dict):
    _section("FX & CRYPTO", SRC_YAHOO)
    parts = []
    for sym, label in FX_TICKERS.items():
        d = ydata.get(sym)
        if d:
            if d["price"] > 10:
                parts.append(f"{label} {d['price']:.2f} {_pct_color(d['pct'])}")
            else:
                parts.append(f"{label} {d['price']:.4f} {_pct_color(d['pct'])}")
    if parts:
        print(f"    {'    '.join(parts)}")
    parts = []
    for sym, label in CRYPTO_TICKERS.items():
        d = ydata.get(sym)
        if d:
            parts.append(f"{label} ${d['price']:,.0f} {_pct_color(d['pct'])}")
    if parts:
        print(f"    {'    '.join(parts)}")


def print_global(ydata: dict):
    _section("GLOBAL (overnight)", SRC_YAHOO)
    parts = []
    for sym, label in GLOBAL_TICKERS.items():
        d = ydata.get(sym)
        if d:
            parts.append(f"{label} {d['price']:,.0f} {_pct_color(d['pct'])}")
    if parts:
        print(f"    {'    '.join(parts)}")


def print_movers(movers: list):
    _section("MOVERS", SRC_GOOGLE)
    gainers = sorted([q for q in movers if (q.get("pct_change") or 0) > 0],
                     key=lambda x: x["pct_change"], reverse=True)[:5]
    losers = sorted([q for q in movers if (q.get("pct_change") or 0) < 0],
                    key=lambda x: x["pct_change"])[:5]
    if gainers:
        line = "  ".join(f"\033[32m{q['symbol']} +{q['pct_change']:.1f}%\033[0m" for q in gainers)
        print(f"    ▲ {line}")
    if losers:
        line = "  ".join(f"\033[31m{q['symbol']} {q['pct_change']:.1f}%\033[0m" for q in losers)
        print(f"    ▼ {line}")


def print_earnings(earnings: list):
    _section("EARNINGS TODAY", SRC_GOOGLE)
    if not earnings:
        print("    (none)")
        return
    tickers = [e["ticker"] for e in earnings[:15]]
    print(f"    {' '.join(tickers)}")


def print_followed(followed: list):
    _section("MOST FOLLOWED", SRC_GOOGLE)
    for q in followed[:8]:
        print(f"    {q['symbol']:<6} {fmt_price(q['price']):>10}  {_pct_color(q['pct_change'])}")


def print_news(title: str, articles: list, article_texts: list | None):
    _section(title, SRC_MIXED if article_texts else SRC_GOOGLE)
    if not articles:
        print("    (none)")
        return

    text_map = {a["url"]: a for a in (article_texts or [])}

    for i, art in enumerate(articles):
        headline = art.get("headline") or "(no headline)"
        url = art["url"]
        print(f"\n  \033[1m[{i+1}]\033[0m {headline}")
        print(f"      \033[4m{url}\033[0m")

        t = text_map.get(url)
        if t:
            if t.get("error"):
                print(f"      \033[33m⚠ {t['error']}\033[0m")
            elif t.get("text"):
                text = t["text"]
                if len(text) > 1500:
                    text = text[:1500] + "…"
                for line in text.split("\n"):
                    line = line.strip()
                    if line:
                        print(f"      {line}")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json(indices, movers, followed, earnings, news_fin, news_res,
               article_texts_fin, article_texts_res, ydata, elapsed, n_articles):
    def _ygroup(ticker_map):
        out = {}
        for sym, label in ticker_map.items():
            d = ydata.get(sym)
            if d:
                out[label] = {"ticker": sym, **d}
        return out

    output = {
        "timestamp": datetime.now(ET).isoformat(),
        "elapsed_s": round(elapsed, 1),
        "sources": {
            "indices": "google_finance", "movers": "google_finance",
            "most_followed": "google_finance", "earnings": "google_finance",
            "news": "google_finance+trafilatura",
            "sectors": "yahoo_finance", "rates": "yahoo_finance",
            "commodities": "yahoo_finance", "fx": "yahoo_finance",
            "crypto": "yahoo_finance", "global": "yahoo_finance",
            "bonds": "yahoo_finance",
        },
        "indices": indices,
        "sectors": _ygroup(SECTOR_TICKERS),
        "rates": _ygroup(RATE_TICKERS),
        "bonds": _ygroup(BOND_TICKERS),
        "commodities": _ygroup(COMMODITY_TICKERS),
        "fx": _ygroup(FX_TICKERS),
        "crypto": _ygroup(CRYPTO_TICKERS),
        "global": _ygroup(GLOBAL_TICKERS),
        "movers": movers,
        "most_followed": followed,
        "earnings_calendar": earnings,
        "news_financial": news_fin[:n_articles],
        "news_research": news_res[:n_articles],
    }

    # Attach article text
    for section_key, texts in [("news_financial", article_texts_fin),
                                ("news_research", article_texts_res)]:
        if not texts:
            continue
        tmap = {t["url"]: t for t in texts}
        for art in output[section_key]:
            m = tmap.get(art["url"])
            if m:
                art["article_text"] = m.get("text")
                art["article_error"] = m.get("error")

    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args):
    t0 = time.time()

    # --- Ticker mode: deep dive on a single stock ---
    if args.ticker:
        print(f"\033[2mResolving {args.ticker}…\033[0m", file=sys.stderr)
        resolved = resolve_exchange(args.ticker)
        if not resolved:
            print(f"ERROR: Could not find {args.ticker} on NASDAQ/NYSE/NYSEARCA", file=sys.stderr)
            sys.exit(1)
        html, exch = resolved
        print(f"\033[2mParsing {args.ticker}:{exch}…\033[0m", file=sys.stderr)
        tdata = parse_ticker_page(html)
        elapsed = time.time() - t0
        if args.json:
            out = build_ticker_json(args.ticker.upper(), tdata)
            out["exchange"] = exch
            out["elapsed_s"] = round(elapsed, 1)
            json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
            print()
        else:
            print_ticker_report(args.ticker.upper(), tdata, args)
            print(f"\n\033[2m  {elapsed:.1f}s total ({args.ticker}:{exch})\033[0m")
        return

    # --- Google Finance (parallel with Yahoo) ---
    gf_result = [None]
    yf_result = [{}]

    def _fetch_google():
        print("\033[2mFetching Google Finance…\033[0m", file=sys.stderr)
        html = fetch_url(GOOGLE_FINANCE_URL)
        callbacks = extract_callbacks(html)
        if not callbacks:
            print("ERROR: No AF_initDataCallback data found.", file=sys.stderr)
            return
        mapping = identify_callbacks(callbacks)
        gf_result[0] = (callbacks, mapping)

    def _fetch_yahoo():
        if args.lite or not HAS_YFINANCE:
            return
        print("\033[2mFetching Yahoo Finance (33 tickers)…\033[0m", file=sys.stderr)
        yf_result[0] = fetch_yahoo_quotes()

    with ThreadPoolExecutor(max_workers=2) as pool:
        pool.submit(_fetch_google)
        yf_future = pool.submit(_fetch_yahoo)
        yf_future.result()  # wait for both

    if gf_result[0] is None:
        sys.exit(1)

    callbacks, mapping = gf_result[0]
    ydata = yf_result[0]

    # Parse Google data
    indices = parse_indices(callbacks, mapping)
    movers = parse_movers(callbacks, mapping)
    followed = parse_most_followed(callbacks, mapping)
    earnings = parse_earnings_calendar(callbacks, mapping)
    news_fin, news_res = parse_news(callbacks, mapping)

    # Fetch articles
    n_articles = args.articles
    article_texts_fin = None
    article_texts_res = None

    if not args.no_articles and n_articles > 0 and HAS_TRAFILATURA:
        fin_urls = [a["url"] for a in news_fin[:n_articles]]
        res_urls = [a["url"] for a in news_res[:n_articles]]
        all_urls = fin_urls + res_urls
        if all_urls:
            print(f"\033[2mFetching {len(all_urls)} articles…\033[0m", file=sys.stderr)
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(extract_article_text, url): url for url in all_urls}
                all_texts = {}
                for future in as_completed(futures):
                    r = future.result()
                    all_texts[r["url"]] = r
            article_texts_fin = [all_texts[u] for u in fin_urls if u in all_texts]
            article_texts_res = [all_texts[u] for u in res_urls if u in all_texts]

    elapsed = time.time() - t0

    # --- Output ---
    if args.json:
        out = build_json(indices, movers, followed, earnings,
                         news_fin, news_res, article_texts_fin, article_texts_res,
                         ydata, elapsed, n_articles)
        json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        now_et = datetime.now(ET).strftime("%Y-%m-%d %I:%M %p ET")
        print(f"\n\033[1;36m{'═' * W}\033[0m")
        print(f"\033[1;37m  US MARKET SNAPSHOT  •  {now_et}\033[0m")
        print(f"\033[1;36m{'═' * W}\033[0m")

        if args.section in (None, "market"):
            print_indices(indices)
            if ydata:
                print_sectors(ydata)
                print_rates(ydata)
                print_commodities(ydata)
                print_fx_crypto(ydata)
                print_global(ydata)
            print_movers(movers)
            print_followed(followed)
            print_earnings(earnings)

        if args.section in (None, "news"):
            print_news(f"FINANCIAL NEWS ({len(news_fin[:n_articles])})", news_fin[:n_articles], article_texts_fin)
            print_news(f"RESEARCH ({len(news_res[:n_articles])})", news_res[:n_articles], article_texts_res)

        y_note = f" + Yahoo {len(ydata)} tickers" if ydata else ""
        print(f"\n\033[2m  {elapsed:.1f}s total (Google{y_note} + {len((article_texts_fin or []) + (article_texts_res or []))} articles)\033[0m")


def main():
    p = argparse.ArgumentParser(description="US Market Snapshot")
    p.add_argument("--ticker", type=str, help="Deep dive on a single stock (e.g. AAPL, GS:NYSE)")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--lite", action="store_true", help="Google Finance only (skip Yahoo)")
    p.add_argument("--articles", type=int, default=10, help="Articles per section (default: 10)")
    p.add_argument("--no-articles", action="store_true", help="Skip article text")
    p.add_argument("--section", choices=["market", "news"], help="Only one section")
    main_args = p.parse_args()
    run(main_args)


if __name__ == "__main__":
    main()
