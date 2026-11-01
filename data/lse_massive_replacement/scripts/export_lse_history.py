#!/usr/bin/env python3
"""Use one LSE bulk job to save an isolated deep-history Parquet file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence


AUDIT_ROOT = Path(__file__).resolve().parents[1]
LSE_SOURCE = AUDIT_ROOT / "raw" / "lse-data-main"
sys.path.insert(0, str(LSE_SOURCE))

from lse import LSE  # noqa: E402

from fetch_lse_proxy_pilot import read_api_key, safe_name  # noqa: E402


def resolve_period(
    day_value: str | None,
    start_value: str | None,
    end_value: str | None,
) -> tuple[str, str]:
    """Resolve either one day or one explicit half-open date range."""

    if day_value:
        if start_value or end_value:
            raise ValueError("--date cannot be combined with --start or --end")
        day = date.fromisoformat(day_value)
        return day.isoformat(), (day + timedelta(days=1)).isoformat()
    if not start_value or not end_value:
        raise ValueError("pass --date or both --start and --end")
    start = date.fromisoformat(start_value)
    end = date.fromisoformat(end_value)
    if end <= start:
        raise ValueError("--end must be after --start")
    return start.isoformat(), end.isoformat()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--dataset", default="stocks")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--date")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        start, end = resolve_period(args.date, args.start, args.end)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )

    args.dest.mkdir(parents=True, exist_ok=True)
    destination = args.dest / (
        f"{safe_name(args.dataset)}__{safe_name(args.symbol)}__"
        f"{start}__{end}__{safe_name(args.timeframe)}.parquet"
    )
    cache_status = "cached"
    if not destination.exists():
        client = LSE(api_key=api_key, timeout=120)
        downloaded = Path(
            client.history(
                args.symbol,
                dataset=args.dataset,
                timeframe=args.timeframe,
                start=start,
                end=end,
                dest=str(args.dest),
                dataframe=False,
                poll_seconds=1.5,
                timeout=1800,
            )
        )
        os.replace(downloaded, destination)
        cache_status = "downloaded"

    rows = None
    columns = None
    try:
        import pyarrow.parquet as parquet

        metadata = parquet.read_metadata(destination)
        rows = metadata.num_rows
        columns = metadata.schema.names
    except ImportError:
        try:
            import duckdb

            connection = duckdb.connect()
            rows = connection.execute(
                "SELECT count(*) FROM read_parquet(?)",
                [str(destination)],
            ).fetchone()[0]
            columns = [
                item[0]
                for item in connection.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)",
                    [str(destination)],
                ).fetchall()
            ]
        except ImportError:
            pass

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "One read-only LSE bulk export. The API key was not printed or "
            "saved. Production code and databases were untouched."
        ),
        "request": {
            "dataset": args.dataset,
            "symbol": args.symbol,
            "timeframe": args.timeframe,
            "start": start,
            "end_exclusive": end,
        },
        "artifact": {
            "status": cache_status,
            "file": str(
                destination.resolve().relative_to(AUDIT_ROOT.resolve())
            ),
            "bytes": destination.stat().st_size,
            "rows": rows,
            "columns": columns,
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.manifest)
    print(
        f"saved {rows if rows is not None else 'unknown'} rows: "
        f"{destination}"
    )
    print(f"saved manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
