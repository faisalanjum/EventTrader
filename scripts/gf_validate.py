#!/usr/bin/env python3
"""
Validate market_snapshot.py --ticker against the full ticker universe.

Pull 1: Fetch all tickers, validate data quality.
Pull 2: After 60s, re-fetch a sample to verify price updates.

Usage:
  venv/bin/python3 scripts/validate_ticker_fetch.py                # full run
  venv/bin/python3 scripts/validate_ticker_fetch.py --sample 20    # quick test with 20 tickers
  venv/bin/python3 scripts/validate_ticker_fetch.py --skip-pull2   # skip the 60s wait + re-fetch
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gf_scraper import fetch_url, extract_callbacks
from gf_snapshot import (
    resolve_exchange, parse_ticker_page, STOCK_QUOTE_URL,
    SESSION_NAMES, ET,
)

UNIVERSE_CSV = "/tmp/ticker_universe.csv"
RESULTS_DIR = "/tmp/ticker_validation"

# Google Finance exchange map
GF_EXCHANGE = {"NYS": "NYSE", "NAS": "NASDAQ", "BATS": "BATS", "ASE": "NYSEAMERICAN"}


def load_universe(path: str, sample: int | None = None) -> list[tuple[str, str]]:
    """Load ticker,exchange pairs from CSV."""
    pairs = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append((row["ticker"], row["gf_exchange"]))
    if sample and sample < len(pairs):
        import random
        random.seed(42)
        pairs = random.sample(pairs, sample)
    return pairs


def fetch_one(ticker: str, exchange: str) -> dict:
    """Fetch and parse a single ticker. Returns validation result."""
    result = {
        "ticker": ticker,
        "exchange": exchange,
        "status": "ok",
        "title": None,
        "sessions": 0,
        "regular_bars": 0,
        "afterhours_bars": 0,
        "premarket_bars": 0,
        "latest_price": None,
        "latest_time": None,
        "financials": 0,
        "key_events": 0,
        "has_profile": False,
        "fetch_ms": 0,
        "error": None,
    }

    t0 = time.time()
    try:
        # Try given exchange first, then fallback to others
        html = None
        actual_exchange = exchange
        for exch in [exchange] + [e for e in ["NASDAQ", "NYSE", "NYSEARCA"] if e != exchange]:
            url = STOCK_QUOTE_URL.format(ticker=ticker, exchange=exch)
            try:
                candidate = fetch_url(url, retries=1, timeout=10)
                m = re.search(r'<title>([^<]+)</title>', candidate)
                if m and ("Stock Price" in m.group(1) or "Price &" in m.group(1)):
                    html = candidate
                    actual_exchange = exch
                    break
            except Exception:
                continue

        if html is None:
            result["status"] = "not_found"
            result["error"] = f"Not found on any exchange"
            result["fetch_ms"] = int((time.time() - t0) * 1000)
            return result

        result["exchange"] = actual_exchange

        tdata = parse_ticker_page(html)
        result["title"] = tdata.get("title")
        result["has_profile"] = bool(tdata.get("profile"))
        result["financials"] = len(tdata.get("financials", []))
        result["key_events"] = len(tdata.get("key_events", []))

        for sess in tdata.get("sessions", []):
            result["sessions"] += 1
            stype = sess.get("type")
            bars = sess.get("count", 0)
            if stype == 1:
                result["regular_bars"] = bars
                result["latest_price"] = sess["close"]
                result["latest_time"] = sess["end"]
            elif stype == 3:
                result["afterhours_bars"] = bars
                result["latest_price"] = sess["close"]
                result["latest_time"] = sess["end"]
            elif stype == 2:
                result["premarket_bars"] = bars

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]

    result["fetch_ms"] = int((time.time() - t0) * 1000)
    return result


def run_pull(pairs: list[tuple[str, str]], label: str, max_workers: int = 10) -> list[dict]:
    """Fetch all tickers with controlled concurrency."""
    total = len(pairs)
    results = []
    done = 0
    errors = 0
    t0 = time.time()

    print(f"\n{'='*72}")
    print(f"  {label}: {total} tickers, {max_workers} threads")
    print(f"{'='*72}")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_one, t, e): (t, e) for t, e in pairs}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            done += 1
            if r["status"] != "ok":
                errors += 1

            # Progress every 50 tickers
            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                print(f"  [{done:>4}/{total}] {errors} errors | {rate:.1f} tickers/s | ETA {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.1f}s ({len(results)/elapsed:.1f} tickers/s)")
    return results


def print_report(results: list[dict], label: str):
    """Print validation summary."""
    total = len(results)
    ok = sum(1 for r in results if r["status"] == "ok")
    wrong_exch = sum(1 for r in results if r["status"] == "wrong_exchange")
    errors = sum(1 for r in results if r["status"] == "error")

    has_regular = sum(1 for r in results if r["regular_bars"] > 0)
    has_ah = sum(1 for r in results if r["afterhours_bars"] > 0)
    has_pm = sum(1 for r in results if r["premarket_bars"] > 0)
    has_financials = sum(1 for r in results if r["financials"] > 0)
    has_events = sum(1 for r in results if r["key_events"] > 0)
    has_profile = sum(1 for r in results if r["has_profile"])

    avg_ms = sum(r["fetch_ms"] for r in results) / total if total else 0
    avg_regular = sum(r["regular_bars"] for r in results if r["regular_bars"] > 0) / max(has_regular, 1)
    avg_ah = sum(r["afterhours_bars"] for r in results if r["afterhours_bars"] > 0) / max(has_ah, 1)

    print(f"\n{'─'*72}")
    print(f"  {label} REPORT  ({total} tickers)")
    print(f"{'─'*72}")
    print(f"  Status:     OK {ok}  |  Wrong exchange {wrong_exch}  |  Error {errors}")
    print(f"  Coverage:")
    print(f"    Regular session bars:  {has_regular:>4}/{total} ({has_regular/total*100:.1f}%)  avg {avg_regular:.0f} bars")
    print(f"    After-hours bars:      {has_ah:>4}/{total} ({has_ah/total*100:.1f}%)  avg {avg_ah:.0f} bars")
    print(f"    Pre-market bars:       {has_pm:>4}/{total} ({has_pm/total*100:.1f}%)")
    print(f"    Quarterly financials:  {has_financials:>4}/{total} ({has_financials/total*100:.1f}%)")
    print(f"    Key events/news:       {has_events:>4}/{total} ({has_events/total*100:.1f}%)")
    print(f"    Company profile:       {has_profile:>4}/{total} ({has_profile/total*100:.1f}%)")
    print(f"  Performance:  avg {avg_ms:.0f}ms/ticker")

    # Show failures
    failures = [r for r in results if r["status"] != "ok"]
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for r in failures[:20]:
            print(f"    {r['ticker']:>6}:{r['exchange']:<10} {r['status']}  {r.get('error','')[:60]}")
        if len(failures) > 20:
            print(f"    ... +{len(failures)-20} more")


def compare_pulls(pull1: list[dict], pull2: list[dict]):
    """Compare two pulls to verify price updates."""
    p1_map = {r["ticker"]: r for r in pull1}
    p2_map = {r["ticker"]: r for r in pull2}

    common = set(p1_map.keys()) & set(p2_map.keys())
    changed = 0
    same = 0
    both_ok = 0

    print(f"\n{'─'*72}")
    print(f"  PULL COMPARISON  ({len(common)} tickers)")
    print(f"{'─'*72}")

    diffs = []
    for t in sorted(common):
        r1 = p1_map[t]
        r2 = p2_map[t]
        if r1["status"] != "ok" or r2["status"] != "ok":
            continue
        both_ok += 1
        p1_price = r1["latest_price"]
        p2_price = r2["latest_price"]
        if p1_price and p2_price:
            if abs(p1_price - p2_price) > 0.001:
                changed += 1
                diff = p2_price - p1_price
                diffs.append((t, p1_price, p2_price, diff))
            else:
                same += 1

    print(f"  Both OK: {both_ok}")
    print(f"  Price changed: {changed}  |  Price same: {same}")
    if diffs:
        print(f"\n  Price changes (showing up to 10):")
        for t, p1, p2, d in sorted(diffs, key=lambda x: abs(x[3]), reverse=True)[:10]:
            print(f"    {t:>6}  ${p1:.2f} → ${p2:.2f}  ({'+' if d>0 else ''}{d:.2f})")


def main():
    parser = argparse.ArgumentParser(description="Validate ticker fetch against universe")
    parser.add_argument("--sample", type=int, help="Random sample size (default: all)")
    parser.add_argument("--skip-pull2", action="store_true", help="Skip second pull")
    parser.add_argument("--threads", type=int, default=10, help="Concurrent threads (default: 10)")
    parser.add_argument("--wait", type=int, default=60, help="Seconds between pulls (default: 60)")
    args = parser.parse_args()

    if not os.path.exists(UNIVERSE_CSV):
        print(f"ERROR: {UNIVERSE_CSV} not found. Run market_snapshot.py first or generate via Neo4j.", file=sys.stderr)
        sys.exit(1)

    pairs = load_universe(UNIVERSE_CSV, args.sample)
    print(f"Loaded {len(pairs)} tickers from {UNIVERSE_CSV}")

    # Exclude TSE (Canadian) tickers
    pairs = [(t, e) for t, e in pairs if e not in ("TSE", "BATS")]
    print(f"After filtering non-US: {len(pairs)} tickers")

    # Pull 1
    pull1 = run_pull(pairs, "PULL 1", max_workers=args.threads)
    print_report(pull1, "PULL 1")

    # Save results
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"{RESULTS_DIR}/pull1_{ts}.json", "w") as f:
        json.dump(pull1, f, indent=2)
    print(f"\n  Saved to {RESULTS_DIR}/pull1_{ts}.json")

    if args.skip_pull2:
        return

    # Wait
    print(f"\n  Waiting {args.wait}s before Pull 2...")
    time.sleep(args.wait)

    # Pull 2 — only re-fetch tickers that had after-hours data (most likely to change)
    ah_tickers = [(r["ticker"], r["exchange"]) for r in pull1 if r["afterhours_bars"] > 0]
    if not ah_tickers:
        # Fall back to a random sample of OK tickers
        ok_tickers = [(r["ticker"], r["exchange"]) for r in pull1 if r["status"] == "ok"]
        import random
        ah_tickers = random.sample(ok_tickers, min(50, len(ok_tickers)))

    pull2 = run_pull(ah_tickers, "PULL 2 (after-hours subset)", max_workers=args.threads)
    print_report(pull2, "PULL 2")

    with open(f"{RESULTS_DIR}/pull2_{ts}.json", "w") as f:
        json.dump(pull2, f, indent=2)

    compare_pulls(pull1, pull2)


if __name__ == "__main__":
    main()
