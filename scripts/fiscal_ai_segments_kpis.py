#!/usr/bin/env python3
"""Fetch Fiscal.ai Segments & KPIs for the EventMarketDB universe.

This script is intentionally standalone:
  - read-only Redis access for the stock universe
  - no EventMarketDB service imports
  - no Neo4j writes
  - local file storage only

Default output:
  data/fiscal_ai_segments/fiscal_segments.sqlite
  data/fiscal_ai_segments/quarterly_latest2.csv
  data/fiscal_ai_segments/raw/*.json.gz
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import redis
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "fiscal_ai_segments"
REDIS_SYMBOLS_KEY = "admin:tradable_universe:symbols"
REDIS_UNIVERSE_KEY = "admin:tradable_universe:stock_universe"
DEFAULT_REDIS_HOST = "127.0.0.1"
DEFAULT_REDIS_PORT = 6379
DEFAULT_PERIOD = "quarterly"
DEFAULT_STATEMENT = "segments-and-kpis"
FISCAL_BASE = "https://fiscal.ai"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

SEGMENT_COLUMNS = [
    "run_id",
    "symbol",
    "company_slug",
    "company_name",
    "universe_exchange",
    "cik",
    "period_type",
    "section_key",
    "section",
    "metric_key",
    "metric_name",
    "metric_id",
    "metric_tag",
    "format",
    "is_kpi",
    "period_label",
    "period_end_date",
    "value_native",
    "currency_native",
    "exchange_rate",
    "value_usd",
    "value_millions_usd",
    "unit_scale",
    "reporting_currency",
    "scraped_at",
    "source_url",
]


@dataclass(frozen=True)
class Company:
    symbol: str
    exchange: str
    company_name: str
    cik: str


@dataclass(frozen=True)
class Resolution:
    company: Company
    matched_slug: str | None
    status: str
    error: str | None
    fiscal_ticker: str
    fiscal_name: str
    fiscal_exchange: str
    fiscal_identifier: str
    candidate_slugs: list[str]


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def write_heartbeat(
    out_dir: Path,
    *,
    stage: str,
    current: int,
    total: int,
    ok: int,
    failed: int,
    message: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "updated_at": now_utc(),
        "stage": stage,
        "current": current,
        "total": total,
        "ok": ok,
        "failed": failed,
        "message": message,
        "extra": extra or {},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = out_dir / "heartbeat.json.tmp"
    final_path = out_dir / "heartbeat.json"
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(final_path)
    with (out_dir / "run.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def connect_redis(host: str, port: int) -> redis.Redis:
    return redis.Redis(
        host=host,
        port=port,
        db=0,
        decode_responses=True,
        socket_timeout=30,
        socket_connect_timeout=5,
        health_check_interval=60,
    )


def load_universe(r: redis.Redis) -> list[Company]:
    symbols_raw = r.get(REDIS_SYMBOLS_KEY)
    universe_raw = r.get(REDIS_UNIVERSE_KEY)
    if not symbols_raw:
        raise RuntimeError(f"Missing Redis key: {REDIS_SYMBOLS_KEY}")
    if not universe_raw:
        raise RuntimeError(f"Missing Redis key: {REDIS_UNIVERSE_KEY}")

    allowed_symbols = {s.strip().upper() for s in symbols_raw.split(",") if s.strip()}
    payload = json.loads(universe_raw)
    symbol_map = payload.get("symbol") or {}
    exchange_map = payload.get("exchange") or {}
    name_map = payload.get("company_name") or {}
    cik_map = payload.get("cik") or {}

    companies: list[Company] = []
    for idx, symbol in symbol_map.items():
        symbol = str(symbol).strip().upper()
        if not symbol or symbol not in allowed_symbols:
            continue
        companies.append(
            Company(
                symbol=symbol,
                exchange=str(exchange_map.get(idx, "")).strip().upper(),
                company_name=str(name_map.get(idx, "")).strip(),
                cik=str(cik_map.get(idx, "")).strip(),
            )
        )

    companies.sort(key=lambda c: c.symbol)
    return companies


def slug_candidates(company: Company) -> list[str]:
    symbol = company.symbol.replace(".", "-").replace("/", "-")
    exchange = company.exchange.upper()

    if exchange == "NAS":
        prefixes = ["NasdaqGS", "NasdaqGM", "NasdaqCM"]
    elif exchange == "NYS":
        prefixes = ["NYSE", "NYSEAM", "NYSEAmerican", "NYSEArca"]
    elif exchange == "TSE":
        prefixes = ["TSX", "TSXV", "TSXVentures"]
    elif exchange == "BATS":
        prefixes = ["BATS", "CboeBZX", "NYSEArca"]
    else:
        prefixes = [
            "NasdaqGS",
            "NasdaqGM",
            "NasdaqCM",
            "NYSE",
            "NYSEAM",
            "NYSEAmerican",
            "NYSEArca",
            "TSX",
            "BATS",
            "CboeBZX",
        ]

    # Last-resort alternates help with stale/wrong exchange values in the universe.
    alternates = ["NasdaqGS", "NasdaqGM", "NasdaqCM", "NYSE", "NYSEAM", "NYSEAmerican"]
    seen: set[str] = set()
    slugs: list[str] = []
    for prefix in [*prefixes, *alternates]:
        slug = f"{prefix}-{symbol}"
        if slug not in seen:
            seen.add(slug)
            slugs.append(slug)
    return slugs


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    return s


def fetch_build_id(http: requests.Session) -> str:
    url = f"{FISCAL_BASE}/company/NasdaqGS-AAPL/financials/segments-and-kpis/quarterly/"
    resp = http.get(url, timeout=60)
    resp.raise_for_status()
    patterns = [
        r"/_next/data/([^/]+)/company/NasdaqGS-AAPL",
        r'"buildId"\s*:\s*"([^"]+)"',
        r"static/([^/]+)/_buildManifest\.js",
    ]
    for pattern in patterns:
        match = re.search(pattern, resp.text)
        if match:
            return match.group(1)
    raise RuntimeError("Unable to find Fiscal.ai Next.js build id")


def fiscal_json_url(build_id: str, slug: str, period: str) -> str:
    quoted_slug = quote(slug, safe="-")
    return (
        f"{FISCAL_BASE}/_next/data/{build_id}/company/{quoted_slug}/financials/"
        f"{DEFAULT_STATEMENT}/{period}.json?symbol={quoted_slug}"
        f"&statement={DEFAULT_STATEMENT}&period={period}"
    )


def fiscal_company_json_url(build_id: str, slug: str) -> str:
    quoted_slug = quote(slug, safe="-")
    return f"{FISCAL_BASE}/_next/data/{build_id}/company/{quoted_slug}.json?symbol={quoted_slug}"


def extract_company_fields(payload: dict[str, Any]) -> dict[str, str]:
    company = ((payload.get("pageProps") or {}).get("company") or {})
    return {
        "ticker": str(company.get("ticker") or company.get("atlasTicker") or "").strip().upper(),
        "name": str(company.get("name") or "").strip(),
        "exchange": str(company.get("exchange") or company.get("exchangeCode") or "").strip(),
        "identifier": str(company.get("identifier") or company.get("atlasCompanyIdentifier") or "").strip(),
    }


def resolve_company_slug(
    http: requests.Session,
    build_id: str,
    company: Company,
    sleep_seconds: float,
) -> Resolution:
    candidates = slug_candidates(company)
    last_error: str | None = None
    first_mismatch: str | None = None

    for slug in candidates:
        try:
            resp = http.get(fiscal_company_json_url(build_id, slug), timeout=60)
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(sleep_seconds)
            continue

        if resp.status_code != 200:
            last_error = f"http_{resp.status_code}"
            if resp.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(max(sleep_seconds, 2.0))
            else:
                time.sleep(sleep_seconds)
            continue

        try:
            fields = extract_company_fields(resp.json())
        except ValueError as exc:
            last_error = f"invalid_json: {exc}"
            time.sleep(sleep_seconds)
            continue

        if fields["ticker"] == company.symbol:
            return Resolution(
                company=company,
                matched_slug=slug,
                status="matched",
                error=None,
                fiscal_ticker=fields["ticker"],
                fiscal_name=fields["name"],
                fiscal_exchange=fields["exchange"],
                fiscal_identifier=fields["identifier"],
                candidate_slugs=candidates,
            )

        first_mismatch = (
            first_mismatch
            or f"{slug} returned ticker={fields['ticker'] or '<missing>'}"
        )
        last_error = first_mismatch
        time.sleep(sleep_seconds)

    return Resolution(
        company=company,
        matched_slug=None,
        status="unmatched",
        error=last_error or "no_candidate_matched",
        fiscal_ticker="",
        fiscal_name="",
        fiscal_exchange="",
        fiscal_identifier="",
        candidate_slugs=candidates,
    )


def fetch_segments_payload(
    http: requests.Session,
    build_id: str,
    company: Company,
    period: str,
    sleep_seconds: float,
    known_slug: str | None = None,
    max_attempts: int = 3,
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    last_error: str | None = None
    candidates = [known_slug] if known_slug else slug_candidates(company)
    current_build_id = build_id
    last_slug: str | None = None
    for slug in candidates:
        if not slug:
            continue
        last_slug = slug
        for attempt in range(1, max_attempts + 1):
            url = fiscal_json_url(current_build_id, slug, period)
            try:
                resp = http.get(url, timeout=90)
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(max(sleep_seconds, attempt))
                continue

            if resp.status_code == 200:
                try:
                    payload = resp.json()
                except ValueError as exc:
                    return slug, None, f"invalid_json: {exc}"
                return slug, payload, None

            last_error = f"http_{resp.status_code}"
            if resp.status_code == 404:
                try:
                    refreshed_build_id = fetch_build_id(http)
                except Exception:
                    refreshed_build_id = current_build_id
                if refreshed_build_id != current_build_id:
                    current_build_id = refreshed_build_id
                    time.sleep(sleep_seconds)
                    continue

            if resp.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(max(sleep_seconds, attempt * 2.0))
                continue
            if resp.status_code == 404 and known_slug:
                time.sleep(max(sleep_seconds, attempt))
                continue
            break

        time.sleep(sleep_seconds)

    return last_slug, None, last_error


def metric_is_base(metric_name: str) -> bool:
    return not (metric_name.endswith(" % Chg.") or metric_name.endswith(" Common Size"))


def number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def convert_to_usd(value: float | None, currency: str, exchange_rate: Any) -> float | None:
    if value is None:
        return None
    if not currency or currency.upper() == "USD":
        return value
    rate = number_or_none(exchange_rate)
    if not rate:
        return None
    return value * rate


def flatten_segments(
    company: Company,
    slug: str,
    payload: dict[str, Any],
    period: str,
    latest_n: int,
    include_derived: bool,
    run_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    page_props = payload.get("pageProps") or {}
    segments = page_props.get("segmentsData") or {}
    reporting_currency = segments.get("reportingCurrency") or ""
    data_by_period = segments.get("data") or {}
    dates_by_period = segments.get("dates") or {}

    period_key = "Quarterly" if period == "quarterly" else period.title()
    period_dates = dates_by_period.get(period_key) or []
    period_dates = sorted(period_dates, key=lambda item: item.get("value", -1))
    selected_periods = period_dates[-latest_n:] if latest_n else period_dates
    selected_dates = [item.get("date") for item in selected_periods]

    rows: list[dict[str, Any]] = []
    section_map = data_by_period.get(period_key) or {}
    scraped_at = now_utc()
    for section_key, section in section_map.items():
        section_title = section.get("title") or section_key
        for row in section.get("rows") or []:
            metric = row.get("metric") or {}
            metric_name = metric.get("metricName") or metric.get("name") or metric.get("id") or ""
            metric_id = metric.get("metricId") or metric_name
            metric_key = f"{section_key}::{metric_id}"
            if not include_derived and not metric_is_base(metric_name):
                continue

            for period_item in selected_periods:
                period_end_date = period_item.get("date")
                if not period_end_date:
                    continue
                cell = row.get(period_end_date) or {}
                value = number_or_none(cell.get("value"))
                currency = (cell.get("currency") or reporting_currency or "").upper()
                exchange_rate = cell.get("exchangeRate")
                value_usd = convert_to_usd(value, currency, exchange_rate)
                fmt = metric.get("format") or ""
                value_millions_usd = (
                    value_usd / 1_000_000
                    if value_usd is not None and fmt == "number"
                    else None
                )
                rows.append(
                    {
                        "run_id": run_id,
                        "symbol": company.symbol,
                        "company_slug": slug,
                        "company_name": company.company_name,
                        "universe_exchange": company.exchange,
                        "cik": company.cik,
                        "period_type": period,
                        "section_key": section_key,
                        "section": section_title,
                        "metric_key": metric_key,
                        "metric_name": metric_name,
                        "metric_id": metric_id,
                        "metric_tag": metric.get("metricTag") or "",
                        "format": fmt,
                        "is_kpi": int(bool(metric.get("isKPIs"))),
                        "period_label": period_item.get("label") or "",
                        "period_end_date": period_end_date,
                        "value_native": value,
                        "currency_native": currency,
                        "exchange_rate": number_or_none(exchange_rate),
                        "value_usd": value_usd,
                        "value_millions_usd": value_millions_usd,
                        "unit_scale": "millions_usd" if fmt == "number" else fmt,
                        "reporting_currency": reporting_currency,
                        "scraped_at": scraped_at,
                        "source_url": f"{FISCAL_BASE}/company/{slug}/financials/{DEFAULT_STATEMENT}/{period}/",
                    }
                )

    meta = {
        "reporting_currency": reporting_currency,
        "periods_available": len(period_dates),
        "selected_periods": selected_periods,
        "selected_dates": selected_dates,
        "sections": list(section_map.keys()),
        "row_count": len(rows),
    }
    return rows, meta


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;

        CREATE TABLE IF NOT EXISTS fiscal_segments (
            run_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            company_slug TEXT NOT NULL,
            company_name TEXT,
            universe_exchange TEXT,
            cik TEXT,
            period_type TEXT NOT NULL,
            section_key TEXT,
            section TEXT,
            metric_key TEXT NOT NULL,
            metric_name TEXT,
            metric_id TEXT,
            metric_tag TEXT,
            format TEXT,
            is_kpi INTEGER,
            period_label TEXT,
            period_end_date TEXT NOT NULL,
            value_native REAL,
            currency_native TEXT,
            exchange_rate REAL,
            value_usd REAL,
            value_millions_usd REAL,
            unit_scale TEXT,
            reporting_currency TEXT,
            scraped_at TEXT,
            source_url TEXT,
            PRIMARY KEY (company_slug, period_type, metric_key, period_end_date)
        );

        CREATE TABLE IF NOT EXISTS fiscal_segments_fetch_log (
            run_id TEXT,
            symbol TEXT,
            universe_exchange TEXT,
            company_name TEXT,
            company_slug TEXT,
            period_type TEXT,
            status TEXT,
            error TEXT,
            row_count INTEGER,
            reporting_currency TEXT,
            selected_periods_json TEXT,
            scraped_at TEXT
        );

        CREATE TABLE IF NOT EXISTS fiscal_segments_slug_resolution (
            symbol TEXT NOT NULL,
            universe_exchange TEXT,
            company_name TEXT,
            cik TEXT,
            matched_slug TEXT,
            status TEXT,
            error TEXT,
            fiscal_ticker TEXT,
            fiscal_name TEXT,
            fiscal_exchange TEXT,
            fiscal_identifier TEXT,
            candidate_slugs_json TEXT,
            resolved_at TEXT,
            PRIMARY KEY (symbol, universe_exchange, cik)
        );

        CREATE INDEX IF NOT EXISTS idx_fiscal_segments_symbol
            ON fiscal_segments(symbol, period_type, period_end_date);
        CREATE INDEX IF NOT EXISTS idx_fiscal_segments_slug
            ON fiscal_segments(company_slug, period_type, period_end_date);
        CREATE INDEX IF NOT EXISTS idx_fiscal_segments_metric
            ON fiscal_segments(metric_name, period_end_date);
        """
    )


