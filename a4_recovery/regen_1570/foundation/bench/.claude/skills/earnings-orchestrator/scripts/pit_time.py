#!/usr/bin/env python3
"""Shared PIT timestamp utilities for wrapper scripts."""
from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")


def parse_timestamp(value: Any) -> datetime | None:
    """Parse ISO8601/RFC2822 and default naive timestamps to New York time."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()

    try:
        iso = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(iso)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=NY_TZ)
    except ValueError:
        pass

    try:
        dt = parsedate_to_datetime(text)
        if dt is None:
            return None
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=NY_TZ)
    except (TypeError, ValueError):
        return None


def to_new_york_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=NY_TZ)
    return dt.astimezone(NY_TZ).isoformat()
