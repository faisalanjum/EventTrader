#!/usr/bin/env python3
"""Suggest, but never auto-apply, LSE catalog matches for unresolved holdings."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Sequence

from build_holding_ticker_map import normalize_company_name


def rank_name_candidates(
    holding_name: str,
    catalog_rows: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    wanted = normalize_company_name(holding_name)
    ranked = []
    for row in catalog_rows:
        if row.get("dataset") != "stocks" or not row.get("symbol"):
            continue
        candidate = normalize_company_name(str(row.get("name", "")))
        if not wanted or not candidate:
            continue
        score = SequenceMatcher(None, wanted, candidate).ratio()
        ranked.append(
            {
                "symbol": str(row["symbol"]).upper(),
                "name": str(row.get("name", "")),
                "score": round(score, 6),
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["symbol"]))
    return ranked[: max(int(limit), 0)]


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--unresolved-map", type=Path, required=True)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=root / "inventory" / "lse_market_catalog_2026-07-19.json",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    unresolved_map = json.loads(
        args.unresolved_map.read_text(encoding="utf-8")
    )
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    rows = []
    high_confidence = 0
    for holding in unresolved_map["unresolved"]:
        candidates = rank_name_candidates(
            str(holding.get("name", "")),
            catalog["rows"],
            limit=args.limit,
        )
        top_score = candidates[0]["score"] if candidates else 0.0
        second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
        review_tier = (
            "high_confidence_review"
            if top_score >= 0.9 and top_score - second_score >= 0.05
            else "manual_review"
        )
        high_confidence += review_tier == "high_confidence_review"
        rows.append(
            {
                **holding,
                "review_tier": review_tier,
                "candidates": candidates,
            }
        )

    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Local fuzzy-name suggestions only. No suggestion was applied "
            "automatically and no production file or database was changed."
        ),
        "method": (
            "SequenceMatcher over normalized company names in the complete "
            "LSE stock catalog. Every result requires identifier or manual "
            "review before use."
        ),
        "summary": {
            "unresolved": len(rows),
            "high_confidence_review": high_confidence,
            "manual_review": len(rows) - high_confidence,
        },
        "rows": rows,
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
