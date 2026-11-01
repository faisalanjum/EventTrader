#!/usr/bin/env python3
"""Fetch official historical N-PORT holdings for the four pilot funds."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from xml.etree import ElementTree

import requests


ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
NPORT_NS = {"n": "http://www.sec.gov/edgar/nport"}
SEC_HEADERS = {
    "User-Agent": "EventMarketDB research contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}
FUNDS = {
    "IGV": {
        "cik": "1100663",
        "series": "S000004355",
        "name": "iShares Expanded Tech-Software Sector ETF",
    },
    "SOXX": {
        "cik": "1100663",
        "series": "S000004354",
        "name": "iShares Semiconductor ETF",
    },
    "XLE": {
        "cik": "1064641",
        "series": "S000006410",
        "name": "The Energy Select Sector SPDR Fund",
    },
    "XLK": {
        "cik": "1064641",
        "series": "S000006415",
        "name": "The Technology Select Sector SPDR Fund",
    },
}


def load_funds(
    path: Path,
    selected_symbols: Sequence[str] | None = None,
) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matched = payload.get("matched", {})
    selected = {
        symbol.strip().upper()
        for symbol in (selected_symbols or [])
        if symbol.strip()
    }
    funds: dict[str, dict[str, Any]] = {}
    for symbol, row in matched.items():
        normalized = symbol.upper()
        if selected and normalized not in selected:
            continue
        if row.get("registrations"):
            funds[normalized] = {
                "name": str(row.get("name") or normalized),
                "registrations": [
                    {
                        "cik": str(registration["cik"]),
                        "series": str(registration["series_id"]),
                        "class_id": str(registration["class_id"]),
                    }
                    for registration in row["registrations"]
                ],
            }
        else:
            funds[normalized] = {
                "cik": str(row["cik"]),
                "series": str(row["series_id"]),
                "class_id": str(row["class_id"]),
                "name": str(row.get("name") or normalized),
            }
    missing = sorted(selected - set(funds))
    if missing:
        raise ValueError(f"fund map is missing: {','.join(missing)}")
    return dict(sorted(funds.items()))


def _text(parent: ElementTree.Element, path: str) -> str:
    value = parent.find(path, NPORT_NS)
    return (value.text or "").strip() if value is not None else ""


def _attribute(
    parent: ElementTree.Element,
    path: str,
    name: str,
) -> str:
    value = parent.find(path, NPORT_NS)
    return (value.get(name) or "").strip() if value is not None else ""


def parse_nport(raw: bytes) -> dict[str, Any]:
    root = ElementTree.fromstring(raw)
    report_date = _text(root, ".//n:genInfo/n:repPdDate")
    holdings: list[dict[str, Any]] = []
    for item in root.findall(".//n:invstOrSec", NPORT_NS):
        if _text(item, "n:assetCat") != "EC":
            continue
        payoff = _text(item, "n:payoffProfile")
        if payoff and payoff != "Long":
            continue
        try:
            weight = float(_text(item, "n:pctVal"))
        except ValueError:
            continue
        if weight <= 0:
            continue
        holding = {
            "name": _text(item, "n:name"),
            "cusip": _text(item, "n:cusip"),
            "weight_percent": weight,
        }
        optional = {
            "title": _text(item, "n:title"),
            "lei": _text(item, "n:lei"),
            "isin": _attribute(
                item,
                "n:identifiers/n:isin",
                "value",
            ),
            "ticker": _attribute(
                item,
                "n:identifiers/n:ticker",
                "value",
            ),
            "currency": _text(item, "n:curCd"),
            "investment_country": _text(item, "n:invCountry"),
        }
        holding.update(
            {key: value for key, value in optional.items() if value}
        )
        holdings.append(holding)
    holdings.sort(key=lambda row: row["weight_percent"], reverse=True)
    return {"report_date": report_date, "holdings": holdings}


def parse_atom(raw: bytes) -> list[dict[str, str]]:
    root = ElementTree.fromstring(raw)
    result = []
    for entry in root.findall("a:entry", ATOM_NS):
        content = entry.find("a:content", ATOM_NS)
        if content is None:
            continue

        def content_text(name: str) -> str:
            value = content.find(f"a:{name}", ATOM_NS)
            return (value.text or "").strip() if value is not None else ""

        accession = content_text("accession-number")
        filing_date = content_text("filing-date")
        filing_type = content_text("filing-type")
        if accession and filing_date and filing_type.startswith("NPORT-P"):
            result.append(
                {
                    "accession": accession,
                    "filing_date": filing_date,
                    "filing_type": filing_type,
                }
            )
    return result


def filing_may_cover_period(
    filing_date: str,
    start_report_date: str,
) -> bool:
    """A relevant report cannot be filed before the report period starts."""

    return filing_date >= start_report_date


def fetch_bytes(
    session: requests.Session,
    url: str,
) -> bytes:
    last_error = ""
    for attempt in range(4):
        try:
            response = session.get(
                url,
                headers=SEC_HEADERS,
                timeout=90,
            )
            if response.status_code == 200:
                return response.content
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            if response.status_code != 429 and response.status_code < 500:
                break
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:200]}"
        if attempt < 3:
            time.sleep(min(2**attempt, 10))
    raise RuntimeError(last_error or "SEC request failed")


def _parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-report-date", default="2022-10-01")
    parser.add_argument("--end-report-date", default="2026-03-31")
    parser.add_argument("--fund-map", type=Path)
    parser.add_argument(
        "--symbols",
        default="",
        help="Optional comma-separated fund symbols.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=root / "raw" / "sec_nport_pilot",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request-pause-seconds", type=float, default=0.15)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    selected_symbols = [
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    ]
    if args.fund_map:
        funds = load_funds(args.fund_map, selected_symbols)
    else:
        funds = {
            symbol: fund
            for symbol, fund in FUNDS.items()
            if not selected_symbols or symbol in selected_symbols
        }
        missing = sorted(set(selected_symbols) - set(funds))
        if missing:
            raise ValueError(f"pilot fund list is missing: {','.join(missing)}")

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "source": "SEC EDGAR public NPORT-P filings",
        "safety": (
            "Public read-only SEC GET requests. No credentials, database "
            "access, or production writes."
        ),
        "period": {
            "start_report_date": args.start_report_date,
            "end_report_date": args.end_report_date,
        },
        "funds": {},
    }

    with requests.Session() as session:
        for fund_symbol, fund in funds.items():
            candidates: list[dict[str, Any]] = []
            errors: list[dict[str, str]] = []
            registrations = fund.get("registrations") or [
                {
                    "cik": fund["cik"],
                    "series": fund["series"],
                    "class_id": fund["class_id"],
                }
            ]
            atom_sources: list[dict[str, Any]] = []
            for registration in registrations:
                query = urllib.parse.urlencode(
                    {
                        "action": "getcompany",
                        "CIK": registration["series"],
                        "type": "NPORT-P",
                        "dateb": "",
                        "owner": "exclude",
                        "count": 100,
                        "output": "atom",
                    }
                )
                atom_url = (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?{query}"
                )
                fund_dir = args.raw_dir / fund_symbol
                if len(registrations) > 1:
                    fund_dir = fund_dir / registration["series"]
                atom_path = fund_dir / "filings.atom.xml"
                if atom_path.exists():
                    atom_raw = atom_path.read_bytes()
                else:
                    atom_raw = fetch_bytes(session, atom_url)
                    atom_path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = atom_path.with_suffix(".tmp")
                    temporary.write_bytes(atom_raw)
                    os.replace(temporary, atom_path)
                    time.sleep(max(args.request_pause_seconds, 0))

                filings = parse_atom(atom_raw)
                atom_sources.append(
                    {
                        **registration,
                        "atom_url": atom_url,
                        "atom_entries": len(filings),
                    }
                )
                for filing in filings:
                    if not filing_may_cover_period(
                        filing["filing_date"],
                        args.start_report_date,
                    ):
                        continue
                    accession_plain = filing["accession"].replace("-", "")
                    xml_url = (
                        "https://www.sec.gov/Archives/edgar/data/"
                        f"{registration['cik']}/{accession_plain}/"
                        "primary_doc.xml"
                    )
                    xml_path = (
                        fund_dir
                        / f"{filing['accession']}_primary_doc.xml"
                    )
                    try:
                        if xml_path.exists():
                            raw = xml_path.read_bytes()
                        else:
                            raw = fetch_bytes(session, xml_url)
                            xml_path.parent.mkdir(parents=True, exist_ok=True)
                            temporary = xml_path.with_suffix(".tmp")
                            temporary.write_bytes(raw)
                            os.replace(temporary, xml_path)
                            time.sleep(max(args.request_pause_seconds, 0))
                        parsed = parse_nport(raw)
                    except (RuntimeError, ElementTree.ParseError) as exc:
                        errors.append(
                            {
                                **filing,
                                "series": registration["series"],
                                "error": (
                                    f"{type(exc).__name__}: "
                                    f"{str(exc)[:250]}"
                                ),
                            }
                        )
                        continue
                    report_date = parsed["report_date"]
                    if not (
                        args.start_report_date
                        <= report_date
                        <= args.end_report_date
                    ):
                        continue
                    candidates.append(
                        {
                            **filing,
                            "report_date": report_date,
                            "series": registration["series"],
                            "source_url": xml_url,
                            "holdings": parsed["holdings"],
                        }
                    )

            selected_by_date: dict[str, dict[str, Any]] = {}
            for snapshot in sorted(
                candidates,
                key=lambda row: (
                    row["report_date"],
                    row["filing_date"],
                    row["filing_type"],
                ),
            ):
                selected_by_date[snapshot["report_date"]] = snapshot

            snapshots = []
            for report_date in sorted(selected_by_date):
                selected = selected_by_date[report_date]
                snapshots.append(
                    {
                        "report_date": report_date,
                        "filing_date": selected["filing_date"],
                        "filing_type": selected["filing_type"],
                        "accession": selected["accession"],
                        "series": selected.get("series"),
                        "source_url": selected["source_url"],
                        "equity_holdings": len(selected["holdings"]),
                        "equity_weight_percent": round(
                            sum(
                                item["weight_percent"]
                                for item in selected["holdings"]
                            ),
                            8,
                        ),
                        "holdings": selected["holdings"],
                    }
                )
            report["funds"][fund_symbol] = {
                **fund,
                "atom_url": (
                    atom_sources[0]["atom_url"]
                    if len(atom_sources) == 1
                    else None
                ),
                "atom_sources": atom_sources,
                "atom_entries": sum(
                    source["atom_entries"] for source in atom_sources
                ),
                "snapshots": snapshots,
                "errors": errors,
            }
            print(
                f"{fund_symbol}: {len(snapshots)} quarterly snapshots, "
                f"{len(errors)} errors"
            )

    report["summary"] = {
        "funds": len(report["funds"]),
        "snapshots": sum(
            len(fund["snapshots"]) for fund in report["funds"].values()
        ),
        "errors": sum(
            len(fund["errors"]) for fund in report["funds"].values()
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, args.output)
    print(f"saved: {args.output}")
    return 0 if report["summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
