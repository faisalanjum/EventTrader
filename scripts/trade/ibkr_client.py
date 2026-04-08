"""Isolated IBKR client for the trade daemon.

Adapted from ibkr-mcp-server/app/services/ patterns (client.py, orders.py,
market_data.py, account.py, positions.py). Does NOT import from or modify the
running MCP server code.

Uses separate clientIds (20/21) to avoid session collisions with the MCP server
(10/1). Connects directly to the IBKR Gateway — no MCP HTTP layer.

Isolation rule (Appendix A0):
  - This module is a COPY/ADAPTATION of MCP server patterns
  - The running MCP services are never touched
  - IBKR Gateway supports multiple simultaneous clients
"""

from __future__ import annotations

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Any

from ib_async import IB, LimitOrder, MarketOrder, Order, StopOrder, Trade, util
from ib_async.contract import Contract

logger = logging.getLogger("trade_daemon.ibkr")

# ── Sentinel values from ib_async ──────────────────────────────────────────
_UNSET_DOUBLE = 1.7976931348623157e308
_UNSET_INT = 2147483647

# ── Default tick sizes by price range (US equities) ────────────────────────
# IBKR/exchanges enforce minimum price increments. These are the standard
# US equity tick sizes. For exact per-contract ticks, use contract.minTick
# after qualification (more precise but requires an extra round-trip).
_US_EQUITY_TICK_RULES: list[tuple[float, float]] = [
    # (price_below, tick_size)
    (1.0, 0.0001),
    (float("inf"), 0.01),
]


def _tick_size_for_price(price: float, min_tick: float | None = None) -> float:
    """Return the valid tick size for a given price.

    If min_tick is provided (from a qualified contract), use it directly.
    Otherwise, fall back to standard US equity rules.
    """
    if min_tick and min_tick > 0:
        return min_tick
    for threshold, tick in _US_EQUITY_TICK_RULES:
        if price < threshold:
            return tick
    return 0.01


def round_to_tick(price: float, tick: float) -> float:
    """Round a price to the nearest valid tick increment."""
    if tick <= 0:
        return round(price, 2)
    return round(round(price / tick) * tick, 10)


@dataclass
class QuoteSnapshot:
    """Snapshot of current market data for a symbol."""
    symbol: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    close: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None

    @property
    def spread(self) -> float | None:
        if self.bid is not None and self.ask is not None and self.bid > 0:
            return self.ask - self.bid
        return None

    @property
    def spread_pct(self) -> float | None:
        if self.spread is not None and self.mid is not None and self.mid > 0:
            return (self.spread / self.mid) * 100
        return None

    @property
    def mid(self) -> float | None:
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return None


@dataclass
class OrderResult:
    """Result of an order placement."""
    order_id: int
    perm_id: int
    client_id: int
    symbol: str
    con_id: int | None
    action: str
    order_type: str
    quantity: float
    limit_price: float | None
    stop_price: float | None
    status: str
    filled: float
    remaining: float
    avg_fill_price: float
    parent_id: int
    oca_group: str | None


@dataclass
class AccountSummary:
    """Key account metrics."""
    net_liquidation: float = 0.0
    total_cash: float = 0.0
    buying_power: float = 0.0
    available_funds: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    gross_position_value: float = 0.0


@dataclass
class Position:
    """A held position."""
    symbol: str
    con_id: int
    quantity: float
    avg_cost: float
    market_value: float = 0.0


