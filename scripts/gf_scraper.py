#!/usr/bin/env python3
"""
Google Finance Market Summary Scraper
======================================
Fetches real-time US market summary from Google Finance, including:
  - Major US indices (S&P 500, Dow, Nasdaq, Russell 2000)
  - Top gainers / losers
  - Most followed stocks
  - Earnings calendar
  - Market news headlines + full article text (first N links)
  - Research/financial news + full article text (first N links)

Data source: AF_initDataCallback JSON blobs embedded in server-rendered HTML.
No browser/JS execution needed — pure HTTP + parse.

Usage:
  python3 scripts/market_summary.py                  # pretty terminal output
  python3 scripts/market_summary.py --json            # JSON output
  python3 scripts/market_summary.py --articles 5      # fetch text from first 5 articles (default: 10)
  python3 scripts/market_summary.py --no-articles     # skip article text fetching
  python3 scripts/market_summary.py --section news    # only news section
  python3 scripts/market_summary.py --section market  # only market data
"""

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Optional: trafilatura for article extraction
try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GOOGLE_FINANCE_URL = "https://www.google.com/finance/?hl=en&gl=us"

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
]

# US exchanges / indices to filter for
US_EXCHANGES = {"NASDAQ", "NYSE", "NYSEARCA", "NYSEAMERICAN", "BATS", "INDEXSP", "INDEXDJX", "INDEXNASDAQ", "INDEXRUSSELL"}

# Major US indices by symbol
US_INDEX_SYMBOLS = {".INX", ".DJI", ".IXIC", "RUT", "RUI", "NDX", "VIX"}

