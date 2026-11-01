#!/usr/bin/env python3
"""Map production benchmark tickers to official SEC fund identifiers."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import requests


SEC_SOURCE_URL = "https://www.sec.gov/files/company_tickers_mf.json"
SEC_HEADERS = {
    "User-Agent": "EventMarketDB research contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def parse_sec_fund_rows(raw: bytes) -> list[dict[str, str]]:
    payload = json.loads(raw)
    fields = payload.get("fields")
    data = payload.get("data")
    required = {"cik", "seriesId", "classId", "symbol"}
    if not isinstance(fields, list) or not required.issubset(fields):
        raise ValueError("SEC fund file is missing required fields")
    if not isinstance(data, list):
        raise ValueError("SEC fund file data must be a list")

    result: list[dict[str, str]] = []
    for values in data:
        if not isinstance(values, list) or len(values) != len(fields):
            raise ValueError("SEC fund row does not match declared fields")
        row = dict(zip(fields, values))
        result.append(
            {
                "cik": str(row["cik"]),
                "series_id": str(row["seriesId"]),
                "class_id": str(row["classId"]),
                "symbol": str(row["symbol"]).strip().upper(),
            }
        )
    return result


def map_target_funds(
    rows: Iterable[dict[str, str]],
    targets: Iterable[str],
) -> dict[str, Any]:
    target_symbols = sorted({str(symbol).strip().upper() for symbol in targets})
    by_symbol: dict[str, list[dict[str, str]]] = {
        symbol: [] for symbol in target_symbols
    }
    for row in rows:
        symbol = row["symbol"].upper()
        if symbol in by_symbol:
            by_symbol[symbol].append(dict(row))

    return {
        "matched": {
            symbol: matches[0]
            for symbol, matches in by_symbol.items()
            if len(matches) == 1
        },
        "missing": [
            symbol for symbol, matches in by_symbol.items() if not matches
        ],
        "ambiguous": {
            symbol: matches
            for symbol, matches in by_symbol.items()
            if len(matches) > 1
        },
    }


def _read_source(source: str) -> bytes:
    if source.startswith(("https://", "http://")):
        response = requests.get(
            source,
            headers=SEC_HEADERS,
            timeout=90,
        )
        response.raise_for_status()
        return response.content
    return Path(source).read_bytes()


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--sec-source", default=SEC_SOURCE_URL)
    parser.add_argument(
        "--targets",
        type=Path,
        default=(
            root
            / "results"
            / "production_etf_coverage_2026-07-19.json"
        ),
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=(
            root / "inventory" / "sec_company_tickers_mf_2026-07-19.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "inventory" / "all63_sec_fund_map_2026-07-19.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    raw = _read_source(args.sec_source)
    rows = parse_sec_fund_rows(raw)
    target_payload = json.loads(args.targets.read_text(encoding="utf-8"))
    targets = [row["symbol"] for row in target_payload["requirements"]]
    mapping = map_target_funds(rows, targets)

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": SEC_SOURCE_URL,
        "target_source": str(args.targets),
        "safety": (
            "Public read-only SEC data. No database access, credentials, "
            "or production writes."
        ),
        **mapping,
        "summary": {
            "targets": len(set(targets)),
            "matched": len(mapping["matched"]),
            "missing": len(mapping["missing"]),
            "ambiguous": len(mapping["ambiguous"]),
        },
    }

    _atomic_write(args.raw_output, raw)
    _atomic_write(
        args.output,
        (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(
        f"matched {report['summary']['matched']} of "
        f"{report['summary']['targets']}; "
        f"missing={','.join(mapping['missing']) or 'none'}; "
        f"ambiguous={','.join(mapping['ambiguous']) or 'none'}"
    )
    print(f"saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
