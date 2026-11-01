#!/usr/bin/env python3
"""Combine exact-LSE and holdings-basket evidence for all required ETFs."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


EVIDENCE_FIELDS = (
    "verdict",
    "observations",
    "target_coverage",
    "correlation",
    "beta",
    "mean_absolute_error_pp",
    "minimum_selected_weight",
    "basket_size",
    "method",
    "source",
)


def candidate_summary(
    candidate: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not candidate:
        return None
    comparison = candidate["comparison"]
    coverage = comparison["coverage"]
    full = comparison["full_period"]
    return {
        "verdict": comparison.get("numerical_verdict"),
        "observations": full.get("observations"),
        "target_coverage": coverage.get("fraction"),
        "correlation": full.get("correlation"),
        "beta": full.get("beta"),
        "mean_absolute_error_pp": full.get("mean_absolute_error_pp"),
        "minimum_selected_weight": candidate.get(
            "minimum_weight_coverage"
        ),
        "basket_size": candidate.get("size"),
        "method": candidate.get("method"),
    }


def _verdict(evidence: dict[str, Any] | None) -> str | None:
    return evidence.get("verdict") if evidence else None


def classify_replacement(
    *,
    exact_lse: bool,
    invalid_mapping: bool,
    historical_strict: dict[str, Any] | None,
    recent_strict: dict[str, Any] | None,
    historical_sensitivity: dict[str, Any] | None,
    recent_sensitivity: dict[str, Any] | None,
) -> str:
    if invalid_mapping:
        return "invalid_production_mapping"
    if exact_lse:
        return "exact_lse_recent"
    if (
        _verdict(historical_strict) == "strong"
        and _verdict(recent_strict) == "strong"
    ):
        return "basket_strong_strict_both"
    if (
        _verdict(historical_sensitivity) == "strong"
        and _verdict(recent_sensitivity) == "strong"
    ):
        return "basket_strong_only_with_lower_coverage"
    observed = {
        _verdict(item)
        for item in (
            historical_strict,
            recent_strict,
            historical_sensitivity,
            recent_sensitivity,
        )
    }
    if observed.intersection({"strong", "context_only"}):
        return "basket_partial_or_context"
    return "no_supported_replacement"


def load_evidence(paths: list[Path]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        for symbol, fund in report.get("funds", {}).items():
            if symbol in evidence:
                raise ValueError(
                    f"Duplicate evidence for {symbol}: "
                    f"{evidence[symbol]['source']} and {path}"
                )
            summary = candidate_summary(fund.get("best_candidate"))
            if summary is not None:
                summary["source"] = str(path)
                evidence[str(symbol)] = summary
    return evidence


def recommendation(classification: str) -> str:
    return {
        "exact_lse_recent": (
            "Use exact LSE ETF data for recent/live work only with freshness "
            "and complete-close checks; use another source for older history."
        ),
        "invalid_production_mapping": (
            "Fix the production benchmark mapping before choosing a data "
            "source."
        ),
        "basket_strong_strict_both": (
            "Regular-close basket candidate. Event-time and outside-hours "
            "replacement is not proven."
        ),
        "basket_strong_only_with_lower_coverage": (
            "Promising diagnostic basket, but not ready because it needed "
            "relaxed constituent-weight and/or target-date coverage."
        ),
        "basket_partial_or_context": (
            "Context signal only; do not treat it as the ETF return."
        ),
        "no_supported_replacement": (
            "No supported LSE replacement found."
        ),
    }[classification]


def build_rows(
    coverage_report: dict[str, Any],
    *,
    invalid_symbols: set[str],
    historical_strict: dict[str, dict[str, Any]],
    recent_strict: dict[str, dict[str, Any]],
    historical_sensitivity: dict[str, dict[str, Any]],
    recent_sensitivity: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for requirement in coverage_report["requirements"]:
        symbol = str(requirement["symbol"])
        exact_lse = bool(
            requirement.get("lse", {}).get("exact_etf_available")
        )
        classification = classify_replacement(
            exact_lse=exact_lse,
            invalid_mapping=symbol in invalid_symbols,
            historical_strict=historical_strict.get(symbol),
            recent_strict=recent_strict.get(symbol),
            historical_sensitivity=historical_sensitivity.get(symbol),
            recent_sensitivity=recent_sensitivity.get(symbol),
        )
        rows.append(
            {
                "symbol": symbol,
                "roles": requirement.get("roles", []),
                "production_groups": requirement.get("groups", []),
                "production_company_count": requirement.get(
                    "csv_company_count", 0
                ),
                "exact_lse_etf": exact_lse,
                "historical_strict": historical_strict.get(symbol),
                "recent_strict": recent_strict.get(symbol),
                "historical_lower_coverage_diagnostic": (
                    historical_sensitivity.get(symbol)
                ),
                "recent_lower_coverage_diagnostic": (
                    recent_sensitivity.get(symbol)
                ),
                "classification": classification,
                "recommendation": recommendation(classification),
                "complete_massive_replacement_proven": False,
            }
        )
    return rows


def _evidence_text(value: dict[str, Any] | None) -> str:
    if not value:
        return "—"
    verdict = value.get("verdict") or "unknown"
    observations = value.get("observations")
    return f"{verdict} ({observations or 0}d)"


def markdown_report(report: dict[str, Any]) -> str:
    labels = {
        "exact_lse_recent": "Exact LSE, recent",
        "invalid_production_mapping": "Invalid mapping",
        "basket_strong_strict_both": "Strong basket, strict",
        "basket_strong_only_with_lower_coverage": (
            "Strong only under relaxed coverage"
        ),
        "basket_partial_or_context": "Partial / context",
        "no_supported_replacement": "No supported replacement",
    }
    lines = [
        "# All 63 Production ETF Replacement Matrix",
        "",
        f"Generated: {report['generated_at_utc']}",
        "",
        "## Bottom line",
        "",
        (
            "This table tests regular U.S. market closes. It does not prove "
            "a full Massive replacement for one-second event returns, "
            "pre-market, or after-hours returns."
        ),
        "",
        "| Result | Count |",
        "|---|---:|",
    ]
    for key, count in sorted(report["summary"]["classifications"].items()):
        lines.append(f"| {labels[key]} | {count} |")
    lines.extend(
        [
            "",
            "“Strict” requires at least 80% of selected constituent weight "
            "and the normal target-date rule. The relaxed-coverage columns "
            "are diagnostics, not approval for production use.",
            "",
            "| ETF | Role | Companies | Exact LSE | Historical strict | "
            "Recent strict | Historical diagnostic | Recent diagnostic | "
            "Result |",
            "|---|---|---:|:---:|---|---|---|---|---|",
        ]
    )
    for row in report["rows"]:
        lines.append(
            "| {symbol} | {roles} | {companies} | {exact} | {historical} | "
            "{recent} | {historical_diagnostic} | {recent_diagnostic} | "
            "{classification} |".format(
                symbol=row["symbol"],
                roles=", ".join(row["roles"]),
                companies=row["production_company_count"],
                exact="yes" if row["exact_lse_etf"] else "no",
                historical=_evidence_text(row["historical_strict"]),
                recent=_evidence_text(row["recent_strict"]),
                historical_diagnostic=_evidence_text(
                    row["historical_lower_coverage_diagnostic"]
                ),
                recent_diagnostic=_evidence_text(
                    row["recent_lower_coverage_diagnostic"]
                ),
                classification=labels[row["classification"]],
            )
        )
    lines.extend(
        [
            "",
            "Full numerical details and source-file paths are in the JSON "
            "and CSV versions beside this document.",
            "",
        ]
    )
    return "\n".join(lines)


def csv_text(rows: list[dict[str, Any]]) -> str:
    basic_fields = (
        "symbol",
        "roles",
        "production_groups",
        "production_company_count",
        "exact_lse_etf",
        "classification",
        "recommendation",
        "complete_massive_replacement_proven",
    )
    evidence_columns = (
        "historical_strict",
        "recent_strict",
        "historical_lower_coverage_diagnostic",
        "recent_lower_coverage_diagnostic",
    )
    fieldnames = list(basic_fields)
    for column in evidence_columns:
        fieldnames.extend(
            f"{column}_{field}" for field in EVIDENCE_FIELDS
        )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        flat = {
            key: (
                ";".join(row[key])
                if isinstance(row.get(key), list)
                else row.get(key)
            )
            for key in basic_fields
        }
        for column in evidence_columns:
            value = row.get(column) or {}
            for field in EVIDENCE_FIELDS:
                flat[f"{column}_{field}"] = value.get(field)
        writer.writerow(flat)
    return stream.getvalue()


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument(
        "--historical-strict", action="append", type=Path, default=[]
    )
    parser.add_argument(
        "--recent-strict", action="append", type=Path, default=[]
    )
    parser.add_argument(
        "--historical-sensitivity", action="append", type=Path, default=[]
    )
    parser.add_argument(
        "--recent-sensitivity", action="append", type=Path, default=[]
    )
    parser.add_argument(
        "--invalid-symbol", action="append", default=[]
    )
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))
    historical_strict = load_evidence(args.historical_strict)
    recent_strict = load_evidence(args.recent_strict)
    historical_sensitivity = load_evidence(
        args.historical_sensitivity
    )
    recent_sensitivity = load_evidence(args.recent_sensitivity)
    rows = build_rows(
        coverage,
        invalid_symbols={
            str(symbol).upper() for symbol in args.invalid_symbol
        },
        historical_strict=historical_strict,
        recent_strict=recent_strict,
        historical_sensitivity=historical_sensitivity,
        recent_sensitivity=recent_sensitivity,
    )
    report = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "safety": (
            "Built only from isolated read-only evidence files. No network, "
            "database, Redis, or production write."
        ),
        "method": {
            "strict": (
                "At least 80% selected constituent-weight coverage, plus "
                "the normal history/recent target-date rules."
            ),
            "lower_coverage_diagnostic": (
                "Allows selected constituent-weight coverage below 80% "
                "and/or the recent target-date threshold below 80%. This is "
                "diagnostic evidence, not production readiness."
            ),
            "split_handling": (
                "All basket reports use the complete LSE split table and "
                "automatic split/no-double-adjustment logic."
            ),
            "full_replacement_limit": (
                "Daily regular-close matching does not prove one-second "
                "event, pre-market, or after-hours equivalence."
            ),
        },
        "sources": {
            "coverage": str(args.coverage),
            "historical_strict": [
                str(path) for path in args.historical_strict
            ],
            "recent_strict": [
                str(path) for path in args.recent_strict
            ],
            "historical_sensitivity": [
                str(path) for path in args.historical_sensitivity
            ],
            "recent_sensitivity": [
                str(path) for path in args.recent_sensitivity
            ],
        },
        "summary": {
            "required_etfs": len(rows),
            "exact_lse_etfs": sum(
                bool(row["exact_lse_etf"]) for row in rows
            ),
            "classifications": dict(
                sorted(Counter(
                    row["classification"] for row in rows
                ).items())
            ),
            "complete_massive_replacement_proven": 0,
        },
        "rows": rows,
    }
    write_atomic(
        args.output_json,
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    write_atomic(args.output_csv, csv_text(rows))
    write_atomic(args.output_markdown, markdown_report(report))
    print(json.dumps(report["summary"], sort_keys=True))
    print(f"saved: {args.output_json}")
    print(f"saved: {args.output_csv}")
    print(f"saved: {args.output_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