ET = timezone(timedelta(hours=-4))  # EDT

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_url(url: str, retries: int = 3, timeout: int = 15) -> str:
    """Fetch URL with retry + rotating user agent."""
    last_err = None
    for attempt in range(retries):
        ua = USER_AGENTS[attempt % len(USER_AGENTS)]
        req = Request(url, headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (URLError, HTTPError, TimeoutError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {last_err}")


def extract_article_text(url: str, timeout: int = 12) -> dict:
    """Fetch a URL and extract article text using trafilatura."""
    result = {"url": url, "title": None, "text": None, "error": None}
    if not HAS_TRAFILATURA:
        result["error"] = "trafilatura not installed"
        return result
    try:
        html = fetch_url(url, retries=2, timeout=timeout)
        text = trafilatura.extract(html, include_comments=False, include_tables=True,
                                   favor_precision=False, favor_recall=True)
        metadata = trafilatura.extract_metadata(html)
        result["title"] = metadata.title if metadata else None
        result["text"] = text if text else "(no extractable text)"
    except Exception as e:
        result["error"] = str(e)
    return result

# ---------------------------------------------------------------------------
# Google Finance parser
# ---------------------------------------------------------------------------

def extract_callbacks(html: str) -> dict[str, Any]:
    """Extract all AF_initDataCallback data blobs keyed by ds:N."""
    callbacks = {}
    for m in re.finditer(r"AF_initDataCallback\(\{key:\s*'(ds:\d+)'", html):
        key = m.group(1)
        # Find "data:" after the key
        data_prefix = "data:"
        data_start = html.find(data_prefix, m.start())
        if data_start < 0 or data_start > m.start() + 500:
            continue
        data_start += len(data_prefix)

        # Walk to find the balanced end of the JSON array
        depth = 0
        i = data_start
        end = min(len(html), data_start + 500_000)
        while i < end:
            ch = html[i]
            if ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    break
            elif ch == '"':
                # skip string contents
                i += 1
                while i < end and html[i] != '"':
                    if html[i] == '\\':
                        i += 1  # skip escaped char
                    i += 1
            i += 1

        raw = html[data_start:i + 1]
        try:
            callbacks[key] = json.loads(raw)
        except json.JSONDecodeError:
            pass
    return callbacks


def identify_callbacks(callbacks: dict) -> dict[str, str]:
    """Identify which callback key contains which data type via content heuristics.

    Google Finance embeds data in AF_initDataCallback blocks with keys like ds:0..ds:9.
    The key numbers can shift between requests, so we identify by content patterns:
      - indices_sections: grouped index sections ("Dow Jones" label + .DJI data)
      - index_cards: flat list of major indices (.INX first)
      - most_followed: contains AAPL + TSLA + GOOGL (big-cap watchlist)
      - gainers_losers: high pct_change stocks (top movers)
      - spotlight: single featured stock with news URL (marketwatch/barrons)
      - earnings_calendar: calendar.google.com links + "Earnings"
      - news_financial: many article URLs alongside stock quote arrays
      - news_research: article URLs without stock context (general/research)
    """
    mapping = {}
    # Score each callback
    for key, data in callbacks.items():
        flat = json.dumps(data, ensure_ascii=False)
        sample = flat[:8000]

        # --- Indices ---
        if '".DJI"' in sample and '"Dow Jones"' in sample:
            mapping["indices_sections"] = key
        if '".INX"' in sample and '".DJI"' in sample and key != mapping.get("indices_sections"):
            mapping["index_cards"] = key

        # --- Most followed (AAPL + TSLA + GOOGL watchlist, has volume numbers) ---
        if '"AAPL"' in sample and '"TSLA"' in sample and '"GOOGL"' in sample:
            mapping["most_followed"] = key

        # --- Earnings calendar ---
        if "calendar.google.com" in flat and "Earnings" in flat:
            mapping["earnings_calendar"] = key

        # --- News sections (both have article URLs; distinguish by stock density) ---
        article_urls = re.findall(r'"(https?://(?!encrypted-tbn|www\.gstatic|calendar\.google)[^"]+)"', flat)
        if len(article_urls) >= 3 and key not in mapping.values():
            # Count stock ticker references — financial news has many more
            ticker_refs = len(re.findall(r'"(?:NYSE|NASDAQ)"', flat))
            if ticker_refs >= 8:
                if "news_financial" not in mapping:
                    mapping["news_financial"] = key
            elif "news_research" not in mapping:
                mapping["news_research"] = key

        # --- Gainers/losers (stocks with extreme pct changes, no article URLs) ---
        # The real gainers/losers callback has multiple stocks with 10%+ moves
        pct_matches = re.findall(r',\s*(-?\d+\.\d+),\s*[23],\s*[234],\s*[23]\]', flat)
        if len(pct_matches) >= 6 and len(article_urls) < 3:
            pcts = [abs(float(p)) for p in pct_matches]
            extreme = sum(1 for p in pcts if p > 10.0)
            if extreme >= 3:  # at least 3 stocks with 10%+ moves = true movers
                mapping["gainers_losers"] = key

        # --- Spotlight mover (single featured stock + MarketWatch/Barrons URL) ---
        if (len(article_urls) == 1
                and any(x in flat for x in ["marketwatch.com", "barrons.com"])
                and key not in mapping.values()):
            mapping["spotlight"] = key

    return mapping


def parse_quote(arr: list) -> dict | None:
    """Parse a single quote/index array into a structured dict.

    The array format (positional):
      [0] freebase_id     "/m/016yss"
      [1] [symbol, exchange]  [".INX", "INDEXSP"]
      [2] name            "S&P 500"
      [3] asset_type      0=stock, 1=index
      [4] currency        "USD" or null (indices)
      [5] [price, change, pct_change, ...]
      [7] prev_close
      ...
    """
    if not isinstance(arr, list) or len(arr) < 6:
        return None
    try:
        sym_exch = arr[1]
        if not isinstance(sym_exch, list) or len(sym_exch) < 2:
            return None
        symbol = sym_exch[0]
        exchange = sym_exch[1]
        name = arr[2]
        asset_type = "index" if arr[3] == 1 else "stock"
        currency = arr[4]
        price_arr = arr[5] if isinstance(arr[5], list) else []
        price = price_arr[0] if len(price_arr) > 0 else None
        change = price_arr[1] if len(price_arr) > 1 else None
        pct_change = price_arr[2] if len(price_arr) > 2 else None
        prev_close = arr[7] if len(arr) > 7 else None
        return {
            "symbol": symbol,
            "exchange": exchange,
            "name": name,
            "type": asset_type,
            "currency": currency,
            "price": price,
            "change": change,
            "pct_change": pct_change,
            "prev_close": prev_close,
        }
    except (IndexError, TypeError):
        return None


def is_us_quote(q: dict) -> bool:
    """Check if a parsed quote is US-based."""
    if not q:
        return False
    if q["exchange"] in US_EXCHANGES:
        return True
    if q["symbol"] in US_INDEX_SYMBOLS:
        return True
    return False


def parse_indices(callbacks: dict, mapping: dict) -> list[dict]:
    """Extract US indices from the indices_sections or index_cards callback."""
    results = []
    seen = set()

    for cb_name in ("indices_sections", "index_cards"):
        key = mapping.get(cb_name)
        if not key or key not in callbacks:
            continue
        data = callbacks[key]
        _walk_for_quotes(data, results, seen, us_only=True, types={"index"})

    return results


def parse_movers(callbacks: dict, mapping: dict) -> list[dict]:
    """Extract top movers (gainers/losers) from gainers_losers + spotlight callbacks."""
    results = []
    seen = set()

    for cb_name in ("gainers_losers", "spotlight"):
        key = mapping.get(cb_name)
        if not key or key not in callbacks:
            continue
        _walk_for_quotes(callbacks[key], results, seen, us_only=True, types={"stock"})

    return results


def parse_most_followed(callbacks: dict, mapping: dict) -> list[dict]:
    """Extract most followed stocks."""
    results = []
    seen = set()
    key = mapping.get("most_followed")
    if key and key in callbacks:
        _walk_for_quotes(callbacks[key], results, seen, us_only=True, types={"stock"})
    return results


def _walk_for_quotes(data, results: list, seen: set, us_only: bool = True, types: set | None = None):
    """Recursively walk nested arrays to find quote arrays."""
    if not isinstance(data, list):
        return
    # Check if this looks like a quote array (has freebase id pattern)
    if (len(data) >= 6
            and isinstance(data[0], str) and data[0].startswith("/")
            and isinstance(data[1], list) and len(data[1]) >= 2):
        q = parse_quote(data)
        if q and q["symbol"] not in seen:
            if (not us_only or is_us_quote(q)) and (not types or q["type"] in types):
                results.append(q)
                seen.add(q["symbol"])
        return
    # Recurse
    for item in data:
        if isinstance(item, list):
            _walk_for_quotes(item, results, seen, us_only, types)


def parse_news(callbacks: dict, mapping: dict) -> tuple[list[dict], list[dict]]:
    """Extract news articles (financial and general)."""
    financial = []
    general = []

    for category, output in [("news_financial", financial), ("news_research", general)]:
        key = mapping.get(category)
        if not key or key not in callbacks:
            continue
        data = callbacks[key]
        flat = json.dumps(data, ensure_ascii=False)
        # Extract URLs and their surrounding context for headlines
        urls = re.findall(r'"(https?://(?!encrypted-tbn|www\.gstatic)[^"]+)"', flat)
        headlines = re.findall(r'"([A-Z][^"]{15,200})"', flat)
        # Pair them up heuristically
        seen_urls = set()
        for url in urls:
            if url in seen_urls:
                continue
            if any(x in url for x in ["gstatic.com", "calendar.google.com", "google.com/finance"]):
                continue
            seen_urls.add(url)
            # Find the nearest headline
            url_pos = flat.find(url)
            best_headline = None
            best_dist = float('inf')
            for h in headlines:
                h_pos = flat.find(h)
                dist = abs(h_pos - url_pos)
                if dist < best_dist and dist < 1000:
                    best_dist = dist
                    best_headline = h
            output.append({"url": url, "headline": best_headline})

    return financial, general


def parse_earnings_calendar(callbacks: dict, mapping: dict) -> list[dict]:
    """Extract today's earnings calendar."""
    results = []
    key = mapping.get("earnings_calendar")
    if not key or key not in callbacks:
        return results
    data = callbacks[key]
    flat = json.dumps(data, ensure_ascii=False)
    # Find company names and tickers in earnings data
    entries = re.findall(r'\["(/[^"]+)",\s*\["([^"]+)",\s*"([^"]+)"\],\s*"([^"]*)",\s*"([^"]*)"', flat)
    for fid, ticker, exchange, alt_id, name in entries:
        if name:
            results.append({"ticker": ticker, "exchange": exchange, "name": name})
    return results

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def fmt_change(change: float | None, pct: float | None) -> str:
    if change is None or pct is None:
        return "N/A"
    sign = "+" if change >= 0 else ""
    arrow = "\033[32m▲\033[0m" if change >= 0 else "\033[31m▼\033[0m"
    return f"{arrow} {sign}{change:,.2f} ({sign}{pct:.2f}%)"


def fmt_price(price: float | None) -> str:
    if price is None:
        return "N/A"
    return f"{price:,.2f}"


def print_section(title: str):
    width = 72
    print(f"\n\033[1;36m{'─' * width}\033[0m")
    print(f"\033[1;37m  {title}\033[0m")
    print(f"\033[1;36m{'─' * width}\033[0m")


def print_market_summary(indices: list, movers: list, followed: list,
                         earnings: list, timestamp: str):
    print_section(f"US MARKET SUMMARY  •  {timestamp}")

    if indices:
        print(f"\n  \033[1mMajor Indices\033[0m")
        for q in indices:
            print(f"    {q['name']:<35} {fmt_price(q['price']):>12}  {fmt_change(q['change'], q['pct_change'])}")

    if followed:
        print(f"\n  \033[1mMost Followed\033[0m")
        for q in followed[:10]:
            label = f"{q['symbol']:<6} {q['name']}"
            print(f"    {label:<35} {fmt_price(q['price']):>12}  {fmt_change(q['change'], q['pct_change'])}")

    if movers:
        gainers = [q for q in movers if q.get("pct_change") and q["pct_change"] > 0]
        losers = [q for q in movers if q.get("pct_change") and q["pct_change"] < 0]
        gainers.sort(key=lambda x: x["pct_change"] or 0, reverse=True)
        losers.sort(key=lambda x: x["pct_change"] or 0)

        if gainers:
            print(f"\n  \033[1;32mTop Gainers\033[0m")
            for q in gainers[:5]:
                label = f"{q['symbol']:<6} {q['name']}"
                print(f"    {label:<35} {fmt_price(q['price']):>12}  {fmt_change(q['change'], q['pct_change'])}")
        if losers:
            print(f"\n  \033[1;31mTop Losers\033[0m")
            for q in losers[:5]:
                label = f"{q['symbol']:<6} {q['name']}"
                print(f"    {label:<35} {fmt_price(q['price']):>12}  {fmt_change(q['change'], q['pct_change'])}")

    if earnings:
        print(f"\n  \033[1mEarnings Today\033[0m")
        for e in earnings[:10]:
            print(f"    {e['ticker']:<6} {e['name']}")


def print_news_section(title: str, articles: list[dict], article_texts: list[dict] | None):
    print_section(title)
    if not articles:
        print("    (none)")
        return

    text_map = {}
    if article_texts:
        text_map = {a["url"]: a for a in article_texts}

    for i, art in enumerate(articles):
        headline = art.get("headline") or "(no headline)"
        url = art["url"]
        print(f"\n  \033[1m[{i+1}]\033[0m {headline}")
        print(f"      \033[4m{url}\033[0m")

        if url in text_map:
            t = text_map[url]
            if t.get("error"):
                print(f"      \033[33m⚠ {t['error']}\033[0m")
            elif t.get("text"):
                # Truncate to ~800 chars for display
                text = t["text"]
                if len(text) > 1500:
                    text = text[:1500] + "…"
                for line in text.split("\n"):
                    line = line.strip()
                    if line:
                        print(f"      {line}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args):
    t0 = time.time()
    print("\033[2mFetching Google Finance…\033[0m", file=sys.stderr)
    html = fetch_url(GOOGLE_FINANCE_URL)
    elapsed_fetch = time.time() - t0

    callbacks = extract_callbacks(html)
    if not callbacks:
        print("ERROR: No AF_initDataCallback data found. Google may have changed the page format.", file=sys.stderr)
        sys.exit(1)

    mapping = identify_callbacks(callbacks)
    now_et = datetime.now(ET).strftime("%Y-%m-%d %I:%M %p ET")

    # Parse market data
    indices = parse_indices(callbacks, mapping)
    movers = parse_movers(callbacks, mapping)
    followed = parse_most_followed(callbacks, mapping)
    earnings = parse_earnings_calendar(callbacks, mapping)
    news_financial, news_general = parse_news(callbacks, mapping)

    # Fetch article text if requested
    article_texts_financial = None
    article_texts_general = None
    n_articles = args.articles

    if not args.no_articles and n_articles > 0 and HAS_TRAFILATURA:
        urls_to_fetch = []
        fin_urls = [a["url"] for a in news_financial[:n_articles]]
        gen_urls = [a["url"] for a in news_general[:n_articles]]
        all_urls = fin_urls + gen_urls

        if all_urls:
            print(f"\033[2mFetching {len(all_urls)} articles…\033[0m", file=sys.stderr)
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {pool.submit(extract_article_text, url): url for url in all_urls}
                all_texts = {}
                for future in as_completed(futures):
                    result = future.result()
                    all_texts[result["url"]] = result

            article_texts_financial = [all_texts[u] for u in fin_urls if u in all_texts]
            article_texts_general = [all_texts[u] for u in gen_urls if u in all_texts]

    elapsed_total = time.time() - t0

    if args.json:
        output = {
            "timestamp": now_et,
            "fetch_time_s": round(elapsed_fetch, 2),
            "total_time_s": round(elapsed_total, 2),
            "indices": indices,
            "most_followed": followed,
            "movers": movers,
            "earnings_calendar": earnings,
            "news_financial": news_financial[:n_articles],
            "news_general": news_general[:n_articles],
        }
        if article_texts_financial:
            for art in output["news_financial"]:
                match = next((t for t in article_texts_financial if t["url"] == art["url"]), None)
                if match:
                    art["article_title"] = match.get("title")
                    art["article_text"] = match.get("text")
                    art["article_error"] = match.get("error")
        if article_texts_general:
            for art in output["news_general"]:
                match = next((t for t in article_texts_general if t["url"] == art["url"]), None)
                if match:
                    art["article_title"] = match.get("title")
                    art["article_text"] = match.get("text")
                    art["article_error"] = match.get("error")
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        if args.section in (None, "market"):
            print_market_summary(indices, movers, followed, earnings, now_et)
        if args.section in (None, "news"):
            print_news_section("FINANCIAL NEWS", news_financial[:n_articles], article_texts_financial)
            print_news_section("GENERAL NEWS / RESEARCH", news_general[:n_articles], article_texts_general)

        print(f"\n\033[2m  Fetched in {elapsed_fetch:.1f}s page + {elapsed_total - elapsed_fetch:.1f}s articles = {elapsed_total:.1f}s total\033[0m")
        print(f"\033[2m  Callbacks found: {list(callbacks.keys())}  Mapped: {mapping}\033[0m")


def main():
    parser = argparse.ArgumentParser(description="Google Finance US Market Summary")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--articles", type=int, default=10, help="Number of articles to fetch text for (default: 10)")
    parser.add_argument("--no-articles", action="store_true", help="Skip article text fetching")
    parser.add_argument("--section", choices=["market", "news"], help="Only show specific section")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
