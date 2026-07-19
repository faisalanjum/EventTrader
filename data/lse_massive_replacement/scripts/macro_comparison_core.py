"""Pure normalization helpers for the isolated macro-input comparison."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd


EASTERN = ZoneInfo("America/New_York")


def lse_timestamp(row: Mapping[str, Any]) -> datetime:
    raw = str(row.get("ts", row.get("timestamp", ""))).strip()
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def lse_minutes_for_et_day(
    rows: Iterable[Mapping[str, Any]],
    day: str,
) -> list[Mapping[str, Any]]:
    """Keep the U.S. extended-hours window for one Eastern trading date."""

    target_date = date.fromisoformat(day)
    selected: list[Mapping[str, Any]] = []
    for row in rows:
        eastern = lse_timestamp(row).astimezone(EASTERN)
        if (
            eastern.date() == target_date
            and time(4, 0) <= eastern.time().replace(tzinfo=None) < time(20, 0)
        ):
            selected.append(row)
    return sorted(selected, key=lse_timestamp)


def normalize_lse_minutes(
    rows: Iterable[Mapping[str, Any]],
    day: str,
) -> list[dict[str, Any]]:
    result = []
    for row in lse_minutes_for_et_day(rows, day):
        timestamp = lse_timestamp(row)
        result.append(
            {
                "ts_ms": int(timestamp.timestamp() * 1000),
                "ts_iso": timestamp.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            }
        )
    return result


def normalize_massive_minutes(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "ts_ms": int(row["t"]),
            "ts_iso": datetime.fromtimestamp(
                int(row["t"]) / 1000, tz=timezone.utc
            ).isoformat(),
            "open": float(row["o"]),
            "high": float(row["h"]),
            "low": float(row["l"]),
            "close": float(row["c"]),
            "volume": float(row.get("v", 0)),
        }
        for row in rows
    ]


def normalize_lse_daily(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    calendar = xcals.get_calendar("XNYS")
    result = []
    for row in rows:
        day = str(row.get("ts", row.get("timestamp", "")))[:10]
        if not day or not calendar.is_session(pd.Timestamp(day)):
            continue
        result.append(
            {
                "date": day,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            }
        )
    return sorted(result, key=lambda row: row["date"])


def normalize_massive_daily(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        timestamp = datetime.fromtimestamp(
            int(row["t"]) / 1000, tz=timezone.utc
        ).astimezone(EASTERN)
        result.append(
            {
                "date": timestamp.date().isoformat(),
                "open": float(row["o"]),
                "high": float(row["h"]),
                "low": float(row["l"]),
                "close": float(row["c"]),
                "volume": float(row.get("v", 0)),
            }
        )
    return sorted(result, key=lambda row: row["date"])
