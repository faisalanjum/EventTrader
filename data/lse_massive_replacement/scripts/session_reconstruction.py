"""Pure helpers for rebuilding a candle from timestamped LSE rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


def row_timestamp(row: Mapping[str, Any]) -> datetime:
    raw = str(row["ts"]).strip()
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def rows_in_window(
    rows: Iterable[Mapping[str, Any]],
    start: datetime,
    end: datetime,
) -> list[Mapping[str, Any]]:
    """Return rows in the half-open UTC window ``start <= ts < end``."""

    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    selected = [
        row
        for row in rows
        if start_utc <= row_timestamp(row) < end_utc
    ]
    return sorted(selected, key=row_timestamp)


def aggregate_rows(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, float | int | str] | None:
    ordered = sorted(rows, key=row_timestamp)
    if not ordered:
        return None
    return {
        "row_count": len(ordered),
        "first_ts": str(ordered[0]["ts"]),
        "last_ts": str(ordered[-1]["ts"]),
        "open": float(ordered[0]["open"]),
        "high": max(float(row["high"]) for row in ordered),
        "low": min(float(row["low"]) for row in ordered),
        "close": float(ordered[-1]["close"]),
        "volume": sum(float(row.get("volume", 0)) for row in ordered),
    }