@dataclass
class BracketPlacementResult:
    """Result of a 2-leg bracket order (entry + stop).

    The CLIENT reports status. The DAEMON decides what to do.
    """
    status: str  # "filled", "filled_stop_inactive", "partial_fill", "timeout_no_fill", "entry_rejected"
    entry: OrderResult
    stop: OrderResult
    filled_quantity: float
    intended_quantity: int
    stop_active: bool
    message: str

    @property
    def needs_flatten(self) -> bool:
        """True if the daemon should immediately flatten (fail-closed).

        This means: we HAVE shares but NO stop protection.
        """
        return self.filled_quantity > 0 and not self.stop_active

    @property
    def needs_stop_qty_adjustment(self) -> bool:
        """True if stop quantity doesn't match filled quantity (partial fill).

        Daemon must: (1) cancel unfilled parent remainder, (2) adjust stop qty.
        """
        return (self.status == "partial_fill"
                and self.stop_active
                and self.filled_quantity != self.intended_quantity)

    @property
    def needs_bracket_cancellation(self) -> bool:
        """True if the entire bracket should be cancelled (no fills achieved)."""
        return self.filled_quantity == 0 and self.status in ("timeout_no_fill", "entry_rejected")

    @property
    def needs_parent_remainder_cancel(self) -> bool:
        """True if parent order has unfilled remainder that must be cancelled.

        On partial fill: we have some shares, but the parent is still working
        on the rest. Daemon must cancel the remainder before adjusting the stop
        to match the actual filled quantity.
        """
        return self.status == "partial_fill" and self.filled_quantity < self.intended_quantity

    @property
    def is_fully_protected(self) -> bool:
        """True if position is fully filled AND stop is confirmed active."""
        return self.status == "filled" and self.stop_active


@dataclass
class IBKRConfig:
    """IBKR connection configuration for the trade daemon."""
    host: str = "ibkr-paper-gateway"
    port: int = 4004
    mktdata_client_id: int = 20
    order_client_id: int = 21
    data_mode: str = "delayed"  # "delayed" or "realtime"
    limit_buffer_pct: float = 0.15  # 0.15% buffer for marketable limits
    order_timeout_sec: float = 60.0
    connect_timeout_sec: float = 20.0
    heartbeat_interval_sec: float = 30.0

    @classmethod
    def from_account_mode(
        cls, account_mode: str, data_mode: str = "delayed", **overrides
    ) -> IBKRConfig:
        """Create config for paper or live mode."""
        if account_mode == "paper":
            defaults = dict(
                host="ibkr-paper-gateway",
                port=4004,
                mktdata_client_id=20,
                order_client_id=21,
                data_mode=data_mode,
            )
        elif account_mode == "live":
            defaults = dict(
                host="ibkr-ib-gateway",  # matches K8s service name
                port=4003,
                mktdata_client_id=22,
                order_client_id=23,
                data_mode=data_mode,
            )
        else:
            raise ValueError(f"Unknown account_mode: {account_mode!r}. Use 'paper' or 'live'.")
        defaults.update(overrides)
        return cls(**defaults)

    @property
    def is_realtime(self) -> bool:
        return self.data_mode == "realtime"


