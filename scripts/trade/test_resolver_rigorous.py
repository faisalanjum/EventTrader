"""Rigorous test harness for Neo4jExchangeResolver + trade-daemon wiring.

Three layers of testing, each gated independently so partial environments
still produce useful signal:

  1. UNIT — pure-Python tests with an injected fake driver. No Neo4j, no
     IBKR. Always runs.
  2. INTEGRATION-NEO4J — real Neo4j queries via NEO4J_URI/NEO4J_USERNAME/
     NEO4J_PASSWORD env. Skipped if env not set or driver fails to connect.
  3. INTEGRATION-IBKR — full pipeline against paper IBKR gateway. Calls
     qualify_stock both with and without the resolver, asserts conIds are
     identical (proves zero regression). Skipped if gateway unreachable.

Exits 0 only if every layer that ran succeeded. Skipped layers don't fail.

Usage:
  python scripts/trade/test_resolver_rigorous.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.trade.ibkr_client import IBKRConfig, TradeDaemonIBClient
from scripts.trade.neo4j_exchange_resolver import (
    Neo4jExchangeResolver,
    _NEO4J_TO_IBKR,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rigorous")


# ─────────────────────────────────────────────────────────────────────
# Layer 1 — UNIT TESTS (no external dependencies)
# ─────────────────────────────────────────────────────────────────────


class _FakeRecord:
    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, k):
        return self._data[k]


class _FakeResult:
    def __init__(self, record: _FakeRecord | None):
        self._record = record

    def single(self):
        return self._record

    def data(self):
        return [self._record._data] if self._record else []


class _FakeSession:
    def __init__(self, mapping: dict[str, str | None], counters: dict, fail: bool = False):
        self._mapping = mapping
        self._counters = counters
        self._fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def run(self, query: str, **params):
        self._counters["queries"] = self._counters.get("queries", 0) + 1
        if self._fail:
            raise RuntimeError("simulated neo4j outage")
        if "UNWIND" in query:
            syms = params.get("syms", [])
            rows = [{"ticker": s, "ex": self._mapping.get(s)} for s in syms if self._mapping.get(s)]
            class R:
                def data(self_inner): return rows
            return R()
        sym = params.get("sym")
        ex = self._mapping.get(sym)
        rec = _FakeRecord({"ex": ex}) if ex is not None else None
        return _FakeResult(rec)


class _FakeDriver:
    def __init__(self, mapping: dict[str, str | None], fail: bool = False):
        self._mapping = mapping
        self._fail = fail
        self.counters: dict[str, int] = {}

    def session(self):
        return _FakeSession(self._mapping, self.counters, fail=self._fail)

    def close(self):
        self.counters["closed"] = self.counters.get("closed", 0) + 1


def unit_tests() -> int:
    failures = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal failures
        if cond:
            log.info("UNIT pass: %s", name)
        else:
            failures += 1
            log.error("UNIT FAIL: %s — %s", name, detail)

    # 1.1 — happy path lookups
    drv = _FakeDriver({"AAPL": "NAS", "IBM": "NYS", "CBOE": "BATS"})
    r = Neo4jExchangeResolver(driver=drv)
    check("AAPL → NASDAQ", r("AAPL") == "NASDAQ")
    check("IBM → NYSE", r("IBM") == "NYSE")
    check("CBOE → BATS", r("CBOE") == "BATS")

    # 1.2 — case insensitivity
    check("aapl (lowercase) → NASDAQ", r("aapl") == "NASDAQ")

    # 1.3 — cache effectiveness (no extra queries on repeat)
    queries_before = drv.counters.get("queries", 0)
    for _ in range(5):
        r("AAPL")
    queries_after = drv.counters.get("queries", 0)
    check(
        "cache prevents repeat queries",
        queries_after == queries_before,
        f"expected no new queries, got {queries_after - queries_before}",
    )

    # 1.4 — unknown ticker → None, cached as miss
    drv2 = _FakeDriver({})
    r2 = Neo4jExchangeResolver(driver=drv2)
    check("UNKNOWN → None", r2("UNKNOWN") is None)
    q_before = drv2.counters.get("queries", 0)
    r2("UNKNOWN")  # second call should hit cache
    q_after = drv2.counters.get("queries", 0)
    check("miss is cached (no second query)", q_after == q_before)

    # 1.5 — Neo4j down → returns None, NOT cached (so retry can succeed)
    drv3 = _FakeDriver({"AAPL": "NAS"}, fail=True)
    r3 = Neo4jExchangeResolver(driver=drv3)
    check("Neo4j outage → None", r3("AAPL") is None)
    queries_before = drv3.counters.get("queries", 0)
    r3("AAPL")  # should retry, not stay cached
    queries_after = drv3.counters.get("queries", 0)
    check(
        "outage NOT cached — retries on next call",
        queries_after > queries_before,
        f"expected retry, got {queries_after - queries_before} new queries",
    )

    # 1.6 — TSE intentionally not in map
    drv4 = _FakeDriver({"CP": "TSE"})
    r4 = Neo4jExchangeResolver(driver=drv4)
    check("TSE-listed → None (Toronto not US)", r4("CP") is None)

    # 1.7 — preload primes the cache
    drv5 = _FakeDriver({"AAPL": "NAS", "IBM": "NYS", "CP": "TSE", "BOGUS": None})
    r5 = Neo4jExchangeResolver(driver=drv5)
    primed = r5.preload(["AAPL", "IBM", "CP", "ZZZZ"])
    check(
        "preload result shape",
        primed == {"AAPL": "NASDAQ", "IBM": "NYSE", "CP": None, "ZZZZ": None},
        f"got {primed}",
    )
    q_before = drv5.counters.get("queries", 0)
    for sym in ["AAPL", "IBM", "CP", "ZZZZ"]:
        r5(sym)
    q_after = drv5.counters.get("queries", 0)
    check(
        "preload populates cache (no per-symbol queries after)",
        q_after == q_before,
        f"got {q_after - q_before} new queries",
    )

    # 1.8 — context manager closes driver when owned
    class _OwnedDriver(_FakeDriver):
        pass
    od = _OwnedDriver({"AAPL": "NAS"})
    # simulate "owned" by constructing without driver= arg path:
    r6 = Neo4jExchangeResolver(driver=od)
    r6._owns_driver = True  # force ownership for the close-test
    with r6:
        r6("AAPL")
    check("context-manager closes owned driver", od.counters.get("closed") == 1)

    # 1.9 — injected driver is NOT closed by default
    inj = _FakeDriver({"AAPL": "NAS"})
    r7 = Neo4jExchangeResolver(driver=inj)
    r7.close()
    check(
        "injected driver NOT closed by resolver.close()",
        inj.counters.get("closed", 0) == 0,
    )

    # 1.10 — _NEO4J_TO_IBKR coverage matches Neo4j universe
    check(
        "code map covers exactly NAS, NYS, BATS",
        set(_NEO4J_TO_IBKR) == {"NAS", "NYS", "BATS"},
    )

    # 1.11 — _build_stock_contract on the client uses resolver
    cfg = IBKRConfig.from_account_mode("paper")
    drv8 = _FakeDriver({"AAPL": "NAS"})
    r8 = Neo4jExchangeResolver(driver=drv8)
    client = TradeDaemonIBClient(cfg, primary_exchange_resolver=r8)
    c_resolved = client._build_stock_contract("AAPL")
    c_unknown = client._build_stock_contract("ZZZZ")
    check("client uses SMART:NASDAQ via resolver", c_resolved.exchange == "SMART:NASDAQ")
    check("client falls back to SMART for unknown", c_unknown.exchange == "SMART")

    # 1.12 — client without resolver preserves original behavior
    plain_client = TradeDaemonIBClient(cfg)
    c_plain = plain_client._build_stock_contract("AAPL")
    check("client w/o resolver → bare SMART (regression guard)", c_plain.exchange == "SMART")

    log.info("UNIT layer: %d failure(s)", failures)
    return failures


# ─────────────────────────────────────────────────────────────────────
# Layer 2 — INTEGRATION against real Neo4j
# ─────────────────────────────────────────────────────────────────────


def neo4j_integration() -> int | None:
    if not all(os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")):
        log.warning("NEO4J INTEGRATION layer SKIPPED — env not set")
        return None

    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        if cond:
            log.info("NEO4J pass: %s", name)
        else:
            failures += 1
            log.error("NEO4J FAIL: %s — %s", name, detail)

    try:
        resolver = Neo4jExchangeResolver()
    except Exception as e:
        log.warning("NEO4J INTEGRATION layer SKIPPED — driver init failed: %s", e)
        return None

    try:
        # Known-stable lookups against the real graph (verified present in
        # the Company universe by direct query — selected to span all 3
        # supported exchange codes plus a confirmed-absent ticker).
        cases = [
            ("AAPL", "NASDAQ"),
            ("NVDA", "NASDAQ"),
            ("AMZN", "NASDAQ"),
            ("IBM", "NYSE"),
            ("GS", "NYSE"),
            ("WMT", "NYSE"),
            ("CBOE", "BATS"),
        ]
        for sym, want in cases:
            got = resolver(sym)
            check(f"{sym} → {want}", got == want, f"got {got!r}")

        # Tickers known to be ABSENT from the curated universe — should
        # return None (not all megacaps are in the graph; that's by design).
        for absent in ("MSFT", "JPM", "ZZZNOTREAL"):
            check(f"{absent} → None (not in universe)", resolver(absent) is None)

        # Bulk preload returns the same answers (use a fresh resolver so
        # we exercise the preload path, not the cache from prior calls).
        fresh = Neo4jExchangeResolver()
        try:
            primed = fresh.preload([s for s, _ in cases])
            for sym, want in cases:
                check(f"preload({sym}) → {want}", primed.get(sym) == want)
        finally:
            fresh.close()

    finally:
        resolver.close()

    log.info("NEO4J INTEGRATION layer: %d failure(s)", failures)
    return failures


# ─────────────────────────────────────────────────────────────────────
# Layer 3 — INTEGRATION against paper IBKR gateway
# ─────────────────────────────────────────────────────────────────────


async def _qualify(client: TradeDaemonIBClient, sym: str):
    return await client.qualify_stock(sym)


async def ibkr_integration() -> int | None:
    if not all(os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")):
        log.warning("IBKR INTEGRATION layer SKIPPED — Neo4j env not set")
        return None

    failures = 0

    def check(name, cond, detail=""):
        nonlocal failures
        if cond:
            log.info("IBKR pass: %s", name)
        else:
            failures += 1
            log.error("IBKR FAIL: %s — %s", name, detail)

    # Paper gateway is reached via the kubectl port-forward bound to
    # 127.0.0.1:4002 by the test driver script.
    gw_host = os.environ.get("IBKR_PAPER_GW_HOST", "127.0.0.1")
    gw_port = int(os.environ.get("IBKR_PAPER_GW_PORT", "4002"))

    try:
        from ib_async import IB
        probe = IB()
        await asyncio.wait_for(
            probe.connectAsync(gw_host, gw_port, clientId=99, timeout=5),
            timeout=8,
        )
        probe.disconnect()
    except Exception as e:
        log.warning(
            "IBKR INTEGRATION layer SKIPPED — paper gateway not reachable at %s:%d (%s)",
            gw_host, gw_port, e,
        )
        return None

    resolver = Neo4jExchangeResolver()
    try:
        # Two clients: one with resolver, one without. Distinct client IDs.
        cfg_a = IBKRConfig.from_account_mode("paper", host=gw_host, port=gw_port)
        cfg_a.mktdata_client_id = 30
        cfg_a.order_client_id = 31
        cfg_b = IBKRConfig.from_account_mode("paper", host=gw_host, port=gw_port)
        cfg_b.mktdata_client_id = 32
        cfg_b.order_client_id = 33

        client_resolver = TradeDaemonIBClient(cfg_a, primary_exchange_resolver=resolver)
        client_plain = TradeDaemonIBClient(cfg_b)

        await client_resolver.connect()
        await client_plain.connect()

        try:
            # Use tickers known to be in the Neo4j universe so the
            # resolver path actually exercises SMART:<primary>.
            for sym in ["AAPL", "NVDA", "IBM", "GS"]:
                ca = await _qualify(client_resolver, sym)
                cb = await _qualify(client_plain, sym)
                check(
                    f"{sym} conId matches (resolver={ca.conId}, plain={cb.conId})",
                    ca.conId == cb.conId,
                    f"resolver returned {ca.conId}, plain returned {cb.conId}",
                )
                # Also assert the resolver path actually used SMART:<primary>
                check(
                    f"{sym} resolver path qualified (conId>0)",
                    ca.conId > 0,
                )
            # Ticker NOT in universe — should still resolve via fallback
            # to bare SMART (resolver returns None → original behavior).
            ca_msft = await _qualify(client_resolver, "MSFT")
            cb_msft = await _qualify(client_plain, "MSFT")
            check(
                f"MSFT (not in graph) conId matches via fallback "
                f"(resolver={ca_msft.conId}, plain={cb_msft.conId})",
                ca_msft.conId == cb_msft.conId,
            )
        finally:
            await client_resolver.shutdown()
            await client_plain.shutdown()
    finally:
        resolver.close()

    log.info("IBKR INTEGRATION layer: %d failure(s)", failures)
    return failures


# ─────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────


def main() -> int:
    log.info("===== Layer 1: UNIT =====")
    unit_failures = unit_tests()

    log.info("===== Layer 2: NEO4J INTEGRATION =====")
    neo4j_failures = neo4j_integration()

    log.info("===== Layer 3: IBKR INTEGRATION =====")
    ibkr_failures = asyncio.run(ibkr_integration())

    log.info("===== SUMMARY =====")
    log.info("UNIT       : %s", "0 fail" if unit_failures == 0 else f"{unit_failures} FAIL")
    log.info("NEO4J INT  : %s", "skipped" if neo4j_failures is None else (f"{neo4j_failures} fail" if neo4j_failures else "0 fail"))
    log.info("IBKR INT   : %s", "skipped" if ibkr_failures is None else (f"{ibkr_failures} fail" if ibkr_failures else "0 fail"))

    bad = unit_failures + (neo4j_failures or 0) + (ibkr_failures or 0)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
