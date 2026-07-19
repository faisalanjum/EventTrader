#!/usr/bin/env python3
"""Use one LSE bulk-export job to download an isolated history sample."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


AUDIT_ROOT = Path(__file__).resolve().parents[1]
LSE_SOURCE = AUDIT_ROOT / "raw" / "lse-data-main"
sys.path.insert(0, str(LSE_SOURCE))

from lse import LSE  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--timeframe", default="tick")
    parser.add_argument("--dest", type=Path, required=True)
    args = parser.parse_args()

    day = date.fromisoformat(args.date)
    end = day + timedelta(days=1)
    key = os.environ.get("LSE_API_KEY") or getpass.getpass("LSE API key: ")
    if not key:
        raise SystemExit("No LSE API key supplied")

    args.dest.mkdir(parents=True, exist_ok=True)
    client = LSE(api_key=key)
    path = client.history(
        args.symbol.upper(),
        dataset="stocks",
        timeframe=args.timeframe,
        start=day.isoformat(),
        end=end.isoformat(),
        dest=str(args.dest),
        dataframe=False,
        poll_seconds=1.5,
        timeout=1800,
    )
    print(f"saved: {path}")
    print(
        "completed_at_utc: "
        + datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
