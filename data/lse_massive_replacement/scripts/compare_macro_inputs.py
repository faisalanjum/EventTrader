#!/usr/bin/env python3
"""Run production macro formulas on Massive and LSE bars side by side."""

from __future__ import annotations

import argparse
import getpass
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REPOSITORY = Path("/home/faisal/EventMarketDB")
sys.path.insert(0, str(REPOSITORY))

from scripts.earnings.builders.macro_snapshot import (  # noqa: E402
    INDICATOR_TICKERS,
    _compute_indicator_daily,
    _compute_spy_now,
)

from macro_comparison_core import (  # noqa: E402
    normalize_lse_daily,
    normalize_lse_minutes,
    normalize_massive_daily,
    normalize_massive_minutes,
)


LSE_BASE = "https://api.londonstrategicedge.com/vault"
MASSIVE_BASE = "https://api.massive.com"
USER_AGENT = "EventMarketDB-isolated-replacement-audit/1.0"
SUPPORTED_LSE_INDICATORS = ("TLT", "HYG", "IWM", "GLD")


def read_cache(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_cache(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(value, handle, separators=(",", ":"))
    os.replace(temporary, path)


def get_json(
    url: str,
    headers: dict[str, str],
    cache: Path,
) -> Any:
    if cache.exists():
        return read_cache(cache)
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    value = json.loads(raw.decode("utf-8"))
    write_cache(cache, value)
    return value


def lse_candles(
    key: str,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    cache_dir: Path,
) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "dataset": "etf",
            "timeframe": timeframe,
            "start": start,
            "end": end,
            "order": "asc",
            "limit": 5000,
        }
    )
    value = get_json(
        f"{LSE_BASE}/candles?{params}",
        {
            "x-api-key": key,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
        cache_dir / "lse" / f"{symbol}_{timeframe}_{start}_{end}.json.gz",
    )
    if not isinstance(value, list):
        raise RuntimeError(f"LSE returned {type(value).__name__}")
    return value


def massive_candles(
    key: str,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    limit: int,
    cache_dir: Path,
    last_call: list[float],
    interval: float,
) -> list[dict[str, Any]]:
    cache = (
        cache_dir
        / "massive"
        / f"{symbol}_{timeframe}_{start}_{end}.json.gz"
    )
    if cache.exists():
        value = read_cache(cache)
    else:
        elapsed = time.monotonic() - last_call[0]
        if last_call[0] and elapsed < interval:
            time.sleep(interval - elapsed)
        params = urllib.parse.urlencode(
            {"adjusted": "true", "sort": "asc", "limit": limit}
        )
        url = (
            f"{MASSIVE_BASE}/v2/aggs/ticker/{symbol}/range/1/"
            f"{timeframe}/{start}/{end}?{params}"
        )
        value = get_json(
            url,
            {
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            cache,
        )
        last_call[0] = time.monotonic()
    if not isinstance(value, dict) or value.get("status") not in ("OK", "DELAYED"):
        raise RuntimeError(f"Unexpected Massive response for {symbol}/{timeframe}")
    return value.get("results", [])


def numeric_differences(
    reference: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    result = {}
    for field in sorted(reference.keys() | candidate.keys()):
        left = reference.get(field)
        right = candidate.get(field)
        if (
            isinstance(left, (int, float))
            and not isinstance(left, bool)
            and isinstance(right, (int, float))
            and not isinstance(right, bool)
        ):
            result[field] = {
                "massive": left,
                "lse": right,
                "difference": round(float(right) - float(left), 10),
            }
        elif left != right:
            result[field] = {"massive": left, "lse": right}
    return result


def history_quality(rows: list[dict[str, Any]], pit_date: str) -> dict[str, Any]:
    dates = [row["date"] for row in rows]
    return {
        "rows": len(rows),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "covers_pit_year_start": bool(
            dates and dates[0] <= f"{pit_date[:4]}-01-02"
        ),
        "has_200_settled_rows": len(rows) >= 200,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pit", default="2026-07-17T16:30:00-04:00")
    parser.add_argument("--session", default="post_market")
    parser.add_argument("--lse-daily-start", default="2026-04-27")
    parser.add_argument("--massive-daily-start", default="2025-01-01")
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--massive-interval", type=float, default=13.0)
    args = parser.parse_args()

    lse_key = os.environ.get("LSE_API_KEY") or getpass.getpass("LSE API key: ")
    massive_key = os.environ.get("POLYGON_API_KEY")
    if not lse_key or not massive_key:
        raise SystemExit("LSE and Massive keys are required")

    pit_dt = datetime.fromisoformat(args.pit.replace("Z", "+00:00"))
    pit_date = pit_dt.date().isoformat()
    next_date = (pit_dt.date() + timedelta(days=1)).isoformat()
    last_massive_call = [0.0]

    lse_spy_minute_raw = lse_candles(
        lse_key, "SPY", "1m", pit_date, next_date, args.cache_dir
    )
    lse_spy_daily_raw = lse_candles(
        lse_key,
        "SPY",
        "1d",
        args.lse_daily_start,
        next_date,
        args.cache_dir,
    )
    massive_spy_minute_raw = massive_candles(
        massive_key,
        "SPY",
        "minute",
        pit_date,
        pit_date,
        1000,
        args.cache_dir,
        last_massive_call,
        args.massive_interval,
    )
    massive_spy_daily_raw = massive_candles(
        massive_key,
        "SPY",
        "day",
        args.massive_daily_start,
        pit_date,
        5000,
        args.cache_dir,
        last_massive_call,
        args.massive_interval,
    )

    lse_spy_minute = normalize_lse_minutes(lse_spy_minute_raw, pit_date)
    lse_spy_daily = normalize_lse_daily(lse_spy_daily_raw)
    massive_spy_minute = normalize_massive_minutes(
        massive_spy_minute_raw
    )
    massive_spy_daily = normalize_massive_daily(massive_spy_daily_raw)

    massive_spy = _compute_spy_now(
        massive_spy_minute,
        massive_spy_daily,
        args.pit,
        args.session,
    )
    lse_spy = _compute_spy_now(
        lse_spy_minute,
        lse_spy_daily,
        args.pit,
        args.session,
    )

    indicators: dict[str, Any] = {}
    label_by_ticker = {
        ticker: label for label, ticker in INDICATOR_TICKERS.items()
    }
    for symbol in SUPPORTED_LSE_INDICATORS:
        lse_raw = lse_candles(
            lse_key,
            symbol,
            "1d",
            args.lse_daily_start,
            next_date,
            args.cache_dir,
        )
        massive_raw = massive_candles(
            massive_key,
            symbol,
            "day",
            args.massive_daily_start,
            pit_date,
            5000,
            args.cache_dir,
            last_massive_call,
            args.massive_interval,
        )
        lse_rows = normalize_lse_daily(lse_raw)
        massive_rows = normalize_massive_daily(massive_raw)
        massive_metric = _compute_indicator_daily(
            massive_rows, pit_date, args.session
        )
        lse_metric = _compute_indicator_daily(
            lse_rows, pit_date, args.session
        )
        indicators[symbol] = {
            "label": label_by_ticker[symbol],
            "massive_history": history_quality(massive_rows, pit_date),
            "lse_history": history_quality(lse_rows, pit_date),
            "massive_metric": massive_metric,
            "lse_metric": lse_metric,
            "differences": numeric_differences(
                massive_metric or {}, lse_metric or {}
            ),
        }
        print(f"macro indicator complete: {symbol}", flush=True)

    all_indicator_symbols = set(INDICATOR_TICKERS.values())
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "pit": args.pit,
        "session": args.session,
        "spy": {
            "raw_row_counts": {
                "massive_minute": len(massive_spy_minute_raw),
                "lse_minute_utc_day": len(lse_spy_minute_raw),
                "lse_minute_after_et_day_filter": len(lse_spy_minute),
                "massive_daily": len(massive_spy_daily),
                "lse_daily_after_exchange_calendar_filter": len(lse_spy_daily),
            },
            "massive_history": history_quality(massive_spy_daily, pit_date),
            "lse_history": history_quality(lse_spy_daily, pit_date),
            "massive_metric": massive_spy,
            "lse_metric": lse_spy,
            "differences": numeric_differences(massive_spy, lse_spy),
        },
        "supported_lse_indicators": indicators,
        "missing_lse_indicator_symbols": sorted(
            all_indicator_symbols - set(SUPPORTED_LSE_INDICATORS)
        ),
        "safety": (
            "GET requests only; API keys were not printed or saved. "
            "Production macro functions were imported read-only. No database "
            "or production code was changed."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
