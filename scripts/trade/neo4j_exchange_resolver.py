"""Neo4j-backed primary exchange resolver for the trade daemon.

Looks up a US-equity ticker's primary listing exchange in Neo4j and returns
the IBKR-compatible name (NASDAQ / NYSE / BATS). When the ticker is unknown
to Neo4j, or Neo4j is unreachable, returns None — callers fall back to bare
"SMART" (existing behavior) instead of failing.

No per-ticker mapping is hardcoded. The only static table is the 4-entry
short-code translation Neo4j stores (NAS/NYS/BATS) → IBKR primary names.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from neo4j import GraphDatabase

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger("trade_daemon.neo4j_resolver")

# Neo4j stores abbreviated exchange codes for US listings.
# This is structural translation, not a per-ticker table.
_NEO4J_TO_IBKR: dict[str, str] = {
    "NAS": "NASDAQ",
    "NYS": "NYSE",
    "BATS": "BATS",
    # TSE intentionally omitted — Toronto-listed names are not routed via
    # the live/paper US gateways; resolver returns None for them and the
    # caller falls back to bare SMART.
}

# Sentinel cache value for "looked up, not found" so we don't re-query.
_MISS = object()


class Neo4jExchangeResolver:
    """Callable that maps ticker → IBKR primary exchange via Neo4j.

    Designed to be passed as `primary_exchange_resolver` to
    `TradeDaemonIBClient`. Implements `__call__(symbol) -> str | None`.

    Caches per-symbol results forever (process lifetime). Cache is
    populated on first lookup; subsequent lookups are O(1) in-memory.

    Failure modes (all fall back to None → bare SMART):
      - Neo4j unreachable → log warning, cache None for this call only
      - Ticker not in Company nodes → cache None permanently
      - Neo4j ticker has exchange not in {NAS,NYS,BATS} → cache None
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        *,
        driver: "Driver | None" = None,
    ) -> None:
        """Construct the resolver.

        Args:
            uri/user/password: Neo4j connection params. Default to
                NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD env vars.
            driver: Inject an already-constructed neo4j Driver (useful
                for tests). When supplied, uri/user/password are ignored
                and the resolver does not own the driver lifecycle —
                caller is responsible for closing it.
        """
        self._owns_driver = driver is None
        if driver is not None:
            self._driver = driver
        else:
            uri = uri or os.environ.get("NEO4J_URI")
            user = user or os.environ.get("NEO4J_USERNAME")
            password = password or os.environ.get("NEO4J_PASSWORD")
            if not (uri and user and password):
                msg = (
                    "Neo4jExchangeResolver requires NEO4J_URI / NEO4J_USERNAME"
                    " / NEO4J_PASSWORD (env or args) when no driver is injected"
                )
                raise ValueError(msg)
            self._driver = GraphDatabase.driver(uri, auth=(user, password))

        # symbol -> primary exchange string OR _MISS sentinel for "not in graph"
        self._cache: dict[str, str | object] = {}

    def __call__(self, symbol: str) -> str | None:
        """Resolve a ticker to its IBKR primary exchange, or None."""
        key = symbol.upper()
        cached = self._cache.get(key)
        if cached is _MISS:
            return None
        if cached is not None:
            # cached non-None must be a string
            return cached  # type: ignore[return-value]

        try:
            with self._driver.session() as s:
                rec = s.run(
                    "MATCH (c:Company {ticker:$sym}) RETURN c.exchange AS ex",
                    sym=key,
                ).single()
            neo_ex = rec["ex"] if rec else None
            primary = _NEO4J_TO_IBKR.get(neo_ex) if neo_ex else None
        except Exception as e:
            # Don't poison the cache on transient Neo4j failure — leave
            # the symbol uncached so a later lookup can succeed.
            logger.warning(
                "Neo4j lookup failed for %s: %s — falling back to SMART",
                key, e,
            )
            return None

        self._cache[key] = primary if primary is not None else _MISS
        return primary

    def preload(self, symbols: list[str]) -> dict[str, str | None]:
        """Bulk-prime the cache for a list of symbols.

        Use this at daemon startup when the universe is known upfront,
        to avoid per-symbol latency on first lookup. Returns the
        resolved-or-None map for each requested symbol.

        Safe on Neo4j failure — symbols that fail to load remain
        uncached and will be retried lazily on first __call__.
        """
        if not symbols:
            return {}
        normalized = sorted({s.upper() for s in symbols})
        result: dict[str, str | None] = {}
        try:
            with self._driver.session() as s:
                rows = s.run(
                    "UNWIND $syms AS sym "
                    "MATCH (c:Company {ticker: sym}) "
                    "RETURN c.ticker AS ticker, c.exchange AS ex",
                    syms=normalized,
                ).data()
        except Exception as e:
            logger.warning(
                "Neo4j preload failed: %s — symbols will be looked up lazily",
                e,
            )
            return {s: None for s in normalized}

        found: dict[str, str | None] = {}
        for r in rows:
            primary = _NEO4J_TO_IBKR.get(r["ex"]) if r["ex"] else None
            found[r["ticker"]] = primary
        for sym in normalized:
            primary = found.get(sym)
            self._cache[sym] = primary if primary is not None else _MISS
            result[sym] = primary
        return result

    def close(self) -> None:
        """Close the underlying Neo4j driver if we own it."""
        if self._owns_driver:
            self._driver.close()

    def __enter__(self) -> "Neo4jExchangeResolver":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