class TradeDaemonIBClient:
    """Isolated IBKR client for the trade daemon.

    Two separate IB connections (same pattern as MCP server):
      - mktdata connection (clientId=20): quotes, account, positions
      - order connection (clientId=21): order placement and management

    Separate connections ensure order tracking survives market-data reconnects
    and vice versa.
    """

    def __init__(self, config: IBKRConfig) -> None:
        self.config = config

        # Market data connection
        self._mktdata_ib = IB()
        self._mktdata_ib.disconnectedEvent += self._on_mktdata_disconnected

        # Order connection (separate, like MCP server pattern)
        self._order_ib = IB()
        self._order_ib.disconnectedEvent += self._on_order_disconnected

        # Shared state
        self._contract_cache: dict[str, Contract] = {}
        self._mktdata_reconnect_lock = asyncio.Lock()
        self._order_reconnect_lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None
        self._shutting_down = False
        self._connected = False
        self._last_on_update_callback: callable | None = None
        self._streaming_subscriptions: dict[str, tuple[Contract, Any]] = {}

    # ── Connection ──────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect both market data and order clients."""
        await self._connect_mktdata()
        await self._connect_orders()
        await self._start_heartbeat()
        self._connected = True
        logger.info(
            "Trade daemon connected to IBKR Gateway %s:%d (mktdata=%d, orders=%d)",
            self.config.host, self.config.port,
            self.config.mktdata_client_id, self.config.order_client_id,
        )

    async def _connect_mktdata(self) -> None:
        if self._mktdata_ib.isConnected():
            return
        async with self._mktdata_reconnect_lock:
            if self._mktdata_ib.isConnected():
                return
            await self._connect_with_backoff(
                self._mktdata_ib,
                self.config.mktdata_client_id,
                "mktdata",
            )

    async def _connect_orders(self) -> None:
        if self._order_ib.isConnected():
            return
        async with self._order_reconnect_lock:
            if self._order_ib.isConnected():
                return
            await self._connect_with_backoff(
                self._order_ib,
                self.config.order_client_id,
                "orders",
            )

    async def _connect_with_backoff(
        self, ib: IB, client_id: int, label: str
    ) -> None:
        """Connect with exponential backoff. Adapted from MCP client.py."""
        delays = [1, 2, 5, 10, 30]
        for attempt, delay in enumerate(delays, 1):
            try:
                if attempt > 1:
                    await asyncio.sleep(delay)
                if hasattr(util.getLoop, "cache_clear"):
                    util.getLoop.cache_clear()
                if ib.isConnected():
                    ib.disconnect()
                await ib.connectAsync(
                    host=self.config.host,
                    port=self.config.port,
                    clientId=client_id,
                    timeout=self.config.connect_timeout_sec,
                    readonly=False,
                )
                ib.RequestTimeout = self.config.connect_timeout_sec
                logger.info(
                    "[%s] Connected to IBKR (clientId=%d, attempt=%d)",
                    label, client_id, attempt,
                )
                return
            except Exception as e:
                logger.warning(
                    "[%s] Connect attempt %d/%d failed: %s",
                    label, attempt, len(delays), e,
                )

        # Final attempt after 60s
        logger.error("[%s] All attempts failed. Waiting 60s for final try...", label)
        await asyncio.sleep(60)
        try:
            if hasattr(util.getLoop, "cache_clear"):
                util.getLoop.cache_clear()
            if ib.isConnected():
                ib.disconnect()
            await ib.connectAsync(
                host=self.config.host,
                port=self.config.port,
                clientId=client_id,
                timeout=self.config.connect_timeout_sec,
                readonly=False,
            )
            ib.RequestTimeout = self.config.connect_timeout_sec
            logger.info("[%s] Connected on final attempt", label)
        except Exception as e:
            raise ConnectionError(
                f"[{label}] Failed to connect to IBKR Gateway "
                f"{self.config.host}:{self.config.port} (clientId={client_id}): {e}"
            ) from e

    def _on_mktdata_disconnected(self) -> None:
        if self._shutting_down:
            return
        logger.warning("Market data connection lost — scheduling reconnect + resubscribe")
        self._contract_cache.clear()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._reconnect_and_resubscribe())
        except RuntimeError:
            logger.error("No event loop for mktdata reconnect")

    async def _reconnect_and_resubscribe(self) -> None:
        """Reconnect market data and restore streaming subscriptions."""
        await self._connect_mktdata()
        if self._mktdata_ib.isConnected() and hasattr(self, '_streaming_subscriptions') and self._streaming_subscriptions:
            logger.info("Restoring %d streaming subscriptions after reconnect", len(self._streaming_subscriptions))
            try:
                await self.resubscribe_all(on_update=self._last_on_update_callback)
                logger.info("Streaming subscriptions restored successfully")
            except Exception as e:
                logger.error("Failed to restore streaming subscriptions: %s", e)

    def _on_order_disconnected(self) -> None:
        if self._shutting_down:
            return
        logger.warning("Order connection lost — will reconnect on next order")

    # ── Heartbeat ───────────────────────────────────────────────────────

    async def _start_heartbeat(self) -> None:
        if self._heartbeat_task is not None:
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Ping gateway every N seconds. Auto-heals dead connections."""
        while not self._shutting_down:
            await asyncio.sleep(self.config.heartbeat_interval_sec)

            # Market data heartbeat
            if not self._mktdata_ib.isConnected():
                logger.info("Heartbeat: mktdata disconnected — reconnecting")
                await self._connect_mktdata()
            else:
                try:
                    await asyncio.wait_for(
                        self._mktdata_ib.reqCurrentTimeAsync(), timeout=10
                    )
                except Exception as e:
                    logger.warning("Heartbeat mktdata failed: %s — disconnecting", e)
                    self._mktdata_ib.disconnect()

            # Order client heartbeat
            if not self._order_ib.isConnected():
                logger.info("Heartbeat: orders disconnected — reconnecting")
                await self._connect_orders()
            else:
                try:
                    await asyncio.wait_for(
                        self._order_ib.reqCurrentTimeAsync(), timeout=10
                    )
                except Exception as e:
                    logger.warning("Heartbeat orders failed: %s — disconnecting", e)
                    self._order_ib.disconnect()

    # ── Contracts ───────────────────────────────────────────────────────

    async def qualify_stock(self, symbol: str) -> Contract:
        """Qualify a US equity contract. Cached to avoid redundant round-trips."""
        key = symbol.upper()
        if key not in self._contract_cache:
            await self._connect_mktdata()
            contract = Contract(
                symbol=key, secType="STK", exchange="SMART", currency="USD"
            )
            [qualified] = await self._mktdata_ib.qualifyContractsAsync(contract)
            self._contract_cache[key] = qualified
            logger.debug(
                "Qualified %s → conId=%d minTick=%s",
                key, qualified.conId, getattr(qualified, "minTick", "?"),
            )
        return self._contract_cache[key]

    def get_min_tick(self, contract: Contract) -> float | None:
        """Get the minimum tick size from a qualified contract, if available."""
        mt = getattr(contract, "minTick", None)
        if mt and mt > 0 and mt < _UNSET_DOUBLE * 0.9:
            return mt
        return None

    # ── Market Data (snapshot / delayed mode) ───────────────────────────

    async def get_quote(self, symbol: str) -> QuoteSnapshot:
        """Get a snapshot quote for a symbol. Works in both live and delayed mode."""
        await self._connect_mktdata()
        contract = await self.qualify_stock(symbol)

        # DATA_MODE controls market data type, NOT market hours.
        # Realtime must always use type 1 — including extended hours (post/pre-market)
        # where most earnings trade. Delayed uses type 4 (delayed-frozen snapshot).
        if self.config.is_realtime:
            self._mktdata_ib.reqMarketDataType(1)  # live (all hours)
        else:
            self._mktdata_ib.reqMarketDataType(4)  # delayed-frozen

        tickers = await self._mktdata_ib.reqTickersAsync(contract)
        if not tickers:
            raise ValueError(f"No quote data for {symbol}")

        t = tickers[0]
        return QuoteSnapshot(
            symbol=symbol,
            bid=_clean_price(t.bid),
            ask=_clean_price(t.ask),
            last=_clean_price(t.last),
            close=_clean_price(t.close),
            high=_clean_price(t.high),
            low=_clean_price(t.low),
            volume=t.volume if t.volume and t.volume > 0 else None,
        )

    async def get_account_summary(self) -> AccountSummary:
        """Get key account metrics."""
        await self._connect_mktdata()
        values = self._mktdata_ib.accountValues()
        summary = AccountSummary()
        tag_map = {
            "NetLiquidation": "net_liquidation",
            "TotalCashValue": "total_cash",
            "BuyingPower": "buying_power",
            "AvailableFunds": "available_funds",
            "UnrealizedPnL": "unrealized_pnl",
            "RealizedPnL": "realized_pnl",
            "GrossPositionValue": "gross_position_value",
        }
        for av in values:
            if av.tag in tag_map:
                # Accept the account's base currency (may be USD or CAD)
                # Skip per-currency duplicates — take the first (base currency) match
                current = getattr(summary, tag_map[av.tag])
                if current == 0.0:
                    try:
                        setattr(summary, tag_map[av.tag], float(av.value))
                    except (ValueError, TypeError):
                        pass
        return summary

    async def get_positions(self) -> list[Position]:
        """Get all held positions."""
        await self._connect_mktdata()
        positions = self._mktdata_ib.positions()
        result = []
        for p in positions:
            try:
                multiplier = float(p.contract.multiplier or 1)
            except (ValueError, TypeError, AttributeError):
                multiplier = 1.0
            result.append(Position(
                symbol=p.contract.localSymbol or p.contract.symbol,
                con_id=p.contract.conId,
                quantity=float(p.position),
                avg_cost=p.avgCost / multiplier,
                market_value=float(p.position) * (p.avgCost / multiplier),
            ))
        return result

    # ── Streaming Market Data (realtime mode) ─────────────────────────

    async def subscribe_quotes(
        self,
        symbols: list[str],
        on_update: callable | None = None,
    ) -> dict[str, Any]:
        """Subscribe to streaming market data for multiple symbols.

        Uses reqMktData (persistent subscription, NOT snapshot).
        Each quote update fires the on_update callback with (symbol, ticker).

        Args:
            symbols: list of ticker symbols to subscribe to
            on_update: callback(symbol: str, ticker) called on each update

        Returns:
            dict mapping symbol → ib_async Ticker object (for threshold checking)
        """
        await self._connect_mktdata()

        # DATA_MODE controls market data type, NOT market hours.
        # Realtime always uses type 1 (live, including extended hours).
        # Delayed uses type 3 (delayed streaming).
        if self.config.is_realtime:
            self._mktdata_ib.reqMarketDataType(1)  # live streaming (all hours)
        else:
            self._mktdata_ib.reqMarketDataType(3)  # delayed streaming

        # Save callback for reconnect-resubscribe
        if on_update:
            self._last_on_update_callback = on_update

        subscriptions: dict[str, Any] = {}
        for symbol in symbols:
            contract = await self.qualify_stock(symbol)
            # reqMktData with snapshot=False → persistent streaming subscription
            ticker = self._mktdata_ib.reqMktData(
                contract,
                genericTickList="",
                snapshot=False,
                regulatorySnapshot=False,
            )
            subscriptions[symbol.upper()] = ticker

            # Per-ticker callback: fires on each price update
            if on_update:
                sym = symbol.upper()  # capture for closure
                ticker.updateEvent += lambda t, s=sym: on_update(s, t)

            logger.info("Subscribed to streaming quotes for %s (reqId=%s)", symbol, ticker.reqId if hasattr(ticker, 'reqId') else '?')

        # Store subscriptions for cleanup and reconnect-resubscribe
        for symbol in symbols:
            key = symbol.upper()
            self._streaming_subscriptions[key] = (
                self._contract_cache[key],
                subscriptions[key],
            )

        return subscriptions

    async def unsubscribe_quotes(self, symbols: list[str] | None = None) -> None:
        """Unsubscribe from streaming market data.

        Args:
            symbols: specific symbols to unsubscribe, or None for all.
        """
        if not hasattr(self, '_streaming_subscriptions'):
            return

        targets = symbols or list(self._streaming_subscriptions.keys())
        for symbol in targets:
            key = symbol.upper()
            if key in self._streaming_subscriptions:
                contract, ticker = self._streaming_subscriptions[key]
                try:
                    self._mktdata_ib.cancelMktData(contract)
                    logger.info("Unsubscribed from streaming quotes for %s", key)
                except Exception as e:
                    logger.warning("Error unsubscribing %s: %s", key, e)
                del self._streaming_subscriptions[key]

    async def resubscribe_all(self, on_update: callable | None = None) -> dict[str, Any]:
        """Re-establish all streaming subscriptions (after reconnect).

        Returns new ticker objects for threshold re-registration.
        """
        if not hasattr(self, '_streaming_subscriptions') or not self._streaming_subscriptions:
            return {}

        symbols = list(self._streaming_subscriptions.keys())
        # Clear old subscriptions (contracts are stale after reconnect)
        self._streaming_subscriptions.clear()
        # Re-subscribe
        return await self.subscribe_quotes(symbols, on_update)

    @property
    def streaming_symbols(self) -> list[str]:
        """List of symbols currently subscribed to streaming data."""
        if not hasattr(self, '_streaming_subscriptions'):
            return []
        return list(self._streaming_subscriptions.keys())

    # ── Orders ──────────────────────────────────────────────────────────

    async def place_marketable_limit(
        self,
        symbol: str,
        action: str,
        quantity: int,
        reference_price: float,
    ) -> OrderResult:
        """Place a marketable limit order (side-aware, tick-aware).

        BUY:  limit = ask + max(1 tick, ask × LIMIT_BUFFER_PCT)
        SELL: limit = bid - max(1 tick, bid × LIMIT_BUFFER_PCT)

        The reference_price should be the current ask (for BUY) or bid (for SELL).
        """
        await self._connect_orders()
        contract = await self._qualify_for_orders(symbol)
        min_tick = self.get_min_tick(contract)
        tick = _tick_size_for_price(reference_price, min_tick)
        buffer = max(tick, reference_price * (self.config.limit_buffer_pct / 100))

        if action.upper() == "BUY":
            limit_price = reference_price + buffer
        else:
            limit_price = reference_price - buffer

        limit_price = round_to_tick(limit_price, tick)

        order = LimitOrder(action.upper(), quantity, limit_price)
        order.tif = "DAY"
        order.outsideRth = True  # allow extended hours

        trade = self._order_ib.placeOrder(contract, order)
        await self._wait_for_status(trade)
        return _trade_to_result(trade)

    async def place_market_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
    ) -> OrderResult:
        """Place a market order. USE ONLY FOR EMERGENCIES (kill-switch, flatten)."""
        await self._connect_orders()
        contract = await self._qualify_for_orders(symbol)

        order = MarketOrder(action.upper(), quantity)
        order.tif = "DAY"
        order.outsideRth = True

        trade = self._order_ib.placeOrder(contract, order)
        await self._wait_for_status(trade)
        return _trade_to_result(trade)

    async def place_entry_with_stop(
        self,
        symbol: str,
        action: str,
        quantity: int,
        limit_price: float,
        stop_price: float,
        fill_timeout: float | None = None,
    ) -> "BracketPlacementResult":
        """Place a 2-leg bracket: entry (marketable limit) + stop-loss.

        No take-profit leg — "let winners run" per plan.

        Production safety features:
        - Waits for parent fill (with timeout)
        - Verifies stop becomes active after parent fills
        - Reports partial fills with actual filled quantity
        - Returns clear status for daemon to act on (including fail-closed scenarios)

        The CLIENT reports status. The DAEMON decides what to do (e.g., flatten).
        """
        fill_timeout = fill_timeout or self.config.order_timeout_sec
        await self._connect_orders()
        contract = await self._qualify_for_orders(symbol)
        min_tick = self.get_min_tick(contract)
        tick = _tick_size_for_price(limit_price, min_tick)

        # Round prices to valid ticks
        limit_price = round_to_tick(limit_price, tick)
        stop_price = round_to_tick(stop_price, tick)

        # Determine exit action (opposite of entry)
        exit_action = "SELL" if action.upper() == "BUY" else "BUY"

        # Build 2-leg bracket manually (existing bracketOrder is 3-leg)
        parent_id = self._order_ib.client.getReqId()
        stop_id = self._order_ib.client.getReqId()

        # Parent: entry order (marketable limit)
        parent = LimitOrder(action.upper(), quantity, limit_price)
        parent.orderId = parent_id
        parent.tif = "DAY"
        parent.outsideRth = True
        parent.transmit = False  # don't send until child is attached

        # Child: stop-loss (attached to parent via parentId)
        stop = StopOrder(exit_action, quantity, stop_price)
        stop.orderId = stop_id
        stop.parentId = parent_id
        stop.tif = "GTC"  # stop stays active until triggered or cancelled
        stop.outsideRth = True
        stop.transmit = True  # transmit the whole bracket

        # Place both
        parent_trade = self._order_ib.placeOrder(contract, parent)
        stop_trade = self._order_ib.placeOrder(contract, stop)

        # Wait for parent to reach a terminal-ish state
        await self._wait_for_fill(parent_trade, timeout=fill_timeout)

        parent_result = _trade_to_result(parent_trade)
        stop_result = _trade_to_result(stop_trade)

        # ── Determine outcome ──────────────────────────────────────
        # FIX 1: Check filled_qty FIRST. A partial fill that later becomes
        # Cancelled/Inactive still has real shares we must protect.
        # Never collapse filled shares into "entry_rejected" with qty=0.
        filled_qty = parent_result.filled
        parent_terminal = parent_result.status in ("Cancelled", "Inactive", "ApiCancelled", "Filled")

        # Case A: Zero fills
        if filled_qty == 0:
            status = "entry_rejected" if parent_terminal else "timeout_no_fill"
            return BracketPlacementResult(
                status=status,
                entry=parent_result,
                stop=stop_result,
                filled_quantity=0,
                intended_quantity=quantity,
                stop_active=False,
                # Daemon MUST cancel the entire bracket to clean up
                message=f"No fills ({parent_result.status}). "
                        f"Daemon must cancel bracket (parent={parent_id}, stop={stop_id}).",
            )

        # Case B: Some shares filled (partial or full) — verify stop is active.
        # FIX 2: Poll for stop activation with bounded window, not fixed sleep.
        stop_is_active = False
        for _ in range(10):  # poll up to 5 seconds (10 × 0.5s)
            await asyncio.sleep(0.5)
            stop_is_active = stop_trade.orderStatus.status in ("PreSubmitted", "Submitted")
            if stop_is_active:
                break

        # Refresh results after polling
        parent_result = _trade_to_result(parent_trade)
        stop_result = _trade_to_result(stop_trade)
        filled_qty = parent_result.filled  # may have increased during poll
        is_partial = 0 < filled_qty < quantity

        # FIX 3: Explicitly define remainder behavior for daemon.
        if is_partial:
            return BracketPlacementResult(
                status="partial_fill",
                entry=parent_result,
                stop=stop_result,
                filled_quantity=filled_qty,
                intended_quantity=quantity,
                stop_active=stop_is_active,
                # Explicit daemon instructions:
                message=f"Partial fill: {filled_qty}/{quantity} shares. "
                        f"Stop {'active' if stop_is_active else 'NOT ACTIVE'}. "
                        f"Daemon MUST: (1) cancel unfilled parent remainder, "
                        f"(2) {'adjust stop qty to {}'.format(int(filled_qty)) if stop_is_active else 'FLATTEN immediately — no stop protection'}, "
                        f"(3) proceed with {int(filled_qty)} shares.",
            )

        # Full fill
        return BracketPlacementResult(
            status="filled" if stop_is_active else "filled_stop_inactive",
            entry=parent_result,
            stop=stop_result,
            filled_quantity=filled_qty,
            intended_quantity=quantity,
            stop_active=stop_is_active,
            message="Entry filled, stop active — fully protected"
                    if stop_is_active
                    else "Entry filled but stop NOT ACTIVE — daemon MUST flatten immediately",
        )

    async def modify_stop_quantity(self, order_id: int, new_quantity: int) -> OrderResult | None:
        """Adjust stop order quantity (e.g., after partial fill).

        Returns updated order result, or None if order not found.
        """
        await self._connect_orders()
        trade = self._find_trade(order_id)
        if trade is None:
            logger.warning("Stop order %d not found for quantity adjustment", order_id)
            return None
        trade.order.totalQuantity = new_quantity
        self._order_ib.placeOrder(trade.contract, trade.order)
        await self._wait_for_status(trade, timeout=10)
        logger.info("Stop %d quantity adjusted to %d", order_id, new_quantity)
        return _trade_to_result(trade)

    async def flatten_position(self, symbol: str, quantity: int, action: str = "SELL") -> OrderResult:
        """Emergency flatten — market order to close a position immediately.

        Use when:
        - Stop placement/activation failed (fail-closed)
        - Stop repair failed during reconciliation
        - Account kill-switch triggered

        This is a MARKET ORDER — accepts any fill price for speed.
        """
        logger.warning(
            "FLATTEN: emergency %s %d %s at market", action, quantity, symbol
        )
        return await self.place_market_order(symbol, action, quantity)

    async def verify_stop_active(self, order_id: int) -> bool:
        """Check if a stop order is currently active (PreSubmitted or Submitted).

        Returns True if active, False otherwise.
        """
        await self._connect_orders()
        trade = self._find_trade(order_id)
        if trade is None:
            return False
        return trade.orderStatus.status in ("PreSubmitted", "Submitted")

    async def cancel_order(self, order_id: int) -> OrderResult | None:
        """Cancel an open order by ID."""
        await self._connect_orders()
        trade = self._find_trade(order_id)
        if trade is None:
            logger.warning("Order %d not found for cancellation", order_id)
            return None
        self._order_ib.cancelOrder(trade.order)
        await self._wait_for_status(trade)
        return _trade_to_result(trade)

    async def get_open_orders(self) -> list[OrderResult]:
        """Get all open orders for this client."""
        await self._connect_orders()
        return [_trade_to_result(t) for t in self._order_ib.openTrades()]

    async def get_order_status(self, order_id: int) -> OrderResult | None:
        """Get status of a specific order."""
        await self._connect_orders()
        trade = self._find_trade(order_id)
        if trade is None:
            return None
        return _trade_to_result(trade)

    # ── Internal helpers ────────────────────────────────────────────────

    async def _qualify_for_orders(self, symbol: str) -> Contract:
        """Qualify a contract using the ORDER connection (not mktdata).

        The order connection has its own contract cache to avoid cross-connection
        issues. Qualification results are cached for the session.
        """
        key = symbol.upper()
        # We reuse the mktdata cache since contract objects are portable
        if key in self._contract_cache:
            return self._contract_cache[key]
        contract = Contract(
            symbol=key, secType="STK", exchange="SMART", currency="USD"
        )
        [qualified] = await self._order_ib.qualifyContractsAsync(contract)
        self._contract_cache[key] = qualified
        return qualified

    async def _wait_for_status(self, trade: Trade, timeout: float | None = None) -> None:
        """Wait for trade status to change from initial state, or timeout."""
        timeout = timeout or self.config.order_timeout_sec
        deadline = asyncio.get_running_loop().time() + timeout
        initial = trade.orderStatus.status
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.1)
            current = trade.orderStatus.status
            if current != initial:
                return
            if current in ("Filled", "Cancelled", "Inactive", "ApiCancelled"):
                return

    async def _wait_for_fill(self, trade: Trade, timeout: float | None = None) -> None:
        """Wait for a trade to reach a fill-related terminal state.

        Terminal states: Filled, Cancelled, Inactive, ApiCancelled.
        Also returns on partial fill if remaining == 0 or status settles.

        More patient than _wait_for_status — designed for entry orders where
        we want to capture partial fills before timing out.
        """
        timeout = timeout or self.config.order_timeout_sec
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.2)
            status = trade.orderStatus.status
            filled = float(trade.orderStatus.filled)

            # Fully terminal
            if status in ("Filled", "Cancelled", "Inactive", "ApiCancelled"):
                return

            # Partial fill detected — give a bit more time for full fill
            if filled > 0 and status == "Submitted":
                # Wait up to 5 more seconds for remaining to fill
                partial_deadline = min(
                    deadline,
                    asyncio.get_running_loop().time() + 5.0,
                )
                while asyncio.get_running_loop().time() < partial_deadline:
                    await asyncio.sleep(0.2)
                    if trade.orderStatus.status == "Filled":
                        return
                # Partial fill is stable — return with what we have
                return

    def _find_trade(self, order_id: int) -> Trade | None:
        """Find an open trade by order ID."""
        for trade in self._order_ib.openTrades():
            if trade.order.orderId == order_id:
                return trade
        return None

    # ── Shutdown ────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Graceful shutdown — stop heartbeat and disconnect both clients."""
        self._shutting_down = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        for ib in (self._mktdata_ib, self._order_ib):
            if ib.isConnected():
                ib.disconnect()
        self._connected = False
        logger.info("Trade daemon IBKR client shut down")

    @property
    def is_connected(self) -> bool:
        return self._mktdata_ib.isConnected() and self._order_ib.isConnected()

    @property
    def is_mktdata_connected(self) -> bool:
        return self._mktdata_ib.isConnected()

    @property
    def is_orders_connected(self) -> bool:
        return self._order_ib.isConnected()


