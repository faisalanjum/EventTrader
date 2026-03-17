#!/usr/bin/env python3
"""
Trade-Ready Earnings Scanner
==============================
Polls earnings calendars, matches against company universe, writes Redis TradeReady list.

Sources (priority order):
  1. Alpha Vantage EARNINGS_CALENDAR (bulk, paid, authoritative)
  2. earningscall.biz get_calendar (per-date, adds conference_date)
  3. Yahoo Finance yfinance (tie-breaker only, called when 1+2 disagree)

Usage:
  python3 scripts/trade_ready_scanner.py                # Scan today + next trading day
  python3 scripts/trade_ready_scanner.py --list          # Dry run: print, don't write
  python3 scripts/trade_ready_scanner.py --show          # Show current TradeReady list
  python3 scripts/trade_ready_scanner.py --date 2026-03-20  # Specific date only
  python3 scripts/trade_ready_scanner.py --source av     # Single source (av|ecall|yahoo)
  python3 scripts/trade_ready_scanner.py --cleanup       # Purge stale entries only
"""
import argparse
import csv
import io
import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

# Project root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ET = ZoneInfo("America/New_York")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("trade_ready_scanner")

# ── .env loading ──

def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


# ── Trading day logic (NYSE calendar) ──

def get_market_calendar():
    """Return exchange_calendars XNYS calendar instance."""
    import exchange_calendars as xcals
    return xcals.get_calendar("XNYS")


def next_trading_day(cal, from_date: date) -> date:
    """Next NYSE trading day after from_date."""
    import pandas as pd
    return cal.next_session(pd.Timestamp(from_date)).date()


def scan_dates(cal, from_date: date) -> list[date]:
    """Return [today, next_trading_day] — the two dates we check."""
    nxt = next_trading_day(cal, from_date)
    dates = [from_date, nxt] if nxt != from_date else [from_date]
    return sorted(set(dates))


# ── Universe loading ──

def load_universe_neo4j() -> set[str] | None:
    """Load tickers from Neo4j Company nodes."""
    try:
        from scripts.earnings.utils import load_env as load_env_neo4j, neo4j_session
        load_env_neo4j()
        with neo4j_session() as (session, err):
            if err:
                log.warning(f"Neo4j unavailable: {err}")
                return None
            result = session.run("MATCH (c:Company) RETURN c.ticker AS t")
            tickers = {r["t"].upper() for r in result if r["t"]}
            log.info(f"Universe from Neo4j: {len(tickers)} tickers")
            return tickers
    except Exception as e:
        log.warning(f"Neo4j failed: {e}")
        return None