def write_rows(
    con: sqlite3.Connection,
    *,
    company_slug: str,
    period_type: str,
    rows: list[dict[str, Any]],
) -> None:
    placeholders = ",".join("?" for _ in SEGMENT_COLUMNS)
    insert_sql = (
        f"INSERT OR REPLACE INTO fiscal_segments "
        f"({','.join(SEGMENT_COLUMNS)}) VALUES ({placeholders})"
    )
    with con:
        con.execute(
            "DELETE FROM fiscal_segments WHERE company_slug = ? AND period_type = ?",
            (company_slug, period_type),
        )
        if rows:
            con.executemany(
                insert_sql,
                [[row.get(column) for column in SEGMENT_COLUMNS] for row in rows],
            )


def write_resolutions(con: sqlite3.Connection, resolutions: list[Resolution]) -> None:
    if not resolutions:
        return
    rows = [
        (
            r.company.symbol,
            r.company.exchange,
            r.company.company_name,
            r.company.cik,
            r.matched_slug or "",
            r.status,
            r.error or "",
            r.fiscal_ticker,
            r.fiscal_name,
            r.fiscal_exchange,
            r.fiscal_identifier,
            json.dumps(r.candidate_slugs),
            now_utc(),
        )
        for r in resolutions
    ]
    with con:
        con.executemany(
            """
            INSERT OR REPLACE INTO fiscal_segments_slug_resolution
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def export_resolutions_csv(con: sqlite3.Connection, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = con.execute(
        """
        SELECT *
        FROM fiscal_segments_slug_resolution
        ORDER BY status, symbol
        """
    )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([description[0] for description in cursor.description])
        writer.writerows(cursor.fetchall())


def write_log(
    con: sqlite3.Connection,
    run_id: str,
    company: Company,
    slug: str | None,
    status: str,
    error: str | None,
    meta: dict[str, Any] | None,
    period: str,
) -> None:
    with con:
        con.execute(
            """
        INSERT INTO fiscal_segments_fetch_log
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                company.symbol,
                company.exchange,
                company.company_name,
                slug or "",
                period,
                status,
                error or "",
                int((meta or {}).get("row_count") or 0),
                (meta or {}).get("reporting_currency") or "",
                json.dumps((meta or {}).get("selected_periods") or []),
                now_utc(),
            ],
        )