# ── Utility functions ──────────────────────────────────────────────────────


def _clean_price(val: float | None) -> float | None:
    """Convert ib_async UNSET sentinel or NaN to None."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or val >= _UNSET_DOUBLE * 0.9):
        return None
    if val <= 0:
        return None
    return val


def _trade_to_result(trade: Trade) -> OrderResult:
    """Convert an ib_async Trade to our OrderResult dataclass."""
    return OrderResult(
        order_id=trade.order.orderId,
        perm_id=trade.order.permId,
        client_id=trade.order.clientId,
        symbol=trade.contract.symbol if trade.contract else "",
        con_id=trade.contract.conId if trade.contract else None,
        action=trade.order.action,
        order_type=trade.order.orderType,
        quantity=float(trade.order.totalQuantity),
        limit_price=_clean_order_price(trade.order.lmtPrice),
        stop_price=_clean_order_price(trade.order.auxPrice),
        status=trade.orderStatus.status,
        filled=float(trade.orderStatus.filled),
        remaining=float(trade.orderStatus.remaining),
        avg_fill_price=float(trade.orderStatus.avgFillPrice),
        parent_id=trade.order.parentId,
        oca_group=trade.order.ocaGroup or None,
    )


def _clean_order_price(val: float) -> float | None:
    """Convert ib_async UNSET sentinel to None for order prices."""
    if val is None or val >= _UNSET_DOUBLE * 0.9:
        return None
    return val
