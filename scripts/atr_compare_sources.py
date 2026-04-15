#!/usr/bin/env python3
"""
Compare ATR_N across Neo4j, Polygon, and direct IBKR gateway data.

Usage:
  venv/bin/python scripts/atr_compare_sources.py --tickers AAPL NVDA TSLA --days 14
  venv/bin/python scripts/atr_compare_sources.py --tickers ATRC EOLS LESL --days 28 --account-mode live

Notes:
  - ATR_N needs N true ranges, so the script aligns on the last N+1 common bars.
  - Neo4j/Polygon/IBKR are all reduced to the same common trading-date window before ATR is computed.
  - IBKR uses the existing in-repo direct gateway client code from ibkr-mcp-server/app/services/history.py.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from neo4j import GraphDatabase
from polygon.rest import RESTClient


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for path in [here.parent] + list(here.parents):
        if (path / "ibkr-mcp-server").exists() and (path / "eventReturns").exists():
            return path
    raise RuntimeError("Could not locate repo root")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ibkr-mcp-server"))

from scripts.earnings.utils import load_env  # noqa: E402
import app.services.client as ib_client_module  # noqa: E402
from app.core.config import init_config  # noqa: E402
from app.core.setup_logging import logger as ib_logger  # noqa: E402
from app.services.history import HistoryClient  # noqa: E402

load_env()
ib_logger.remove()
ib_logger.add(sys.stderr, level="ERROR", colorize=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare ATR across Neo4j, Polygon, and IBKR")
    parser.add_argument("--tickers", nargs="+", required=True, help="Stock tickers")
    parser.add_argument("--days", type=int, required=True, help="ATR lookback, e.g. 14 or 28")
    parser.add_argument(
        "--account-mode",
        choices=["paper", "live"],
        default=os.getenv("ACCOUNT_MODE", "live"),
        help="IBKR target gateway mode",
    )
    parser.add_argument("--ibkr-host", default=None, help="Optional IBKR gateway host override")
    parser.add_argument("--ibkr-port", type=int, default=None, help="Optional IBKR gateway port override")
    parser.add_argument("--ibkr-client-id", type=int, default=None, help="Optional IBKR clientId override")
    return parser.parse_args()


def _is_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _cluster_ip_for_service(service: str) -> str | None:
    try:
        result = subprocess.run(
            ["kubectl", "-n", "mcp-services", "get", "svc", service, "-o", "jsonpath={.spec.clusterIP}"],
            check=True,
            capture_output=True,
            text=True,
        )
        ip = result.stdout.strip()
        return ip or None
    except Exception:
        return None


def resolve_ibkr_target(account_mode: str, host_override: str | None, port_override: int | None, client_id_override: int | None) -> dict:
    if account_mode == "paper":
        service = "ibkr-paper-gateway"
        default_port = 4004
        default_client_id = 20
        env_host = os.getenv("IBKR_PAPER_HOST")
        env_port = int(os.getenv("IBKR_PAPER_PORT", str(default_port)))
        env_client_id = int(os.getenv("IBKR_PAPER_CLIENT_ID", str(default_client_id)))
    else:
        service = "ibkr-ib-gateway"
        default_port = 4003
        default_client_id = 21
        env_host = os.getenv("IBKR_LIVE_HOST")
        env_port = int(os.getenv("IBKR_LIVE_PORT", str(default_port)))
        env_client_id = int(os.getenv("IBKR_LIVE_CLIENT_ID", str(default_client_id)))

    port = port_override or env_port
    client_id = client_id_override or env_client_id

    if host_override:
        host = host_override
    else:
        candidates = []
        if env_host:
            candidates.append(env_host)
        ip = _cluster_ip_for_service(service)
        if ip:
            candidates.append(ip)
        candidates.append(service)

        host = None
        for candidate in candidates:
            if _is_reachable(candidate, port):
                host = candidate
                break
        if host is None:
            tried = ", ".join(candidates)
            raise RuntimeError(f"Could not reach IBKR {account_mode} gateway on port {port}. Tried: {tried}")

    return {"host": host, "port": port, "client_id": client_id}


def recent_calendar_start(trading_days: int) -> date:
    return date.today() - timedelta(days=max(60, trading_days * 4))


def atr_from_rows(rows: list[dict], days: int) -> float:
    if len(rows) < days + 1:
        raise ValueError(f"Need at least {days + 1} bars, got {len(rows)}")

    trs = []
    prev_close = float(rows[0]["close"])
    for row in rows[1:]:
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
        prev_close = close

    window = trs[-days:]
    return sum(window) / len(window)


def align_last_common_window(rows_by_source: dict[str, list[dict]], days: int) -> tuple[list[str], dict[str, list[dict]]]:
    date_maps = {
        source: {row["date"]: row for row in rows}
        for source, rows in rows_by_source.items()
    }
    common_dates = sorted(set.intersection(*(set(m.keys()) for m in date_maps.values())))
    if len(common_dates) < days + 1:
        raise ValueError(f"Need at least {days + 1} common bars across all sources, got {len(common_dates)}")

    dates = common_dates[-(days + 1):]
    aligned = {
        source: [date_maps[source][d] for d in dates]
        for source in rows_by_source
    }
    return dates, aligned


def fetch_neo4j_rows(driver, ticker: str, limit: int) -> list[dict]:
    query = """
    MATCH (d:Date)-[r:HAS_PRICE]->(c:Company {ticker:$ticker})
    WHERE r.open IS NOT NULL AND r.high IS NOT NULL AND r.low IS NOT NULL AND r.close IS NOT NULL
    RETURN d.date AS date,
           toFloat(r.open) AS open,
           toFloat(r.high) AS high,
           toFloat(r.low)  AS low,
           toFloat(r.close) AS close
    ORDER BY d.date DESC
    LIMIT $limit
    """
    with driver.session() as session:
        rows = [dict(row) for row in session.run(query, ticker=ticker.upper(), limit=limit)]
    rows.reverse()
    return rows


def fetch_polygon_rows(client: RESTClient, ticker: str, from_date: date, to_date: date) -> list[dict]:
    aggs = list(
        client.list_aggs(
            ticker.upper(),
            1,
            "day",
            from_date.isoformat(),
            to_date.isoformat(),
            adjusted=True,
            sort="asc",
            limit=5000,
        )
    )
    return [
        {
            "date": datetime.fromtimestamp(agg.timestamp / 1000, tz=timezone.utc).date().isoformat(),
            "open": float(agg.open),
            "high": float(agg.high),
            "low": float(agg.low),
            "close": float(agg.close),
        }
        for agg in aggs
    ]


async def fetch_ibkr_rows(client: HistoryClient, ticker: str, from_date: date, to_date: date) -> list[dict]:
    bars = await client.get_historical_bars(
        symbol=ticker.upper(),
        sec_type="STK",
        exchange="SMART",
        freq="1d",
        from_date=from_date,
        to_date=to_date,
        use_rth=True,
        currency="USD",
    )
    return [
        {
            "date": bar.timestamp[:10],
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
        }
        for bar in bars
    ]


async def main() -> None:
    args = parse_args()
    if args.days < 1:
        raise SystemExit("--days must be >= 1")

    target = resolve_ibkr_target(args.account_mode, args.ibkr_host, args.ibkr_port, args.ibkr_client_id)

    # Use daemon-style clientId namespace, not the MCP server defaults.
    ib_client_module.MARKET_DATA_CLIENT_ID = target["client_id"]
    init_config(
        gateway_mode="external",
        ib_gateway_host=target["host"],
        ib_gateway_port=target["port"],
    )

    neo_driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    polygon = RESTClient(os.environ["POLYGON_API_KEY"])
    ibkr_client = HistoryClient()

    from_date = recent_calendar_start(args.days)
    to_date = date.today()
    neo_limit = max(args.days * 5, args.days + 30)

    print(
        "ticker | last_date | close | atr_days | neo4j_atr | polygon_atr | ibkr_atr | "
        "neo4j_pct | polygon_pct | ibkr_pct | neo-poly | ib-poly"
    )

    try:
        for ticker in [t.upper() for t in args.tickers]:
            try:
                neo_rows = fetch_neo4j_rows(neo_driver, ticker, neo_limit)
                polygon_rows = fetch_polygon_rows(polygon, ticker, from_date, to_date)
                ibkr_rows = await fetch_ibkr_rows(ibkr_client, ticker, from_date, to_date)

                dates, aligned = align_last_common_window(
                    {"neo4j": neo_rows, "polygon": polygon_rows, "ibkr": ibkr_rows},
                    args.days,
                )

                neo_atr = atr_from_rows(aligned["neo4j"], args.days)
                polygon_atr = atr_from_rows(aligned["polygon"], args.days)
                ibkr_atr = atr_from_rows(aligned["ibkr"], args.days)

                close = float(aligned["polygon"][-1]["close"])
                last_date = dates[-1]
                neo_pct = 100.0 * neo_atr / close
                polygon_pct = 100.0 * polygon_atr / close
                ibkr_pct = 100.0 * ibkr_atr / close

                print(
                    f"{ticker} | {last_date} | {close:.2f} | {args.days} | "
                    f"{neo_atr:.4f} | {polygon_atr:.4f} | {ibkr_atr:.4f} | "
                    f"{neo_pct:.2f}% | {polygon_pct:.2f}% | {ibkr_pct:.2f}% | "
                    f"{neo_atr - polygon_atr:+.4f} | {ibkr_atr - polygon_atr:+.4f}"
                )
            except Exception as exc:
                print(f"{ticker} | ERROR | {exc}")
    finally:
        await ibkr_client.shutdown()
        neo_driver.close()


if __name__ == "__main__":
    asyncio.run(main())