def write_raw(raw_dir: Path, slug: str, period: str, payload: dict[str, Any]) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{slug}_{period}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def export_csv(con: sqlite3.Connection, csv_path: Path, period_type: str) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    cursor = con.execute(
        """
        SELECT *
        FROM fiscal_segments
        WHERE period_type = ?
        ORDER BY symbol, section, metric_name, period_end_date
        """,
        (period_type,),
    )
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([description[0] for description in cursor.description])
        writer.writerows(cursor.fetchall())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-host", default=os.getenv("REDIS_HOST", DEFAULT_REDIS_HOST))
    parser.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", DEFAULT_REDIS_PORT)))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=0, help="Limit companies for canary runs")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols to fetch")
    parser.add_argument("--period", choices=["quarterly", "annual"], default=DEFAULT_PERIOD)
    parser.add_argument("--latest-n", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--include-derived", action="store_true", help="Include %% Chg. and Common Size rows")
    parser.add_argument("--skip-raw", action="store_true", help="Do not write gzipped source JSON snapshots")
    parser.add_argument("--resolve-only", action="store_true", help="Only resolve Fiscal.ai slugs and write coverage report")
    parser.add_argument("--use-existing-resolution", action="store_true", help="Reuse output slug_resolution.csv if it covers all requested symbols")
    parser.add_argument("--skip-completed", action="store_true", help="Skip slugs already logged as successful for the selected period")
    args = parser.parse_args()

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "fiscal_segments.sqlite"
    raw_dir = out_dir / "raw"
    effective_latest_n = args.latest_n
    if effective_latest_n is None:
        effective_latest_n = 2 if args.period == "quarterly" else 0
    csv_name = (
        f"{args.period}_latest{effective_latest_n}.csv"
        if effective_latest_n
        else f"{args.period}_all.csv"
    )
    csv_path = out_dir / csv_name
    resolution_csv_path = out_dir / "slug_resolution.csv"
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    r = connect_redis(args.redis_host, args.redis_port)
    r.ping()
    companies = load_universe(r)
    if args.symbols:
        wanted = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}
        companies = [company for company in companies if company.symbol in wanted]
    if args.limit:
        companies = companies[: args.limit]

    http = session()
    build_id = fetch_build_id(http)
    print(f"Universe companies: {len(companies)}")
    print(f"Fiscal.ai build id: {build_id}")
    print(f"Output DB: {db_path}")
    write_heartbeat(
        out_dir,
        stage="start",
        current=0,
        total=len(companies),
        ok=0,
        failed=0,
        message="loaded universe and fiscal build id",
        extra={"build_id": build_id, "db_path": str(db_path), "run_id": run_id},
    )

    con = sqlite3.connect(str(db_path), timeout=60)
    ensure_schema(con)

    resolutions: list[Resolution] = []
    if args.use_existing_resolution and resolution_csv_path.exists():
        by_symbol_exchange_cik: dict[tuple[str, str, str], dict[str, str]] = {}
        with resolution_csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row.get("symbol", ""), row.get("universe_exchange", ""), row.get("cik", ""))
                by_symbol_exchange_cik[key] = row
        for company in companies:
            row = by_symbol_exchange_cik.get((company.symbol, company.exchange, company.cik))
            if not row or row.get("status") != "matched" or not row.get("matched_slug"):
                resolutions = []
                break
            resolutions.append(
                Resolution(
                    company=company,
                    matched_slug=row.get("matched_slug"),
                    status=row.get("status", "matched"),
                    error=row.get("error") or None,
                    fiscal_ticker=row.get("fiscal_ticker", ""),
                    fiscal_name=row.get("fiscal_name", ""),
                    fiscal_exchange=row.get("fiscal_exchange", ""),
                    fiscal_identifier=row.get("fiscal_identifier", ""),
                    candidate_slugs=json.loads(row.get("candidate_slugs_json") or "[]"),
                )
            )
        if resolutions:
            print(f"Reusing existing slug report: {resolution_csv_path}")

    if not resolutions:
        for index, company in enumerate(companies, start=1):
            resolution = resolve_company_slug(http, build_id, company, args.sleep)
            resolutions.append(resolution)
            if resolution.matched_slug:
                print(
                    f"[resolve {index}/{len(companies)}] MATCH {company.symbol} "
                    f"{company.exchange} -> {resolution.matched_slug}"
                )
            else:
                print(
                    f"[resolve {index}/{len(companies)}] MISS {company.symbol} "
                    f"{company.exchange}: {resolution.error}"
                )
            write_heartbeat(
                out_dir,
                stage="resolve",
                current=index,
                total=len(companies),
                ok=sum(1 for item in resolutions if item.matched_slug),
                failed=sum(1 for item in resolutions if not item.matched_slug),
                message=f"resolved {company.symbol}",
                extra={
                    "symbol": company.symbol,
                    "matched_slug": resolution.matched_slug,
                    "status": resolution.status,
                    "error": resolution.error,
                },
            )
            time.sleep(args.sleep)

    write_resolutions(con, resolutions)
    export_resolutions_csv(con, resolution_csv_path)
    matched = [r for r in resolutions if r.matched_slug]
    unmatched = [r for r in resolutions if not r.matched_slug]
    print(f"Slug coverage: {len(matched)}/{len(resolutions)} matched ({len(unmatched)} unmatched)")
    print(f"Slug report: {resolution_csv_path}")
    if args.resolve_only:
        write_heartbeat(
            out_dir,
            stage="complete",
            current=len(resolutions),
            total=len(resolutions),
            ok=len(matched),
            failed=len(unmatched),
            message="slug resolution complete",
            extra={"slug_report": str(resolution_csv_path)},
        )
        con.close()
        return 0 if not unmatched else 1

    if args.skip_completed:
        completed_slugs = {
            row[0]
            for row in con.execute(
                """
                SELECT DISTINCT company_slug
                FROM fiscal_segments_fetch_log
                WHERE period_type = ?
                  AND status = 'ok'
                  AND company_slug != ''
                """,
                (args.period,),
            )
        }
        before = len(matched)
        matched = [r for r in matched if r.matched_slug not in completed_slugs]
        print(f"Skipping completed {before - len(matched)} slugs; remaining fetches: {len(matched)}")

    ok = 0
    failed = 0
    for index, resolution in enumerate(matched, start=1):
        company = resolution.company
        slug, payload, error = fetch_segments_payload(
            http=http,
            build_id=build_id,
            company=company,
            period=args.period,
            sleep_seconds=args.sleep,
            known_slug=resolution.matched_slug,
        )
        if payload is None or slug is None:
            failed += 1
            write_log(con, run_id, company, slug, "failed", error, None, args.period)
            print(f"[{index}/{len(companies)}] FAIL {company.symbol} {company.exchange}: {error}")
            write_heartbeat(
                out_dir,
                stage="fetch",
                current=index,
                total=len(matched),
                ok=ok,
                failed=failed,
                message=f"failed fetch {company.symbol}",
                extra={"symbol": company.symbol, "error": error},
            )
            continue

        rows, meta = flatten_segments(
            company=company,
            slug=slug,
            payload=payload,
            period=args.period,
            latest_n=effective_latest_n,
            include_derived=args.include_derived,
            run_id=run_id,
        )
        write_rows(con, company_slug=slug, period_type=args.period, rows=rows)
        write_log(con, run_id, company, slug, "ok", None, meta, args.period)
        if not args.skip_raw:
            write_raw(raw_dir, slug, args.period, payload)
        ok += 1
        selected = ", ".join(p.get("label", "") for p in meta["selected_periods"])
        print(f"[{index}/{len(companies)}] OK {company.symbol} -> {slug}: {len(rows)} rows ({selected})")
        write_heartbeat(
            out_dir,
            stage="fetch",
            current=index,
            total=len(matched),
            ok=ok,
            failed=failed,
            message=f"fetched {company.symbol}",
            extra={
                "symbol": company.symbol,
                "slug": slug,
                "rows": len(rows),
                "selected_periods": meta["selected_periods"],
            },
        )
        time.sleep(args.sleep)

    export_csv(con, csv_path, args.period)
    con.close()
    print(f"Done. ok={ok} failed={failed}")
    print(f"CSV: {csv_path}")
    print(f"SQLite: {db_path}")
    write_heartbeat(
        out_dir,
        stage="complete",
        current=len(matched),
        total=len(matched),
        ok=ok,
        failed=failed,
        message="fetch complete",
        extra={"csv_path": str(csv_path), "db_path": str(db_path)},
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
