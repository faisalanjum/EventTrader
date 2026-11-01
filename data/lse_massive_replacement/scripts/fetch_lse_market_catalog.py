#!/usr/bin/env python3
"""Save the LSE stock and market-series catalog without saving credentials."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from audit_production_etf_coverage import (
    MARKET_PROXY_DATASETS,
    _catalog_row,
    api_get,
)
from fetch_lse_proxy_pilot import read_api_key


RELEVANT_DATASETS = MARKET_PROXY_DATASETS | {"stocks"}


def select_relevant_catalog(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only stocks and series that could substitute for market prices."""

    selected = [
        _catalog_row(row)
        for row in rows
        if str(row.get("dataset", "")).lower() in RELEVANT_DATASETS
    ]
    return sorted(
        selected,
        key=lambda row: (
            str(row.get("dataset", "")),
            str(row.get("symbol", "")),
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private-key-source", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    api_key = read_api_key(
        os.environ.get("LSE_API_KEY", ""),
        args.private_key_source,
    )
    response = api_get(api_key, "/catalog")
    rows = response.get("body")
    if response.get("status") != 200 or not isinstance(rows, list):
        raise RuntimeError(
            f"LSE catalog failed with status {response.get('status')}"
        )

    relevant = select_relevant_catalog(rows)
    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": "https://api.londonstrategicedge.com/vault/catalog",
        "safety": (
            "One read-only LSE GET request. The API key and headers were not "
            "printed or saved. Production code and databases were untouched."
        ),
        "all_catalog_counts": dict(
            sorted(Counter(str(row.get("dataset", "")) for row in rows).items())
        ),
        "saved_catalog_counts": dict(
            sorted(
                Counter(
                    str(row.get("dataset", ""))
                    for row in relevant
                ).items()
            )
        ),
        "rows": relevant,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(
        f"saved {len(relevant)} stock/market rows from "
        f"{len(rows)} catalog rows: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
