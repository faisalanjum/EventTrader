#!/usr/bin/env python3
"""Compare LSE and Massive daily bars without touching production state.

Secrets are read from process memory or a hidden prompt. Cache files contain
response rows only, never request headers or API keys.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import gzip
import json
import math
import os
import re
import statistics
import threading
import time
from array import array
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote

import exchange_calendars as xcals
import pandas as pd
import requests

from compare_core import (
    Bar,
    bars_by_date,
    daily_returns,
    normalize_lse_bar,
    normalize_massive_bar,
)


LSE_BASE = "https://api.londonstrategicedge.com/vault"
MASSIVE_BASE = "https://api.polygon.io"
USER_AGENT = "EventMarketDB-isolated-replacement-audit/1.0"


class FetchError(RuntimeError):
    pass


class RateGate:
    """Keep request starts a fixed distance apart across worker threads."""

    def __init__(self, seconds_between_starts: float):
        self.seconds = seconds_between_starts
        self.lock = threading.Lock()
        self.next_start = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_start - now)
            self.next_start = max(now, self.next_start) + self.seconds
        if delay:
            time.sleep(delay)


def safe_name(symbol: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", symbol)


def redact_error_text(text: str, secrets: Iterable[str]) -> str:
    """Remove credentials before an exception is printed or saved."""
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return re.sub(
        r"(?i)\b(api[_-]?key|token|access[_-]?token)=([^&\s]+)",
        r"\1=[REDACTED]",
        redacted,
    )


def read_json_gzip(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_gzip(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(value, handle, separators=(",", ":"))
    os.replace(temporary, path)


def get_json_with_retries(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, Any],
    headers: dict[str, str],
    gate: RateGate | None = None,
    attempts: int = 6,
) -> Any:
    last_problem = ""
    for attempt in range(attempts):
        if gate is not None:
            gate.wait()
        try:
            response = session.get(
                url,
                params=params,
                headers=headers,
                timeout=(15, 90),
            )
        except requests.RequestException as exc:
            last_problem = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 15))
                continue
            break

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as exc:
                raise FetchError("HTTP 200 response was not valid JSON") from exc

        body = response.text[:300].replace("\n", " ")
        last_problem = f"HTTP {response.status_code}: {body}"
        if response.status_code == 429 or response.status_code >= 500:
            retry_after = response.headers.get("Retry-After")
            try:
                wait_seconds = float(retry_after) if retry_after else 2 ** attempt
            except ValueError:
                wait_seconds = 2 ** attempt
            if attempt + 1 < attempts:
                time.sleep(min(wait_seconds, 30))
                continue
        break

    raise FetchError(last_problem or "request failed")


def fetch_lse_daily(
    symbol: str,
    start: str,
    end_inclusive: str,
    key: str,
    cache_dir: Path,
    gate: RateGate,
) -> list[dict[str, Any]]:
    cache = cache_dir / "lse" / (
        f"{safe_name(symbol)}_{start}_{end_inclusive}_1d.json.gz"
    )
    if cache.exists():
        return read_json_gzip(cache)

    end_exclusive = (date.fromisoformat(end_inclusive) + timedelta(days=1)).isoformat()
    with requests.Session() as session:
        value = get_json_with_retries(
            session,
            f"{LSE_BASE}/candles",
            params={
                "symbol": symbol,
                "dataset": "stocks",
                "timeframe": "1d",
                "start": start,
                "end": end_exclusive,
                "order": "asc",
                "limit": 5000,
            },
            headers={
                "x-api-key": key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            gate=gate,
        )
    if not isinstance(value, list):
        raise FetchError(f"LSE returned {type(value).__name__}, expected list")
    write_json_gzip(cache, value)
    return value


def fetch_massive_daily(
    symbol: str,
    start: str,
    end_inclusive: str,
    key: str,
    cache_dir: Path,
) -> list[dict[str, Any]]:
    cache = cache_dir / "massive" / (
        f"{safe_name(symbol)}_{start}_{end_inclusive}_1d.json.gz"
    )
    if cache.exists():
        return read_json_gzip(cache)

    with requests.Session() as session:
        value = get_json_with_retries(
            session,
            (
                f"{MASSIVE_BASE}/v2/aggs/ticker/{quote(symbol, safe='')}"
                f"/range/1/day/{start}/{end_inclusive}"
            ),
            params={
                "adjusted": "true",
                "sort": "asc",
                "limit": 5000,
            },
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
    if not isinstance(value, dict):
        raise FetchError(f"Massive returned {type(value).__name__}, expected object")
    if value.get("status") not in ("OK", "DELAYED"):
        raise FetchError(
            f"Massive status={value.get('status')!r}: "
            f"{str(value.get('error') or value.get('message') or '')[:250]}"
        )
    rows = value.get("results") or []
    if not isinstance(rows, list):
        raise FetchError("Massive results was not a list")
    write_json_gzip(cache, rows)
    return rows


def session_dates(start: str, end_inclusive: str) -> list[str]:
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range(
        pd.Timestamp(start), pd.Timestamp(end_inclusive)
    )
    return [session.date().isoformat() for session in sessions]


def even_sample(values: list[str], count: int) -> list[str]:
    if count >= len(values):
        return values
    if count <= 0:
        return []
    if count == 1:
        return [values[len(values) // 2]]
    indexes = {
        round(position * (len(values) - 1) / (count - 1))
        for position in range(count)
    }
    return [values[index] for index in sorted(indexes)]


def load_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        values = [part.strip().upper() for part in args.symbols.split(",")]
    else:
        values = [
            line.strip().upper()
            for line in args.symbols_file.read_text().splitlines()
            if line.strip()
        ]
    values = sorted(set(values))
    if args.sample_count is not None:
        values = even_sample(values, args.sample_count)
    return values


@dataclass
class DifferenceAccumulator:
    price_field: bool
    compared: int = 0
    exact: int = 0
    absolute_sum: float = 0.0
    within_1bp: int = 0
    within_10bp: int = 0
    within_50bp: int = 0

    def __post_init__(self) -> None:
        self.absolute = array("d")
        self.absolute_bp = array("d")
        self.within_1_cent = 0
        self.within_5_cents = 0
        self.within_10_cents = 0

    def add(self, reference: float, candidate: float) -> None:
        difference = abs(candidate - reference)
        self.compared += 1
        self.exact += candidate == reference
        self.absolute_sum += difference
        self.absolute.append(difference)
        if reference != 0:
            bp = difference / abs(reference) * 10_000
            self.absolute_bp.append(bp)
            self.within_1bp += bp <= 1
            self.within_10bp += bp <= 10
            self.within_50bp += bp <= 50
        if self.price_field:
            self.within_1_cent += difference <= 0.0100000001
            self.within_5_cents += difference <= 0.0500000001
            self.within_10_cents += difference <= 0.1000000001

    @staticmethod
    def percentile(values: array, fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        return ordered[math.ceil((len(ordered) - 1) * fraction)]

    def result(self) -> dict[str, Any]:
        output: dict[str, Any] = {
            "compared": self.compared,
            "exact": self.exact,
            "mean_absolute": (
                self.absolute_sum / self.compared if self.compared else None
            ),
            "median_absolute": (
                statistics.median(self.absolute) if self.absolute else None
            ),
            "p95_absolute": self.percentile(self.absolute, 0.95),
            "max_absolute": max(self.absolute) if self.absolute else None,
            "mean_absolute_bp": (
                statistics.fmean(self.absolute_bp)
                if self.absolute_bp
                else None
            ),
            "p95_absolute_bp": self.percentile(self.absolute_bp, 0.95),
            "max_absolute_bp": (
                max(self.absolute_bp) if self.absolute_bp else None
            ),
            "within_1bp": self.within_1bp,
            "within_10bp": self.within_10bp,
            "within_50bp": self.within_50bp,
        }
        if self.price_field:
            output.update(
                {
                    "within_1_cent": self.within_1_cent,
                    "within_5_cents": self.within_5_cents,
                    "within_10_cents": self.within_10_cents,
                }
            )
        return output


@dataclass
class ReturnAccumulator:
    compared: int = 0
    same_rounded_2dp: int = 0
    within_1bp: int = 0
    within_5bp: int = 0

    def __post_init__(self) -> None:
        self.absolute_percentage_points = array("d")

    def add(self, reference: float, candidate: float) -> None:
        difference = abs(candidate - reference)
        self.compared += 1
        self.same_rounded_2dp += reference == candidate
        self.within_1bp += difference <= 0.01
        self.within_5bp += difference <= 0.05
        self.absolute_percentage_points.append(difference)

    def result(self) -> dict[str, Any]:
        values = self.absolute_percentage_points
        return {
            "compared": self.compared,
            "same_rounded_2dp": self.same_rounded_2dp,
            "within_1bp": self.within_1bp,
            "within_5bp": self.within_5bp,
            "mean_absolute_percentage_points": (
                statistics.fmean(values) if values else None
            ),
            "p95_absolute_percentage_points": (
                DifferenceAccumulator.percentile(values, 0.95)
            ),
            "max_absolute_percentage_points": max(values) if values else None,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols-file", type=Path)
    parser.add_argument("--symbols")
    parser.add_argument("--sample-count", type=int)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv-gz", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    if not args.symbols and not args.symbols_file:
        parser.error("pass --symbols or --symbols-file")
    if args.workers < 1 or args.workers > 2:
        parser.error("--workers must be 1 or 2 because the LSE plan allows 2")

    symbols = load_symbols(args)
    if not symbols:
        raise SystemExit("No symbols selected")

    massive_key = os.environ.get("POLYGON_API_KEY")
    if not massive_key:
        raise SystemExit("POLYGON_API_KEY is not set")
    lse_key = os.environ.get("LSE_API_KEY") or getpass.getpass("LSE API key: ")
    if not lse_key:
        raise SystemExit("No LSE API key supplied")

    canonical_dates = session_dates(args.start, args.end)
    canonical_set = set(canonical_dates)
    gate = RateGate(seconds_between_starts=0.35)

    def fetch_symbol(symbol: str) -> tuple[str, list[Bar], list[Bar]]:
        lse_rows = fetch_lse_daily(
            symbol, args.start, args.end, lse_key, args.cache_dir, gate
        )
        massive_rows = fetch_massive_daily(
            symbol, args.start, args.end, massive_key, args.cache_dir
        )
        return (
            symbol,
            [normalize_lse_bar(row) for row in lse_rows],
            [normalize_massive_bar(symbol, row) for row in massive_rows],
        )

    successes: dict[str, tuple[list[Bar], list[Bar]]] = {}
    errors: dict[str, str] = {}
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}
        for completed, future in enumerate(as_completed(futures), start=1):
            symbol = futures[future]
            try:
                _, lse_bars, massive_bars = future.result()
                successes[symbol] = (lse_bars, massive_bars)
            except Exception as exc:
                raw_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                errors[symbol] = redact_error_text(
                    raw_error, (massive_key, lse_key)
                )
            if completed == 1 or completed % 20 == 0 or completed == len(symbols):
                print(
                    f"daily API fetch: {completed}/{len(symbols)} "
                    f"(errors={len(errors)})",
                    flush=True,
                )

    field_accumulators = {
        field: DifferenceAccumulator(price_field=True)
        for field in ("open", "high", "low", "close")
    }
    volume_accumulator = DifferenceAccumulator(price_field=False)
    return_accumulator = ReturnAccumulator()
    symbol_summaries: dict[str, Any] = {}
    raw_lse_non_session_dates = 0
    massive_non_session_dates = 0
    massive_only_dates = 0
    lse_only_session_dates = 0
    overlap_dates = 0

    args.output_csv_gz.parent.mkdir(parents=True, exist_ok=True)
    csv_fields = [
        "symbol",
        "date",
        "massive_open",
        "lse_open",
        "massive_high",
        "lse_high",
        "massive_low",
        "lse_low",
        "massive_close",
        "lse_close",
        "massive_volume",
        "lse_volume",
        "massive_return",
        "lse_return",
    ]
    with gzip.open(args.output_csv_gz, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields)
        writer.writeheader()
        for symbol in sorted(successes):
            raw_lse_bars, raw_massive_bars = successes[symbol]
            raw_lse = bars_by_date(raw_lse_bars)
            massive = bars_by_date(raw_massive_bars)
            lse = {
                bar_date: bar
                for bar_date, bar in raw_lse.items()
                if bar_date in canonical_set
            }
            lse_non_session = sorted(set(raw_lse) - canonical_set)
            massive_non_session = sorted(set(massive) - canonical_set)
            overlap = sorted(set(lse) & set(massive))
            massive_only = sorted(set(massive) - set(lse))
            lse_only = sorted(set(lse) - set(massive))
            m_returns = daily_returns(massive, session_dates=canonical_dates)
            l_returns = daily_returns(lse, session_dates=canonical_dates)

            raw_lse_non_session_dates += len(lse_non_session)
            massive_non_session_dates += len(massive_non_session)
            massive_only_dates += len(massive_only)
            lse_only_session_dates += len(lse_only)
            overlap_dates += len(overlap)

            return_overlap = set(m_returns) & set(l_returns)
            for bar_date in overlap:
                massive_bar = massive[bar_date]
                lse_bar = lse[bar_date]
                for field, accumulator in field_accumulators.items():
                    accumulator.add(
                        getattr(massive_bar, field), getattr(lse_bar, field)
                    )
                volume_accumulator.add(massive_bar.volume, lse_bar.volume)
                if bar_date in return_overlap:
                    return_accumulator.add(
                        m_returns[bar_date], l_returns[bar_date]
                    )
                writer.writerow(
                    {
                        "symbol": symbol,
                        "date": bar_date,
                        "massive_open": massive_bar.open,
                        "lse_open": lse_bar.open,
                        "massive_high": massive_bar.high,
                        "lse_high": lse_bar.high,
                        "massive_low": massive_bar.low,
                        "lse_low": lse_bar.low,
                        "massive_close": massive_bar.close,
                        "lse_close": lse_bar.close,
                        "massive_volume": massive_bar.volume,
                        "lse_volume": lse_bar.volume,
                        "massive_return": m_returns.get(bar_date),
                        "lse_return": l_returns.get(bar_date),
                    }
                )

            symbol_summaries[symbol] = {
                "lse_raw_dates": len(raw_lse),
                "lse_session_dates": len(lse),
                "massive_dates": len(massive),
                "overlap_dates": len(overlap),
                "massive_only_dates": len(massive_only),
                "lse_only_session_dates": len(lse_only),
                "lse_non_session_dates": len(lse_non_session),
                "lse_non_session_date_examples": lse_non_session[:10],
                "massive_non_session_dates": len(massive_non_session),
                "first_overlap_date": overlap[0] if overlap else None,
                "last_overlap_date": overlap[-1] if overlap else None,
                "return_overlap_dates": len(return_overlap),
            }

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "safety": (
            "Read-only HTTPS GET requests only. API keys were not printed or "
            "saved. Production code and databases were not changed."
        ),
        "method": {
            "start_inclusive": args.start,
            "end_inclusive": args.end,
            "massive": "1/day adjusted=true, asc, limit=5000",
            "lse": (
                "stocks 1d, asc, limit=5000; end advanced one day because live "
                "server treats end date as exclusive"
            ),
            "calendar": "XNYS; non-session LSE rows excluded from accuracy metrics",
            "return_formula": "round((current_close-prior_close)/prior_close*100, 2)",
            "missing_session_rule": (
                "A return is omitted unless both consecutive XNYS sessions have bars"
            ),
        },
        "requested_symbols": len(symbols),
        "successful_symbols": len(successes),
        "failed_symbols": len(errors),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "coverage": {
            "canonical_sessions": len(canonical_dates),
            "overlap_symbol_dates": overlap_dates,
            "massive_only_symbol_dates": massive_only_dates,
            "lse_only_session_symbol_dates": lse_only_session_dates,
            "lse_non_session_symbol_dates": raw_lse_non_session_dates,
            "massive_non_session_symbol_dates": massive_non_session_dates,
        },
        "ohlc": {
            field: accumulator.result()
            for field, accumulator in field_accumulators.items()
        },
        "volume": volume_accumulator.result(),
        "daily_returns": return_accumulator.result(),
        "errors": dict(sorted(errors.items())),
        "symbol_summaries": symbol_summaries,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"saved: {args.output_json}")
    print(f"saved: {args.output_csv_gz}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