def load_universe_redis(r) -> set[str] | None:
    """Load tickers from Redis admin:tradable_universe:symbols."""
    try:
        raw = r.get("admin:tradable_universe:symbols")
        if not raw:
            return None
        symbols = raw.split(",") if isinstance(raw, str) else raw.decode().split(",")
        tickers = {s.strip().upper() for s in symbols if s.strip()}
        log.info(f"Universe from Redis: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        log.warning(f"Redis universe failed: {e}")
        return None


def load_universe_csv() -> set[str] | None:
    """Load tickers from config/final_symbols.csv."""
    csv_path = ROOT / "config" / "final_symbols.csv"
    if not csv_path.exists():
        return None
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        tickers = {s.upper() for s in df["symbol"].dropna().astype(str) if s.strip()}
        log.info(f"Universe from CSV: {len(tickers)} tickers")
        return tickers
    except Exception as e:
        log.warning(f"CSV universe failed: {e}")
        return None


def load_universe(r=None) -> set[str]:
    """Load universe: Neo4j → Redis → CSV fallback chain."""
    universe = load_universe_neo4j()
    if universe:
        return universe
    if r:
        universe = load_universe_redis(r)
        if universe:
            return universe
    universe = load_universe_csv()
    if universe:
        return universe
    log.error("No universe source available")
    sys.exit(1)


# ── Source 1: Alpha Vantage (PRIMARY) ──

def fetch_alphavantage(api_key: str, target_dates: set[date]) -> dict[str, dict]:
    """Fetch AV EARNINGS_CALENDAR bulk CSV, filter to target_dates."""
    url = f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={api_key}"
    req = Request(url, headers={"User-Agent": "trade-ready-scanner/1.0"})
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        log.error(f"AV fetch failed: {e}")
        return {}

    # Check for error/rate-limit
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and ("Note" in data or "Error Message" in data or "Information" in data):
            log.error(f"AV error: {data}")
            return {}
    except (json.JSONDecodeError, ValueError):
        pass  # Expected — CSV response

    results = {}
    date_strs = {d.isoformat() for d in target_dates}
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        report_date = row.get("reportDate", "")
        if report_date not in date_strs:
            continue
        symbol = (row.get("symbol") or "").upper()
        if not symbol:
            continue
        results[symbol] = {
            "ticker": symbol,
            "earnings_date": report_date,
            "time_of_day": row.get("timeOfTheDay") or "unknown",
            "estimate": row.get("estimate") or None,
            "fiscal_date_ending": row.get("fiscalDateEnding") or None,
            "source": "alphavantage",
        }
    log.info(f"AV: {len(results)} tickers on target dates")
    return results


# ── Source 2: earningscall.biz (SECONDARY) ──

def fetch_earningscall(target_dates: list[date]) -> dict[str, dict]:
    """Fetch earningscall.biz calendar for each target date."""
    try:
        import earningscall
        from earningscall import get_calendar
        # Set API key (env var name used by existing codebase)
        api_key = os.environ.get("EARNINGS_CALL_API_KEY", "")
        if api_key:
            earningscall.api_key = api_key
    except ImportError:
        log.error("earningscall package not installed")
        return {}

    results = {}
    for d in target_dates:
        try:
            events = get_calendar(datetime(d.year, d.month, d.day))
            for e in events:
                symbol = (e.symbol or "").upper()
                if not symbol:
                    continue
                conf_dt = None
                if e.conference_date:
                    try:
                        conf_dt = e.conference_date.astimezone(ET).isoformat()
                    except Exception:
                        conf_dt = str(e.conference_date)
                results[symbol] = {
                    "ticker": symbol,
                    "earnings_date": d.isoformat(),
                    "conference_date": conf_dt,
                    "quarter": getattr(e, "quarter", None),
                    "year": getattr(e, "year", None),
                    "source": "earningscall",
                }
            log.info(f"earningscall {d}: {len(events)} events")
        except Exception as e:
            log.error(f"earningscall fetch failed for {d}: {e}")
    return results


# ── Source 3: Yahoo Finance (TIE-BREAKER) ──

def fetch_yahoo(tickers: list[str]) -> dict[str, dict]:
    """Fetch Yahoo Finance calendar for specific tickers (tie-break only)."""
    if not tickers:
        return {}
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance not installed")
        return {}

    results = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            cal = stock.calendar
            if cal is None or not isinstance(cal, dict):
                continue
            earnings_dates = cal.get("Earnings Date")
            if not earnings_dates:
                continue
            ed = earnings_dates[0] if isinstance(earnings_dates, list) else earnings_dates
            results[ticker] = {
                "ticker": ticker,
                "earnings_date": str(ed)[:10],  # YYYY-MM-DD
                "source": "yahoo",
            }
        except Exception as e:
            log.debug(f"Yahoo failed for {ticker}: {e}")
    if tickers:
        log.info(f"Yahoo tie-break: {len(results)}/{len(tickers)} resolved")
    return results


# ── Merge ──

def merge_sources(av: dict, ecall: dict, universe: set[str]) -> tuple[dict[str, dict], list[str]]:
    """Merge AV + earningscall, filter to universe.
    Returns (merged_entries, tickers_needing_tiebreak)."""
    merged = {}
    conflicts = []

    # Start with AV (primary)
    for ticker, entry in av.items():
        if ticker in universe:
            merged[ticker] = {
                "ticker": ticker,
                "earnings_date": entry["earnings_date"],
                "time_of_day": entry.get("time_of_day", "unknown"),
                "conference_date": None,
                "sources": ["alphavantage"],
                "date_agreement": 1,
            }

    # Merge earningscall
    for ticker, entry in ecall.items():
        if ticker not in universe:
            continue
        if ticker in merged:
            if merged[ticker]["earnings_date"] == entry["earnings_date"]:
                # Same date — merge conference_date
                merged[ticker]["conference_date"] = entry.get("conference_date")
                merged[ticker]["sources"].append("earningscall")
                merged[ticker]["date_agreement"] = 2
            else:
                # Date conflict — needs tie-break
                conflicts.append(ticker)
                merged[ticker]["_ecall_date"] = entry["earnings_date"]
                merged[ticker]["conference_date"] = entry.get("conference_date")
                merged[ticker]["sources"].append("earningscall")
        else:
            # Only in earningscall
            merged[ticker] = {
                "ticker": ticker,
                "earnings_date": entry["earnings_date"],
                "time_of_day": "unknown",
                "conference_date": entry.get("conference_date"),
                "sources": ["earningscall"],
                "date_agreement": 1,
            }

    return merged, conflicts


def resolve_conflicts(merged: dict, conflicts: list[str], yahoo: dict):
    """Resolve date conflicts using Yahoo as tie-breaker. 2-of-3 majority wins."""
    for ticker in conflicts:
        entry = merged.get(ticker)
        if not entry:
            continue
        av_date = entry["earnings_date"]
        ecall_date = entry.pop("_ecall_date", None)
        yahoo_date = yahoo.get(ticker, {}).get("earnings_date")

        dates = [av_date, ecall_date, yahoo_date]
        # Count votes
        votes = {}
        for d in dates:
            if d:
                votes[d] = votes.get(d, 0) + 1

        # Pick majority or fallback to AV
        winner = max(votes, key=votes.get) if votes else av_date
        entry["earnings_date"] = winner
        entry["date_agreement"] = votes.get(winner, 1)
        if yahoo_date:
            entry["sources"].append("yahoo")

    # Clean up any remaining _ecall_date keys
    for entry in merged.values():
        entry.pop("_ecall_date", None)


# ── Redis operations ──

def get_redis():
    """Connect to Redis."""
    import redis as redis_lib
    host = os.environ.get("REDIS_HOST", "192.168.40.72")
    port = int(os.environ.get("REDIS_PORT", "31379"))
    return redis_lib.Redis(host=host, port=port, decode_responses=True)


def write_to_redis(r, entries: dict[str, dict]) -> int:
    """Write entries to Redis. Idempotent. Returns count written."""
    if not entries:
        return 0

    now = datetime.now(ET).isoformat()
    pipe = r.pipeline()

    for ticker, entry in entries.items():
        # Preserve added_at if entry already exists
        existing_raw = r.hget("trade_ready:entries", ticker)
        if existing_raw:
            try:
                existing = json.loads(existing_raw)
                entry["added_at"] = existing.get("added_at", now)
            except (json.JSONDecodeError, TypeError):
                entry["added_at"] = now
        else:
            entry["added_at"] = now

        entry["updated_at"] = now

        pipe.hset("trade_ready:entries", ticker, json.dumps(entry))
        pipe.sadd(f"trade_ready:by_date:{entry['earnings_date']}", ticker)

    # Scan log
    scan_log = {
        "last_scan": now,
        "tickers_in_universe": len(entries),
        "sources_checked": list({s for e in entries.values() for s in e.get("sources", [])}),
        "dates": sorted({e["earnings_date"] for e in entries.values()}),
    }
    pipe.set("trade_ready:scan_log", json.dumps(scan_log))

    pipe.execute()
    log.info(f"Redis: wrote {len(entries)} entries")
    return len(entries)


def cleanup_stale(r, today: date) -> int:
    """Remove entries with earnings_date < today."""
    removed = 0
    all_entries = r.hgetall("trade_ready:entries")
    pipe = r.pipeline()

    for ticker, raw in all_entries.items():
        try:
            entry = json.loads(raw)
            ed = date.fromisoformat(entry["earnings_date"])
            if ed < today:
                pipe.hdel("trade_ready:entries", ticker)
                pipe.srem(f"trade_ready:by_date:{entry['earnings_date']}", ticker)
                removed += 1
        except (json.JSONDecodeError, KeyError, ValueError):
            pipe.hdel("trade_ready:entries", ticker)
            removed += 1

    if removed:
        pipe.execute()
    log.info(f"Cleanup: removed {removed} stale entries")
    return removed


def show_trade_ready(r, filter_date: str | None = None):
    """Print current TradeReady list."""
    if filter_date:
        tickers = r.smembers(f"trade_ready:by_date:{filter_date}")
        if not tickers:
            print(f"No entries for {filter_date}")
            return
        entries = {}
        for t in sorted(tickers):
            raw = r.hget("trade_ready:entries", t)
            if raw:
                entries[t] = json.loads(raw)
    else:
        raw_entries = r.hgetall("trade_ready:entries")
        entries = {k: json.loads(v) for k, v in raw_entries.items()}

    if not entries:
        print("TradeReady list is empty")
        return

    # Group by date
    by_date = {}
    for ticker, e in sorted(entries.items()):
        d = e.get("earnings_date", "unknown")
        by_date.setdefault(d, []).append(e)

    for d in sorted(by_date):
        print(f"\n{'='*60}")
        print(f"  {d}  ({len(by_date[d])} tickers)")
        print(f"{'='*60}")
        for e in sorted(by_date[d], key=lambda x: x["ticker"]):
            tod = e.get("time_of_day", "?")
            conf = e.get("conference_date", "")
            conf_str = f"  call: {conf}" if conf else ""
            srcs = ",".join(e.get("sources", []))
            agree = e.get("date_agreement", "?")
            print(f"  {e['ticker']:<8} {tod:<14} agree:{agree}  src:[{srcs}]{conf_str}")

    # Scan log
    scan_log_raw = r.get("trade_ready:scan_log")
    if scan_log_raw:
        sl = json.loads(scan_log_raw)
        print(f"\nLast scan: {sl.get('last_scan', '?')}")


# ── Print (dry run) ──

def print_entries(entries: dict[str, dict]):
    """Print entries without writing to Redis."""
    if not entries:
        print("No matching tickers found")
        return
    by_date = {}
    for e in entries.values():
        d = e.get("earnings_date", "unknown")
        by_date.setdefault(d, []).append(e)

    for d in sorted(by_date):
        print(f"\n--- {d} ({len(by_date[d])} tickers) ---")
        for e in sorted(by_date[d], key=lambda x: x["ticker"]):
            tod = e.get("time_of_day", "?")
            conf = e.get("conference_date", "")
            conf_str = f"  call:{conf}" if conf else ""
            srcs = ",".join(e.get("sources", []))
            agree = e.get("date_agreement", "?")
            print(f"  {e['ticker']:<8} {tod:<14} agree:{agree} [{srcs}]{conf_str}")


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Trade-Ready Earnings Scanner")
    parser.add_argument("--list", action="store_true", help="Dry run: print matches, don't write")
    parser.add_argument("--show", action="store_true", help="Show current TradeReady list from Redis")
    parser.add_argument("--cleanup", action="store_true", help="Purge stale entries only")
    parser.add_argument("--date", type=str, help="Check specific date (YYYY-MM-DD or 'today')")
    parser.add_argument("--source", choices=["av", "ecall", "yahoo"], help="Use single source only")
    args = parser.parse_args()

    load_env()

    # Show mode — just read Redis and display
    if args.show:
        r = get_redis()
        filter_date = None
        if args.date:
            filter_date = date.today().isoformat() if args.date == "today" else args.date
        show_trade_ready(r, filter_date)
        return

    # Cleanup mode
    if args.cleanup:
        r = get_redis()
        cleanup_stale(r, date.today())
        return

    # Compute scan dates
    cal = get_market_calendar()
    today = date.today()

    if args.date:
        if args.date == "today":
            target_dates = [today]
        else:
            target_dates = [date.fromisoformat(args.date)]
    else:
        target_dates = scan_dates(cal, today)

    log.info(f"Scanning dates: {[d.isoformat() for d in target_dates]}")

    # Load universe
    r = get_redis() if not args.list else None
    universe = load_universe(r)
    log.info(f"Universe: {len(universe)} tickers")

    # Fetch sources
    av_results = {}
    ecall_results = {}
    target_set = set(target_dates)

    if args.source != "ecall" and args.source != "yahoo":
        api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        if api_key:
            av_results = fetch_alphavantage(api_key, target_set)
        else:
            log.warning("ALPHAVANTAGE_API_KEY not set, skipping AV")

    if args.source != "av" and args.source != "yahoo":
        ecall_results = fetch_earningscall(target_dates)

    # Merge
    merged, conflicts = merge_sources(av_results, ecall_results, universe)

    # Yahoo tie-break (only for conflicts)
    yahoo_results = {}
    if conflicts and args.source != "av" and args.source != "ecall":
        log.info(f"Date conflicts for {len(conflicts)} tickers, calling Yahoo")
        yahoo_results = fetch_yahoo(conflicts)

    resolve_conflicts(merged, conflicts, yahoo_results)

    log.info(f"Final: {len(merged)} tickers in universe on target dates")

    # Output
    if args.list or r is None:
        print_entries(merged)
    else:
        write_to_redis(r, merged)


if __name__ == "__main__":
    main()
