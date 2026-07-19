#!/usr/bin/env python3
"""Compare stored Massive event returns with LSE one-second candles.

The reference values are read from an earlier read-only Neo4j export. This
script has no network or database behavior.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


REPOSITORY = Path("/home/faisal/EventMarketDB")
sys.path.insert(0, str(REPOSITORY))

from utils.market_session import MarketSessionClassifier  # noqa: E402


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def rounded_return(start: float, end: float) -> float:
    if not math.isfinite(start) or not math.isfinite(end) or start == 0:
        raise ValueError("Prices must be finite and start must be nonzero")
    return round((end - start) / start * 100, 2)


def parquet_bounds(
    connection: duckdb.DuckDBPyConnection,
    parquet: str | list[str],
) -> tuple[datetime, datetime]:
    connection.execute("SET TimeZone='UTC'")
    row = connection.execute(
        "SELECT epoch(min(ts)), epoch(max(ts)) FROM read_parquet(?)",
        [parquet],
    ).fetchone()
    if row is None or row[0] is None or row[1] is None:
        raise ValueError("One-second Parquet file is empty")
    return (
        datetime.fromtimestamp(row[0], tz=timezone.utc),
        datetime.fromtimestamp(row[1], tz=timezone.utc),
    )


def prior_second_close(
    connection: duckdb.DuckDBPyConnection,
    parquet: str | list[str],
    target: datetime,
) -> dict[str, Any] | None:
    connection.execute("SET TimeZone='UTC'")
    cursor = connection.execute(
        """
        SELECT epoch(ts), close
        FROM read_parquet(?)
        WHERE ts <= CAST(? AS TIMESTAMPTZ)
        ORDER BY ts DESC
        LIMIT 1
        """,
        [parquet, target.astimezone(timezone.utc).isoformat()],
    )
    row = cursor.fetchone()
    if row is None:
        return None
    bar_start = datetime.fromtimestamp(row[0], tz=timezone.utc)
    return {"bar_start": bar_start.isoformat(), "close": float(row[1])}


def production_window(
    classifier: MarketSessionClassifier,
    created: datetime,
    period: str,
) -> tuple[datetime, datetime]:
    if period == "hourly":
        start = classifier.get_interval_start_time(created)
        end = classifier.get_interval_end_time(
            created, 60, respect_session_boundary=False
        )
    elif period == "session":
        start = classifier.get_start_time(created)
        end = classifier.get_end_time(created)
    elif period == "daily":
        start, end = classifier.get_1d_impact_times(created)
    else:
        raise ValueError(f"Unsupported period: {period}")
    return start.to_pydatetime(), end.to_pydatetime()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument(
        "--period",
        choices=("hourly", "session", "daily"),
        default="hourly",
    )
    parser.add_argument(
        "--seconds",
        type=Path,
        action="append",
        required=True,
        help="One-second Parquet file; may be repeated for adjacent UTC days.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.events.read_text(encoding="utf-8"))
    events = source.get("cases", {}).get(args.case)
    if events is None:
        raise SystemExit(f"Case not found in event export: {args.case}")

    connection = duckdb.connect()
    market_session = MarketSessionClassifier()
    second_files = [str(path) for path in args.seconds]
    minimum_bar_start, maximum_bar_start = parquet_bounds(
        connection, second_files
    )
    details: list[dict[str, Any]] = []

    for event in events:
        created = parse_timestamp(event["created"])
        start, end = production_window(
            market_session, created, args.period
        )
        stored_schedule = json.loads(event["returns_schedule"])
        scheduled_end = parse_timestamp(stored_schedule[args.period])
        schedule_matches = (
            end.astimezone(timezone.utc) == scheduled_end.astimezone(timezone.utc)
        )

        start_utc = start.astimezone(timezone.utc)
        end_utc = end.astimezone(timezone.utc)
        start_covered = minimum_bar_start <= start_utc <= maximum_bar_start
        end_covered = minimum_bar_start <= end_utc <= maximum_bar_start
        start_price = (
            prior_second_close(connection, second_files, start)
            if start_covered
            else None
        )
        end_price = (
            prior_second_close(connection, second_files, end)
            if end_covered
            else None
        )
        candidate_return = None
        if start_price is not None and end_price is not None:
            candidate_return = rounded_return(
                start_price["close"], end_price["close"]
            )

        reference = (
            float(event[f"{args.period}_stock"])
            if event.get(f"{args.period}_stock") is not None
            else None
        )
        difference = (
            round(candidate_return - reference, 10)
            if candidate_return is not None and reference is not None
            else None
        )
        details.append(
            {
                "event_id": event["event_id"],
                "created": event["created"],
                "market_session": event.get("market_session"),
                "production_start": start.isoformat(),
                "production_end": end.isoformat(),
                "stored_scheduled_end": stored_schedule[args.period],
                "period": args.period,
                "schedule_matches": schedule_matches,
                "start_within_export_bounds": start_covered,
                "end_within_export_bounds": end_covered,
                "lse_start": start_price,
                "lse_end": end_price,
                "massive_stored_return": reference,
                "lse_return": candidate_return,
                "difference_percentage_points": difference,
                "exact_2dp": difference == 0,
            }
        )

    comparable = [
        row for row in details
        if row["difference_percentage_points"] is not None
    ]
    errors = [
        abs(float(row["difference_percentage_points"])) for row in comparable
    ]
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "case": args.case,
        "period": args.period,
        "reference": (
            f"Stored Neo4j {args.period}_stock values originally produced by Massive "
            "one-second adjusted aggregates."
        ),
        "candidate": (
            "LSE one-second candle close from the newest bar whose bar-start "
            "timestamp is at or before each production start/end timestamp."
        ),
        "events": len(events),
        "one_second_files": second_files,
        "export_bounds_utc": {
            "first_bar_start": minimum_bar_start.isoformat(),
            "last_bar_start": maximum_bar_start.isoformat(),
        },
        "summary": {
            "comparable": len(comparable),
            "schedule_matches": sum(row["schedule_matches"] for row in details),
            "exact_2dp": sum(row["exact_2dp"] for row in comparable),
            "within_1bp": sum(error <= 0.01 for error in errors),
            "within_5bp": sum(error <= 0.05 for error in errors),
            "mean_absolute_percentage_points": (
                sum(errors) / len(errors) if errors else None
            ),
            "max_absolute_percentage_points": max(errors) if errors else None,
        },
        "details": details,
        "safety": (
            "No network or database calls. Production source was imported "
            "read-only only for its exact market-window calculation."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
