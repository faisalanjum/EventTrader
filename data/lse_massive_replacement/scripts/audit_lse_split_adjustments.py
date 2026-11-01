#!/usr/bin/env python3
"""Load complete LSE split data and diagnose suspicious close jumps."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import exchange_calendars as xcals
import pandas as pd

from compare_corporate_actions import fetch_reference_rows
from fetch_lse_proxy_pilot import read_api_key
from run_proxy_pilot import read_gzip_rows, regular_close_returns


REFERENCE_ROW_LIMIT = 5000


def large_return_candidates(
    symbol: str,
    returns: pd.Series,
    threshold_pp: float,
) -> list[dict[str, Any]]:
    return [
        {
            "symbol": str(symbol).upper(),
            "date": str(day)[:10],
            "raw_return_pp": round(float(value), 8),
        }
        for day, value in returns.items()
        if abs(float(value)) >= float(threshold_pp)
    ]


def splits_in_period(
    rows: list[dict[str, Any]],
    start: str,
    end: str,
) -> list[dict[str, Any]]:
    return sorted(
        [
            row
            for row in rows
            if start
            <= str(row.get("effective_date", ""))[:10]
            <= end
            and row.get("symbol")
        ],
        key=lambda row: (
            str(row.get("effective_date", "")),
            str(row.get("symbol", "")),
        ),
    )


def fetch_complete_reference_period(
    fetch_range: Callable[[str, str], list[dict[str, Any]]],
    start: str,
    end: str,
    *,
    row_limit: int = REFERENCE_ROW_LIMIT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load every row, splitting capped date ranges until none are truncated."""
    all_rows: list[dict[str, Any]] = []
    completed_ranges: list[dict[str, Any]] = []

    def visit(range_start: date, range_end: date) -> None:
        start_text = range_start.isoformat()
        end_text = range_end.isoformat()
        rows = fetch_range(start_text, end_text)
        if len(rows) < row_limit:
            all_rows.extend(rows)
            completed_ranges.append(
                {
                    "start": start_text,
                    "end": end_text,
                    "rows": len(rows),
                }
            )
            return
        if range_start == range_end:
            raise RuntimeError(
                "LSE returned its row limit for one date; completeness "
                f"cannot be proven for {start_text}"
            )
        midpoint = range_start + (range_end - range_start) // 2
        visit(range_start, midpoint)
        visit(midpoint + timedelta(days=1), range_end)

    visit(date.fromisoformat(start), date.fromisoformat(end))
    return all_rows, completed_ranges


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        action="append",
        type=Path,
        default=[],
        help=(
            "Optional hourly manifest used only to diagnose large raw moves. "
            "Split loading always covers every LSE symbol."
        ),
    )
    parser.add_argument("--start", required=True)
    parser.add_argument(
        "--end",
        default=date.today().isoformat(),
        help="Inclusive end date; defaults to today.",
    )
    parser.add_argument("--threshold-pp", type=float, default=35.0)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=root / "raw" / "recent_split_checks",
    )
    parser.add_argument("--private-key-source", type=Path)
    parser.add_argument("--request-pause-seconds", type=float, default=0.34)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    files_by_symbol: dict[str, set[Path]] = {}
    for manifest_path in args.manifest:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["chunks"]:
            symbol = str(item["symbol"]).upper()
            files_by_symbol.setdefault(symbol, set()).add(
                root / item["cache_file"]
            )

    calendar = xcals.get_calendar("XNYS")
    calendar_sessions = calendar.sessions_in_range(
        pd.Timestamp(args.start),
        pd.Timestamp(args.end),
    )
    sessions = [
        session.date().isoformat() for session in calendar_sessions
    ]
    market_closes = {
        session.date().isoformat(): calendar.session_close(session).isoformat()
        for session in calendar_sessions
    }

    candidates: list[dict[str, Any]] = []
    for symbol, paths in sorted(files_by_symbol.items()):
        rows: list[dict[str, Any]] = []
        for path in sorted(paths):
            if path.exists():
                rows.extend(read_gzip_rows(path))
        returns = regular_close_returns(
            rows,
            sessions,
            market_closes,
            round_digits=None,
        )
        candidates.extend(
            large_return_candidates(
                symbol,
                returns,
                args.threshold_pp,
            )
        )

    large_move_symbols = sorted(
        {str(row["symbol"]) for row in candidates}
    )
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    fetched_rows, completed_ranges = fetch_complete_reference_period(
        lambda range_start, range_end: fetch_reference_rows(
            api_key,
            "stock_splits",
            None,
            args.cache_dir,
            start=range_start,
            end=range_end,
            minimum_interval=args.request_pause_seconds,
        ),
        args.start,
        args.end,
    )
    period_rows = splits_in_period(fetched_rows, args.start, args.end)
    split_symbols = sorted(
        {
            str(row.get("symbol", "")).upper()
            for row in period_rows
            if row.get("symbol")
        }
    )
    matched = {
        (
            str(row.get("symbol", "")).upper(),
            str(row.get("effective_date", ""))[:10],
        )
        for row in period_rows
    }
    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Local isolated caches and read-only LSE reference GETs only. "
            "The API key was not printed or saved."
        ),
        "period": {"start": args.start, "end": args.end},
        "split_table": {
            "scope": "all symbols in the requested period",
            "symbol_filter": None,
            "row_limit": REFERENCE_ROW_LIMIT,
            "complete": True,
            "completed_date_ranges": completed_ranges,
            "rule": (
                "A capped date range is split into smaller date ranges "
                "automatically until every response is below the row limit."
            ),
        },
        "threshold_pp": args.threshold_pp,
        "manifests": [str(path) for path in args.manifest],
        "candidates": sorted(
            candidates,
            key=lambda row: (row["symbol"], row["date"]),
        ),
        "large_move_symbols": large_move_symbols,
        "split_symbols": split_symbols,
        "rows": period_rows,
        "matched_candidates": [
            row
            for row in sorted(
                candidates,
                key=lambda item: (item["symbol"], item["date"]),
            )
            if (row["symbol"], row["date"]) in matched
        ],
        "summary": {
            "hourly_symbols_scanned": len(files_by_symbol),
            "large_return_candidates": len(candidates),
            "large_move_symbols": len(large_move_symbols),
            "split_symbols_in_complete_table": len(split_symbols),
            "period_split_rows": len(period_rows),
            "complete_date_ranges_fetched": len(completed_ranges),
            "matched_large_return_candidates": sum(
                (row["symbol"], row["date"]) in matched
                for row in candidates
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(json.dumps(report["summary"], sort_keys=True))
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
